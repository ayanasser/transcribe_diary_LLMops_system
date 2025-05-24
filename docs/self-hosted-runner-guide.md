# Self-Hosted GitHub Runner Setup Guide

This guide provides instructions for setting up GitHub self-hosted runners for the MLOps Assessment project.

## Why Use Self-Hosted Runners?

Self-hosted runners provide several advantages for MLOps workflows:

- **Custom Hardware**: Access to GPUs for ML model training and inference
- **Persistent Storage**: Cache models and data between workflow runs
- **Faster Builds**: Local Docker cache improves build times significantly
- **Cost Efficiency**: No GitHub-hosted minutes consumption
- **Custom Dependencies**: Pre-installed ML libraries and specialized tools

## Requirements

- Linux server/VM/desktop with:
  - At least 4 CPU cores
  - Minimum 8GB RAM (16GB+ recommended)
  - 100GB+ disk space
  - Docker installed
  - Python 3.8+ installed
  - Optional: NVIDIA GPU with CUDA support

## Quick Setup

1. Clone the repository:
   ```bash
   git clone git@github.com:ayanasser/transcribe_diary_LLMops_system.git
   cd transcribe_diary_LLMops_system
   ```

2. Run the setup script:
   ```bash
   chmod +x scripts/setup-github-runner.sh
   ./scripts/setup-github-runner.sh
   ```

3. When prompted, enter your GitHub Personal Access Token (PAT).
   - Create one at: https://github.com/settings/tokens
   - Required scopes: `repo`, `workflow`

4. Start the runner service:
   ```bash
   sudo systemctl start github-runner
   sudo systemctl status github-runner
   ```

## Manual Setup

If you prefer manual installation:

1. Create a directory for the runner:
   ```bash
   mkdir ~/github-runner && cd ~/github-runner
   ```

2. Download the runner package:
   ```bash
   curl -o actions-runner-linux-x64-2.321.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
   ```

3. Extract the installer:
   ```bash
   tar xzf ./actions-runner-linux-x64-2.321.0.tar.gz
   ```

4. Configure the runner:
   ```bash
   ./config.sh --url https://github.com/ayanasser/transcribe_diary_LLMops_system \
               --token YOUR_TOKEN \
               --name "mlops-runner-$(hostname)" \
               --labels "self-hosted,linux,x64,mlops" \
               --work "_work" \
               --unattended
   ```

5. Install as a service:
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

## Runner Labels & Job Targeting

The setup script configures runners with these labels:
- `self-hosted`: All custom runners
- `linux`: Operating system
- `x64`: Architecture
- `mlops`: MLOps-specific tooling
- `docker`: Docker capability
- `gpu`: GPU-equipped machines (optional)

Target specific runners in workflows:
```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, mlops]
    # OR
    runs-on: [self-hosted, linux, mlops, gpu]
```

## Troubleshooting

- **Runner offline**: Check the service status with `sudo systemctl status github-runner`
- **Job failures**: Check logs at `~/github-runner/_diag/`
- **Permission issues**: Ensure the runner user has permissions for Docker and the workspace
- **Missing dependencies**: Use `scripts/install-mlops-deps.sh` to install common MLOps tools

## Security Considerations

1. Use dedicated machines/VMs for runners
2. Regularly update runner software with `scripts/update-runner.sh`
3. Consider network isolation for production deployment runners
4. Review jobs allowed to run on your self-hosted runners in repository settings

## Maintenance

- **Update runner**: Run `scripts/update-runner.sh`
- **Monitor disk space**: Clean Docker images periodically with `docker system prune`
- **Backup runner configuration**: Copy `~/github-runner/.runner` and `~/github-runner/.credentials`
