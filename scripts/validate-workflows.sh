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

# GitHub Workflow Validation Script
# Simple version that checks workflows are correctly configured for self-hosted runners

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Simple print functions
echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Main validation function
validate_workflows() {
    echo "===== GitHub Workflow Validation ====="
    echo "Checking workflow files for self-hosted runner configuration"
    echo "--------------------------------------"
    
    # Find workflow directory
    WORKFLOWS_DIR="/home/aya/mlops_assessment/.github/workflows"
    
    if [ ! -d "$WORKFLOWS_DIR" ]; then
        echo_error "Workflows directory not found: $WORKFLOWS_DIR"
        return 1
    fi
    
    echo_info "Found workflows directory: $WORKFLOWS_DIR"
    
    # List workflow files
    WORKFLOW_FILES=$(ls $WORKFLOWS_DIR/*.yml 2>/dev/null)
    if [ -z "$WORKFLOW_FILES" ]; then
        echo_warning "No workflow files found"
        return 0
    fi
    
    # Check each workflow file
    for file in $WORKFLOW_FILES; do
        echo ""
        echo "Checking $(basename $file)..."
        
        # Check for self-hosted runners
        if grep -q "self-hosted" "$file"; then
            echo_success "✅ Uses self-hosted runners"
            
            # Check for specific labels
            if grep -q "linux" "$file"; then
                echo_info "✅ Includes 'linux' label"
            fi
            
            if grep -q "mlops" "$file"; then
                echo_info "✅ Includes 'mlops' label"
            fi
            
            if grep -q "docker" "$file"; then
                echo_info "✅ Includes 'docker' label"
            fi
            
            if grep -q "gpu" "$file"; then
                echo_info "✅ Includes 'gpu' label"
            fi
        else
            echo_warning "❌ Does NOT use self-hosted runners"
        fi
        
        # Check for common issues
        if grep -q "docker" "$file" && ! grep -q "runs-on:.*docker" "$file"; then
            echo_warning "⚠️ Uses Docker but may not have 'docker' label"
        fi
        
        if grep -qE "nvidia|cuda|gpu" "$file" && ! grep -q "runs-on:.*gpu" "$file"; then
            echo_warning "⚠️ Uses GPU features but may not have 'gpu' label"
        fi
    done
    
    echo ""
    echo_success "Validation completed"
}

# Call main function
validate_workflows
