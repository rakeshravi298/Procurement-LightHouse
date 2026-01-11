# Procurement Lighthouse PoC

An event-driven procurement control tower system optimized for AWS t2.micro Free Tier deployment.

## Architecture Overview

- **Event-Driven**: Uses PostgreSQL LISTEN/NOTIFY for real-time event processing
- **Single Instance**: All components run on one EC2 t2.micro instance
- **Lightweight**: Optimized for 1 vCPU, 1GB RAM constraints
- **Zero Cost**: Runs entirely within AWS Free Tier limits

## Components

- **PostgreSQL**: Event bus and data storage with optimized settings
- **Python Event Processor**: Real-time event handling and ML inference
- **Data Simulator**: Generates realistic ERP-like events
- **Flask Web Server**: Simple web interface and API endpoints
- **Grafana OSS**: Real-time dashboards and visualization
- **ML Engine**: Lightweight forecasting and risk assessment

## Quick Start

### 1. EC2 Instance Setup

Launch an AWS t2.micro instance with Amazon Linux 2 and run:

```bash
# Download and run setup script
curl -O https://raw.githubusercontent.com/your-repo/procurement-lighthouse/main/deploy/ec2_setup.sh
chmod +x ec2_setup.sh
sudo ./ec2_setup.sh
```

### 2. Application Deployment

```bash
# Clone repository
cd /opt/procurement_lighthouse
git clone https://github.com/your-repo/procurement-lighthouse.git .

# Install Python dependencies
pip3 install -r requirements.txt

# Setup database and seed demo data
python3 -m procurement_lighthouse.main setup

# Check system status
python3 -m procurement_lighthouse.main status
```

### 3. Start Services

The system requires two services to run:

```bash
# Terminal 1: Start event processing service
python3 -m procurement_lighthouse.main events

# Terminal 2: Start data simulation service  
python3 -m procurement_lighthouse.main simulate
```

### 4. Security Group Configuration

### 4. Start Services

The system requires multiple services to run:

```bash
# Terminal 1: Start event processing service
python3 -m procurement_lighthouse.main events

# Terminal 2: Start data simulation service  
python3 -m procurement_lighthouse.main simulate

# Terminal 3: Start web server
python3 -m procurement_lighthouse.main web
```

### 5. Security Group Configuration

Configure your EC2 security group to allow:
- Port 5000 (Web Interface)
- Port 3000 (Grafana)
- Port 22 (SSH)

## Services

### Event Processing Service
Listens to PostgreSQL LISTEN/NOTIFY events and processes them in real-time:
- Inventory change processing
- Purchase order status updates
- Alert generation and management
- KPI calculations and metrics

### Data Simulation Service
Generates realistic ERP-like events for demonstration:
- **Inventory Simulator**: Consumption, receipts, and adjustments
- **PO Simulator**: Creates POs for low stock items and advances PO lifecycle

### Service Commands
```bash
# Start event processing
python3 -m procurement_lighthouse.main events

# Start data simulation
python3 -m procurement_lighthouse.main simulate

# Start web server
python3 -m procurement_lighthouse.main web

# Initialize Grafana dashboards
python3 -m procurement_lighthouse.main grafana init

# Check Grafana status
python3 -m procurement_lighthouse.main grafana status

# Check system status
python3 -m procurement_lighthouse.main status

# View alerts dashboard
python3 -m procurement_lighthouse.main alerts

# ML operations
python3 -m procurement_lighthouse.main ml status
python3 -m procurement_lighthouse.main ml batch

# Grafana dashboard management
python3 -m procurement_lighthouse.main grafana init
python3 -m procurement_lighthouse.main grafana status
python3 -m procurement_lighthouse.main grafana dashboards

# Setup database
python3 -m procurement_lighthouse.main setup
```

## Project Structure

```
procurement_lighthouse/
├── __init__.py
├── config.py              # Configuration settings
├── main.py                # Main entry point
├── utils.py               # Utility functions
├── database/
│   ├── __init__.py
│   ├── connection.py      # Database connection management
│   ├── schema.sql         # Database schema and triggers
│   └── setup.py           # Database initialization
├── events/                # Event processing (Task 2)
├── simulator/             # Data simulation (Task 3)
├── ml/                    # ML inference engine (Tasks 6-7)
└── web/                   # Web server (Task 8)
```

## Configuration

Environment variables (set in `/etc/environment`):

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=procurement_lighthouse
DB_USER=procurement_user
DB_PASSWORD=procurement_pass
MODELS_PATH=/opt/procurement_lighthouse/models
WEB_HOST=0.0.0.0
WEB_PORT=8080
GRAFANA_HOST=localhost
GRAFANA_PORT=3000
```

## Database Schema

### Core Tables
- `inventory` - Current stock levels and safety stock
- `purchase_orders` - PO status and delivery information
- `po_line_items` - PO line item details
- `consumption_history` - Material consumption tracking
- `forecasts` - ML predictions and confidence intervals
- `alerts` - System alerts and exceptions

### Event System
- PostgreSQL triggers automatically emit events on data changes
- Event channels: `inventory_changed`, `po_status_changed`, `alert_generated`, `forecast_updated`
- Real-time processing without polling or batch jobs

## Performance Optimizations for t2.micro

### PostgreSQL Settings
- `shared_buffers = 128MB`
- `max_connections = 20`
- `effective_cache_size = 512MB`
- `work_mem = 4MB`

### Application Optimizations
- Single database connection (no pooling)
- Conservative event generation frequencies
- Lightweight ML models (<10MB)
- Memory-efficient batch processing
- File-based logging to reduce I/O

## Accessing the System

### Web Interface
- URL: `http://your-ec2-ip:5000`
- Provides system dashboard with real-time status
- API endpoints for inventory, alerts, and ML data
- System control interface for starting services

### Grafana Dashboards
- URL: `http://your-ec2-ip:3000`
- Username: `admin`
- Password: `admin`
- **4 Pre-configured Dashboards**:
  - **Overview**: System status, inventory levels, alert distribution
  - **Inventory**: Low stock items, consumption trends, stock distribution
  - **Alerts**: Active alerts, alert frequency, resolution times
  - **ML Predictions**: High-risk items, forecast accuracy, consumption vs forecast
- Auto-refresh every 15 seconds (optimized for t2.micro)
- PostgreSQL datasource with connection pooling limits

## Development

### Running Tests
```bash
# Install test dependencies
pip3 install pytest hypothesis

# Run tests (when implemented)
python3 -m pytest
```

### Adding New Components
1. Create module in appropriate directory
2. Update configuration in `config.py`
3. Add database schema changes to `schema.sql`
4. Update main entry point if needed

## Monitoring

### Logs
- Application logs: `/var/log/procurement_lighthouse.log`
- PostgreSQL logs: `/var/lib/pgsql/13/data/log/`
- Grafana logs: `/var/log/grafana/`

### System Health
```bash
# Check service status
sudo systemctl status postgresql-13
sudo systemctl status grafana-server

# Check application status
python3 -m procurement_lighthouse.main status
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL service: `sudo systemctl status postgresql-13`
   - Verify credentials in environment variables
   - Check pg_hba.conf authentication settings

2. **Out of Memory**
   - Monitor with `free -h` and `top`
   - Reduce event generation frequency
   - Check for memory leaks in long-running processes

3. **Grafana Not Accessible**
   - Check service: `sudo systemctl status grafana-server`
   - Verify security group allows port 3000
   - Check firewall settings

### Performance Monitoring
```bash
# Monitor memory usage
free -h

# Monitor CPU usage
top

# Monitor disk usage
df -h

# Monitor PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

## License

MIT License - See LICENSE file for details.

## Support

For issues and questions, please check the troubleshooting section or create an issue in the repository.