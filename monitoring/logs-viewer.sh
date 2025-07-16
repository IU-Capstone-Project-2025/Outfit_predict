#!/usr/bin/env bash
set -euo pipefail

# OutfitPredict Log Viewer and Management Script
# Provides easy access to view and manage application logs

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${BLUE}OutfitPredict Log Viewer${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  all           Show logs from all containers"
    echo "  backend       Show backend API logs"
    echo "  frontend      Show frontend logs"
    echo "  db            Show database logs"
    echo "  minio         Show MinIO storage logs"
    echo "  monitoring    Show monitoring service logs"
    echo "  follow        Follow logs in real-time (all containers)"
    echo "  errors        Show only error logs"
    echo "  rotate        Rotate log files to prevent disk space issues"
    echo "  status        Show container status and health"
    echo "  clean         Clean old log files (older than 7 days)"
    echo ""
    echo "Options:"
    echo "  -n, --lines   Number of lines to show (default: 100)"
    echo "  -f, --follow  Follow log output"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backend -n 50        Show last 50 lines of backend logs"
    echo "  $0 follow               Follow all container logs in real-time"
    echo "  $0 errors               Show only error messages"
}

# Default values
LINES=100
FOLLOW=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            COMMAND="$1"
            shift
            ;;
    esac
done

# Check if docker compose is available
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker or Docker Compose not found${NC}"
    exit 1
fi

# Function to show container logs
show_logs() {
    local service="$1"
    local lines="$2"
    local follow="$3"
    
    if [[ "$follow" == "true" ]]; then
        echo -e "${GREEN}Following logs for $service...${NC}"
        docker compose logs -f --tail="$lines" "$service"
    else
        echo -e "${GREEN}Showing last $lines lines for $service:${NC}"
        docker compose logs --tail="$lines" "$service"
    fi
}

# Function to show error logs
show_errors() {
    echo -e "${RED}Searching for errors in all containers...${NC}"
    docker compose logs --tail=1000 | grep -i "error\|exception\|fail\|critical" | tail -50
}

# Function to show container status
show_status() {
    echo -e "${BLUE}Container Status:${NC}"
    docker compose ps
    echo ""
    echo -e "${BLUE}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Function to rotate logs
rotate_logs() {
    echo -e "${YELLOW}Rotating application logs...${NC}"
    
    # Rotate custom application logs
    if [[ -d "./logs" ]]; then
        find ./logs -name "*.log" -size +100M -exec mv {} {}.$(date +%Y%m%d_%H%M%S) \;
        find ./logs -name "*.log.*" -mtime +7 -delete
        echo -e "${GREEN}Application logs rotated${NC}"
    fi
    
    # Restart containers to start fresh logs
    echo -e "${YELLOW}Restarting containers for log cleanup...${NC}"
    docker compose restart
    echo -e "${GREEN}Log rotation completed${NC}"
}

# Function to clean old logs
clean_logs() {
    echo -e "${YELLOW}Cleaning old log files...${NC}"
    
    # Clean application logs older than 7 days
    if [[ -d "./logs" ]]; then
        find ./logs -name "*.log.*" -mtime +7 -delete
        echo -e "${GREEN}Old application logs cleaned${NC}"
    fi
    
    # Clean Docker logs
    docker system prune -f --volumes --filter "until=168h"
    echo -e "${GREEN}Old Docker logs and volumes cleaned${NC}"
}

# Main command handling
case "${COMMAND:-help}" in
    all)
        show_logs "" "$LINES" "$FOLLOW"
        ;;
    backend)
        show_logs "backend" "$LINES" "$FOLLOW"
        ;;
    frontend)
        show_logs "frontend" "$LINES" "$FOLLOW"
        ;;
    db)
        show_logs "db" "$LINES" "$FOLLOW"
        ;;
    minio)
        show_logs "minio" "$LINES" "$FOLLOW"
        ;;
    monitoring)
        echo -e "${GREEN}Monitoring Services Logs:${NC}"
        show_logs "dozzle" "$LINES" false
        show_logs "prometheus" "$LINES" false
        show_logs "grafana" "$LINES" false
        ;;
    follow)
        echo -e "${GREEN}Following all container logs... (Press Ctrl+C to stop)${NC}"
        docker compose logs -f --tail="$LINES"
        ;;
    errors)
        show_errors
        ;;
    status)
        show_status
        ;;
    rotate)
        rotate_logs
        ;;
    clean)
        clean_logs
        ;;
    help|*)
        show_help
        ;;
esac 