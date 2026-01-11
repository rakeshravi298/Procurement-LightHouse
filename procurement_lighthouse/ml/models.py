"""
ML model wrapper classes for procurement lighthouse
"""
import numpy as np

class ConsumptionForecaster:
    """Wrapper for consumption forecasting model with scaler"""
    def __init__(self, model, scaler):
        self.model = model
        self.scaler = scaler
    
    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X):
        # For compatibility, return dummy probabilities
        predictions = self.predict(X)
        return np.column_stack([1 - predictions/100, predictions/100])

class StockoutClassifier:
    """Wrapper for stockout risk classification model with scaler"""
    def __init__(self, model, scaler):
        self.model = model
        self.scaler = scaler
    
    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)