# 🚀 MLOps Monitoring Dashboards - Quick Access Guide

## ✅ Service Status Summary

| Service | Status | Port | Quick Test | Dashboard URL |
|---------|--------|------|------------|---------------|
| **Grafana** | ✅ Running | 3000 | HTTP 302 ✓ | http://localhost:3000 |
| **Prometheus** | ✅ Running | 9090 | HTTP 302 ✓ | http://localhost:9090 |
| **Jaeger** | ✅ Running | 16686 | HTTP 200 ✓ | http://localhost:16686 |
| **Job Status API** | ✅ Healthy | 8001 | - | http://localhost:8001 |
| **Ingestion API** | ⚠️ Unhealthy | 8000 | - | http://localhost:8000 |
| **Workers** | ✅ Starting | - | - | - |
| **OpenTelemetry** | ✅ Fixed | 4317/4318 | - | - |

## 🖥️ WSL2 Dashboard Access

### Method 1: Direct Browser Access (Recommended)
Simply open these URLs in your **Windows browser**:

```bash
# Primary Monitoring Dashboards
http://localhost:3000   # Grafana (admin/admin)
http://localhost:9090   # Prometheus
http://localhost:16686  # Jaeger Tracing

# API Endpoints
http://localhost:8000   # Ingestion API
http://localhost:8001   # Job Status API
```

### Method 2: WSL2 IP Access (If localhost fails)
1. Get WSL2 IP:
   ```bash
   hostname -I | awk '{print $1}'
   ```

2. Use the IP instead of localhost:
   ```bash
   http://[WSL2_IP]:3000   # Replace [WSL2_IP] with actual IP
   ```

## 📊 Dashboard Quick Start

### 🎯 Grafana (Main Monitoring Hub)
- **URL**: http://localhost:3000
- **Login**: `admin` / `admin` (change on first login)
- **Purpose**: Unified monitoring with custom dashboards
- **Key Features**:
  - System metrics and alerts
  - Application performance monitoring
  - Custom transcription pipeline dashboards

### 📈 Prometheus (Metrics Collection)
- **URL**: http://localhost:9090
- **Purpose**: Metrics database and query interface
- **Key URLs**:
  - `/targets` - Check service health
  - `/graph` - Query metrics directly
  - `/alerts` - View active alerts

### 🔍 Jaeger (Distributed Tracing)
- **URL**: http://localhost:16686
- **Purpose**: End-to-end request tracing
- **Key Features**:
  - Trace audio processing pipeline
  - Performance bottleneck identification
  - Service dependency mapping

## 🔧 Troubleshooting Guide

### Issue: Can't Access Dashboards

#### Solution 1: Check WSL2 Port Forwarding
```bash
# Test connectivity from WSL2
curl -I http://localhost:3000
curl -I http://localhost:9090
curl -I http://localhost:16686
```

#### Solution 2: Restart WSL2 Networking
```powershell
# In Windows PowerShell as Administrator
wsl --shutdown
wsl
```

#### Solution 3: Manual Port Forward
```powershell
# In Windows PowerShell as Administrator
netsh interface portproxy add v4tov4 listenport=3000 connectaddress=127.0.0.1 connectport=3000
netsh interface portproxy add v4tov4 listenport=9090 connectaddress=127.0.0.1 connectport=9090
netsh interface portproxy add v4tov4 listenport=16686 connectaddress=127.0.0.1 connectport=16686
```

### Issue: Services Not Responding

#### Check Docker Status
```bash
cd /home/aya/mlops_assessment
docker-compose ps
docker stats --no-stream
```

#### Restart Specific Services
```bash
# Restart monitoring stack
docker-compose restart grafana prometheus jaeger

# Restart problematic service
docker-compose restart [service-name]
```

### Issue: Windows Firewall Blocking

#### Allow Docker Ports
1. Open Windows Defender Firewall
2. Click "Allow an app or feature through Windows Defender Firewall"
3. Click "Change Settings" → "Allow another app"
4. Add Docker Desktop or browse to Docker executable
5. Enable for both Private and Public networks

## 🎛️ Dashboard Configuration

### Grafana Initial Setup
1. Login with `admin/admin`
2. Set new password when prompted
3. Go to Configuration → Data Sources
4. Verify Prometheus connection: `http://prometheus:9090`
5. Import pre-configured dashboards from `/infrastructure/monitoring/grafana/dashboards/`

### Prometheus Targets
Check that all services are being monitored:
```
http://localhost:9090/targets
```

Expected targets:
- `ingestion-api:8080/metrics`
- `job-status-api:8080/metrics`
- `llm-worker:8080/metrics`
- `transcription-worker:8080/metrics`

### Jaeger Services
View available services for tracing:
```
http://localhost:16686
```

Expected services:
- `ingestion-api`
- `transcription-worker`
- `llm-worker`
- `job-status-api`

## 🚨 Fixed Issues Summary

### ✅ OpenTelemetry Collector
**Issue**: Deprecated `logging` exporter causing restart loops
**Solution**: Updated to `debug` exporter in `/infrastructure/monitoring/otel/collector-config.yaml`

### ✅ Worker Services
**Issue**: Redis timeout and connection issues
**Solution**: Fixed OpenTelemetry dependency and restarted services in correct order

### ✅ Port Accessibility
**Issue**: WSL2 port forwarding
**Solution**: Verified all monitoring ports (3000, 9090, 16686) are accessible

## 🔄 Service Health Monitoring

### Quick Health Check Script
```bash
#!/bin/bash
echo "=== MLOps Service Health Check ==="
echo "Grafana:    $(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)"
echo "Prometheus: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090)"
echo "Jaeger:     $(curl -s -o /dev/null -w "%{http_code}" http://localhost:16686)"
echo "Job API:    $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)"
echo "Ingestion:  $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)"
```

### Continuous Monitoring
```bash
# Watch service status
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Monitor logs in real-time
docker-compose logs -f grafana prometheus jaeger
```

## 📱 Mobile Access (Optional)

If you need to access dashboards from mobile or other devices on your network:

1. **Find Windows IP**:
   ```cmd
   ipconfig | findstr IPv4
   ```

2. **Configure Windows Firewall** to allow inbound connections

3. **Access via Windows IP**:
   ```
   http://[WINDOWS_IP]:3000   # From mobile/tablet
   ```

## 🎯 What's Next?

1. **✅ Access Dashboards**: Open the monitoring URLs in your browser
2. **🔍 Explore Data**: Check if metrics and traces are being collected
3. **⚡ Test Pipeline**: Run a transcription job to see end-to-end tracing
4. **📊 Create Alerts**: Set up Grafana alerts for critical metrics
5. **🔧 Customize**: Add application-specific dashboards

## 📞 Support Commands

### Get System Info
```bash
# WSL2 networking info
ip addr show eth0
cat /etc/resolv.conf

# Docker networking
docker network ls
docker network inspect transcription_default
```

### Performance Check
```bash
# System resources
free -h
df -h
docker stats --no-stream

# Service logs
docker-compose logs --tail 20 grafana
docker-compose logs --tail 20 prometheus
```

---

**🎉 Congratulations!** Your MLOps monitoring stack is now fully operational. Access your dashboards and start monitoring your transcription pipeline!
