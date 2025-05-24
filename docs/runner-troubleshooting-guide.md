# Self-Hosted Runner Troubleshooting Guide

This document provides solutions for common issues that may occur with self-hosted GitHub Actions runners.

## Common Issues and Solutions

### Runner Service Won't Start

**Issue:** The GitHub runner service fails to start.

**Possible Causes & Solutions:**

1. **Service not properly configured:**
   ```bash
   # Check service status
   sudo systemctl status github-runner
   
   # Check logs for errors
   sudo journalctl -u github-runner -e
   ```

2. **Runner files missing:**
   ```bash
   # Check if runner directory exists and has all necessary files
   ls -la ~/github-runner
   ```

3. **Permission issues:**
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER ~/github-runner
   
   # Fix run.sh permissions
   chmod +x ~/github-runner/run.sh
   ```

### Runner Shows Offline in GitHub

**Issue:** Runner appears offline in GitHub repository settings.

**Solutions:**

1. **Restart the runner service:**
   ```bash
   sudo systemctl restart github-runner
   ```

2. **Check network connectivity:**
   ```bash
   # Verify GitHub connectivity
   ping github.com
   curl -I https://github.com
   ```

3. **Re-register the runner:**
   ```bash
   cd ~/github-runner
   ./config.sh remove
   # Then run setup-github-runner.sh again
   ```

### Runner Can't Run Workflows with GPU

**Issue:** Workflows can't access the GPU.

**Solutions:**

1. **Verify GPU is detected:**
   ```bash
   nvidia-smi
   ```

2. **Check if NVIDIA Container Toolkit is installed:**
   ```bash
   docker info | grep -i nvidia
   ```

3. **Install/reinstall NVIDIA drivers:**
   ```bash
   sudo apt install nvidia-driver-XXX
   # Replace XXX with appropriate driver version
   ```

4. **Test with a simple container:**
   ```bash
   docker run --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
   ```

### Runner Can't Execute Docker Commands

**Issue:** Docker commands fail in workflows.

**Solutions:**

1. **Add user to docker group:**
   ```bash
   sudo usermod -aG docker $USER
   # Restart runner service after this
   ```

2. **Verify docker socket permissions:**
   ```bash
   ls -la /var/run/docker.sock
   ```

3. **Restart Docker service:**
   ```bash
   sudo systemctl restart docker
   ```

### Workflow Timeouts

**Issue:** Workflows take too long and time out.

**Solutions:**

1. **Check resource utilization:**
   ```bash
   top
   htop
   free -h
   df -h
   ```

2. **Increase timeout in workflow file:**
   ```yaml
   jobs:
     build:
       timeout-minutes: 60  # Increase this value
   ```

3. **Optimize workflow steps using caching:**
   ```yaml
   - name: Cache dependencies
     uses: actions/cache@v3
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
   ```

## Maintenance Tasks

### Updating the Runner

To update the runner to the latest version:

```bash
./scripts/update-runner.sh
```

### Monitoring Runner Health

Run regular health checks:

```bash
# Check service status
sudo systemctl status github-runner

# Check system resources
./scripts/health-check.sh

# Check logs for errors
sudo journalctl -u github-runner -e | grep -i error
```

### Clearing Disk Space

Remove unnecessary files:

```bash
# Clean up Docker resources
docker system prune -af --volumes

# Clean up runner work directories
cd ~/github-runner/_work
find . -type d -name "node_modules" -exec rm -rf {} +
find . -type d -name ".git" -exec rm -rf {} +
```

## Advanced Configuration

### Adding Custom Labels

Edit your runner configuration:

```bash
cd ~/github-runner
./config.sh remove
./config.sh --url https://github.com/ayanasser/transcribe_diary_LLMops_system \
            --token <YOUR_TOKEN> \
            --name "mlops-runner-$(hostname)" \
            --labels "self-hosted,linux,x64,mlops,docker,custom-label" \
            --unattended
```

### Configuring Multiple Runners

To set up multiple runners on the same machine:

```bash
# Create a new runner directory
mkdir ~/github-runner2

# Copy setup-github-runner.sh
cp ~/mlops_assessment/scripts/setup-github-runner.sh ~/setup-runner2.sh

# Edit the script to use different directories and names
# Then run the modified script
```

## Logs and Diagnostics

### Collecting Diagnostic Information

If you need to provide diagnostic information to GitHub support:

```bash
# Collect runner information
cd ~/github-runner
./run.sh --check

# Export logs
sudo journalctl -u github-runner -o json > runner-logs.json
```
