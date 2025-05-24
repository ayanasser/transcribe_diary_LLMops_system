#!/bin/bash

# Docker Build Performance Monitor
# Measures and reports on build performance improvements

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
RESULTS_FILE="build_performance_results.json"
SERVICES=("ingestion-api" "job-status-api" "transcription-worker" "llm-worker")

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

# Function to measure build time for a service
measure_build_time() {
    local service=$1
    local build_type=$2
    local use_cache=$3
    
    log "Measuring build time for $service ($build_type, cache: $use_cache)"
    
    # Clean build cache if not using cache
    if [[ "$use_cache" == "false" ]]; then
        docker builder prune -f >/dev/null 2>&1
    fi
    
    local start_time=$(date +%s.%N)
    
    # Build the service
    if [[ "$build_type" == "fast" ]]; then
        export COMPOSE_FILE="docker-compose.yml:docker-compose.fast.yml"
    else
        export COMPOSE_FILE="docker-compose.yml"
    fi
    
    if docker-compose build "$service" >/dev/null 2>&1; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)
        echo "$duration"
    else
        error "Build failed for $service"
        echo "0"
    fi
}

# Function to get image size
get_image_size() {
    local service=$1
    local image_name="mlops_assessment-${service}"
    
    local size=$(docker images --format "{{.Size}}" "$image_name" 2>/dev/null | head -1)
    echo "${size:-0}"
}

# Function to run performance tests
run_performance_tests() {
    log "Running comprehensive build performance tests..."
    
    local results="{"
    local first_service=true
    
    for service in "${SERVICES[@]}"; do
        if [[ "$first_service" == "false" ]]; then
            results="$results,"
        fi
        first_service=false
        
        log "Testing $service..."
        
        # Test scenarios
        local standard_no_cache=$(measure_build_time "$service" "standard" "false")
        local standard_with_cache=$(measure_build_time "$service" "standard" "true")
        local fast_with_cache=$(measure_build_time "$service" "fast" "true")
        local image_size=$(get_image_size "$service")
        
        results="$results
        \"$service\": {
            \"standard_no_cache\": $standard_no_cache,
            \"standard_with_cache\": $standard_with_cache,
            \"fast_with_cache\": $fast_with_cache,
            \"image_size\": \"$image_size\",
            \"cache_improvement_percent\": $(echo "scale=2; ($standard_no_cache - $standard_with_cache) / $standard_no_cache * 100" | bc -l 2>/dev/null || echo "0"),
            \"fast_improvement_percent\": $(echo "scale=2; ($standard_no_cache - $fast_with_cache) / $standard_no_cache * 100" | bc -l 2>/dev/null || echo "0")
        }"
    done
    
    results="$results
    }"
    
    echo "$results" > "$RESULTS_FILE"
    success "Performance test results saved to $RESULTS_FILE"
}

# Function to generate performance report
generate_report() {
    if [[ ! -f "$RESULTS_FILE" ]]; then
        error "No results file found. Run performance tests first."
        return 1
    fi
    
    log "Generating performance report..."
    
    echo
    echo "=========================================="
    echo "Docker Build Performance Report"
    echo "=========================================="
    echo
    
    # Parse results and create table
    printf "%-20s %-12s %-12s %-12s %-12s %-15s\n" \
        "Service" "No Cache" "With Cache" "Fast Build" "Image Size" "Cache Improve"
    printf "%-20s %-12s %-12s %-12s %-12s %-15s\n" \
        "--------------------" "------------" "------------" "------------" "------------" "---------------"
    
    for service in "${SERVICES[@]}"; do
        local no_cache=$(jq -r ".\"$service\".standard_no_cache" "$RESULTS_FILE" 2>/dev/null || echo "0")
        local with_cache=$(jq -r ".\"$service\".standard_with_cache" "$RESULTS_FILE" 2>/dev/null || echo "0")
        local fast_cache=$(jq -r ".\"$service\".fast_with_cache" "$RESULTS_FILE" 2>/dev/null || echo "0")
        local size=$(jq -r ".\"$service\".image_size" "$RESULTS_FILE" 2>/dev/null || echo "N/A")
        local improvement=$(jq -r ".\"$service\".cache_improvement_percent" "$RESULTS_FILE" 2>/dev/null || echo "0")
        
        printf "%-20s %-12.2fs %-12.2fs %-12.2fs %-12s %-15.1f%%\n" \
            "$service" "$no_cache" "$with_cache" "$fast_cache" "$size" "$improvement"
    done
    
    echo
    echo "Key Optimizations Implemented:"
    echo "• BuildKit cache mounts for apt and pip"
    echo "• Multi-stage builds with optimized layer ordering"
    echo "• .dockerignore files to reduce build context"
    echo "• Fast build configuration with registry caching"
    echo
    
    # Calculate total improvements
    local total_no_cache=0
    local total_with_cache=0
    local total_fast=0
    
    for service in "${SERVICES[@]}"; do
        local no_cache=$(jq -r ".\"$service\".standard_no_cache" "$RESULTS_FILE" 2>/dev/null || echo "0")
        local with_cache=$(jq -r ".\"$service\".standard_with_cache" "$RESULTS_FILE" 2>/dev/null || echo "0")
        local fast_cache=$(jq -r ".\"$service\".fast_with_cache" "$RESULTS_FILE" 2>/dev/null || echo "0")
        
        total_no_cache=$(echo "$total_no_cache + $no_cache" | bc -l)
        total_with_cache=$(echo "$total_with_cache + $with_cache" | bc -l)
        total_fast=$(echo "$total_fast + $fast_cache" | bc -l)
    done
    
    local cache_improvement=$(echo "scale=1; ($total_no_cache - $total_with_cache) / $total_no_cache * 100" | bc -l 2>/dev/null || echo "0")
    local fast_improvement=$(echo "scale=1; ($total_no_cache - $total_fast) / $total_no_cache * 100" | bc -l 2>/dev/null || echo "0")
    
    echo "Overall Performance Improvements:"
    echo "• Cache optimization: ${cache_improvement}% faster"
    echo "• Fast build workflow: ${fast_improvement}% faster"
    echo "• Total time saved: $(echo "scale=1; $total_no_cache - $total_fast" | bc -l)s per full build"
    echo
}

# Function to test parallel vs sequential builds
test_parallel_builds() {
    log "Testing parallel vs sequential build performance..."
    
    # Sequential build
    log "Running sequential build..."
    local seq_start=$(date +%s.%N)
    for service in "${SERVICES[@]}"; do
        docker-compose build "$service" >/dev/null 2>&1
    done
    local seq_end=$(date +%s.%N)
    local seq_duration=$(echo "$seq_end - $seq_start" | bc -l)
    
    # Parallel build (using background processes)
    log "Running parallel build..."
    local par_start=$(date +%s.%N)
    local pids=()
    
    for service in "${SERVICES[@]}"; do
        docker-compose build "$service" >/dev/null 2>&1 &
        pids+=($!)
    done
    
    # Wait for all builds
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    local par_end=$(date +%s.%N)
    local par_duration=$(echo "$par_end - $par_start" | bc -l)
    
    local improvement=$(echo "scale=1; ($seq_duration - $par_duration) / $seq_duration * 100" | bc -l)
    
    echo
    echo "Parallel Build Performance:"
    echo "• Sequential build: ${seq_duration}s"
    echo "• Parallel build: ${par_duration}s"
    echo "• Improvement: ${improvement}% faster"
    echo
}

# Function to show build recommendations
show_recommendations() {
    echo
    echo "=========================================="
    echo "Build Optimization Recommendations"
    echo "=========================================="
    echo
    echo "1. Development Workflow:"
    echo "   • Use: ./scripts/build-optimized.sh fast"
    echo "   • Or: docker-compose -f docker-compose.yml -f docker-compose.fast.yml build"
    echo
    echo "2. CI/CD Pipeline:"
    echo "   • Enable BuildKit: export DOCKER_BUILDKIT=1"
    echo "   • Use registry cache: --cache-from registry.io/image:latest"
    echo "   • Build in parallel where possible"
    echo
    echo "3. Production Builds:"
    echo "   • Use: BUILD_TARGET=production ./scripts/build-optimized.sh"
    echo "   • Multi-stage builds reduce final image size"
    echo
    echo "4. Local Development:"
    echo "   • Use bind mounts for code changes"
    echo "   • Only rebuild when dependencies change"
    echo "   • Leverage .dockerignore to reduce context"
    echo
}

# Main execution
main() {
    local command="${1:-test}"
    
    case "$command" in
        "test")
            run_performance_tests
            generate_report
            test_parallel_builds
            show_recommendations
            ;;
        "report")
            generate_report
            ;;
        "parallel")
            test_parallel_builds
            ;;
        "recommendations")
            show_recommendations
            ;;
        "help"|*)
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  test           - Run full performance test suite (default)"
            echo "  report         - Generate report from existing results"
            echo "  parallel       - Test parallel vs sequential builds"
            echo "  recommendations - Show optimization recommendations"
            echo "  help           - Show this help"
            ;;
    esac
}

# Check dependencies
if ! command -v bc >/dev/null 2>&1; then
    warn "bc is required for calculations. Installing..."
    sudo apt-get update && sudo apt-get install -y bc
fi

if ! command -v jq >/dev/null 2>&1; then
    warn "jq is required for JSON parsing. Installing..."
    sudo apt-get update && sudo apt-get install -y jq
fi

main "$@"
