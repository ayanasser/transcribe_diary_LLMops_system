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

# GitHub Runner Management Script
# Controls the GitHub Actions self-hosted runner

RUNNER_DIR="$HOME/github-runner"
SERVICE_NAME="github-runner"
DRY_RUN=false

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

show_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|remove} [--dry-run]"
    echo ""
    echo "Commands:"
    echo "  start   - Start the GitHub runner service"
    echo "  stop    - Stop the GitHub runner service"
    echo "  restart - Restart the GitHub runner service"
    echo "  status  - Show runner service status"
    echo "  logs    - Show runner logs (follow mode)"
    echo "  remove  - Remove and unregister the runner"
    echo ""
    echo "Options:"
    echo "  --dry-run  - Test commands without actually executing them"
    echo ""
}

start_runner() {
    print_status "Starting GitHub runner service..."
    sudo systemctl start $SERVICE_NAME
    
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Runner service started successfully!"
        print_status "Check status at: https://github.com/ayanasser/transcribe_diary_LLMops_system/settings/actions/runners"
    else
        print_error "Failed to start runner service."
        return 1
    fi
}

stop_runner() {
    print_status "Stopping GitHub runner service..."
    sudo systemctl stop $SERVICE_NAME
    
    if ! sudo systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Runner service stopped successfully!"
    else
        print_error "Failed to stop runner service."
        return 1
    fi
}

restart_runner() {
    print_status "Restarting GitHub runner service..."
    sudo systemctl restart $SERVICE_NAME
    
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Runner service restarted successfully!"
    else
        print_error "Failed to restart runner service."
        return 1
    fi
}

show_status() {
    print_status "GitHub Runner Service Status:"
    echo "================================"
    
    # Service status
    sudo systemctl status $SERVICE_NAME --no-pager
    
    echo ""
    print_status "System Resources:"
    echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')"
    echo "Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
    echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
    
    echo ""
    print_status "Docker Status:"
    docker system df 2>/dev/null || echo "Docker not available"
}

show_logs() {
    print_status "Following GitHub runner logs (Ctrl+C to exit)..."
    sudo journalctl -u $SERVICE_NAME -f
}

remove_runner() {
    print_warning "This will permanently remove and unregister the runner."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Stopping runner service..."
        sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
        
        print_status "Disabling runner service..."
        sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
        
        print_status "Removing service file..."
        sudo rm -f /etc/systemd/system/$SERVICE_NAME.service
        sudo systemctl daemon-reload
        
        if [ -d "$RUNNER_DIR" ]; then
            print_status "Unregistering runner..."
            cd "$RUNNER_DIR"
            
            print_warning "You need to provide a GitHub Personal Access Token (PAT) for removal."
            read -p "Enter your GitHub token: " -s GITHUB_TOKEN
            echo
            
            ./config.sh remove --token "$GITHUB_TOKEN" 2>/dev/null || true
            
            print_status "Removing runner directory..."
            cd ~
            rm -rf "$RUNNER_DIR"
        fi
        
        print_status "Runner removed successfully!"
    else
        print_status "Removal cancelled."
    fi
}

# Parse command line arguments
parse_args() {
    COMMAND=$1
    shift
    
    if [[ $# -gt 0 ]]; then
        case "$1" in
            --dry-run)
                DRY_RUN=true
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    fi
}

# Main script logic
COMMAND=$1
shift
parse_args "$COMMAND" "$@"

if [ "$DRY_RUN" = true ]; then
    print_warning "DRY RUN MODE: Commands will be simulated but not executed"
fi

case "$COMMAND" in
    start)
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would start GitHub runner service"
        else
            start_runner
        fi
        ;;
    stop)
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would stop GitHub runner service"
        else
            stop_runner
        fi
        ;;
    restart)
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would restart GitHub runner service"
        else
            restart_runner
        fi
        ;;
    status)
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would check GitHub runner status"
            print_status "[DRY RUN] Service: $SERVICE_NAME"
            print_status "[DRY RUN] Directory: $RUNNER_DIR"
        else
            show_status
        fi
        ;;
    logs)
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would show logs for GitHub runner"
        else
            show_logs
        fi
        ;;
    remove)
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would remove and unregister the runner"
        else
            remove_runner
        fi
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

exit $?
