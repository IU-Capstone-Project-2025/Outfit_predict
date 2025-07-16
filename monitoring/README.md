# OutfitPredict Monitoring System

This directory contains the monitoring setup for the OutfitPredict application, providing comprehensive log viewing, metrics monitoring, and system observability.

## 🔧 Monitoring Stack

### Services Overview

| Service | Port | Purpose | Direct Access | Nginx Proxy |
|---------|------|---------|---------------|-------------|
| **Dozzle** | 9999 | Real-time Docker log viewer | http://localhost:9999 | https://your-domain.com/logs/ |
| **Grafana** | 3001 | Metrics dashboards and visualization | http://localhost:3001 | https://your-domain.com/grafana/ |
| **Prometheus** | 9090 | Metrics collection and storage | http://localhost:9090 | https://your-domain.com/prometheus/ |
| **Node Exporter** | 9100 | System metrics collection | http://localhost:9100/metrics | https://your-domain.com/metrics |

### 🚀 Quick Start

1. **Deploy monitoring stack:**
   ```bash
   docker compose up -d
   ```

2. **Access monitoring interfaces:**
   
   **Direct Access (Development):**
   - **Dozzle (Logs)**: http://localhost:9999 - Real-time container logs
   - **Grafana (Dashboards)**: http://localhost:3001 - Metrics and visualizations
     - Username: `admin`
     - Password: `admin123` (or from GRAFANA_PASSWORD env var)
   - **Prometheus**: http://localhost:9090 - Raw metrics and targets
   
   **Production Access (via Nginx proxy):**
   - **Dozzle (Logs)**: https://your-domain.com/logs/
   - **Grafana (Dashboards)**: https://your-domain.com/grafana/
   - **Prometheus**: https://your-domain.com/prometheus/
   - **System Metrics**: https://your-domain.com/metrics
   - **Health Check**: https://your-domain.com/health

3. **Use the log viewer script:**
   ```bash
   ./monitoring/logs-viewer.sh help
   ./monitoring/logs-viewer.sh backend -n 50
   ./monitoring/logs-viewer.sh follow
   ```

## 📊 Monitoring Features

### 1. Real-time Log Viewing (Dozzle)
- **Web-based interface** for viewing Docker container logs
- **Real-time streaming** of log output
- **Search and filter** capabilities
- **Multi-container view** with easy switching
- **No configuration required** - automatically discovers containers

### 2. Metrics and Dashboards (Grafana + Prometheus)
- **System metrics**: CPU, memory, disk, network usage
- **Application metrics**: API response times, request counts, error rates
- **Infrastructure metrics**: Database connections, storage usage
- **Custom dashboards** for different aspects of the application
- **Alerting capabilities** (can be configured)

### 3. Log Management (Custom Scripts)
- **Centralized log viewing** with `logs-viewer.sh`
- **Log rotation** to prevent disk space issues
- **Error filtering** to quickly find issues
- **Container status** and resource usage monitoring

## 🛠️ Log Viewer Script Usage

The `logs-viewer.sh` script provides easy command-line access to container logs:

```bash
# Show help
./monitoring/logs-viewer.sh help

# View backend logs
./monitoring/logs-viewer.sh backend

# Follow all logs in real-time
./monitoring/logs-viewer.sh follow

# Show only errors
./monitoring/logs-viewer.sh errors

# Show container status and resource usage
./monitoring/logs-viewer.sh status

# Clean old log files
./monitoring/logs-viewer.sh clean

# Rotate large log files
./monitoring/logs-viewer.sh rotate
```

## 📁 Configuration Files

```
monitoring/
├── README.md                          # This documentation
├── prometheus.yml                     # Prometheus configuration
├── logs-viewer.sh                     # Log management script
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── prometheus.yml         # Grafana-Prometheus connection
        └── dashboards/
            └── dashboard.yml          # Dashboard configuration
```

## 🔍 Monitoring Targets

### Current Monitoring Coverage:
- ✅ **System Metrics**: CPU, memory, disk, network (Node Exporter)
- ✅ **Container Logs**: All application containers (Dozzle)
- ✅ **Container Stats**: Resource usage, health status
- ✅ **MinIO Metrics**: Storage service metrics
- ⚠️ **Application Metrics**: Requires adding `/metrics` endpoint to backend
- ⚠️ **Database Metrics**: Requires adding PostgreSQL exporter

### Adding Application Metrics (Optional)

To enable application-level metrics in your backend:

1. **Add Prometheus metrics to your FastAPI app:**
   ```python
   from prometheus_client import Counter, Histogram, generate_latest
   
   REQUEST_COUNT = Counter('app_requests_total', 'Total app requests', ['method', 'endpoint'])
   REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
   
   @app.get("/metrics")
   async def metrics():
       return Response(generate_latest(), media_type="text/plain")
   ```

2. **The Prometheus configuration is already set up** to scrape `/metrics` from the backend.

## 🚨 Alerts and Notifications

### Setting Up Alerts (Optional)

1. **In Grafana**, create alert rules for:
   - High CPU/Memory usage
   - Application errors
   - Container downtime
   - Disk space low

2. **Configure notification channels**:
   - Email notifications
   - Slack/Discord webhooks
   - PagerDuty integration

## 🧹 Maintenance

### Log Rotation
```bash
# Automatic log rotation (run weekly via cron)
./monitoring/logs-viewer.sh rotate

# Clean old logs (run daily via cron)
./monitoring/logs-viewer.sh clean
```

### Performance Tuning
- **Prometheus retention**: Currently set to 200h, adjust in `prometheus.yml`
- **Log tail size**: Dozzle shows last 300 lines by default
- **Scrape intervals**: Adjust based on your monitoring needs

## 🔧 Troubleshooting

### Common Issues:

1. **Dozzle not showing logs**:
   - Check Docker socket permissions: `ls -la /var/run/docker.sock`
   - Ensure Dozzle container has access to Docker socket

2. **Grafana can't connect to Prometheus**:
   - Verify both containers are on the same network
   - Check Prometheus is accessible: `curl http://prometheus:9090`

3. **High disk usage**:
   - Run log cleanup: `./monitoring/logs-viewer.sh clean`
   - Implement regular log rotation

4. **Container resource issues**:
   - Check resource usage: `./monitoring/logs-viewer.sh status`
   - Adjust container resource limits in `docker-compose.yml`

## 📈 Next Steps

1. **Customize Grafana dashboards** for your specific metrics
2. **Set up alerting rules** for critical system events
3. **Add application-specific metrics** to the backend
4. **Configure log aggregation** for better search capabilities
5. **Set up automated backup** of Grafana dashboards and Prometheus data 