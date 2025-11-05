# -*- coding: utf-8 -*-
"""LTPA Token Diagnostics - Check LTPA configuration and validation"""

import base64
import re
import ssl
import socket
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import requests
from requests.exceptions import SSLError, ConnectionError, Timeout

from .base import BaseDiagnostic, DiagnosticResult, DiagnosticLevel
from ..settings import SETTINGS


class LTPADiagnostics(BaseDiagnostic):
    """Diagnose LTPA token configuration and validation issues"""

    def run_checks(self) -> List[DiagnosticResult]:
        """Execute all LTPA diagnostic checks"""
        self.clear_results()

        self.check_ltpa_configuration()
        self.check_dash_connectivity()
        self.check_ssl_configuration()
        self.check_ltpa_service_endpoint()
        self.check_cookie_configuration()

        return self.results

    def check_ltpa_configuration(self):
        """Validate LTPA configuration settings"""
        config_issues = []

        # Check DASH host configuration
        if not SETTINGS.DASH_HOST_IP:
            self.add_result(
                "LTPA Config - DASH Host",
                DiagnosticLevel.CRITICAL,
                "DASH_HOST_IP is not configured",
                recommendation="Set DASH_HOST_IP environment variable to your DASH server IP/hostname"
            )
            config_issues.append("Missing DASH_HOST_IP")
        else:
            self.add_result(
                "LTPA Config - DASH Host",
                DiagnosticLevel.SUCCESS,
                f"DASH host configured: {SETTINGS.DASH_HOST_IP}",
                details={"host": SETTINGS.DASH_HOST_IP, "port": SETTINGS.DASH_HOST_PORT}
            )

        # Check LTPA token name
        if not SETTINGS.LTPA_TOKEN_NAME:
            self.add_result(
                "LTPA Config - Token Name",
                DiagnosticLevel.ERROR,
                "LTPA_TOKEN_NAME is not configured",
                recommendation="Set LTPA_TOKEN_NAME (usually 'LtpaToken2')"
            )
            config_issues.append("Missing LTPA_TOKEN_NAME")
        else:
            self.add_result(
                "LTPA Config - Token Name",
                DiagnosticLevel.SUCCESS,
                f"LTPA token name: {SETTINGS.LTPA_TOKEN_NAME}",
                details={"token_name": SETTINGS.LTPA_TOKEN_NAME}
            )

        # Check integration service path
        if not SETTINGS.DASH_INTEGRATION_SERVICE:
            self.add_result(
                "LTPA Config - Service Path",
                DiagnosticLevel.ERROR,
                "DASH_INTEGRATION_SERVICE is not configured",
                recommendation="Set DASH_INTEGRATION_SERVICE (e.g., 'ltpa-integration/validate')"
            )
            config_issues.append("Missing DASH_INTEGRATION_SERVICE")
        else:
            self.add_result(
                "LTPA Config - Service Path",
                DiagnosticLevel.SUCCESS,
                f"Integration service path: {SETTINGS.DASH_INTEGRATION_SERVICE}",
                details={"service_path": SETTINGS.DASH_INTEGRATION_SERVICE}
            )

        # Check timeout configuration
        if SETTINGS.TIMEOUT_SECONDS < 5:
            self.add_result(
                "LTPA Config - Timeout",
                DiagnosticLevel.WARNING,
                f"Timeout is very low: {SETTINGS.TIMEOUT_SECONDS}s",
                recommendation="Consider increasing TIMEOUT_SECONDS to at least 5-10 seconds"
            )
        else:
            self.add_result(
                "LTPA Config - Timeout",
                DiagnosticLevel.SUCCESS,
                f"Timeout configured: {SETTINGS.TIMEOUT_SECONDS}s"
            )

        return config_issues

    def check_dash_connectivity(self):
        """Test connectivity to DASH server"""
        host = SETTINGS.DASH_HOST_IP
        port = SETTINGS.DASH_HOST_PORT

        if not host:
            return

        # Test basic TCP connectivity
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SETTINGS.TIMEOUT_SECONDS)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                self.add_result(
                    "Connectivity - TCP",
                    DiagnosticLevel.SUCCESS,
                    f"TCP connection to {host}:{port} successful",
                    details={"host": host, "port": port}
                )
            else:
                self.add_result(
                    "Connectivity - TCP",
                    DiagnosticLevel.ERROR,
                    f"Cannot establish TCP connection to {host}:{port}",
                    details={"host": host, "port": port, "error_code": result},
                    recommendation="Check network connectivity, firewall rules, and verify DASH server is running"
                )
        except socket.gaierror as e:
            self.add_result(
                "Connectivity - DNS",
                DiagnosticLevel.ERROR,
                f"DNS resolution failed for {host}: {str(e)}",
                details={"host": host, "error": str(e)},
                recommendation="Check hostname spelling and DNS configuration"
            )
        except Exception as e:
            self.add_result(
                "Connectivity - TCP",
                DiagnosticLevel.ERROR,
                f"Connection test failed: {str(e)}",
                details={"error": str(e)},
                recommendation="Check network connectivity and firewall rules"
            )

    def check_ssl_configuration(self):
        """Check SSL/TLS configuration"""
        host = SETTINGS.DASH_HOST_IP
        port = SETTINGS.DASH_HOST_PORT

        if not host:
            return

        # Check if TLS verification is enabled
        if not SETTINGS.VERIFY_TLS or SETTINGS.requests_verify is False:
            self.add_result(
                "SSL/TLS - Verification",
                DiagnosticLevel.WARNING,
                "TLS certificate verification is DISABLED",
                details={"verify_tls": SETTINGS.VERIFY_TLS},
                recommendation="Enable TLS verification in production (VERIFY_TLS=true)"
            )
        else:
            self.add_result(
                "SSL/TLS - Verification",
                DiagnosticLevel.SUCCESS,
                "TLS certificate verification is enabled",
                details={"verify_tls": SETTINGS.VERIFY_TLS}
            )

        # Test SSL handshake
        try:
            context = ssl.create_default_context()
            if not SETTINGS.VERIFY_TLS:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((host, port), timeout=SETTINGS.TIMEOUT_SECONDS) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

                    self.add_result(
                        "SSL/TLS - Handshake",
                        DiagnosticLevel.SUCCESS,
                        f"SSL/TLS handshake successful ({version})",
                        details={
                            "protocol": version,
                            "cipher": cipher,
                            "has_certificate": cert is not None
                        }
                    )
        except ssl.SSLError as e:
            self.add_result(
                "SSL/TLS - Handshake",
                DiagnosticLevel.ERROR,
                f"SSL handshake failed: {str(e)}",
                details={"error": str(e)},
                recommendation="Check SSL certificate validity, trust chain, or set CA_BUNDLE_PATH"
            )
        except Exception as e:
            self.add_result(
                "SSL/TLS - Handshake",
                DiagnosticLevel.WARNING,
                f"Could not test SSL handshake: {str(e)}",
                details={"error": str(e)}
            )

    def check_ltpa_service_endpoint(self):
        """Test LTPA validation service endpoint"""
        url = SETTINGS.servlet_url

        if not url:
            return

        # Test endpoint without token (should fail but endpoint should exist)
        try:
            resp = requests.get(
                url,
                timeout=SETTINGS.TIMEOUT_SECONDS,
                verify=SETTINGS.requests_verify,
                allow_redirects=False
            )

            # We expect 401/403 for missing token, but 404/503 indicates config issues
            if resp.status_code in [401, 403]:
                self.add_result(
                    "LTPA Service - Endpoint",
                    DiagnosticLevel.SUCCESS,
                    f"LTPA validation endpoint is reachable (returned {resp.status_code} as expected)",
                    details={
                        "url": url,
                        "status_code": resp.status_code,
                        "response_time_ms": int(resp.elapsed.total_seconds() * 1000)
                    }
                )
            elif resp.status_code == 404:
                self.add_result(
                    "LTPA Service - Endpoint",
                    DiagnosticLevel.ERROR,
                    f"LTPA validation endpoint not found (404)",
                    details={"url": url, "status_code": 404},
                    recommendation="Verify DASH_INTEGRATION_SERVICE path is correct"
                )
            elif resp.status_code >= 500:
                self.add_result(
                    "LTPA Service - Endpoint",
                    DiagnosticLevel.ERROR,
                    f"LTPA validation service error ({resp.status_code})",
                    details={"url": url, "status_code": resp.status_code},
                    recommendation="Check DASH server health and logs"
                )
            else:
                self.add_result(
                    "LTPA Service - Endpoint",
                    DiagnosticLevel.WARNING,
                    f"Unexpected response from LTPA service: {resp.status_code}",
                    details={"url": url, "status_code": resp.status_code}
                )

        except SSLError as e:
            self.add_result(
                "LTPA Service - Endpoint",
                DiagnosticLevel.ERROR,
                f"SSL error accessing LTPA service: {str(e)}",
                details={"url": url, "error": str(e)},
                recommendation="Check SSL certificate configuration or set VERIFY_TLS=false for testing"
            )
        except ConnectionError as e:
            self.add_result(
                "LTPA Service - Endpoint",
                DiagnosticLevel.ERROR,
                f"Connection error accessing LTPA service: {str(e)}",
                details={"url": url, "error": str(e)},
                recommendation="Verify DASH server is running and accessible"
            )
        except Timeout as e:
            self.add_result(
                "LTPA Service - Endpoint",
                DiagnosticLevel.ERROR,
                f"Timeout accessing LTPA service: {str(e)}",
                details={"url": url, "timeout": SETTINGS.TIMEOUT_SECONDS},
                recommendation="Check network latency or increase TIMEOUT_SECONDS"
            )
        except Exception as e:
            self.add_result(
                "LTPA Service - Endpoint",
                DiagnosticLevel.ERROR,
                f"Error accessing LTPA service: {str(e)}",
                details={"url": url, "error": str(e)}
            )

    def check_cookie_configuration(self):
        """Check cookie configuration issues"""
        token_name = SETTINGS.LTPA_TOKEN_NAME

        if not token_name:
            return

        # Validate token name format
        if not re.match(r'^[a-zA-Z0-9_-]+$', token_name):
            self.add_result(
                "Cookie - Name Format",
                DiagnosticLevel.WARNING,
                f"Token name contains unusual characters: {token_name}",
                details={"token_name": token_name},
                recommendation="LTPA token names should typically be alphanumeric"
            )
        else:
            self.add_result(
                "Cookie - Name Format",
                DiagnosticLevel.SUCCESS,
                f"Token name format is valid: {token_name}"
            )

        # Check for common naming issues
        common_names = ['LtpaToken', 'LtpaToken2']
        if token_name not in common_names:
            self.add_result(
                "Cookie - Name Convention",
                DiagnosticLevel.INFO,
                f"Using non-standard token name: {token_name}",
                details={"token_name": token_name, "common_names": common_names},
                recommendation="Ensure this matches your WebSphere/DASH configuration"
            )

    def validate_ltpa_token(self, token: str) -> Dict[str, Any]:
        """Validate a specific LTPA token and return detailed results"""
        results = {
            "valid": False,
            "checks": [],
            "details": {}
        }

        # Check token format
        if not token or not isinstance(token, str):
            results["checks"].append({
                "name": "Token Format",
                "passed": False,
                "message": "Token is empty or invalid type"
            })
            return results

        results["details"]["length"] = len(token)

        # Check if token is base64 encoded (common for LTPA tokens)
        try:
            decoded = base64.b64decode(token)
            results["checks"].append({
                "name": "Base64 Encoding",
                "passed": True,
                "message": f"Token is valid base64 ({len(decoded)} bytes decoded)"
            })
            results["details"]["decoded_length"] = len(decoded)
        except Exception as e:
            results["checks"].append({
                "name": "Base64 Encoding",
                "passed": False,
                "message": f"Token is not valid base64: {str(e)}"
            })

        # Try to validate with DASH
        if SETTINGS.DASH_HOST_IP:
            try:
                url = SETTINGS.servlet_url
                headers = {
                    "Accept": "application/json",
                    "Cookie": f"{SETTINGS.LTPA_TOKEN_NAME}={token}",
                    "X-Lpta-Token": token,
                }
                resp = requests.get(
                    url,
                    headers=headers,
                    timeout=SETTINGS.TIMEOUT_SECONDS,
                    verify=SETTINGS.requests_verify,
                )

                if resp.status_code == 200:
                    results["valid"] = True
                    results["checks"].append({
                        "name": "DASH Validation",
                        "passed": True,
                        "message": "Token validated successfully by DASH"
                    })
                    try:
                        results["details"]["dash_response"] = resp.json()
                    except:
                        pass
                else:
                    results["checks"].append({
                        "name": "DASH Validation",
                        "passed": False,
                        "message": f"DASH rejected token (HTTP {resp.status_code})"
                    })
            except Exception as e:
                results["checks"].append({
                    "name": "DASH Validation",
                    "passed": False,
                    "message": f"Error validating with DASH: {str(e)}"
                })

        return results
