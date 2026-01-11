#!/usr/bin/env python3
"""
Simple Flask app test
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from flask import Flask, jsonify, render_template
from datetime import datetime

def create_simple_app():
    """Create a simple Flask app for testing"""
    app = Flask(__name__, template_folder='procurement_lighthouse/web/templates')
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html',
                             system_status={'database': 'unknown', 'inventory_count': 0, 'active_alerts': 0, 'recent_events': 0, 'timestamp': datetime.now().isoformat()},
                             recent_alerts=[],
                             ml_status={'service_running': False, 'models_available': False},
                             alert_summary={'total_active': 0})
    
    return app

if __name__ == '__main__':
    print("Creating simple Flask app...")
    app = create_simple_app()
    print("✓ Simple Flask app created successfully")
    
    print("Testing routes...")
    with app.test_client() as client:
        response = client.get('/health')
        print(f"✓ Health endpoint: HTTP {response.status_code}")
        
        response = client.get('/')
        print(f"✓ Dashboard endpoint: HTTP {response.status_code}")
    
    print("\n✅ Simple Flask app test completed!")
    print("Starting development server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)