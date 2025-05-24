#!/bin/bash

# Optimized Docker Build Script
# This script implements advanced build optimizations for faster development cycles

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICES=("ingestion-api" "job-status-api" "transcription-worker" "llm-worker")
BUILD_TARGET="${BUILD_TARGET:-development}"
REGISTRY="${REGISTRY:-}"
PARALLEL_BUILDS="${PARALLEL_BUILDS:-true}"
CACHE_FROM_REGISTRY="${CACHE_FROM_REGISTRY:-false}"

# Enable BuildKit for advanced features
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to build a single service
build_service() {
    local service=$1
    local start_time=$(date +%s)
    
    log "Building $service..."
    
    # Build arguments
    local build_args=(
        "--build-arg" "BUILDKIT_INLINE_CACHE=1"
        "--build-arg" "BUILD_TARGET=$BUILD_TARGET"
    )
    
    # Add cache from arguments if registry is specified
    if [[ "$CACHE_FROM_REGISTRY" == "true" && -n "$REGISTRY" ]]; then
        build_args+=(
            "--cache-from" "${REGISTRY}${service}:latest"
            "--cache-from" "${REGISTRY}${service}:buildcache"
        )
    fi
    
    # Build the service
    if docker-compose build "${build_args[@]}" "$service"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "Built $service in ${duration}s"
    else
        error "Failed to build $service"
        return 1
    fi
}

# Function to build all services in parallel
build_parallel() {
    log "Building services in parallel..."
    local pids=()
    
    for service in "${SERVICES[@]}"; do
        build_service "$service" &
        pids+=($!)
    done
    
    # Wait for all builds to complete
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            failed=1
        fi
    done
    
    return $failed
}

# Function to build services sequentially
build_sequential() {
    log "Building services sequentially..."
    
    for service in "${SERVICES[@]}"; do
        if ! build_service "$service"; then
            return 1
        fi
    done
}

# Function to clean build cache
clean_cache() {
    log "Cleaning Docker build cache..."
    docker builder prune -f
    docker system prune -f --volumes
    success "Cache cleaned"
}

# Function to show build statistics
show_stats() {
    log "Docker build statistics:"
    echo
    echo "Images built:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -E "(ingestion-api|job-status-api|transcription-worker|llm-worker)" || true
    echo
    echo "Build cache usage:"
    docker system df
}

# Function to test fast development workflow
test_fast_build() {
    log "Testing fast development build workflow..."
    
    # Use the fast compose override
    if [[ -f "docker-compose.fast.yml" ]]; then
        export COMPOSE_FILE="docker-compose.yml:docker-compose.fast.yml"
        log "Using fast build configuration"
    fi
    
    # Build with development target
    BUILD_TARGET=development build_sequential
}

# Function to validate builds
validate_builds() {
    log "Validating built images..."
    
    for service in "${SERVICES[@]}"; do
        local image_name="mlops_assessment-${service}"
        if docker images --format "{{.Repository}}" | grep -q "$image_name"; then
            success "✓ $service image exists"
        else
            error "✗ $service image missing"
            return 1
        fi
    done
}

# Main execution
main() {
    local command="${1:-build}"
    local total_start_time=$(date +%s)
    
    case "$command" in
        "build")
            log "Starting optimized build process..."
            log "Target: $BUILD_TARGET"
            log "Parallel: $PARALLEL_BUILDS"
            
            if [[ "$PARALLEL_BUILDS" == "true" ]]; then
                build_parallel
            else
                build_sequential
            fi
            
            if [[ $? -eq 0 ]]; then
                validate_builds
                show_stats
                local total_time=$(($(date +%s) - total_start_time))
                success "All builds completed successfully in ${total_time}s"
            else
                error "Build process failed"
                exit 1
            fi
            ;;
        "fast")
            test_fast_build
            ;;
        "clean")
            clean_cache
            ;;
        "stats")
            show_stats
            ;;
        "help"|*)
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  build    - Build all services (default)"
            echo "  fast     - Fast development build"
            echo "  clean    - Clean build cache"
            echo "  stats    - Show build statistics"
            echo "  help     - Show this help"
            echo
            echo "Environment variables:"
            echo "  BUILD_TARGET        - development|production (default: development)"
            echo "  PARALLEL_BUILDS     - true|false (default: true)"
            echo "  REGISTRY           - Registry prefix for cache"
            echo "  CACHE_FROM_REGISTRY - true|false (default: false)"
            ;;
    esac
}

main "$@"
