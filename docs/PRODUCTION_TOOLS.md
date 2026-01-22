# Production Tools & Features

New production-ready tools and features added to AIRClass.

---

## 🆕 What's New

### 1. Environment Configuration (.env)
- **File**: `.env.example` → Copy to `.env`
- **Purpose**: Centralized configuration for all deployment modes
- **Key Settings**:
  - `MODE`: standalone | master | slave
  - `JWT_SECRET_KEY`: **MUST CHANGE** in production
  - `MAX_CONNECTIONS`: Capacity per slave
  - `MASTER_URL`: For slave mode

**Quick Start**:
```bash
cp .env.example .env
nano .env  # Edit your settings
docker-compose up -d
```

### 2. Cluster Monitoring Script
- **File**: `scripts/monitor-cluster.sh`
- **Purpose**: Real-time cluster health monitoring
- **Features**:
  - Live node status
  - Load balancing metrics
  - Capacity analysis
  - Auto-refresh mode
  - Alert integration

**Usage**:
```bash
# One-time check
./scripts/monitor-cluster.sh

# Continuous monitoring
./scripts/monitor-cluster.sh --watch

# Custom interval (30 seconds)
./scripts/monitor-cluster.sh --watch --interval 30

# JSON output (for scripts)
./scripts/monitor-cluster.sh --json

# With alerts (Slack/Discord webhook)
export ALERT_WEBHOOK=https://hooks.slack.com/...
./scripts/monitor-cluster.sh --watch --alert
```

**Output Example**:
```
═══════════════════════════════════════════════════════════════
  AIRClass Cluster Monitor - 2024-01-22 18:00:00
═══════════════════════════════════════════════════════════════
[OK] Master is UP at http://localhost:8000

┌─────────────────────────────────────────────────────────────┐
│                  AIRClass Cluster Status                    │
├─────────────────────────────────────────────────────────────┤
│ Total Nodes: 3                Active: 3                     │
├─────────────────────────────────────────────────────────────┤
│ Node: slave-1
│   URL: http://192.168.1.11:8000
│   Status: active
│   Connections: 45/150 (30.0%)
│   Last Seen: 2024-01-22T18:00:00
├─────────────────────────────────────────────────────────────┤
...
```

### 3. Backup & Restore Scripts
- **Files**: `scripts/backup-cluster.sh`, `scripts/restore-cluster.sh`
- **Purpose**: Configuration backup and disaster recovery
- **Backs up**:
  - Environment configuration (.env)
  - Docker compose files
  - MediaMTX configuration
  - Cluster state snapshot
  - Container status

**Backup Usage**:
```bash
# Manual backup
./scripts/backup-cluster.sh

# Auto backup (keeps last 7 days)
./scripts/backup-cluster.sh --auto

# Custom location
./scripts/backup-cluster.sh /mnt/backups

# Setup automated backups (cron)
crontab -e
# Add: 0 2 * * * /opt/airclass/scripts/backup-cluster.sh --auto
```

**Restore Usage**:
```bash
# From directory
./scripts/restore-cluster.sh ./backups/airclass_backup_20240122_180000

# From archive
./scripts/restore-cluster.sh ./backups/airclass_backup_20240122_180000.tar.gz
```

### 4. Prometheus Metrics Endpoint
- **Endpoint**: `GET /metrics`
- **Purpose**: Production monitoring with Prometheus/Grafana
- **Metrics Exposed**:
  - `airclass_http_requests_total` - HTTP request counts
  - `airclass_http_request_duration_seconds` - Request latency
  - `airclass_active_streams` - Number of active streams
  - `airclass_active_connections` - WebSocket/HLS connections
  - `airclass_tokens_issued_total` - JWT tokens issued
  - `airclass_cluster_nodes_total` - Cluster node count by status
  - `airclass_cluster_load_percentage` - Per-node load
  - `airclass_cluster_connections` - Per-node connections
  - `airclass_errors_total` - Error counts by type

**Access Metrics**:
```bash
curl http://localhost:8000/metrics

# Example output:
# HELP airclass_active_connections Number of active connections
# TYPE airclass_active_connections gauge
airclass_active_connections{type="teacher"} 1.0
airclass_active_connections{type="student"} 45.0
airclass_active_connections{type="monitor"} 3.0
...
```

**Prometheus Configuration** (add to `prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'airclass-master'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    
  - job_name: 'airclass-slaves'
    static_configs:
      - targets: 
        - '192.168.1.11:8000'
        - '192.168.1.12:8000'
        - '192.168.1.13:8000'
    metrics_path: '/metrics'
```

### 5. Admin Dashboard (Web UI)
- **Route**: `/admin`
- **URL**: `http://localhost:5173/admin`
- **Purpose**: Visual cluster monitoring
- **Features**:
  - Real-time cluster status
  - Node health indicators
  - Load balancing visualization
  - Capacity planning recommendations
  - Auto-refresh (5s interval)
  - Responsive design

**Access**:
```bash
# Start frontend
cd frontend
npm run dev

# Open browser
http://localhost:5173/admin
```

**Screenshots**:
- Cluster summary (4 cards): Nodes, Capacity, Load, Average Load
- Nodes table: Status, Load %, Connections, URLs, Last Seen
- Real-time recommendations: Scale up/down alerts
- Auto-refresh toggle

### 6. Production Deployment Guide
- **File**: `docs/PRODUCTION_DEPLOYMENT.md`
- **Purpose**: Complete deployment checklist
- **Sections**:
  - Pre-deployment checklist (hardware, software, network)
  - Security configuration (firewall, SSL, JWT)
  - Step-by-step deployment (Master + Slaves)
  - Testing procedures
  - Monitoring setup
  - Scaling guide
  - Troubleshooting
  - Maintenance tasks

---

## 📊 Monitoring Stack (Optional)

### Setup Prometheus + Grafana

1. **Add to docker-compose.yml** (already included, just uncomment):
```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

2. **Create prometheus.yml**:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'airclass'
    static_configs:
      - targets: ['master:8000', 'slave:8000']
```

3. **Start monitoring stack**:
```bash
docker-compose up -d prometheus grafana
```

4. **Access**:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

5. **Import Grafana Dashboard**:
- Add Prometheus datasource: http://prometheus:9090
- Create dashboard with panels:
  - Cluster Nodes: `airclass_cluster_nodes_total`
  - Total Load: `sum(airclass_cluster_connections)`
  - Average Load: `avg(airclass_cluster_load_percentage)`
  - Request Rate: `rate(airclass_http_requests_total[5m])`

---

## 🔧 Quick Reference

### Environment Variables
```bash
# Core
MODE=standalone|master|slave
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>

# Cluster (slave mode)
MASTER_URL=http://master-ip:8000
NODE_ID=slave-1
MAX_CONNECTIONS=150

# Ports
BACKEND_PORT=8000
RTMP_PORT=1935
HLS_PORT=8888
```

### Useful Commands
```bash
# Monitoring
./scripts/monitor-cluster.sh --watch

# Backup
./scripts/backup-cluster.sh --auto

# Check metrics
curl http://localhost:8000/metrics | grep airclass

# View cluster
curl http://localhost:8000/cluster/nodes | jq

# Check health
curl http://localhost:8000/health

# Scale cluster
docker-compose up -d --scale slave=5
```

### Important Endpoints
- **Health**: `/health`
- **Metrics**: `/metrics`
- **Cluster Status**: `/cluster/nodes`
- **Best Node**: `/cluster/best-node`
- **Admin UI**: `/admin`

---

## 🚀 Production Checklist

Before deploying to production:

- [ ] Change `JWT_SECRET_KEY` in `.env`
- [ ] Set proper `CORS_ORIGINS`
- [ ] Configure firewall rules
- [ ] Enable HTTPS (nginx + Let's Encrypt)
- [ ] Setup automated backups (cron)
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Test disaster recovery (restore from backup)
- [ ] Document server IPs and credentials
- [ ] Setup alert webhooks (Slack/Discord)
- [ ] Review and test scaling procedures

---

## 📈 Performance Tips

1. **Monitoring**: Setup Prometheus alerts for load >80%
2. **Scaling**: Auto-scale based on `airclass_cluster_load_percentage`
3. **Backup**: Daily automated backups at 2 AM
4. **Logs**: Rotate Docker logs with `--log-opt max-size=10m`
5. **Security**: Restrict `/admin` and `/metrics` with nginx auth

---

## 🆘 Troubleshooting

### Metrics not showing
```bash
# Check Prometheus dependency
pip install prometheus-client

# Test endpoint
curl http://localhost:8000/metrics
```

### Admin dashboard blank
```bash
# Check CORS
curl -H "Origin: http://localhost:5173" http://localhost:8000/cluster/nodes

# Check backend logs
docker-compose logs -f master
```

### Monitoring script fails
```bash
# Install jq
sudo apt install -y jq

# Check permissions
chmod +x scripts/*.sh
```

---

**Last Updated**: 2024-01-22  
**Version**: 2.0.0  
**For Support**: See `docs/PRODUCTION_DEPLOYMENT.md`
