#!/bin/bash
# EC2 setup script for Procurement Lighthouse PoC
# Optimized for AWS t2.micro Free Tier

set -e

echo "=== Procurement Lighthouse PoC - EC2 Setup ==="
echo "Optimizing for t2.micro (1 vCPU, 1GB RAM)"

# Update system
sudo yum update -y

# Install Python 3.9 and pip
sudo yum install -y python3 python3-pip git

# Install PostgreSQL 13
sudo yum install -y postgresql13-server postgresql13-devel

# Initialize PostgreSQL
sudo /usr/pgsql-13/bin/postgresql-13-setup initdb

# Configure PostgreSQL for t2.micro
sudo tee /var/lib/pgsql/13/data/postgresql.conf.custom << EOF
# t2.micro optimizations (1GB RAM)
shared_buffers = 128MB
effective_cache_size = 512MB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 20
wal_buffers = 16MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1
effective_io_concurrency = 200
EOF

# Append custom config to main config
sudo bash -c 'cat /var/lib/pgsql/13/data/postgresql.conf.custom >> /var/lib/pgsql/13/data/postgresql.conf'

# Configure PostgreSQL authentication
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /var/lib/pgsql/13/data/postgresql.conf
sudo sed -i "s/ident/md5/g" /var/lib/pgsql/13/data/pg_hba.conf

# Start and enable PostgreSQL
sudo systemctl start postgresql-13
sudo systemctl enable postgresql-13

# Create database user
sudo -u postgres psql -c "CREATE USER procurement_user WITH PASSWORD 'procurement_pass';"
sudo -u postgres psql -c "ALTER USER procurement_user CREATEDB;"

# Install Grafana OSS
sudo tee /etc/yum.repos.d/grafana.repo << EOF
[grafana]
name=grafana
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF

sudo yum install -y grafana

# Configure Grafana for t2.micro
sudo tee /etc/grafana/grafana.ini.custom << EOF
[server]
http_port = 3000
domain = localhost

[database]
type = sqlite3
path = grafana.db

[analytics]
reporting_enabled = false
check_for_updates = false

[security]
admin_user = admin
admin_password = admin

[users]
allow_sign_up = false

[auth.anonymous]
enabled = false
EOF

# Backup original and use custom config
sudo cp /etc/grafana/grafana.ini /etc/grafana/grafana.ini.backup
sudo cp /etc/grafana/grafana.ini.custom /etc/grafana/grafana.ini

# Start and enable Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Create application directory
sudo mkdir -p /opt/procurement_lighthouse
sudo chown ec2-user:ec2-user /opt/procurement_lighthouse

# Create models directory
sudo mkdir -p /opt/procurement_lighthouse/models
sudo chown ec2-user:ec2-user /opt/procurement_lighthouse/models

# Create log directory
sudo mkdir -p /var/log/procurement_lighthouse
sudo chown ec2-user:ec2-user /var/log/procurement_lighthouse

# Set environment variables
sudo tee /etc/environment << EOF
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
EOF

echo "=== EC2 Setup Complete ==="
echo "Next steps:"
echo "1. Clone your application code to /opt/procurement_lighthouse"
echo "2. Install Python dependencies: pip3 install -r requirements.txt"
echo "3. Run setup: python3 -m procurement_lighthouse.main setup"
echo "4. Configure security groups to allow ports 8080 (web) and 3000 (Grafana)"
echo ""
echo "Services status:"
echo "- PostgreSQL: $(sudo systemctl is-active postgresql-13)"
echo "- Grafana: $(sudo systemctl is-active grafana-server)"