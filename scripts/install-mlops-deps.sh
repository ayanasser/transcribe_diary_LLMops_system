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

# MLOps dependencies installer script for GitHub self-hosted runners
# This script installs common dependencies needed for machine learning operations
# Including ML libraries, monitoring tools, and infrastructure components

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

# Check if running with necessary privileges
if [[ $EUID -ne 0 ]]; then
   print_warning "This script should be run with sudo for full functionality."
   print_warning "Some installations might fail without proper privileges."
   read -p "Continue anyway? (y/n) " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
   fi
fi

# Update package lists
print_status "Updating package lists..."
apt update || {
    print_warning "Failed to update package lists. Continuing anyway..."
}

# Install system dependencies
print_status "Installing system dependencies..."
apt install -y \
    build-essential \
    curl \
    wget \
    git \
    jq \
    unzip \
    zip \
    tar \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    htop

# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    print_status "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER || true
    print_status "Docker installed successfully. You may need to log out and back in for group changes to take effect."
else
    print_status "Docker is already installed."
fi

# Install Docker Compose V2
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# Install Kubernetes tools if not already installed
print_status "Installing Kubernetes tools..."

# kubectl
if ! command -v kubectl &> /dev/null; then
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
fi

# helm
if ! command -v helm &> /dev/null; then
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# Install NVIDIA Container Toolkit if NVIDIA GPU is detected
if command -v nvidia-smi &> /dev/null; then
    print_status "NVIDIA GPU detected, installing NVIDIA Container Toolkit..."
    
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
    apt update && apt install -y nvidia-container-toolkit
    systemctl restart docker
    print_status "NVIDIA Container Toolkit installed successfully."
else
    print_warning "No NVIDIA GPU detected. Skipping NVIDIA Container Toolkit installation."
fi

# Setup Python environment for ML tasks
print_status "Setting up Python ML environment..."

# Create a virtualenv for ML tasks
if [ "$SUDO_USER" ]; then
    RUNNER_HOME=$(eval echo ~$SUDO_USER)
    ML_ENV_DIR="$RUNNER_HOME/ml-env"
    
    if [ ! -d "$ML_ENV_DIR" ]; then
        print_status "Creating ML Python virtual environment at $ML_ENV_DIR..."
        su - $SUDO_USER -c "python3 -m venv $ML_ENV_DIR"
    fi
    
    # Install ML packages
    print_status "Installing ML packages in virtual environment..."
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install --upgrade pip wheel setuptools"
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install numpy pandas scikit-learn matplotlib pytest pytest-benchmark"
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install torch torchvision"
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install tensorflow"
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install openai transformers sentence-transformers"
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install pytest pytest-cov pylint black isort"
    su - $SUDO_USER -c "$ML_ENV_DIR/bin/pip install jupyterlab"
    
    # Create activation script
    print_status "Creating ML environment activation script..."
    cat > "$RUNNER_HOME/activate-ml-env.sh" << EOF
#!/bin/bash
source $ML_ENV_DIR/bin/activate
echo "ML environment activated. Use 'deactivate' to exit."
EOF
    chmod +x "$RUNNER_HOME/activate-ml-env.sh"
    chown $SUDO_USER:$SUDO_USER "$RUNNER_HOME/activate-ml-env.sh"
    
    # Update bashrc to include ML environment function
    if ! grep -q "ml-env" "$RUNNER_HOME/.bashrc"; then
        print_status "Adding ml-env function to .bashrc"
        cat >> "$RUNNER_HOME/.bashrc" << EOF

# ML environment activation
ml-env() {
    source $ML_ENV_DIR/bin/activate
    echo "ML environment activated. Use 'deactivate' to exit."
}
EOF
    fi
else
    print_warning "Cannot determine sudo user. Skipping ML environment setup."
fi

# Install monitoring tools
print_status "Installing monitoring tools..."

# Install Prometheus node exporter
if ! command -v node_exporter &> /dev/null; then
    print_status "Installing Prometheus node exporter..."
    NODE_EXPORTER_VERSION="1.6.1"
    wget -q https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
    tar xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
    cp node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/
    rm -rf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64*
    
    # Create systemd service
    cat > /etc/systemd/system/node_exporter.service << EOF
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable node_exporter
    systemctl start node_exporter
    print_status "Prometheus node exporter installed and started."
fi

print_status "Installation of MLOps dependencies complete!"
echo
print_status "Next steps:"
echo "1. If you're setting up a GitHub runner, run: ./setup-github-runner.sh"
echo "2. To activate the ML environment: source ~/activate-ml-env.sh or ml-env"
echo "3. If you have a GPU, run: nvidia-smi to verify it's detected"
echo
print_warning "You may need to log out and back in for group changes to take effect."
