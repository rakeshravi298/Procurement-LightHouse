#!/usr/bin/env python3
"""
Test script for web server functionality
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

def test_web_server():
    """Test web server endpoints"""
    base_url = "http://localhost:5000"
    
    # Test endpoints
    endpoints = [
        ("/health", "Health check"),
        ("/", "Dashboard"),
        ("/api/system/status", "System status API"),
        ("/api/inventory", "Inventory API"),
        ("/api/alerts", "Alerts API"),
        ("/api/ml/status", "ML status API"),
    ]
    
    logger.info("Testing web server endpoints...")
    
    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            logger.info(f"Testing {description}: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✓ {description}: OK")
                
                # For JSON endpoints, check if response is valid JSON
                if endpoint.startswith('/api/') or endpoint == '/health':
                    try:
                        data = response.json()
                        logger.info(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else 'Non-dict response'}")
                    except Exception as e:
                        logger.warning(f"  Could not parse JSON: {e}")
                else:
                    # For HTML endpoints, check if it contains expected content
                    if 'Procurement Lighthouse' in response.text:
                        logger.info(f"  HTML content looks good")
                    else:
                        logger.warning(f"  HTML content may be incomplete")
                        
            else:
                logger.error(f"✗ {description}: HTTP {response.status_code}")
                logger.error(f"  Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ {description}: Connection failed - is the web server running?")
        except requests.exceptions.Timeout:
            logger.error(f"✗ {description}: Request timeout")
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
            
            response = requests.post(url, json={}, timeout=30)
            
            if response.status_code in [200, 202]:
                logger.info(f"✓ {description}: OK")
                try:
                    data = response.json()
                    logger.info(f"  Response: {data.get('message', data)}")
                except:
                    logger.info(f"  Response: {response.text[:100]}...")
            else:
                logger.warning(f"⚠ {description}: HTTP {response.status_code}")
                logger.warning(f"  Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ {description}: Connection failed")
        except requests.exceptions.Timeout:
            logger.error(f"✗ {description}: Request timeout")
        except Exception as e:
            logger.error(f"✗ {description}: {e}")

def main():
    """Main test function"""
    setup_logging('INFO')
    
    logger.info("Web Server Test")
    logger.info("=" * 50)
    
    logger.info("Make sure to start the web server first:")
    logger.info("python -m procurement_lighthouse.main web")
    logger.info("")
    
    # Wait a moment for user to start server
    try:
        input("Press Enter when the web server is running, or Ctrl+C to exit...")
    except KeyboardInterrupt:
        logger.info("Test cancelled")
        return 0
    
    test_web_server()
    
    logger.info("\nWeb server test completed!")
    logger.info("If all tests passed, the web interface is working correctly.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())