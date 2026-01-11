"""
Grafana service for dashboard management
Optimized for AWS t2.micro deployment
"""
import logging
import time
from typing import Dict, List, Optional
from .config import grafana_config

logger = logging.getLogger(__name__)

class GrafanaService:
    """Service for managing Grafana dashboards and configuration"""
    
    def __init__(self):
        self.config = grafana_config
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Grafana with datasources and dashboards"""
        try:
            logger.info("Initializing Grafana service...")
            
            # Wait for Grafana to be ready
            if not self.config.wait_for_grafana():
                logger.error("Grafana is not ready")
                return False
            
            # Create PostgreSQL datasource
            if not self.config.create_datasource():
                logger.error("Failed to create PostgreSQL datasource")
                return False
            
            # Create all dashboards
            dashboard_configs = self.config.get_dashboard_configs()
            success_count = 0
            
            for dashboard_config in dashboard_configs:
                if self.config.create_dashboard(dashboard_config):
                    success_count += 1
                else:
                    logger.warning(f"Failed to create dashboard: {dashboard_config['dashboard']['title']}")
            
            logger.info(f"Created {success_count}/{len(dashboard_configs)} dashboards")
            
            if success_count > 0:
                self._initialized = True
                logger.info("Grafana service initialized successfully")
                return True
            else:
                logger.error("Failed to create any dashboards")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Grafana service: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get Grafana service status"""
        try:
            # Test Grafana connection
            response = self.config.session.get(f"{self.config.grafana_url}/api/health", timeout=5)
            grafana_running = response.status_code == 200
            
            # Get datasource status
            datasource_response = self.config.session.get(f"{self.config.grafana_url}/api/datasources/name/PostgreSQL")
            datasource_configured = datasource_response.status_code == 200
            
            # Get dashboard count
            dashboards_response = self.config.session.get(f"{self.config.grafana_url}/api/search?type=dash-db")
            dashboard_count = len(dashboards_response.json()) if dashboards_response.status_code == 200 else 0
            
            return {
                'service_running': grafana_running,
                'initialized': self._initialized,
                'grafana_url': self.config.grafana_url,
                'datasource_configured': datasource_configured,
                'dashboard_count': dashboard_count,
                'admin_user': self.config.admin_user,
                'status': 'healthy' if grafana_running and datasource_configured else 'unhealthy'
            }
            
        except Exception as e:
            logger.error(f"Error getting Grafana status: {e}")
            return {
                'service_running': False,
                'initialized': False,
                'error': str(e),
                'status': 'error'
            }
    
    def get_dashboard_urls(self) -> List[Dict]:
        """Get URLs for all dashboards"""
        try:
            response = self.config.session.get(f"{self.config.grafana_url}/api/search?type=dash-db")
            
            if response.status_code != 200:
                return []
            
            dashboards = response.json()
            dashboard_urls = []
            
            for dashboard in dashboards:
                dashboard_urls.append({
                    'title': dashboard.get('title', 'Unknown'),
                    'url': f"{self.config.grafana_url}{dashboard.get('url', '')}",
                    'tags': dashboard.get('tags', [])
                })
            
            return dashboard_urls
            
        except Exception as e:
            logger.error(f"Error getting dashboard URLs: {e}")
            return []
    
    def test_datasource_connection(self) -> bool:
        """Test PostgreSQL datasource connection"""
        try:
            response = self.config.session.post(
                f"{self.config.grafana_url}/api/datasources/proxy/1/query",
                json={
                    "queries": [
                        {
                            "refId": "A",
                            "rawSql": "SELECT 1 as test",
                            "format": "table"
                        }
                    ]
                },
                headers={"Content-Type": "application/json"}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error testing datasource connection: {e}")
            return False
    
    def refresh_dashboards(self) -> bool:
        """Refresh all dashboards by recreating them"""
        try:
            logger.info("Refreshing Grafana dashboards...")
            
            dashboard_configs = self.config.get_dashboard_configs()
            success_count = 0
            
            for dashboard_config in dashboard_configs:
                if self.config.create_dashboard(dashboard_config):
                    success_count += 1
            
            logger.info(f"Refreshed {success_count}/{len(dashboard_configs)} dashboards")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error refreshing dashboards: {e}")
            return False
    
    def get_dashboard_data_summary(self) -> Dict:
        """Get summary of data available for dashboards"""
        try:
            from ..database.connection import db
            
            summary = {
                'inventory_items': 0,
                'active_alerts': 0,
                'recent_events': 0,
                'purchase_orders': 0,
                'forecasts': 0,
                'consumption_records': 0
            }
            
            with db.cursor() as cursor:
                # Inventory count
                cursor.execute("SELECT COUNT(*) as count FROM inventory")
                summary['inventory_items'] = cursor.fetchone()['count']
                
                # Active alerts
                cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'active'")
                summary['active_alerts'] = cursor.fetchone()['count']
                
                # Recent events
                cursor.execute("SELECT COUNT(*) as count FROM event_log WHERE processed_at > NOW() - INTERVAL '1 hour'")
                summary['recent_events'] = cursor.fetchone()['count']
                
                # Purchase orders
                cursor.execute("SELECT COUNT(*) as count FROM purchase_orders")
                summary['purchase_orders'] = cursor.fetchone()['count']
                
                # Forecasts
                cursor.execute("SELECT COUNT(*) as count FROM forecasts")
                summary['forecasts'] = cursor.fetchone()['count']
                
                # Consumption history
                cursor.execute("SELECT COUNT(*) as count FROM consumption_history")
                summary['consumption_records'] = cursor.fetchone()['count']
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting dashboard data summary: {e}")
            return {}

# Global service instance
grafana_service = GrafanaService()