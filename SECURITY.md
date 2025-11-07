# Security Guidelines

## Overview

This document outlines security considerations and best practices for deploying and operating the TCE LTPA Starter application.

## Authentication & Authorization

### Diagnostic Endpoints

All diagnostic endpoints (except `/diagnostics/health`) require authentication and admin privileges:

- **Required Roles**: `TCE_ADMIN` or `NETCOOL_ADMIN`
- **Protected Endpoints**:
  - `/diagnostics/check-all`
  - `/diagnostics/check-ltpa`
  - `/diagnostics/check-session`
  - `/diagnostics/check-performance`
  - `/diagnostics/validate-token`
  - `/diagnostics/test-session`
  - `/diagnostics/benchmark`
  - `/diagnostics/search-logs`
  - `/diagnostics/report`

**Important**: The `/diagnostics/health` endpoint is intentionally unprotected for use by monitoring systems and load balancers.

### LTPA Token Validation

The application validates LTPA tokens using the following methods:

1. **Cookie**: `LtpaToken2` (or configured via `LTPA_TOKEN_NAME`)
2. **Custom Headers**: `X-Ltpa-Token`, `X-Lpta-Token`, `X-LTPA-Token`

Tokens are validated against the configured DASH server endpoint.

## SSRF Protection

The application implements Server-Side Request Forgery (SSRF) protections for endpoints that accept URLs:

### Protected Endpoints

- `/diagnostics/test-session` (POST)
- `/diagnostics/benchmark` (POST)

### URL Validation Rules

1. **Allowed Schemes**: Only `http://` and `https://` are permitted
2. **Private IP Blocking**: Requests to private IP ranges are blocked:
   - `10.0.0.0/8`
   - `172.16.0.0/12`
   - `192.168.0.0/16`
   - `127.0.0.0/8` (localhost)
   - Link-local and reserved addresses
3. **DNS Resolution**: Hostnames are resolved and checked against private IP ranges
4. **Timeout Enforcement**: All external requests have strict timeout limits

### Log Directory Access Control

The `/diagnostics/search-logs` endpoint restricts directory access to a predefined allowlist:

- `/opt/IBM/tivoli/netcool/omnibus/log`
- `/opt/IBM/JazzSM/profile/logs`
- `/opt/IBM/WebSphere/AppServer/profiles/*/logs`
- `/var/log/netcool`
- `/var/log/dash`
- `logs/`
- `./logs`

Path traversal attempts are blocked by validating requested directories against this allowlist.

## Secret Management

### Flask SECRET_KEY

The `FLASK_SECRET_KEY` is critical for session security. The application enforces the following:

**Production Requirements** (when `FLASK_DEBUG=false`):
- Must not be empty
- Must not be a weak default value (`change-me`, `secret`, `dev`, `test`, `development`, `default`)
- Must be at least 32 characters long
- Application will fail to start if these requirements are not met

**Development Mode** (when `FLASK_DEBUG=true`):
- Weak keys trigger warnings but do not prevent startup
- This is acceptable for local development only

**Generating a Secure Key**:
```bash
openssl rand -hex 32
```

### Environment Variables

Store sensitive configuration in environment variables:

```bash
FLASK_SECRET_KEY=<generated-secure-key>
DASH_HOST_IP=<dash-server-ip>
DASH_HOST_PORT=8443
LTPA_TOKEN_NAME=LtpaToken2
VERIFY_TLS=true
CA_BUNDLE_PATH=/path/to/ca-bundle.crt  # Optional
```

### Kubernetes/Helm Deployment

When deploying to Kubernetes:

1. **Use Secrets for Sensitive Data**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tce-ltpa-secrets
type: Opaque
stringData:
  flask-secret-key: <generated-secure-key>
```

2. **Mount Secrets as Environment Variables**:
```yaml
env:
  - name: FLASK_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: tce-ltpa-secrets
        key: flask-secret-key
```

3. **Restrict RBAC**: Limit access to diagnostic endpoints using Kubernetes RBAC and network policies

## TLS/SSL Configuration

### Certificate Verification

**Production**: Always enable TLS verification:
```bash
VERIFY_TLS=true
```

**Development/Testing**: TLS verification can be disabled for self-signed certificates:
```bash
VERIFY_TLS=false
```

**Custom CA Bundle**: For custom certificate authorities:
```bash
CA_BUNDLE_PATH=/path/to/ca-bundle.crt
VERIFY_TLS=true
```

### HTTPS Enforcement

- Use HTTPS for all production deployments
- Configure reverse proxies (nginx, Apache) to enforce HTTPS
- Set secure cookie flags: `Secure`, `HttpOnly`, `SameSite=Strict`

## Network Security

### Firewall Rules

Recommended firewall configuration:

1. **Inbound**:
   - Allow port 5000 (or configured port) from trusted networks only
   - Allow HTTPS (443/8443) from DASH server for LTPA validation

2. **Outbound**:
   - Allow HTTPS to DASH server for LTPA validation
   - Restrict other outbound connections

### Network Segmentation

- Deploy in a private network segment
- Use network policies to restrict access to diagnostic endpoints
- Implement rate limiting at the reverse proxy/load balancer level

## Monitoring & Logging

### Health Checks

Use the unprotected `/diagnostics/health` endpoint for:
- Kubernetes liveness probes
- Load balancer health checks
- Monitoring systems

**Do NOT** use other diagnostic endpoints for automated health checks as they require authentication.

### Log Security

- Logs do not contain LTPA token values
- Sensitive configuration values are redacted (SECRET_KEY, passwords)
- Implement log rotation and retention policies
- Restrict access to log files

### Audit Logging

Consider implementing audit logging for:
- Authentication attempts (success/failure)
- Diagnostic endpoint access
- Configuration changes
- Failed authorization attempts

## Deployment Checklist

Before deploying to production:

- [ ] Generate and set a strong `FLASK_SECRET_KEY` (32+ characters)
- [ ] Enable TLS verification (`VERIFY_TLS=true`)
- [ ] Configure proper CA bundle if using custom certificates
- [ ] Verify DASH server connectivity and LTPA validation
- [ ] Test authentication and authorization for all endpoints
- [ ] Configure firewall rules and network policies
- [ ] Set up monitoring and alerting
- [ ] Implement log rotation and retention
- [ ] Review and restrict access to diagnostic endpoints
- [ ] Enable HTTPS with valid certificates
- [ ] Configure secure cookie flags at reverse proxy
- [ ] Test SSRF protections with various URL inputs
- [ ] Verify log directory access controls

## Incident Response

If a security issue is discovered:

1. **Immediate Actions**:
   - Rotate `FLASK_SECRET_KEY` immediately
   - Review access logs for suspicious activity
   - Disable diagnostic endpoints if compromised
   - Notify security team

2. **Investigation**:
   - Analyze logs for unauthorized access
   - Check for SSRF exploitation attempts
   - Review authentication failures
   - Assess data exposure

3. **Remediation**:
   - Apply security patches
   - Update configurations
   - Implement additional controls
   - Document lessons learned

## Reporting Security Issues

To report security vulnerabilities, please contact the repository maintainers directly. Do not open public issues for security concerns.

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [IBM Netcool Security Documentation](https://www.ibm.com/docs/en/netcool)
