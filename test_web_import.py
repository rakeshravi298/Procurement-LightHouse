#!/usr/bin/env python3
"""
Test Flask app import
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    print("Testing Flask app import...")
    
    # Test create_app function
    from procurement_lighthouse.web.app import create_app
    print("✓ create_app imported successfully")
    
    # Test app instance
    from procurement_lighthouse.web.app import app
    print("✓ app instance imported successfully")
    
    # Test app creation
    test_app = create_app()
    print("✓ Flask app created successfully")
    
    # Test basic app properties
    print(f"✓ App name: {test_app.name}")
    print(f"✓ App config keys: {list(test_app.config.keys())}")
    
    # Test routes
    with test_app.test_client() as client:
        # Test health endpoint (should work without database)
        try:
            response = client.get('/health')
            print(f"✓ Health endpoint test: HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠ Health endpoint test failed (expected without DB): {e}")
    
    print("\n✅ Flask app import test completed successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)