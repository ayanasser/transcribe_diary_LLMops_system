# MIT License
# Copyright (c) 2025 Aya Nasser

# Environment configuration for GitHub self-hosted runners
# This file contains environment variables and paths needed for MLOps workflows

# GitHub Repository Configuration
export GITHUB_OWNER="ayanasser"
export GITHUB_REPO="transcribe_diary_LLMops_system"
export RUNNER_WORK_DIR="$HOME/github-runner/_work"

# Docker Configuration
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Python Configuration  
export PYTHONPATH="$RUNNER_WORK_DIR/transcribe_diary_LLMops_system/transcribe_diary_LLMops_system:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# MLOps Tools Paths
export PATH="/usr/local/bin:$PATH"

# Resource Limits for ML Workflows
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4

# Cleanup settings
export RUNNER_CLEANUP_WORKSPACE=true

# Logging
export RUNNER_LOG_LEVEL=INFO
