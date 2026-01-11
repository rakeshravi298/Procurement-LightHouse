"""
Memory-efficient ML inference engine
Optimized for t2.micro with minimal resource usage
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

from .model_manager import model_manager
from ..database.connection import db
from ..config import config

logger = logging.getLogger(__name__)

class MLInferenceEngine:
    """Lightweight ML inference engine for t2.micro"""
    
    def __init__(self):
        self.inference_stats = {
            'predictions_made': 0,
            'inference_errors': 0,
            'last_inference': None,
            'models_used': set()
        }
        
        # Model configurations
        self.model_configs = {
            'consumption_forecast': {
                'model_name': 'consumption_forecaster',
                'input_features': ['current_stock', 'safety_stock', 'avg_consumption_7d', 'avg_consumption_30d'],
                'output_type': 'consumption_prediction',
                'batch_size': 10  # Process in small batches for t2.micro
            },
            'stockout_risk': {
                'model_name': 'stockout_classifier',
                'input_features': ['current_stock', 'safety_stock', 'consumption_rate', 'lead_time_days'],
                'output_type': 'risk_score',
                'batch_size': 20
            }
        }
    
    def predict_consumption(self, item_id: int, forecast_days: int = 7) -> Optional[Dict[str, Any]]:
        """Predict consumption for an item"""
        start_time = time.time()
        
        try:
            # Get item features
            features = self._get_consumption_features(item_id)
            if not features:
                logger.warning(f"Could not get features for item {item_id}")
                return None
            
            # Load model
            model = model_manager.load_model('consumption_forecaster')
            if model is None:
                logger.warning("Consumption forecaster model not available")
                return None
            
            # Prepare input data
            input_data = self._prepare_consumption_input(features, forecast_days)
            
            # Make prediction
            prediction = model.predict([input_data])[0]
            confidence = self._calculate_prediction_confidence(model, input_data)
            
            # Store prediction
            prediction_result = {
                'item_id': item_id,
                'forecast_days': forecast_days,
                'predicted_consumption': max(0, int(prediction)),  # Ensure non-negative
                'confidence_score': confidence,
                'features_used': features,
                'prediction_date': datetime.now(),
                'model_version': 'consumption_forecaster_v1'
            }
            
            self._store_forecast(prediction_result)
            
            # Update stats
            self.inference_stats['predictions_made'] += 1
            self.inference_stats['last_inference'] = datetime.now()
            self.inference_stats['models_used'].add('consumption_forecaster')
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Consumption prediction for item {item_id}: {prediction_result['predicted_consumption']} units ({processing_time:.1f}ms)")
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Error predicting consumption for item {item_id}: {e}")
            self.inference_stats['inference_errors'] += 1
            return None
    
    def predict_stockout_risk(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Predict stockout risk for an item"""
        start_time = time.time()
        
        try:
            # Get item features
            features = self._get_stockout_features(item_id)
            if not features:
                logger.warning(f"Could not get stockout features for item {item_id}")
                return None
            
            # Load model
            model = model_manager.load_model('stockout_classifier')
            if model is None:
                logger.warning("Stockout classifier model not available")
                return None
            
            # Prepare input data
            input_data = self._prepare_stockout_input(features)
            
            # Make prediction
            risk_probability = model.predict_proba([input_data])[0][1]  # Probability of stockout
            risk_level = self._classify_risk_level(risk_probability)
            
            # Calculate days until stockout
            days_until_stockout = self._estimate_days_until_stockout(features)
            
            # Store prediction
            prediction_result = {
                'item_id': item_id,
                'risk_probability': risk_probability,
                'risk_level': risk_level,
                'days_until_stockout': days_until_stockout,
                'features_used': features,
                'prediction_date': datetime.now(),
                'model_version': 'stockout_classifier_v1'
            }
            
            self._store_risk_prediction(prediction_result)
            
            # Update stats
            self.inference_stats['predictions_made'] += 1
            self.inference_stats['last_inference'] = datetime.now()
            self.inference_stats['models_used'].add('stockout_classifier')
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Stockout risk for item {item_id}: {risk_level} ({risk_probability:.2%}, {processing_time:.1f}ms)")
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Error predicting stockout risk for item {item_id}: {e}")
            self.inference_stats['inference_errors'] += 1
            return None
    
    def batch_predict_consumption(self, item_ids: List[int], forecast_days: int = 7) -> List[Dict[str, Any]]:
        """Batch prediction for multiple items (memory efficient)"""
        results = []
        batch_size = self.model_configs['consumption_forecast']['batch_size']
        
        try:
            # Process in small batches
            for i in range(0, len(item_ids), batch_size):
                batch_ids = item_ids[i:i + batch_size]
                
                for item_id in batch_ids:
                    result = self.predict_consumption(item_id, forecast_days)
                    if result:
                        results.append(result)
                
                # Small delay between batches to avoid overwhelming t2.micro
                if i + batch_size < len(item_ids):
                    time.sleep(0.1)
            
            logger.info(f"Batch consumption prediction completed: {len(results)}/{len(item_ids)} successful")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch consumption prediction: {e}")
            return results
    
    def batch_predict_stockout_risk(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch stockout risk prediction"""
        results = []
        batch_size = self.model_configs['stockout_risk']['batch_size']
        
        try:
            # Process in small batches
            for i in range(0, len(item_ids), batch_size):
                batch_ids = item_ids[i:i + batch_size]
                
                for item_id in batch_ids:
                    result = self.predict_stockout_risk(item_id)
                    if result:
                        results.append(result)
                
                # Small delay between batches
                if i + batch_size < len(item_ids):
                    time.sleep(0.1)
            
            logger.info(f"Batch stockout risk prediction completed: {len(results)}/{len(item_ids)} successful")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch stockout risk prediction: {e}")
            return results
    
    def _get_consumption_features(self, item_id: int) -> Optional[Dict[str, float]]:
        """Get features for consumption prediction"""
        try:
            with db.cursor() as cursor:
                # Get inventory info
                cursor.execute("""
                    SELECT current_stock, safety_stock, unit_cost
                    FROM inventory 
                    WHERE item_id = %s
                """, (item_id,))
                
                inventory = cursor.fetchone()
                if not inventory:
                    return None
                
                # Get consumption history
                cursor.execute("""
                    SELECT 
                        AVG(CASE WHEN consumption_date > NOW() - INTERVAL '7 days' 
                            THEN quantity_consumed ELSE NULL END) as avg_consumption_7d,
                        AVG(CASE WHEN consumption_date > NOW() - INTERVAL '30 days' 
                            THEN quantity_consumed ELSE NULL END) as avg_consumption_30d,
                        COUNT(*) as history_count
                    FROM consumption_history 
                    WHERE item_id = %s 
                      AND consumption_date > NOW() - INTERVAL '30 days'
                """, (item_id,))
                
                consumption = cursor.fetchone()
                
                return {
                    'current_stock': float(inventory['current_stock']),
                    'safety_stock': float(inventory['safety_stock']),
                    'avg_consumption_7d': float(consumption['avg_consumption_7d'] or 0),
                    'avg_consumption_30d': float(consumption['avg_consumption_30d'] or 0),
                    'unit_cost': float(inventory['unit_cost']),
                    'history_count': int(consumption['history_count'])
                }
                
        except Exception as e:
            logger.error(f"Error getting consumption features for item {item_id}: {e}")
            return None
    
    def _get_stockout_features(self, item_id: int) -> Optional[Dict[str, float]]:
        """Get features for stockout risk prediction"""
        try:
            with db.cursor() as cursor:
                # Get inventory and consumption data
                cursor.execute("""
                    SELECT 
                        i.current_stock, i.safety_stock, i.unit_cost,
                        AVG(ch.quantity_consumed) as avg_consumption,
                        STDDEV(ch.quantity_consumed) as consumption_stddev,
                        COUNT(ch.consumption_id) as consumption_records
                    FROM inventory i
                    LEFT JOIN consumption_history ch ON i.item_id = ch.item_id 
                        AND ch.consumption_date > NOW() - INTERVAL '30 days'
                    WHERE i.item_id = %s
                    GROUP BY i.item_id, i.current_stock, i.safety_stock, i.unit_cost
                """, (item_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                # Calculate consumption rate
                avg_consumption = float(result['avg_consumption'] or 0)
                consumption_rate = avg_consumption if avg_consumption > 0 else 0.1
                
                # Estimate lead time (simplified)
                lead_time_days = 7.0  # Default lead time
                
                return {
                    'current_stock': float(result['current_stock']),
                    'safety_stock': float(result['safety_stock']),
                    'consumption_rate': consumption_rate,
                    'consumption_stddev': float(result['consumption_stddev'] or 0),
                    'lead_time_days': lead_time_days,
                    'stock_ratio': float(result['current_stock']) / max(float(result['safety_stock']), 1.0)
                }
                
        except Exception as e:
            logger.error(f"Error getting stockout features for item {item_id}: {e}")
            return None
    
    def _prepare_consumption_input(self, features: Dict[str, float], forecast_days: int) -> List[float]:
        """Prepare input data for consumption model"""
        return [
            features['current_stock'],
            features['safety_stock'],
            features['avg_consumption_7d'],
            features['avg_consumption_30d'],
            float(forecast_days),
            features.get('unit_cost', 0.0)
        ]
    
    def _prepare_stockout_input(self, features: Dict[str, float]) -> List[float]:
        """Prepare input data for stockout model"""
        return [
            features['current_stock'],
            features['safety_stock'],
            features['consumption_rate'],
            features['lead_time_days'],
            features['stock_ratio'],
            features.get('consumption_stddev', 0.0)
        ]
    
    def _calculate_prediction_confidence(self, model: Any, input_data: List[float]) -> float:
        """Calculate prediction confidence (simplified)"""
        try:
            # Simple confidence based on feature completeness
            non_zero_features = sum(1 for x in input_data if x > 0)
            confidence = min(0.95, non_zero_features / len(input_data))
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _classify_risk_level(self, risk_probability: float) -> str:
        """Classify risk probability into levels"""
        if risk_probability >= 0.8:
            return 'critical'
        elif risk_probability >= 0.6:
            return 'high'
        elif risk_probability >= 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_days_until_stockout(self, features: Dict[str, float]) -> Optional[int]:
        """Estimate days until stockout based on consumption rate"""
        try:
            current_stock = features['current_stock']
            consumption_rate = features['consumption_rate']
            
            if consumption_rate <= 0:
                return None
            
            days_until_stockout = int(current_stock / consumption_rate)
            return max(0, days_until_stockout)
            
        except Exception as e:
            logger.error(f"Error estimating days until stockout: {e}")
            return None
    
    def _store_forecast(self, prediction_result: Dict[str, Any]):
        """Store forecast prediction in database"""
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO forecasts (
                        item_id, forecast_date, predicted_consumption, 
                        confidence_score, model_version, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    prediction_result['item_id'],
                    prediction_result['prediction_date'].date(),
                    prediction_result['predicted_consumption'],
                    prediction_result['confidence_score'],
                    prediction_result['model_version'],
                    prediction_result['prediction_date']
                ))
                
        except Exception as e:
            logger.error(f"Error storing forecast: {e}")
    
    def _store_risk_prediction(self, prediction_result: Dict[str, Any]):
        """Store risk prediction in database"""
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO risk_predictions (
                        item_id, risk_probability, risk_level, 
                        days_until_stockout, model_version, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    prediction_result['item_id'],
                    prediction_result['risk_probability'],
                    prediction_result['risk_level'],
                    prediction_result['days_until_stockout'],
                    prediction_result['model_version'],
                    prediction_result['prediction_date']
                ))
                
        except Exception as e:
            logger.error(f"Error storing risk prediction: {e}")
    
    def get_recent_predictions(self, item_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent predictions"""
        try:
            with db.cursor() as cursor:
                if item_id:
                    cursor.execute("""
                        SELECT f.*, i.item_name
                        FROM forecasts f
                        JOIN inventory i ON f.item_id = i.item_id
                        WHERE f.item_id = %s
                        ORDER BY f.created_at DESC
                        LIMIT %s
                    """, (item_id, limit))
                else:
                    cursor.execute("""
                        SELECT f.*, i.item_name
                        FROM forecasts f
                        JOIN inventory i ON f.item_id = i.item_id
                        ORDER BY f.created_at DESC
                        LIMIT %s
                    """, (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting recent predictions: {e}")
            return []
    
    def get_inference_stats(self) -> Dict[str, Any]:
        """Get inference engine statistics"""
        stats = self.inference_stats.copy()
        stats['models_used'] = list(stats['models_used'])
        
        # Add model status
        stats['available_models'] = model_manager.list_available_models()
        stats['cache_status'] = model_manager.get_cache_status()
        
        return stats


# Global inference engine instance
ml_inference = MLInferenceEngine()