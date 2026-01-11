#!/usr/bin/env python3
"""
System diagnostic script for troubleshooting
"""
import logging
import sys
from datetime import datetime, timedelta
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging
from procurement_lighthouse.config import config

def diagnose_database():
    """Diagnose database connectivity and schema"""
    print("=== Database Diagnostics ===")
    
    try:
        # Test connection
        with db.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            print(f"✅ PostgreSQL Version: {version['version']}")
            
            # Check tables exist
            tables = ['inventory', 'purchase_orders', 'po_line_items', 
                     'consumption_history', 'forecasts', 'alerts', 
                     'event_log', 'system_metrics']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                print(f"✅ Table {table}: {count} records")
            
            # Check triggers exist
            cursor.execute("""
                SELECT trigger_name, event_object_table 
                FROM information_schema.triggers 
                WHERE trigger_schema = 'public'
                ORDER BY event_object_table, trigger_name
            """)
            triggers = cursor.fetchall()
            
            print(f"\n📋 Database Triggers ({len(triggers)}):")
            for trigger in triggers:
                print(f"  - {trigger['trigger_name']} on {trigger['event_object_table']}")
            
            # Check views exist
            cursor.execute("""
                SELECT table_name FROM information_schema.views 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            views = cursor.fetchall()
            
            print(f"\n📊 Database Views ({len(views)}):")
            for view in views:
                print(f"  - {view['table_name']}")
                
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False
    
    return True

def diagnose_events():
    """Diagnose event system"""
    print("\n=== Event System Diagnostics ===")
    
    try:
        with db.cursor() as cursor:
            # Recent events
            cursor.execute("""
                SELECT event_type, COUNT(*) as count,
                       MAX(processed_at) as last_event
                FROM event_log 
                WHERE processed_at > NOW() - INTERVAL '1 hour'
                GROUP BY event_type
                ORDER BY count DESC
            """)
            recent_events = cursor.fetchall()
            
            if recent_events:
                print("📈 Recent Events (last hour):")
                for event in recent_events:
                    print(f"  - {event['event_type']}: {event['count']} events (last: {event['last_event']})")
            else:
                print("⚠️  No recent events found")
            
            # Event processing performance
            cursor.execute("""
                SELECT AVG(processing_duration_ms) as avg_ms,
                       MIN(processing_duration_ms) as min_ms,
                       MAX(processing_duration_ms) as max_ms,
                       COUNT(*) as total_events
                FROM event_log 
                WHERE processed_at > NOW() - INTERVAL '1 hour'
                  AND processing_duration_ms IS NOT NULL
            """)
            perf = cursor.fetchone()
            
            if perf and perf['total_events'] > 0:
                print(f"\n⚡ Processing Performance:")
                print(f"  - Average: {perf['avg_ms']:.1f}ms")
                print(f"  - Min: {perf['min_ms']}ms")
                print(f"  - Max: {perf['max_ms']}ms")
                print(f"  - Total events: {perf['total_events']}")
            else:
                print("⚠️  No performance data available")
                
    except Exception as e:
        print(f"❌ Event System Error: {e}")
        return False
    
    return True

def diagnose_alerts():
    """Diagnose alert system"""
    print("\n=== Alert System Diagnostics ===")
    
    try:
        with db.cursor() as cursor:
            # Alert counts by type and severity
            cursor.execute("""
                SELECT alert_type, severity, COUNT(*) as count,
                       MAX(created_at) as last_alert
                FROM alerts 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY alert_type, severity
                ORDER BY count DESC
            """)
            alerts = cursor.fetchall()
            
            if alerts:
                print("🚨 Recent Alerts (last 24 hours):")
                for alert in alerts:
                    print(f"  - {alert['alert_type']} ({alert['severity']}): {alert['count']} alerts (last: {alert['last_alert']})")
            else:
                print("ℹ️  No recent alerts")
            
            # Active alerts
            cursor.execute("""
                SELECT alert_type, severity, COUNT(*) as count
                FROM alerts 
                WHERE status = 'active'
                GROUP BY alert_type, severity
                ORDER BY severity DESC, count DESC
            """)
            active_alerts = cursor.fetchall()
            
            if active_alerts:
                print(f"\n🔴 Active Alerts:")
                for alert in active_alerts:
                    print(f"  - {alert['alert_type']} ({alert['severity']}): {alert['count']} active")
            else:
                print("\n✅ No active alerts")
                
    except Exception as e:
        print(f"❌ Alert System Error: {e}")
        return False
    
    return True

def diagnose_simulation():
    """Diagnose data simulation"""
    print("\n=== Data Simulation Diagnostics ===")
    
    try:
        with db.cursor() as cursor:
            # Recent inventory changes
            cursor.execute("""
                SELECT COUNT(*) as changes,
                       MAX(last_updated) as last_change
                FROM inventory 
                WHERE last_updated > NOW() - INTERVAL '10 minutes'
            """)
            inv_changes = cursor.fetchone()
            
            print(f"📦 Inventory Changes (last 10 min): {inv_changes['changes']}")
            if inv_changes['last_change']:
                print(f"    Last change: {inv_changes['last_change']}")
            
            # Recent consumption
            cursor.execute("""
                SELECT COUNT(*) as consumption,
                       SUM(quantity_consumed) as total_consumed,
                       MAX(consumption_date) as last_consumption
                FROM consumption_history 
                WHERE consumption_date > NOW() - INTERVAL '10 minutes'
            """)
            consumption = cursor.fetchone()
            
            print(f"🏭 Consumption Events (last 10 min): {consumption['consumption']}")
            if consumption['total_consumed']:
                print(f"    Total consumed: {consumption['total_consumed']} units")
                print(f"    Last consumption: {consumption['last_consumption']}")
            
            # PO activity
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM purchase_orders
                GROUP BY status
                ORDER BY status
            """)
            po_status = cursor.fetchall()
            
            print(f"\n🛒 Purchase Order Status:")
            for status in po_status:
                print(f"  - {status['status']}: {status['count']}")
            
            # Recent PO changes
            cursor.execute("""
                SELECT COUNT(*) as recent_pos
                FROM purchase_orders 
                WHERE created_date > NOW() - INTERVAL '1 hour'
                   OR (status IN ('approved', 'shipped', 'received') 
                       AND created_date > NOW() - INTERVAL '6 hours')
            """)
            recent_pos = cursor.fetchone()
            
            print(f"    Recent activity: {recent_pos['recent_pos']} POs")
            
    except Exception as e:
        print(f"❌ Simulation Error: {e}")
        return False
    
    return True

def diagnose_configuration():
    """Diagnose system configuration"""
    print("\n=== Configuration Diagnostics ===")
    
    print(f"🔧 Database Config:")
    print(f"  - Host: {config.database.host}")
    print(f"  - Port: {config.database.port}")
    print(f"  - Database: {config.database.database}")
    print(f"  - Max Connections: {config.database.max_connections}")
    
    print(f"\n⚙️  Event Config:")
    print(f"  - Channels: {', '.join(config.events.event_channels)}")
    print(f"  - Reconnect Delay: {config.events.reconnect_delay}s")
    print(f"  - Max Retries: {config.events.max_retries}")
    
    print(f"\n🎲 Simulator Config:")
    print(f"  - Inventory Interval: {config.simulator.inventory_event_interval}s")
    print(f"  - PO Interval: {config.simulator.po_event_interval}s")
    print(f"  - Max Items: {config.simulator.max_items}")
    print(f"  - Max POs: {config.simulator.max_pos}")
    
    print(f"\n🌐 Web Config:")
    print(f"  - Host: {config.web.host}")
    print(f"  - Port: {config.web.port}")
    print(f"  - Debug: {config.web.debug}")

def main():
    """Run system diagnostics"""
    setup_logging('INFO')
    
    print("🔍 Procurement Lighthouse System Diagnostics")
    print("=" * 50)
    
    all_good = True
    
    # Run diagnostics
    if not diagnose_database():
        all_good = False
    
    if not diagnose_events():
        all_good = False
    
    if not diagnose_alerts():
        all_good = False
    
    if not diagnose_simulation():
        all_good = False
    
    diagnose_configuration()
    
    print("\n" + "=" * 50)
    if all_good:
        print("✅ System diagnostics completed successfully")
    else:
        print("⚠️  Some issues detected - check output above")
    
    print("\n💡 Troubleshooting Tips:")
    print("1. Ensure PostgreSQL is running and accessible")
    print("2. Check that database schema is properly initialized")
    print("3. Verify both services are running:")
    print("   - python3 -m procurement_lighthouse.main events")
    print("   - python3 -m procurement_lighthouse.main simulate")
    print("4. Check logs for detailed error information")

if __name__ == "__main__":
    main()