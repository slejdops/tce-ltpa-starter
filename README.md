# Netcool DASH LTPA Auth & Diagnostic Tool

End-to-end Flask application that authenticates via IBM Netcool DASH's LTPA token and provides comprehensive diagnostic tools for troubleshooting LTPA tokens, user sessions, and GUI performance issues with the Tivoli Netcool DASH, JazzSM, and WebGUI stack.

## Quickstart (local)
```bash
python3 -m pip install -r requirements.txt
export FLASK_SECRET_KEY="change-me"
export DASH_HOST_IP="10.0.0.5"
export DASH_HOST_PORT="443"
export DASH_INTEGRATION_SERVICE="ltpa-integration/validate"
export LTPA_TOKEN_NAME="LtpaToken2"
export VERIFY_TLS="true"
export TIMEOUT_SECONDS="5"
python run.py
# Open http://localhost:5000/whoami (requires valid LTPA), /dashboard for RBAC example
```

## Docker
```bash
docker build -t tce-ltpa:latest .
docker run -p 5000:5000 --rm   -e FLASK_SECRET_KEY=change-me   -e DASH_HOST_IP=10.0.0.5   -e DASH_HOST_PORT=443   -e DASH_INTEGRATION_SERVICE='ltpa-integration/validate'   -e LTPA_TOKEN_NAME='LtpaToken2'   tce-ltpa:latest
```

## Tests
```bash
python3 -m pip install -r requirements-dev.txt
pytest -q
```

## Docker Compose
```bash
cp .env.example .env
docker compose up --build
```

## Helm (from source tree)
See `charts/tce-ltpa/values.yaml` for options.
```bash
helm upgrade --install tce charts/tce-ltpa   --set image.repository=ghcr.io/your-org/tce-ltpa   --set image.tag=1.0.0   --set ingress.enabled=true   --set ingress.className=nginx   --set ingress.hosts[0].host=app.example.com   --set flaskSecret.value="$(openssl rand -hex 32)"
```

## CI / Release
- CI runs on push/PR: tests + Docker build (`.github/workflows/ci.yml`).
- Release on tag (e.g., `v1.2.3`): pushes Docker to GHCR, packages/pushes Helm chart to GHCR OCI, uploads chart to GitHub Release (`.github/workflows/release.yml`).

---

Security notes:
- Keep TLS verification enabled in production. If DASH uses a private CA, set `CA_BUNDLE_PATH` or mount a Secret and set `REQUESTS_CA_BUNDLE`.
- Ensure this app and DASH share an SSO boundary/domain as required by your LTPA setup.

---

## Diagnostic Tool

This application includes a comprehensive diagnostic tool to help troubleshoot issues with LTPA tokens, user sessions, and GUI performance.

### Features

The diagnostic tool provides:

1. **LTPA Token Diagnostics**
   - Validate LTPA token format and structure
   - Test token validation against DASH
   - Check cookie configuration
   - Verify SSL/TLS settings
   - Test connectivity to DASH server

2. **Session Diagnostics**
   - Check Flask session configuration
   - Validate session cookie security settings
   - Test session persistence across requests
   - Analyze session timeout behavior
   - Verify SSO cookie domain configuration

3. **Performance Diagnostics**
   - Measure LTPA validation endpoint response times
   - Check network latency to DASH server
   - Test DNS resolution performance
   - Benchmark specific endpoints
   - Analyze SSL/TLS handshake overhead

4. **System Data Collection**
   - Gather environment and configuration information
   - Find and analyze log files
   - Search logs for error patterns
   - Check network connectivity
   - Collect system information

### CLI Usage

The diagnostic tool can be run from the command line:

```bash
# Make the script executable
chmod +x diagnose.py

# Quick health check
./diagnose.py health

# Run all diagnostic checks
./diagnose.py check-all

# Run all checks with log analysis
./diagnose.py check-all --include-logs

# Run specific diagnostic categories
./diagnose.py check-ltpa
./diagnose.py check-session
./diagnose.py check-performance

# Validate a specific LTPA token
./diagnose.py validate-token "your-ltpa-token-here"

# Test session persistence
./diagnose.py test-session https://your-dash-server/api/endpoint your-ltpa-token

# Benchmark an endpoint
./diagnose.py benchmark https://your-dash-server/api/endpoint -n 20

# Search logs for errors
./diagnose.py search-logs --dirs /var/log/netcool,/opt/IBM/logs

# Search logs excluding certain directories
./diagnose.py search-logs --dirs /var/log --exclude-dirs /var/log/archive,/var/log/old

# Generate comprehensive report
./diagnose.py report --include-logs -o diagnostic_report.json --format json
```

### API Endpoints

The diagnostic tool is also available via REST API endpoints:

```bash
# Health check (fast)
curl http://localhost:5000/diagnostics/health

# Run all diagnostic checks
curl http://localhost:5000/diagnostics/check-all

# Run specific diagnostic categories
curl http://localhost:5000/diagnostics/check-ltpa
curl http://localhost:5000/diagnostics/check-session
curl http://localhost:5000/diagnostics/check-performance

# Validate LTPA token
curl -X POST http://localhost:5000/diagnostics/validate-token \
  -H "Content-Type: application/json" \
  -d '{"token": "your-ltpa-token"}'

# Test session persistence
curl -X POST http://localhost:5000/diagnostics/test-session \
  -H "Content-Type: application/json" \
  -d '{"url": "https://dash-server/api/test", "token": "ltpa-token", "num_requests": 5}'

# Benchmark endpoint
curl -X POST http://localhost:5000/diagnostics/benchmark \
  -H "Content-Type: application/json" \
  -d '{"url": "https://dash-server/api/test", "num_requests": 10}'

# Search logs for errors
curl http://localhost:5000/diagnostics/search-logs?max_matches=50

# Search logs with directory exclusion
curl "http://localhost:5000/diagnostics/search-logs?dirs=/var/log/netcool&exclude_dirs=/var/log/netcool/archive&max_matches=50"

# Generate comprehensive report
curl http://localhost:5000/diagnostics/report?include_logs=true
```

### Troubleshooting Common Issues

#### LTPA Token Issues

If you're experiencing LTPA token problems:

1. Run `./diagnose.py check-ltpa` to check configuration
2. Verify DASH connectivity and SSL/TLS settings
3. Validate your token with `./diagnose.py validate-token <token>`
4. Check cookie name matches your WebSphere/DASH configuration

**Common Problems:**
- **Invalid token format**: Token may be corrupted or incorrectly copied
- **Token rejected by DASH**: Token may be expired or from wrong domain
- **SSL handshake failure**: Check certificate trust chain or disable TLS verification for testing
- **Connection timeout**: Check network connectivity and firewall rules

#### Session Issues

If you're having session-related problems:

1. Run `./diagnose.py check-session` to check session configuration
2. Verify FLASK_SECRET_KEY is set and not a default value
3. Check that cookies are being set with proper domain/path
4. Test session persistence with `./diagnose.py test-session`

**Common Problems:**
- **Sessions not persisting**: Check cookie domain configuration
- **Session expired immediately**: Verify SSO cookie domain matches
- **Lost session after redirect**: Check cookie path and secure flags

#### Performance Issues

If the GUI is slow:

1. Run `./diagnose.py check-performance` to measure response times
2. Check network latency with the performance diagnostics
3. Benchmark specific endpoints to identify bottlenecks
4. Analyze SSL/TLS handshake overhead

**Common Problems:**
- **Slow LTPA validation**: Check DASH server load and network latency
- **High network latency**: Review network routing and DNS configuration
- **SSL overhead**: Consider using connection pooling or session resumption

### Output Formats

The diagnostic tool supports multiple output formats:

**Text format (default)**: Human-readable output with color-coded status indicators
```bash
./diagnose.py check-all
```

**JSON format**: Machine-readable output for integration with other tools
```bash
./diagnose.py check-all --format json -o report.json
```

### Diagnostic Result Levels

Results are categorized by severity:

- ✓ **SUCCESS**: Check passed, no issues found
- ℹ **INFO**: Informational message, no action required
- ⚠ **WARNING**: Potential issue, review recommended
- ✗ **ERROR**: Issue found, action recommended
- ⚠⚠ **CRITICAL**: Critical issue, immediate action required

### Integration with Monitoring

The health check endpoint can be integrated with monitoring systems:

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /diagnostics/health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10

# Prometheus metrics endpoint (custom implementation)
# Monitor the /diagnostics/check-all endpoint periodically
```

### Log Analysis

The diagnostic tool can search common Netcool log locations:

- `/opt/IBM/tivoli/netcool/omnibus/log`
- `/opt/IBM/JazzSM/profile/logs`
- `/opt/IBM/WebSphere/AppServer/profiles/*/logs`
- `/var/log/netcool`
- `/var/log/dash`

It searches for common error patterns:
- ERROR, SEVERE, FATAL log levels
- Exception stack traces
- Authentication failures
- LTPA token errors
- Session expiration messages

### Environment Variables for Diagnostics

The diagnostic tool uses the same environment variables as the main application:

- `DASH_HOST_IP`: DASH server hostname/IP (required)
- `DASH_HOST_PORT`: DASH server port (default: 443)
- `DASH_INTEGRATION_SERVICE`: LTPA validation service path
- `LTPA_TOKEN_NAME`: Cookie name for LTPA token (default: LtpaToken2)
- `VERIFY_TLS`: Enable TLS certificate verification (true/false)
- `TIMEOUT_SECONDS`: Request timeout in seconds (default: 5)
- `FLASK_SECRET_KEY`: Flask session secret (required)
