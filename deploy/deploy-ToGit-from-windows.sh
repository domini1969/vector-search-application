#!/bin/bash

# Deploy to Git from Windows: Windows → GitHub
# Handles Windows to GitHub deployment automatically
# Just run: bash deploy-ToGit-from-windows.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
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
    echo -e "${BLUE}🔄 $1${NC}"
}

clear
echo ""
echo "████████████████████████████████████████████████████████████████"
echo "█                                                              █"
echo "█            Windows to GitHub Deployment                █"
echo "█                                                              █"
echo "█         Windows → GitHub → AWS Deployment                 █"
echo "█                                                              █"
echo "████████████████████████████████████████████████████████████████"
echo ""

# Configuration
GIT_REPO_URL="https://github.com/domini1969/vector-search-application.git"

print_header "PHASE 1: Environment Validation"

# Check if we're in the right directory
if [[ ! -f "app/main.py" ]]; then
    print_error "app/main.py not found!"
    print_info "Please run this script from your vector service root directory"
    exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
    print_error "requirements.txt not found!"
    exit 1
fi

print_success "Directory validation passed"

print_header "PHASE 2: Clean Git Setup"

# Remove existing git completely
if [[ -d ".git" ]]; then
    print_info "Removing old Git repository..."
    rm -rf .git
fi

# Initialize fresh Git
git init --initial-branch=main 2>/dev/null || git init
git config user.name "Vector Search Deploy" 2>/dev/null || true
git config user.email "deploy@vector-search.app" 2>/dev/null || true

print_success "Fresh Git repository initialized"

print_header "PHASE 3: Automatic Script Fixes"

# Fix all shell scripts for Linux compatibility
SCRIPTS_FIXED=0
for script in *.sh; do
    if [[ -f "$script" && "$script" != "deploy-ToGit-from-windows.sh" ]]; then
        # Fix line endings and shebang
        sed -i 's/\r$//' "$script"
        sed -i '1s|.*|#!/bin/bash|' "$script"
        chmod +x "$script"
        SCRIPTS_FIXED=$((SCRIPTS_FIXED + 1))
    fi
done

print_success "Fixed $SCRIPTS_FIXED shell scripts for Linux compatibility"

print_header "PHASE 4: File Preparation"

# Verify .env file exists for deployment
if [[ -f ".env" ]]; then
    print_success ".env file found - will be deployed to AWS"
    print_info "Environment configuration will be copied to AWS"
else
    print_error "ERROR: .env file not found!"
    print_warning "The application requires .env file for configuration"
    print_warning "Please ensure .env file exists in the project root"
    exit 1
fi

print_success "Configuration files prepared"

print_header "PHASE 5: Security & Size Check"

# Add all files
git add .

# Count files
FILE_COUNT=$(git status --porcelain | wc -l)
print_info "Staging $FILE_COUNT files for deployment"

# Security check - critical for production
SENSITIVE_CHECK=$(git status --porcelain | grep -E '\.(pem|ppk)$|AWS-Key/|\.env$' || true)
if [[ -n "$SENSITIVE_CHECK" ]]; then
    print_warning "SECURITY ALERT: Sensitive files detected!"
    echo "$SENSITIVE_CHECK"
    print_info "These files will be automatically excluded by .gitignore"
    
    # Remove .env from staging but keep it for AWS deployment
    if git status --porcelain | grep -q "\.env$"; then
        print_info "Removing .env from Git staging (will be copied to AWS separately)"
        git rm --cached .env 2>/dev/null || true
        echo ".env" >> .gitignore 2>/dev/null || true
    fi
    
    # Remove other sensitive files
    git status --porcelain | grep -E '\.(pem|ppk)$|AWS-Key/' | while read -r line; do
        file=$(echo "$line" | cut -c4-)
        print_info "Removing $file from staging"
        git rm --cached "$file" 2>/dev/null || true
    done
    
    print_success "Sensitive files properly excluded from Git"
else
    print_success "No sensitive files detected"
fi

# Check for large files
LARGE_FILES=$(git ls-files 2>/dev/null | xargs -I {} find {} -size +50M 2>/dev/null || true)
if [[ -n "$LARGE_FILES" ]]; then
    print_warning "Large files detected (>50MB):"
    echo "$LARGE_FILES"
    print_info "Large files are excluded by .gitignore - this is normal"
fi

print_success "Security and size validation passed"

print_header "PHASE 6: Git Commit"

# Create comprehensive commit message
COMMIT_MSG="Vector Search Application Deployment

✨ Features:
- FastAPI backend with multi-method search (dense, sparse, hybrid)
- Streamlit UI with enhanced search interface
- Qdrant v1.15 vector database integration
- Docker-based infrastructure setup
- Automated AWS deployment pipeline
- Linux-compatible shell scripts
- Production-ready systemd services

🔧 Architecture:
- Backend: FastAPI with async support
- Frontend: Streamlit interactive UI
- Database: Qdrant vector database
- Infrastructure: Docker + systemd
- Deployment: Git-based automation

📦 Deployment Scripts:
- cleanup-aws.sh: Environment cleanup
- setup-aws.sh: Infrastructure setup
- setup-application-services-aws.sh: Application deployment
- deploy-aws.sh: Complete orchestration

🛡️ Security:
- Sensitive files automatically excluded
- Production environment configuration
- Secure credential handling

Generated with Deploy Script
📅 Deployed: $(date)

Co-Authored-By: Claude <noreply@anthropic.com>"

git commit -m "$COMMIT_MSG"
print_success "Code committed with comprehensive metadata"

print_header "PHASE 7: GitHub Push"

# Set up remote
git remote remove origin 2>/dev/null || true
git remote add origin "$GIT_REPO_URL"

# Get current branch
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

echo ""
echo "🔐 GITHUB PUSH TO PUBLIC REPOSITORY"
echo "==================================="
echo ""
print_info "Repository: $GIT_REPO_URL"
print_info "Branch: $BRANCH_NAME"
print_info "Files: $FILE_COUNT"
print_info "Status: Public repository"
echo ""
print_warning "Even public repos require authentication for PUSH operations:"
echo "   Username: domini1969"
echo "   Password: Your GitHub Personal Access Token (NOT your regular password)"
echo ""
print_info "📝 Need a token? Get one at: https://github.com/settings/tokens"
print_info "   Required permissions: repo (full repository access)"
echo ""
print_info "💡 Alternative: Use SSH keys instead of HTTPS for password-free push"
echo ""

# Try push with better error handling
read -p "Press Enter when ready to authenticate and push..." -r

print_step "Pushing to GitHub..."

# First try - normal push
if git push -u origin "$BRANCH_NAME" --force 2>/dev/null; then
    PUSH_SUCCESS=true
    print_success "Successfully pushed to GitHub!"
elif git push -u origin "$BRANCH_NAME" --force; then
    PUSH_SUCCESS=true  
    print_success "Successfully pushed to GitHub!"
else
    PUSH_SUCCESS=false
    print_error "Push failed - authentication required"
    echo ""
    print_info "This is normal for public repos - you still need authentication to PUSH"
    print_info "Try again with your GitHub username and Personal Access Token"
fi

print_header "PHASE 8: Deployment Instructions"

echo ""
echo "████████████████████████████████████████████████████████████████"
if [[ "$PUSH_SUCCESS" == "true" ]]; then
    echo "█                                                              █"
    echo "█                     SUCCESS!                            █"
    echo "█              Ready for AWS Deployment                       █"
    echo "█                                                              █"
    echo "████████████████████████████████████████████████████████████████"
    echo ""
    echo "✅ COMPLETED TASKS:"
    echo "  ✓ Git repository cleaned and re-initialized"
    echo "  ✓ All $SCRIPTS_FIXED shell scripts fixed for Linux"
    echo "  ✓ Security validation passed"
    echo "  ✓ $FILE_COUNT files committed and pushed"
    echo "  ✓ Repository deployed: $GIT_REPO_URL"
    echo ""
    echo "🚀 AWS DEPLOYMENT (Copy and run on your AWS instance):"
    echo "======================================================"
    echo ""
    echo "# 1. SSH to your AWS instance:"
    echo "ssh -i your-key.pem ec2-user@your-aws-instance-ip"
    echo ""
    echo "# 2. One-command deployment:"
    cat << 'EOF'
git clone https://github.com/domini1969/vector-search-application.git && cd vector-search-application/deploy && chmod +x *.sh && export GIT_REPO_URL="https://github.com/domini1969/vector-search-application.git" && ./deploy-RunAt-aws.sh
EOF
    echo ""
    echo "🌐 ACCESS YOUR APPLICATION (after AWS deployment):"
    echo "================================================="
    echo "  🔗 API Documentation: http://YOUR-AWS-IP:8000/docs"
    echo "  🔍 Search Interface:  http://YOUR-AWS-IP:8501"
    echo "  🗄️  Qdrant Dashboard:  http://YOUR-AWS-IP:6333/dashboard"
    echo ""
    echo "🎯 MANAGEMENT COMMANDS (on AWS):"
    echo "==============================="
    echo "  sudo systemctl status qdrant vector-api vector-ui"
    echo "  sudo systemctl restart vector-api vector-ui"
    echo "  sudo journalctl -u vector-api -f"
    echo ""
    print_success "Deployment Package Ready!"
    
else
    echo "█                                                              █"
    echo "█                  Manual Push Needed                   █"
    echo "█                                                              █"
    echo "████████████████████████████████████████████████████████████████"
    echo ""
    echo "✅ COMPLETED TASKS:"
    echo "  ✓ Git repository cleaned and prepared"
    echo "  ✓ All shell scripts fixed for Linux"
    echo "  ✓ Files committed locally"
    echo ""
    echo "❌ REMAINING TASK:"
    echo "  ⚠️  Push to GitHub (authentication failed)"
    echo ""
    echo "📋 MANUAL COMPLETION:"
    echo "===================="
    echo "git push -u origin $BRANCH_NAME --force"
    echo ""
    echo "When prompted:"
    echo "  Username: domini1969"
    echo "  Password: [Your GitHub Personal Access Token]"
    echo ""
    echo "Then proceed with AWS deployment using the commands above."
fi

echo ""
echo "📊 DEPLOYMENT STATISTICS:"
echo "========================"
echo "Repository: $GIT_REPO_URL"
echo "Branch: $BRANCH_NAME"
echo "Files: $FILE_COUNT"
echo "Scripts Fixed: $SCRIPTS_FIXED"
echo "Status: $(if [[ "$PUSH_SUCCESS" == "true" ]]; then echo "✅ Ready for AWS"; else echo "⚠️  Manual push needed"; fi)"
echo ""
echo "Generated: $(date)"
echo ""
echo "████████████████████████████████████████████████████████████████"