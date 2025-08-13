# Qdrant Vector Search Service - EC2 Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installing Qdrant on EC2 Linux](#installing-qdrant-on-ec2-linux)
4. [Strategy 1: Docker-Based Deployment](#strategy-1-docker-based-deployment)
5. [Strategy 2: Native Python Deployment](#strategy-2-native-python-deployment)
6. [Strategy 3: AWS ECS/Fargate Deployment](#strategy-3-aws-ecsfargate-deployment)
7. [Comparison & Recommendations](#comparison--recommendations)
8. [Troubleshooting](#troubleshooting)

## Overview

This guide provides three comprehensive strategies for deploying the Qdrant Vector Search Service to Amazon EC2 Linux instances. The service consists of:

- **FastAPI Backend** - REST API for vector search operations
- **Qdrant Vector Database** - For storing and searching vector embeddings
- **Sentence Transformers** - For generating text embeddings
- **Streamlit UI** - Web interface for search functionality
- **Indexing Scripts** - For bulk data loading and management

## Prerequisites

### System Requirements
- **EC2 Instance**: Ubuntu 22.04 LTS (recommended)
- **Instance Type**: t3.medium or larger (2+ vCPUs, 4+ GB RAM)
- **Storage**: 20+ GB EBS volume
- **Network**: Security groups configured for required ports

### Required Ports
- **22** - SSH access
- **8000** - FastAPI backend
- **8501** - Streamlit UI
- **6333** - Qdrant HTTP API
- **6334** - Qdrant gRPC API

---

## Installing Qdrant on EC2 Linux

This section provides multiple methods for installing Qdrant locally on your EC2 Linux instance.

### Method 1: Binary Installation (Recommended)

```bash
# 1. Download the latest Qdrant binary
cd /tmp
curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz | tar xz

# 2. Move to system path
sudo mv qdrant /usr/local/bin/
sudo chmod +x /usr/local/bin/qdrant

# 3. Verify installation
qdrant --version

# 4. Create Qdrant user and directories
sudo useradd -r -s /bin/false qdrant
sudo mkdir -p /var/lib/qdrant
sudo mkdir -p /var/log/qdrant
sudo mkdir -p /etc/qdrant
sudo chown -R qdrant:qdrant /var/lib/qdrant
sudo chown -R qdrant:qdrant /var/log/qdrant
```

### Qdrant Configuration

#### Basic Configuration File

```bash
# Create configuration directory and file
sudo mkdir -p /etc/qdrant
sudo tee /etc/qdrant/qdrant.yaml > /dev/null << 'EOF'
storage:
  # Storage path for collections
  storage_path: /var/lib/qdrant/storage
  
  # Performance settings
  performance:
    max_search_threads: 4
    max_optimization_threads: 2
    max_compaction_threads: 2
  
  # Memory settings
  memmap_threshold: 20000
  on_disk_payload: false

service:
  # HTTP API settings
  http_port: 6333
  http_host: 0.0.0.0
  
  # gRPC API settings
  grpc_port: 6334
  grpc_host: 0.0.0.0
  
  # CORS settings
  cors:
    allowed_origins:
      - "*"
    allowed_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    allowed_headers:
      - "*"

cluster:
  # Disable clustering for single instance
  enabled: false

telemetry:
  # Disable telemetry for production
  enabled: false

log_level: INFO
EOF

# Set proper permissions
sudo chown -R qdrant:qdrant /etc/qdrant
```

#### Advanced Configuration

```bash
# Create advanced configuration for production
sudo tee /etc/qdrant/qdrant-production.yaml > /dev/null << 'EOF'
storage:
  storage_path: /var/lib/qdrant/storage
  
  # Optimized performance settings
  performance:
    max_search_threads: 8
    max_optimization_threads: 4
    max_compaction_threads: 4
  
  # Memory optimization
  memmap_threshold: 50000
  on_disk_payload: true
  
  # Snapshot settings
  snapshots_path: /var/lib/qdrant/snapshots
  
  # Optimizers settings
  optimizers:
    default_segment_number: 2
    max_segment_size: 20000
    memmap_threshold: 50000
    indexing_threshold: 20000
    flush_interval_sec: 5
    max_optimization_threads: 4

service:
  http_port: 6333
  http_host: 0.0.0.0
  grpc_port: 6334
  grpc_host: 0.0.0.0
  
  # Security settings
  cors:
    allowed_origins:
      - "http://localhost:8501"
      - "http://your-domain.com"
    allowed_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    allowed_headers:
      - "Content-Type"
      - "Authorization"
      - "X-Requested-With"

cluster:
  enabled: false

telemetry:
  enabled: false

log_level: INFO

# HNSW index settings
hnsw:
  m: 16
  ef_construct: 100
  full_scan_threshold: 10000
  max_indexing_threads: 4
EOF
```

### Systemd Service Configuration

```bash
# Create systemd service file
sudo tee /etc/systemd/system/qdrant.service > /dev/null << 'EOF'
[Unit]
Description=Qdrant Vector Database
Documentation=https://qdrant.tech/documentation/
After=network.target
Wants=network.target

[Service]
Type=simple
User=qdrant
Group=qdrant
WorkingDirectory=/var/lib/qdrant
ExecStart=/usr/local/bin/qdrant --config-path /etc/qdrant/qdrant.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=qdrant

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/qdrant /var/log/qdrant

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable qdrant
sudo systemctl start qdrant

# Check service status
sudo systemctl status qdrant
```

### Verification and Testing

```bash
# 1. Check if Qdrant is running
sudo systemctl status qdrant

# 2. Test HTTP API
curl http://localhost:6333/health

# 3. Test gRPC API (if you have grpcurl installed)
grpcurl -plaintext localhost:6334 list

# 4. Check logs
sudo journalctl -u qdrant -f

# 5. Test collection creation
curl -X PUT http://localhost:6333/collections/test_collection \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

# 6. List collections
curl http://localhost:6333/collections

# 7. Delete test collection
curl -X DELETE http://localhost:6333/collections/test_collection
```

### Performance Optimization

#### Memory Optimization

```bash
# Check current memory usage
free -h
cat /proc/meminfo

# Optimize Qdrant memory settings based on available RAM
# For 4GB RAM instance:
sudo tee /etc/qdrant/qdrant-optimized.yaml > /dev/null << 'EOF'
storage:
  storage_path: /var/lib/qdrant/storage
  
  # Optimize for 4GB RAM
  performance:
    max_search_threads: 2
    max_optimization_threads: 1
    max_compaction_threads: 1
  
  # Memory settings for 4GB RAM
  memmap_threshold: 10000
  on_disk_payload: true
  
  optimizers:
    default_segment_number: 1
    max_segment_size: 10000
    memmap_threshold: 10000
    indexing_threshold: 10000
    flush_interval_sec: 10
    max_optimization_threads: 1

service:
  http_port: 6333
  http_host: 0.0.0.0
  grpc_port: 6334
  grpc_host: 0.0.0.0

cluster:
  enabled: false

telemetry:
  enabled: false

log_level: INFO

hnsw:
  m: 12
  ef_construct: 64
  full_scan_threshold: 5000
  max_indexing_threads: 1
EOF

# For 16GB RAM instance (Large):
sudo tee /etc/qdrant/qdrant-large-instance.yaml > /dev/null << 'EOF'
storage:
  storage_path: /var/lib/qdrant/storage
  
  # Optimize for 16GB RAM - Large Instance
  performance:
    max_search_threads: 8
    max_optimization_threads: 4
    max_compaction_threads: 4
  
  # Memory settings for 16GB RAM
  memmap_threshold: 50000
  on_disk_payload: false  # Keep payloads in memory for better performance
  
  # Snapshot settings
  snapshots_path: /var/lib/qdrant/snapshots
  
  # Optimizers settings for large instance
  optimizers:
    default_segment_number: 4
    max_segment_size: 50000
    memmap_threshold: 50000
    indexing_threshold: 20000
    flush_interval_sec: 5
    max_optimization_threads: 4

service:
  http_port: 6333
  http_host: 0.0.0.0
  grpc_port: 6334
  grpc_host: 0.0.0.0
  
  # Security settings
  cors:
    allowed_origins:
      - "http://localhost:8501"
      - "http://your-domain.com"
    allowed_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    allowed_headers:
      - "Content-Type"
      - "Authorization"
      - "X-Requested-With"

cluster:
  enabled: false

telemetry:
  enabled: false

log_level: INFO

# HNSW index settings optimized for large instance
hnsw:
  m: 32
  ef_construct: 200
  full_scan_threshold: 20000
  max_indexing_threads: 4
EOF
```

#### Large Instance Optimization (4 vCPUs, 16 GB RAM)

```bash
# Create optimized configuration for large instance
sudo tee /etc/qdrant/qdrant-large.yaml > /dev/null << 'EOF'
storage:
  storage_path: /var/lib/qdrant/storage
  
  # Optimized for 4 vCPUs, 16 GB RAM
  performance:
    max_search_threads: 6          # Use 6 threads (leave 2 for system)
    max_optimization_threads: 3    # Use 3 threads for optimization
    max_compaction_threads: 3      # Use 3 threads for compaction
  
  # Memory settings for 16GB RAM
  memmap_threshold: 60000          # Higher threshold for more memory
  on_disk_payload: false           # Keep payloads in memory for speed
  
  # Snapshot settings
  snapshots_path: /var/lib/qdrant/snapshots
  
  # Optimizers settings
  optimizers:
    default_segment_number: 6      # More segments for better parallelism
    max_segment_size: 40000        # Larger segments
    memmap_threshold: 60000        # Higher memory threshold
    indexing_threshold: 15000      # Lower indexing threshold
    flush_interval_sec: 3          # Faster flushing
    max_optimization_threads: 3    # Parallel optimization

service:
  http_port: 6333
  http_host: 0.0.0.0
  grpc_port: 6334
  grpc_host: 0.0.0.0
  
  # Enhanced CORS for production
  cors:
    allowed_origins:
      - "http://localhost:8501"
      - "http://your-domain.com"
      - "https://your-domain.com"
    allowed_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    allowed_headers:
      - "Content-Type"
      - "Authorization"
      - "X-Requested-With"
      - "Accept"

cluster:
  enabled: false

telemetry:
  enabled: false

log_level: INFO

# HNSW index settings for large instance
hnsw:
  m: 24              # Higher M for better recall
  ef_construct: 150  # Higher ef_construct for better index quality
  full_scan_threshold: 15000
  max_indexing_threads: 3
EOF

# Update systemd service for large instance
sudo tee /etc/systemd/system/qdrant.service > /dev/null << 'EOF'
[Unit]
Description=Qdrant Vector Database
Documentation=https://qdrant.tech/documentation/
After=network.target
Wants=network.target

[Service]
Type=simple
User=qdrant
Group=qdrant
WorkingDirectory=/var/lib/qdrant
ExecStart=/usr/local/bin/qdrant --config-path /etc/qdrant/qdrant-large.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=qdrant

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/qdrant /var/log/qdrant

# Resource limits for large instance
LimitNOFILE=131072
LimitNPROC=8192
# Memory limit: 12GB (leaving 4GB for system)
LimitAS=12884901888

[Install]
WantedBy=multi-user.target
EOF

# Reload and restart with new configuration
sudo systemctl daemon-reload
sudo systemctl restart qdrant
sudo systemctl status qdrant
```

#### System Optimization for Large Instance

```bash
# Optimize system settings for 16GB RAM instance
sudo tee /etc/sysctl.d/99-qdrant-large-instance.conf > /dev/null << 'EOF'
# File descriptor limits
fs.file-max = 131072
fs.nr_open = 131072

# Memory management for 16GB RAM
vm.swappiness = 1
vm.dirty_ratio = 20
vm.dirty_background_ratio = 10
vm.vfs_cache_pressure = 50

# Network optimizations for high throughput
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.core.rmem_default = 8388608
net.core.wmem_default = 8388608
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1

# TCP optimizations
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_syn_backlog = 8192
net.core.netdev_max_backlog = 5000

# Increase connection tracking
net.netfilter.nf_conntrack_max = 131072
net.netfilter.nf_conntrack_tcp_timeout_established = 86400
EOF

# Apply system optimizations
sudo sysctl -p /etc/sysctl.d/99-qdrant-large-instance.conf

# Update user limits for qdrant user
sudo tee /etc/security/limits.d/qdrant.conf > /dev/null << 'EOF'
qdrant soft nofile 131072
qdrant hard nofile 131072
qdrant soft nproc 8192
qdrant hard nproc 8192
qdrant soft memlock unlimited
qdrant hard memlock unlimited
EOF

# Verify optimizations
echo "=== System Memory ==="
free -h

echo "=== File Descriptors ==="
ulimit -n

echo "=== CPU Cores ==="
nproc

echo "=== Qdrant Process ==="
ps aux | grep qdrant | grep -v grep
```

### Disk I/O Optimization

```bash
# Check disk I/O performance
sudo apt install -y iostat
iostat -x 1 5

# Optimize disk settings for EBS
sudo tee /etc/sysctl.d/99-qdrant-optimization.conf > /dev/null << 'EOF'
# Increase file descriptor limits
fs.file-max = 65536

# Optimize for SSD/EBS
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# Network optimizations
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
EOF

sudo sysctl -p /etc/sysctl.d/99-qdrant-optimization.conf
```

### Monitoring and Logging

#### Log Configuration

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/qdrant > /dev/null << 'EOF'
/var/log/qdrant/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 qdrant qdrant
    postrotate
        systemctl reload qdrant
    endscript
}
EOF
```

#### Basic Monitoring Script

```bash
# Create monitoring script
sudo tee /usr/local/bin/qdrant-monitor.sh > /dev/null << 'EOF'
#!/bin/bash

# Qdrant monitoring script
LOG_FILE="/var/log/qdrant/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check if Qdrant is running
if systemctl is-active --quiet qdrant; then
    STATUS="RUNNING"
else
    STATUS="STOPPED"
    echo "$DATE - Qdrant service is not running!" >> $LOG_FILE
    systemctl restart qdrant
fi

# Check memory usage
MEMORY_USAGE=$(ps aux | grep qdrant | grep -v grep | awk '{print $6}' | head -1)
if [ ! -z "$MEMORY_USAGE" ]; then
    MEMORY_MB=$((MEMORY_USAGE / 1024))
    echo "$DATE - Qdrant memory usage: ${MEMORY_MB}MB" >> $LOG_FILE
fi

# Check disk usage
DISK_USAGE=$(du -sh /var/lib/qdrant/storage 2>/dev/null | cut -f1)
echo "$DATE - Qdrant disk usage: $DISK_USAGE" >> $LOG_FILE

# Test API connectivity
if curl -s http://localhost:6333/health > /dev/null; then
    echo "$DATE - Qdrant API is responding" >> $LOG_FILE
else
    echo "$DATE - Qdrant API is not responding!" >> $LOG_FILE
fi
EOF

sudo chmod +x /usr/local/bin/qdrant-monitor.sh

# Add to crontab for regular monitoring
echo "*/5 * * * * /usr/local/bin/qdrant-monitor.sh" | sudo crontab -
```

### Troubleshooting Qdrant Installation

#### Common Issues

```bash
# 1. Permission issues
sudo chown -R qdrant:qdrant /var/lib/qdrant
sudo chown -R qdrant:qdrant /var/log/qdrant
sudo chown -R qdrant:qdrant /etc/qdrant

# 2. Port conflicts
sudo netstat -tlnp | grep :6333
sudo netstat -tlnp | grep :6334

# 3. Memory issues
free -h
sudo dmesg | grep -i "out of memory"

# 4. Disk space issues
df -h
du -sh /var/lib/qdrant/storage

# 5. Check Qdrant logs
sudo journalctl -u qdrant -n 50 --no-pager
sudo tail -f /var/log/qdrant/qdrant.log
```

#### Performance Issues

```bash
# 1. Check system resources
htop
iostat -x 1 5
iotop

# 2. Check Qdrant performance
curl -s http://localhost:6333/collections | jq .

# 3. Monitor network connections
sudo netstat -an | grep :6333
sudo ss -tulpn | grep :6333

# 4. Check for memory leaks
sudo cat /proc/$(pgrep qdrant)/status | grep VmRSS
```

#### Recovery Procedures

```bash
# 1. Restart Qdrant service
sudo systemctl restart qdrant

# 2. Reset Qdrant data (WARNING: This will delete all data)
sudo systemctl stop qdrant
sudo rm -rf /var/lib/qdrant/storage/*
sudo systemctl start qdrant

# 3. Restore from backup
sudo systemctl stop qdrant
sudo tar -xzf qdrant-backup.tar.gz -C /var/lib/qdrant/
sudo chown -R qdrant:qdrant /var/lib/qdrant
sudo systemctl start qdrant

# 4. Check collection integrity
curl -s http://localhost:6333/collections | jq '.collections[] | {name: .name, vectors_count: .vectors_count}'
```

---

## Strategy 1: Docker-Based Deployment (Recommended)

### Phase 1: EC2 Instance Setup

```bash
# 1. Launch EC2 instance (Ubuntu 22.04 LTS)
# Instance type: t3.medium or larger (2+ vCPUs, 4+ GB RAM)
# Storage: 20+ GB EBS volume

# 2. Connect to instance and update system
sudo apt update && sudo apt upgrade -y

# 3. Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

# 4. Logout and login again for group changes to take effect
exit
# Reconnect to instance
```

### Phase 2: Application Deployment

```bash
# 1. Clone/upload codebase to EC2
git clone <your-repo> /home/ubuntu/qdrant-service
cd /home/ubuntu/qdrant-service

# 2. Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY search_ui/ ./search_ui/

# Create necessary directories
RUN mkdir -p data logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 3. Create .env file for configuration
cat > .env << 'EOF'
HOST=qdrant
PORT=6333
COLLECTION_NAME=products
VECTOR_SIZE=384
SEARCH_LIMIT=100
SCORE_THRESHOLD=0.7
LOG_LEVEL=INFO
LOG_PATH=/app/logs/service.log
MODEL_NAME=BAAI/bge-small-en-v1.5
EOF

# 4. Create production docker-compose file
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant-db
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  vector-search-server:
    build: .
    container_name: vector-search-server
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - HOST=qdrant
      - PORT=6333
      - COLLECTION_NAME=products
      - VECTOR_SIZE=384
      - SEARCH_LIMIT=100
      - SCORE_THRESHOLD=0.7
      - LOG_LEVEL=INFO
      - LOG_PATH=/app/logs/service.log
      - MODEL_NAME=BAAI/bge-small-en-v1.5
    depends_on:
      qdrant:
        condition: service_healthy
    restart: unless-stopped

  search-ui:
    build:
      context: .
      dockerfile: Dockerfile.ui
    container_name: search-ui
    ports:
      - "8501:8501"
    environment:
      - SEARCH_API_HOST=vector-search-server
      - SEARCH_API_PORT=8000
      - SEARCH_ENDPOINT_TYPE=fusion
    depends_on:
      - vector-search-server
    restart: unless-stopped

volumes:
  qdrant_storage:
EOF

# 5. Create UI Dockerfile
cat > Dockerfile.ui << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Streamlit and dependencies
RUN pip install streamlit requests python-dotenv

# Copy UI code
COPY search_ui/ ./search_ui/

# Expose port
EXPOSE 8501

# Start Streamlit
CMD ["streamlit", "run", "search_ui/search.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

# 6. Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 7. Check service status
docker-compose -f docker-compose.prod.yml ps
docker logs vector-search-server
docker logs qdrant-db
docker logs search-ui
```

### Phase 3: Data Loading

```bash
# 1. Copy your data files to the server
scp -i your-key.pem products.json ubuntu@your-ec2-ip:/home/ubuntu/qdrant-service/data/

# 2. Run indexing script
docker exec -it vector-search-server python scripts/indexing.py

# 3. Verify data loading
curl http://localhost:8000/api/collections
```

### Phase 4: Security & Monitoring

```bash
# 1. Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # API
sudo ufw allow 8501/tcp  # UI
sudo ufw enable

# 2. Set up monitoring
sudo apt install -y htop nginx

# 3. Configure nginx reverse proxy (optional)
sudo tee /etc/nginx/sites-available/qdrant-service > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # UI proxy
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/qdrant-service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Strategy 2: Native Python Deployment

### Phase 1: EC2 Instance Setup

```bash
# 1. Launch EC2 instance (Ubuntu 22.04 LTS)
# Instance type: t3.medium or larger

# 2. Update system and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx git curl

# 3. Create application user
sudo useradd -m -s /bin/bash qdrant-app
sudo usermod -aG sudo qdrant-app
```

### Phase 2: Application Setup

```bash
# 1. Switch to application user
sudo su - qdrant-app

# 2. Clone/upload codebase
git clone <your-repo> /home/qdrant-app/qdrant-service
cd /home/qdrant-app/qdrant-service

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Install Qdrant binary
curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv qdrant /usr/local/bin/
```

### Phase 3: Service Configuration

```bash
# 1. Create systemd service for Qdrant
sudo tee /etc/systemd/system/qdrant.service > /dev/null << 'EOF'
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=qdrant-app
WorkingDirectory=/home/qdrant-app/qdrant-service
ExecStart=/usr/local/bin/qdrant
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 2. Create systemd service for FastAPI
sudo tee /etc/systemd/system/vector-search.service > /dev/null << 'EOF'
[Unit]
Description=Vector Search API
After=network.target qdrant.service
Requires=qdrant.service

[Service]
Type=simple
User=qdrant-app
WorkingDirectory=/home/qdrant-app/qdrant-service
Environment=PATH=/home/qdrant-app/qdrant-service/venv/bin
ExecStart=/home/qdrant-app/qdrant-service/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 3. Create systemd service for Streamlit UI
sudo tee /etc/systemd/system/search-ui.service > /dev/null << 'EOF'
[Unit]
Description=Search UI
After=network.target vector-search.service
Requires=vector-search.service

[Service]
Type=simple
User=qdrant-app
WorkingDirectory=/home/qdrant-app/qdrant-service
Environment=PATH=/home/qdrant-app/qdrant-service/venv/bin
ExecStart=/home/qdrant-app/qdrant-service/venv/bin/streamlit run search_ui/search.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 4. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable qdrant
sudo systemctl enable vector-search
sudo systemctl enable search-ui

sudo systemctl start qdrant
sudo systemctl start vector-search
sudo systemctl start search-ui

# 5. Check service status
sudo systemctl status qdrant
sudo systemctl status vector-search
sudo systemctl status search-ui
```

### Phase 4: Nginx Configuration

```bash
# 1. Configure nginx
sudo tee /etc/nginx/sites-available/qdrant-service > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # UI proxy
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 2. Enable site and restart nginx
sudo ln -s /etc/nginx/sites-available/qdrant-service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Strategy 3: AWS ECS/Fargate Deployment

### Phase 1: AWS Infrastructure Setup

```bash
# 1. Install AWS CLI and configure
aws configure

# 2. Create ECR repositories
aws ecr create-repository --repository-name qdrant-service
aws ecr create-repository --repository-name qdrant-db
aws ecr create-repository --repository-name search-ui

# 3. Create VPC and security groups (via AWS Console or CLI)
```

### Phase 2: Container Image Building

```bash
# 1. Create optimized Dockerfile for ECS
cat > Dockerfile.ecs << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create directories
RUN mkdir -p data logs

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 2. Build and push images
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

docker build -f Dockerfile.ecs -t qdrant-service .
docker tag qdrant-service:latest your-account.dkr.ecr.us-east-1.amazonaws.com/qdrant-service:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/qdrant-service:latest
```

### Phase 3: ECS Task Definitions

Create `qdrant-task-definition.json`:

```json
{
    "family": "qdrant-service",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::your-account:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "qdrant-db",
            "image": "qdrant/qdrant:latest",
            "portMappings": [
                {"containerPort": 6333, "protocol": "tcp"},
                {"containerPort": 6334, "protocol": "tcp"}
            ],
            "environment": [
                {"name": "QDRANT__SERVICE__HTTP_PORT", "value": "6333"},
                {"name": "QDRANT__SERVICE__GRPC_PORT", "value": "6334"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/qdrant-service",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "qdrant"
                }
            }
        },
        {
            "name": "vector-search-server",
            "image": "your-account.dkr.ecr.us-east-1.amazonaws.com/qdrant-service:latest",
            "portMappings": [
                {"containerPort": 8000, "protocol": "tcp"}
            ],
            "environment": [
                {"name": "HOST", "value": "localhost"},
                {"name": "PORT", "value": "6333"},
                {"name": "COLLECTION_NAME", "value": "products"}
            ],
            "dependsOn": [
                {"containerName": "qdrant-db", "condition": "START"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/qdrant-service",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "vector-search"
                }
            }
        }
    ]
}
```

### Phase 4: ECS Service Deployment

```bash
# 1. Register task definition
aws ecs register-task-definition --cli-input-json file://qdrant-task-definition.json

# 2. Create ECS service
aws ecs create-service \
    --cluster your-cluster \
    --service-name qdrant-service \
    --task-definition qdrant-service:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"

# 3. Set up Application Load Balancer (ALB)
# Configure ALB target groups and listeners via AWS Console
```

### Phase 5: CI/CD Pipeline

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to ECS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and push Docker image
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
          docker build -f Dockerfile.ecs -t qdrant-service .
          docker tag qdrant-service:latest ${{ secrets.ECR_REGISTRY }}/qdrant-service:latest
          docker push ${{ secrets.ECR_REGISTRY }}/qdrant-service:latest
      
      - name: Update ECS service
        run: |
          aws ecs update-service --cluster your-cluster --service qdrant-service --force-new-deployment
```

---

## Comparison & Recommendations

| Strategy | Complexity | Cost | Scalability | Maintenance | Best For |
|----------|------------|------|-------------|-------------|----------|
| **Docker (Strategy 1)** | Medium | Low | High | Medium | Most use cases |
| **Native Python (Strategy 2)** | High | Low | Medium | High | Full control needed |
| **ECS/Fargate (Strategy 3)** | High | High | Very High | Low | Enterprise/production |

### Recommendation

**Strategy 1 (Docker)** is recommended for most deployments because it:
- Provides good isolation and portability
- Balances complexity with functionality
- Easy to scale and maintain
- Works well for both development and production

**Choose Strategy 2** if you need maximum control over the environment or have specific performance requirements.

**Choose Strategy 3** if you're already heavily invested in AWS and need enterprise-grade scalability and management.

---

## Troubleshooting

### Common Issues

#### 1. Docker Services Not Starting
```bash
# Check Docker logs
docker logs vector-search-server
docker logs qdrant-db
docker logs search-ui

# Check Docker service status
docker-compose -f docker-compose.prod.yml ps
```

#### 2. Port Conflicts
```bash
# Check what's using the ports
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :8501
sudo netstat -tlnp | grep :6333

# Kill processes if needed
sudo kill -9 <PID>
```

#### 3. Memory Issues
```bash
# Check memory usage
free -h
docker stats

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Qdrant Connection Issues
```bash
# Test Qdrant connectivity
curl http://localhost:6333/health

# Check Qdrant logs
docker logs qdrant-db

# Verify collection exists
curl http://localhost:6333/collections
```

#### 5. Model Loading Issues
```bash
# Check model cache
ls -la ~/.cache/sentence_transformers/

# Clear cache if needed
rm -rf ~/.cache/sentence_transformers/

# Check available memory
free -h
```

### Performance Optimization

#### 1. Increase Docker Resources
```bash
# Edit Docker daemon configuration
sudo nano /etc/docker/daemon.json

# Add memory and CPU limits
{
  "default-memory": "4g",
  "default-cpus": "2"
}

# Restart Docker
sudo systemctl restart docker
```

#### 2. Optimize Qdrant Configuration
```bash
# Create custom Qdrant config
cat > qdrant_config.yaml << 'EOF'
storage:
  performance:
    max_search_threads: 4
    max_optimization_threads: 2

service:
  http_port: 6333
  grpc_port: 6334

cluster:
  enabled: false
EOF

# Update docker-compose to use custom config
```

#### 3. Monitor Performance
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Monitor system resources
htop
iotop
nethogs

# Monitor Docker resources
docker stats
```

### Backup and Recovery

#### 1. Backup Qdrant Data
```bash
# Create backup script
cat > backup_qdrant.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup Qdrant storage
docker exec qdrant-db tar -czf /tmp/qdrant_backup_$DATE.tar.gz /qdrant/storage
docker cp qdrant-db:/tmp/qdrant_backup_$DATE.tar.gz $BACKUP_DIR/

# Backup application data
tar -czf $BACKUP_DIR/app_data_$DATE.tar.gz data/ logs/

echo "Backup completed: $BACKUP_DIR/qdrant_backup_$DATE.tar.gz"
EOF

chmod +x backup_qdrant.sh

# Schedule daily backups
echo "0 2 * * * /home/ubuntu/backups/backup_qdrant.sh" | crontab -
```

#### 2. Restore from Backup
```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore Qdrant data
docker cp backup_file.tar.gz qdrant-db:/tmp/
docker exec qdrant-db tar -xzf /tmp/backup_file.tar.gz -C /

# Restore application data
tar -xzf app_data_backup.tar.gz

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

---

## Security Considerations

### 1. Network Security
- Configure security groups to allow only necessary ports
- Use VPC for network isolation
- Implement SSL/TLS for production deployments

### 2. Access Control
- Use IAM roles and policies (AWS)
- Implement API authentication
- Regular security updates

### 3. Data Protection
- Encrypt data at rest and in transit
- Regular backups
- Monitor access logs

---

## Maintenance

### Regular Tasks
1. **Weekly**: Check service logs and performance
2. **Monthly**: Update system packages and dependencies
3. **Quarterly**: Review and update security configurations
4. **As needed**: Scale resources based on usage patterns

### Monitoring Setup
```bash
# Install monitoring tools
sudo apt install -y prometheus node-exporter grafana

# Configure basic monitoring
# (Detailed monitoring setup would require additional configuration)
```

---

This deployment guide provides comprehensive instructions for deploying the Qdrant Vector Search Service to EC2 instances using three different strategies. Choose the strategy that best fits your requirements and follow the step-by-step instructions provided. 