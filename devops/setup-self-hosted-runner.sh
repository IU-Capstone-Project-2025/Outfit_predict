#!/usr/bin/env bash
set -euo pipefail

# Self-hosted GitHub Actions Runner Setup Script
# This script sets up a self-hosted runner on your production server

# Configuration
RUNNER_USER="${RUNNER_USER:-github-runner}"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
SERVICE_NAME="github-actions-runner"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

log "Setting up self-hosted GitHub Actions runner..."

# Step 1: Create dedicated user for the runner
if ! id "$RUNNER_USER" &>/dev/null; then
    log "Creating user: $RUNNER_USER"
    useradd -m -s /bin/bash "$RUNNER_USER"
    usermod -aG docker "$RUNNER_USER"  # Add to docker group
    success "User $RUNNER_USER created"
else
    log "User $RUNNER_USER already exists"
fi

# Step 2: Install dependencies
log "Installing dependencies..."
apt-get update
apt-get install -y curl jq

# Step 3: Download and install GitHub Actions runner
log "Setting up GitHub Actions runner..."

# Create runner directory as root, then change ownership
mkdir -p "$RUNNER_DIR"
chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

# Switch to runner user for download and extraction
sudo -u "$RUNNER_USER" bash << EOF
set -euo pipefail

cd "$RUNNER_DIR"

# Get latest runner version
RUNNER_VERSION=\$(curl -s https://api.github.com/repos/actions/runner/releases/latest | jq -r '.tag_name' | sed 's/v//')
echo "Latest runner version: \$RUNNER_VERSION"

# Download runner
if [[ ! -f "actions-runner-linux-x64-\${RUNNER_VERSION}.tar.gz" ]]; then
    curl -o actions-runner-linux-x64-\${RUNNER_VERSION}.tar.gz -L https://github.com/actions/runner/releases/download/v\${RUNNER_VERSION}/actions-runner-linux-x64-\${RUNNER_VERSION}.tar.gz
fi

# Extract runner
if [[ ! -f "./config.sh" ]]; then
    tar xzf actions-runner-linux-x64-\${RUNNER_VERSION}.tar.gz
fi

EOF

# Install dependencies as root (this requires root privileges)
log "Installing runner dependencies..."
if [[ -f "$RUNNER_DIR/bin/installdependencies.sh" ]]; then
    cd "$RUNNER_DIR"
    ./bin/installdependencies.sh
else
    error "Runner installation files not found!"
fi

success "GitHub Actions runner downloaded and installed"

# Step 4: Create systemd service
log "Creating systemd service..."

cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=$RUNNER_USER
WorkingDirectory=$RUNNER_DIR
ExecStart=$RUNNER_DIR/run.sh
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=github-actions-runner
Environment=DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
success "Systemd service created"

# Step 5: Set permissions
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME"

# Step 6: Create configuration script
cat > "$RUNNER_HOME/configure-runner.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# This script configures the GitHub Actions runner
# Run this as the github-runner user with your repository token

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <REPO_URL> <TOKEN>"
    echo "Example: $0 https://github.com/IU-Capstone-Project-2025/Outfit_predict ghp_xxxxxxxxxxxx"
    exit 1
fi

REPO_URL="$1"
TOKEN="$2"
RUNNER_NAME="${3:-$(hostname)-runner}"

cd /home/github-runner/actions-runner

# Configure the runner
./config.sh --url "$REPO_URL" --token "$TOKEN" --name "$RUNNER_NAME" --work _work --labels self-hosted,linux,outfit-predict --unattended

echo "Runner configured successfully!"
echo "To start the runner service: sudo systemctl start github-actions-runner"
echo "To enable auto-start: sudo systemctl enable github-actions-runner"
EOF

chmod +x "$RUNNER_HOME/configure-runner.sh"
chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME/configure-runner.sh"

# Step 7: Create deployment directory and permissions
mkdir -p /home/"$RUNNER_USER"/Outfit_predict
chown -R "$RUNNER_USER:$RUNNER_USER" /home/"$RUNNER_USER"/Outfit_predict

# Step 8: Grant sudo permissions for deployment
cat > /etc/sudoers.d/github-runner << EOF
# Allow github-runner to manage docker and deployment
$RUNNER_USER ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/local/bin/docker-compose, /usr/bin/docker-compose, /bin/systemctl restart github-actions-runner, /bin/systemctl start github-actions-runner, /bin/systemctl stop github-actions-runner
EOF

success "Self-hosted runner setup completed!"

echo ""
echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}🎉 Self-hosted Runner Setup Complete!${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo ""
echo "1. Get a runner registration token from GitHub:"
echo "   → Go to: https://github.com/IU-Capstone-Project-2025/Outfit_predict/settings/actions/runners"
echo "   → Click 'New self-hosted runner'"
echo "   → Copy the token from the configuration command"
echo ""
echo "2. Configure the runner:"
echo "   sudo -u $RUNNER_USER /home/$RUNNER_USER/configure-runner.sh https://github.com/IU-Capstone-Project-2025/Outfit_predict <YOUR_TOKEN>"
echo ""
echo "3. Start the runner service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo "   sudo systemctl enable $SERVICE_NAME"
echo ""
echo "4. Check runner status:"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo -e "${YELLOW}🔐 Security Notes:${NC}"
echo "• Runner user has limited sudo access for deployment"
echo "• Runner runs in isolated directory: $RUNNER_DIR"
echo "• Review the workflow files before enabling"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "• Logs: sudo journalctl -u $SERVICE_NAME -f"
echo "• Status: sudo systemctl status $SERVICE_NAME"
echo ""
