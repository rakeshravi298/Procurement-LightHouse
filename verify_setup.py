#!/usr/bin/env python3
"""
Setup verification script - checks if system is properly configured
"""
import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Need Python 3.8+")
        return False

def check_project_structure():
    """Check project structure"""
    required_files = [
        'procurement_lighthouse/__init__.py',
        'procurement_lighthouse/config.py',
        'procurement_lighthouse/database/connection.py',
        'procurement_lighthouse/database/schema.sql',
        'procurement_lighthouse/events/listener.py',
        'procurement_lighthouse/events/processor.py',
        'procurement_lighthouse/simulator/inventory.py',
        'procurement_lighthouse/simulator/purchase_orders.py',
        'requirements.txt',
        'README.md'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if not missing_files:
        print(f"✅ Project structure complete ({len(required_files)} files)")
        return True
    else:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False

def check_dependencies():
    """Check if dependencies can be imported"""
    required_modules = [
        'psycopg2',
        'flask', 
        'sklearn',
        'joblib',
        'numpy',
        'pandas'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if not missing_modules:
        print(f"✅ All dependencies available")
        return True
    else:
        print(f"❌ Missing dependencies: {', '.join(missing_modules)}")
        print("   Install with: pip install -r requirements.txt")
        return False

def check_configuration():
    """Check configuration files"""
    try:
        # Try to import config without database connection
        sys.path.insert(0, '.')
        from procurement_lighthouse.config import config
        
        print("✅ Configuration loaded successfully")
        print(f"   Database: {config.database.host}:{config.database.port}/{config.database.database}")
        print(f"   Event channels: {len(config.events.event_channels)}")
        print(f"   Simulator intervals: {config.simulator.inventory_event_interval}s / {config.simulator.po_event_interval}s")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def check_database_schema():
    """Check database schema file"""
    schema_file = Path('procurement_lighthouse/database/schema.sql')
    
    if not schema_file.exists():
        print("❌ Database schema file missing")
        return False
    
    try:
        content = schema_file.read_text()
        
        # Check for key components
        required_elements = [
            'CREATE TABLE IF NOT EXISTS inventory',
            'CREATE TABLE IF NOT EXISTS purchase_orders', 
            'CREATE TABLE IF NOT EXISTS alerts',
            'CREATE TABLE IF NOT EXISTS event_log',
            'notify_inventory_change',
            'notify_po_change',
            'trigger_inventory_change',
            'trigger_po_change'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if not missing_elements:
            print(f"✅ Database schema complete ({len(required_elements)} elements)")
            return True
        else:
            print(f"❌ Schema missing: {', '.join(missing_elements)}")
            return False
            
    except Exception as e:
        print(f"❌ Error reading schema: {e}")
        return False

def main():
    """Run setup verification"""
    print("🔍 Procurement Lighthouse Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Project Structure", check_project_structure),
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Database Schema", check_database_schema)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 Setup verification passed!")
        print("\nNext steps:")
        print("1. Install PostgreSQL and configure database")
        print("2. Run: python3 -m procurement_lighthouse.main setup")
        print("3. Start services:")
        print("   Terminal 1: python3 -m procurement_lighthouse.main events")
        print("   Terminal 2: python3 -m procurement_lighthouse.main simulate")
        print("4. Run validation: python3 validate_system.py")
    else:
        print("⚠️  Setup verification failed!")
        print("Please fix the issues above before proceeding.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)