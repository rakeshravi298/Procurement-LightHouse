#!/usr/bin/env python3
"""
Comprehensive system validation for Procurement Lighthouse PoC
Tests the complete event-driven system end-to-end
"""
import time
import logging
import sys
from datetime import datetime, timedelta
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging

class SystemValidator:
    """Validates the core event system functionality"""
    
    def __init__(self):
        self.test_results = []
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for validation"""
        setup_logging('INFO')
        self.logger = logging.getLogger(__name__)
    
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append((test_name, passed, message))
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        if not passed:
            self.logger.error(f"Test failed: {test_name} - {message}")
    
    def test_database_connection(self) -> bool:
        """Test database connectivity and basic queries"""
        try:
            with db.cursor() as cursor:
                # Test basic connectivity
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                if result['test'] != 1:
                    self.log_test_result("Database Connection", False, "Basic query failed")
                    return False
                
                # Test inventory table
                cursor.execute("SELECT COUNT(*) as count FROM inventory")
                inv_count = cursor.fetchone()['count']
                
                # Test purchase orders table
                cursor.execute("SELECT COUNT(*) as count FROM purchase_orders")
                po_count = cursor.fetchone()['count']
                
                # Test event log table
                cursor.execute("SELECT COUNT(*) as count FROM event_log")
                event_count = cursor.fetchone()['count']
                
                self.log_test_result(
                    "Database Connection", 
                    True, 
                    f"Inventory: {inv_count}, POs: {po_count}, Events: {event_count}"
                )
                return True
                
        except Exception as e:
            self.log_test_result("Database Connection", False, str(e))
            return False
    
    def test_database_triggers(self) -> bool:
        """Test that database triggers are working"""
        try:
            with db.cursor() as cursor:
                # Get initial event count
                cursor.execute("SELECT COUNT(*) as count FROM event_log")
                initial_count = cursor.fetchone()['count']
                
                # Update an inventory item to trigger event
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = current_stock + 1,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = (SELECT item_id FROM inventory LIMIT 1)
                """)
                
                # Wait briefly for trigger processing
                time.sleep(1)
                
                # Check if event was logged
                cursor.execute("""
                    SELECT COUNT(*) as count FROM event_log 
                    WHERE processed_at > NOW() - INTERVAL '10 seconds'
                """)
                new_events = cursor.fetchone()['count']
                
                if new_events > 0:
                    self.log_test_result(
                        "Database Triggers", 
                        True, 
                        f"Generated {new_events} events"
                    )
                    return True
                else:
                    self.log_test_result(
                        "Database Triggers", 
                        False, 
                        "No events generated from inventory update"
                    )
                    return False
                    
        except Exception as e:
            self.log_test_result("Database Triggers", False, str(e))
            return False
    
    def test_event_processing(self) -> bool:
        """Test event processing functionality"""
        try:
            with db.cursor() as cursor:
                # Check for recent event processing
                cursor.execute("""
                    SELECT COUNT(*) as count FROM event_log 
                    WHERE processed_at > NOW() - INTERVAL '5 minutes'
                """)
                recent_events = cursor.fetchone()['count']
                
                # Check system metrics
                cursor.execute("""
                    SELECT COUNT(*) as count FROM system_metrics 
                    WHERE recorded_at > NOW() - INTERVAL '5 minutes'
                """)
                recent_metrics = cursor.fetchone()['count']
                
                if recent_events > 0 or recent_metrics > 0:
                    self.log_test_result(
                        "Event Processing", 
                        True, 
                        f"Recent events: {recent_events}, metrics: {recent_metrics}"
                    )
                    return True
                else:
                    self.log_test_result(
                        "Event Processing", 
                        False, 
                        "No recent event processing activity detected"
                    )
                    return False
                    
        except Exception as e:
            self.log_test_result("Event Processing", False, str(e))
            return False
    
    def test_alert_generation(self) -> bool:
        """Test alert generation system"""
        try:
            with db.cursor() as cursor:
                # Get current alert count
                cursor.execute("SELECT COUNT(*) as count FROM alerts")
                initial_alerts = cursor.fetchone()['count']
                
                # Create a low stock condition to trigger alert
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = 0
                    WHERE item_id = (
                        SELECT item_id FROM inventory 
                        WHERE current_stock > safety_stock 
                        LIMIT 1
                    )
                """)
                
                # Wait for alert processing
                time.sleep(3)
                
                # Check for new alerts
                cursor.execute("""
                    SELECT COUNT(*) as count FROM alerts 
                    WHERE created_at > NOW() - INTERVAL '30 seconds'
                """)
                new_alerts = cursor.fetchone()['count']
                
                if new_alerts > 0:
                    self.log_test_result(
                        "Alert Generation", 
                        True, 
                        f"Generated {new_alerts} new alerts"
                    )
                    return True
                else:
                    # Check if alerts exist at all
                    cursor.execute("SELECT COUNT(*) as count FROM alerts")
                    total_alerts = cursor.fetchone()['count']
                    
                    if total_alerts > initial_alerts:
                        self.log_test_result(
                            "Alert Generation", 
                            True, 
                            f"Alert system working (total alerts: {total_alerts})"
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Alert Generation", 
                            False, 
                            "No alerts generated despite low stock condition"
                        )
                        return False
                        
        except Exception as e:
            self.log_test_result("Alert Generation", False, str(e))
            return False
    
    def test_data_simulation(self) -> bool:
        """Test data simulation activity"""
        try:
            with db.cursor() as cursor:
                # Check for recent inventory changes
                cursor.execute("""
                    SELECT COUNT(*) as count FROM inventory 
                    WHERE last_updated > NOW() - INTERVAL '10 minutes'
                """)
                recent_inventory_changes = cursor.fetchone()['count']
                
                # Check for recent consumption history
                cursor.execute("""
                    SELECT COUNT(*) as count FROM consumption_history 
                    WHERE consumption_date > NOW() - INTERVAL '10 minutes'
                """)
                recent_consumption = cursor.fetchone()['count']
                
                # Check for recent PO activity
                cursor.execute("""
                    SELECT COUNT(*) as count FROM purchase_orders 
                    WHERE created_date > NOW() - INTERVAL '10 minutes'
                       OR (status IN ('approved', 'shipped', 'received') 
                           AND created_date > NOW() - INTERVAL '1 hour')
                """)
                recent_po_activity = cursor.fetchone()['count']
                
                total_activity = recent_inventory_changes + recent_consumption + recent_po_activity
                
                if total_activity > 0:
                    self.log_test_result(
                        "Data Simulation", 
                        True, 
                        f"Inventory: {recent_inventory_changes}, Consumption: {recent_consumption}, POs: {recent_po_activity}"
                    )
                    return True
                else:
                    self.log_test_result(
                        "Data Simulation", 
                        False, 
                        "No recent simulation activity detected"
                    )
                    return False
                    
        except Exception as e:
            self.log_test_result("Data Simulation", False, str(e))
            return False
    
    def test_end_to_end_flow(self) -> bool:
        """Test complete end-to-end event flow"""
        try:
            with db.cursor() as cursor:
                # Record initial state
                cursor.execute("SELECT COUNT(*) as count FROM event_log")
                initial_events = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM system_metrics")
                initial_metrics = cursor.fetchone()['count']
                
                # Trigger a significant change
                cursor.execute("""
                    INSERT INTO consumption_history (item_id, quantity_consumed, consumption_reason, department)
                    SELECT item_id, 10, 'System Test', 'Testing'
                    FROM inventory 
                    WHERE current_stock > 10 
                    LIMIT 1
                """)
                
                # Update corresponding inventory
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = current_stock - 10,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = (
                        SELECT item_id FROM consumption_history 
                        WHERE consumption_reason = 'System Test' 
                        ORDER BY consumption_date DESC 
                        LIMIT 1
                    )
                """)
                
                # Wait for processing
                time.sleep(5)
                
                # Check for event processing
                cursor.execute("""
                    SELECT COUNT(*) as count FROM event_log 
                    WHERE processed_at > NOW() - INTERVAL '30 seconds'
                """)
                new_events = cursor.fetchone()['count']
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM system_metrics 
                    WHERE recorded_at > NOW() - INTERVAL '30 seconds'
                """)
                new_metrics = cursor.fetchone()['count']
                
                if new_events > 0 and new_metrics > 0:
                    self.log_test_result(
                        "End-to-End Flow", 
                        True, 
                        f"Events: {new_events}, Metrics: {new_metrics}"
                    )
                    return True
                else:
                    self.log_test_result(
                        "End-to-End Flow", 
                        False, 
                        f"Incomplete processing - Events: {new_events}, Metrics: {new_metrics}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test_result("End-to-End Flow", False, str(e))
            return False
    
    def test_system_performance(self) -> bool:
        """Test system performance metrics"""
        try:
            with db.cursor() as cursor:
                # Check processing times
                cursor.execute("""
                    SELECT AVG(processing_duration_ms) as avg_time,
                           MAX(processing_duration_ms) as max_time,
                           COUNT(*) as event_count
                    FROM event_log 
                    WHERE processed_at > NOW() - INTERVAL '1 hour'
                      AND processing_duration_ms IS NOT NULL
                """)
                perf_data = cursor.fetchone()
                
                if perf_data and perf_data['event_count'] > 0:
                    avg_time = float(perf_data['avg_time']) if perf_data['avg_time'] else 0
                    max_time = perf_data['max_time'] or 0
                    event_count = perf_data['event_count']
                    
                    # Performance thresholds for t2.micro
                    avg_threshold = 1000  # 1 second average
                    max_threshold = 5000  # 5 second max
                    
                    performance_ok = avg_time < avg_threshold and max_time < max_threshold
                    
                    self.log_test_result(
                        "System Performance", 
                        performance_ok, 
                        f"Avg: {avg_time:.1f}ms, Max: {max_time}ms, Events: {event_count}"
                    )
                    return performance_ok
                else:
                    self.log_test_result(
                        "System Performance", 
                        False, 
                        "No performance data available"
                    )
                    return False
                    
        except Exception as e:
            self.log_test_result("System Performance", False, str(e))
            return False
    
    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print("=== Procurement Lighthouse System Validation ===\n")
        
        tests = [
            self.test_database_connection,
            self.test_database_triggers,
            self.test_event_processing,
            self.test_alert_generation,
            self.test_data_simulation,
            self.test_end_to_end_flow,
            self.test_system_performance
        ]
        
        all_passed = True
        
        for test in tests:
            try:
                result = test()
                if not result:
                    all_passed = False
            except Exception as e:
                self.logger.error(f"Test execution error: {e}")
                all_passed = False
            
            print()  # Add spacing between tests
        
        return all_passed
    
    def print_summary(self):
        """Print validation summary"""
        print("=== Validation Summary ===")
        
        passed_count = sum(1 for _, passed, _ in self.test_results if passed)
        total_count = len(self.test_results)
        
        print(f"Tests Passed: {passed_count}/{total_count}")
        
        if passed_count == total_count:
            print("🎉 All tests passed! Core event system is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the issues above.")
            print("\nFailed tests:")
            for test_name, passed, message in self.test_results:
                if not passed:
                    print(f"  - {test_name}: {message}")
        
        print("\nNext steps:")
        if passed_count == total_count:
            print("✅ System is ready for alert management implementation (Task 5)")
        else:
            print("🔧 Fix the failing tests before proceeding")
            print("💡 Ensure both services are running:")
            print("   Terminal 1: python3 -m procurement_lighthouse.main events")
            print("   Terminal 2: python3 -m procurement_lighthouse.main simulate")


def main():
    """Main validation entry point"""
    validator = SystemValidator()
    
    print("This validation requires both services to be running:")
    print("Terminal 1: python3 -m procurement_lighthouse.main events")
    print("Terminal 2: python3 -m procurement_lighthouse.main simulate")
    print()
    
    response = input("Are both services running? (y/n): ").lower().strip()
    if response != 'y':
        print("Please start both services and run validation again.")
        sys.exit(1)
    
    print("Starting validation...\n")
    
    all_passed = validator.run_all_tests()
    validator.print_summary()
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()