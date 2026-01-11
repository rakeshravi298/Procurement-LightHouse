"""
PostgreSQL event listener using LISTEN/NOTIFY
Optimized for t2.micro - single connection, minimal memory usage
"""
import logging
import time
import json
import select
from typing import Dict, Callable, Optional
import psycopg2
import psycopg2.extensions

from ..config import config
from ..utils import parse_event_payload

logger = logging.getLogger(__name__)

class EventListener:
    """Lightweight PostgreSQL event listener for t2.micro"""
    
    def __init__(self):
        self._connection: Optional[psycopg2.connection] = None
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        
        # Connection parameters
        self._conn_params = {
            'host': config.database.host,
            'port': config.database.port,
            'database': config.database.database,
            'user': config.database.username,
            'password': config.database.password
        }
    
    def connect(self) -> bool:
        """Establish database connection for listening"""
        try:
            self._connection = psycopg2.connect(**self._conn_params)
            self._connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            logger.info("Event listener connected to database")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Failed to connect event listener: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Event listener disconnected")
    
    def register_handler(self, channel: str, handler: Callable):
        """Register event handler for specific channel"""
        self._handlers[channel] = handler
        logger.info(f"Registered handler for channel: {channel}")
    
    def subscribe_to_channels(self):
        """Subscribe to all configured event channels"""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        for channel in config.events.event_channels:
            cursor.execute(f"LISTEN {channel}")
            logger.info(f"Subscribed to channel: {channel}")
        
        cursor.close()
    
    def _reconnect_with_backoff(self) -> bool:
        """Reconnect with exponential backoff"""
        max_retries = config.events.max_retries
        base_delay = config.events.reconnect_delay
        
        for attempt in range(max_retries):
            delay = base_delay * (2 ** attempt)
            logger.info(f"Reconnection attempt {attempt + 1}/{max_retries} in {delay}s")
            time.sleep(delay)
            
            if self.connect():
                self.subscribe_to_channels()
                return True
        
        logger.error("Failed to reconnect after maximum retries")
        return False
    
    def _handle_notification(self, notification):
        """Process incoming notification"""
        try:
            channel = notification.channel
            payload = notification.payload
            
            logger.debug(f"Received notification on {channel}: {payload}")
            
            # Parse payload
            event_data = parse_event_payload(payload)
            if not event_data:
                logger.warning(f"Invalid payload on channel {channel}: {payload}")
                return
            
            # Find and execute handler
            handler = self._handlers.get(channel)
            if handler:
                try:
                    handler(channel, event_data)
                except Exception as e:
                    logger.error(f"Handler error for {channel}: {e}")
            else:
                logger.warning(f"No handler registered for channel: {channel}")
                
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
    
    def start_listening(self):
        """Start the event listening loop"""
        if not self.connect():
            raise RuntimeError("Failed to establish database connection")
        
        self.subscribe_to_channels()
        self._running = True
        
        logger.info("Event listener started")
        
        try:
            while self._running:
                # Check for connection issues
                if self._connection.closed:
                    logger.warning("Database connection lost, attempting reconnection")
                    if not self._reconnect_with_backoff():
                        break
                
                # Wait for notifications with timeout
                if select.select([self._connection], [], [], 1) == ([], [], []):
                    continue  # Timeout, check if still running
                
                # Process notifications
                self._connection.poll()
                
                while self._connection.notifies:
                    notification = self._connection.notifies.pop(0)
                    self._handle_notification(notification)
                    
        except KeyboardInterrupt:
            logger.info("Event listener interrupted by user")
        except Exception as e:
            logger.error(f"Event listener error: {e}")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop the event listening loop"""
        self._running = False
        self.disconnect()
        logger.info("Event listener stopped")
    
    def is_running(self) -> bool:
        """Check if listener is currently running"""
        return self._running and self._connection and not self._connection.closed


class EventRouter:
    """Routes events to appropriate processors"""
    
    def __init__(self):
        self.listener = EventListener()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup event handlers for each channel"""
        # Import processor here to avoid circular imports
        from .processor import event_processor
        self.processor = event_processor
        
        # Register handlers for each event type
        self.listener.register_handler('inventory_changed', self._handle_inventory_event)
        self.listener.register_handler('po_status_changed', self._handle_po_event)
        self.listener.register_handler('alert_generated', self._handle_alert_event)
        self.listener.register_handler('forecast_updated', self._handle_forecast_event)
    
    def _handle_inventory_event(self, channel: str, event_data: dict):
        """Handle inventory change events"""
        # Log the event for monitoring
        self._log_event('inventory_changed', event_data)
        
        # Process with event processor
        self.processor.process_inventory_event(channel, event_data)
    
    def _handle_po_event(self, channel: str, event_data: dict):
        """Handle purchase order events"""
        # Log the event for monitoring
        self._log_event('po_status_changed', event_data)
        
        # Process with event processor
        self.processor.process_po_event(channel, event_data)
    
    def _handle_alert_event(self, channel: str, event_data: dict):
        """Handle alert generation events"""
        # Log the event for monitoring
        self._log_event('alert_generated', event_data)
        
        # Process with event processor
        self.processor.process_alert_event(channel, event_data)
    
    def _handle_forecast_event(self, channel: str, event_data: dict):
        """Handle forecast update events"""
        # Log the event for monitoring
        self._log_event('forecast_updated', event_data)
        
        # Process with event processor
        self.processor.process_forecast_event(channel, event_data)
    
    def _log_event(self, event_type: str, event_data: dict):
        """Log event to file for monitoring (lightweight for t2.micro)"""
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"{timestamp} | {event_type} | {json.dumps(event_data)}\n"
            
            # Write to event log file
            with open('/var/log/procurement_lighthouse_events.log', 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
    def start(self):
        """Start the event router"""
        logger.info("Starting event router...")
        self.listener.start_listening()
    
    def stop(self):
        """Stop the event router"""
        logger.info("Stopping event router...")
        self.listener.stop_listening()
    
    def is_running(self) -> bool:
        """Check if router is running"""
        return self.listener.is_running()


# Global event router instance
event_router = EventRouter()