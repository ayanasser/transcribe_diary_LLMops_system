#!/bin/bash

# MLOps Service Health Check Script
# Usage: ./health-check.sh

echo "🔍 MLOps Assessment - Service Health Check"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

# Function to test HTTP endpoint
test_endpoint() {
    local url=$1
    local name=$2
    local expected_code=${3:-200}
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    
    if [ "$response" = "$expected_code" ] || [ "$response" = "200" ] || [ "$response" = "302" ]; then
        echo "✅ $name: HTTP $response"
    else
        echo "❌ $name: HTTP $response (Expected $expected_code)"
    fi
}

# Function to check Docker container status
check_container() {
    local container_name=$1
    local display_name=$2
    
    status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null)
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null)
    
    if [ "$status" = "running" ]; then
        if [ "$health" = "healthy" ]; then
            echo "✅ $display_name: Running (Healthy)"
        elif [ "$health" = "unhealthy" ]; then
            echo "⚠️  $display_name: Running (Unhealthy)"
        elif [ "$health" = "starting" ]; then
            echo "🔄 $display_name: Running (Starting)"
        else
            echo "✅ $display_name: Running"
        fi
    elif [ "$status" = "restarting" ]; then
        echo "🔄 $display_name: Restarting"
    elif [ "$status" = "exited" ]; then
        echo "❌ $display_name: Stopped"
    else
        echo "❓ $display_name: Unknown ($status)"
    fi
}

echo "📊 Monitoring Dashboards:"
test_endpoint "http://localhost:3000" "Grafana" "302"
test_endpoint "http://localhost:9090" "Prometheus" "302"
test_endpoint "http://localhost:16686" "Jaeger" "200"

echo ""
echo "🔌 API Endpoints:"
test_endpoint "http://localhost:8000/health" "Ingestion API"
test_endpoint "http://localhost:8001/health" "Job Status API"

echo ""
echo "🐳 Container Status:"
check_container "transcription-grafana" "Grafana"
check_container "transcription-prometheus" "Prometheus"
check_container "transcription-jaeger" "Jaeger"
check_container "transcription-otel-collector" "OpenTelemetry"
check_container "transcription-ingestion-api" "Ingestion API"
check_container "transcription-job-status-api" "Job Status API"
check_container "mlops_assessment_llm-worker_1" "LLM Worker 1"
check_container "mlops_assessment_llm-worker_2" "LLM Worker 2"
check_container "mlops_assessment_transcription-worker_1" "Transcription Worker 1"
check_container "mlops_assessment_transcription-worker_2" "Transcription Worker 2"
check_container "transcription-postgres" "PostgreSQL"
check_container "transcription-redis" "Redis"

echo ""
echo "💾 Infrastructure Status:"
check_container "transcription-postgres" "Database"
check_container "transcription-redis" "Message Queue"

echo ""
echo "🌐 Quick Access URLs:"
echo "   Grafana:    http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo "   Jaeger:     http://localhost:16686"
echo "   Job API:    http://localhost:8001"
echo "   Ingestion:  http://localhost:8000"

echo ""
echo "📈 System Resources:"
echo "   Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "   Disk:   $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"

# Check for recent container restarts
echo ""
echo "🔄 Recent Activity:"
recent_restarts=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(Restarting|Up [0-9]+ seconds)" | wc -l)
if [ "$recent_restarts" -gt 0 ]; then
    echo "⚠️  $recent_restarts container(s) recently restarted:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(Restarting|Up [0-9]+ seconds)"
else
    echo "✅ All containers stable"
fi

echo ""
echo "=========================================="
echo "Health check completed at $(date)"
