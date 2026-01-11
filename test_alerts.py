#!/usr/bin/env python3
"""
Test script for alert management system
"""
import time
import logging
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging

def test_stock_alerts():
    """Test stock-related alerts"""
    print("Testing stock alerts...")
    
    try:
        with db.cursor() as cursor:
            # Get initial alert count
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'active'")
            initial_alerts = cursor.fetchone()['count']
            
            # Create low stock condition
            cursor.execute("""
                UPDATE inventory 
                SET current_stock = safety_stock - 1
                WHERE item_id = (
                    SELECT item_id FROM inventory 
                    WHERE current_stock > safety_stock + 5
                    LIMIT 1
                )
                RETURNING item_id, item_name, current_stock, safety_stock
            """)
            
            updated_item = cursor.fetchone()
            if updated_item:
                print(f"   Created low stock condition for {updated_item['item_name']}")
                print(f"   Stock: {updated_item['current_stock']}, Safety: {updated_item['safety_stock']}")
                
                # Wait for event processing
                time.sleep(3)
                
                # Check for new alerts
                cursor.execute("""
                    SELECT COUNT(*) as count FROM alerts 
                    WHERE status = 'active' 
                      AND item_id = %s
                      AND created_at > NOW() - INTERVAL '1 minute'
                """, (updated_item['item_id'],))
                
                new_alerts = cursor.fetchone()['count']
                
                if new_alerts > 0:
                    print(f"   ✅ Generated {new_alerts} stock alerts")
                else:
                    print("   ⚠️  No stock alerts generated")
            else:
                print("   ⚠️  Could not create low stock condition")
                
    except Exception as e:
        print(f"   ❌ Error testing stock alerts: {e}")

def test_delivery_alerts():
    """Test delivery-related alerts"""
    print("\nTesting delivery alerts...")
    
    try:
        with db.cursor() as cursor:
            # Create overdue delivery condition
            cursor.execute("""
                UPDATE purchase_orders 
                SET expected_delivery = CURRENT_DATE - INTERVAL '5 days'
                WHERE po_id = (
                    SELECT po_id FROM purchase_orders 
                    WHERE status IN ('created', 'approved', 'shipped')
                      AND expected_delivery > CURRENT_DATE
                    LIMIT 1
                )
                RETURNING po_id, supplier_name, expected_delivery, status
            """)
            
            updated_po = cursor.fetchone()
            if updated_po:
                print(f"   Created overdue condition for PO {updated_po['po_id']} ({updated_po['supplier_name']})")
                print(f"   Expected: {updated_po['expected_delivery']}, Status: {updated_po['status']}")
                
                # Trigger PO status update to generate event
                cursor.execute("""
                    UPDATE purchase_orders 
                    SET status = %s
                    WHERE po_id = %s
                """, (updated_po['status'], updated_po['po_id']))  # Same status to trigger event
                
                # Wait for event processing
                time.sleep(3)
                
                # Check for new alerts
                cursor.execute("""
                    SELECT COUNT(*) as count FROM alerts 
                    WHERE status = 'active' 
                      AND po_id = %s
                      AND created_at > NOW() - INTERVAL '1 minute'
                """, (updated_po['po_id'],))
                
                new_alerts = cursor.fetchone()['count']
                
                if new_alerts > 0:
                    print(f"   ✅ Generated {new_alerts} delivery alerts")
                else:
                    print("   ⚠️  No delivery alerts generated")
            else:
                print("   ⚠️  Could not create overdue delivery condition")
                
    except Exception as e:
        print(f"   ❌ Error testing delivery alerts: {e}")

def test_alert_resolution():
    """Test alert auto-resolution"""
    print("\nTesting alert resolution...")
    
    try:
        from procurement_lighthouse.alerts.service import alert_service
        
        # Get active alerts before resolution
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'active'")
            active_before = cursor.fetchone()['count']
        
        # Run alert maintenance (includes auto-resolution)
        maintenance_results = alert_service.run_maintenance()
        
        # Get active alerts after resolution
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'active'")
            active_after = cursor.fetchone()['count']
        
        resolved_count = maintenance_results.get('alerts_resolved', 0)
        
        print(f"   Active alerts before: {active_before}")
        print(f"   Active alerts after: {active_after}")
        print(f"   Alerts resolved: {resolved_count}")
        
        if resolved_count > 0:
            print("   ✅ Alert resolution working")
        else:
            print("   ℹ️  No alerts needed resolution")
            
    except Exception as e:
        print(f"   ❌ Error testing alert resolution: {e}")

def test_alert_dashboard():
    """Test alert dashboard data"""
    print("\nTesting alert dashboard...")
    
    try:
        from procurement_lighthouse.alerts.service import alert_service
        
        # Get dashboard data
        dashboard_data = alert_service.get_alert_dashboard_data()
        
        if dashboard_data:
            summary = dashboard_data.get('summary', {})
            active_alerts = dashboard_data.get('active_alerts', [])
            
            print(f"   Total active alerts: {summary.get('total_active', 0)}")
            print(f"   Recent alerts (1h): {summary.get('recent_alerts_1h', 0)}")
            print(f"   Alert types: {len(summary.get('active_by_type', {}))}")
            print(f"   Top alerts retrieved: {len(active_alerts)}")
            
            if summary.get('active_by_severity'):
                print("   By severity:")
                for severity, count in summary['active_by_severity'].items():
                    print(f"     {severity}: {count}")
            
            print("   ✅ Alert dashboard data available")
        else:
            print("   ❌ No dashboard data available")
            
    except Exception as e:
        print(f"   ❌ Error testing alert dashboard: {e}")

def test_alert_deduplication():
    """Test alert deduplication"""
    print("\nTesting alert deduplication...")
    
    try:
        from procurement_lighthouse.alerts.manager import alert_manager, AlertType, AlertSeverity
        
        # Get initial alert count
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM alerts")
            initial_count = cursor.fetchone()['count']
        
        # Try to create duplicate alerts
        test_item_id = 1
        alert1 = alert_manager._create_alert(
            AlertType.STOCK_LOW, 
            AlertSeverity.MEDIUM, 
            "Test alert 1", 
            item_id=test_item_id
        )
        
        alert2 = alert_manager._create_alert(
            AlertType.STOCK_LOW, 
            AlertSeverity.MEDIUM, 
            "Test alert 2", 
            item_id=test_item_id
        )
        
        # Get final alert count
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM alerts")
            final_count = cursor.fetchone()['count']
        
        alerts_created = final_count - initial_count
        
        print(f"   Attempted to create 2 duplicate alerts")
        print(f"   Actually created: {alerts_created}")
        
        if alerts_created == 1:
            print("   ✅ Deduplication working correctly")
        elif alerts_created == 2:
            print("   ⚠️  Deduplication may not be working")
        else:
            print("   ❓ Unexpected result")
            
    except Exception as e:
        print(f"   ❌ Error testing alert deduplication: {e}")

def main():
    """Run alert system tests"""
    setup_logging('INFO')
    
    print("=== Alert Management System Test ===")
    print("Make sure event processing service is running:")
    print("python3 -m procurement_lighthouse.main events")
    print()
    
    input("Press Enter when event processing service is running...")
    
    test_stock_alerts()
    test_delivery_alerts()
    test_alert_resolution()
    test_alert_dashboard()
    test_alert_deduplication()
    
    print("\n=== Test Complete ===")
    print("Check alerts with: python3 -m procurement_lighthouse.main alerts")

if __name__ == "__main__":
    main()