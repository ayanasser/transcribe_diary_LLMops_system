# Operational Runbook
## MLOps Audio Transcription & Diary Generation System

### Document Information
- **Version**: 1.0
- **Date**: May 24, 2025
- **Purpose**: Operational procedures and troubleshooting
- **Audience**: DevOps Engineers, SREs, System Administrators

---

## 🚀 Quick Start Guide

### Local Development Deployment

#### Prerequisites
```bash
# Required software
- Docker Engine 20.10+
- Docker Compose 2.0+
- GNU Make
- 16GB+ RAM, 8+ CPU cores
- 50GB+ free disk space

# Optional for GPU support
- NVIDIA Docker Toolkit
- CUDA 11.8+ compatible GPU
```

#### Deployment Commands
```bash
# Clone repository
git clone <repository-url>
cd mlops_assessment

# Start full stack
make up

# Check service health
make health

# View logs
make logs

# Development mode with hot reload
make dev

# Scale workers
docker-compose up --scale transcription-worker=4

# GPU-enabled deployment
docker-compose --profile gpu up
```

#### Service Verification
```bash
# API Health Checks
curl http://localhost:8000/health  # Ingestion API
curl http://localhost:8001/health  # Job Status API

# Submit test job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://example.com/audio.mp3",
    "priority": "medium",
    "whisper_model": "base"
  }'

# Check job status
curl http://localhost:8001/jobs/<job_id>
```

### Cloud Production Deployment

#### GCP Kubernetes Deployment
```bash
# Set up GCP project
export PROJECT_ID="your-project-id"
export CLUSTER_NAME="transcription-cluster"
export REGION="us-central1"

# Create GKE cluster
gcloud container clusters create $CLUSTER_NAME \
  --project=$PROJECT_ID \
  --zone=$REGION-a \
  --machine-type=n1-standard-4 \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10

# Deploy application
kubectl apply -f infrastructure/k8s/base/
kubectl apply -f infrastructure/k8s/overlays/production/

# Verify deployment
kubectl get pods -n default
kubectl get services -n default
```

---

## 📊 Monitoring & Observability

### Access Monitoring Dashboards

#### Local Development
```bash
# Prometheus (Metrics)
http://localhost:9090

# Grafana (Dashboards)
http://localhost:3000
# Login: admin/admin

# Jaeger (Distributed Tracing)
http://localhost:16686

# OpenTelemetry Collector
http://localhost:8889/metrics
```

#### Key Metrics to Monitor

##### System Health Metrics
```yaml
Service Availability:
  - endpoint_up{service="ingestion-api"} == 1
  - endpoint_up{service="job-status-api"} == 1
  - redis_up == 1
  - postgres_up == 1

Response Times:
  - http_request_duration_seconds_bucket{le="0.2"} > 0.95
  - job_processing_duration_seconds < 300

Error Rates:
  - rate(http_requests_total{status=~"5.."}[5m]) < 0.01
  - rate(job_failures_total[5m]) < 0.05
```

##### Business Metrics
```yaml
Throughput:
  - rate(jobs_submitted_total[1h])
  - rate(jobs_completed_total[1h])
  - rate(transcriptions_completed_total[1h])

Queue Health:
  - redis_queue_depth{queue="transcription_queue"} < 100
  - redis_queue_depth{queue="llm_queue"} < 200

Resource Utilization:
  - cpu_usage_percent < 80
  - memory_usage_percent < 85
  - gpu_usage_percent < 90
```

### Alerting Rules

#### Critical Alerts (Immediate Response)
```yaml
Service Down:
  - Alert: ServiceDown
  - Condition: up == 0
  - Duration: 1m
  - Severity: critical

High Error Rate:
  - Alert: HighErrorRate
  - Condition: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  - Duration: 5m
  - Severity: critical

Queue Backup:
  - Alert: QueueBackup
  - Condition: redis_queue_depth > 500
  - Duration: 10m
  - Severity: warning
```

#### Warning Alerts (Attention Required)
```yaml
High Latency:
  - Alert: HighLatency
  - Condition: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1.0
  - Duration: 10m
  - Severity: warning

Resource Exhaustion:
  - Alert: HighResourceUsage
  - Condition: cpu_usage_percent > 85 OR memory_usage_percent > 90
  - Duration: 15m
  - Severity: warning
```

---

## 🔧 Troubleshooting Guide

### Common Issues & Solutions

#### Service Startup Issues

##### Issue: Services fail to start
```bash
# Check Docker logs
docker-compose logs <service-name>

# Common causes:
1. Port conflicts (8000, 8001, 5432, 6379)
2. Insufficient resources (RAM/CPU)
3. Missing environment variables
4. Volume mount issues

# Solutions:
# Change ports in docker-compose.yml
# Increase Docker resource limits
# Check .env file or environment variables
# Verify volume permissions
```

##### Issue: Database connection failures
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U user -d transcription_db

# Check connection from services
docker-compose exec ingestion-api python -c "
from shared.utils.helpers import get_db_connection
try:
    conn = get_db_connection()
    print('Database connection: OK')
except Exception as e:
    print(f'Database connection failed: {e}')
"

# Common solutions:
# Wait for database initialization (30-60 seconds)
# Check DATABASE_URL environment variable
# Verify PostgreSQL container health
```

##### Issue: Redis connection failures
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Check from application
docker-compose exec transcription-worker python -c "
from shared.utils.helpers import redis_client
print('Redis health:', redis_client.health_check())
"

# Common solutions:
# Verify Redis container is running
# Check REDIS_HOST environment variable
# Ensure Redis health check passes
```

#### Processing Issues

##### Issue: Jobs stuck in PENDING status
```bash
# Check transcription worker logs
docker-compose logs transcription-worker

# Check Redis queues
docker-compose exec redis redis-cli LLEN transcription_queue
docker-compose exec redis redis-cli LLEN llm_queue

# Common causes:
1. Workers not processing messages
2. Worker crashes or hangs
3. Redis connectivity issues
4. Queue subscription problems

# Solutions:
# Restart workers: docker-compose restart transcription-worker
# Scale workers: docker-compose up --scale transcription-worker=3
# Check worker health endpoints
# Monitor worker resource usage
```

##### Issue: Transcription failures
```bash
# Check worker logs
docker-compose logs transcription-worker

# Common errors:
1. Audio download failures (404, timeout)
2. Unsupported audio format
3. Out of memory errors
4. Model loading failures

# Solutions:
# Verify audio URL accessibility
# Check supported formats: MP3, WAV, M4A, FLAC, OGG
# Increase worker memory: update docker-compose.yml
# Clear model cache: docker volume rm whisper_cache
```

##### Issue: LLM generation failures
```bash
# Check LLM worker logs
docker-compose logs llm-worker

# Common errors:
1. OpenAI API key issues
2. Rate limiting
3. Token limit exceeded
4. Provider service outages

# Solutions:
# Verify OPENAI_API_KEY environment variable
# Check API key validity and quotas
# Implement retry logic (already included)
# Monitor provider status pages
```

#### Performance Issues

##### Issue: High API response times
```bash
# Check API metrics
curl http://localhost:9090/api/v1/query?query=rate(http_request_duration_seconds_sum[5m])

# Check resource usage
docker stats

# Common causes:
1. Database query performance
2. High concurrent load
3. Resource contention
4. Inefficient code paths

# Solutions:
# Scale API services horizontally
# Optimize database queries
# Add Redis caching
# Profile application performance
```

##### Issue: Queue processing delays
```bash
# Check queue depths
docker-compose exec redis redis-cli LLEN transcription_queue
docker-compose exec redis redis-cli LLEN llm_queue

# Check worker scaling
docker-compose ps

# Solutions:
# Scale workers: docker-compose up --scale transcription-worker=5
# Optimize worker performance
# Add priority queue processing
# Monitor resource bottlenecks
```

### Debugging Commands

#### Application Debugging
```bash
# Enter container for debugging
docker-compose exec ingestion-api bash
docker-compose exec transcription-worker bash

# Check Python environment
python --version
pip list

# Test imports
python -c "import whisper; print('Whisper OK')"
python -c "import openai; print('OpenAI OK')"

# Check configuration
python -c "from shared.config.settings import settings; print(settings.dict())"
```

#### Network Debugging
```bash
# Check container networking
docker network ls
docker network inspect mlops_assessment_transcription-net

# Test connectivity between services
docker-compose exec ingestion-api ping redis
docker-compose exec ingestion-api ping postgres

# Check port binding
netstat -tlnp | grep -E "(8000|8001|5432|6379)"
```

#### Storage Debugging
```bash
# Check volume mounts
docker volume ls
docker volume inspect shared_storage

# Check file permissions
docker-compose exec ingestion-api ls -la /app/storage

# Check disk usage
docker system df
docker system prune  # Clean up unused resources
```

---

## 🛡️ Security Operations

### Security Monitoring

#### Access Control
```bash
# Check API authentication (when implemented)
curl -H "Authorization: Bearer invalid-token" http://localhost:8000/jobs
# Should return 401 Unauthorized

# Monitor failed authentication attempts
grep "authentication failed" logs/*.log
```

#### Vulnerability Management
```bash
# Scan Docker images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image transcription-ingestion-api:latest

# Update base images regularly
docker-compose pull
docker-compose up -d --build
```

#### Data Protection
```bash
# Check for sensitive data in logs
grep -r "password\|secret\|key" logs/
# Should not reveal actual secrets

# Verify encryption in transit
curl -k -v https://localhost/api/health 2>&1 | grep "SSL certificate"
```

### Incident Response

#### Security Incident Procedure
```yaml
1. Immediate Response:
   - Isolate affected services
   - Preserve logs and evidence
   - Notify security team

2. Investigation:
   - Analyze logs and traces
   - Identify attack vectors
   - Assess data exposure

3. Remediation:
   - Patch vulnerabilities
   - Update security controls
   - Rotate compromised credentials

4. Recovery:
   - Restore services
   - Verify security posture
   - Document lessons learned
```

---

## 📈 Performance Tuning

### Optimization Strategies

#### API Performance
```bash
# Enable HTTP/2 and compression
# Add to nginx.conf:
http2_max_field_size 16k;
gzip on;
gzip_types text/plain application/json;

# Optimize FastAPI
# In production:
workers = (2 * CPU_cores) + 1
worker_class = "uvicorn.workers.UvicornWorker"
```

#### Database Performance
```bash
# PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;

# Add database indexes
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

#### Worker Performance
```bash
# Transcription worker optimization
# Use GPU when available
export WHISPER_DEVICE=cuda

# Optimize model loading
export WHISPER_CACHE_DIR=/app/whisper_cache

# LLM worker optimization
# Batch requests when possible
export LLM_BATCH_SIZE=5
export LLM_TIMEOUT=30
```

#### Redis Performance
```bash
# Redis configuration
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

### Load Testing

#### API Load Testing
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test ingestion API
ab -n 1000 -c 10 -H "Content-Type: application/json" \
   -p test-job.json http://localhost:8000/jobs

# Test status API
ab -n 1000 -c 10 http://localhost:8001/jobs/test-job-id
```

#### End-to-End Testing
```bash
# Submit multiple concurrent jobs
for i in {1..10}; do
  curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d "{\"audio_url\": \"https://example.com/audio$i.mp3\"}" &
done
wait
```

---

## 💰 Cost Management

### Cost Monitoring

#### Resource Usage Tracking
```bash
# Monitor CPU/Memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Track storage usage
docker system df
du -sh /var/lib/docker/volumes/

# Monitor API usage
grep "POST /jobs" logs/ingestion-api.log | wc -l  # Jobs submitted
grep "completed" logs/transcription-worker.log | wc -l  # Jobs completed
```

#### LLM Cost Tracking
```bash
# OpenAI API usage (requires API key with billing access)
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     "https://api.openai.com/v1/usage?date=$(date +%Y-%m-%d)"

# Track token usage in application logs
grep "token_usage" logs/llm-worker.log | \
  awk '{sum += $5} END {print "Total tokens:", sum}'
```

### Cost Optimization

#### Infrastructure Optimization
```yaml
Development Environment:
  - Use minimal resource allocation
  - Shut down non-essential services
  - Use local storage instead of cloud

Production Environment:
  - Use spot instances for non-critical workloads
  - Implement auto-scaling based on demand
  - Optimize resource requests and limits
```

#### LLM Cost Optimization
```yaml
Strategies:
  - Use cheaper models for simple tasks
  - Implement response caching
  - Optimize prompt length
  - Batch requests when possible

Implementation:
  - GPT-3.5-turbo for basic diary notes
  - GPT-4 only for complex analysis
  - Cache common responses in Redis
  - Compress prompts while maintaining quality
```

---

## 🔄 Backup & Recovery

### Backup Procedures

#### Database Backup
```bash
# Create PostgreSQL backup
docker-compose exec postgres pg_dump -U user transcription_db > backup.sql

# Schedule daily backups
0 2 * * * docker-compose exec postgres pg_dump -U user transcription_db | \
          gzip > /backups/transcription_db_$(date +\%Y\%m\%d).sql.gz
```

#### Application Data Backup
```bash
# Backup storage volumes
docker run --rm -v shared_storage:/data -v $(pwd):/backup \
  alpine tar czf /backup/storage_backup_$(date +%Y%m%d).tar.gz /data

# Backup Redis data
docker-compose exec redis redis-cli BGSAVE
docker cp transcription-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

#### Configuration Backup
```bash
# Backup configuration files
tar czf config_backup_$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  .env \
  infrastructure/ \
  shared/config/
```

### Recovery Procedures

#### Database Recovery
```bash
# Stop services
docker-compose stop

# Restore database
docker-compose exec postgres psql -U user -d transcription_db < backup.sql

# Restart services
docker-compose start
```

#### Application Recovery
```bash
# Restore storage data
docker run --rm -v shared_storage:/data -v $(pwd):/backup \
  alpine tar xzf /backup/storage_backup_20241124.tar.gz -C /

# Restore Redis data
docker-compose stop redis
docker cp redis_backup_20241124.rdb transcription-redis:/data/dump.rdb
docker-compose start redis
```

### Disaster Recovery

#### Recovery Time Objectives (RTO)
```yaml
Service Restoration:
  - Critical services: 15 minutes
  - Full functionality: 1 hour
  - Historical data: 4 hours

Data Recovery:
  - Recent jobs (24h): 15 minutes
  - Full database: 1 hour
  - File storage: 2 hours
```

#### Recovery Point Objectives (RPO)
```yaml
Data Loss Tolerance:
  - Active jobs: 0 minutes (real-time replication)
  - Job metadata: 15 minutes (continuous backup)
  - File storage: 1 hour (hourly snapshots)
```

---

## 📞 Emergency Contacts & Escalation

### On-Call Procedures

#### Severity Levels
```yaml
P1 - Critical (0-15 minutes):
  - Complete service outage
  - Data corruption
  - Security incidents

P2 - High (15-60 minutes):
  - Partial service degradation
  - High error rates
  - Performance issues

P3 - Medium (1-4 hours):
  - Minor functionality issues
  - Non-critical service failures

P4 - Low (Next business day):
  - Cosmetic issues
  - Enhancement requests
```

#### Escalation Matrix
```yaml
Level 1: On-call Engineer
  - Initial response and troubleshooting
  - Service restoration attempts
  - Escalation decision

Level 2: Senior Engineer / Team Lead
  - Complex technical issues
  - Architecture decisions
  - Resource allocation

Level 3: Engineering Manager
  - Business impact decisions
  - External communication
  - Resource authorization
```

### Communication Channels
```yaml
Alerting:
  - PagerDuty for critical alerts
  - Slack #ops-alerts for warnings
  - Email for daily summaries

Status Updates:
  - Slack #general for user communication
  - Status page for external users
  - Post-incident reports via email

Documentation:
  - Confluence for runbooks
  - GitHub for code changes
  - Jira for incident tracking
```

---

This operational runbook provides comprehensive procedures for deploying, monitoring, troubleshooting, and maintaining the MLOps audio transcription system. Regular updates should be made based on operational experience and system changes.
