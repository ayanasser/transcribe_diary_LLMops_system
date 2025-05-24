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

# GitHub Self-Hosted Runner Setup Script for MLOps Assessment
# This script configures a high-performance self-hosted runner for MLOps workflows with:
# - Docker for container management
# - CUDA for GPU-based ML (optional)
# - Python environment for ML tasks
# - Kubernetes tools for deployment
# This script sets up a GitHub Actions self-hosted runner for MLOps workflows

set -e

# Configuration
GITHUB_OWNER="ayanasser"
GITHUB_REPO="transcribe_diary_LLMops_system"
RUNNER_NAME="mlops-runner-$(hostname)"
RUNNER_LABELS="self-hosted,linux,x64,mlops,docker"
RUNNER_DIR="$HOME/github-runner"

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons."
   exit 1
fi

# Check required dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if user is in docker group
    if ! groups $USER | grep &>/dev/null '\bdocker\b'; then
        print_warning "User $USER is not in the docker group. Adding to docker group..."
        sudo usermod -aG docker $USER
        print_warning "You may need to log out and back in for docker group changes to take effect."
    fi
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        print_error "Git is required but not installed."
        exit 1
    fi
    
    print_status "Dependencies check completed."
}

# Install additional MLOps dependencies
install_mlops_dependencies() {
    print_status "Installing MLOps dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install Python and pip if not present
    if ! command -v python3 &> /dev/null; then
        sudo apt install -y python3 python3-pip python3-venv
    fi
    
    # Install additional tools for ML workflows
    sudo apt install -y curl wget jq unzip
    
    # Install kubectl for Kubernetes deployments
    if ! command -v kubectl &> /dev/null; then
        print_status "Installing kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
        rm kubectl
    fi
    
    # Install Helm for Kubernetes package management
    if ! command -v helm &> /dev/null; then
        print_status "Installing Helm..."
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    fi
    
    print_status "MLOps dependencies installed successfully."
}

# Configure the runner
configure_runner() {
    print_status "Configuring GitHub Actions runner..."
    
    cd "$RUNNER_DIR"
    
    print_warning "You need to provide a GitHub Personal Access Token (PAT) or registration token."
    print_warning "Go to: https://github.com/$GITHUB_OWNER/$GITHUB_REPO/settings/actions/runners/new"
    print_warning "Copy the registration token from the page above."
    
    read -p "Enter your GitHub registration token: " -s GITHUB_TOKEN
    echo
    
    # Configure the runner
    ./config.sh \
        --url "https://github.com/$GITHUB_OWNER/$GITHUB_REPO" \
        --token "$GITHUB_TOKEN" \
        --name "$RUNNER_NAME" \
        --labels "$RUNNER_LABELS" \
        --work "_work" \
        --unattended \
        --replace
    
    print_status "Runner configured successfully!"
}

# Create systemd service for the runner
create_service() {
    print_status "Creating systemd service for the runner..."
    
    # Create service file
    sudo tee /etc/systemd/system/github-runner.service > /dev/null <<EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$RUNNER_DIR
ExecStart=$RUNNER_DIR/run.sh
Restart=always
RestartSec=10
KillMode=process
TimeoutStopSec=5min
KillSignal=SIGINT
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=HOME=$HOME

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable the service
    sudo systemctl daemon-reload
    sudo systemctl enable github-runner.service
    
    print_status "Systemd service created and enabled."
}

# Main execution
main() {
    print_status "Starting GitHub Actions Self-Hosted Runner setup..."
    
    check_dependencies
    install_mlops_dependencies
    configure_runner
    create_service
    
    print_status "Setup completed successfully!"
    echo
    print_status "Next steps:"
    echo "1. Start the runner service: sudo systemctl start github-runner"
    echo "2. Check service status: sudo systemctl status github-runner"
    echo "3. View logs: sudo journalctl -u github-runner -f"
    echo
    print_status "The runner will appear in your GitHub repository under:"
    print_status "https://github.com/$GITHUB_OWNER/$GITHUB_REPO/settings/actions/runners"
    echo
    print_warning "Remember to update your workflow files to use 'runs-on: self-hosted'"
}

# Run main function
main "$@"
