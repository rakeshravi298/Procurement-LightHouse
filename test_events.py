#!/usr/bin/env python3
"""
Simple test script to verify event processing functionality
"""
import time
import logging
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging

def test_inventory_events():
    """Test inventory change events"""
    print("Testing inventory events...")
    
    try:
        # Update inventory to trigger event
        with db.cursor() as cursor:
            # Get first inventory item
            cursor.execute("SELECT item_id, current_stock FROM inventory LIMIT 1")
            item = cursor.fetchone()
            
            if item:
                item_id = item['item_id']
                current_stock = item['current_stock']
                new_stock = current_stock - 5  # Simulate consumption
                
                print(f"Updating item {item_id}: {current_stock} -> {new_stock}")
                
                # Update inventory (this should trigger event)
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = %s
                """, (new_stock, item_id))
                
                print("Inventory updated - event should be triggered")
                
                # Wait a moment for processing
                time.sleep(2)
                
                # Check if event was logged
                cursor.execute("""
                    SELECT COUNT(*) as count FROM event_log 
                    WHERE event_type = 'inventory_changed' 
                    AND processed_at > NOW() - INTERVAL '1 minute'
                """)
                result = cursor.fetchone()
                print(f"Recent inventory events logged: {result['count']}")
                
                # Check for alerts
                cursor.execute("""
                    SELECT COUNT(*) as count FROM alerts 
                    WHERE item_id = %s AND status = 'active'
                    AND created_at > NOW() - INTERVAL '1 minute'
                """, (item_id,))
                alert_result = cursor.fetchone()
                print(f"New alerts generated: {alert_result['count']}")
                
    except Exception as e:
        print(f"Error testing inventory events: {e}")

def test_po_events():
    """Test purchase order events"""
    print("\nTesting PO events...")
    
    try:
        with db.cursor() as cursor:
            # Get first PO
            cursor.execute("SELECT po_id, status FROM purchase_orders LIMIT 1")
            po = cursor.fetchone()
            
            if po:
                po_id = po['po_id']
                current_status = po['status']
                new_status = 'shipped' if current_status != 'shipped' else 'received'
                
                print(f"Updating PO {po_id}: {current_status} -> {new_status}")
                
                # Update PO status (this should trigger event)
                cursor.execute("""
                    UPDATE purchase_orders 
                    SET status = %s
                    WHERE po_id = %s
                """, (new_status, po_id))
                
                print("PO updated - event should be triggered")
                
                # Wait a moment for processing
                time.sleep(2)
                
                # Check if event was logged
                cursor.execute("""
                    SELECT COUNT(*) as count FROM event_log 
                    WHERE event_type = 'po_status_changed' 
                    AND processed_at > NOW() - INTERVAL '1 minute'
                """)
                result = cursor.fetchone()
                print(f"Recent PO events logged: {result['count']}")
                
    except Exception as e:
        print(f"Error testing PO events: {e}")

def test_manual_alert():
    """Test manual alert generation"""
    print("\nTesting manual alert generation...")
    
    try:
        with db.cursor() as cursor:
            # Insert a test alert
            cursor.execute("""
                INSERT INTO alerts (alert_type, severity, message)
                VALUES ('test_alert', 'low', 'Test alert for event processing verification')
            """)
            
            print("Test alert inserted - event should be triggered")
            
            # Wait a moment for processing
            time.sleep(2)
            
            # Check if event was logged
            cursor.execute("""
                SELECT COUNT(*) as count FROM event_log 
                WHERE event_type = 'alert_generated' 
                AND processed_at > NOW() - INTERVAL '1 minute'
            """)
            result = cursor.fetchone()
            print(f"Recent alert events logged: {result['count']}")
            
    except Exception as e:
        print(f"Error testing manual alert: {e}")

def main():
    """Run event processing tests"""
    setup_logging('INFO')
    
    print("=== Event Processing Test ===")
    print("Make sure event processing service is running:")
    print("python3 -m procurement_lighthouse.main events")
    print()
    
    input("Press Enter when event processing service is running...")
    
    test_inventory_events()
    test_po_events()
    test_manual_alert()
    
    print("\n=== Test Complete ===")
    print("Check the event processing service logs for detailed processing information")

if __name__ == "__main__":
    main()