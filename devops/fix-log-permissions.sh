#!/usr/bin/env bash
set -e

# Fix log permissions for GitHub Actions runner
# This script ensures the runner can clean up log files created by Docker containers

USER_NAME="${1:-$(whoami)}"
LOGS_DIR="${2:-logs}"

echo "🔧 Fixing log permissions for user: $USER_NAME"

# Create logs directory if it doesn't exist
if [[ ! -d "$LOGS_DIR" ]]; then
    echo "📁 Creating logs directory: $LOGS_DIR"
    mkdir -p "$LOGS_DIR"
fi

# Fix ownership and permissions
echo "👤 Changing ownership of $LOGS_DIR to $USER_NAME"
sudo chown -R "$USER_NAME:$USER_NAME" "$LOGS_DIR" || {
    echo "⚠️ Could not change ownership, trying with current user permissions"
    sudo chmod -R 755 "$LOGS_DIR" || true
}

# Make sure directory is writable
echo "📝 Setting permissions to 755 for $LOGS_DIR"
sudo chmod -R 755 "$LOGS_DIR" || true

# Set proper umask for future files
echo "🔐 Setting umask for future file creation"
umask 022

echo "✅ Log permissions fixed successfully"

# Show current permissions
echo "📋 Current permissions:"
ls -la "$LOGS_DIR"
