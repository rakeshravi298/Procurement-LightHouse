"""
Lightweight inventory simulator for t2.micro
Generates realistic inventory events with minimal CPU usage
"""
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading

from ..database.connection import db
from ..config import config
from ..utils import validate_positive_integer

logger = logging.getLogger(__name__)

class InventorySimulator:
    """Lightweight inventory event simulator optimized for t2.micro"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.items_cache = []
        self.last_cache_update = None
        
        # Event patterns optimized for t2.micro
        self.event_patterns = {
            'consumption': {
                'frequency': 0.7,  # 70% of events
                'min_quantity': 1,
                'max_quantity': 20,
                'departments': ['Manufacturing', 'Maintenance', 'Assembly', 'Quality Control']
            },
            'receipt': {
                'frequency': 0.2,  # 20% of events
                'min_quantity': 10,
                'max_quantity': 100,
                'reasons': ['Purchase Order Receipt', 'Return to Stock', 'Transfer In']
            },
            'adjustment': {
                'frequency': 0.1,  # 10% of events
                'min_quantity': -10,
                'max_quantity': 10,
                'reasons': ['Cycle Count Adjustment', 'Damage Write-off', 'Found Stock']
            }
        }
    
    def _load_inventory_items(self) -> List[Dict]:
        """Load inventory items with caching for t2.micro efficiency"""
        try:
            # Use cache if recent (5 minutes)
            if (self.last_cache_update and 
                datetime.now() - self.last_cache_update < timedelta(minutes=5) and
                self.items_cache):
                return self.items_cache
            
            # Load from database
            query = """
                SELECT item_id, item_name, current_stock, safety_stock, location
                FROM inventory
                WHERE current_stock >= 0
                ORDER BY item_id
            """
            
            self.items_cache = db.execute_query(query)
            self.last_cache_update = datetime.now()
            
            logger.debug(f"Loaded {len(self.items_cache)} inventory items")
            return self.items_cache
            
        except Exception as e:
            logger.error(f"Error loading inventory items: {e}")
            return []
    
    def _select_random_item(self, items: List[Dict]) -> Optional[Dict]:
        """Select random item with weighted selection for more realistic patterns"""
        if not items:
            return None
        
        # Weight selection towards items with higher stock levels
        # This creates more realistic consumption patterns
        weights = []
        for item in items:
            stock = item['current_stock']
            # Items with more stock are more likely to be consumed
            weight = max(1, stock // 10)  # Minimum weight of 1
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(items)
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, weight in enumerate(weights):
            current_weight += weight
            if rand_val <= current_weight:
                return items[i]
        
        return items[-1]  # Fallback
    
    def _generate_consumption_event(self, item: Dict) -> bool:
        """Generate inventory consumption event"""
        try:
            item_id = item['item_id']
            item_name = item['item_name']
            current_stock = item['current_stock']
            
            # Don't consume if stock is too low
            if current_stock <= 1:
                return False
            
            # Generate consumption quantity (conservative for t2.micro)
            pattern = self.event_patterns['consumption']
            max_consume = min(pattern['max_quantity'], current_stock - 1)
            quantity = random.randint(pattern['min_quantity'], max_consume)
            
            # Select random department and reason
            department = random.choice(pattern['departments'])
            reasons = ['Production', 'Maintenance', 'Testing', 'Assembly']
            reason = random.choice(reasons)
            
            # Update inventory (this will trigger database event)
            new_stock = current_stock - quantity
            
            with db.cursor() as cursor:
                # Update inventory
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = %s
                """, (new_stock, item_id))
                
                # Record consumption history
                cursor.execute("""
                    INSERT INTO consumption_history 
                    (item_id, quantity_consumed, consumption_reason, department)
                    VALUES (%s, %s, %s, %s)
                """, (item_id, quantity, reason, department))
            
            logger.info(f"Consumption: {item_name} -{quantity} units ({department}) -> {new_stock} remaining")
            return True
            
        except Exception as e:
            logger.error(f"Error generating consumption event: {e}")
            return False
    
    def _generate_receipt_event(self, item: Dict) -> bool:
        """Generate inventory receipt event"""
        try:
            item_id = item['item_id']
            item_name = item['item_name']
            current_stock = item['current_stock']
            
            # Generate receipt quantity
            pattern = self.event_patterns['receipt']
            quantity = random.randint(pattern['min_quantity'], pattern['max_quantity'])
            
            # Select random reason
            reason = random.choice(pattern['reasons'])
            
            # Update inventory (this will trigger database event)
            new_stock = current_stock + quantity
            
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = %s
                """, (new_stock, item_id))
            
            logger.info(f"Receipt: {item_name} +{quantity} units ({reason}) -> {new_stock} total")
            return True
            
        except Exception as e:
            logger.error(f"Error generating receipt event: {e}")
            return False
    
    def _generate_adjustment_event(self, item: Dict) -> bool:
        """Generate inventory adjustment event"""
        try:
            item_id = item['item_id']
            item_name = item['item_name']
            current_stock = item['current_stock']
            
            # Generate adjustment quantity
            pattern = self.event_patterns['adjustment']
            quantity = random.randint(pattern['min_quantity'], pattern['max_quantity'])
            
            # Ensure we don't go negative
            if current_stock + quantity < 0:
                quantity = -current_stock + 1
            
            # Skip if no meaningful adjustment
            if quantity == 0:
                return False
            
            # Select random reason
            reason = random.choice(pattern['reasons'])
            
            # Update inventory (this will trigger database event)
            new_stock = current_stock + quantity
            
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = %s
                """, (new_stock, item_id))
            
            adjustment_type = "+" if quantity > 0 else ""
            logger.info(f"Adjustment: {item_name} {adjustment_type}{quantity} units ({reason}) -> {new_stock} total")
            return True
            
        except Exception as e:
            logger.error(f"Error generating adjustment event: {e}")
            return False
    
    def _generate_single_event(self) -> bool:
        """Generate a single inventory event"""
        try:
            # Load inventory items
            items = self._load_inventory_items()
            if not items:
                logger.warning("No inventory items available for simulation")
                return False
            
            # Select random item
            item = self._select_random_item(items)
            if not item:
                return False
            
            # Determine event type based on frequency
            rand_val = random.random()
            
            if rand_val < self.event_patterns['consumption']['frequency']:
                return self._generate_consumption_event(item)
            elif rand_val < (self.event_patterns['consumption']['frequency'] + 
                           self.event_patterns['receipt']['frequency']):
                return self._generate_receipt_event(item)
            else:
                return self._generate_adjustment_event(item)
                
        except Exception as e:
            logger.error(f"Error generating inventory event: {e}")
            return False
    
    def _simulation_loop(self):
        """Main simulation loop optimized for t2.micro"""
        logger.info("Inventory simulation started")
        
        event_count = 0
        error_count = 0
        
        while self.running:
            try:
                # Generate event
                success = self._generate_single_event()
                
                if success:
                    event_count += 1
                else:
                    error_count += 1
                
                # Log progress periodically
                if event_count % 10 == 0:
                    logger.info(f"Inventory simulation: {event_count} events generated, {error_count} errors")
                
                # Sleep for configured interval (conservative for t2.micro)
                time.sleep(config.simulator.inventory_event_interval)
                
            except Exception as e:
                logger.error(f"Simulation loop error: {e}")
                error_count += 1
                time.sleep(5)  # Brief pause on error
        
        logger.info(f"Inventory simulation stopped. Generated {event_count} events")
    
    def start(self):
        """Start the inventory simulator"""
        if self.running:
            logger.warning("Inventory simulator already running")
            return
        
        logger.info("Starting inventory simulator...")
        self.running = True
        
        # Start simulation in separate thread
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Inventory simulator started (interval: {config.simulator.inventory_event_interval}s)")
    
    def stop(self):
        """Stop the inventory simulator"""
        if not self.running:
            return
        
        logger.info("Stopping inventory simulator...")
        self.running = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("Inventory simulator stopped")
    
    def is_running(self) -> bool:
        """Check if simulator is running"""
        return self.running and self.thread and self.thread.is_alive()
    
    def get_status(self) -> Dict:
        """Get simulator status"""
        return {
            'running': self.is_running(),
            'items_cached': len(self.items_cache),
            'last_cache_update': self.last_cache_update.isoformat() if self.last_cache_update else None,
            'event_interval': config.simulator.inventory_event_interval
        }


# Global inventory simulator instance
inventory_simulator = InventorySimulator()