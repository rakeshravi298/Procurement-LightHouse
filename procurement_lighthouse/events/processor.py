"""
Event processor with lightweight KPI calculations and alert generation
Optimized for t2.micro memory constraints
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..database.connection import db
from ..config import config
from ..utils import calculate_stock_status, validate_positive_integer

logger = logging.getLogger(__name__)

class EventProcessor:
    """Lightweight event processor for t2.micro"""
    
    def __init__(self):
        self.processing_stats = {
            'events_processed': 0,
            'processing_errors': 0,
            'last_processed': None
        }
    
    def process_inventory_event(self, channel: str, event_data: dict):
        """Process inventory change events with KPI updates and alert generation"""
        start_time = time.time()
        
        try:
            item_id = event_data.get('item_id')
            old_quantity = event_data.get('old_quantity', 0)
            new_quantity = event_data.get('new_quantity', 0)
            change_type = event_data.get('change_type')
            
            if not item_id:
                logger.warning("Inventory event missing item_id")
                return
            
            logger.info(f"Processing inventory event: Item {item_id}, {old_quantity} -> {new_quantity}")
            
            # Get current inventory details
            inventory_info = self._get_inventory_info(item_id)
            if not inventory_info:
                logger.warning(f"Inventory item {item_id} not found")
                return
            
            # Update KPIs
            self._update_inventory_kpis(item_id, old_quantity, new_quantity, change_type)
            
            # Check for alerts
            self._check_inventory_alerts(inventory_info)
            
            # Trigger ML inference if significant change
            if abs(new_quantity - old_quantity) > 10:  # Threshold for ML trigger
                self._trigger_ml_inference(item_id, 'consumption_forecast')
            
            self._record_processing_time(start_time, 'inventory_changed')
            
        except Exception as e:
            logger.error(f"Error processing inventory event: {e}")
            self.processing_stats['processing_errors'] += 1
    
    def process_po_event(self, channel: str, event_data: dict):
        """Process purchase order events with status tracking"""
        start_time = time.time()
        
        try:
            po_id = event_data.get('po_id')
            old_status = event_data.get('old_status', '')
            new_status = event_data.get('new_status', '')
            change_type = event_data.get('change_type')
            
            if not po_id:
                logger.warning("PO event missing po_id")
                return
            
            logger.info(f"Processing PO event: PO {po_id}, {old_status} -> {new_status}")
            
            # Get PO details
            po_info = self._get_po_info(po_id)
            if not po_info:
                logger.warning(f"Purchase order {po_id} not found")
                return
            
            # Update PO KPIs
            self._update_po_kpis(po_id, old_status, new_status)
            
            # Check for delivery alerts
            self._check_po_alerts(po_info)
            
            # If PO is received, update inventory
            if new_status == 'received':
                self._process_po_receipt(po_id)
            
            self._record_processing_time(start_time, 'po_status_changed')
            
        except Exception as e:
            logger.error(f"Error processing PO event: {e}")
            self.processing_stats['processing_errors'] += 1
    
    def process_alert_event(self, channel: str, event_data: dict):
        """Process alert generation events"""
        start_time = time.time()
        
        try:
            alert_id = event_data.get('alert_id')
            alert_type = event_data.get('alert_type')
            severity = event_data.get('severity')
            
            if not alert_id:
                logger.warning("Alert event missing alert_id")
                return
            
            logger.info(f"Processing alert event: Alert {alert_id}, {alert_type} ({severity})")
            
            # Update alert metrics
            self._update_alert_metrics(alert_type, severity)
            
            # Log high-severity alerts
            if severity in ['high', 'critical']:
                logger.warning(f"High-severity alert generated: {alert_type} (ID: {alert_id})")
            
            self._record_processing_time(start_time, 'alert_generated')
            
        except Exception as e:
            logger.error(f"Error processing alert event: {e}")
            self.processing_stats['processing_errors'] += 1
    
    def process_forecast_event(self, channel: str, event_data: dict):
        """Process forecast update events"""
        start_time = time.time()
        
        try:
            forecast_id = event_data.get('forecast_id')
            item_id = event_data.get('item_id')
            predicted_consumption = event_data.get('predicted_consumption')
            
            if not forecast_id:
                logger.warning("Forecast event missing forecast_id")
                return
            
            logger.info(f"Processing forecast event: Forecast {forecast_id} for item {item_id}")
            
            # Update forecast metrics
            self._update_forecast_metrics(item_id, predicted_consumption)
            
            # Check if forecast indicates potential stockout
            if predicted_consumption:
                self._check_forecast_alerts(item_id, predicted_consumption)
            
            self._record_processing_time(start_time, 'forecast_updated')
            
        except Exception as e:
            logger.error(f"Error processing forecast event: {e}")
            self.processing_stats['processing_errors'] += 1
    
    def _get_inventory_info(self, item_id: int) -> Optional[dict]:
        """Get inventory information for item"""
        try:
            query = """
                SELECT item_id, item_name, current_stock, safety_stock, 
                       unit_cost, location, last_updated
                FROM inventory 
                WHERE item_id = %s
            """
            results = db.execute_query(query, (item_id,))
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting inventory info for {item_id}: {e}")
            return None
    
    def _get_po_info(self, po_id: int) -> Optional[dict]:
        """Get purchase order information"""
        try:
            query = """
                SELECT po_id, supplier_name, status, created_date, 
                       expected_delivery, total_value
                FROM purchase_orders 
                WHERE po_id = %s
            """
            results = db.execute_query(query, (po_id,))
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting PO info for {po_id}: {e}")
            return None
    
    def _update_inventory_kpis(self, item_id: int, old_quantity: int, new_quantity: int, change_type: str):
        """Update inventory-related KPIs (lightweight for t2.micro)"""
        try:
            # Calculate simple metrics
            quantity_change = new_quantity - old_quantity
            
            # Record system metrics
            metrics_to_record = [
                ('inventory_quantity_change', quantity_change),
                ('inventory_events_processed', 1)
            ]
            
            if change_type == 'UPDATE':
                if quantity_change > 0:
                    metrics_to_record.append(('inventory_receipts', quantity_change))
                elif quantity_change < 0:
                    metrics_to_record.append(('inventory_consumption', abs(quantity_change)))
            
            self._record_metrics(metrics_to_record)
            
        except Exception as e:
            logger.error(f"Error updating inventory KPIs: {e}")
    
    def _update_po_kpis(self, po_id: int, old_status: str, new_status: str):
        """Update purchase order KPIs"""
        try:
            # Record PO status change metrics
            metrics_to_record = [
                ('po_status_changes', 1),
                (f'po_status_{new_status}', 1)
            ]
            
            # Track delivery performance
            if new_status == 'received':
                metrics_to_record.append(('po_deliveries_completed', 1))
            elif new_status == 'shipped':
                metrics_to_record.append(('po_shipments', 1))
            
            self._record_metrics(metrics_to_record)
            
        except Exception as e:
            logger.error(f"Error updating PO KPIs: {e}")
    
    def _update_alert_metrics(self, alert_type: str, severity: str):
        """Update alert-related metrics"""
        try:
            metrics_to_record = [
                ('alerts_generated', 1),
                (f'alerts_{severity}', 1),
                (f'alerts_{alert_type}', 1)
            ]
            
            self._record_metrics(metrics_to_record)
            
        except Exception as e:
            logger.error(f"Error updating alert metrics: {e}")
    
    def _update_forecast_metrics(self, item_id: int, predicted_consumption: int):
        """Update forecast-related metrics"""
        try:
            metrics_to_record = [
                ('forecasts_generated', 1),
                ('forecast_total_consumption', predicted_consumption or 0)
            ]
            
            self._record_metrics(metrics_to_record)
            
        except Exception as e:
            logger.error(f"Error updating forecast metrics: {e}")
    
    def _record_metrics(self, metrics: list):
        """Record multiple metrics efficiently"""
        try:
            current_time = datetime.now()
            
            for metric_name, metric_value in metrics:
                db.execute_command("""
                    INSERT INTO system_metrics (metric_name, metric_value, recorded_at)
                    VALUES (%s, %s, %s)
                """, (metric_name, metric_value, current_time))
            
        except Exception as e:
            logger.error(f"Error recording metrics: {e}")
    
    def _check_inventory_alerts(self, inventory_info: dict):
        """Check for inventory-related alerts using alert service"""
        try:
            from ..alerts.service import alert_service
            
            item_id = inventory_info['item_id']
            current_stock = inventory_info['current_stock']
            
            # Process alerts through alert service
            alerts_generated = alert_service.process_inventory_alert(item_id, current_stock)
            
            if alerts_generated > 0:
                logger.info(f"Generated {alerts_generated} inventory alerts for item {item_id}")
            
        except Exception as e:
            logger.error(f"Error checking inventory alerts: {e}")
    
    def _check_po_alerts(self, po_info: dict):
        """Check for purchase order alerts using alert service"""
        try:
            from ..alerts.service import alert_service
            
            po_id = po_info['po_id']
            
            # Process alerts through alert service
            alerts_generated = alert_service.process_delivery_alert(po_id)
            
            if alerts_generated > 0:
                logger.info(f"Generated {alerts_generated} delivery alerts for PO {po_id}")
            
        except Exception as e:
            logger.error(f"Error checking PO alerts: {e}")
    
    def _check_forecast_alerts(self, item_id: int, predicted_consumption: int):
        """Check for forecast-related alerts using alert service"""
        try:
            from ..alerts.service import alert_service
            
            # Get recent actual consumption for comparison
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(quantity_consumed) as total_consumed
                    FROM consumption_history 
                    WHERE item_id = %s 
                      AND consumption_date > NOW() - INTERVAL '7 days'
                """, (item_id,))
                
                result = cursor.fetchone()
                actual_consumption = result['total_consumed'] or 0
            
            # Process demand spike alerts
            if actual_consumption > 0:
                alerts_generated = alert_service.process_demand_spike_alert(
                    item_id, actual_consumption, predicted_consumption
                )
                
                if alerts_generated > 0:
                    logger.info(f"Generated {alerts_generated} demand spike alerts for item {item_id}")
            
        except Exception as e:
            logger.error(f"Error checking forecast alerts: {e}")
    
    def _trigger_ml_inference(self, item_id: int, model_type: str):
        """Trigger ML inference using ML service"""
        try:
            from ..ml.service import ml_service
            
            logger.info(f"ML inference triggered: {model_type} for item {item_id}")
            
            if model_type == 'consumption_forecast':
                # Get current and old stock for ML service
                inventory_info = self._get_inventory_info(item_id)
                if inventory_info:
                    current_stock = inventory_info['current_stock']
                    old_stock = current_stock - 10  # Approximate old stock
                    
                    # Trigger ML inference through service
                    result = ml_service.handle_inventory_change_event(
                        item_id, old_stock, current_stock
                    )
                    
                    if result.get('triggered'):
                        logger.info(f"ML inference completed for item {item_id}: {len(result.get('results', {}))} predictions")
            
        except Exception as e:
            logger.error(f"Error triggering ML inference: {e}")
    
    def _process_po_receipt(self, po_id: int):
        """Process PO receipt and update inventory"""
        try:
            # Get PO line items
            query = """
                SELECT pli.item_id, pli.quantity_ordered, i.current_stock
                FROM po_line_items pli
                JOIN inventory i ON pli.item_id = i.item_id
                WHERE pli.po_id = %s
            """
            
            line_items = db.execute_query(query, (po_id,))
            
            for item in line_items:
                item_id = item['item_id']
                quantity_ordered = item['quantity_ordered']
                current_stock = item['current_stock']
                
                # Update inventory
                new_stock = current_stock + quantity_ordered
                db.execute_command("""
                    UPDATE inventory 
                    SET current_stock = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = %s
                """, (new_stock, item_id))
                
                # Update PO line item
                db.execute_command("""
                    UPDATE po_line_items 
                    SET quantity_received = %s
                    WHERE po_id = %s AND item_id = %s
                """, (quantity_ordered, po_id, item_id))
            
            logger.info(f"Processed PO receipt: {po_id}")
            
        except Exception as e:
            logger.error(f"Error processing PO receipt: {e}")
    
    def _run_alert_maintenance(self):
        """Run periodic alert maintenance"""
        try:
            from ..alerts.service import alert_service
            
            # Run maintenance every 100 processed events
            if self.processing_stats['events_processed'] % 100 == 0:
                maintenance_results = alert_service.run_maintenance()
                logger.info(f"Alert maintenance completed: {maintenance_results}")
            
        except Exception as e:
            logger.error(f"Error running alert maintenance: {e}")
    
    def _record_processing_time(self, start_time: float, event_type: str):
        """Record event processing time for monitoring"""
        try:
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update processing stats
            self.processing_stats['events_processed'] += 1
            self.processing_stats['last_processed'] = datetime.now()
            
            # Record processing time metric
            self._record_metrics([
                (f'processing_time_{event_type}_ms', processing_time_ms),
                ('events_processed_total', 1)
            ])
            
            # Run periodic alert maintenance
            self._run_alert_maintenance()
            
            logger.debug(f"Event {event_type} processed in {processing_time_ms}ms")
            
        except Exception as e:
            logger.error(f"Error recording processing time: {e}")
    
    def get_processing_stats(self) -> dict:
        """Get current processing statistics"""
        return self.processing_stats.copy()


# Global event processor instance
event_processor = EventProcessor()