#!/usr/bin/env python3
"""
Test script for Grafana dashboard functionality
"""
import sys
import logging
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from procurement_lighthouse.utils import setup_logging

logger = logging.getLogger(__name__)

def test_grafana_service():
    """Test Grafana service functionality"""
    try:
        from procurement_lighthouse.grafana.service import grafana_service
        
        logger.info("Testing Grafana service...")
        
        # Test service status
        logger.info("1. Testing service status...")
        status = grafana_service.get_status()
        logger.info(f"   Service running: {status.get('service_running', False)}")
        logger.info(f"   Grafana URL: {status.get('grafana_url', 'N/A')}")
        logger.info(f"   Status: {status.get('status', 'unknown')}")
        
        if not status.get('service_running', False):
            logger.warning("   Grafana is not running. Make sure Grafana service is started.")
            logger.info("   To start Grafana: sudo systemctl start grafana-server")
            return False
        
        # Test initialization
        logger.info("2. Testing Grafana initialization...")
        if grafana_service.initialize():
            logger.info("   ✓ Grafana initialized successfully")
        else:
            logger.error("   ✗ Grafana initialization failed")
            return False
        
        # Test dashboard URLs
        logger.info("3. Testing dashboard URLs...")
        dashboard_urls = grafana_service.get_dashboard_urls()
        logger.info(f"   Found {len(dashboard_urls)} dashboards:")
        for dashboard in dashboard_urls:
            logger.info(f"     • {dashboard['title']}: {dashboard['url']}")
        
        # Test datasource connection
        logger.info("4. Testing datasource connection...")
        if grafana_service.test_datasource_connection():
            logger.info("   ✓ Datasource connection test passed")
        else:
            logger.warning("   ⚠ Datasource connection test failed (may need database setup)")
        
        # Test data summary
        logger.info("5. Testing data summary...")
        data_summary = grafana_service.get_dashboard_data_summary()
        if data_summary:
            logger.info("   Data available for visualization:")
            for key, value in data_summary.items():
                logger.info(f"     {key.replace('_', ' ').title()}: {value}")
        else:
            logger.warning("   No data summary available (may need database setup)")
        
        return True
        
    except Exception as e:
        logger.error(f"Grafana service test failed: {e}")
        return False

def test_grafana_config():
    """Test Grafana configuration"""
    try:
        from procurement_lighthouse.grafana.config import grafana_config
        
        logger.info("Testing Grafana configuration...")
        
        # Test configuration values
        logger.info(f"   Grafana URL: {grafana_config.grafana_url}")
        logger.info(f"   Admin user: {grafana_config.admin_user}")
        
        # Test dashboard configs
        dashboard_configs = grafana_config.get_dashboard_configs()
        logger.info(f"   Dashboard configurations: {len(dashboard_configs)}")
        
        for config in dashboard_configs:
            title = config['dashboard']['title']
            panel_count = len(config['dashboard']['panels'])
            logger.info(f"     • {title}: {panel_count} panels")
        
        return True
        
    except Exception as e:
        logger.error(f"Grafana config test failed: {e}")
        return False

def main():
    """Main test function"""
    setup_logging('INFO')
    
    logger.info("Grafana Dashboard Test")
    logger.info("=" * 50)
    
    # Test configuration
    logger.info("Testing Grafana configuration...")
    config_success = test_grafana_config()
    
    if not config_success:
        logger.error("Configuration test failed")
        return 1
    
    # Test service
    logger.info("\nTesting Grafana service...")
    service_success = test_grafana_service()
    
    if service_success:
        logger.info("\n✅ Grafana test completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Access Grafana at: http://localhost:3000")
        logger.info("2. Login with admin/admin")
        logger.info("3. View the created dashboards")
        logger.info("4. Ensure data is flowing by running:")
        logger.info("   python -m procurement_lighthouse.main setup")
        logger.info("   python -m procurement_lighthouse.main simulate")
        logger.info("   python -m procurement_lighthouse.main events")
    else:
        logger.error("\n❌ Grafana test failed!")
        logger.error("Troubleshooting:")
        logger.error("1. Check if Grafana is running: sudo systemctl status grafana-server")
        logger.error("2. Start Grafana if needed: sudo systemctl start grafana-server")
        logger.error("3. Check Grafana logs: sudo journalctl -u grafana-server")
        logger.error("4. Verify port 3000 is accessible")
    
    return 0 if service_success else 1

if __name__ == "__main__":
    sys.exit(main())