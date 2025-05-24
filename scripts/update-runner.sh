#!/bin/bash

# MIT License
# Copyright (c) 2025 Aya Nasser
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Script to update GitHub self-hosted runner to the latest version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if runner directory exists
RUNNER_DIR="$HOME/github-runner"
if [ ! -d "$RUNNER_DIR" ]; then
    print_error "Runner directory not found at $RUNNER_DIR"
    print_error "Please run setup-github-runner.sh first"
    exit 1
fi

# Stop the runner service
print_status "Stopping GitHub runner service..."
if systemctl is-active --quiet github-runner; then
    sudo systemctl stop github-runner
    print_status "Runner service stopped"
else
    print_warning "Runner service is not running"
fi

# Go to runner directory
cd "$RUNNER_DIR"

# Get latest runner version
print_status "Checking for the latest GitHub runner version..."
LATEST_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

if [ -z "$LATEST_VERSION" ]; then
    print_error "Failed to determine latest runner version"
    exit 1
fi

print_status "Latest runner version: $LATEST_VERSION"

# Check current version
if [ -f "$RUNNER_DIR/runnerversion" ]; then
    CURRENT_VERSION=$(cat "$RUNNER_DIR/runnerversion")
    print_status "Current runner version: $CURRENT_VERSION"
    
    if [ "$CURRENT_VERSION" == "$LATEST_VERSION" ]; then
        print_status "Runner is already at the latest version"
        
        # Restart the runner service
        print_status "Restarting runner service..."
        sudo systemctl start github-runner
        
        exit 0
    fi
else
    print_warning "Could not determine current runner version"
fi

# Download the latest runner
print_status "Downloading runner version $LATEST_VERSION..."
curl -o "actions-runner-linux-x64-${LATEST_VERSION}.tar.gz" -L "https://github.com/actions/runner/releases/download/v${LATEST_VERSION}/actions-runner-linux-x64-${LATEST_VERSION}.tar.gz"

# Create backup of current runner config
print_status "Backing up runner configuration..."
mkdir -p "$HOME/runner-backup"
cp -f "$RUNNER_DIR/.runner" "$HOME/runner-backup/" 2>/dev/null || true
cp -f "$RUNNER_DIR/.credentials" "$HOME/runner-backup/" 2>/dev/null || true
cp -f "$RUNNER_DIR/.credentials_rsaparams" "$HOME/runner-backup/" 2>/dev/null || true
cp -f "$RUNNER_DIR/config.sh" "$HOME/runner-backup/" 2>/dev/null || true

# Extract the new runner over the existing one
print_status "Extracting new runner version..."
tar xzf "actions-runner-linux-x64-${LATEST_VERSION}.tar.gz" --overwrite

# Restore configuration
print_status "Restoring runner configuration..."
cp -f "$HOME/runner-backup/.runner" "$RUNNER_DIR/" 2>/dev/null || true
cp -f "$HOME/runner-backup/.credentials" "$RUNNER_DIR/" 2>/dev/null || true
cp -f "$HOME/runner-backup/.credentials_rsaparams" "$RUNNER_DIR/" 2>/dev/null || true

# Clean up
rm "actions-runner-linux-x64-${LATEST_VERSION}.tar.gz"

# Restart the runner service
print_status "Restarting runner service..."
sudo systemctl start github-runner

# Check if service started successfully
if systemctl is-active --quiet github-runner; then
    print_status "Runner updated to version $LATEST_VERSION and service restarted successfully"
else
    print_error "Failed to restart runner service"
    print_error "Check logs with: sudo journalctl -u github-runner -e"
    exit 1
fi
