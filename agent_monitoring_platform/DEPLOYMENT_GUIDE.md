# Deployment Guide - Agent Monitoring Platform

## Prerequisites

- Python 3.9+
- PostgreSQL 12+ (for production)
- Docker (optional, for containerization)
- Kubernetes (optional, for orchestration)

## Local Development Setup

### 1. Clone and Install

```bash
git clone <repository>
cd agent_monitoring_platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# Database
MONITORING_DB_URL=sqlite:///monitoring.db
MONITORING_LOG_LEVEL=INFO

# Telemetry
MONITORING_EXPORT_INTERVAL=60
MONITORING_RETENTION_DAYS=90

# Alerting
SLACK_WEBHOOK_URL=

# Dashboard
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8501
```

### 3. Initialize Database

```bash
python -c "
from data_engineering.database_manager import DatabaseManager
db = DatabaseManager()
db.create_tables()
print('✅ Database initialized')
"
```

### 4. Run Examples

```bash
# Basic monitoring
python examples/basic_monitoring.py

# Full pipeline
python examples/full_pipeline.py
```

### 5. Start Dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

Visit `http://localhost:8501`

## Production Deployment

### 1. Use PostgreSQL

Update `.env`:

```bash
MONITORING_DB_URL=postgresql://user:password@db-host:5432/monitoring
MONITORING_DB_POOL_SIZE=20
MONITORING_DB_MAX_OVERFLOW=40
MONITORING_DB_SSL=true
```

### 2. Setup Database Backup

```bash
# PostgreSQL backup
pg_dump -U user -h host monitoring > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U user -h host monitoring < backup_20240101.sql
```

### 3. Configure Monitoring Stack

```bash
# Install production dependencies
pip install gunicorn uvicorn psycopg2 prometheus-client

# Create systemd service for collector
sudo tee /etc/systemd/system/monitoring-collector.service > /dev/null <<EOF
[Unit]
Description=Agent Monitoring Collector
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory=/opt/monitoring
Environment="MONITORING_DB_URL=postgresql://..."
ExecStart=/opt/monitoring/venv/bin/python -m telemetry.collector
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable monitoring-collector
sudo systemctl start monitoring-collector
```

### 4. Setup Web Server

```bash
# Create WSGI app
# wsgi.py
import streamlit
from streamlit.web import cli

def app():
    cli.main()

# Run with Gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
```

### 5. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY agent_monitoring_platform/ .

# Create non-root user
RUN useradd -m monitoring

# Switch to non-root user
USER monitoring

# Expose ports
EXPOSE 8501 8000

# Run application
CMD ["streamlit", "run", "dashboard/streamlit_app.py"]
```

Build and run:

```bash
# Build image
docker build -t monitoring-platform:latest .

# Run container
docker run -d \
  --name monitoring \
  -e MONITORING_DB_URL=postgresql://... \
  -p 8501:8501 \
  -p 8000:8000 \
  monitoring-platform:latest

# View logs
docker logs -f monitoring
```

### 6. Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: monitoring
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  monitoring:
    build: .
    depends_on:
      - postgres
    environment:
      MONITORING_DB_URL: postgresql://postgres:secure_password@postgres:5432/monitoring
      MONITORING_DB_SSL: "false"
    ports:
      - "8501:8501"
    volumes:
      - ./outputs:/app/outputs

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

volumes:
  postgres_data:
```

Deploy:

```bash
docker-compose up -d
docker-compose logs -f monitoring
```

### 7. Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: monitoring-platform
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: monitoring-platform
  template:
    metadata:
      labels:
        app: monitoring-platform
    spec:
      containers:
      - name: monitoring
        image: monitoring-platform:latest
        ports:
        - containerPort: 8501
        - containerPort: 8000
        env:
        - name: MONITORING_DB_URL
          valueFrom:
            secretKeyRef:
              name: monitoring-secrets
              key: db_url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: monitoring-platform-svc
  namespace: monitoring
spec:
  selector:
    app: monitoring-platform
  ports:
  - port: 8501
    targetPort: 8501
    name: web
  - port: 8000
    targetPort: 8000
    name: api
  type: LoadBalancer
---
apiVersion: v1
kind: Secret
metadata:
  name: monitoring-secrets
  namespace: monitoring
type: Opaque
stringData:
  db_url: postgresql://user:password@postgres:5432/monitoring
```

Deploy to Kubernetes:

```bash
kubectl create namespace monitoring

# Create secret
kubectl create secret generic monitoring-secrets \
  --from-literal=db_url=postgresql://... \
  -n monitoring

# Deploy
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get pods -n monitoring
kubectl logs -f deployment/monitoring-platform -n monitoring
```

## Monitoring & Alerting

### 1. Prometheus Integration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'monitoring-platform'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboards

```bash
# Install Grafana
docker run -d -p 3000:3000 grafana/grafana

# Import dashboard
# - Connect to Prometheus data source
# - Create custom dashboards for metrics
```

### 3. Alert Rules

Create alert rules file:

```yaml
groups:
  - name: monitoring
    interval: 30s
    rules:
    - alert: HighAgentLatency
      expr: agent_execution_duration > 5000
      for: 5m
      annotations:
        summary: "Agent latency is high"

    - alert: HighErrorRate
      expr: rate(agent_errors[5m]) > 0.1
      for: 5m
      annotations:
        summary: "Agent error rate is high"
```

## Security

### 1. SSL/TLS Setup

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Configure nginx with SSL
location / {
    proxy_pass http://localhost:8501;
    proxy_ssl_certificate /etc/ssl/cert.pem;
    proxy_ssl_certificate_key /etc/ssl/key.pem;
}
```

### 2. Authentication

```bash
# Setup reverse proxy authentication
# Using nginx + oauth2_proxy

location / {
    auth_request /oauth2/auth;
    error_page 401 = /oauth2/sign_in;
    
    proxy_pass http://localhost:8501;
}
```

### 3. Database Encryption

```python
# Enable PostgreSQL encryption
# In postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

## Performance Optimization

### 1. Database Indexing

```sql
CREATE INDEX idx_agent_executions_agent_timestamp ON agent_executions(agent_id, timestamp DESC);
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp DESC);
CREATE INDEX idx_metrics_metric_name ON metrics(metric_name);
```

### 2. Connection Pooling

```python
# Use PgBouncer
# pgbouncer.ini
[databases]
monitoring = host=localhost port=5432 dbname=monitoring

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

### 3. Caching

```python
from functools import lru_cache
import redis

cache = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=1024)
def get_metrics_summary():
    return analytics.get_aggregations(...)
```

## Backup & Recovery

### 1. Automated Backups

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/var/backups/monitoring"
DB_HOST="localhost"
DB_NAME="monitoring"
DB_USER="postgres"

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/monitoring_$DATE.sql.gz"

pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Keep last 30 days of backups
find $BACKUP_DIR -name "monitoring_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

Schedule with cron:

```bash
# Run backup daily at 2 AM
0 2 * * * /opt/monitoring/backup.sh
```

### 2. Recovery Procedure

```bash
# List available backups
ls -la /var/backups/monitoring/

# Restore from backup
gunzip -c /var/backups/monitoring/monitoring_20240101_020000.sql.gz | \
  psql -h localhost -U postgres monitoring
```

## Monitoring Health

### 1. Health Checks

```bash
# Database connectivity
python -c "from data_engineering.database_manager import DatabaseManager; db = DatabaseManager(); print(db.get_statistics())"

# Service status
systemctl status monitoring-collector

# Docker health
docker ps --filter "name=monitoring"
```

### 2. Logs Monitoring

```bash
# View application logs
tail -f /var/log/monitoring/*.log

# Search for errors
grep ERROR /var/log/monitoring/*.log

# Using ELK stack (optional)
# Configure filebeat to send logs to Elasticsearch
```

## Troubleshooting

### High Memory Usage

```bash
# Check Python process memory
ps aux | grep python

# Clear old data
python -c "
from data_engineering.database_manager import DatabaseManager
db = DatabaseManager()
db.cleanup_old_data(retention_days=30)
"
```

### Slow Queries

```bash
# Enable query logging
# In postgresql.conf
log_min_duration_statement = 1000  # Log queries > 1 second

# Check slow query log
tail /var/log/postgresql/postgresql.log | grep duration
```

### Connection Issues

```bash
# Test database connection
psql -h localhost -U postgres -d monitoring -c "SELECT 1"

# Check connection limits
psql -c "SHOW max_connections"
```

## Maintenance

### Regular Tasks

- **Weekly**: Review logs and alerts
- **Monthly**: Run database ANALYZE and VACUUM
- **Quarterly**: Review and archive old data
- **Annually**: Update dependencies and security patches

### Update Procedure

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run migrations (if any)
python -m alembic upgrade head

# Restart services
systemctl restart monitoring-collector
docker-compose restart monitoring
```

---

**Deployment Complete** ✅

For support, refer to troubleshooting section or open an issue.
