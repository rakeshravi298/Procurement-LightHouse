"""
Lightweight ML model management system
Optimized for t2.micro with minimal memory usage
"""
import logging
import os
import pickle
import joblib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import numpy as np

from ..config import config

logger = logging.getLogger(__name__)

class ModelManager:
    """Lightweight ML model manager for t2.micro"""
    
    def __init__(self):
        self.models = {}  # In-memory model cache (small models only)
        self.model_metadata = {}
        self.models_dir = os.path.join(os.path.dirname(__file__), 'models')
        self.max_cache_size = 3  # Limit cached models for t2.micro
        
        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Load model metadata
        self._load_model_metadata()
    
    def _load_model_metadata(self):
        """Load model metadata from disk"""
        try:
            metadata_file = os.path.join(self.models_dir, 'model_metadata.pkl')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'rb') as f:
                    self.model_metadata = pickle.load(f)
                logger.info(f"Loaded metadata for {len(self.model_metadata)} models")
            else:
                logger.info("No model metadata found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading model metadata: {e}")
            self.model_metadata = {}
    
    def _save_model_metadata(self):
        """Save model metadata to disk"""
        try:
            metadata_file = os.path.join(self.models_dir, 'model_metadata.pkl')
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.model_metadata, f)
            logger.debug("Model metadata saved")
            
        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")
    
    def load_model(self, model_name: str, force_reload: bool = False) -> Optional[Any]:
        """Load ML model with caching"""
        try:
            # Check cache first
            if not force_reload and model_name in self.models:
                logger.debug(f"Model {model_name} loaded from cache")
                return self.models[model_name]
            
            # Check if model file exists
            model_file = os.path.join(self.models_dir, f"{model_name}.pkl")
            if not os.path.exists(model_file):
                logger.warning(f"Model file not found: {model_file}")
                return None
            
            # Load model from disk
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
            
            # Manage cache size (remove oldest if needed)
            if len(self.models) >= self.max_cache_size:
                oldest_model = min(self.models.keys(), 
                                 key=lambda k: self.model_metadata.get(k, {}).get('last_used', datetime.min))
                del self.models[oldest_model]
                logger.debug(f"Removed {oldest_model} from cache to make space")
            
            # Cache the model
            self.models[model_name] = model
            
            # Update metadata
            if model_name not in self.model_metadata:
                self.model_metadata[model_name] = {}
            
            self.model_metadata[model_name].update({
                'last_used': datetime.now(),
                'load_count': self.model_metadata[model_name].get('load_count', 0) + 1,
                'file_size': os.path.getsize(model_file)
            })
            
            self._save_model_metadata()
            
            logger.info(f"Model {model_name} loaded successfully")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return None
    
    def save_model(self, model: Any, model_name: str, model_info: Dict = None) -> bool:
        """Save ML model to disk"""
        try:
            model_file = os.path.join(self.models_dir, f"{model_name}.pkl")
            
            # Save model
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            
            # Update metadata
            if model_name not in self.model_metadata:
                self.model_metadata[model_name] = {}
            
            self.model_metadata[model_name].update({
                'created_at': datetime.now(),
                'file_size': os.path.getsize(model_file),
                'model_info': model_info or {}
            })
            
            self._save_model_metadata()
            
            logger.info(f"Model {model_name} saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model {model_name}: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get model information"""
        try:
            if model_name not in self.model_metadata:
                return {'exists': False}
            
            metadata = self.model_metadata[model_name].copy()
            metadata['exists'] = True
            metadata['cached'] = model_name in self.models
            
            # Add file existence check
            model_file = os.path.join(self.models_dir, f"{model_name}.pkl")
            metadata['file_exists'] = os.path.exists(model_file)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting model info for {model_name}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def list_available_models(self) -> List[str]:
        """List all available models"""
        try:
            # Get models from metadata
            metadata_models = set(self.model_metadata.keys())
            
            # Get models from filesystem
            file_models = set()
            if os.path.exists(self.models_dir):
                for file in os.listdir(self.models_dir):
                    if file.endswith('.pkl') and file != 'model_metadata.pkl':
                        file_models.add(file[:-4])  # Remove .pkl extension
            
            # Return union of both
            return sorted(list(metadata_models.union(file_models)))
            
        except Exception as e:
            logger.error(f"Error listing available models: {e}")
            return []
    
    def delete_model(self, model_name: str) -> bool:
        """Delete model from disk and cache"""
        try:
            # Remove from cache
            if model_name in self.models:
                del self.models[model_name]
            
            # Remove from metadata
            if model_name in self.model_metadata:
                del self.model_metadata[model_name]
                self._save_model_metadata()
            
            # Remove file
            model_file = os.path.join(self.models_dir, f"{model_name}.pkl")
            if os.path.exists(model_file):
                os.remove(model_file)
            
            logger.info(f"Model {model_name} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting model {model_name}: {e}")
            return False
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get model cache status"""
        try:
            total_memory = sum(
                self.model_metadata.get(name, {}).get('file_size', 0) 
                for name in self.models.keys()
            )
            
            return {
                'cached_models': len(self.models),
                'max_cache_size': self.max_cache_size,
                'total_models': len(self.model_metadata),
                'estimated_memory_mb': total_memory / (1024 * 1024),
                'cached_model_names': list(self.models.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {}
    
    def clear_cache(self) -> int:
        """Clear model cache to free memory"""
        try:
            cleared_count = len(self.models)
            self.models.clear()
            logger.info(f"Cleared {cleared_count} models from cache")
            return cleared_count
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def validate_model(self, model_name: str) -> Dict[str, Any]:
        """Validate model can be loaded and used"""
        validation_result = {
            'model_name': model_name,
            'valid': False,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if model exists
            model_info = self.get_model_info(model_name)
            if not model_info.get('exists', False):
                validation_result['errors'].append("Model does not exist")
                return validation_result
            
            if not model_info.get('file_exists', False):
                validation_result['errors'].append("Model file not found on disk")
                return validation_result
            
            # Try to load model
            model = self.load_model(model_name)
            if model is None:
                validation_result['errors'].append("Failed to load model")
                return validation_result
            
            # Check if model has required methods
            required_methods = ['predict']
            for method in required_methods:
                if not hasattr(model, method):
                    validation_result['errors'].append(f"Model missing required method: {method}")
            
            # Check model size
            file_size_mb = model_info.get('file_size', 0) / (1024 * 1024)
            if file_size_mb > 50:  # 50MB limit for t2.micro
                validation_result['warnings'].append(f"Model is large ({file_size_mb:.1f}MB) - may impact t2.micro performance")
            
            # If no errors, model is valid
            if not validation_result['errors']:
                validation_result['valid'] = True
                validation_result['file_size_mb'] = file_size_mb
            
            return validation_result
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
            return validation_result


# Global model manager instance
model_manager = ModelManager()