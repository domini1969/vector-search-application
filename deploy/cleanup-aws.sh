#!/bin/bash

# AWS Instance Cleanup Script
# Removes Vector Search Service installation completely
# Restores instance to clean state for fresh installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[CLEANUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "AWS Instance Cleanup Script"
echo "This will remove ALL Vector Search Service components"
echo "=============================================="

# Confirmation prompt
read -p "Are you sure you want to clean up the installation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 1
fi

print_header "Stopping Services"

# Stop and disable services
SERVICES=("vector-ui" "vector-api" "qdrant")
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        print_status "Stopping $service..."
        sudo systemctl stop $service
    fi
    
    if systemctl is-enabled --quiet $service 2>/dev/null; then
        print_status "Disabling $service..."
        sudo systemctl disable $service
    fi
done

print_header "Removing Service Files"

# Remove systemd service files
SERVICE_FILES=(
    "/etc/systemd/system/qdrant.service"
    "/etc/systemd/system/vector-api.service" 
    "/etc/systemd/system/vector-ui.service"
)

for file in "${SERVICE_FILES[@]}"; do
    if [[ -f $file ]]; then
        print_status "Removing $file"
        sudo rm -f $file
    fi
done

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl reset-failed 2>/dev/null || true

print_header "Removing Binaries and Data"

# Remove Qdrant binary and data
if [[ -f /usr/local/bin/qdrant ]]; then
    print_status "Removing Qdrant binary"
    sudo rm -f /usr/local/bin/qdrant
fi

if [[ -d /var/lib/qdrant ]]; then
    print_status "Removing Qdrant data directory"
    sudo rm -rf /var/lib/qdrant
fi

if [[ -d /var/log/qdrant ]]; then
    print_status "Removing Qdrant log directory"
    sudo rm -rf /var/log/qdrant
fi

print_header "Removing Application Files"

# Remove application directories
APP_DIRS=(
    "~/vector-service"
    "~/vector-search"
    "~/qdrant-docker"
    "~/qdrant_backup_*"
)

for dir in "${APP_DIRS[@]}"; do
    expanded_dir=$(eval echo $dir)
    if [[ -d $expanded_dir ]] || ls $expanded_dir 1> /dev/null 2>&1; then
        print_status "Removing $expanded_dir"
        rm -rf $expanded_dir
    fi
done

# Remove cache directories (optional - user may want to keep these)
read -p "Remove Python/ML model caches? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    CACHE_DIRS=(
        "~/.fastembed"
        "~/.cache/huggingface"
        "~/.cache/torch"
        "~/.cache/sentence_transformers"
    )
    
    for dir in "${CACHE_DIRS[@]}"; do
        expanded_dir=$(eval echo $dir)
        if [[ -d $expanded_dir ]]; then
            print_status "Removing cache: $expanded_dir"
            rm -rf $expanded_dir
        fi
    done
else
    print_status "Keeping ML model caches (saves download time for future installs)"
fi


print_header "Removing Cron Jobs and Scripts"

# Remove cron jobs
print_status "Cleaning cron jobs..."
crontab -l 2>/dev/null | grep -v -E "(health-check|health-monitor)" | crontab - 2>/dev/null || true

# Remove scripts
SCRIPTS=(
    "~/health-check.sh"
    "~/health-monitor.sh"
    "~/health-monitor-enhanced.sh"
    "~/backup.sh"
    "~/setup-aws.sh"
    "~/setup-aws-enhanced.sh"
)

for script in "${SCRIPTS[@]}"; do
    expanded_script=$(eval echo $script)
    if [[ -f $expanded_script ]]; then
        print_status "Removing $expanded_script"
        rm -f $expanded_script
    fi
done

print_header "Cleaning Python Environment"

# Remove Python virtual environments
VENV_DIRS=(
    "~/venv"
    "~/vector-service/venv"
    "~/.local/lib/python3.*/site-packages/fastembed*"
    "~/.local/lib/python3.*/site-packages/qdrant*"
)

for venv_dir in "${VENV_DIRS[@]}"; do
    expanded_venv=$(eval echo $venv_dir)
    if [[ -d $expanded_venv ]] || ls $expanded_venv 1> /dev/null 2>&1; then
        print_status "Removing Python environment: $expanded_venv"
        rm -rf $expanded_venv
    fi
done

print_header "Cleaning Package Cache"

# Detect OS and clean package cache
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$NAME
fi

if [[ "$OS" == *"Amazon Linux"* ]]; then
    print_status "Cleaning yum cache..."
    sudo yum clean all
    
    # Remove development packages if installed by our script
    DEV_PACKAGES="gcc gcc-c++ python3-devel atlas-devel lapack-devel blas-devel"
    for pkg in $DEV_PACKAGES; do
        if yum list installed $pkg &>/dev/null; then
            print_warning "Development package $pkg is installed (not removing - may be needed by other apps)"
        fi
    done
    
elif [[ "$OS" == *"Ubuntu"* ]]; then
    print_status "Cleaning apt cache..."
    sudo apt autoremove -y
    sudo apt autoclean
fi

print_header "Checking for Port Usage"

# Check if any of our ports are still in use
PORTS=(6333 8000 8501)
for port in "${PORTS[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        print_warning "Port $port is still in use. You may need to reboot."
        netstat -tuln | grep ":$port "
    fi
done

print_header "Cleaning Logs"

# Remove log files
LOG_DIRS=(
    "~/logs"
    "~/vector-service/logs"
    "/var/log/vector-*"
)

for log_dir in "${LOG_DIRS[@]}"; do
    expanded_log=$(eval echo $log_dir)
    if [[ -d $expanded_log ]] || ls $expanded_log 1> /dev/null 2>&1; then
        print_status "Removing logs: $expanded_log"
        sudo rm -rf $expanded_log
    fi
done

print_header "Final Cleanup"

# Clean up any remaining processes (more thorough)
PROCESSES=("qdrant" "uvicorn" "streamlit" "python.*app.main" "docker.*qdrant")
for proc in "${PROCESSES[@]}"; do
    if pgrep -f "$proc" > /dev/null; then
        print_status "Killing remaining $proc processes"
        pkill -f "$proc" || true
        sleep 2
        # Force kill if still running
        if pgrep -f "$proc" > /dev/null; then
            print_warning "Force killing stubborn $proc processes"
            pkill -9 -f "$proc" || true
        fi
    fi
done

# Stop Docker containers if they exist
if command -v docker >/dev/null 2>&1; then
    if docker ps | grep -q qdrant; then
        print_status "Stopping Qdrant Docker containers"
        docker stop $(docker ps -q --filter "name=qdrant") 2>/dev/null || true
        docker rm $(docker ps -aq --filter "name=qdrant") 2>/dev/null || true
    fi
fi

# Clean up systemd journal if it got too large
print_status "Cleaning systemd journal..."
sudo journalctl --vacuum-time=1d --quiet

print_header "Verification"

# Verify cleanup
echo
print_status "Verifying cleanup..."

# Check services
REMAINING_SERVICES=0
for service in "${SERVICES[@]}"; do
    if systemctl is-enabled --quiet $service 2>/dev/null; then
        print_warning "Service $service is still enabled"
        REMAINING_SERVICES=$((REMAINING_SERVICES + 1))
    fi
done

# Check directories
REMAINING_DIRS=0
CHECK_DIRS=("~/vector-service" "/var/lib/qdrant")
for dir in "${CHECK_DIRS[@]}"; do
    expanded_dir=$(eval echo $dir)
    if [[ -d $expanded_dir ]]; then
        print_warning "Directory $expanded_dir still exists"
        REMAINING_DIRS=$((REMAINING_DIRS + 1))
    fi
done

# Check processes
REMAINING_PROCESSES=0
for proc in "${PROCESSES[@]}"; do
    if pgrep -f $proc > /dev/null; then
        print_warning "Process $proc is still running"
        REMAINING_PROCESSES=$((REMAINING_PROCESSES + 1))
    fi
done

echo
echo "=============================================="
print_header "Cleanup Complete"
echo "=============================================="

if [[ $REMAINING_SERVICES -eq 0 && $REMAINING_DIRS -eq 0 && $REMAINING_PROCESSES -eq 0 ]]; then
    echo -e "${GREEN}[OK] Clean removal successful!${NC}"
    echo "Your AWS instance is now ready for fresh installation."
else
    echo -e "${YELLOW}[WARNING]  Cleanup completed with warnings${NC}"
    echo "Some components may require manual removal or reboot."
fi

echo
echo "[NOTES] What was removed:"
echo "[OK] All Vector Search services (qdrant, vector-api, vector-ui)"
echo "[OK] Application files and directories"
echo "[OK] Python virtual environments"
echo "[OK] Service configuration files"
echo "[OK] Cron jobs and monitoring scripts"
echo "[OK] Cache and temporary files"
echo
echo "🔄 To start fresh installation:"
echo "1. Reboot the instance (recommended): sudo reboot"
echo "2. Run the setup script: ./setup-aws.sh"
echo
echo "💾 What was preserved:"
echo "[OK] Base OS and system packages"
echo "[OK] SSH keys and user accounts"
echo "[OK] AWS instance configuration"
echo "[OK] Network settings"

if [[ $REMAINING_SERVICES -gt 0 || $REMAINING_DIRS -gt 0 || $REMAINING_PROCESSES -gt 0 ]]; then
    echo
    print_warning "Recommendation: Reboot the instance to ensure complete cleanup"
    echo "sudo reboot"
fi

echo
print_status "Cleanup script completed successfully!"