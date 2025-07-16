#!/usr/bin/env bash
set -euo pipefail

# Configuration
PROJECT_DIR="/home/${DEPLOY_USER:-$USER}/Outfit_predict"
BACKUP_DIR="/home/${DEPLOY_USER:-$USER}/backups"
REGISTRY="${REGISTRY:-ghcr.io}"
REPO_NAME="${GITHUB_REPOSITORY:-iu-capstone-project-2025/outfit_predict}"
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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error_exit "This script should not be run as root for security reasons"
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to backup current state
backup_current_state() {
    log "Creating backup of current state..."

    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/outfit_backup_$TIMESTAMP"

    mkdir -p "$BACKUP_PATH"

    # Backup docker-compose.yml
    if [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
        cp "$PROJECT_DIR/docker-compose.yml" "$BACKUP_PATH/"
    fi

    # Backup .env file
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        cp "$PROJECT_DIR/.env" "$BACKUP_PATH/"
    fi

    # Export current containers state
    cd "$PROJECT_DIR"
    docker-compose config > "$BACKUP_PATH/docker-compose-resolved.yml" 2>/dev/null || true

    success "Backup created at $BACKUP_PATH"
    echo "$BACKUP_PATH" > "$BACKUP_DIR/latest_backup.txt"
}

# Function to restore from backup
restore_backup() {
    if [[ -f "$BACKUP_DIR/latest_backup.txt" ]]; then
        BACKUP_PATH=$(cat "$BACKUP_DIR/latest_backup.txt")
        if [[ -d "$BACKUP_PATH" ]]; then
            warning "Restoring from backup: $BACKUP_PATH"
            cp "$BACKUP_PATH/docker-compose.yml" "$PROJECT_DIR/" 2>/dev/null || true
            cd "$PROJECT_DIR"
            docker-compose up -d --force-recreate
            success "Restored from backup"
        fi
    fi
}

# Function to check service health
check_health() {
    log "Performing health checks..."

    # Wait for services to start
    sleep 30

    # Check frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        success "Frontend is healthy"
    else
        error_exit "Frontend health check failed"
    fi

    # Check backend
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "Backend is healthy"
    elif curl -f http://localhost:8000 > /dev/null 2>&1; then
        success "Backend is responding (health endpoint might not exist)"
    else
        error_exit "Backend health check failed"
    fi

    # Check database connectivity (through backend)
    if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
        success "Backend API documentation is accessible"
    fi
}

# Main deployment function
deploy() {
    log "Starting deployment process..."

    # Backup current state
    backup_current_state

    # Navigate to project directory
    cd "$PROJECT_DIR" || error_exit "Project directory not found: $PROJECT_DIR"

    # Pull latest changes
    log "Pulling latest changes from repository..."
    git fetch origin
    git reset --hard origin/main
    git lfs pull || warning "Git LFS pull failed, continuing anyway"

    # Set image names
    BACKEND_IMAGE="$REGISTRY/$REPO_NAME/backend:latest"
    FRONTEND_IMAGE="$REGISTRY/$REPO_NAME/frontend:latest"

    # Login to container registry if token is provided
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        log "Logging into container registry..."
        echo "$GITHUB_TOKEN" | docker login "$REGISTRY" -u "${GITHUB_ACTOR:-github-actions}" --password-stdin
    fi

    # Pull new images
    log "Pulling new Docker images..."
    docker pull "$BACKEND_IMAGE" || error_exit "Failed to pull backend image"
    docker pull "$FRONTEND_IMAGE" || error_exit "Failed to pull frontend image"

    # Create production docker-compose file
    log "Creating production docker-compose configuration..."
    cp docker-compose.yml docker-compose.prod.yml

    # Update docker-compose to use registry images
    sed -i "s|build: ./backend|image: $BACKEND_IMAGE|g" docker-compose.prod.yml
    sed -i "s|build:.*|image: $FRONTEND_IMAGE|g" docker-compose.prod.yml
    sed -i "/context:/d" docker-compose.prod.yml
    sed -i "/args:/d" docker-compose.prod.yml

    # Deploy new containers
    log "Deploying new containers..."
    docker-compose -f docker-compose.prod.yml pull
    docker-compose -f docker-compose.prod.yml up -d --force-recreate

    # Health check
    if check_health; then
        success "Deployment completed successfully!"

        # Clean up old images
        log "Cleaning up old Docker images..."
        docker image prune -f

        # Remove old backups (keep last 5)
        find "$BACKUP_DIR" -name "outfit_backup_*" -type d | sort -r | tail -n +6 | xargs -r rm -rf

        # Show running containers
        log "Current running containers:"
        docker-compose -f docker-compose.prod.yml ps

    else
        error_exit "Health checks failed, rolling back..."
        restore_backup
        exit 1
    fi
}

# Rollback function
rollback() {
    log "Rolling back to previous version..."
    restore_backup
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "rollback")
        rollback
        ;;
    "health")
        check_health
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health}"
        echo "  deploy   - Deploy the latest version"
        echo "  rollback - Rollback to the previous version"
        echo "  health   - Check service health"
        exit 1
        ;;
esac
