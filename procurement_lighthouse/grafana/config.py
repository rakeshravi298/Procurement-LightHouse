"""
Grafana configuration and dashboard management
Optimized for AWS t2.micro deployment
"""
import json
import logging
import requests
from typing import Dict, List, Optional
from ..config import config

logger = logging.getLogger(__name__)

class GrafanaConfig:
    """Grafana configuration manager for t2.micro constraints"""
    
    def __init__(self):
        self.grafana_url = f"http://{config.grafana.host}:{config.grafana.port}"
        self.admin_user = "admin"
        self.admin_password = "admin"
        self.session = requests.Session()
        self.session.auth = (self.admin_user, self.admin_password)
        
    def wait_for_grafana(self, max_retries: int = 30, delay: int = 2) -> bool:
        """Wait for Grafana to be ready"""
        import time
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(f"{self.grafana_url}/api/health", timeout=5)
                if response.status_code == 200:
                    logger.info("Grafana is ready")
                    return True
            except Exception as e:
                logger.debug(f"Grafana not ready (attempt {attempt + 1}): {e}")
                
            time.sleep(delay)
        
        logger.error("Grafana failed to become ready")
        return False
    
    def create_datasource(self) -> bool:
        """Create PostgreSQL datasource"""
        try:
            # Check if datasource already exists
            response = self.session.get(f"{self.grafana_url}/api/datasources/name/PostgreSQL")
            if response.status_code == 200:
                logger.info("PostgreSQL datasource already exists")
                return True
            
            # Create new datasource
            datasource_config = {
                "name": "PostgreSQL",
                "type": "postgres",
                "url": f"{config.database.host}:{config.database.port}",
                "database": config.database.name,
                "user": config.database.user,
                "secureJsonData": {
                    "password": config.database.password
                },
                "jsonData": {
                    "sslmode": "disable",
                    "maxOpenConns": 5,  # Conservative for t2.micro
                    "maxIdleConns": 2,
                    "connMaxLifetime": 14400,
                    "postgresVersion": 1300,
                    "timescaledb": False
                },
                "access": "proxy",
                "isDefault": True
            }
            
            response = self.session.post(
                f"{self.grafana_url}/api/datasources",
                json=datasource_config,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 409]:  # 409 = already exists
                logger.info("PostgreSQL datasource created successfully")
                return True
            else:
                logger.error(f"Failed to create datasource: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating datasource: {e}")
            return False
    
    def create_dashboard(self, dashboard_config: Dict) -> bool:
        """Create or update a dashboard"""
        try:
            response = self.session.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_config,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Dashboard '{dashboard_config['dashboard']['title']}' created: {result.get('url', 'N/A')}")
                return True
            else:
                logger.error(f"Failed to create dashboard: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            return False
    
    def get_dashboard_configs(self) -> List[Dict]:
        """Get all dashboard configurations optimized for t2.micro"""
        return [
            self._get_main_dashboard_config(),
            self._get_inventory_dashboard_config(),
            self._get_alerts_dashboard_config(),
            self._get_ml_dashboard_config()
        ]
    
    def _get_main_dashboard_config(self) -> Dict:
        """Main overview dashboard configuration"""
        return {
            "dashboard": {
                "id": None,
                "title": "Procurement Lighthouse - Overview",
                "tags": ["procurement", "overview"],
                "timezone": "browser",
                "refresh": "15s",  # Conservative refresh for t2.micro
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "System Status",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT COUNT(*) as value, 'Inventory Items' as metric FROM inventory",
                                "refId": "A",
                                "format": "table"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {"displayMode": "basic"},
                                "unit": "short"
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Active Alerts",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT COUNT(*) as value FROM alerts WHERE status = 'active'",
                                "refId": "A",
                                "format": "table"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 5},
                                        {"color": "red", "value": 10}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 3,
                        "title": "Recent Events",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT COUNT(*) as value FROM event_log WHERE processed_at > NOW() - INTERVAL '1 hour'",
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Purchase Orders",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT COUNT(*) as value FROM purchase_orders WHERE status IN ('created', 'approved')",
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Inventory Levels Over Time",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    last_updated as time,
                                    item_name as metric,
                                    current_stock as value
                                FROM inventory 
                                WHERE last_updated > NOW() - INTERVAL '1 hour'
                                ORDER BY last_updated
                                """,
                                "refId": "A",
                                "format": "time_series"
                            }
                        ]
                    },
                    {
                        "id": 6,
                        "title": "Alert Severity Distribution",
                        "type": "piechart",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 8},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    severity as metric,
                                    COUNT(*) as value
                                FROM alerts 
                                WHERE status = 'active'
                                GROUP BY severity
                                """,
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    }
                ]
            },
            "overwrite": True
        }
    
    def _get_inventory_dashboard_config(self) -> Dict:
        """Inventory-focused dashboard configuration"""
        return {
            "dashboard": {
                "id": None,
                "title": "Procurement Lighthouse - Inventory",
                "tags": ["procurement", "inventory"],
                "timezone": "browser",
                "refresh": "30s",
                "time": {
                    "from": "now-6h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "Low Stock Items",
                        "type": "table",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    item_name as "Item",
                                    current_stock as "Current Stock",
                                    safety_stock as "Safety Stock",
                                    ROUND((current_stock::float / safety_stock::float) * 100, 1) as "Stock %"
                                FROM inventory 
                                WHERE current_stock <= safety_stock * 1.2
                                ORDER BY (current_stock::float / safety_stock::float)
                                """,
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Stock Level Distribution",
                        "type": "bargauge",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    item_name as metric,
                                    current_stock as value
                                FROM inventory 
                                ORDER BY current_stock DESC
                                LIMIT 10
                                """,
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Consumption Trends",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 9},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    consumption_date as time,
                                    item_name as metric,
                                    quantity_consumed as value
                                FROM consumption_history 
                                WHERE consumption_date > NOW() - INTERVAL '6 hours'
                                ORDER BY consumption_date
                                """,
                                "refId": "A",
                                "format": "time_series"
                            }
                        ]
                    }
                ]
            },
            "overwrite": True
        }
    
    def _get_alerts_dashboard_config(self) -> Dict:
        """Alerts-focused dashboard configuration"""
        return {
            "dashboard": {
                "id": None,
                "title": "Procurement Lighthouse - Alerts",
                "tags": ["procurement", "alerts"],
                "timezone": "browser",
                "refresh": "10s",  # More frequent for alerts
                "time": {
                    "from": "now-24h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "Active Alerts",
                        "type": "table",
                        "gridPos": {"h": 12, "w": 24, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    created_at as "Created",
                                    alert_type as "Type",
                                    severity as "Severity",
                                    message as "Message",
                                    COALESCE(item_name, supplier_name, 'System') as "Context"
                                FROM alerts 
                                WHERE status = 'active'
                                ORDER BY created_at DESC
                                """,
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Alert Frequency",
                        "type": "timeseries",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 12},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    DATE_TRUNC('hour', created_at) as time,
                                    alert_type as metric,
                                    COUNT(*) as value
                                FROM alerts 
                                WHERE created_at > NOW() - INTERVAL '24 hours'
                                GROUP BY DATE_TRUNC('hour', created_at), alert_type
                                ORDER BY time
                                """,
                                "refId": "A",
                                "format": "time_series"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Alert Resolution Time",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 12},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/60) as value
                                FROM alerts 
                                WHERE status = 'resolved' 
                                AND resolved_at > NOW() - INTERVAL '24 hours'
                                """,
                                "refId": "A",
                                "format": "table"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "min",
                                "displayName": "Avg Resolution Time"
                            }
                        }
                    }
                ]
            },
            "overwrite": True
        }
    
    def _get_ml_dashboard_config(self) -> Dict:
        """ML predictions dashboard configuration"""
        return {
            "dashboard": {
                "id": None,
                "title": "Procurement Lighthouse - ML Predictions",
                "tags": ["procurement", "ml", "forecasting"],
                "timezone": "browser",
                "refresh": "60s",  # Less frequent for ML data
                "time": {
                    "from": "now-7d",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "High Risk Items",
                        "type": "table",
                        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    i.item_name as "Item",
                                    f.predicted_consumption as "Forecast",
                                    f.confidence_score as "Confidence",
                                    f.prediction_date as "Updated"
                                FROM forecasts f
                                JOIN inventory i ON f.item_id = i.item_id
                                WHERE f.confidence_score < 0.7
                                ORDER BY f.confidence_score
                                """,
                                "refId": "A",
                                "format": "table"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Forecast Accuracy",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 12, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    prediction_date as time,
                                    'Confidence Score' as metric,
                                    AVG(confidence_score) as value
                                FROM forecasts 
                                WHERE prediction_date > NOW() - INTERVAL '7 days'
                                GROUP BY prediction_date
                                ORDER BY prediction_date
                                """,
                                "refId": "A",
                                "format": "time_series"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Consumption vs Forecast",
                        "type": "timeseries",
                        "gridPos": {"h": 9, "w": 24, "x": 0, "y": 9},
                        "targets": [
                            {
                                "expr": """
                                SELECT 
                                    ch.consumption_date as time,
                                    CONCAT(i.item_name, ' - Actual') as metric,
                                    ch.quantity_consumed as value
                                FROM consumption_history ch
                                JOIN inventory i ON ch.item_id = i.item_id
                                WHERE ch.consumption_date > NOW() - INTERVAL '7 days'
                                UNION ALL
                                SELECT 
                                    f.prediction_date as time,
                                    CONCAT(i.item_name, ' - Forecast') as metric,
                                    f.predicted_consumption as value
                                FROM forecasts f
                                JOIN inventory i ON f.item_id = i.item_id
                                WHERE f.prediction_date > NOW() - INTERVAL '7 days'
                                ORDER BY time
                                """,
                                "refId": "A",
                                "format": "time_series"
                            }
                        ]
                    }
                ]
            },
            "overwrite": True
        }

grafana_config = GrafanaConfig()