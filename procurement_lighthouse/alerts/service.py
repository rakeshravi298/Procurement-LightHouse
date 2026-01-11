"""
Alert service for automated alert processing
Integrates with event processing system
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from .manager import alert_manager, AlertType, AlertSeverity
from ..database.connection import db

logger = logging.getLogger(__name__)

class AlertService:
    """Lightweight alert service for t2.micro"""
    
    def __init__(self):
        self.processing_stats = {
            'alerts_processed': 0,
            'alerts_generated': 0,
            'alerts_resolved': 0,
            'last_cleanup': None
        }
    
    def process_inventory_alert(self, item_id: int, current_stock: int, 
                              old_stock: int = None) -> int:
        """Process inventory-related alerts"""
        try:
            # Get inventory details
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT item_name, safety_stock, location
                    FROM inventory 
                    WHERE item_id = %s
                """, (item_id,))
                
                item_info = cursor.fetchone()
                if not item_info:
                    logger.warning(f"Item {item_id} not found for alert processing")
                    return 0
            
            # Check for alerts
            alerts = alert_manager.check_inventory_alerts(
                item_id=item_id,
                current_stock=current_stock,
                safety_stock=item_info['safety_stock'],
                item_name=item_info['item_name']
            )
            
            # Update stats
            self.processing_stats['alerts_generated'] += len(alerts)
            self.processing_stats['alerts_processed'] += 1
            
            if alerts:
                logger.info(f"Generated {len(alerts)} inventory alerts for item {item_id}")
            
            return len(alerts)
            
        except Exception as e:
            logger.error(f"Error processing inventory alert for item {item_id}: {e}")
            return 0
    
    def process_delivery_alert(self, po_id: int) -> int:
        """Process delivery-related alerts"""
        try:
            # Get PO details
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT supplier_name, status, expected_delivery, created_date
                    FROM purchase_orders 
                    WHERE po_id = %s
                """, (po_id,))
                
                po_info = cursor.fetchone()
                if not po_info:
                    logger.warning(f"PO {po_id} not found for alert processing")
                    return 0
            
            # Check for alerts
            alerts = alert_manager.check_delivery_alerts(
                po_id=po_id,
                supplier_name=po_info['supplier_name'],
                expected_delivery=po_info['expected_delivery'],
                status=po_info['status']
            )
            
            # Update stats
            self.processing_stats['alerts_generated'] += len(alerts)
            self.processing_stats['alerts_processed'] += 1
            
            if alerts:
                logger.info(f"Generated {len(alerts)} delivery alerts for PO {po_id}")
            
            return len(alerts)
            
        except Exception as e:
            logger.error(f"Error processing delivery alert for PO {po_id}: {e}")
            return 0
    
    def process_demand_spike_alert(self, item_id: int, actual_consumption: int, 
                                 predicted_consumption: int = None) -> int:
        """Process demand spike alerts"""
        try:
            # Get item details
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT item_name FROM inventory WHERE item_id = %s
                """, (item_id,))
                
                item_info = cursor.fetchone()
                if not item_info:
                    logger.warning(f"Item {item_id} not found for demand spike alert")
                    return 0
                
                # Get recent forecast if not provided
                if predicted_consumption is None:
                    cursor.execute("""
                        SELECT predicted_consumption
                        FROM forecasts 
                        WHERE item_id = %s 
                          AND forecast_date >= CURRENT_DATE
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (item_id,))
                    
                    forecast = cursor.fetchone()
                    predicted_consumption = forecast['predicted_consumption'] if forecast else 0
            
            if predicted_consumption <= 0:
                return 0  # No forecast available
            
            # Check for demand spike alerts
            alerts = alert_manager.check_demand_spike_alerts(
                item_id=item_id,
                item_name=item_info['item_name'],
                actual_consumption=actual_consumption,
                predicted_consumption=predicted_consumption
            )
            
            # Update stats
            self.processing_stats['alerts_generated'] += len(alerts)
            self.processing_stats['alerts_processed'] += 1
            
            if alerts:
                logger.info(f"Generated {len(alerts)} demand spike alerts for item {item_id}")
            
            return len(alerts)
            
        except Exception as e:
            logger.error(f"Error processing demand spike alert for item {item_id}: {e}")
            return 0
    
    def auto_resolve_alerts(self) -> int:
        """Automatically resolve alerts that are no longer valid"""
        resolved_count = 0
        
        try:
            # Get active stock alerts
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT a.alert_id, a.item_id, a.alert_type, i.current_stock, i.safety_stock
                    FROM alerts a
                    JOIN inventory i ON a.item_id = i.item_id
                    WHERE a.status = 'active' 
                      AND a.alert_type IN ('stock_low', 'stock_out')
                """)
                
                stock_alerts = cursor.fetchall()
                
                for alert in stock_alerts:
                    should_resolve = False
                    
                    # Resolve stock_out alerts if stock is restored
                    if alert['alert_type'] == 'stock_out' and alert['current_stock'] > 0:
                        should_resolve = True
                    
                    # Resolve stock_low alerts if stock is above safety level
                    elif (alert['alert_type'] == 'stock_low' and 
                          alert['current_stock'] > alert['safety_stock'] * 1.2):  # 20% buffer
                        should_resolve = True
                    
                    if should_resolve:
                        if alert_manager.resolve_alert(alert['alert_id'], "Auto-resolved: condition improved"):
                            resolved_count += 1
                
                # Auto-resolve delivery alerts for received POs
                cursor.execute("""
                    SELECT a.alert_id
                    FROM alerts a
                    JOIN purchase_orders po ON a.po_id = po.po_id
                    WHERE a.status = 'active' 
                      AND a.alert_type = 'delivery_overdue'
                      AND po.status = 'received'
                """)
                
                delivery_alerts = cursor.fetchall()
                
                for alert in delivery_alerts:
                    if alert_manager.resolve_alert(alert['alert_id'], "Auto-resolved: PO received"):
                        resolved_count += 1
            
            # Update stats
            self.processing_stats['alerts_resolved'] += resolved_count
            
            if resolved_count > 0:
                logger.info(f"Auto-resolved {resolved_count} alerts")
            
            return resolved_count
            
        except Exception as e:
            logger.error(f"Error auto-resolving alerts: {e}")
            return 0
    
    def run_maintenance(self) -> Dict[str, int]:
        """Run alert system maintenance tasks"""
        maintenance_results = {
            'alerts_resolved': 0,
            'alerts_cleaned': 0
        }
        
        try:
            # Auto-resolve alerts
            maintenance_results['alerts_resolved'] = self.auto_resolve_alerts()
            
            # Clean up old alerts (run once per day)
            if (not self.processing_stats['last_cleanup'] or 
                datetime.now() - self.processing_stats['last_cleanup'] > timedelta(hours=24)):
                
                maintenance_results['alerts_cleaned'] = alert_manager.cleanup_old_alerts(days_old=7)
                self.processing_stats['last_cleanup'] = datetime.now()
            
            logger.info(f"Alert maintenance completed: {maintenance_results}")
            return maintenance_results
            
        except Exception as e:
            logger.error(f"Error running alert maintenance: {e}")
            return maintenance_results
    
    def get_alert_dashboard_data(self) -> Dict[str, Any]:
        """Get alert data for dashboard display"""
        try:
            # Get alert summary
            summary = alert_manager.get_alert_summary()
            
            # Get recent active alerts
            active_alerts = alert_manager.get_active_alerts(limit=20)
            
            # Format for dashboard
            dashboard_data = {
                'summary': summary,
                'active_alerts': active_alerts,
                'processing_stats': self.processing_stats.copy(),
                'last_updated': datetime.now().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting alert dashboard data: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get alert service status"""
        try:
            summary = alert_manager.get_alert_summary()
            
            return {
                'service_running': True,
                'processing_stats': self.processing_stats,
                'alert_summary': summary,
                'last_maintenance': self.processing_stats['last_cleanup'].isoformat() if self.processing_stats['last_cleanup'] else None
            }
            
        except Exception as e:
            logger.error(f"Error getting alert service status: {e}")
            return {'service_running': False, 'error': str(e)}


# Global alert service instance
alert_service = AlertService()