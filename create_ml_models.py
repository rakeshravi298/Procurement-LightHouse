#!/usr/bin/env python3
"""
Create simple, lightweight ML models for procurement forecasting
Optimized for AWS t2.micro deployment
"""
import sys
import os
import pickle
import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import model classes
from procurement_lighthouse.ml.models import ConsumptionForecaster, StockoutClassifier

def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def generate_consumption_training_data(n_samples=1000):
    """Generate synthetic training data for consumption forecasting"""
    np.random.seed(42)  # For reproducible results
    
    # Features: current_stock, safety_stock, avg_consumption_7d, avg_consumption_30d, forecast_days, unit_cost
    current_stock = np.random.uniform(0, 1000, n_samples)
    safety_stock = np.random.uniform(10, 200, n_samples)
    avg_consumption_7d = np.random.uniform(1, 50, n_samples)
    avg_consumption_30d = np.random.uniform(1, 45, n_samples)  # Slightly lower than 7d average
    forecast_days = np.random.choice([1, 3, 7, 14, 30], n_samples)
    unit_cost = np.random.uniform(1, 100, n_samples)
    
    # Create feature matrix
    X = np.column_stack([
        current_stock,
        safety_stock,
        avg_consumption_7d,
        avg_consumption_30d,
        forecast_days,
        unit_cost
    ])
    
    # Generate realistic consumption predictions
    # Base consumption on historical averages with some seasonality and randomness
    base_consumption = avg_consumption_7d * forecast_days / 7
    seasonality_factor = 1 + 0.2 * np.sin(np.random.uniform(0, 2*np.pi, n_samples))
    stock_influence = np.where(current_stock < safety_stock, 1.2, 1.0)  # Higher consumption when low stock
    noise = np.random.normal(0, 0.1, n_samples)
    
    y = np.maximum(0, base_consumption * seasonality_factor * stock_influence * (1 + noise))
    
    return X, y

def generate_stockout_training_data(n_samples=1000):
    """Generate synthetic training data for stockout risk classification"""
    np.random.seed(42)  # For reproducible results
    
    # Features: current_stock, safety_stock, consumption_rate, lead_time_days, stock_ratio, consumption_stddev
    current_stock = np.random.uniform(0, 500, n_samples)
    safety_stock = np.random.uniform(10, 100, n_samples)
    consumption_rate = np.random.uniform(0.5, 20, n_samples)
    lead_time_days = np.random.uniform(1, 30, n_samples)
    stock_ratio = current_stock / np.maximum(safety_stock, 1)
    consumption_stddev = np.random.uniform(0, 5, n_samples)
    
    # Create feature matrix
    X = np.column_stack([
        current_stock,
        safety_stock,
        consumption_rate,
        lead_time_days,
        stock_ratio,
        consumption_stddev
    ])
    
    # Generate stockout risk labels
    # Higher risk when: low stock, high consumption rate, long lead times
    days_until_stockout = current_stock / np.maximum(consumption_rate, 0.1)
    risk_score = 1 / (1 + np.exp(-(lead_time_days - days_until_stockout) / 5))  # Sigmoid function
    
    # Add some randomness and threshold
    risk_score += np.random.normal(0, 0.1, n_samples)
    y = (risk_score > 0.5).astype(int)  # Binary classification: 0 = low risk, 1 = high risk
    
    return X, y

def create_consumption_forecaster():
    """Create and train consumption forecasting model"""
    logging.info("Creating consumption forecasting model...")
    
    # Generate training data
    X, y = generate_consumption_training_data(n_samples=2000)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features for better performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train simple linear regression model
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test_scaled)
    mse = mean_squared_error(y_test, y_pred)
    
    logging.info(f"Consumption forecaster trained - MSE: {mse:.2f}")
    
    # Create forecaster with scaler
    forecaster = ConsumptionForecaster(model, scaler)
    
    return forecaster, mse

def create_stockout_classifier():
    """Create and train stockout risk classification model"""
    logging.info("Creating stockout risk classification model...")
    
    # Generate training data
    X, y = generate_stockout_training_data(n_samples=2000)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train logistic regression model
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train_scaled, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    logging.info(f"Stockout classifier trained - Accuracy: {accuracy:.2f}")
    
    # Create classifier with scaler
    classifier = StockoutClassifier(model, scaler)
    
    return classifier, accuracy

def save_models():
    """Create and save ML models"""
    # Create models directory
    models_dir = os.path.join('procurement_lighthouse', 'ml', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    # Create consumption forecaster
    consumption_model, consumption_mse = create_consumption_forecaster()
    
    # Save consumption forecaster
    consumption_path = os.path.join(models_dir, 'consumption_forecaster.pkl')
    with open(consumption_path, 'wb') as f:
        pickle.dump(consumption_model, f)
    
    model_size_mb = os.path.getsize(consumption_path) / (1024 * 1024)
    logging.info(f"Consumption forecaster saved: {consumption_path} ({model_size_mb:.2f}MB)")
    
    # Create stockout classifier
    stockout_model, stockout_accuracy = create_stockout_classifier()
    
    # Save stockout classifier
    stockout_path = os.path.join(models_dir, 'stockout_classifier.pkl')
    with open(stockout_path, 'wb') as f:
        pickle.dump(stockout_model, f)
    
    model_size_mb = os.path.getsize(stockout_path) / (1024 * 1024)
    logging.info(f"Stockout classifier saved: {stockout_path} ({model_size_mb:.2f}MB)")
    
    # Create model metadata
    metadata = {
        'consumption_forecaster': {
            'created_at': np.datetime64('now').item(),
            'model_type': 'LinearRegression',
            'features': ['current_stock', 'safety_stock', 'avg_consumption_7d', 'avg_consumption_30d', 'forecast_days', 'unit_cost'],
            'performance': {'mse': consumption_mse},
            'version': 'v1.0',
            'description': 'Simple linear regression model for consumption forecasting'
        },
        'stockout_classifier': {
            'created_at': np.datetime64('now').item(),
            'model_type': 'LogisticRegression',
            'features': ['current_stock', 'safety_stock', 'consumption_rate', 'lead_time_days', 'stock_ratio', 'consumption_stddev'],
            'performance': {'accuracy': stockout_accuracy},
            'version': 'v1.0',
            'description': 'Simple logistic regression model for stockout risk classification'
        }
    }
    
    # Save metadata
    metadata_path = os.path.join(models_dir, 'model_metadata.pkl')
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    
    logging.info(f"Model metadata saved: {metadata_path}")
    
    return {
        'consumption_forecaster': consumption_path,
        'stockout_classifier': stockout_path,
        'metadata': metadata_path,
        'performance': {
            'consumption_mse': consumption_mse,
            'stockout_accuracy': stockout_accuracy
        }
    }

def test_models():
    """Test the created models"""
    logging.info("Testing created models...")
    
    try:
        from procurement_lighthouse.ml.model_manager import model_manager
        
        # Test loading consumption forecaster
        consumption_model = model_manager.load_model('consumption_forecaster')
        if consumption_model:
            # Test prediction with dummy data
            test_input = np.array([[100, 50, 10, 8, 7, 25]])  # current_stock, safety_stock, avg_7d, avg_30d, forecast_days, unit_cost
            prediction = consumption_model.predict(test_input)
            logging.info(f"✓ Consumption forecaster test prediction: {prediction[0]:.2f} units")
        else:
            logging.error("✗ Failed to load consumption forecaster")
        
        # Test loading stockout classifier
        stockout_model = model_manager.load_model('stockout_classifier')
        if stockout_model:
            # Test prediction with dummy data
            test_input = np.array([[20, 50, 5, 10, 0.4, 2]])  # current_stock, safety_stock, consumption_rate, lead_time, stock_ratio, stddev
            prediction = stockout_model.predict(test_input)
            probabilities = stockout_model.predict_proba(test_input)
            logging.info(f"✓ Stockout classifier test prediction: {prediction[0]} (risk probability: {probabilities[0][1]:.2%})")
        else:
            logging.error("✗ Failed to load stockout classifier")
        
        # Test model info
        models = model_manager.list_available_models()
        logging.info(f"✓ Available models: {models}")
        
        return True
        
    except Exception as e:
        logging.error(f"✗ Model testing failed: {e}")
        return False

def main():
    """Main function to create ML models"""
    setup_logging()
    
    logging.info("=== Creating ML Models for Procurement Lighthouse ===")
    
    try:
        # Create and save models
        results = save_models()
        
        logging.info("=== Model Creation Summary ===")
        logging.info(f"Consumption Forecaster MSE: {results['performance']['consumption_mse']:.2f}")
        logging.info(f"Stockout Classifier Accuracy: {results['performance']['stockout_accuracy']:.2%}")
        
        # Test models
        if test_models():
            logging.info("✓ All models created and tested successfully!")
            return 0
        else:
            logging.error("✗ Model testing failed")
            return 1
            
    except Exception as e:
        logging.error(f"Model creation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())