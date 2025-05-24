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

# GitHub Runner Health Check Script
# Tests and validates the health of a self-hosted GitHub Actions runner

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RUNNER_DIR="$HOME/github-runner"
SERVICE_NAME="github-runner"
GITHUB_OWNER="ayanasser"
GITHUB_REPO="transcribe_diary_LLMops_system"

# Print functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check runner installation
check_runner_installed() {
    print_header "RUNNER INSTALLATION"
    
    if [ -d "$RUNNER_DIR" ]; then
        print_success "Runner directory exists at $RUNNER_DIR"
        
        # Check for critical files
        if [ -f "$RUNNER_DIR/run.sh" ] && [ -f "$RUNNER_DIR/config.sh" ]; then
            print_success "Runner scripts are present"
        else
            print_error "Runner scripts are missing"
            return 1
        fi
        
        # Check version
        if [ -f "$RUNNER_DIR/runnerversion" ]; then
            VERSION=$(cat "$RUNNER_DIR/runnerversion")
            print_status "Runner version: $VERSION"
        else
            print_warning "Could not determine runner version"
        fi
    else
        print_error "Runner directory not found at $RUNNER_DIR"
        return 1
    fi
    
    return 0
}

# Check service status
check_service_status() {
    print_header "SERVICE STATUS"
    
    if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
        print_success "Runner service is enabled to start on boot"
    else
        print_warning "Runner service is not enabled to start on boot"
    fi
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Runner service is currently active"
    else
        print_warning "Runner service is not active"
    fi
    
    # Get service uptime
    UPTIME=$(systemctl show -p ActiveEnterTimestamp --value $SERVICE_NAME 2>/dev/null || echo "Unknown")
    if [ "$UPTIME" != "Unknown" ]; then
        print_status "Service started at: $UPTIME"
    fi
}

# Check system resources
check_system_resources() {
    print_header "SYSTEM RESOURCES"
    
    # CPU info
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')"%"
    CPU_CORES=$(nproc)
    print_status "CPU Usage: $CPU_USAGE (across $CPU_CORES cores)"
    
    # Memory info
    MEM_TOTAL=$(free -h | awk 'NR==2{print $2}')
    MEM_USED=$(free -h | awk 'NR==2{print $3}')
    MEM_PERCENT=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')"%"
    print_status "Memory Usage: $MEM_USED / $MEM_TOTAL ($MEM_PERCENT)"
    
    # Disk info
    DISK_USAGE=$(df -h / | awk 'NR==2{print $5}')
    DISK_FREE=$(df -h / | awk 'NR==2{print $4}')
    print_status "Disk Usage: $DISK_USAGE (${DISK_FREE} free)"
    
    # Check if disk usage is high
    DISK_PERCENT=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    if [ "$DISK_PERCENT" -gt 90 ]; then
        print_error "Disk space critically low! Consider cleaning up."
        
        # Show largest directories in runner workspace
        if [ -d "$RUNNER_DIR/_work" ]; then
            print_status "Largest directories in workspace:"
            du -h --max-depth=2 "$RUNNER_DIR/_work" 2>/dev/null | sort -hr | head -5
        fi
    fi
}

# Check GPU (if available)
check_gpu() {
    print_header "GPU STATUS"
    
    if command -v nvidia-smi &> /dev/null; then
        print_success "NVIDIA GPU detected"
        print_status "GPU Information:"
        nvidia-smi --query-gpu=name,driver_version,utilization.gpu,memory.used,memory.total --format=csv,noheader
        
        # Check CUDA
        if [ -d "/usr/local/cuda" ]; then
            CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $6}' | sed 's/,//')
            print_success "CUDA installed: $CUDA_VERSION"
        else
            print_warning "CUDA installation not found in /usr/local/cuda"
        fi
        
        # Check Docker GPU support
        if command -v docker &> /dev/null; then
            if docker info 2>/dev/null | grep -q "nvidia"; then
                print_success "Docker GPU support is configured"
            else
                print_warning "Docker doesn't appear to have GPU support configured"
            fi
        fi
    else
        print_status "No NVIDIA GPU detected"
    fi
}

# Check Docker
check_docker() {
    print_header "DOCKER STATUS"
    
    if command -v docker &> /dev/null; then
        print_success "Docker is installed"
        print_status "Docker version: $(docker --version)"
        
        # Check if Docker is running
        if docker info &> /dev/null; then
            print_success "Docker daemon is running"
            
            # Show container count
            CONTAINER_COUNT=$(docker ps -q | wc -l)
            print_status "Running containers: $CONTAINER_COUNT"
            
            # Show disk usage
            print_status "Docker disk usage:"
            docker system df | grep -v "TYPE"
        else
            print_error "Docker daemon is not running"
        fi
        
        # Check if user is in docker group
        if groups | grep -q '\bdocker\b'; then
            print_success "User is in docker group"
        else
            print_warning "User is not in docker group. May have permission issues."
        fi
    else
        print_error "Docker is not installed"
    fi
}

# Check Python environment
check_python() {
    print_header "PYTHON ENVIRONMENT"
    
    if command -v python3 &> /dev/null; then
        print_success "Python is installed"
        print_status "Python version: $(python3 --version 2>&1)"
        
        # Check for ML environment
        ML_ENV_DIR="$HOME/ml-env"
        if [ -d "$ML_ENV_DIR" ]; then
            print_success "ML environment exists at $ML_ENV_DIR"
            
            # List some key packages
            if [ -f "$ML_ENV_DIR/bin/pip" ]; then
                print_status "Key ML packages:"
                $ML_ENV_DIR/bin/pip list | grep -E "numpy|torch|tensorflow|pandas|scikit-learn" || echo "No common ML packages found"
            fi
        else
            print_status "No dedicated ML environment found at $ML_ENV_DIR"
        fi
    else
        print_error "Python3 is not installed"
    fi
}

# Check network connectivity
check_network() {
    print_header "NETWORK CONNECTIVITY"
    
    # Check GitHub connectivity
    if ping -c 1 github.com &> /dev/null; then
        print_success "Connected to GitHub"
    else
        print_error "Cannot connect to GitHub"
    fi
    
    # Check if any specific ports are blocked
    print_status "Checking for network limitations..."
    if curl -s https://api.github.com &> /dev/null; then
        print_success "Can connect to GitHub API"
    else
        print_error "Cannot connect to GitHub API"
    fi
    
    # Check outbound connections
    print_status "Outbound connections:"
    netstat -tn 2>/dev/null | grep ESTABLISHED | wc -l | xargs echo "  Established connections:"
}

# Check logs for errors
check_logs() {
    print_header "LOG ANALYSIS"
    
    # Get recent runner errors
    if systemctl status $SERVICE_NAME &> /dev/null; then
        ERROR_COUNT=$(journalctl -u $SERVICE_NAME -p err..crit --since "24 hours ago" 2>/dev/null | wc -l)
        
        if [ "$ERROR_COUNT" -gt 0 ]; then
            print_warning "Found $ERROR_COUNT errors/critical issues in the logs (last 24h)"
            print_status "Recent errors (last 5):"
            journalctl -u $SERVICE_NAME -p err..crit --since "24 hours ago" -n 5 --no-pager 2>/dev/null
        else
            print_success "No errors found in logs (last 24h)"
        fi
    else
        print_warning "Cannot access service logs"
    fi
    
    # Check for common issues in runner logs
    if [ -d "$RUNNER_DIR/_diag" ]; then
        RECENT_LOGS=$(find "$RUNNER_DIR/_diag" -name "*.log" -mtime -1 | wc -l)
        print_status "Found $RECENT_LOGS log files created in the last 24h"
    fi
}

# Generate summary report
generate_summary() {
    print_header "HEALTH CHECK SUMMARY"
    
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "Runner directory: $RUNNER_DIR"
    echo "Service name: $SERVICE_NAME"
    
    # Overall status
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "Overall status: ${GREEN}HEALTHY${NC} - Runner service is active"
    else
        echo -e "Overall status: ${RED}UNHEALTHY${NC} - Runner service is not active"
    fi
    
    # Recommendations section
    echo -e "\n${BLUE}=== RECOMMENDATIONS ===${NC}"
    
    # Service issues
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "* ${YELLOW}Start the runner service:${NC} sudo systemctl start $SERVICE_NAME"
    fi
    
    # Disk space issues
    DISK_PERCENT=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    if [ "$DISK_PERCENT" -gt 80 ]; then
        echo -e "* ${YELLOW}Clean up disk space:${NC} docker system prune -af"
    fi
    
    # Docker group check
    if command -v docker &> /dev/null && ! groups | grep -q '\bdocker\b'; then
        echo -e "* ${YELLOW}Add user to docker group:${NC} sudo usermod -aG docker \$USER && newgrp docker"
    fi
}

# Main function
main() {
    echo "GitHub Runner Health Check - $(date)"
    echo "============================================"
    
    check_runner_installed
    check_service_status
    check_system_resources
    check_gpu
    check_docker
    check_python
    check_network
    check_logs
    generate_summary
    
    echo -e "\nHealth check completed!"
}

# Run main function
main
