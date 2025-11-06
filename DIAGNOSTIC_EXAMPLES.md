# Diagnostic Tool - Usage Examples

This document provides real-world examples of using the Netcool DASH diagnostic tool to troubleshoot common issues.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Troubleshooting LTPA Token Issues](#troubleshooting-ltpa-token-issues)
3. [Diagnosing Session Problems](#diagnosing-session-problems)
4. [Performance Analysis](#performance-analysis)
5. [Log Analysis](#log-analysis)
6. [Automated Monitoring](#automated-monitoring)

---

## Quick Start

### Initial Health Check

Start with a quick health check to verify basic connectivity:

```bash
./diagnose.py health
```

Expected output if healthy:
```
================================================================================
HEALTH STATUS
================================================================================
Healthy: True
Timestamp: 2025-11-05T10:30:00.000000

Checks:
  ✓ dash_connectivity: True
  ✓ configuration: True
```

### Comprehensive Diagnostic

Run all diagnostic checks:

```bash
./diagnose.py check-all
```

Or with verbose output and log analysis:

```bash
./diagnose.py check-all --verbose --include-logs -o full_report.json --format json
```

---

## Troubleshooting LTPA Token Issues

### Scenario 1: "Authentication Failed" Errors

**Problem**: Users are seeing "Authentication Failed" or 401/403 errors.

**Diagnostic Steps**:

```bash
# Step 1: Check LTPA configuration
./diagnose.py check-ltpa

# Step 2: Validate a specific token (get from browser cookies)
./diagnose.py validate-token "AAECAwQFBgcICQoLDA0ODxAREhM..."

# Step 3: Check via API
curl -X POST http://localhost:5000/diagnostics/validate-token \
  -H "Content-Type: application/json" \
  -d '{"token": "AAECAwQFBgcICQoLDA0ODxAREhM..."}'
```

**Common Issues and Solutions**:

1. **Token Name Mismatch**
   ```
   ✗ LTPA Config - Token Name
     Using non-standard token name: LtpaToken
     → Recommendation: Ensure this matches your WebSphere/DASH configuration
   ```
   **Solution**: Update `LTPA_TOKEN_NAME` environment variable to match your server configuration (usually `LtpaToken2`)

2. **SSL Certificate Validation Failed**
   ```
   ✗ SSL/TLS - Handshake
     SSL handshake failed: certificate verify failed
     → Recommendation: Check SSL certificate validity, trust chain, or set CA_BUNDLE_PATH
   ```
   **Solution**:
   - For production: Set `CA_BUNDLE_PATH` to your CA certificate
   - For testing: Set `VERIFY_TLS=false` (NOT recommended for production)

3. **DASH Service Not Reachable**
   ```
   ✗ LTPA Service - Endpoint
     LTPA validation endpoint not found (404)
     → Recommendation: Verify DASH_INTEGRATION_SERVICE path is correct
   ```
   **Solution**: Check `DASH_INTEGRATION_SERVICE` setting (should be something like `ltpa-integration/validate`)

### Scenario 2: Token Format Issues

**Problem**: Tokens appear to be malformed or corrupted.

```bash
# Validate token format and structure
./diagnose.py validate-token "your-token" --verbose
```

Expected output for valid token:
```json
{
  "valid": true,
  "checks": [
    {
      "name": "Base64 Encoding",
      "passed": true,
      "message": "Token is valid base64 (256 bytes decoded)"
    },
    {
      "name": "DASH Validation",
      "passed": true,
      "message": "Token validated successfully by DASH"
    }
  ]
}
```

---

## Diagnosing Session Problems

### Scenario 3: Sessions Not Persisting

**Problem**: Users are logged out after each request or page refresh.

**Diagnostic Steps**:

```bash
# Check session configuration
./diagnose.py check-session

# Test session persistence with multiple requests
./diagnose.py test-session \
  https://your-dash-server:8443/ibm/console/api/platform/info \
  "your-ltpa-token" \
  -n 10
```

Expected output for stable session:
```
================================================================================
SESSION PERSISTENCE TEST
================================================================================
URL: https://your-dash-server:8443/ibm/console/api/platform/info
Total Requests: 10
Successful: 10
Failed: 0
Session Stable: True

Average Response Time: 245.50ms
Min: 189.20ms
Max: 312.45ms
```

**Common Issues and Solutions**:

1. **Weak or Missing Secret Key**
   ```
   ✗ Session - Secret Key
     FLASK_SECRET_KEY is using a default/weak value
     → Recommendation: Change FLASK_SECRET_KEY to a strong random value
   ```
   **Solution**:
   ```bash
   export FLASK_SECRET_KEY="$(openssl rand -hex 32)"
   ```

2. **Cookie Domain Issues**
   ```
   ℹ Session - SSO Domain
     For SSO to work, ensure LTPA cookies are set for the common domain
     → Recommendation: Verify that DASH and this app share the same cookie domain
   ```
   **Solution**: Ensure both DASH and your app are on the same domain (e.g., `.example.com`)

### Scenario 4: Session Timeout Analysis

**Problem**: Need to determine actual session timeout value.

```bash
# This will test at 0s, 60s, 300s, 600s intervals
# You can implement custom timeout testing via the API
curl -X POST http://localhost:5000/diagnostics/test-session \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://dash-server/api/test",
    "token": "your-token",
    "num_requests": 5
  }'
```

---

## Performance Analysis

### Scenario 5: Slow GUI Response Times

**Problem**: Users complain about slow loading times for DASH/JazzSM UI.

**Diagnostic Steps**:

```bash
# Step 1: Check overall performance
./diagnose.py check-performance

# Step 2: Benchmark specific endpoints
./diagnose.py benchmark \
  https://your-dash-server:8443/ibm/console/api/platform/info \
  -n 20 \
  -t "your-ltpa-token"

# Step 3: Generate detailed report
./diagnose.py report --include-logs -o performance_report.json --format json
```

**Sample Output**:
```
================================================================================
ENDPOINT BENCHMARK
================================================================================
URL: https://dash-server:8443/ibm/console/api/platform/info
Total Requests: 20
Successful: 20
Failed: 0

Response Time Statistics:
  Mean: 456.23ms
  Median: 432.10ms
  Min: 389.50ms
  Max: 612.34ms
  Std Dev: 58.76ms
  95th percentile: 578.90ms
  99th percentile: 605.12ms
```

**Common Issues and Solutions**:

1. **High Network Latency**
   ```
   ⚠ Performance - Network Latency
     Elevated network latency to DASH (387ms)
     → Recommendation: High latency may indicate network congestion or routing issues
   ```
   **Solution**:
   - Check network path between app and DASH server
   - Review firewall rules and routing
   - Consider moving app closer to DASH server

2. **Slow LTPA Validation**
   ```
   ⚠ Performance - LTPA Validation
     LTPA validation endpoint is very slow (1245ms)
     → Recommendation: Slow responses may indicate server load or SSL overhead
   ```
   **Solution**:
   - Check DASH server resource utilization
   - Review DASH logs for errors
   - Consider increasing DASH server resources

3. **DNS Resolution Issues**
   ```
   ⚠ Performance - DNS Resolution
     Slow DNS resolution (325ms)
     → Recommendation: Consider using IP address directly or checking DNS server
   ```
   **Solution**: Use IP address in `DASH_HOST_IP` instead of hostname

### Scenario 6: SSL/TLS Performance Analysis

**Problem**: Suspect SSL handshake is causing delays.

```python
# Use the Python API for advanced analysis
from tce_app.diagnostics import DiagnosticRunner

runner = DiagnosticRunner()
ssl_perf = runner.performance.analyze_ssl_performance()
print(f"TCP Time: {ssl_perf['tcp_time_ms']}ms")
print(f"SSL Time: {ssl_perf['ssl_time_ms']}ms")
print(f"Total Time: {ssl_perf['total_time_ms']}ms")
print(f"SSL Version: {ssl_perf['ssl_version']}")
```

---

## Log Analysis

### Scenario 7: Finding Error Patterns

**Problem**: Need to find recent errors in Netcool logs.

```bash
# Search all standard log locations
./diagnose.py search-logs --max-matches 100

# Search specific directories
./diagnose.py search-logs \
  --dirs /opt/IBM/tivoli/netcool/omnibus/log,/var/log/netcool \
  --max-matches 50

# Search with directory exclusion (skip archived or rotated logs)
./diagnose.py search-logs \
  --dirs /var/log/netcool \
  --exclude-dirs /var/log/netcool/archive,/var/log/netcool/backup \
  --max-matches 50

# Via API with specific patterns
curl "http://localhost:5000/diagnostics/search-logs?max_matches=25"

# Via API with exclusion
curl "http://localhost:5000/diagnostics/search-logs?dirs=/var/log/netcool&exclude_dirs=/var/log/netcool/archive&max_matches=50"
```

**Sample Output**:
```
================================================================================
LOG ERROR SEARCH
================================================================================
Found 15 error matches

File: /opt/IBM/tivoli/netcool/omnibus/log/ObjectServer.log:1234
  2025-11-05 10:15:32 ERROR [Auth] LTPA token validation failed for user 'admin'

File: /opt/IBM/JazzSM/profile/logs/server1/SystemOut.log:5678
  2025-11-05 10:16:45 SEVERE [WebContainer] Session timeout occurred for session ID xyz123

File: /var/log/netcool/dash.log:910
  2025-11-05 10:18:23 ERROR [SSL] Certificate validation failed: unable to get local issuer
```

### Scenario 8: Continuous Monitoring

**Problem**: Need to monitor for new errors continuously.

Create a monitoring script:

```bash
#!/bin/bash
# monitor_diagnostics.sh

while true; do
  echo "=== Diagnostic Check at $(date) ==="

  # Run health check
  ./diagnose.py health

  if [ $? -ne 0 ]; then
    echo "ALERT: Health check failed!"
    # Send alert notification
    ./diagnose.py report --include-logs -o "alert_$(date +%Y%m%d_%H%M%S).json" --format json
  fi

  # Wait 5 minutes
  sleep 300
done
```

---

## Automated Monitoring

### Scenario 9: Kubernetes Liveness/Readiness Probes

Configure your Kubernetes deployment:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: tce-ltpa-app
spec:
  containers:
  - name: app
    image: tce-ltpa:latest
    ports:
    - containerPort: 5000
    livenessProbe:
      httpGet:
        path: /diagnostics/health
        port: 5000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /diagnostics/health
        port: 5000
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
```

### Scenario 10: Prometheus/Grafana Integration

Create a custom exporter script:

```python
#!/usr/bin/env python3
# prometheus_exporter.py

import time
from prometheus_client import start_http_server, Gauge, Counter
from tce_app.diagnostics import DiagnosticRunner

# Define metrics
ltpa_check_status = Gauge('ltpa_check_status', 'LTPA diagnostic status (1=healthy, 0=unhealthy)')
session_check_status = Gauge('session_check_status', 'Session diagnostic status')
performance_check_status = Gauge('performance_check_status', 'Performance diagnostic status')
dash_response_time = Gauge('dash_response_time_ms', 'DASH response time in milliseconds')

runner = DiagnosticRunner()

def collect_metrics():
    """Collect diagnostic metrics"""
    # Get health status
    health = runner.get_health_status()
    ltpa_check_status.set(1 if health['checks'].get('dash_connectivity') else 0)

    # Run performance check
    perf_results = runner.run_performance_checks()
    # Extract response time from results
    for check in perf_results['checks']:
        if 'LTPA Validation' in check['name'] and 'details' in check:
            dash_response_time.set(check['details'].get('response_time_ms', 0))

if __name__ == '__main__':
    # Start metrics server on port 8000
    start_http_server(8000)

    while True:
        collect_metrics()
        time.sleep(60)  # Collect every minute
```

### Scenario 11: Scheduled Diagnostic Reports

Create a cron job for daily reports:

```bash
# crontab -e
# Run comprehensive diagnostic report daily at 2 AM
0 2 * * * cd /app && ./diagnose.py report --include-logs -o "/reports/daily_$(date +\%Y\%m\%d).json" --format json
```

---

## Advanced Usage

### Custom Diagnostic Script

Create a custom script that combines multiple checks:

```python
#!/usr/bin/env python3
# custom_diagnostic.py

from tce_app.diagnostics import DiagnosticRunner
import json
import sys

def main():
    runner = DiagnosticRunner()

    # Run all checks
    print("Running comprehensive diagnostics...")
    results = runner.run_all_checks()

    # Check overall status
    if results['overall_status'] in ['critical', 'error']:
        print(f"ALERT: System status is {results['overall_status']}")

        # Search logs for recent errors
        errors = runner.search_logs(max_matches=20)

        # Save detailed report
        report = {
            'diagnostics': results,
            'recent_errors': errors
        }

        with open('urgent_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print("Detailed report saved to urgent_report.json")
        sys.exit(1)

    print(f"System status: {results['overall_status']}")
    sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## Tips and Best Practices

1. **Regular Health Checks**: Run `./diagnose.py health` regularly (every 5-10 minutes) for quick status updates

2. **Performance Baselines**: Establish baseline performance metrics in your environment:
   ```bash
   ./diagnose.py benchmark https://your-dash-server/api/endpoint -n 100 -o baseline.json --format json
   ```

3. **Log Rotation**: When using `--include-logs`, be aware of large log files. Use `--max-log-matches` to limit output

4. **Token Security**: Never log full LTPA tokens in production. The diagnostic tool automatically truncates sensitive data in logs

5. **Network Isolation**: If running diagnostics from outside the DASH network, results may differ from production behavior

6. **Scheduled Reports**: Set up automated diagnostic reports to track trends over time

7. **Alert Thresholds**: Define alert thresholds based on your environment:
   - Response time > 500ms: Warning
   - Response time > 1000ms: Alert
   - Failed health check: Critical alert

---

## Getting Help

If diagnostics reveal issues you can't resolve:

1. Save a comprehensive report:
   ```bash
   ./diagnose.py report --include-logs -o support_report.json --format json
   ```

2. Include the following information when seeking help:
   - Diagnostic report (support_report.json)
   - DASH/JazzSM version
   - WebSphere version
   - Network topology (app to DASH connectivity)
   - Recent changes to configuration

3. Check IBM Netcool documentation for LTPA configuration requirements

4. Review WebSphere LTPA token generation and validation logs
