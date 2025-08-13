#!/bin/bash

# Deploy and Run on AWS: GitHub → AWS
# Automated deployment on AWS Linux
# Run this on your AWS instance after cloning from GitHub
#
# Usage:
#   ./deploy-RunAt-aws.sh          # Normal deployment (no cleanup)
#   ./deploy-RunAt-aws.sh --clean  # Force cleanup before deployment

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_header() {
    echo -e "${BLUE}🚀 $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

clear
echo ""
echo "████████████████████████████████████████████████████████████████"
echo "█                                                              █"
echo "█               Deploy and Run on AWS                     █"
echo "█                                                              █"
echo "█        Complete Vector Search Application Setup             █"
echo "█                                                              █"
echo "████████████████████████████████████████████████████████████████"
echo ""

# Configuration
GIT_REPO_URL="https://github.com/domini1969/vector-search-application.git"
FORCE_CLEANUP=false

# Parse command line arguments
if [[ "$1" == "--clean" ]]; then
    FORCE_CLEANUP=true
    print_info "Cleanup mode enabled via --clean flag"
fi

print_header "PHASE 1: Pre-flight Checks"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "Don't run this script as root!"
    print_info "Run as ec2-user: ./deploy-RunAt-aws.sh"
    exit 1
fi

# Check OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_NAME=$NAME
    print_info "Detected OS: $OS_NAME"
else
    print_warning "Cannot detect OS - proceeding with generic setup"
    OS_NAME="Unknown"
fi

print_success "Pre-flight checks passed"

print_header "PHASE 2: Repository Setup"

# Handle existing repository
if [[ -d "vector-search-application" ]]; then
    print_step "Updating existing repository..."
    cd vector-search-application
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || {
        print_warning "Git pull failed - using existing code"
    }
else
    print_step "Cloning fresh repository..."
    if ! git clone "$GIT_REPO_URL"; then
        print_error "Failed to clone repository!"
        print_info "Check your internet connection and repository access"
        exit 1
    fi
    cd vector-search-application
fi

# Verify we have the required files
if [[ ! -f "app/main.py" ]]; then
    print_error "app/main.py not found in repository!"
    exit 1
fi

# Make all scripts executable
print_step "Making scripts executable..."
chmod +x *.sh 2>/dev/null || true
SCRIPT_COUNT=$(ls -1 *.sh 2>/dev/null | wc -l)
print_success "Made $SCRIPT_COUNT scripts executable"

print_header "PHASE 3: Environment Setup"

# Handle cleanup based on flag or user choice
if [[ "$FORCE_CLEANUP" == "true" ]]; then
    print_info "Cleanup forced via --clean flag"
    if [[ -f "./cleanup-aws.sh" ]]; then
        print_step "Running cleanup script..."
        ./cleanup-aws.sh || {
            print_warning "Cleanup had warnings - continuing anyway"
        }
    else
        print_warning "cleanup-aws.sh not found - skipping cleanup"
    fi
else
    print_info "🔄 Normal deployment mode (no cleanup by default)"
    print_info "💡 Run with --clean flag if you need to reset the environment"
    
    # Only ask if there are signs of existing installation
    if sudo systemctl list-units --type=service | grep -q "qdrant\|vector-"; then
        print_warning "Existing Vector Search services detected"
        read -p "🧹 Clean existing installation? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [[ -f "./cleanup-aws.sh" ]]; then
                print_step "Running cleanup script..."
                ./cleanup-aws.sh || {
                    print_warning "Cleanup had warnings - continuing anyway"
                }
            else
                print_warning "cleanup-aws.sh not found - skipping cleanup"
            fi
        else
            print_info "Continuing with existing environment"
        fi
    else
        print_success "No existing installation detected - proceeding with fresh setup"
    fi
fi

print_header "PHASE 4: Infrastructure Setup"

if [[ ! -f "./setup-aws.sh" ]]; then
    print_error "setup-aws.sh not found!"
    print_info "Required files missing from repository"
    exit 1
fi

print_step "Installing infrastructure (Qdrant, Docker, Python)..."
print_info "This may take 5-10 minutes depending on your instance size"

export GIT_REPO_URL="$GIT_REPO_URL"

# Run infrastructure setup with error handling
if ./setup-aws.sh; then
    print_success "Infrastructure setup completed"
else
    print_error "Infrastructure setup failed!"
    print_info "Check the logs above for details"
    exit 1
fi

print_header "PHASE 5: Application Deployment"

# Find the correct application services script
APP_SCRIPT=""
if [[ -f "./setup-application-services-aws.sh" ]]; then
    APP_SCRIPT="./setup-application-services-aws.sh"
elif [[ -f "./setup-application-services.sh" ]]; then
    APP_SCRIPT="./setup-application-services.sh"
else
    print_error "Application services script not found!"
    print_info "Looking for: setup-application-services-aws.sh or setup-application-services.sh"
    exit 1
fi

print_step "Deploying application from GitHub..."
print_info "Creating Python environment and systemd services..."

# Deploy application with error handling
if $APP_SCRIPT; then
    print_success "Application deployment completed"
else
    print_error "Application deployment failed!"
    print_info "Check the logs above for details"
    exit 1
fi

print_header "PHASE 6: Service Verification"

print_step "Waiting for services to start..."
sleep 15

# Check services
SERVICES=("qdrant" "vector-api" "vector-ui")
SERVICES_OK=0
SERVICES_TOTAL=${#SERVICES[@]}

print_info "Checking $SERVICES_TOTAL services..."

for service in "${SERVICES[@]}"; do
    if sudo systemctl is-active --quiet "$service"; then
        print_success "$service: Running"
        SERVICES_OK=$((SERVICES_OK + 1))
    else
        print_warning "$service: Not running"
        print_info "Status: $(sudo systemctl is-active "$service" 2>/dev/null || echo 'unknown')"
    fi
done

print_header "PHASE 7: Endpoint Testing"

# Get public IP
print_step "Detecting public IP..."
PUBLIC_IP=""

# Try multiple methods to get public IP
PUBLIC_IP=$(curl -s --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
if [[ -z "$PUBLIC_IP" ]]; then
    PUBLIC_IP=$(curl -s --max-time 5 http://checkip.amazonaws.com 2>/dev/null || echo "")
fi
if [[ -z "$PUBLIC_IP" ]]; then
    PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "")
fi
if [[ -z "$PUBLIC_IP" ]]; then
    PUBLIC_IP="YOUR-AWS-INSTANCE-IP"
    print_warning "Could not auto-detect public IP"
else
    print_success "Public IP detected: $PUBLIC_IP"
fi

# Test endpoints
ENDPOINTS_OK=0
ENDPOINTS_TOTAL=3

print_step "Testing application endpoints..."
sleep 5  # Give services more time

# Test Qdrant
if curl -s --max-time 10 http://localhost:6333/health > /dev/null 2>&1; then
    print_success "Qdrant API: Responding"
    ENDPOINTS_OK=$((ENDPOINTS_OK + 1))
else
    print_warning "Qdrant API: Not responding"
fi

# Test Vector API
if curl -s --max-time 10 http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Vector API: Responding" 
    ENDPOINTS_OK=$((ENDPOINTS_OK + 1))
else
    print_warning "Vector API: Not responding"
fi

# Test UI (Streamlit takes longer to start)
if curl -s --max-time 15 http://localhost:8501 > /dev/null 2>&1; then
    print_success "Search UI: Responding"
    ENDPOINTS_OK=$((ENDPOINTS_OK + 1))
else
    print_warning "Search UI: Starting (Streamlit takes time)"
fi

print_header "PHASE 8: Deployment Results"

echo ""
echo "████████████████████████████████████████████████████████████████"

if [[ $SERVICES_OK -eq $SERVICES_TOTAL && $ENDPOINTS_OK -ge 2 ]]; then
    echo "█                                                              █"
    echo "█                    🎉 DEPLOYMENT SUCCESS! 🎉               █"
    echo "█                                                              █"
    echo "████████████████████████████████████████████████████████████████"
    echo ""
    echo "🌐 ACCESS YOUR VECTOR SEARCH APPLICATION:"
    echo "========================================"
    echo ""
    echo "┌──────────────────────────────────────────────────────────────┐"
    echo "│  🔗 API Documentation:  http://$PUBLIC_IP:8000/docs        │"
    echo "│  🔍 Search Interface:   http://$PUBLIC_IP:8501             │"
    echo "│  🗄️  Qdrant Dashboard:   http://$PUBLIC_IP:6333/dashboard  │"
    echo "└──────────────────────────────────────────────────────────────┘"
    echo ""
    print_success "All services operational!"
    
elif [[ $SERVICES_OK -gt 0 ]]; then
    echo "█                                                              █"
    echo "█                ⚠️  PARTIAL DEPLOYMENT ⚠️                    █"
    echo "█                                                              █"
    echo "████████████████████████████████████████████████████████████████"
    echo ""
    print_warning "Some services need attention"
    echo ""
    echo "🌐 AVAILABLE SERVICES:"
    echo "==================="
    if curl -s --max-time 5 http://localhost:6333/health > /dev/null; then
        echo "  🗄️  Qdrant Dashboard: http://$PUBLIC_IP:6333/dashboard"
    fi
    if curl -s --max-time 5 http://localhost:8000/health > /dev/null; then
        echo "  🔗 API Documentation: http://$PUBLIC_IP:8000/docs"
    fi
    if curl -s --max-time 5 http://localhost:8501 > /dev/null; then
        echo "  🔍 Search Interface: http://$PUBLIC_IP:8501"
    fi
    
else
    echo "█                                                              █"
    echo "█                   ❌ DEPLOYMENT ISSUES ❌                   █"
    echo "█                                                              █"
    echo "████████████████████████████████████████████████████████████████"
    echo ""
    print_error "Deployment encountered problems"
fi

echo ""
echo "📊 DEPLOYMENT STATISTICS:"
echo "========================"
echo "Services Running: $SERVICES_OK/$SERVICES_TOTAL"
echo "Endpoints Responding: $ENDPOINTS_OK/$ENDPOINTS_TOTAL"
echo "Public IP: $PUBLIC_IP"
echo "Repository: $GIT_REPO_URL"
echo "OS: $OS_NAME"
echo "Deployment Time: $(date)"
echo ""

if [[ $SERVICES_OK -lt $SERVICES_TOTAL || $ENDPOINTS_OK -lt 2 ]]; then
    echo "🔧 TROUBLESHOOTING COMMANDS:"
    echo "============================"
    echo "# Check service status:"
    echo "sudo systemctl status qdrant vector-api vector-ui"
    echo ""
    echo "# View service logs:"
    echo "sudo journalctl -u qdrant -f"
    echo "sudo journalctl -u vector-api -f"
    echo "sudo journalctl -u vector-ui -f"
    echo ""
    echo "# Restart services:"
    echo "sudo systemctl restart qdrant"
    echo "sudo systemctl restart vector-api vector-ui"
    echo ""
    echo "# Check application logs:"
    echo "tail -f logs/vector-api.log"
    echo "tail -f logs/vector-ui.log"
fi

echo ""
echo "🎯 MANAGEMENT COMMANDS:"
echo "======================"
echo "# Service management:"
echo "sudo systemctl start|stop|restart qdrant vector-api vector-ui"
echo ""
echo "# Health check:"
echo "curl http://localhost:6333/health"
echo "curl http://localhost:8000/health"
echo ""
echo "# Performance test:"
echo "curl 'http://localhost:8000/api/search/ultra-fast?q=test&count=5'"
echo ""

if [[ $SERVICES_OK -eq $SERVICES_TOTAL && $ENDPOINTS_OK -ge 2 ]]; then
    print_success "Your Vector Search Application is LIVE!"
else
    print_warning "Deployment completed with issues - see troubleshooting above"
fi

echo ""
echo "████████████████████████████████████████████████████████████████"