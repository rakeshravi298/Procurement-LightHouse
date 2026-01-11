"""
Configuration settings optimized for AWS t2.micro Free Tier
"""
import os
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    """PostgreSQL configuration optimized for t2.micro (1GB RAM)"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '5432'))
    database: str = os.getenv('DB_NAME', 'procurement_lighthouse')
    username: str = os.getenv('DB_USER', 'postgres')
    password: str = os.getenv('DB_PASSWORD', 'postgres')
    
    # t2.micro optimized settings
    max_connections: int = 20
    shared_buffers: str = "128MB"
    effective_cache_size: str = "512MB"
    work_mem: str = "4MB"

@dataclass
class EventConfig:
    """Event processing configuration"""
    event_channels: list = None
    reconnect_delay: int = 5  # seconds
    max_retries: int = 3
    
    def __post_init__(self):
        if self.event_channels is None:
            self.event_channels = [
                'inventory_changed',
                'po_status_changed', 
                'alert_generated',
                'forecast_updated'
            ]

@dataclass
class SimulatorConfig:
    """Data simulator configuration - conservative for t2.micro"""
    inventory_event_interval: int = 60  # seconds (reduced frequency)
    po_event_interval: int = 180  # seconds (3 minutes)
    consumption_event_interval: int = 45  # seconds
    max_items: int = 50  # small dataset for demo
    max_pos: int = 20  # limited POs

@dataclass
class MLConfig:
    """ML engine configuration"""
    models_path: str = os.getenv('MODELS_PATH', '/opt/procurement_lighthouse/models')
    max_model_size_mb: int = 10  # Keep models small for t2.micro
    inference_batch_size: int = 10  # Process in small batches
    
@dataclass
class WebConfig:
    """Web server configuration"""
    host: str = os.getenv('WEB_HOST', '0.0.0.0')
    port: int = int(os.getenv('WEB_PORT', '8080'))
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'

@dataclass
class GrafanaConfig:
    """Grafana configuration"""
    host: str = os.getenv('GRAFANA_HOST', 'localhost')
    port: int = int(os.getenv('GRAFANA_PORT', '3000'))
    refresh_interval: int = 15  # seconds (conservative for t2.micro)

# Global configuration instance
class Config:
    def __init__(self):
        self.database = DatabaseConfig()
        self.events = EventConfig()
        self.simulator = SimulatorConfig()
        self.ml = MLConfig()
        self.web = WebConfig()
        self.grafana = GrafanaConfig()

config = Config()