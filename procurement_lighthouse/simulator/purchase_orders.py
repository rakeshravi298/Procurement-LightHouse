"""
Simple purchase order simulator for t2.micro
Simulates PO lifecycle with longer delays to reduce CPU load
"""
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading

from ..database.connection import db
from ..config import config

logger = logging.getLogger(__name__)

class PurchaseOrderSimulator:
    """Simple PO lifecycle simulator optimized for t2.micro"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.pos_cache = []
        self.suppliers = [
            'Acme Steel Supply', 'Metro Materials', 'Industrial Parts Co',
            'Quality Components', 'Reliable Suppliers Inc', 'Prime Manufacturing',
            'Global Parts Ltd', 'Precision Tools Corp', 'Standard Supply Co'
        ]
        
        # PO lifecycle patterns (conservative timing for t2.micro)
        self.lifecycle_patterns = {
            'created_to_approved': {
                'probability': 0.8,  # 80% chance to approve
                'min_delay_hours': 1,
                'max_delay_hours': 24
            },
            'approved_to_shipped': {
                'probability': 0.9,  # 90% chance to ship
                'min_delay_hours': 24,
                'max_delay_hours': 168  # 1 week
            },
            'shipped_to_received': {
                'probability': 0.95,  # 95% chance to receive
                'min_delay_hours': 24,
                'max_delay_hours': 72  # 3 days
            },
            'create_new_po': {
                'probability': 0.3,  # 30% chance to create new PO per cycle
                'min_items': 1,
                'max_items': 3
            }
        }
    
    def _load_purchase_orders(self) -> List[Dict]:
        """Load active purchase orders"""
        try:
            query = """
                SELECT po_id, supplier_name, status, created_date, 
                       expected_delivery, total_value
                FROM purchase_orders
                WHERE status IN ('created', 'approved', 'shipped')
                ORDER BY created_date DESC
                LIMIT %s
            """
            
            return db.execute_query(query, (config.simulator.max_pos,))
            
        except Exception as e:
            logger.error(f"Error loading purchase orders: {e}")
            return []
    
    def _get_low_stock_items(self) -> List[Dict]:
        """Get items that are low on stock for PO creation"""
        try:
            query = """
                SELECT item_id, item_name, current_stock, safety_stock, unit_cost
                FROM inventory
                WHERE current_stock <= safety_stock * 1.5
                ORDER BY (current_stock::float / safety_stock) ASC
                LIMIT 10
            """
            
            return db.execute_query(query)
            
        except Exception as e:
            logger.error(f"Error getting low stock items: {e}")
            return []
    
    def _create_new_purchase_order(self) -> bool:
        """Create a new purchase order for low stock items"""
        try:
            # Get items that need restocking
            low_stock_items = self._get_low_stock_items()
            if not low_stock_items:
                logger.debug("No low stock items found for PO creation")
                return False
            
            # Select random supplier
            supplier = random.choice(self.suppliers)
            
            # Select 1-3 items for the PO
            pattern = self.lifecycle_patterns['create_new_po']
            num_items = random.randint(pattern['min_items'], 
                                     min(pattern['max_items'], len(low_stock_items)))
            selected_items = random.sample(low_stock_items, num_items)
            
            # Calculate delivery date (5-14 days from now)
            delivery_date = datetime.now().date() + timedelta(
                days=random.randint(5, 14)
            )
            
            # Calculate total value
            total_value = 0
            po_items = []
            
            for item in selected_items:
                # Order enough to bring stock above safety level
                safety_stock = item['safety_stock']
                current_stock = item['current_stock']
                unit_cost = float(item['unit_cost']) if item['unit_cost'] else 1.0
                
                # Order 2-3x safety stock to ensure good coverage
                order_quantity = random.randint(safety_stock * 2, safety_stock * 3)
                line_total = order_quantity * unit_cost
                total_value += line_total
                
                po_items.append({
                    'item_id': item['item_id'],
                    'quantity': order_quantity,
                    'unit_price': unit_cost
                })
            
            # Create purchase order
            with db.cursor() as cursor:
                # Insert PO
                cursor.execute("""
                    INSERT INTO purchase_orders 
                    (supplier_name, status, expected_delivery, total_value)
                    VALUES (%s, 'created', %s, %s)
                    RETURNING po_id
                """, (supplier, delivery_date, total_value))
                
                po_result = cursor.fetchone()
                po_id = po_result['po_id']
                
                # Insert PO line items
                for po_item in po_items:
                    cursor.execute("""
                        INSERT INTO po_line_items 
                        (po_id, item_id, quantity_ordered, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (po_id, po_item['item_id'], po_item['quantity'], po_item['unit_price']))
            
            logger.info(f"Created PO {po_id}: {supplier}, {num_items} items, ${total_value:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating purchase order: {e}")
            return False
    
    def _advance_po_status(self, po: Dict) -> bool:
        """Advance PO to next status in lifecycle"""
        try:
            po_id = po['po_id']
            current_status = po['status']
            supplier_name = po['supplier_name']
            created_date = po['created_date']
            
            # Determine next status and check timing
            next_status = None
            should_advance = False
            
            if current_status == 'created':
                pattern = self.lifecycle_patterns['created_to_approved']
                hours_since_created = (datetime.now() - created_date).total_seconds() / 3600
                
                if (hours_since_created >= pattern['min_delay_hours'] and
                    random.random() < pattern['probability']):
                    next_status = 'approved'
                    should_advance = True
            
            elif current_status == 'approved':
                pattern = self.lifecycle_patterns['approved_to_shipped']
                hours_since_created = (datetime.now() - created_date).total_seconds() / 3600
                
                if (hours_since_created >= pattern['min_delay_hours'] and
                    random.random() < pattern['probability']):
                    next_status = 'shipped'
                    should_advance = True
            
            elif current_status == 'shipped':
                pattern = self.lifecycle_patterns['shipped_to_received']
                hours_since_created = (datetime.now() - created_date).total_seconds() / 3600
                
                if (hours_since_created >= pattern['min_delay_hours'] and
                    random.random() < pattern['probability']):
                    next_status = 'received'
                    should_advance = True
            
            if should_advance and next_status:
                # Update PO status (this will trigger database event)
                with db.cursor() as cursor:
                    cursor.execute("""
                        UPDATE purchase_orders 
                        SET status = %s
                        WHERE po_id = %s
                    """, (next_status, po_id))
                
                logger.info(f"PO {po_id} ({supplier_name}): {current_status} -> {next_status}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error advancing PO status: {e}")
            return False
    
    def _process_existing_pos(self) -> int:
        """Process existing POs and advance their status"""
        try:
            pos = self._load_purchase_orders()
            advanced_count = 0
            
            for po in pos:
                if self._advance_po_status(po):
                    advanced_count += 1
                    
                    # Small delay between PO updates to reduce load
                    time.sleep(0.5)
            
            return advanced_count
            
        except Exception as e:
            logger.error(f"Error processing existing POs: {e}")
            return 0
    
    def _generate_single_event(self) -> bool:
        """Generate a single PO-related event"""
        try:
            # Decide whether to create new PO or advance existing ones
            create_probability = self.lifecycle_patterns['create_new_po']['probability']
            
            if random.random() < create_probability:
                # Try to create new PO
                return self._create_new_purchase_order()
            else:
                # Process existing POs
                advanced_count = self._process_existing_pos()
                return advanced_count > 0
                
        except Exception as e:
            logger.error(f"Error generating PO event: {e}")
            return False
    
    def _simulation_loop(self):
        """Main PO simulation loop optimized for t2.micro"""
        logger.info("PO simulation started")
        
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
                if event_count % 5 == 0:
                    logger.info(f"PO simulation: {event_count} events generated, {error_count} errors")
                
                # Sleep for configured interval (longer for POs to reduce CPU load)
                time.sleep(config.simulator.po_event_interval)
                
            except Exception as e:
                logger.error(f"PO simulation loop error: {e}")
                error_count += 1
                time.sleep(10)  # Longer pause on error
        
        logger.info(f"PO simulation stopped. Generated {event_count} events")
    
    def start(self):
        """Start the PO simulator"""
        if self.running:
            logger.warning("PO simulator already running")
            return
        
        logger.info("Starting PO simulator...")
        self.running = True
        
        # Start simulation in separate thread
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"PO simulator started (interval: {config.simulator.po_event_interval}s)")
    
    def stop(self):
        """Stop the PO simulator"""
        if not self.running:
            return
        
        logger.info("Stopping PO simulator...")
        self.running = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("PO simulator stopped")
    
    def is_running(self) -> bool:
        """Check if simulator is running"""
        return self.running and self.thread and self.thread.is_alive()
    
    def get_status(self) -> Dict:
        """Get simulator status"""
        try:
            # Get current PO counts by status
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM purchase_orders
                    GROUP BY status
                """)
                status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            return {
                'running': self.is_running(),
                'event_interval': config.simulator.po_event_interval,
                'po_status_counts': status_counts,
                'suppliers_available': len(self.suppliers)
            }
            
        except Exception as e:
            logger.error(f"Error getting PO simulator status: {e}")
            return {
                'running': self.is_running(),
                'event_interval': config.simulator.po_event_interval,
                'error': str(e)
            }


# Global PO simulator instance
po_simulator = PurchaseOrderSimulator()