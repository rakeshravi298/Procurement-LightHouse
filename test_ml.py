#!/usr/bin/env python3
"""
Test ML inference engine functionality
"""
import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from procurement_lighthouse.ml.model_manager import model_manager
from procurement_lighthouse.ml.inference import ml_inference
from procurement_lighthouse.ml.service import ml_service
from procurement_lighthouse.database.connection import db
from procurement_lighthouse.utils import setup_logging

def test_model_manager():
    """Test model manager functionality"""
    print("Testing Model Manager...")
    
    # Test listing models (should be empty initially)
    models = model_manager.list_available_models()
    print(f"Available models: {models}")
    
    # Test model info for non-existent model
    info = model_manager.get_model_info('non_existent_model')
    print(f"Non-existent model info: {info}")
    
    # Test cache status
    cache_status = model_manager.get_cache_status()
    print(f"Cache status: {cache_status}")
    
    print("✓ Model Manager tests completed\n")

def test_ml_inference():
    """Test ML inference functionality"""
    print("Testing ML Inference...")
    
    try:
        # Get a test item from database
        with db.cursor() as cursor:
            cursor.execute("SELECT item_id FROM inventory LIMIT 1")
            result = cursor.fetchone()
            
            if not result:
                print("No inventory items found for testing")
                return
            
            item_id = result['item_id']
            print(f"Testing with item_id: {item_id}")
        
        # Test consumption prediction (will fail without model, but should handle gracefully)
        print("Testing consumption prediction...")
        consumption_result = ml_inference.predict_consumption(item_id)
        if consumption_result:
            print(f"Consumption prediction: {consumption_result}")
        else:
            print("Consumption prediction failed (expected without model)")
        
        # Test stockout risk prediction
        print("Testing stockout risk prediction...")
        risk_result = ml_inference.predict_stockout_risk(item_id)
        if risk_result:
            print(f"Stockout risk prediction: {risk_result}")
        else:
            print("Stockout risk prediction failed (expected without model)")
        
        # Test getting recent predictions
        recent_predictions = ml_inference.get_recent_predictions(limit=5)
        print(f"Recent predictions: {len(recent_predictions)} found")
        
        # Test inference stats
        stats = ml_inference.get_inference_stats()
        print(f"Inference stats: {stats}")
        
    except Exception as e:
        print(f"ML inference test error: {e}")
    
    print("✓ ML Inference tests completed\n")

def test_ml_service():
    """Test ML service functionality"""
    print("Testing ML Service...")
    
    try:
        # Test model validation
        print("Testing model validation...")
        validation_result = ml_service.validate_models()
        print(f"Model validation: {validation_result}")
        
        # Test service status
        status = ml_service.get_service_status()
        print(f"Service status: {status}")
        
        # Test dashboard data
        dashboard_data = ml_service.get_ml_dashboard_data()
        print(f"Dashboard data keys: {list(dashboard_data.keys())}")
        
        # Test inventory change event handling
        print("Testing inventory change event...")
        event_result = ml_service.handle_inventory_change_event(1, 100, 85)
        print(f"Event handling result: {event_result}")
        
    except Exception as e:
        print(f"ML service test error: {e}")
    
    print("✓ ML Service tests completed\n")

def test_database_tables():
    """Test ML-related database tables"""
    print("Testing ML Database Tables...")
    
    try:
        with db.cursor() as cursor:
            # Test forecasts table
            cursor.execute("SELECT COUNT(*) as count FROM forecasts")
            forecast_count = cursor.fetchone()['count']
            print(f"Forecasts table: {forecast_count} records")
            
            # Test risk_predictions table
            cursor.execute("SELECT COUNT(*) as count FROM risk_predictions")
            risk_count = cursor.fetchone()['count']
            print(f"Risk predictions table: {risk_count} records")
            
            # Test system_metrics table
            cursor.execute("SELECT COUNT(*) as count FROM system_metrics")
            metrics_count = cursor.fetchone()['count']
            print(f"System metrics table: {metrics_count} records")
            
    except Exception as e:
        print(f"Database table test error: {e}")
    
    print("✓ Database table tests completed\n")

def main():
    """Run all ML tests"""
    print("=== ML Inference Engine Tests ===\n")
    
    # Setup logging
    setup_logging('INFO')
    
    try:
        # Test database connection
        print("Testing database connection...")
        with db.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✓ Database connection successful\n")
        
        # Run tests
        test_database_tables()
        test_model_manager()
        test_ml_inference()
        test_ml_service()
        
        print("=== All ML Tests Completed ===")
        
    except Exception as e:
        print(f"Test setup failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())