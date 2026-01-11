#!/usr/bin/env python3
"""
Test script to verify data simulation functionality
"""
import time
import logging
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging

def test_inventory_simulation():
    """Test inventory simulator by checking for recent changes"""
    print("Testing inventory simulation...")
    
    try:
        with db.cursor() as cursor:
            # Get initial inventory state
            cursor.execute("""
                SELECT item_id, item_name, current_stock 
                FROM inventory 
                ORDER BY item_id 
                LIMIT 5
            """)
            initial_state = cursor.fetchall()
            
            print("Initial inventory state:")
            for item in initial_state:
                print(f"  {item['item_name']}: {item['current_stock']} units")
            
            print("\nWaiting 30 seconds for simulation events...")
            time.sleep(30)
            
            # Check for changes
            cursor.execute("""
                SELECT item_id, item_name, current_stock 
                FROM inventory 
                WHERE item_id IN %s
                ORDER BY item_id
            """, (tuple(item['item_id'] for item in initial_state),))
            
            final_state = cursor.fetchall()
            
            print("\nFinal inventory state:")
            changes_detected = False
            for i, item in enumerate(final_state):
                initial_stock = initial_state[i]['current_stock']
                final_stock = item['current_stock']
                change = final_stock - initial_stock
                
                print(f"  {item['item_name']}: {final_stock} units", end="")
                if change != 0:
                    print(f" ({change:+d})")
                    changes_detected = True
                else:
                    print()
            
            # Check consumption history
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM consumption_history 
                WHERE consumption_date > NOW() - INTERVAL '1 minute'
            """)
            recent_consumption = cursor.fetchone()
            
            print(f"\nRecent consumption events: {recent_consumption['count']}")
            
            if changes_detected or recent_consumption['count'] > 0:
                print("✅ Inventory simulation is working!")
            else:
                print("⚠️  No inventory changes detected")
                
    except Exception as e:
        print(f"❌ Error testing inventory simulation: {e}")

def test_po_simulation():
    """Test PO simulator by checking for status changes"""
    print("\nTesting PO simulation...")
    
    try:
        with db.cursor() as cursor:
            # Get current PO status counts
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM purchase_orders
                GROUP BY status
                ORDER BY status
            """)
            initial_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            print("Initial PO status counts:")
            for status, count in initial_counts.items():
                print(f"  {status}: {count}")
            
            print("\nWaiting 30 seconds for PO events...")
            time.sleep(30)
            
            # Check for changes
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM purchase_orders
                GROUP BY status
                ORDER BY status
            """)
            final_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            print("\nFinal PO status counts:")
            changes_detected = False
            all_statuses = set(initial_counts.keys()) | set(final_counts.keys())
            
            for status in sorted(all_statuses):
                initial = initial_counts.get(status, 0)
                final = final_counts.get(status, 0)
                change = final - initial
                
                print(f"  {status}: {final}", end="")
                if change != 0:
                    print(f" ({change:+d})")
                    changes_detected = True
                else:
                    print()
            
            # Check for recent PO updates
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM purchase_orders
                WHERE created_date > NOW() - INTERVAL '5 minutes'
                   OR (status IN ('approved', 'shipped', 'received') 
                       AND created_date > NOW() - INTERVAL '1 hour')
            """)
            recent_activity = cursor.fetchone()
            
            print(f"\nRecent PO activity: {recent_activity['count']} POs")
            
            if changes_detected or recent_activity['count'] > 0:
                print("✅ PO simulation is working!")
            else:
                print("⚠️  No PO changes detected")
                
    except Exception as e:
        print(f"❌ Error testing PO simulation: {e}")

def test_event_generation():
    """Test that events are being generated and logged"""
    print("\nTesting event generation...")
    
    try:
        with db.cursor() as cursor:
            # Check recent events
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM event_log
                WHERE processed_at > NOW() - INTERVAL '2 minutes'
                GROUP BY event_type
                ORDER BY event_type
            """)
            recent_events = cursor.fetchall()
            
            print("Recent events (last 2 minutes):")
            total_events = 0
            for event in recent_events:
                count = event['count']
                total_events += count
                print(f"  {event['event_type']}: {count}")
            
            if total_events > 0:
                print(f"✅ Event generation is working! ({total_events} total events)")
            else:
                print("⚠️  No recent events detected")
                
            # Check alerts
            cursor.execute("""
                SELECT alert_type, COUNT(*) as count
                FROM alerts
                WHERE created_at > NOW() - INTERVAL '5 minutes'
                GROUP BY alert_type
                ORDER BY alert_type
            """)
            recent_alerts = cursor.fetchall()
            
            if recent_alerts:
                print("\nRecent alerts:")
                for alert in recent_alerts:
                    print(f"  {alert['alert_type']}: {alert['count']}")
            else:
                print("\nNo recent alerts generated")
                
    except Exception as e:
        print(f"❌ Error testing event generation: {e}")

def main():
    """Run simulation tests"""
    setup_logging('INFO')
    
    print("=== Data Simulation Test ===")
    print("Make sure both services are running:")
    print("Terminal 1: python3 -m procurement_lighthouse.main events")
    print("Terminal 2: python3 -m procurement_lighthouse.main simulate")
    print()
    
    input("Press Enter when both services are running...")
    
    test_inventory_simulation()
    test_po_simulation()
    test_event_generation()
    
    print("\n=== Test Complete ===")
    print("Check the service logs for detailed processing information")

if __name__ == "__main__":
    main()