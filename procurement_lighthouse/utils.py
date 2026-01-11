"""
Utility functions for the Procurement Lighthouse PoC
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any

def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration optimized for t2.micro"""
    import os
    import platform
    
    # Create logs directory based on platform
    if platform.system() == 'Windows':
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'procurement_lighthouse.log')
    else:
        # Linux/EC2 - use standard log directory
        log_dir = '/var/log'
        os.makedirs(log_dir, exist_ok=True)
        log_file = '/var/log/procurement_lighthouse.log'
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def parse_event_payload(payload: str) -> Dict[str, Any]:
    """Parse JSON event payload with error handling"""
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse event payload: {payload}, error: {e}")
        return {}

def format_timestamp(dt: datetime = None) -> str:
    """Format timestamp for consistent display"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def calculate_stock_status(current_stock: int, safety_stock: int) -> str:
    """Calculate stock status based on current and safety stock levels"""
    if current_stock <= 0:
        return 'OUT_OF_STOCK'
    elif current_stock <= safety_stock:
        return 'LOW'
    elif current_stock <= safety_stock * 1.5:
        return 'MEDIUM'
    else:
        return 'HIGH'

def validate_positive_integer(value: Any, field_name: str) -> int:
    """Validate and convert value to positive integer"""
    try:
        int_value = int(value)
        if int_value < 0:
            raise ValueError(f"{field_name} must be non-negative")
        return int_value
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid {field_name}: {value}") from e

def memory_efficient_batch(items: list, batch_size: int = 10):
    """Generator for memory-efficient batch processing on t2.micro"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]