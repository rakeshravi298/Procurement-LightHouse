"""
Event processing service runner
Optimized for t2.micro deployment
"""
import logging
import signal
import sys
import time
from threading import Thread, Event

from .listener import event_router
from ..utils import setup_logging

logger = logging.getLogger(__name__)

class EventProcessingService:
    """Service to run event processing in background"""
    
    def __init__(self):
        self.shutdown_event = Event()
        self.router_thread = None
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def start(self):
        """Start the event processing service"""
        if self.running:
            logger.warning("Event processing service already running")
            return
        
        logger.info("Starting event processing service...")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start event router in separate thread
        self.router_thread = Thread(target=self._run_router, daemon=True)
        self.router_thread.start()
        
        self.running = True
        logger.info("Event processing service started")
        
        # Keep main thread alive
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()
    
    def _run_router(self):
        """Run event router in thread"""
        try:
            event_router.start()
        except Exception as e:
            logger.error(f"Event router error: {e}")
        finally:
            self.shutdown_event.set()
    
    def shutdown(self):
        """Shutdown the service gracefully"""
        if not self.running:
            return
        
        logger.info("Shutting down event processing service...")
        
        # Stop event router
        event_router.stop()
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Wait for router thread to finish
        if self.router_thread and self.router_thread.is_alive():
            self.router_thread.join(timeout=5)
        
        self.running = False
        logger.info("Event processing service stopped")
    
    def is_running(self) -> bool:
        """Check if service is running"""
        return self.running and event_router.is_running()
    
    def get_status(self) -> dict:
        """Get service status information"""
        from .processor import event_processor
        
        return {
            'service_running': self.running,
            'router_running': event_router.is_running(),
            'processing_stats': event_processor.get_processing_stats()
        }


def main():
    """Main entry point for event processing service"""
    setup_logging()
    
    service = EventProcessingService()
    
    try:
        service.start()
    except Exception as e:
        logger.error(f"Service startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()