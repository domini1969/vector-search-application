# Vector Search Application Deployment Guide

**Complete guide for local development setup and AWS production deployment.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Local Setup and Development](#local-setup-and-development)
- [AWS Production Deployment](#aws-production-deployment)
- [Post-Deployment Management](#post-deployment-management)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This guide covers two deployment scenarios:

1. **Local Development Setup**: Run the application on your local machine for development and testing
2. **AWS Production Deployment**: Deploy to AWS Linux for production use

**Application Components:**
- FastAPI backend with search endpoints (/query, /dense, /sparse, /hybrid)
- Streamlit interactive search UI
- Qdrant v1.15.2 vector database
- Dense + BM25 search with native RRF fusion

---

## 💻 Local Setup and Development

### Prerequisites

- Python 3.8+ installed
- Git installed
- 8GB+ RAM recommended
- Docker (optional, for Qdrant container)

### Step 1: Clone and Setup Project

```bash
# Clone the repository
git clone https://github.com/domini1969/vector-search-application.git
cd vector-search-application

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your local settings
# Key settings for local development:
HOST=localhost
PORT=6333
COLLECTION_NAME=products_fast
SEARCH_API_HOST=127.0.0.1
SEARCH_API_PORT=8000
STREAMLIT_SERVER_PORT=8501
MAX_SEARCH_THREADS=4
HNSW_EF=100
DEBUG_UI=true
LOG_LEVEL=INFO
```

### Step 3: Setup Qdrant Database

#### Option A: Docker (Recommended)
```bash
# Create Qdrant Docker setup
mkdir -p qdrant-docker
cd qdrant-docker

# Create docker-compose.yml
cat > docker-compose.yml <<EOF
services:
  qdrant:
    image: qdrant/qdrant:v1.15.0
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
EOF

# Start Qdrant
docker-compose up -d

# Verify Qdrant is running
curl http://localhost:6333/health
```

#### Option B: Binary Installation (Linux/Mac)
```bash
# Download Qdrant binary
wget https://github.com/qdrant/qdrant/releases/download/v1.15.0/qdrant-x86_64-unknown-linux-gnu.tar.gz
tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz

# Run Qdrant
./qdrant &

# Verify Qdrant is running
curl http://localhost:6333/health
```

### Step 4: Prepare Data (Optional)

```bash
# Create data directory structure
mkdir -p data/import

# Place your data files in data/import/
# Supported formats: CSV, JSON, Parquet
# Example structure:
# data/
#   import/
#     products.csv
#     documents.json
```

### Step 5: Index Your Data

```bash
# Activate virtual environment if not already active
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Run indexing script with options
python scripts/indexing.py

# Indexing modes available:
# --mode dense    - Dense vectors only (semantic search)
# --mode sparse   - BM25 sparse vectors only (keyword search)  
# --mode hybrid   - Both dense + sparse (recommended)

# Examples:
python scripts/indexing.py --mode hybrid    # Default: both dense and sparse
python scripts/indexing.py --mode dense     # Semantic search only
python scripts/indexing.py --mode sparse    # Keyword search only

# Additional indexing options:
python scripts/indexing.py \
  --mode hybrid \
  --collection products_fast \
  --batch-size 2048 \
  --quantization scalar \
  --threads 4

# Monitor indexing progress
# The script will show progress and create collections in Qdrant
```

### Step 6: Start the Application

#### Terminal 1: Start FastAPI Backend
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Start the API server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# API will be available at:
# - Interactive docs: http://localhost:8000/docs
# - Health check: http://localhost:8000/health
```

#### Terminal 2: Start Streamlit UI
```bash
# Activate virtual environment (in new terminal)
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Start the UI
streamlit run search_ui/search.py --server.port 8501 --server.address 127.0.0.1

# UI will be available at:
# - Search interface: http://localhost:8501
```

### Step 7: Test Local Setup

```bash
# Test Qdrant
curl http://localhost:6333/health

# Test API endpoints
curl http://localhost:8000/health
curl "http://localhost:8000/api/search/query?q=test&count=5&mode=hybrid"
curl "http://localhost:8000/api/search/dense?query=test&limit=5"
curl "http://localhost:8000/api/search/sparse?query=test&limit=5"
curl "http://localhost:8000/api/search/hybrid?query=test&limit=5"

# Test UI (open in browser)
open http://localhost:8501  # Mac
# Or manually navigate to http://localhost:8501
```

### Local Development Workflow

```bash
# Daily development routine:

# 1. Start services
cd qdrant-docker && docker-compose up -d  # Start Qdrant
source venv/bin/activate                   # Activate Python env

# 2. Start application (in separate terminals)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload  # API
streamlit run search_ui/search.py --server.port 8501                   # UI

# 3. Develop and test
# Make changes to code, test endpoints, iterate

# 4. Stop services when done
# Ctrl+C to stop API and UI
cd qdrant-docker && docker-compose down  # Stop Qdrant
```

---

## ☁️ AWS Production Deployment

### Prerequisites

#### AWS Requirements:
- EC2 instance running Amazon Linux 2 or Ubuntu 20.04+
- Instance specs: Minimum 2 vCPU, 4GB RAM (Recommended: 4 vCPU, 15GB RAM)
- SSH access to your instance
- Security groups allowing ports: 22, 6333, 8000, 8501
- Internet access for downloading packages

#### Local Requirements:
- Git Bash (Windows) or Terminal (Linux/Mac)
- GitHub account with repository access
- GitHub Personal Access Token ([Create one here](https://github.com/settings/tokens))

### Step 1: Prepare Code for Deployment (Local Machine)

```bash
# Navigate to project directory
cd vector-search-application/deploy

# Deploy from Windows to GitHub
bash deploy-ToGit-from-windows.sh

# This script will:
# - Clean and initialize Git repository
# - Fix shell scripts for Linux compatibility
# - Validate security (no secrets in code)
# - Commit and push to GitHub
# - Provide AWS deployment commands
```

**Authentication**: When prompted, use:
- Username: `your-github-username`
- Password: `your-github-personal-access-token` (NOT your GitHub password)

### Step 2: Connect to AWS Instance

```bash
# SSH to your AWS instance
ssh -i your-key.pem ec2-user@your-aws-instance-ip

# For Ubuntu instances:
ssh -i your-key.pem ubuntu@your-aws-instance-ip
```

### Step 3: Clone and Deploy Application (AWS Instance)

#### Quick One-Command Deployment:
```bash
git clone https://github.com/domini1969/vector-search-application.git && cd vector-search-application/deploy && chmod +x *.sh && ./deploy-RunAt-aws.sh
```

#### Step-by-Step Deployment:
```bash
# Clone repository
git clone https://github.com/domini1969/vector-search-application.git
cd vector-search-application/deploy

# Make scripts executable
chmod +x *.sh

# Normal deployment (recommended)
./deploy-RunAt-aws.sh

# OR: Force clean deployment (if previous installation exists)
./deploy-RunAt-aws.sh --clean
```

### Step 4: Deployment Process Details

The AWS deployment script performs these phases:

#### Phase 1: Pre-flight Checks
- Validates user permissions (not root)
- Detects operating system
- Confirms AWS environment

#### Phase 2: Repository Setup
- Clones/updates code from GitHub
- Validates application structure
- Makes scripts executable

#### Phase 3: Environment Setup
- Smart cleanup detection (only prompts if existing services found)
- Optional cleanup of previous installations
- Continues with existing environment if no issues

#### Phase 4: Infrastructure Setup
- Installs Docker and Docker Compose
- Sets up Qdrant v1.15.2 vector database
- Configures Python environment
- Installs system dependencies
- Optimizes settings for instance size

#### Phase 5: Application Deployment
- Creates Python virtual environment
- Installs application requirements
- Creates systemd services:
  - `qdrant`: Vector database service
  - `vector-api`: FastAPI backend service
  - `vector-ui`: Streamlit frontend service
- Starts all services automatically

#### Phase 6: Service Verification
- Waits for services to initialize
- Checks systemd service status
- Validates endpoints are responding
- Reports deployment success/issues

### Step 5: Verify Deployment

```bash
# Check service status
sudo systemctl status qdrant vector-api vector-ui

# Test endpoints
curl http://localhost:6333/health  # Qdrant
curl http://localhost:8000/health  # API
curl http://localhost:8501         # UI

# Check application logs
tail -f logs/vector-api.log
tail -f logs/vector-ui.log
```

### Step 6: Index Your Data (Production)

```bash
# Navigate to application directory
cd vector-search-application

# Activate virtual environment
source venv/bin/activate

# Ensure your data files are in data/import/
ls -la data/import/

# Run indexing with production settings
python scripts/indexing.py --mode hybrid

# Indexing modes for production:
# --mode hybrid   - Both dense + sparse (recommended for production)
# --mode dense    - Dense vectors only (semantic search)
# --mode sparse   - BM25 sparse vectors only (keyword search)

# Production optimizations (4 vCPU, 15GB RAM AWS instance):
python scripts/indexing.py \
  --mode hybrid \
  --collection products_fast \
  --batch-size 2048 \
  --embedding-batch-size 4096 \
  --quantization scalar \
  --threads 4 \
  --storage memory

# Monitor progress and verify collections created
curl http://localhost:6333/collections

# Verify indexing completed successfully
curl http://localhost:6333/collections/products_fast
```

### Step 7: Configure Security Groups

Ensure your AWS Security Group allows these inbound rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | FastAPI backend |
| Custom TCP | TCP | 8501 | 0.0.0.0/0 | Streamlit UI |
| Custom TCP | TCP | 6333 | 0.0.0.0/0 | Qdrant dashboard |

### Step 8: Access Your Production Application

After successful deployment, access your application at:

| Service | URL | Purpose |
|---------|-----|---------|
| **API Documentation** | `http://YOUR-AWS-IP:8000/docs` | Interactive API documentation |
| **Search Interface** | `http://YOUR-AWS-IP:8501` | User-friendly search UI |
| **Qdrant Dashboard** | `http://YOUR-AWS-IP:6333/dashboard` | Vector database management |
| **Health Check** | `http://YOUR-AWS-IP:8000/health` | API health status |

---

## 🔧 Post-Deployment Management

### Service Management Commands

```bash
# Check service status
sudo systemctl status qdrant vector-api vector-ui

# Start services
sudo systemctl start qdrant vector-api vector-ui

# Stop services
sudo systemctl stop vector-api vector-ui

# Restart services
sudo systemctl restart vector-api vector-ui

# Enable auto-start on boot
sudo systemctl enable qdrant vector-api vector-ui

# Disable auto-start
sudo systemctl disable vector-api vector-ui
```

### Log Management

```bash
# View live service logs
sudo journalctl -u vector-api -f
sudo journalctl -u vector-ui -f
sudo journalctl -u qdrant -f

# View application logs
tail -f logs/vector-api.log
tail -f logs/vector-ui.log

# View recent errors
sudo journalctl -u vector-api -n 50 --no-pager
sudo journalctl -u qdrant -n 20 --no-pager
```

### Health Monitoring

```bash
# API health checks
curl http://localhost:8000/health
curl http://localhost:6333/health

# Search functionality tests
curl "http://localhost:8000/api/search/query?q=test&count=5&mode=hybrid"
curl "http://localhost:8000/api/search/dense?query=sample&limit=3"
curl "http://localhost:8000/api/search/sparse?query=sample&limit=3"

# Performance test
time curl "http://localhost:8000/api/search/hybrid?query=performance&limit=10"
```

### Backup and Maintenance

```bash
# Backup Qdrant data
sudo mkdir -p /backup/qdrant/$(date +%Y%m%d)
sudo cp -r /var/lib/qdrant/* /backup/qdrant/$(date +%Y%m%d)/

# Update application code
cd vector-search-application
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart vector-api vector-ui

# Rotate logs (if needed)
sudo journalctl --vacuum-time=7d
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Services Not Starting

```bash
# Check service status and logs
sudo systemctl status vector-api
sudo journalctl -u vector-api -n 50

# Common fixes:
# - Check Python virtual environment
source venv/bin/activate
python -c "from app.main import app; print('Import successful')"

# - Reinstall requirements
pip install -r requirements.txt --upgrade

# - Restart services
sudo systemctl restart vector-api vector-ui
```

#### 2. Qdrant Connection Issues

```bash
# Check Qdrant status
sudo systemctl status qdrant
curl http://localhost:6333/health

# For Docker-based Qdrant:
cd ~/qdrant-docker
sudo docker-compose ps
sudo docker-compose logs qdrant

# Restart Qdrant
sudo systemctl restart qdrant
# OR for Docker:
sudo docker-compose restart
```

#### 3. Port Access Issues

```bash
# Check if ports are in use
sudo netstat -tuln | grep -E ":6333|:8000|:8501"

# Check firewall (if applicable)
sudo iptables -L

# Kill conflicting processes
sudo lsof -i :8000
sudo kill -9 <PID>
```

#### 4. Permission Issues

```bash
# Fix application permissions
sudo chown -R ec2-user:ec2-user /home/ec2-user/vector-search-application

# Fix script permissions
chmod +x deploy/*.sh

# Fix Qdrant data permissions
sudo chown -R ec2-user:ec2-user /var/lib/qdrant
```

#### 5. Memory/Performance Issues

```bash
# Check system resources
free -h
df -h
top

# Optimize for smaller instances (edit .env):
MAX_SEARCH_THREADS=2
HNSW_EF=50
SEARCH_CACHE_MAX_SIZE=1000

# Restart services after changes
sudo systemctl restart vector-api vector-ui
```

#### 6. Network/DNS Issues

```bash
# Test external connectivity
curl -I https://github.com
ping 8.8.8.8

# Check security groups (AWS Console)
# Ensure ports 8000, 8501, 6333 are open

# Test local connectivity
curl http://localhost:8000/health
curl http://127.0.0.1:8501
```

### Complete Reset (When Everything Fails)

```bash
# Clean deployment (removes everything and starts fresh)
cd vector-search-application/deploy
./cleanup-aws.sh

# Then redeploy
./deploy-RunAt-aws.sh --clean
```

### Log Collection for Support

```bash
# Collect comprehensive debug information
echo "=== System Info ===" > debug.log
uname -a >> debug.log
free -h >> debug.log
df -h >> debug.log

echo "=== Service Status ===" >> debug.log
sudo systemctl status qdrant vector-api vector-ui >> debug.log

echo "=== Recent Logs ===" >> debug.log
sudo journalctl -u vector-api -n 50 >> debug.log
sudo journalctl -u qdrant -n 20 >> debug.log

echo "=== Application Logs ===" >> debug.log
tail -100 logs/vector-api.log >> debug.log 2>/dev/null || echo "No app logs" >> debug.log

echo "=== Network Status ===" >> debug.log
sudo netstat -tuln | grep -E ":6333|:8000|:8501" >> debug.log

# Share debug.log for troubleshooting
```

---

## 🎯 Summary

### Local Development
1. Clone repository and setup Python environment
2. Install dependencies with `pip install -r requirements.txt`
3. Start Qdrant (Docker or binary)
4. Configure `.env` file
5. Index data with `python scripts/indexing.py`
6. Start API with `uvicorn` and UI with `streamlit`
7. Test at http://localhost:8000/docs and http://localhost:8501

### AWS Production Deployment
1. **Local**: Run `bash deploy-ToGit-from-windows.sh` to push to GitHub
2. **AWS**: Run `./deploy-RunAt-aws.sh` to deploy complete application
3. **Result**: Live application with systemd services and monitoring

**Access URLs** (replace YOUR-AWS-IP):
- API Documentation: `http://YOUR-AWS-IP:8000/docs`
- Search Interface: `http://YOUR-AWS-IP:8501`
- Qdrant Dashboard: `http://YOUR-AWS-IP:6333/dashboard`

---

*Last Updated: January 2025*