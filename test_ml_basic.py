#!/usr/bin/env python3
"""
Basic ML functionality test without database dependency
"""
import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that ML modules can be imported"""
    print("Testing ML module imports...")
    
    try:
        from procurement_lighthouse.ml.model_manager import ModelManager
        print("✓ ModelManager imported successfully")
        
        from procurement_lighthouse.ml.inference import MLInferenceEngine
        print("✓ MLInferenceEngine imported successfully")
        
        from procurement_lighthouse.ml.service import MLService
        print("✓ MLService imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_model_manager():
    """Test model manager basic functionality"""
    print("\nTesting ModelManager basic functionality...")
    
    try:
        from procurement_lighthouse.ml.model_manager import ModelManager
        
        # Create instance
        manager = ModelManager()
        print("✓ ModelManager instance created")
        
        # Test listing models (should be empty)
        models = manager.list_available_models()
        print(f"✓ Available models: {models}")
        
        # Test model info for non-existent model
        info = manager.get_model_info('non_existent_model')
        print(f"✓ Non-existent model info: {info['exists']}")
        
        # Test cache status
        cache_status = manager.get_cache_status()
        print(f"✓ Cache status: {cache_status['cached_models']} models cached")
        
        return True
    except Exception as e:
        print(f"✗ ModelManager test failed: {e}")
        return False

def test_ml_inference():
    """Test ML inference basic functionality"""
    print("\nTesting MLInferenceEngine basic functionality...")
    
    try:
        from procurement_lighthouse.ml.inference import MLInferenceEngine
        
        # Create instance
        engine = MLInferenceEngine()
        print("✓ MLInferenceEngine instance created")
        
        # Test getting stats
        stats = engine.get_inference_stats()
        print(f"✓ Inference stats: {stats['predictions_made']} predictions made")
        
        return True
    except Exception as e:
        print(f"✗ MLInferenceEngine test failed: {e}")
        return False

def test_ml_service():
    """Test ML service basic functionality"""
    print("\nTesting MLService basic functionality...")
    
    try:
        from procurement_lighthouse.ml.service import MLService
        
        # Create instance
        service = MLService()
        print("✓ MLService instance created")
        
        # Test getting service stats
        stats = service.service_stats
        print(f"✓ Service stats: {stats['inference_requests']} requests processed")
        
        return True
    except Exception as e:
        print(f"✗ MLService test failed: {e}")
        return False

def main():
    """Run basic ML tests"""
    print("=== Basic ML Module Tests ===\n")
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    tests_passed = 0
    total_tests = 4
    
    # Run tests
    if test_imports():
        tests_passed += 1
    
    if test_model_manager():
        tests_passed += 1
    
    if test_ml_inference():
        tests_passed += 1
    
    if test_ml_service():
        tests_passed += 1
    
    print(f"\n=== Test Results: {tests_passed}/{total_tests} tests passed ===")
    
    if tests_passed == total_tests:
        print("✓ All basic ML tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())