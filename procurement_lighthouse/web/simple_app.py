"""
Simple Flask web application for Procurement Lighthouse PoC
"""
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configure for t2.micro constraints
    app.config.update(
        SECRET_KEY='procurement-lighthouse-dev-key',
        JSON_SORT_KEYS=False,
        JSONIFY_PRETTYPRINT_REGULAR=False,
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )
    
    @app.route('/health')
    def health_check():
        """Simple health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'not_connected'
        })
    
    @app.route('/')
    def dashboard():
        """Main dashboard page"""
        try:
            system_status = {
                'database': 'not_connected',
                'inventory_count': 0,
                'active_alerts': 0,
                'recent_events': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            return render_template('dashboard.html',
                                 system_status=system_status,
                                 recent_alerts=[],
                                 ml_status={'service_running': False, 'models_available': False},
                                 alert_summary={'total_active': 0})
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return render_template('error.html', error=str(e)), 500
    
    @app.route('/api/system/status')
    def api_system_status():
        """Get system status"""
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'database': 'not_connected',
            'inventory_count': 0,
            'active_alerts': 0,
            'ml_models_available': False,
            'recent_events': 0
        })
    
    @app.route('/api/inventory')
    def api_inventory():
        """Get inventory status"""
        return jsonify({
            'inventory': [],
            'count': 0,
            'timestamp': datetime.now().isoformat(),
            'message': 'Database not connected - demo mode'
        })
    
    @app.route('/api/alerts')
    def api_alerts():
        """Get active alerts"""
        return jsonify({
            'active_alerts': [],
            'summary': {'total_active': 0},
            'timestamp': datetime.now().isoformat(),
            'message': 'Database not connected - demo mode'
        })
    
    @app.route('/api/ml/status')
    def api_ml_status():
        """Get ML service status"""
        return jsonify({
            'service_running': False,
            'models_available': False,
            'message': 'ML service not connected - demo mode'
        })
    
    @app.route('/api/ml/batch', methods=['POST'])
    def api_ml_batch():
        """Run batch ML inference"""
        return jsonify({
            'status': 'demo_mode',
            'message': 'ML batch inference not available in demo mode',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/system/start-simulation', methods=['POST'])
    def api_start_simulation():
        """Start data simulation"""
        return jsonify({
            'status': 'demo_mode',
            'message': 'Use CLI to start simulation: python -m procurement_lighthouse.main simulate',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/system/start-events', methods=['POST'])
    def api_start_events():
        """Start event processing"""
        return jsonify({
            'status': 'demo_mode',
            'message': 'Use CLI to start events: python -m procurement_lighthouse.main events',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error="Page not found", 
                             error_code=404), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html', 
                             error="Internal server error", 
                             error_code=500), 500
    
    return app

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)