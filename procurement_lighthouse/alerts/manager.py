"""
Alert management system with threshold-based alerts
Optimized for t2.micro with minimal processing overhead
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from ..database.connection import db
from ..config import config

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Alert types"""
    STOCK_LOW = "stock_low"
    STOCK_OUT = "stock_out"
    DELIVERY_OVERDUE = "delivery_overdue"
    DEMAND_SPIKE = "demand_spike"
    FORECAST_DEVIATION = "forecast_deviation"
    SYSTEM_ERROR = "system_error"

class AlertManager:
    """Lightweight alert management system for t2.micro"""
    
    def __init__(self):
        self.alert_thresholds = {
            # Stock-related thresholds
            'stock_critical_ratio': 0.0,    # 0% of safety stock = critical
            'stock_low_ratio': 1.0,         # 100% of safety stock = low
            'stock_medium_ratio': 1.5,      # 150% of safety stock = medium warning
            
            # Delivery thresholds (days)
            'delivery_overdue_medium': 1,   # 1 day overdue = medium
            'delivery_overdue_high': 7,     # 7 days overdue = high
            
            # Demand spike thresholds
            'demand_spike_ratio': 2.0,      # 200% of forecast = spike
            'forecast_deviation_ratio': 1.5, # 150% deviation = alert
        }
        
        # Deduplication settings (minutes)
        self.dedup_windows = {
            AlertType.STOCK_LOW: 60,        # 1 hour
            AlertType.STOCK_OUT: 30,        # 30 minutes
            AlertType.DELIVERY_OVERDUE: 240, # 4 hours
            AlertType.DEMAND_SPIKE: 120,    # 2 hours
            AlertType.FORECAST_DEVIATION: 180, # 3 hours
            AlertType.SYSTEM_ERROR: 15,     # 15 minutes
        }
    
    def check_inventory_alerts(self, item_id: int, current_stock: int, 
                             safety_stock: int, item_name: str) -> List[Dict]:
        """Check for inventory-related alerts"""
        alerts_generated = []
        
        try:
            # Calculate stock ratio
            if safety_stock > 0:
                stock_ratio = current_stock / safety_stock
            else:
                stock_ratio = float('inf') if current_stock > 0 else 0
            
            # Critical: Out of stock
            if current_stock <= 0:
                alert = self._create_alert(
                    alert_type=AlertType.STOCK_OUT,
                    severity=AlertSeverity.CRITICAL,
                    item_id=item_id,
                    message=f"{item_name}: Out of stock (0 units available)",
                    metadata={'current_stock': current_stock, 'safety_stock': safety_stock}
                )
                if alert:
                    alerts_generated.append(alert)
            
            # High: Below safety stock
            elif stock_ratio <= self.alert_thresholds['stock_low_ratio']:
                severity = AlertSeverity.HIGH if stock_ratio <= self.alert_thresholds['stock_critical_ratio'] else AlertSeverity.MEDIUM
                
                alert = self._create_alert(
                    alert_type=AlertType.STOCK_LOW,
                    severity=severity,
                    item_id=item_id,
                    message=f"{item_name}: Low stock ({current_stock} units, safety stock: {safety_stock})",
                    metadata={'current_stock': current_stock, 'safety_stock': safety_stock, 'ratio': stock_ratio}
                )
                if alert:
                    alerts_generated.append(alert)
            
            return alerts_generated
            
        except Exception as e:
            logger.error(f"Error checking inventory alerts for item {item_id}: {e}")
            return []
    
    def check_delivery_alerts(self, po_id: int, supplier_name: str, 
                            expected_delivery: datetime, status: str) -> List[Dict]:
        """Check for delivery-related alerts"""
        alerts_generated = []
        
        try:
            # Only check for active POs
            if status in ['received', 'cancelled']:
                return alerts_generated
            
            # Calculate days overdue
            if expected_delivery:
                days_overdue = (datetime.now().date() - expected_delivery).days
                
                if days_overdue > 0:
                    # Determine severity based on days overdue
                    if days_overdue >= self.alert_thresholds['delivery_overdue_high']:
                        severity = AlertSeverity.HIGH
                    elif days_overdue >= self.alert_thresholds['delivery_overdue_medium']:
                        severity = AlertSeverity.MEDIUM
                    else:
                        return alerts_generated  # Less than 1 day, no alert
                    
                    alert = self._create_alert(
                        alert_type=AlertType.DELIVERY_OVERDUE,
                        severity=severity,
                        po_id=po_id,
                        message=f"PO from {supplier_name}: Delivery overdue by {days_overdue} days (expected: {expected_delivery})",
                        metadata={'days_overdue': days_overdue, 'expected_delivery': expected_delivery.isoformat(), 'status': status}
                    )
                    if alert:
                        alerts_generated.append(alert)
            
            return alerts_generated
            
        except Exception as e:
            logger.error(f"Error checking delivery alerts for PO {po_id}: {e}")
            return []
    
    def check_demand_spike_alerts(self, item_id: int, item_name: str, 
                                actual_consumption: int, predicted_consumption: int) -> List[Dict]:
        """Check for demand spike alerts"""
        alerts_generated = []
        
        try:
            if predicted_consumption <= 0:
                return alerts_generated
            
            # Calculate consumption ratio
            consumption_ratio = actual_consumption / predicted_consumption
            
            # Check for demand spike
            if consumption_ratio >= self.alert_thresholds['demand_spike_ratio']:
                severity = AlertSeverity.HIGH if consumption_ratio >= 3.0 else AlertSeverity.MEDIUM
                
                alert = self._create_alert(
                    alert_type=AlertType.DEMAND_SPIKE,
                    severity=severity,
                    item_id=item_id,
                    message=f"{item_name}: Demand spike detected (actual: {actual_consumption}, predicted: {predicted_consumption}, ratio: {consumption_ratio:.1f}x)",
                    metadata={'actual_consumption': actual_consumption, 'predicted_consumption': predicted_consumption, 'ratio': consumption_ratio}
                )
                if alert:
                    alerts_generated.append(alert)
            
            return alerts_generated
            
        except Exception as e:
            logger.error(f"Error checking demand spike alerts for item {item_id}: {e}")
            return []
    
    def check_forecast_deviation_alerts(self, item_id: int, item_name: str, 
                                      forecast_accuracy: float) -> List[Dict]:
        """Check for forecast deviation alerts"""
        alerts_generated = []
        
        try:
            # Check if forecast accuracy is below threshold
            if forecast_accuracy < (1.0 / self.alert_thresholds['forecast_deviation_ratio']):
                severity = AlertSeverity.MEDIUM if forecast_accuracy < 0.5 else AlertSeverity.LOW
                
                alert = self._create_alert(
                    alert_type=AlertType.FORECAST_DEVIATION,
                    severity=severity,
                    item_id=item_id,
                    message=f"{item_name}: Poor forecast accuracy ({forecast_accuracy:.1%})",
                    metadata={'forecast_accuracy': forecast_accuracy}
                )
                if alert:
                    alerts_generated.append(alert)
            
            return alerts_generated
            
        except Exception as e:
            logger.error(f"Error checking forecast deviation alerts for item {item_id}: {e}")
            return []
    
    def _create_alert(self, alert_type: AlertType, severity: AlertSeverity, 
                     message: str, item_id: int = None, po_id: int = None, 
                     metadata: Dict = None) -> Optional[Dict]:
        """Create alert with deduplication"""
        try:
            # Check for duplicate alerts
            if self._is_duplicate_alert(alert_type, item_id, po_id):
                logger.debug(f"Duplicate alert suppressed: {alert_type.value}")
                return None
            
            # Create alert record
            alert_data = {
                'alert_type': alert_type.value,
                'severity': severity.value,
                'item_id': item_id,
                'po_id': po_id,
                'message': message,
                'metadata': metadata or {}
            }
            
            # Insert into database
            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO alerts (alert_type, severity, item_id, po_id, message)
                    VALUES (%(alert_type)s, %(severity)s, %(item_id)s, %(po_id)s, %(message)s)
                    RETURNING alert_id, created_at
                """, alert_data)
                
                result = cursor.fetchone()
                alert_data.update({
                    'alert_id': result['alert_id'],
                    'created_at': result['created_at'],
                    'status': 'active'
                })
            
            logger.info(f"Alert created: {alert_type.value} ({severity.value}) - {message}")
            return alert_data
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None
    
    def _is_duplicate_alert(self, alert_type: AlertType, item_id: int = None, 
                          po_id: int = None) -> bool:
        """Check if alert is duplicate within deduplication window"""
        try:
            dedup_minutes = self.dedup_windows.get(alert_type, 60)
            cutoff_time = datetime.now() - timedelta(minutes=dedup_minutes)
            
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM alerts 
                    WHERE alert_type = %s 
                      AND status = 'active'
                      AND created_at > %s
                      AND (item_id = %s OR item_id IS NULL)
                      AND (po_id = %s OR po_id IS NULL)
                """, (alert_type.value, cutoff_time, item_id, po_id))
                
                result = cursor.fetchone()
                return result['count'] > 0
                
        except Exception as e:
            logger.error(f"Error checking duplicate alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: int, resolution_note: str = None) -> bool:
        """Resolve an active alert"""
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE alerts 
                    SET status = 'resolved', 
                        resolved_at = CURRENT_TIMESTAMP
                    WHERE alert_id = %s AND status = 'active'
                """, (alert_id,))
                
                if cursor.rowcount > 0:
                    logger.info(f"Alert {alert_id} resolved")
                    return True
                else:
                    logger.warning(f"Alert {alert_id} not found or already resolved")
                    return False
                    
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            return False
    
    def get_active_alerts(self, limit: int = 50) -> List[Dict]:
        """Get active alerts ordered by severity and creation time"""
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT a.alert_id, a.alert_type, a.severity, a.message, 
                           a.created_at, a.item_id, a.po_id,
                           i.item_name, po.supplier_name
                    FROM alerts a
                    LEFT JOIN inventory i ON a.item_id = i.item_id
                    LEFT JOIN purchase_orders po ON a.po_id = po.po_id
                    WHERE a.status = 'active'
                    ORDER BY 
                        CASE a.severity 
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        a.created_at DESC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    def get_alert_summary(self) -> Dict:
        """Get alert summary statistics"""
        try:
            with db.cursor() as cursor:
                # Active alerts by severity
                cursor.execute("""
                    SELECT severity, COUNT(*) as count
                    FROM alerts 
                    WHERE status = 'active'
                    GROUP BY severity
                """)
                severity_counts = {row['severity']: row['count'] for row in cursor.fetchall()}
                
                # Active alerts by type
                cursor.execute("""
                    SELECT alert_type, COUNT(*) as count
                    FROM alerts 
                    WHERE status = 'active'
                    GROUP BY alert_type
                """)
                type_counts = {row['alert_type']: row['count'] for row in cursor.fetchall()}
                
                # Recent activity
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM alerts 
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                recent_count = cursor.fetchone()['count']
                
                return {
                    'active_by_severity': severity_counts,
                    'active_by_type': type_counts,
                    'recent_alerts_1h': recent_count,
                    'total_active': sum(severity_counts.values())
                }
                
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def cleanup_old_alerts(self, days_old: int = 30) -> int:
        """Clean up old resolved alerts to save space"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with db.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM alerts 
                    WHERE status = 'resolved' 
                      AND resolved_at < %s
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} old alerts")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
            return 0


# Global alert manager instance
alert_manager = AlertManager()