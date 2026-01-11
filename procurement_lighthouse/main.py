"""
Main entry point for Procurement Lighthouse PoC
"""
import sys
import logging
import argparse
from pathlib import Path

from .utils import setup_logging
from .database.setup import setup_database
from .config import config

logger = logging.getLogger(__name__)

def setup_command():
    """Setup database and initialize system"""
    logger.info("Setting up Procurement Lighthouse PoC...")
    try:
        setup_database()
        logger.info("Setup completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return 1

def alerts_command():
    """Show alert dashboard information"""
    logger.info("Alert Dashboard")
    try:
        from .alerts.service import alert_service
        
        # Get alert dashboard data
        dashboard_data = alert_service.get_alert_dashboard_data()
        
        if not dashboard_data:
            logger.error("Could not retrieve alert data")
            return 1
        
        summary = dashboard_data.get('summary', {})
        active_alerts = dashboard_data.get('active_alerts', [])
        
        # Display summary
        logger.info("=== Alert Summary ===")
        logger.info(f"Total Active Alerts: {summary.get('total_active', 0)}")
        
        severity_counts = summary.get('active_by_severity', {})
        if severity_counts:
            logger.info("By Severity:")
            for severity in ['critical', 'high', 'medium', 'low']:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    logger.info(f"  {severity.title()}: {count}")
        
        type_counts = summary.get('active_by_type', {})
        if type_counts:
            logger.info("By Type:")
            for alert_type, count in type_counts.items():
                logger.info(f"  {alert_type.replace('_', ' ').title()}: {count}")
        
        # Display recent active alerts
        if active_alerts:
            logger.info("\n=== Recent Active Alerts ===")
            for alert in active_alerts[:10]:  # Show top 10
                item_name = alert.get('item_name', 'N/A')
                supplier_name = alert.get('supplier_name', 'N/A')
                context = item_name if item_name != 'N/A' else supplier_name
                
                logger.info(f"[{alert['severity'].upper()}] {alert['alert_type'].replace('_', ' ').title()}")
                logger.info(f"  {context}: {alert['message']}")
                logger.info(f"  Created: {alert['created_at']}")
                logger.info("")
        else:
            logger.info("\n✅ No active alerts")
        
        return 0
        
    except Exception as e:
        logger.error(f"Alert command failed: {e}")
        return 1

def simulate_command():
    """Start data simulation service"""
    logger.info("Starting data simulation service...")
    try:
        from .simulator.service import DataSimulationService
        
        service = DataSimulationService()
        service.start()
        return 0
        
    except Exception as e:
        logger.error(f"Data simulation service failed: {e}")
        return 1

def events_command():
    """Start event processing service"""
    logger.info("Starting event processing service...")
    try:
        from .events.service import EventProcessingService
        
        service = EventProcessingService()
        service.start()
        return 0
        
    except Exception as e:
        logger.error(f"Event processing service failed: {e}")
        return 1

def status_command():
    """Check system status"""
    logger.info("Checking system status...")
    try:
        from .database.connection import db
        
        # Test database connection
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as item_count FROM inventory")
            result = cursor.fetchone()
            logger.info(f"Database connection: OK (Items: {result['item_count']})")
            
            # Check recent events
            cursor.execute("""
                SELECT COUNT(*) as event_count 
                FROM event_log 
                WHERE processed_at > NOW() - INTERVAL '1 hour'
            """)
            event_result = cursor.fetchone()
            logger.info(f"Recent events (1h): {event_result['event_count']}")
            
            # Check active alerts
            cursor.execute("SELECT COUNT(*) as alert_count FROM alerts WHERE status = 'active'")
            alert_result = cursor.fetchone()
            logger.info(f"Active alerts: {alert_result['alert_count']}")
        
        # Check if models directory exists
        models_path = Path(config.ml.models_path)
        if models_path.exists():
            logger.info(f"Models directory: OK ({models_path})")
        else:
            logger.warning(f"Models directory not found: {models_path}")
        
        # Check event processing service status
        try:
            from .events.service import EventProcessingService
            service = EventProcessingService()
            status = service.get_status()
            logger.info(f"Event processing: {'Running' if status['service_running'] else 'Stopped'}")
            if status['processing_stats']['events_processed'] > 0:
                logger.info(f"Events processed: {status['processing_stats']['events_processed']}")
        except Exception as e:
            logger.warning(f"Could not check event processing status: {e}")
        
        # Check data simulation service status
        try:
            from .simulator.service import DataSimulationService
            sim_service = DataSimulationService()
            sim_status = sim_service.get_status()
            logger.info(f"Data simulation: {'Running' if sim_status['service_running'] else 'Stopped'}")
            logger.info(f"Inventory simulator: {'Running' if sim_status['inventory_simulator']['running'] else 'Stopped'}")
            logger.info(f"PO simulator: {'Running' if sim_status['po_simulator']['running'] else 'Stopped'}")
        except Exception as e:
            logger.warning(f"Could not check simulation status: {e}")
        
        logger.info("System status check completed")
        return 0
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return 1

def alerts_command():
    """Show alert dashboard"""
    logger.info("Alert Dashboard")
    try:
        from .alerts.service import alert_service
        
        # Get alert dashboard data
        dashboard_data = alert_service.get_alert_dashboard_data()
        
        # Display summary
        summary = dashboard_data.get('summary', {})
        print(f"Active Alerts Summary:")
        print(f"  Total active: {summary.get('total_active', 0)}")
        
        severity_counts = summary.get('active_by_severity', {})
        for severity in ['critical', 'high', 'medium', 'low']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity.capitalize()}: {count}")
        
        # Display recent alerts
        active_alerts = dashboard_data.get('active_alerts', [])[:10]
        if active_alerts:
            print(f"\nRecent Active Alerts:")
            for alert in active_alerts:
                created = alert['created_at'].strftime('%Y-%m-%d %H:%M')
                print(f"  [{alert['severity'].upper()}] {alert['message']} ({created})")
        else:
            print("\nNo active alerts")
        
        # Display processing stats
        stats = dashboard_data.get('processing_stats', {})
        print(f"\nAlert Processing Stats:")
        print(f"  Alerts generated: {stats.get('alerts_generated', 0)}")
        print(f"  Alerts resolved: {stats.get('alerts_resolved', 0)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Alert dashboard failed: {e}")
        return 1

def web_command():
    """Start web server"""
    logger.info("Starting web server...")
    try:
        # Try to import the full app first, fall back to simple app
        try:
            from .web.app import app
            logger.info("Using full web application with database integration")
        except ImportError as e:
            logger.warning(f"Full app not available ({e}), using simple demo app")
            from .web.simple_app import app
        
        # Run the Flask development server
        # For production, use a proper WSGI server like gunicorn
        logger.info("Web server starting on http://0.0.0.0:5000")
        logger.info("Access the dashboard at: http://localhost:5000")
        
        app.run(host='0.0.0.0', port=5000, debug=False)
        return 0
        
    except Exception as e:
        logger.error(f"Web server failed: {e}")
        return 1

def grafana_command(remaining_args=None):
    """Grafana dashboard management commands"""
    if not remaining_args or len(remaining_args) < 1:
        print("Grafana commands:")
        print("  python -m procurement_lighthouse.main grafana status     - Show Grafana service status")
        print("  python -m procurement_lighthouse.main grafana init      - Initialize Grafana with dashboards")
        print("  python -m procurement_lighthouse.main grafana dashboards - List dashboard URLs")
        print("  python -m procurement_lighthouse.main grafana refresh   - Refresh all dashboards")
        print("  python -m procurement_lighthouse.main grafana test      - Test datasource connection")
        return 1
    
    grafana_subcommand = remaining_args[0]
    
    try:
        if grafana_subcommand == 'status':
            from .grafana.service import grafana_service
            status = grafana_service.get_status()
            
            print("Grafana Service Status:")
            print(f"  Service running: {'✓' if status['service_running'] else '✗'}")
            print(f"  Initialized: {'✓' if status['initialized'] else '✗'}")
            print(f"  Grafana URL: {status['grafana_url']}")
            print(f"  Datasource configured: {'✓' if status['datasource_configured'] else '✗'}")
            print(f"  Dashboard count: {status['dashboard_count']}")
            print(f"  Admin user: {status['admin_user']}")
            print(f"  Overall status: {status['status']}")
            
            if status.get('error'):
                print(f"  Error: {status['error']}")
        
        elif grafana_subcommand == 'init':
            from .grafana.service import grafana_service
            print("Initializing Grafana service...")
            
            if grafana_service.initialize():
                print("✓ Grafana service initialized successfully")
                
                # Show dashboard URLs
                dashboard_urls = grafana_service.get_dashboard_urls()
                if dashboard_urls:
                    print("\nAvailable dashboards:")
                    for dashboard in dashboard_urls:
                        print(f"  • {dashboard['title']}: {dashboard['url']}")
                
                # Show data summary
                data_summary = grafana_service.get_dashboard_data_summary()
                if data_summary:
                    print(f"\nData available for visualization:")
                    print(f"  Inventory items: {data_summary.get('inventory_items', 0)}")
                    print(f"  Active alerts: {data_summary.get('active_alerts', 0)}")
                    print(f"  Recent events: {data_summary.get('recent_events', 0)}")
                    print(f"  Purchase orders: {data_summary.get('purchase_orders', 0)}")
                    print(f"  ML forecasts: {data_summary.get('forecasts', 0)}")
            else:
                print("✗ Failed to initialize Grafana service")
                return 1
        
        elif grafana_subcommand == 'dashboards':
            from .grafana.service import grafana_service
            dashboard_urls = grafana_service.get_dashboard_urls()
            
            if dashboard_urls:
                print("Available Grafana dashboards:")
                for dashboard in dashboard_urls:
                    tags = ', '.join(dashboard['tags']) if dashboard['tags'] else 'No tags'
                    print(f"  • {dashboard['title']}")
                    print(f"    URL: {dashboard['url']}")
                    print(f"    Tags: {tags}")
                    print()
            else:
                print("No dashboards found. Run 'grafana init' to create them.")
        
        elif grafana_subcommand == 'refresh':
            from .grafana.service import grafana_service
            print("Refreshing Grafana dashboards...")
            
            if grafana_service.refresh_dashboards():
                print("✓ Dashboards refreshed successfully")
            else:
                print("✗ Failed to refresh dashboards")
                return 1
        
        elif grafana_subcommand == 'test':
            from .grafana.service import grafana_service
            print("Testing Grafana datasource connection...")
            
            if grafana_service.test_datasource_connection():
                print("✓ Datasource connection test passed")
            else:
                print("✗ Datasource connection test failed")
                return 1
        
        else:
            print(f"Unknown Grafana command: {grafana_subcommand}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Grafana command failed: {e}")
        return 1

def ml_command(remaining_args=None):
    """ML inference and model management commands"""
    if not remaining_args or len(remaining_args) < 1:
        print("ML commands:")
        print("  python -m procurement_lighthouse.main ml validate    - Validate ML models")
        print("  python -m procurement_lighthouse.main ml predict <item_id>  - Run prediction for item")
        print("  python -m procurement_lighthouse.main ml batch      - Run batch inference")
        print("  python -m procurement_lighthouse.main ml status     - Show ML service status")
        print("  python -m procurement_lighthouse.main ml dashboard  - Show ML dashboard data")
        return 1
    
    ml_subcommand = remaining_args[0]
    
    try:
        if ml_subcommand == 'validate':
            from .ml.service import ml_service
            result = ml_service.validate_models()
            print(f"Model validation: {'✓ All valid' if result['all_models_valid'] else '✗ Issues found'}")
            for model_name, validation in result['model_results'].items():
                status = '✓' if validation['valid'] else '✗'
                print(f"  {status} {model_name}")
                if validation.get('errors'):
                    for error in validation['errors']:
                        print(f"    Error: {error}")
                if validation.get('warnings'):
                    for warning in validation['warnings']:
                        print(f"    Warning: {warning}")
        
        elif ml_subcommand == 'predict':
            if len(remaining_args) < 2:
                print("Usage: python -m procurement_lighthouse.main ml predict <item_id>")
                return 1
            
            try:
                item_id = int(remaining_args[1])
                from .ml.inference import ml_inference
                
                print(f"Running ML predictions for item {item_id}...")
                
                # Consumption forecast
                consumption_result = ml_inference.predict_consumption(item_id)
                if consumption_result:
                    print(f"Consumption forecast: {consumption_result['predicted_consumption']} units (confidence: {consumption_result['confidence_score']:.1%})")
                else:
                    print("Consumption forecast: Failed")
                
                # Stockout risk
                risk_result = ml_inference.predict_stockout_risk(item_id)
                if risk_result:
                    print(f"Stockout risk: {risk_result['risk_level']} ({risk_result['risk_probability']:.1%})")
                    if risk_result['days_until_stockout']:
                        print(f"Days until stockout: ~{risk_result['days_until_stockout']}")
                else:
                    print("Stockout risk: Failed")
                    
            except ValueError:
                print("Error: item_id must be a number")
                return 1
        
        elif ml_subcommand == 'batch':
            from .ml.service import ml_service
            print("Running batch ML inference...")
            result = ml_service.run_batch_inference(force=True)
            
            if result.get('completed'):
                print(f"Batch inference completed:")
                print(f"  Items processed: {result['items_processed']}")
                print(f"  Consumption forecasts: {result['consumption_forecasts']}")
                print(f"  Risk assessments: {result['risk_assessments']}")
                print(f"  Alerts generated: {result['alerts_generated']}")
                print(f"  Processing time: {result['processing_time_seconds']:.1f}s")
            else:
                print(f"Batch inference failed: {result.get('error', 'Unknown error')}")
        
        elif ml_subcommand == 'status':
            from .ml.service import ml_service
            status = ml_service.get_service_status()
            
            print("ML Service Status:")
            print(f"  Service running: {'✓' if status['service_running'] else '✗'}")
            print(f"  Models available: {'✓' if status['models_available'] else '✗'}")
            print(f"  Predictions made: {status['service_stats']['successful_predictions']}")
            print(f"  Failed predictions: {status['service_stats']['failed_predictions']}")
            print(f"  Last batch run: {status['last_batch_run'] or 'Never'}")
            
            cache_status = status.get('model_cache', {})
            print(f"  Cached models: {cache_status.get('cached_models', 0)}/{cache_status.get('max_cache_size', 0)}")
            print(f"  Memory usage: {cache_status.get('estimated_memory_mb', 0):.1f}MB")
        
        elif ml_subcommand == 'dashboard':
            from .ml.service import ml_service
            dashboard_data = ml_service.get_ml_dashboard_data()
            
            print("ML Dashboard Data:")
            print(f"  Recent forecasts: {len(dashboard_data.get('recent_forecasts', []))}")
            print(f"  High risk items: {len(dashboard_data.get('high_risk_items', []))}")
            
            # Show high risk items
            high_risk = dashboard_data.get('high_risk_items', [])[:5]
            if high_risk:
                print("\n  Top high-risk items:")
                for item in high_risk:
                    print(f"    {item['item_name']}: {item['risk_level']} ({item['risk_probability']:.1%})")
        
        else:
            print(f"Unknown ML command: {ml_subcommand}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"ML command failed: {e}")
        return 1

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Procurement Lighthouse PoC")
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    subparsers.add_parser('setup', help='Setup database and initialize system')
    
    # Status command
    subparsers.add_parser('status', help='Check system status')
    
    # Events command
    subparsers.add_parser('events', help='Start event processing service')
    
    # Simulate command
    subparsers.add_parser('simulate', help='Start data simulation service')
    
    # Alerts command
    subparsers.add_parser('alerts', help='Show alert dashboard')
    
    # ML command
    subparsers.add_parser('ml', help='ML inference and model management')
    
    # Grafana command
    subparsers.add_parser('grafana', help='Grafana dashboard management')
    
    # Web command
    subparsers.add_parser('web', help='Start web server')
    
    args, remaining_args = parser.parse_known_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    if args.command == 'setup':
        return setup_command()
    elif args.command == 'status':
        return status_command()
    elif args.command == 'events':
        return events_command()
    elif args.command == 'simulate':
        return simulate_command()
    elif args.command == 'alerts':
        return alerts_command()
    elif args.command == 'ml':
        # Pass remaining arguments to ml_command
        return ml_command(remaining_args)
    elif args.command == 'grafana':
        # Pass remaining arguments to grafana_command
        return grafana_command(remaining_args)
    elif args.command == 'web':
        return web_command()
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())