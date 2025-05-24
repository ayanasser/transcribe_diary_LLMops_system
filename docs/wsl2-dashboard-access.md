# WSL2 Dashboard Access Guide

## Overview
This guide explains how to access your MLOps monitoring dashboards from Windows when running Docker in WSL2.

## Current Service Status
Based on the latest check, here are your running services:

| Service | Status | Port | URL |
|---------|--------|------|-----|
| Grafana | ✅ Running | 3000 | http://localhost:3000 |
| Prometheus | ✅ Running | 9090 | http://localhost:9090 |
| Jaeger | ✅ Running | 16686 | http://localhost:16686 |
| Job Status API | ✅ Running | 8001 | http://localhost:8001 |
| Ingestion API | ⚠️ Unhealthy | 8000 | http://localhost:8000 |
| PostgreSQL | ✅ Running | 5432 | localhost:5432 |
| Redis | ✅ Running | 6379 | localhost:6379 |

## Accessing Dashboards from Windows

### Method 1: Direct Access (Recommended)
WSL2 automatically forwards ports to Windows, so you can access dashboards directly:

1. **Grafana Dashboard**: Open your Windows browser and go to:
   ```
   http://localhost:3000
   ```
   - **Username**: `admin`
   - **Password**: `admin` (you'll be prompted to change this)

2. **Prometheus Metrics**: 
   ```
   http://localhost:9090
   ```

3. **Jaeger Tracing**:
   ```
   http://localhost:16686
   ```

### Method 2: Using WSL2 IP Address
If direct localhost access doesn't work:

1. Get your WSL2 IP address:
   ```bash
   hostname -I | awk '{print $1}'
   ```

2. Use the IP address instead of localhost:
   ```
   http://[WSL2_IP]:3000  # Grafana
   http://[WSL2_IP]:9090  # Prometheus
   http://[WSL2_IP]:16686 # Jaeger
   ```

### Method 3: Port Forwarding (If needed)
If you have network issues, you can explicitly forward ports:

```powershell
# Run in Windows PowerShell as Administrator
netsh interface portproxy add v4tov4 listenport=3000 connectaddress=[WSL2_IP] connectport=3000
netsh interface portproxy add v4tov4 listenport=9090 connectaddress=[WSL2_IP] connectport=9090
netsh interface portproxy add v4tov4 listenport=16686 connectaddress=[WSL2_IP] connectport=16686
```

## Dashboard Configurations

### Grafana Setup
1. **First Login**: Use `admin/admin`, then set a new password
2. **Data Sources**: 
   - Prometheus: `http://prometheus:9090`
   - Jaeger: `http://jaeger:16686`
3. **Import Dashboards**: Use the pre-configured dashboards in the `monitoring/` directory

### Prometheus Targets
Access the targets page to verify all services are being monitored:
```
http://localhost:9090/targets
```

### Jaeger Services
View distributed traces for your transcription pipeline:
```
http://localhost:16686
```

## Service Health Issues

### Current Issues Detected
1. **Workers Restarting**: Both LLM and Transcription workers are in restart loops
2. **OpenTelemetry Collector**: Also restarting
3. **Ingestion API**: Running but unhealthy

### Troubleshooting Steps

#### 1. Check Worker Logs
```bash
# Check why workers are restarting
docker logs transcription-llm-worker --tail 50
docker logs transcription-transcription-worker --tail 50
docker logs transcription-otel-collector --tail 50
```

#### 2. Verify Dependencies
Workers might be failing due to:
- Database connection issues
- Redis connection problems
- Missing environment variables
- OpenTelemetry configuration issues

#### 3. Restart in Order
Try restarting services in dependency order:
```bash
# Stop problematic services
docker-compose stop llm-worker transcription-worker otel-collector

# Restart infrastructure first
docker-compose restart redis postgres

# Then restart workers
docker-compose up -d llm-worker transcription-worker otel-collector
```

## Testing Dashboard Access

### Quick Health Check Commands
```bash
# Test Grafana
curl -f http://localhost:3000/api/health

# Test Prometheus
curl -f http://localhost:9090/-/healthy

# Test Jaeger
curl -f http://localhost:16686/api/services
```

### Browser Tests
1. Open each dashboard URL in your Windows browser
2. Verify you can see the login pages/interfaces
3. Check that data is being collected (may take a few minutes)

## Common WSL2 Networking Issues

### Issue 1: Localhost Not Working
**Solution**: Use WSL2 IP address or restart WSL2:
```powershell
# In Windows PowerShell
wsl --shutdown
wsl
```

### Issue 2: Firewall Blocking
**Solution**: Allow Docker ports through Windows Firewall:
- Go to Windows Defender Firewall
- Allow apps through firewall
- Add Docker Desktop or the specific ports

### Issue 3: Port Conflicts
**Solution**: Check if ports are already in use:
```powershell
# In Windows PowerShell
netstat -an | findstr ":3000"
netstat -an | findstr ":9090"
netstat -an | findstr ":16686"
```

## Performance Considerations

### Resource Usage
Monitor system resources while accessing dashboards:
```bash
# Check Docker stats
docker stats --no-stream

# Check WSL2 memory usage
cat /proc/meminfo | grep MemAvailable
```

### Optimization Tips
1. **Close unused browser tabs** when accessing multiple dashboards
2. **Limit dashboard refresh rates** to reduce load
3. **Use specific time ranges** instead of "Last 24h" for better performance

## Security Notes

### Network Security
- Dashboards are accessible from Windows host only
- No external network access by default
- Change default passwords immediately
- Consider setting up authentication for production use

### Data Security
- Monitoring data includes application metrics and traces
- Ensure compliance with data retention policies
- Regularly backup Grafana configurations

## Next Steps

1. **Fix Worker Issues**: Address the restarting workers first
2. **Configure Alerts**: Set up Grafana alerts for critical metrics
3. **Custom Dashboards**: Create application-specific monitoring dashboards
4. **Performance Tuning**: Optimize based on monitoring data

## Support Commands

### Get WSL2 Information
```bash
# WSL2 version and status
wsl --status
wsl --list --verbose

# Network configuration
ip addr show eth0
```

### Docker Network Inspection
```bash
# Check Docker networks
docker network ls
docker network inspect transcription_default
```

### Port Verification
```bash
# Check what's listening on ports
ss -tlnp | grep -E ':(3000|9090|16686)'
```
