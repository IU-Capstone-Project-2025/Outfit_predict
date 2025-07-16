#!/usr/bin/env bash
set -euo pipefail

# Initial Deployment Script - Builds images locally for first deployment
# Use this ONLY for the first deployment before GitHub Actions has built images

PROJECT_DIR="/home/${DEPLOY_USER:-$USER}/Outfit_predict"
BACKUP_DIR="/home/${DEPLOY_USER:-$USER}/backups"
LOG_FILE="/var/log/outfit-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Success message
success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
    log "SUCCESS: $1"
}

# Warning message
warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
    log "WARNING: $1"
}

log "=== INITIAL DEPLOYMENT - Building images locally ==="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error_exit "This script should not be run as root for security reasons"
fi

# Navigate to project directory
cd "$PROJECT_DIR" || error_exit "Project directory not found: $PROJECT_DIR"

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    error_exit ".env file not found. Copy devops/env.production.template to .env and configure it first."
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup current state if containers exist
if docker-compose ps | grep -q "Up\|Exited"; then
    log "Creating backup of current state..."
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/outfit_backup_$TIMESTAMP"
    mkdir -p "$BACKUP_PATH"

    # Backup docker-compose.yml
    if [[ -f "docker-compose.yml" ]]; then
        cp "docker-compose.yml" "$BACKUP_PATH/"
    fi

    # Backup .env file
    if [[ -f ".env" ]]; then
        cp ".env" "$BACKUP_PATH/"
    fi

    success "Backup created at $BACKUP_PATH"
    echo "$BACKUP_PATH" > "$BACKUP_DIR/latest_backup.txt"
fi

# Pull latest changes
log "Pulling latest changes from repository..."
git fetch origin
git reset --hard origin/main
git lfs pull || warning "Git LFS pull failed, continuing anyway"

# Check if Dockerfiles exist
if [[ ! -f "backend/Dockerfile" ]]; then
    error_exit "Backend Dockerfile not found at backend/Dockerfile"
fi

if [[ ! -f "frontend/Dockerfile" ]]; then
    error_exit "Frontend Dockerfile not found at frontend/Dockerfile"
fi

# Stop existing containers
log "Stopping existing containers..."
docker-compose down || true

# Build and deploy with local images
log "Building and deploying with docker-compose..."
docker-compose up --build -d

# Wait for services to start
log "Waiting for services to start..."
sleep 60

# Health check function
check_health() {
    log "Performing health checks..."

    # Check if containers are running
    if ! docker-compose ps | grep -q "Up"; then
        error_exit "Some containers failed to start"
    fi

    # Check frontend
    local frontend_attempts=0
    while [ $frontend_attempts -lt 10 ]; do
        if curl -f http://localhost:3000 > /dev/null 2>&1; then
            success "Frontend is healthy"
            break
        fi
        frontend_attempts=$((frontend_attempts + 1))
        log "Frontend not ready yet, attempt $frontend_attempts/10..."
        sleep 10
    done

    if [ $frontend_attempts -eq 10 ]; then
        error_exit "Frontend health check failed after 10 attempts"
    fi

    # Check backend
    local backend_attempts=0
    while [ $backend_attempts -lt 10 ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            success "Backend is healthy"
            break
        elif curl -f http://localhost:8000 > /dev/null 2>&1; then
            success "Backend is responding (health endpoint might not exist)"
            break
        fi
        backend_attempts=$((backend_attempts + 1))
        log "Backend not ready yet, attempt $backend_attempts/10..."
        sleep 10
    done

    if [ $backend_attempts -eq 10 ]; then
        error_exit "Backend health check failed after 10 attempts"
    fi

    # Check database connectivity (through backend)
    if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
        success "Backend API documentation is accessible"
    fi
}

# Run health checks
if check_health; then
    success "Initial deployment completed successfully!"

    # Show running containers
    log "Current running containers:"
    docker-compose ps

    # Show helpful information
    echo ""
    echo -e "${GREEN}🎉 Deployment Complete!${NC}"
    echo -e "${GREEN}📱 Frontend: http://localhost:3000${NC}"
    echo -e "${GREEN}🔧 Backend API: http://localhost:8000${NC}"
    echo -e "${GREEN}📚 API Docs: http://localhost:8000/docs${NC}"
    echo -e "${GREEN}💾 MinIO Console: http://localhost:9001${NC}"
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo "1. Configure GitHub Secrets for automated deployments"
    echo "2. Test the application functionality"
    echo "3. Set up domain and SSL certificates"
    echo "4. Future deployments will use the automated CD pipeline"
    echo ""
    echo -e "${YELLOW}🔍 Monitoring:${NC}"
    echo "- View logs: docker-compose logs -f"
    echo "- Check status: docker-compose ps"
    echo "- Deployment logs: tail -f /var/log/outfit-deploy.log"

else
    error_exit "Health checks failed during initial deployment"
fi
