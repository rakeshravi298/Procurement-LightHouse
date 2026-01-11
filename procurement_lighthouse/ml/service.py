"""
ML service for event-triggered inference
Integrates ML predictions with the event processing system
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .inference import ml_inference
from .model_manager import model_manager
from ..database.connection import db

logger = logging.getLogger(__name__)

class MLService:
    """ML service for event-driven predictions"""
    
    def __init__(self):
        self.service_stats = {
            'inference_requests': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'last_batch_run': None,
            'models_validated': False
        }
        
        # Event-triggered inference settings
        self.inference_triggers = {
            'inventory_change_threshold': 10,  # Trigger ML if stock changes by 10+ units
            'batch_inference_interval': 3600,  # Run batch inference every hour
            'risk_assessment_interval': 1800,  # Risk assessment every 30 minutes
        }
    
    def handle_inventory_change_event(self, item_id: int, old_quantity: int, new_quantity: int) -> Dict[str, Any]:
        """Handle inventory change events and trigger ML inference if needed"""
        try:
            quantity_change = abs(new_quantity - old_quantity)
            
            # Only trigger ML for significant changes
            if quantity_change < self.inference_triggers['inventory_change_threshold']:
                return {'triggered': False, 'reason': 'change_too_small'}
            
            logger.info(f"Triggering ML inference for item {item_id} (change: {quantity_change} units)")
            
            results = {}
            
            # Trigger consumption forecast
            consumption_result = ml_inference.predict_consumption(item_id, forecast_days=7)
            if consumption_result:
                results['consumption_forecast'] = consumption_result
                self.service_stats['successful_predictions'] += 1
            else:
                self.service_stats['failed_predictions'] += 1
            
            # Trigger stockout risk assessment
            risk_result = ml_inference.predict_stockout_risk(item_id)
            if risk_result:
                results['stockout_risk'] = risk_result
                self.service_stats['successful_predictions'] += 1
                
                # Generate alert if high risk
                if risk_result['risk_level'] in ['high', 'critical']:
                    self._generate_ml_alert(item_id, risk_result)
            else:
                self.service_stats['failed_predictions'] += 1
            
            self.service_stats['inference_requests'] += 1
            
            return {
                'triggered': True,
                'item_id': item_id,
                'results': results,
                'processing_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error handling inventory change event for item {item_id}: {e}")
            self.service_stats['failed_predictions'] += 1
            return {'triggered': False, 'error': str(e)}
    
    def run_batch_inference(self, force: bool = False) -> Dict[str, Any]:
        """Run batch ML inference for all active items"""
        try:
            # Check if batch inference is due
            if not force and self.service_stats['last_batch_run']:
                time_since_last = (datetime.now() - self.service_stats['last_batch_run']).total_seconds()
                if time_since_last < self.inference_triggers['batch_inference_interval']:
                    return {'skipped': True, 'reason': 'too_soon', 'next_run_in': self.inference_triggers['batch_inference_interval'] - time_since_last}
            
            start_time = time.time()
            logger.info("Starting batch ML inference")
            
            # Get active items (items with recent activity or low stock)
            active_items = self._get_active_items_for_inference()
            
            if not active_items:
                logger.info("No active items found for batch inference")
                return {'completed': True, 'items_processed': 0}
            
            logger.info(f"Running batch inference for {len(active_items)} items")
            
            # Run consumption forecasts
            consumption_results = ml_inference.batch_predict_consumption(
                [item['item_id'] for item in active_items], 
                forecast_days=7
            )
            
            # Run stockout risk assessments
            risk_results = ml_inference.batch_predict_stockout_risk(
                [item['item_id'] for item in active_items]
            )
            
            # Process results and generate alerts
            alerts_generated = 0
            for risk_result in risk_results:
                if risk_result['risk_level'] in ['high', 'critical']:
                    if self._generate_ml_alert(risk_result['item_id'], risk_result):
                        alerts_generated += 1
            
            # Update stats
            self.service_stats['last_batch_run'] = datetime.now()
            self.service_stats['successful_predictions'] += len(consumption_results) + len(risk_results)
            
            processing_time = time.time() - start_time
            
            result = {
                'completed': True,
                'items_processed': len(active_items),
                'consumption_forecasts': len(consumption_results),
                'risk_assessments': len(risk_results),
                'alerts_generated': alerts_generated,
                'processing_time_seconds': processing_time
            }
            
            logger.info(f"Batch inference completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error running batch inference: {e}")
            return {'completed': False, 'error': str(e)}
    
    def validate_models(self) -> Dict[str, Any]:
        """Validate all ML models are available and working"""
        try:
            validation_results = {}
            
            # Check required models
            required_models = ['consumption_forecaster', 'stockout_classifier']
            
            for model_name in required_models:
                validation_result = model_manager.validate_model(model_name)
                validation_results[model_name] = validation_result
                
                if validation_result['valid']:
                    logger.info(f"Model {model_name} validated successfully")
                else:
                    logger.warning(f"Model {model_name} validation failed: {validation_result['errors']}")
            
            # Update service status
            all_valid = all(result['valid'] for result in validation_results.values())
            self.service_stats['models_validated'] = all_valid
            
            return {
                'all_models_valid': all_valid,
                'model_results': validation_results,
                'available_models': model_manager.list_available_models()
            }
            
        except Exception as e:
            logger.error(f"Error validating models: {e}")
            return {'all_models_valid': False, 'error': str(e)}
    
    def get_ml_dashboard_data(self) -> Dict[str, Any]:
        """Get ML data for dashboard display"""
        try:
            # Get recent predictions
            recent_forecasts = ml_inference.get_recent_predictions(limit=20)
            
            # Get high-risk items
            high_risk_items = self._get_high_risk_items()
            
            # Get model status
            model_status = self.validate_models()
            
            # Get inference stats
            inference_stats = ml_inference.get_inference_stats()
            
            return {
                'recent_forecasts': recent_forecasts,
                'high_risk_items': high_risk_items,
                'model_status': model_status,
                'inference_stats': inference_stats,
                'service_stats': self.service_stats,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting ML dashboard data: {e}")
            return {'error': str(e)}
    
    def _get_active_items_for_inference(self) -> List[Dict[str, Any]]:
        """Get items that need ML inference"""
        try:
            with db.cursor() as cursor:
                # Get items with recent activity or low stock
                cursor.execute("""
                    SELECT DISTINCT i.item_id, i.item_name, i.current_stock, i.safety_stock
                    FROM inventory i
                    LEFT JOIN consumption_history ch ON i.item_id = ch.item_id 
                        AND ch.consumption_date > NOW() - INTERVAL '7 days'
                    LEFT JOIN forecasts f ON i.item_id = f.item_id 
                        AND f.created_at > NOW() - INTERVAL '2 hours'
                    WHERE (
                        ch.item_id IS NOT NULL  -- Has recent consumption
                        OR i.current_stock <= i.safety_stock * 1.5  -- Low stock
                        OR f.item_id IS NULL  -- No recent forecast
                    )
                    AND i.current_stock >= 0  -- Valid stock level
                    ORDER BY 
                        CASE WHEN i.current_stock <= i.safety_stock THEN 1 ELSE 2 END,
                        i.current_stock ASC
                    LIMIT 50  -- Limit for t2.micro performance
                """)
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting active items for inference: {e}")
            return []
    
    def _get_high_risk_items(self) -> List[Dict[str, Any]]:
        """Get items with high stockout risk"""
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT rp.*, i.item_name, i.current_stock, i.safety_stock
                    FROM risk_predictions rp
                    JOIN inventory i ON rp.item_id = i.item_id
                    WHERE rp.risk_level IN ('high', 'critical')
                      AND rp.created_at > NOW() - INTERVAL '4 hours'
                    ORDER BY rp.risk_probability DESC, rp.created_at DESC
                    LIMIT 20
                """)
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting high risk items: {e}")
            return []
    
    def _generate_ml_alert(self, item_id: int, risk_result: Dict[str, Any]) -> bool:
        """Generate alert based on ML prediction"""
        try:
            from ..alerts.manager import alert_manager, AlertType, AlertSeverity
            
            # Get item name
            with db.cursor() as cursor:
                cursor.execute("SELECT item_name FROM inventory WHERE item_id = %s", (item_id,))
                item_info = cursor.fetchone()
                item_name = item_info['item_name'] if item_info else f"Item {item_id}"
            
            # Determine alert severity
            risk_level = risk_result['risk_level']
            if risk_level == 'critical':
                severity = AlertSeverity.CRITICAL
            elif risk_level == 'high':
                severity = AlertSeverity.HIGH
            else:
                severity = AlertSeverity.MEDIUM
            
            # Create alert message
            risk_prob = risk_result['risk_probability']
            days_until = risk_result.get('days_until_stockout')
            
            if days_until is not None:
                message = f"{item_name}: High stockout risk ({risk_prob:.1%} probability, ~{days_until} days until stockout)"
            else:
                message = f"{item_name}: High stockout risk ({risk_prob:.1%} probability)"
            
            # Create alert
            alert = alert_manager._create_alert(
                alert_type=AlertType.FORECAST_DEVIATION,
                severity=severity,
                item_id=item_id,
                message=message,
                metadata={
                    'risk_probability': risk_prob,
                    'risk_level': risk_level,
                    'days_until_stockout': days_until,
                    'ml_model': risk_result.get('model_version', 'unknown'),
                    'prediction_source': 'ml_inference'
                }
            )
            
            if alert:
                logger.info(f"ML alert generated for item {item_id}: {risk_level} risk")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error generating ML alert for item {item_id}: {e}")
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get ML service status"""
        try:
            model_status = self.validate_models()
            
            return {
                'service_running': True,
                'models_available': model_status['all_models_valid'],
                'service_stats': self.service_stats,
                'model_cache': model_manager.get_cache_status(),
                'last_batch_run': self.service_stats['last_batch_run'].isoformat() if self.service_stats['last_batch_run'] else None,
                'inference_triggers': self.inference_triggers
            }
            
        except Exception as e:
            logger.error(f"Error getting ML service status: {e}")
            return {'service_running': False, 'error': str(e)}
    
    def cleanup_old_predictions(self, days_old: int = 7) -> Dict[str, int]:
        """Clean up old predictions to save space"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with db.cursor() as cursor:
                # Clean up old forecasts
                cursor.execute("""
                    DELETE FROM forecasts 
                    WHERE created_at < %s
                """, (cutoff_date,))
                forecasts_deleted = cursor.rowcount
                
                # Clean up old risk predictions
                cursor.execute("""
                    DELETE FROM risk_predictions 
                    WHERE created_at < %s
                """, (cutoff_date,))
                risks_deleted = cursor.rowcount
            
            result = {
                'forecasts_deleted': forecasts_deleted,
                'risk_predictions_deleted': risks_deleted
            }
            
            logger.info(f"ML prediction cleanup completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up old predictions: {e}")
            return {'forecasts_deleted': 0, 'risk_predictions_deleted': 0}


# Global ML service instance
ml_service = MLService()