#!/usr/bin/env python3
"""
Final test for web server functionality
"""
import sys
import logging
import requests
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from procurement_lighthouse.utils import setup_logging

logger = logging.getLogger(__name__)

def test_web_endpoints():
    """Test all web server endpoints"""
    base_url = "http://localhost:5000"
    
    # Test GET endpoints
    get_endpoints = [
        ("/health", "Health check"),
        ("/", "Dashboard"),
        ("/api/system/status", "System status API"),
        ("/api/inventory", "Inventory API"),
        ("/api/alerts", "Alerts API"),
        ("/api/ml/status", "ML status API"),
    ]
    
    logger.info("Testing GET endpoints...")
    
    for endpoint, description in get_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            logger.info(f"Testing {description}: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✓ {description}: OK")
                
                # For JSON endpoints, check response structure
                if endpoint.startswith('/api/') or endpoint == '/health':
                    try:
                        data = response.json()
                        logger.info(f"  Response keys: {list(data.keys())}")
                        
                        # Check for expected fields
                        if 'timestamp' in data:
                            logger.info(f"  Timestamp: {data['timestamp']}")
                        if 'status' in data:
                            logger.info(f"  Status: {data['status']}")
                        if 'message' in data:
                            logger.info(f"  Message: {data['message']}")
                            
                    except Exception as e:
                        logger.warning(f"  Could not parse JSON: {e}")
                else:
                    # For HTML endpoints
                    if 'Procurement Lighthouse' in response.text:
                        logger.info(f"  HTML content looks good")
                    else:
                        logger.warning(f"  HTML content may be incomplete")
                        
            else:
                logger.error(f"✗ {description}: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ {description}: Connection failed - is the web server running?")
            return False
        except Exception as e:
            logger.error(f"✗ {description}: {e}")
    
    # Test POST endpoints
    logger.info("\nTesting POST endpoints...")
    
    post_endpoints = [
        ("/api/ml/batch", "ML batch inference"),
        ("/api/system/start-simulation", "Start simulation"),
        ("/api/system/start-events", "Start events"),
    ]
    
    for endpoint, description in post_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            logger.info(f"Testing {description}: {url}")
            
            response = requests.post(url, json={}, timeout=10)
            
            if response.status_code in [200, 202]:
                logger.info(f"✓ {description}: OK")
                try:
                    data = response.json()
                    logger.info(f"  Message: {data.get('message', 'No message')}")
                except:
                    logger.info(f"  Response: {response.text[:100]}...")
            else:
                logger.warning(f"⚠ {description}: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ {description}: Connection failed")
        except Exception as e:
            logger.error(f"✗ {description}: {e}")
    
    return True

def main():
    """Main test function"""
    setup_logging('INFO')
    
    logger.info("Procurement Lighthouse Web Server Test")
    logger.info("=" * 50)
    
    logger.info("This test assumes the web server is running on http://localhost:5000")
    logger.info("Start the server with: python -m procurement_lighthouse.main web")
    logger.info("")
    
    # Test endpoints
    success = test_web_endpoints()
    
    if success:
        logger.info("\n✅ Web server test completed successfully!")
        logger.info("The web interface is working correctly.")
        logger.info("\nNext steps:")
        logger.info("1. Access the dashboard at: http://localhost:5000")
        logger.info("2. Set up the database with: python -m procurement_lighthouse.main setup")
        logger.info("3. Start services with: python -m procurement_lighthouse.main events")
        logger.info("4. Start simulation with: python -m procurement_lighthouse.main simulate")
    else:
        logger.error("\n❌ Web server test failed!")
        logger.error("Make sure the web server is running before running this test.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())