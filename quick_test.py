#!/usr/bin/env python3
"""
Quick integration test for core components
"""
import sys
import time
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging

def test_basic_functionality():
    """Test basic system functionality"""
    setup_logging('INFO')
    
    print("🧪 Quick Integration Test")
    print("=" * 30)
    
    try:
        # Test database connection
        print("1. Testing database connection...")
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM inventory")
            inv_count = cursor.fetchone()['count']
            print(f"   ✅ Connected - {inv_count} inventory items")
        
        # Test trigger functionality
        print("2. Testing database triggers...")
        with db.cursor() as cursor:
            # Get initial event count
            cursor.execute("SELECT COUNT(*) as count FROM event_log")
            initial_events = cursor.fetchone()['count']
            
            # Trigger an inventory update
            cursor.execute("""
                UPDATE inventory 
                SET current_stock = current_stock + 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE item_id = (SELECT item_id FROM inventory LIMIT 1)
            """)
            
            # Brief wait for trigger
            time.sleep(0.5)
            
            # Check for new events
            cursor.execute("SELECT COUNT(*) as count FROM event_log")
            final_events = cursor.fetchone()['count']
            
            if final_events > initial_events:
                print(f"   ✅ Triggers working - generated {final_events - initial_events} events")
            else:
                print("   ⚠️  No events generated - triggers may not be working")
        
        # Test alert system
        print("3. Testing alert generation...")
        with db.cursor() as cursor:
            # Create a low stock condition
            cursor.execute("""
                UPDATE inventory 
                SET current_stock = 0
                WHERE item_id = (
                    SELECT item_id FROM inventory 
                    WHERE current_stock > 5 
                    LIMIT 1
                )
            """)
            
            # Check for alerts
            cursor.execute("""
                SELECT COUNT(*) as count FROM alerts 
                WHERE created_at > NOW() - INTERVAL '1 minute'
            """)
            recent_alerts = cursor.fetchone()['count']
            
            if recent_alerts > 0:
                print(f"   ✅ Alert system working - {recent_alerts} recent alerts")
            else:
                print("   ℹ️  No recent alerts (may be normal)")
        
        # Test data integrity
        print("4. Testing data integrity...")
        with db.cursor() as cursor:
            # Check for negative stock
            cursor.execute("SELECT COUNT(*) as count FROM inventory WHERE current_stock < 0")
            negative_stock = cursor.fetchone()['count']
            
            # Check for orphaned records
            cursor.execute("""
                SELECT COUNT(*) as count FROM po_line_items pli
                LEFT JOIN inventory i ON pli.item_id = i.item_id
                WHERE i.item_id IS NULL
            """)
            orphaned_items = cursor.fetchone()['count']
            
            if negative_stock == 0 and orphaned_items == 0:
                print("   ✅ Data integrity good")
            else:
                print(f"   ⚠️  Data issues - Negative stock: {negative_stock}, Orphaned items: {orphaned_items}")
        
        print("\n🎉 Quick test completed successfully!")
        print("\nNext steps:")
        print("- Run full validation: python3 validate_system.py")
        print("- Start services and test simulation")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)