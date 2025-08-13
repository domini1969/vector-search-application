#!/bin/bash

# AWS Linux Setup Script for Vector Search Service
# Infrastructure setup with Docker and Qdrant
# Version: 2.0

set -e  # Exit on any error

echo "Starting AWS Linux Setup for Vector Search Service..."
echo "Components: Docker, Qdrant 1.15, Python environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Detect OS and instance type
print_header "System Detection"
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    print_error "Cannot detect OS"
    exit 1
fi

print_status "Detected OS: $OS $VER"

# Detect instance resources
CPU_COUNT=$(nproc)
MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
print_status "Instance resources: $CPU_COUNT vCPU, ${MEMORY_GB}GB RAM"

# Set optimal configuration based on instance size
if [[ $MEMORY_GB -lt 4 ]]; then
    PRESET="memory-efficient"
    BATCH_SIZE=512
    EMBEDDING_BATCH_SIZE=1024
    MAX_THREADS=2
    print_warning "Small instance detected. Using memory-efficient settings."
elif [[ $MEMORY_GB -lt 8 ]]; then
    PRESET="balanced"
    BATCH_SIZE=768
    EMBEDDING_BATCH_SIZE=1536
    MAX_THREADS=4
    print_status "Medium instance detected. Using balanced settings."
else
    PRESET="max-speed"
    BATCH_SIZE=1024
    EMBEDDING_BATCH_SIZE=2048
    MAX_THREADS=$CPU_COUNT
    print_status "Large instance detected. Using max-speed settings."
fi

# Update system
print_header "System Update"
if [[ "$OS" == *"Amazon Linux"* ]]; then
    sudo yum update -y
    print_status "Amazon Linux updated"
elif [[ "$OS" == *"Ubuntu"* ]]; then
    sudo apt update && sudo apt upgrade -y
    print_status "Ubuntu updated"
else
    print_warning "Unsupported OS. Proceeding with generic commands..."
fi

# Install system dependencies
print_header "Installing System Dependencies"
if [[ "$OS" == *"Amazon Linux"* ]]; then
    # Handle curl package conflict in Amazon Linux 2023
    if [[ "$VER" == "2023" ]]; then
        # Amazon Linux 2023 has curl-minimal by default, which is sufficient for our needs
        # Skip installing full curl to avoid the conflict
        print_status "Installing packages for Amazon Linux 2023 (using curl-minimal)..."
        sudo dnf install -y git python3 python3-pip python3-devel gcc gcc-c++ make wget htop
        sudo dnf install -y atlas-devel lapack-devel blas-devel
        print_status "Using existing curl-minimal (sufficient for HTTP requests)"
    else
        # Amazon Linux 2 (original version)
        sudo yum install -y git python3 python3-pip python3-devel gcc gcc-c++ make wget curl htop
        sudo yum install -y atlas-devel lapack-devel blas-devel
    fi
    print_status "Amazon Linux dependencies installed"
elif [[ "$OS" == *"Ubuntu"* ]]; then
    sudo apt install -y git python3 python3-pip python3-venv build-essential wget curl htop
    sudo apt install -y libatlas-base-dev liblapack-dev libblas-dev
    print_status "Ubuntu dependencies installed"
fi

# Install Docker if requested
if [[ "$1" == "--docker" ]]; then
    print_header "Docker Installation"
    
    if [[ "$OS" == *"Amazon Linux"* ]]; then
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker $USER
        
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$OS" == *"Ubuntu"* ]]; then
        sudo apt install -y docker.io docker-compose
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker $USER
    fi
    
    print_status "Docker installation completed."
    print_warning "Please log out and back in for group changes to take effect."
    print_status "Then create docker-compose.yml and run: docker-compose up -d --build"
    exit 0
fi

# Install Qdrant 1.15 using Docker (preferred method)
print_header "Installing Qdrant 1.15 with Docker"

print_status "Installing Docker and Docker Compose..."

# Install Docker based on OS
if [[ "$OS" == *"Amazon Linux"* ]]; then
    if [[ "$VER" == "2023" ]]; then
        # Amazon Linux 2023
        sudo dnf update -y
        sudo dnf install -y docker
    else
        # Amazon Linux 2
        sudo yum update -y
        sudo yum install -y docker
    fi
    
    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker $USER
    
elif [[ "$OS" == *"Ubuntu"* ]]; then
    # Ubuntu
    sudo apt update
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker $USER
else
    print_warning "Unsupported OS for automatic Docker installation"
    print_error "Please install Docker manually and re-run this script"
    exit 1
fi

# Install Docker Compose
print_status "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="2.24.1"
sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create symlinks for both locations
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify Docker installation
print_status "Verifying Docker installation..."
if ! sudo docker --version; then
    print_error "Docker installation failed"
    exit 1
fi

if ! docker-compose --version; then
    print_error "Docker Compose installation failed"
    exit 1
fi

print_status "[OK] Docker and Docker Compose installed successfully"

# Note: User needs to log out and back in for group membership to take effect
print_warning "Docker group added to user. You may need to log out and back in for full Docker access."
# Create Qdrant Docker setup (proven working config)
print_status "Creating Qdrant Docker configuration..."
mkdir -p ~/qdrant-docker

cat > ~/qdrant-docker/docker-compose.yml <<EOF
services:
  qdrant:
    image: qdrant/qdrant:v1.15.0
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - /var/lib/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

print_status "[OK] Qdrant Docker configuration created with healthcheck"
QDRANT_METHOD="docker"

# Setup proper permissions first (critical for Docker)
print_status "Setting up proper permissions for Qdrant..."
sudo mkdir -p /var/lib/qdrant
sudo chown -R $USER:$USER /var/lib/qdrant
sudo chmod -R 755 /var/lib/qdrant

# Test Docker setup
print_status "Testing Docker setup..."
cd ~/qdrant-docker

# Pull the Qdrant image
print_status "Pulling Qdrant Docker image..."
if ! sudo docker pull qdrant/qdrant:v1.15.0; then
    print_error "Failed to pull Qdrant Docker image"
    print_status "Checking Docker daemon status..."
    sudo systemctl status docker --no-pager -l
    exit 1
fi

print_status "[OK] Qdrant Docker image pulled successfully"

# Clean up any existing containers
print_status "Cleaning up any existing Qdrant containers..."
sudo docker-compose down 2>/dev/null || true
sudo docker rm -f qdrant 2>/dev/null || true

# Create Qdrant data directory with proper permissions
sudo mkdir -p /var/lib/qdrant
sudo chown $USER:$USER /var/lib/qdrant
sudo mkdir -p /var/log/qdrant
sudo chown $USER:$USER /var/log/qdrant

# Create Qdrant configuration
print_status "Creating Qdrant configuration..."
cat > /tmp/qdrant-config.yaml <<EOF
service:
  http_port: 6333
  grpc_port: 6334
  host: 0.0.0.0
  enable_cors: true

storage:
  storage_path: /var/lib/qdrant
  snapshots_path: /var/lib/qdrant/snapshots
  on_disk_payload: false
  wal:
    wal_capacity_mb: 32
    wal_segments_ahead: 0

log_level: INFO
EOF

sudo mv /tmp/qdrant-config.yaml /var/lib/qdrant/config.yaml
sudo chown $USER:$USER /var/lib/qdrant/config.yaml

# Create Qdrant systemd service for Docker
print_status "Creating Qdrant systemd service for Docker..."

sudo tee /etc/systemd/system/qdrant.service > /dev/null <<EOF
[Unit]
Description=Qdrant Vector Database v1.15 (Docker)
Documentation=https://qdrant.tech/documentation/
After=network.target docker.service
Requires=docker.service
StartLimitBurst=5
StartLimitInterval=60

[Service]
Type=oneshot
RemainAfterExit=true
User=$USER
Group=$USER
WorkingDirectory=/home/$USER/qdrant-docker

# Use sudo for Docker commands since user group membership takes effect after relogin
ExecStart=/bin/bash -c 'cd /home/$USER/qdrant-docker && sudo /usr/local/bin/docker-compose up -d'
ExecStop=/bin/bash -c 'cd /home/$USER/qdrant-docker && sudo /usr/local/bin/docker-compose down'

TimeoutStartSec=120
TimeoutStopSec=60

# Restart policy
Restart=no

[Install]
WantedBy=multi-user.target
EOF

print_status "[OK] Qdrant systemd service created for Docker method"

# Set up Python environment
print_header "Setting up Python Environment"

# Just upgrade system Python packages - user will create their own venv
print_status "Upgrading system Python packages..."
python3 -m pip install --user --upgrade pip setuptools wheel

print_status "System Python environment ready"
print_status "You can create your virtual environment with:"
print_status "  python3 -m venv venv && source venv/bin/activate"

# Create sample environment configuration
print_header "Creating Sample Configuration"
cat > ~/sample.env <<EOF
# Sample .env file for Vector Search Service
# Copy this to your application directory and modify as needed

# Qdrant Configuration (v1.15)
HOST=localhost
PORT=6333
COLLECTION_NAME=products_fast

# Search API Configuration  
SEARCH_API_HOST=0.0.0.0
SEARCH_API_PORT=8000

# Performance Settings (Optimized for $MEMORY_GB GB RAM, $CPU_COUNT vCPU)
MAX_THREADS=$MAX_THREADS
EMBEDDING_BATCH_SIZE=$EMBEDDING_BATCH_SIZE
UPLOAD_BATCH_SIZE=$BATCH_SIZE

# UI Configuration
STREAMLIT_SERVER_PORT=8501
DEBUG_UI=false

# Logging
LOG_LEVEL=INFO
LOG_PATH=logs/service.log
EOF

print_status "Sample environment configuration created at ~/sample.env"
print_status "Copy this to your application directory when ready"

# Skip application services - user will manage their own application
print_header "Skipping Application Services"
print_status "No systemd services created for your application"
print_status "You will manage your own application startup"

# Create health monitoring script
print_status "Creating health monitoring..."
cat > ~/health-monitor-enhanced.sh <<EOF
#!/bin/bash
# Health Monitor for Vector Search Service

echo "=============================================="
echo "Vector Search Service Health Check"
echo "Time: \$(date)"
echo "Instance: $MEMORY_GB GB RAM, $CPU_COUNT vCPU"
echo "Configuration: $PRESET preset, $MAX_THREADS threads"
echo "=============================================="

# Function to check service
check_service() {
    local service=\$1
    local port=\$2
    local endpoint=\$3
    
    if curl -s -f --max-time 5 http://localhost:\$port\$endpoint > /dev/null 2>&1; then
        echo "[OK] \$service: Running (port \$port)"
        return 0
    else
        echo "[ERROR] \$service: Not responding (port \$port)"
        return 1
    fi
}

# Check services
check_service "Qdrant" "6333" "/health"
check_service "API" "8000" "/health"
check_service "UI" "8501" ""

# Check collections if Qdrant is running
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "   Qdrant API: Responding"
fi

# Check search methods if API is running  
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   Search API: Responding"
fi

# System resources
echo
echo "System Resources:"
MEMORY_USED=\$(free -h | grep '^Mem:' | awk '{print \$3}')
MEMORY_TOTAL=\$(free -h | grep '^Mem:' | awk '{print \$2}')
CPU_LOAD=\$(uptime | awk -F'load average:' '{ print \$2 }' | awk '{print \$1}' | tr -d ',')
DISK_USAGE=\$(df -h / | tail -1 | awk '{print \$5}')

echo "Memory: \$MEMORY_USED/\$MEMORY_TOTAL"
echo "CPU Load: \$CPU_LOAD"
echo "Disk Usage: \$DISK_USAGE"

# Process check
PYTHON_PROCESSES=\$(ps aux | grep -E "(uvicorn|streamlit)" | grep -v grep | wc -l)
echo "Python processes: \$PYTHON_PROCESSES"

echo "=============================================="
EOF

chmod +x ~/health-monitor-enhanced.sh

# Start Qdrant service with error handling
print_header "Starting Qdrant Service"

# Ensure proper permissions first
sudo mkdir -p /var/lib/qdrant
sudo chown -R $USER:$USER /var/lib/qdrant
sudo chmod 755 /var/lib/qdrant

sudo systemctl daemon-reload

# Start Qdrant
sudo systemctl enable qdrant
if ! sudo systemctl start qdrant; then
    print_error "Failed to start Qdrant service"
    sudo journalctl -u qdrant --no-pager -n 10
fi

# Wait for Qdrant to be ready
print_status "Waiting for Qdrant to start..."
QDRANT_READY=false

for i in {1..45}; do
    # Check if service is running
    if sudo systemctl is-active --quiet qdrant; then
        # Check if port is responding
        if curl -s --max-time 3 http://localhost:6333/health > /dev/null 2>&1; then
            print_status "[OK] Qdrant is running and responding"
            QDRANT_READY=true
            break
        fi
    fi
    
    # Show progress every 5 seconds
    if [[ $((i % 5)) -eq 0 ]]; then
        print_status "Still waiting... (${i}s)"
        sudo systemctl status qdrant --no-pager -l | head -3
    fi
    
    sleep 1
done

# Error handling if Qdrant failed to start
if [[ "$QDRANT_READY" != "true" ]]; then
    print_error "Qdrant failed to start properly after 45 seconds"
    print_status "Attempting Docker container restart..."
    
    cd ~/qdrant-docker
    
    # Show current status
    print_status "Docker container status:"
    sudo docker-compose ps
    
    # Show recent logs
    print_status "Container logs:"
    sudo docker-compose logs --tail=30 qdrant
    
    # Try restart approach
    print_status "Restarting Qdrant container..."
    sudo docker-compose down
    sleep 5
    sudo docker-compose up -d
    
    # Wait for restart
    print_status "Waiting for restarted container..."
    for j in {1..30}; do
        if curl -s http://localhost:6333/health > /dev/null 2>&1; then
            print_status "[OK] Qdrant restart successful"
            QDRANT_READY=true
            break
        fi
        sleep 1
    done
    
    # Final check
    if [[ "$QDRANT_READY" != "true" ]]; then
        print_error "[ERROR] Qdrant Docker setup failed"
        print_status "Container diagnostics:"
        sudo docker-compose ps
        sudo docker-compose logs qdrant
        print_status "Manual fix commands:"
        print_status "1. cd ~/qdrant-docker && sudo docker-compose down"
        print_status "2. sudo docker-compose up -d"
        print_status "3. sudo docker-compose logs -f qdrant"
        print_status "4. curl http://localhost:6333/health"
        
        print_error "Setup failed - Qdrant is required for the application"
        exit 1
    fi
fi

# Final verification and public IP detection
print_header "Final Verification"

# Try to get public IP
PUBLIC_IP=""
if command -v curl > /dev/null 2>&1; then
    PUBLIC_IP=$(curl -s --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
fi

if [[ -z "$PUBLIC_IP" ]]; then
    PUBLIC_IP="your-ec2-public-ip"
    print_warning "Could not auto-detect public IP. Please replace 'your-ec2-public-ip' with your actual IP."
fi

# Run health check
print_status "Running comprehensive health check..."

echo "=============================================="
echo "Vector Search Service Health Check"
echo "Time: $(date)"
echo "=============================================="

# Check Qdrant
if curl -s --max-time 5 http://localhost:6333/health > /dev/null 2>&1; then
    echo "[OK] Qdrant: Running (port 6333)"
else
    echo "[ERROR] Qdrant: Not responding (port 6333)"
fi

echo "=============================================="

echo
print_header "Infrastructure Setup Complete"
echo "========================================="
if [[ "$QDRANT_METHOD" == "docker" ]]; then
    echo "[OK] Qdrant 1.15 vector database (Docker)"
else
    echo "[OK] Qdrant 1.15 vector database (Binary)"
fi
echo "[OK] System dependencies installed"  
echo "[OK] Python environment ready"
echo "[OK] Sample configuration created"
echo "[OK] Optimized for ${MEMORY_GB}GB RAM, ${CPU_COUNT} vCPU instance"
echo "========================================="
echo
echo "🌐 Qdrant Access:"
echo "Qdrant Dashboard:  http://$PUBLIC_IP:6333/dashboard"
echo "Qdrant API:        http://$PUBLIC_IP:6333"
echo
echo "[STATS] Configuration Applied:"
echo "Preset: $PRESET"
echo "Max Threads: $MAX_THREADS" 
echo "Embedding Batch Size: $EMBEDDING_BATCH_SIZE"
echo "Upload Batch Size: $BATCH_SIZE"
echo
echo "[FOLDER] Next Steps:"
echo "1. Go to your application directory with your code"
echo "2. Create virtual environment:"
echo "   python3 -m venv venv && source venv/bin/activate"
echo "3. Install your requirements:"
echo "   pip install -r requirements.txt"
echo "4. Copy sample environment:"
echo "   cp ~/sample.env ./.env"
echo "5. Start your application manually:"
echo "   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo
echo "[CONFIG] Infrastructure Management:"
echo "sudo systemctl status qdrant"
echo "sudo systemctl restart qdrant"
echo "sudo journalctl -u qdrant -f"
echo
echo "[SEARCH] Final Service Verification:"
print_status "Checking Qdrant service..."
if sudo systemctl status qdrant >/dev/null 2>&1; then
    echo "[OK] Qdrant service: OK"
else
    echo "[ERROR] Qdrant service: Issues detected"
fi
echo
echo "[TARGET] Your infrastructure is ready!"
echo "Only Qdrant is managed by systemd - you control your application!"