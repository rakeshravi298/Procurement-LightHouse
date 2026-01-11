"""
Database setup and initialization
"""
import logging
import os
from pathlib import Path

from .connection import db

logger = logging.getLogger(__name__)

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to default postgres database to create our database
        import psycopg2
        from ..config import config
        
        conn_params = {
            'host': config.database.host,
            'port': config.database.port,
            'database': 'postgres',  # Connect to default database
            'user': config.database.username,
            'password': config.database.password
        }
        
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (config.database.database,)
            )
            
            if not cursor.fetchone():
                cursor.execute(f'CREATE DATABASE "{config.database.database}"')
                logger.info(f"Database '{config.database.database}' created")
            else:
                logger.info(f"Database '{config.database.database}' already exists")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise

def initialize_schema():
    """Initialize database schema from SQL file"""
    try:
        schema_path = Path(__file__).parent / 'schema.sql'
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema in chunks to handle multiple statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        with db.cursor() as cursor:
            for statement in statements:
                if statement:
                    cursor.execute(statement)
        
        logger.info("Database schema initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize schema: {e}")
        raise

def seed_demo_data():
    """Insert minimal demo data for PoC"""
    try:
        # Sample inventory items (small dataset for t2.micro)
        inventory_data = [
            ('Steel Bolts M8', 150, 50, 0.25, 'Warehouse A'),
            ('Steel Bolts M10', 75, 30, 0.35, 'Warehouse A'),
            ('Aluminum Sheets 2mm', 25, 10, 15.50, 'Warehouse B'),
            ('Copper Wire 12AWG', 200, 75, 2.10, 'Warehouse A'),
            ('Plastic Connectors', 300, 100, 0.15, 'Warehouse C'),
            ('Rubber Gaskets', 80, 25, 1.25, 'Warehouse B'),
            ('Stainless Screws M6', 400, 150, 0.08, 'Warehouse A'),
            ('Electrical Tape', 60, 20, 3.50, 'Warehouse C'),
            ('Heat Shrink Tubing', 120, 40, 0.75, 'Warehouse B'),
            ('Cable Ties', 500, 200, 0.05, 'Warehouse C')
        ]
        
        with db.cursor() as cursor:
            # Clear existing demo data
            cursor.execute("DELETE FROM consumption_history")
            cursor.execute("DELETE FROM po_line_items")
            cursor.execute("DELETE FROM purchase_orders")
            cursor.execute("DELETE FROM forecasts")
            cursor.execute("DELETE FROM alerts")
            cursor.execute("DELETE FROM inventory")
            
            # Insert inventory items
            for item in inventory_data:
                cursor.execute("""
                    INSERT INTO inventory (item_name, current_stock, safety_stock, unit_cost, location)
                    VALUES (%s, %s, %s, %s, %s)
                """, item)
            
            # Insert sample purchase orders
            po_data = [
                ('Acme Steel Supply', 'approved', '2024-01-15', 1250.00),
                ('Metro Materials', 'shipped', '2024-01-12', 875.50),
                ('Industrial Parts Co', 'created', '2024-01-18', 650.25),
                ('Quality Components', 'received', '2024-01-10', 2100.75)
            ]
            
            for po in po_data:
                cursor.execute("""
                    INSERT INTO purchase_orders (supplier_name, status, expected_delivery, total_value)
                    VALUES (%s, %s, %s, %s)
                """, po)
            
            # Insert some PO line items
            cursor.execute("""
                INSERT INTO po_line_items (po_id, item_id, quantity_ordered, unit_price, quantity_received)
                SELECT 1, 1, 200, 0.25, 0 UNION ALL
                SELECT 1, 2, 100, 0.35, 0 UNION ALL
                SELECT 2, 3, 10, 15.50, 10 UNION ALL
                SELECT 2, 4, 50, 2.10, 50 UNION ALL
                SELECT 3, 5, 150, 0.15, 0 UNION ALL
                SELECT 4, 6, 100, 1.25, 100
            """)
            
            # Insert some consumption history
            cursor.execute("""
                INSERT INTO consumption_history (item_id, quantity_consumed, consumption_reason, department)
                SELECT 1, 25, 'Production', 'Manufacturing' UNION ALL
                SELECT 2, 15, 'Maintenance', 'Facilities' UNION ALL
                SELECT 4, 30, 'Production', 'Manufacturing' UNION ALL
                SELECT 5, 45, 'Assembly', 'Manufacturing' UNION ALL
                SELECT 7, 60, 'Production', 'Manufacturing'
            """)
            
            # Insert sample alerts for items below safety stock
            cursor.execute("""
                INSERT INTO alerts (alert_type, severity, item_id, message)
                SELECT 'stock_low', 'high', item_id, 
                       'Stock level (' || current_stock || ') below safety stock (' || safety_stock || ')'
                FROM inventory 
                WHERE current_stock <= safety_stock
            """)
        
        logger.info("Demo data seeded successfully")
        
    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")
        raise

def setup_database():
    """Complete database setup process"""
    logger.info("Starting database setup...")
    
    try:
        create_database()
        initialize_schema()
        seed_demo_data()
        logger.info("Database setup completed successfully")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_database()