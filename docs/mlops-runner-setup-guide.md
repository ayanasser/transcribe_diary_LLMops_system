# MLOps Self-Hosted Runner Setup Guide

This comprehensive guide walks you through setting up high-performance self-hosted GitHub Actions runners specifically optimized for machine learning operations (MLOps) workflows.

## Overview

Self-hosted runners provide several significant advantages for MLOps pipelines:

- **GPU Access**: Direct access to NVIDIA GPUs for ML model training and inference
- **Resource Control**: Configure CPU, memory, and storage based on ML workload needs
- **Dependency Management**: Pre-installed ML libraries and tools reduce setup time
- **Custom Environment**: Full control over the runtime environment
- **Cost Efficiency**: No GitHub-hosted minutes consumption for resource-intensive ML tasks
- **Persistent Cache**: Cached ML models, Docker layers, and dependencies between runs

## System Requirements

### Minimum Requirements
- 4 CPU cores
- 8GB RAM
- 50GB storage
- Ubuntu 20.04+ or other Linux distribution
- Docker installed
- Python 3.8+

### Recommended for ML Workloads
- 8+ CPU cores
- 32GB+ RAM
- 500GB+ SSD storage
- NVIDIA GPU with CUDA support
- Ubuntu 22.04 or newer

## Quick Setup Instructions

### 1. Prepare Your Environment

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential utilities
sudo apt install -y curl wget git jq build-essential

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit (only if you have NVIDIA GPU)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. Clone the Repository

```bash
git clone git@github.com:ayanasser/transcribe_diary_LLMops_system.git
cd transcribe_diary_LLMops_system
```

### 3. Run the Automated Setup Script

```bash
# Make the setup script executable
chmod +x scripts/setup-github-runner.sh

# Run the setup script
./scripts/setup-github-runner.sh
```

During the setup, you'll need to provide:
1. A GitHub Personal Access Token (PAT) with `repo` and `workflow` scopes
2. Labels for your runner (the script will suggest appropriate ones)

### 4. Start the Runner Service

```bash
# Start the service
sudo systemctl start github-runner

# Check the status
sudo systemctl status github-runner
```

## Manual Setup Process

If you prefer a manual setup or need to customize the installation:

### 1. Create Runner Directory

```bash
mkdir -p ~/github-runner
cd ~/github-runner
```

### 2. Download and Extract Runner Package

```bash
# Download the latest runner
curl -o actions-runner-linux-x64-latest.tar.gz -L https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64.tar.gz

# Extract the archive
tar xzf ./actions-runner-linux-x64-latest.tar.gz
```

### 3. Install Dependencies

```bash
# Install runner dependencies
./bin/installdependencies.sh

# Install MLOps-specific dependencies
sudo apt install -y python3-pip python3-venv
pip3 install --user torch torchvision tensorflow numpy pandas scikit-learn matplotlib pytest
```

### 4. Configure the Runner

1. Go to: `https://github.com/ayanasser/transcribe_diary_LLMops_system/settings/actions/runners/new`
2. Copy the registration token
3. Run the configuration command:

```bash
./config.sh --url https://github.com/ayanasser/transcribe_diary_LLMops_system \
            --token YOUR_REGISTRATION_TOKEN \
            --name "mlops-runner-$(hostname)" \
            --labels "self-hosted,linux,x64,mlops,docker" \
            --work "_work" \
            --unattended \
            --replace
```

### 5. Install as a Service

```bash
# Create a service
sudo ./svc.sh install

# Start the service
sudo ./svc.sh start
```

## MLOps Runner Management

### Starting and Stopping

```bash
# Start the runner service
sudo systemctl start github-runner

# Stop the runner service
sudo systemctl stop github-runner

# Restart the runner service
sudo systemctl restart github-runner
```

### Monitoring

```bash
# Check service status
sudo systemctl status github-runner

# View runner logs
sudo journalctl -u github-runner -f

# View diagnostic logs
cat ~/github-runner/_diag/*.log
```

### Maintenance

Use our management script for common tasks:

```bash
# View available commands
./scripts/manage-runner.sh help

# Update the runner
./scripts/manage-runner.sh update

# Clean up disk space
./scripts/manage-runner.sh clean
```

## Runner Labels for MLOps Workflows

Our runners are configured with specific labels to target workflows to the right environment:

- `self-hosted`: Base label for all custom runners
- `linux`: Operating system
- `x64`: Architecture
- `mlops`: Has MLOps tooling installed
- `docker`: Supports Docker operations
- `gpu`: Has NVIDIA GPU (add this only to GPU-equipped machines)

## Customizing Workflow Files

Your workflow files are already configured to use self-hosted runners. They look like:

```yaml
jobs:
  model-training:
    name: Train ML Model
    runs-on: [self-hosted, linux, mlops, gpu]  # Use GPU runners
    
  deploy:
    name: Deploy API
    runs-on: [self-hosted, linux, mlops]       # No GPU needed
```

## Security Considerations

1. **Dedicated machines**: Use dedicated machines/VMs for runners to isolate workflows
2. **Regular updates**: Keep runner software and dependencies up to date
3. **Limit repositories**: Only allow trusted repositories to use these runners
4. **Secret management**: Use GitHub Secrets instead of hardcoding sensitive values
5. **Network isolation**: Consider network isolation for production deployment runners

## Troubleshooting

### Runner Offline or Unavailable
- Check if the service is running: `sudo systemctl status github-runner`
- Verify network connectivity to GitHub
- Check for errors in logs: `sudo journalctl -u github-runner -e`

### Job Failures
- Look at the job logs in GitHub Actions UI
- Check local diagnostic logs: `cat ~/github-runner/_diag/*.log`
- Verify Docker is working: `docker run hello-world`
- If GPU-related issues: `nvidia-smi` to check GPU status

### Permission Issues
- Ensure the runner has permissions to access required resources
- Add the runner user to needed groups: `sudo usermod -aG docker,sudo runneruser`

### Missing Dependencies
- Run the dependency installer: `./scripts/install-mlops-deps.sh`
- Check Python environment: `python3 -m pip list`

## Advanced Configuration

### GPU Passthrough
For NVIDIA GPU usage in containers:

```yaml
# In your workflow file
steps:
  - name: Run GPU workload
    run: |
      docker run --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Custom Python Virtual Environments
Create isolated environments for different ML frameworks:

```bash
python3 -m venv ~/venvs/torch
source ~/venvs/torch/bin/activate
pip install torch torchvision
```

In your workflow:
```yaml
steps:
  - name: Run PyTorch workload
    run: |
      source ~/venvs/torch/bin/activate
      python train.py
```

---

For further assistance or to report issues with self-hosted runners, please contact the MLOps team.
