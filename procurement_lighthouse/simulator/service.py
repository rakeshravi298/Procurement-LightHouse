"""
Data simulation service runner
Manages both inventory and PO simulators for t2.micro
"""
import logging
import signal
import sys
import time
from threading import Event

from .inventory import inventory_simulator
from .purchase_orders import po_simulator
from ..utils import setup_logging

logger = logging.getLogger(__name__)

class DataSimulationService:
    """Service to run data simulation in background"""
    
    def __init__(self):
        self.shutdown_event = Event()
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def start(self):
        """Start the data simulation service"""
        if self.running:
            logger.warning("Data simulation service already running")
            return
        
        logger.info("Starting data simulation service...")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start simulators
        try:
            inventory_simulator.start()
            po_simulator.start()
            
            self.running = True
            logger.info("Data simulation service started")
            
            # Keep main thread alive and monitor simulators
            self._monitor_simulators()
            
        except Exception as e:
            logger.error(f"Failed to start simulators: {e}")
            self.shutdown()
            raise
    
    def _monitor_simulators(self):
        """Monitor simulator health and restart if needed"""
        restart_count = 0
        max_restarts = 3
        
        try:
            while not self.shutdown_event.is_set():
                # Check simulator health
                inv_running = inventory_simulator.is_running()
                po_running = po_simulator.is_running()
                
                if not inv_running or not po_running:
                    logger.warning(f"Simulator health check: Inventory={inv_running}, PO={po_running}")
                    
                    if restart_count < max_restarts:
                        logger.info("Attempting to restart failed simulators...")
                        
                        if not inv_running:
                            inventory_simulator.stop()
                            time.sleep(1)
                            inventory_simulator.start()
                        
                        if not po_running:
                            po_simulator.stop()
                            time.sleep(1)
                            po_simulator.start()
                        
                        restart_count += 1
                        time.sleep(5)  # Wait before next check
                    else:
                        logger.error("Maximum restart attempts reached, shutting down")
                        break
                else:
                    restart_count = 0  # Reset counter on successful check
                
                # Wait before next health check
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the service gracefully"""
        if not self.running:
            return
        
        logger.info("Shutting down data simulation service...")
        
        # Stop simulators
        inventory_simulator.stop()
        po_simulator.stop()
        
        # Signal shutdown
        self.shutdown_event.set()
        self.running = False
        
        logger.info("Data simulation service stopped")
    
    def is_running(self) -> bool:
        """Check if service is running"""
        return (self.running and 
                inventory_simulator.is_running() and 
                po_simulator.is_running())
    
    def get_status(self) -> dict:
        """Get service status information"""
        return {
            'service_running': self.running,
            'inventory_simulator': inventory_simulator.get_status(),
            'po_simulator': po_simulator.get_status()
        }


def main():
    """Main entry point for data simulation service"""
    setup_logging()
    
    service = DataSimulationService()
    
    try:
        service.start()
    except Exception as e:
        logger.error(f"Service startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()