#!/bin/bash

# Application Services Setup Script  
# Run this AFTER setup-aws.sh to deploy and setup vector search application
# This script will:
# 1. Git clone the application repository
# 2. Create Python virtual environment  
# 3. Install requirements
# 4. Create systemd services for FastAPI and Streamlit
# 5. Start all services

set -e

echo "Deploying Vector Search Application from Git..."
echo "This script deploys the complete application with services"
echo "=============================================="

# Configuration - MODIFY THESE VALUES
GIT_REPO_URL="${GIT_REPO_URL:-}"  # Set this environment variable or modify here
APP_DIR_NAME="${APP_DIR_NAME:-vector-search-app}"
GIT_BRANCH="${GIT_BRANCH:-main}"

if [[ -z "$GIT_REPO_URL" ]]; then
    echo "[ERROR] ERROR: GIT_REPO_URL not set!"
    echo "Please set it as environment variable or modify the script:"
    echo "export GIT_REPO_URL='https://github.com/your-username/your-repo.git'"
    echo "Or run: GIT_REPO_URL='your-repo-url' $0"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

print_header "Git Repository Deployment"

# Clean up any existing deployment
if [[ -d "$APP_DIR_NAME" ]]; then
    print_warning "Existing deployment found at $APP_DIR_NAME"
    read -p "Remove and redeploy? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing existing deployment..."
        rm -rf "$APP_DIR_NAME"
    else
        print_status "Using existing deployment..."
        cd "$APP_DIR_NAME"
        CURRENT_DIR=$(pwd)
        print_status "Current directory: $CURRENT_DIR"
        # Skip to validation
    fi
fi

# Clone repository if not using existing
if [[ ! -d "$APP_DIR_NAME" ]]; then
    print_status "Cloning repository from: $GIT_REPO_URL"
    if ! git clone -b "$GIT_BRANCH" "$GIT_REPO_URL" "$APP_DIR_NAME"; then
        print_error "Failed to clone repository"
        print_status "Please check:"
        print_status "1. Repository URL is correct: $GIT_REPO_URL"
        print_status "2. Branch exists: $GIT_BRANCH"  
        print_status "3. You have access to the repository"
        exit 1
    fi
    
    cd "$APP_DIR_NAME"
    CURRENT_DIR=$(pwd)
    print_status "[OK] Repository cloned successfully"
    print_status "Current directory: $CURRENT_DIR"
fi

print_header "Application Structure Validation"

# Check if we're in the right place
if [[ ! -f "app/main.py" ]]; then
    print_error "app/main.py not found in repository."
    print_status "Repository contents:"
    ls -la
    print_status "Expected structure:"
    print_status "  app/main.py"
    print_status "  search_ui/search.py"
    print_status "  requirements.txt"
    exit 1
fi

if [[ ! -f "search_ui/search.py" ]]; then
    print_error "search_ui/search.py not found. Please ensure your repository structure is complete."
    exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
    print_error "requirements.txt not found in repository."
    exit 1
fi

print_status "[OK] Application structure validated"

print_header "Python Environment Setup"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_status "[OK] Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate and install requirements
print_status "Installing Python requirements..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

print_status "[OK] Requirements installed successfully"

# Verify critical packages
if [[ ! -f "venv/bin/uvicorn" ]]; then
    print_error "uvicorn not found after installation. Check requirements.txt"
    exit 1
fi

if [[ ! -f "venv/bin/streamlit" ]]; then
    print_error "streamlit not found after installation. Check requirements.txt"
    exit 1
fi

print_status "[OK] Application deployment completed"

# Detect system resources for optimization
CPU_COUNT=$(nproc)
MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
print_status "Instance resources: $CPU_COUNT vCPU, ${MEMORY_GB}GB RAM"

# Set optimal configuration based on instance size
if [[ $MEMORY_GB -lt 4 ]]; then
    WORKERS=1
    print_warning "Small instance detected. Using 1 worker."
elif [[ $MEMORY_GB -lt 8 ]]; then
    WORKERS=1
    print_status "Medium instance detected. Using 1 worker."
else
    WORKERS=2
    print_status "Large instance detected. Using 2 workers."
fi

# Check if Qdrant is running
print_header "Checking Prerequisites"
if ! curl -s http://localhost:6333/health > /dev/null 2>&1; then
    print_error "Qdrant is not running. Please ensure setup-aws.sh completed successfully."
    print_status "Check Qdrant status: sudo systemctl status qdrant"
    print_status "If using Docker: cd ~/qdrant-docker && sudo docker-compose ps"
    exit 1
fi
print_status "[OK] Qdrant is running"

# Create or verify .env file
if [[ ! -f ".env" ]]; then
    if [[ -f ~/sample.env ]]; then
        print_status "Copying sample.env to .env"
        cp ~/sample.env .env
    else
        print_status "Creating basic .env file"
        cat > .env <<EOF
# Vector Search Service Configuration
HOST=localhost
PORT=6333
COLLECTION_NAME=products_fast
SEARCH_API_HOST=0.0.0.0
SEARCH_API_PORT=8000
STREAMLIT_SERVER_PORT=8501
DEBUG_UI=false
LOG_LEVEL=INFO
LOG_PATH=logs/service.log
EOF
    fi
fi

# Create logs directory
mkdir -p logs
print_status "Created logs directory"

print_header "Creating Systemd Services"

# Clean up any existing broken service files
print_status "Cleaning up any existing service files..."
sudo systemctl stop vector-api vector-ui 2>/dev/null || true
sudo systemctl disable vector-api vector-ui 2>/dev/null || true
sudo rm -f /etc/systemd/system/vector-api.service
sudo rm -f /etc/systemd/system/vector-ui.service
sudo systemctl daemon-reload

# Create FastAPI service
print_status "Creating vector-api service..."
sudo tee /etc/systemd/system/vector-api.service > /dev/null <<EOF
[Unit]
Description=Vector Search API Service
Documentation=https://github.com/your-repo/vector-search
After=network.target qdrant.service
Wants=qdrant.service
StartLimitBurst=5
StartLimitInterval=60

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
Environment=PYTHONPATH=$CURRENT_DIR
EnvironmentFile=$CURRENT_DIR/.env

# Startup command
ExecStart=$CURRENT_DIR/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $WORKERS

# Restart configuration
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30

# Resource limits
LimitNOFILE=65535

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$CURRENT_DIR

# Logging
StandardOutput=append:$CURRENT_DIR/logs/vector-api.log
StandardError=append:$CURRENT_DIR/logs/vector-api.log

[Install]
WantedBy=multi-user.target
EOF

# Create Streamlit UI service
print_status "Creating vector-ui service..."
sudo tee /etc/systemd/system/vector-ui.service > /dev/null <<EOF
[Unit]
Description=Vector Search UI Service
Documentation=https://github.com/your-repo/vector-search
After=network.target vector-api.service
Wants=vector-api.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
Environment=PYTHONPATH=$CURRENT_DIR
EnvironmentFile=$CURRENT_DIR/.env

# Streamlit startup
ExecStart=$CURRENT_DIR/venv/bin/streamlit run search_ui/search.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false

# Restart configuration
Restart=always
RestartSec=15
TimeoutStartSec=45
TimeoutStopSec=15

# Resource limits
LimitNOFILE=4096

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=append:$CURRENT_DIR/logs/vector-ui.log
StandardError=append:$CURRENT_DIR/logs/vector-ui.log

[Install]
WantedBy=multi-user.target
EOF

print_status "[OK] Systemd services created"

# Test application manually first
print_header "Testing Application"
print_status "Testing FastAPI application..."

# Quick test to ensure the app can start
timeout 10s bash -c "cd $CURRENT_DIR && source venv/bin/activate && python -c 'from app.main import app; print(\"[OK] FastAPI app imports successfully\")'" || {
    print_error "FastAPI application has import errors. Please fix before starting services."
    print_status "Try manually: cd $CURRENT_DIR && source venv/bin/activate && python -c 'from app.main import app'"
    exit 1
}

print_status "[OK] FastAPI application test passed"

# Start and enable services
print_header "Starting Services"
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable vector-api
sudo systemctl enable vector-ui
print_status "[OK] Services enabled for auto-start"

# Start API service
print_status "Starting vector-api service..."
if sudo systemctl start vector-api; then
    print_status "[OK] API service started"
else
    print_error "Failed to start API service. Check logs:"
    print_error "sudo journalctl -u vector-api -n 20"
    exit 1
fi

# Wait for API to be ready
print_status "Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_status "[OK] API is responding"
        break
    fi
    if [[ $i -eq 30 ]]; then
        print_error "API failed to respond after 30 seconds"
        print_error "Check logs: sudo journalctl -u vector-api -n 20"
        exit 1
    fi
    sleep 1
    echo -n "."
done
echo

# Start UI service
print_status "Starting vector-ui service..."
if sudo systemctl start vector-ui; then
    print_status "[OK] UI service started"
else
    print_error "Failed to start UI service. Check logs:"
    print_error "sudo journalctl -u vector-ui -n 20"
    exit 1
fi

# Wait for UI to be ready (Streamlit takes longer)
print_status "Waiting for UI to be ready..."
for i in {1..45}; do
    if curl -s --max-time 3 http://localhost:8501 > /dev/null 2>&1; then
        print_status "[OK] UI is responding"
        break
    fi
    if [[ $i -eq 45 ]]; then
        print_warning "UI may still be starting (Streamlit can take time)"
        print_status "Check status: sudo systemctl status vector-ui"
    fi
    sleep 1
    if [[ $((i % 5)) -eq 0 ]]; then
        echo -n " ${i}s"
    else
        echo -n "."
    fi
done
echo

# Final verification
print_header "Service Verification"

# Check service statuses
print_status "Checking service statuses..."
if sudo systemctl is-active --quiet qdrant; then
    echo "[OK] Qdrant: Running"
else
    echo "[ERROR] Qdrant: Not running"
fi

if sudo systemctl is-active --quiet vector-api; then
    echo "[OK] Vector API: Running"
else
    echo "[ERROR] Vector API: Not running"
fi

if sudo systemctl is-active --quiet vector-ui; then
    echo "[OK] Vector UI: Running"
else
    echo "[ERROR] Vector UI: Not running"
fi

# Get public IP for display
PUBLIC_IP=$(curl -s --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")

echo
print_header "Application Services Setup Complete"
echo "=============================================="
echo "[OK] FastAPI service created and started"
echo "[OK] Streamlit UI service created and started" 
echo "[OK] Services enabled for auto-start on boot"
echo "[OK] Logging configured to logs/ directory"
echo "=============================================="
echo
echo "🌐 Access Your Application:"
echo "API Documentation: http://$PUBLIC_IP:8000/docs"
echo "Interactive API:   http://$PUBLIC_IP:8000"
echo "Search UI:         http://$PUBLIC_IP:8501"
echo "Qdrant Dashboard:  http://$PUBLIC_IP:6333/dashboard"
echo
echo "[CONFIG] Service Management Commands:"
echo "sudo systemctl status vector-api vector-ui qdrant"
echo "sudo systemctl restart vector-api vector-ui"
echo "sudo systemctl stop vector-api vector-ui"
echo "sudo systemctl disable vector-api vector-ui  # (disable auto-start)"
echo
echo "[STATS] Monitoring Commands:"
echo "sudo journalctl -u vector-api -f"
echo "sudo journalctl -u vector-ui -f"
echo "tail -f logs/vector-api.log"
echo "tail -f logs/vector-ui.log"
echo
echo "[SEARCH] Health Check:"
echo "curl http://localhost:6333/health  # Qdrant"
echo "curl http://localhost:8000/health  # API"
echo "curl http://localhost:8501         # UI"
echo
echo "[FOLDER] Application Details:"
echo "Directory: $CURRENT_DIR"
echo "Virtual Environment: $CURRENT_DIR/venv"
echo "Configuration: $CURRENT_DIR/.env"
echo "Logs: $CURRENT_DIR/logs/"
echo "Workers: $WORKERS (optimized for ${MEMORY_GB}GB RAM)"
echo
echo "🚨 If services fail to start:"
echo "1. Check logs: sudo journalctl -u vector-api -n 50"
echo "2. Test manually: cd $CURRENT_DIR && source venv/bin/activate && python -m uvicorn app.main:app"
echo "3. Verify dependencies: pip list | grep -E '(fastapi|uvicorn|qdrant|streamlit)'"
echo
print_status "Your Vector Search application is now running as systemd services!"