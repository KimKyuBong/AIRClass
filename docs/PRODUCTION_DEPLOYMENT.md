# Production Deployment Checklist

Complete guide for deploying AIRClass to production environments.

---

## 📋 Pre-Deployment Checklist

### 1. Infrastructure Requirements

#### Hardware Specifications
- [ ] **Master Node** (Traffic Router)
  - [ ] CPU: 2+ cores
  - [ ] RAM: 4GB minimum
  - [ ] Network: 1Gbps LAN
  - [ ] OS: Linux (Ubuntu 20.04+ or CentOS 7+)

- [ ] **Slave Nodes** (Streaming Servers)
  - [ ] CPU: 4+ cores per node
  - [ ] RAM: 8GB minimum per node
  - [ ] Network: 1Gbps LAN (10Gbps recommended for 500+ users)
  - [ ] Storage: 50GB minimum (100GB+ if recording enabled)
  - [ ] OS: Linux (Ubuntu 20.04+ or CentOS 7+)

#### Network Requirements
- [ ] All nodes on same local network
- [ ] Static IP addresses assigned to all nodes
- [ ] Firewall configured (see Security section)
- [ ] DNS/hosts file configured for node discovery
- [ ] Internet access for initial setup (Docker image downloads)

### 2. Software Prerequisites

- [ ] **Docker** installed (20.10+)
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  ```

- [ ] **Docker Compose** installed (2.0+)
  ```bash
  sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  ```

- [ ] **Git** installed (for deployment)
  ```bash
  sudo apt update && sudo apt install -y git
  ```

- [ ] **jq** installed (for monitoring scripts)
  ```bash
  sudo apt install -y jq
  ```

### 3. Security Configuration

#### Firewall Rules
- [ ] **Master Node**
  ```bash
  # Allow HTTP API
  sudo ufw allow 8000/tcp
  
  # Allow from slave nodes only (adjust IP range)
  sudo ufw allow from 192.168.1.0/24 to any port 8000
  
  # Enable firewall
  sudo ufw enable
  ```

- [ ] **Slave Nodes**
  ```bash
  # Allow RTMP from Android devices
  sudo ufw allow 1935/tcp
  
  # Allow HLS from web clients
  sudo ufw allow 8888/tcp
  
  # Allow API from master and clients
  sudo ufw allow 8000/tcp
  
  sudo ufw enable
  ```

#### SSL/TLS (Optional but Recommended)
- [ ] Generate SSL certificates
  ```bash
  # Using Let's Encrypt
  sudo apt install -y certbot
  sudo certbot certonly --standalone -d your-domain.com
  ```

- [ ] Configure reverse proxy (nginx/caddy)
- [ ] Update CORS_ORIGINS in .env
- [ ] Update frontend API URLs to HTTPS

### 4. Configuration Files

#### Environment Setup
- [ ] Copy `.env.example` to `.env`
  ```bash
  cp .env.example .env
  ```

- [ ] **Generate JWT secret key**
  ```bash
  # CRITICAL: Change this in production!
  openssl rand -hex 32
  # Copy output to .env: JWT_SECRET_KEY=<output>
  ```

- [ ] **Configure Master Node** (.env)
  ```bash
  MODE=master
  MAX_CONNECTIONS=0  # Master doesn't handle connections
  BACKEND_PORT=8000
  JWT_SECRET_KEY=<your-generated-secret>
  CORS_ORIGINS=http://your-frontend-domain.com
  ```

- [ ] **Configure Slave Nodes** (.env on each slave)
  ```bash
  MODE=slave
  MASTER_URL=http://<master-ip>:8000
  NODE_ID=slave-1  # Unique per slave
  NODE_NAME=slave-1
  NODE_HOST=<this-slave-ip>
  NODE_PORT=8000
  RTMP_PORT=1935
  HLS_PORT=8888
  MAX_CONNECTIONS=150  # Adjust based on hardware
  JWT_SECRET_KEY=<same-as-master>
  ```

#### MediaMTX Configuration
- [ ] Review `backend/mediamtx.yml`
- [ ] Adjust `hlsSegmentCount` (default: 7)
- [ ] Adjust `hlsSegmentDuration` (default: 1s)
- [ ] Verify authentication is enabled

---

## 🚀 Deployment Steps

### Step 1: Deploy Master Node

1. **Clone repository**
   ```bash
   git clone <your-repo-url> /opt/airclass
   cd /opt/airclass
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with master configuration
   ```

3. **Start master**
   ```bash
   docker-compose up -d master
   ```

4. **Verify master is running**
   ```bash
   # Check health
   curl http://localhost:8000/health
   # Should return: {"status":"ok"}
   
   # Check cluster (should be empty initially)
   curl http://localhost:8000/cluster/nodes
   ```

5. **Check logs**
   ```bash
   docker-compose logs -f master
   ```

### Step 2: Deploy Slave Nodes

**Repeat for each slave node:**

1. **Clone repository on slave**
   ```bash
   git clone <your-repo-url> /opt/airclass
   cd /opt/airclass
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with slave configuration
   # Set MASTER_URL to master's IP
   # Set unique NODE_ID for each slave
   ```

3. **Start slave**
   ```bash
   docker-compose up -d slave
   ```

4. **Verify slave registered**
   ```bash
   # On master node, check cluster
   curl http://<master-ip>:8000/cluster/nodes | jq
   # Should show the newly registered slave
   ```

5. **Check slave logs**
   ```bash
   docker-compose logs -f slave
   ```

### Step 3: Deploy Frontend

1. **Update frontend API URL**
   ```javascript
   // frontend/src/config.js or environment variable
   const API_URL = 'http://<master-ip>:8000';
   ```

2. **Build frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   ```

3. **Deploy with nginx** (recommended)
   ```bash
   # Install nginx
   sudo apt install -y nginx
   
   # Copy build files
   sudo cp -r dist/* /var/www/html/
   
   # Configure nginx
   sudo nano /etc/nginx/sites-available/airclass
   ```
   
   Example nginx config:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       root /var/www/html;
       index index.html;
       
       location / {
           try_files $uri $uri/ /index.html;
       }
       
       # Proxy API requests to master
       location /api {
           proxy_pass http://<master-ip>:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       # Proxy WebSocket
       location /ws {
           proxy_pass http://<master-ip>:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

4. **Enable and start nginx**
   ```bash
   sudo ln -s /etc/nginx/sites-available/airclass /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Step 4: Testing

- [ ] **Test Health Endpoints**
  ```bash
  # Master
  curl http://<master-ip>:8000/health
  
  # Each slave
  curl http://<slave-ip>:8000/health
  ```

- [ ] **Test Cluster Status**
  ```bash
  curl http://<master-ip>:8000/cluster/nodes | jq
  ```

- [ ] **Test Token Generation**
  ```bash
  curl -X POST "http://<master-ip>:8000/api/token?user_type=student&user_id=TestUser" | jq
  # Should return token and slave node URL
  ```

- [ ] **Test RTMP Streaming**
  ```bash
  # Use FFmpeg to simulate stream
  ffmpeg -re -i test.mp4 -c copy -f flv rtmp://<slave-ip>:1935/live/stream
  ```

- [ ] **Test HLS Playback**
  - Open browser: `http://your-frontend-domain.com`
  - Login as student
  - Verify video plays

- [ ] **Test Android App**
  - Configure app with slave RTMP URL
  - Start streaming
  - Verify on web client

### Step 5: Monitoring Setup

- [ ] **Setup monitoring script**
  ```bash
  # Create systemd service for continuous monitoring
  sudo nano /etc/systemd/system/airclass-monitor.service
  ```
  
  ```ini
  [Unit]
  Description=AIRClass Cluster Monitor
  After=network.target
  
  [Service]
  Type=simple
  User=your-user
  WorkingDirectory=/opt/airclass
  ExecStart=/opt/airclass/scripts/monitor-cluster.sh --watch --interval 30
  Restart=always
  
  [Install]
  WantedBy=multi-user.target
  ```
  
  ```bash
  sudo systemctl enable airclass-monitor
  sudo systemctl start airclass-monitor
  ```

- [ ] **Setup automated backups**
  ```bash
  # Add to crontab
  crontab -e
  
  # Backup daily at 2 AM
  0 2 * * * /opt/airclass/scripts/backup-cluster.sh --auto
  ```

---

## 📊 Scaling Guide

### Adding More Slaves

**During runtime (no downtime):**

1. Prepare new server with slave configuration
2. Start slave: `docker-compose up -d slave`
3. Verify registration: `curl http://<master-ip>:8000/cluster/nodes`
4. Monitor load distribution: `./scripts/monitor-cluster.sh --watch`

### Removing Slaves

**Graceful shutdown:**

1. Mark node for removal (manual process)
2. Wait for connections to drain
3. Stop slave: `docker-compose down`
4. Master will automatically detect and remove after timeout

### Capacity Planning

```
Users per Slave = 150 (recommended conservative limit)

For 500 users:
  - Master: 1 node
  - Slaves: 4 nodes (500 / 150 = 3.3, round up to 4)

For 1000 users:
  - Master: 1 node
  - Slaves: 7 nodes (1000 / 150 = 6.6, round up to 7)
```

---

## 🔧 Troubleshooting

### Issue: Slave not registering to Master

**Symptoms:**
- Slave logs show "Failed to register"
- Master's `/cluster/nodes` doesn't show slave

**Solutions:**
1. Check network connectivity:
   ```bash
   ping <master-ip>
   curl http://<master-ip>:8000/health
   ```

2. Verify `MASTER_URL` in slave's `.env`

3. Check firewall rules on master

4. Check master logs: `docker-compose logs master`

### Issue: High latency on HLS streams

**Symptoms:**
- Delay > 10 seconds
- Stuttering playback

**Solutions:**
1. Reduce HLS segment count:
   ```yaml
   # backend/mediamtx.yml
   hlsSegmentCount: 4  # Down from 7
   ```

2. Check network bandwidth:
   ```bash
   iperf3 -s  # On slave
   iperf3 -c <slave-ip>  # On client
   ```

3. Reduce stream quality in Android app

### Issue: Master single point of failure

**Mitigation:**

1. **Backup Master** (manual failover):
   - Keep a standby master with same configuration
   - If primary fails, update slave `MASTER_URL` to backup
   - Restart slaves

2. **Future**: Implement master HA with keepalived/HAProxy

### Issue: Node shows as "offline" but is running

**Cause:** Heartbeat timeout (30s default)

**Solutions:**
1. Check slave network connectivity
2. Verify slave is sending heartbeats:
   ```bash
   docker-compose logs slave | grep "Sending stats"
   ```
3. Check master is receiving:
   ```bash
   docker-compose logs master | grep "Stats received"
   ```

---

## 🔒 Security Hardening

### Production Security Checklist

- [ ] **Change default JWT secret**
  ```bash
  JWT_SECRET_KEY=$(openssl rand -hex 32)
  ```

- [ ] **Enable HTTPS** (use nginx with Let's Encrypt)

- [ ] **Restrict CORS origins**
  ```bash
  CORS_ORIGINS=https://your-production-domain.com
  ```

- [ ] **Firewall configuration**
  - Only allow necessary ports
  - Restrict slave registration to internal network

- [ ] **Disable debug mode**
  ```bash
  DEBUG=false
  VERBOSE=false
  ```

- [ ] **Regular updates**
  ```bash
  docker-compose pull
  docker-compose up -d
  ```

- [ ] **Monitor logs for suspicious activity**
  ```bash
  docker-compose logs -f | grep -i error
  ```

---

## 📈 Performance Optimization

### Backend Optimization

1. **Increase Uvicorn workers** (1 per CPU core)
   ```bash
   WORKERS=8  # For 8-core CPU
   ```

2. **Tune HLS settings** for your network
   ```yaml
   hlsSegmentCount: 7      # Higher = more latency, but smoother
   hlsSegmentDuration: 1s  # Lower = less latency
   ```

3. **Enable Prometheus monitoring**
   ```bash
   PROMETHEUS_ENABLED=true
   ```

### Frontend Optimization

1. **Enable CDN** for static assets
2. **Implement lazy loading** for video players
3. **Use service workers** for offline support

### Network Optimization

1. **Use dedicated VLAN** for streaming traffic
2. **QoS rules** to prioritize streaming packets
3. **Load balancer** in front of slaves (nginx/HAProxy)

---

## 🎓 Maintenance Tasks

### Daily
- [ ] Check cluster status: `./scripts/monitor-cluster.sh`
- [ ] Review logs for errors

### Weekly
- [ ] Backup configuration: `./scripts/backup-cluster.sh`
- [ ] Check disk space on all nodes
- [ ] Review capacity and scale if needed

### Monthly
- [ ] Update Docker images: `docker-compose pull && docker-compose up -d`
- [ ] Test disaster recovery (restore from backup)
- [ ] Review and optimize performance metrics

### Quarterly
- [ ] Security audit
- [ ] Capacity planning review
- [ ] Update documentation

---

## 📞 Support & Resources

### Quick Commands Reference

```bash
# Check cluster health
./scripts/monitor-cluster.sh

# Backup cluster
./scripts/backup-cluster.sh

# Restore from backup
./scripts/restore-cluster.sh /path/to/backup

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Scale slaves
docker-compose up -d --scale slave=N

# Check resource usage
docker stats
```

### Log Locations

- **Master logs**: `docker-compose logs master`
- **Slave logs**: `docker-compose logs slave`
- **MediaMTX logs**: Inside containers at `/app/mediamtx.log`
- **Nginx logs**: `/var/log/nginx/access.log` and `error.log`

### Useful Endpoints

- **Health**: `http://<node>:8000/health`
- **Cluster status**: `http://<master>:8000/cluster/nodes`
- **Best node**: `http://<master>:8000/cluster/best-node`
- **Metrics** (if enabled): `http://<node>:9090/metrics`

---

## ✅ Post-Deployment Verification

After deployment, verify everything is working:

```bash
# 1. All nodes are healthy
curl http://<master-ip>:8000/cluster/nodes | jq '.nodes[] | {id: .node_id, status: .status}'

# 2. Can generate tokens
curl -X POST "http://<master-ip>:8000/api/token?user_type=student&user_id=test" | jq

# 3. Can stream RTMP
ffmpeg -re -i test.mp4 -c copy -f flv rtmp://<slave-ip>:1935/live/stream

# 4. Can play HLS
# Open: http://<slave-ip>:8888/live/stream/index.m3u8

# 5. Frontend accessible
# Open: http://your-frontend-domain.com
```

---

## 🎯 Success Criteria

Your deployment is successful when:

- ✅ All nodes show "active" status in cluster
- ✅ Master routes traffic to least-loaded slave
- ✅ RTMP streaming works from Android app
- ✅ HLS playback works on web frontend
- ✅ JWT authentication works correctly
- ✅ Monitoring script shows healthy cluster
- ✅ Load balancing distributes users evenly
- ✅ Backups run automatically
- ✅ System handles expected user load without issues

---

**Last Updated**: 2024-01-22
**Version**: 1.0
**For Support**: See repository issues or documentation
