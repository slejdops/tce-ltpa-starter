# -*- coding: utf-8 -*-
"""Performance Diagnostics - Check GUI performance and response times"""

import time
import statistics
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from requests.exceptions import RequestException

from .base import BaseDiagnostic, DiagnosticResult, DiagnosticLevel
from ..settings import SETTINGS


class PerformanceDiagnostics(BaseDiagnostic):
    """Diagnose performance issues with DASH, JazzSM, and WebGUI"""

    # Common Netcool/DASH endpoints to test
    COMMON_ENDPOINTS = {
        'dash_home': '/ibm/console',
        'dash_api': '/ibm/console/api/platform/info',
        'jazzsm_home': '/ibm/console/jazz',
        'webgui_login': '/ibm/console/login',
    }

    def run_checks(self) -> List[DiagnosticResult]:
        """Execute all performance diagnostic checks"""
        self.clear_results()

        self.check_ltpa_validation_performance()
        self.check_network_latency()
        self.check_dns_resolution()

        return self.results

    def check_ltpa_validation_performance(self):
        """Check LTPA validation endpoint performance"""
        url = SETTINGS.servlet_url
        if not url:
            self.add_result(
                "Performance - LTPA Validation",
                DiagnosticLevel.WARNING,
                "Cannot test LTPA validation performance - endpoint not configured"
            )
            return

        try:
            # Test without token (just to check endpoint responsiveness)
            start = time.time()
            resp = requests.get(
                url,
                timeout=SETTINGS.TIMEOUT_SECONDS,
                verify=SETTINGS.requests_verify,
                allow_redirects=False
            )
            elapsed_ms = (time.time() - start) * 1000

            if elapsed_ms < 100:
                level = DiagnosticLevel.SUCCESS
                message = f"LTPA validation endpoint is fast ({elapsed_ms:.0f}ms)"
            elif elapsed_ms < 500:
                level = DiagnosticLevel.SUCCESS
                message = f"LTPA validation endpoint response time: {elapsed_ms:.0f}ms"
            elif elapsed_ms < 1000:
                level = DiagnosticLevel.WARNING
                message = f"LTPA validation endpoint is slow ({elapsed_ms:.0f}ms)"
            else:
                level = DiagnosticLevel.WARNING
                message = f"LTPA validation endpoint is very slow ({elapsed_ms:.0f}ms)"

            self.add_result(
                "Performance - LTPA Validation",
                level,
                message,
                details={
                    "url": url,
                    "response_time_ms": round(elapsed_ms, 2),
                    "status_code": resp.status_code
                },
                recommendation="Slow responses may indicate network issues, server load, or SSL overhead"
                if elapsed_ms > 500 else None
            )

        except RequestException as e:
            self.add_result(
                "Performance - LTPA Validation",
                DiagnosticLevel.ERROR,
                f"Failed to test LTPA validation performance: {str(e)}",
                details={"error": str(e)}
            )

    def check_network_latency(self):
        """Check network latency to DASH server"""
        host = SETTINGS.DASH_HOST_IP
        port = SETTINGS.DASH_HOST_PORT

        if not host:
            return

        base_url = f"https://{host}:{port}"

        # Measure TCP connection time
        import socket
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SETTINGS.TIMEOUT_SECONDS)
            sock.connect((host, port))
            tcp_time_ms = (time.time() - start) * 1000
            sock.close()

            if tcp_time_ms < 50:
                level = DiagnosticLevel.SUCCESS
                message = f"Low network latency to DASH ({tcp_time_ms:.0f}ms)"
            elif tcp_time_ms < 200:
                level = DiagnosticLevel.SUCCESS
                message = f"Normal network latency to DASH ({tcp_time_ms:.0f}ms)"
            elif tcp_time_ms < 500:
                level = DiagnosticLevel.WARNING
                message = f"Elevated network latency to DASH ({tcp_time_ms:.0f}ms)"
            else:
                level = DiagnosticLevel.WARNING
                message = f"High network latency to DASH ({tcp_time_ms:.0f}ms)"

            self.add_result(
                "Performance - Network Latency",
                level,
                message,
                details={
                    "host": host,
                    "port": port,
                    "tcp_connect_time_ms": round(tcp_time_ms, 2)
                },
                recommendation="High latency may indicate network congestion or routing issues"
                if tcp_time_ms > 500 else None
            )

        except Exception as e:
            self.add_result(
                "Performance - Network Latency",
                DiagnosticLevel.ERROR,
                f"Could not measure network latency: {str(e)}",
                details={"error": str(e)}
            )

    def check_dns_resolution(self):
        """Check DNS resolution time"""
        host = SETTINGS.DASH_HOST_IP
        if not host:
            return

        import socket
        try:
            start = time.time()
            socket.gethostbyname(host)
            dns_time_ms = (time.time() - start) * 1000

            if dns_time_ms < 50:
                level = DiagnosticLevel.SUCCESS
                message = f"Fast DNS resolution ({dns_time_ms:.0f}ms)"
            elif dns_time_ms < 200:
                level = DiagnosticLevel.SUCCESS
                message = f"Normal DNS resolution time ({dns_time_ms:.0f}ms)"
            else:
                level = DiagnosticLevel.WARNING
                message = f"Slow DNS resolution ({dns_time_ms:.0f}ms)"

            self.add_result(
                "Performance - DNS Resolution",
                level,
                message,
                details={
                    "host": host,
                    "resolution_time_ms": round(dns_time_ms, 2)
                },
                recommendation="Consider using IP address directly or checking DNS server configuration"
                if dns_time_ms > 200 else None
            )

        except socket.gaierror:
            # Already reported in connectivity checks
            pass
        except Exception as e:
            self.add_result(
                "Performance - DNS Resolution",
                DiagnosticLevel.WARNING,
                f"Could not measure DNS resolution: {str(e)}",
                details={"error": str(e)}
            )

    def benchmark_endpoint(
        self,
        url: str,
        num_requests: int = 10,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Benchmark a specific endpoint with multiple requests
        Returns detailed performance statistics
        """
        results = {
            "url": url,
            "total_requests": num_requests,
            "successful": 0,
            "failed": 0,
            "response_times": [],
            "statistics": {}
        }

        if headers is None:
            headers = {}
        if cookies is None:
            cookies = {}

        for i in range(num_requests):
            try:
                start = time.time()
                resp = requests.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    timeout=SETTINGS.TIMEOUT_SECONDS,
                    verify=SETTINGS.requests_verify,
                    allow_redirects=True
                )
                elapsed_ms = (time.time() - start) * 1000

                if resp.status_code == 200:
                    results["successful"] += 1
                    results["response_times"].append(elapsed_ms)
                else:
                    results["failed"] += 1

            except RequestException:
                results["failed"] += 1

            # Small delay between requests
            if i < num_requests - 1:
                time.sleep(0.1)

        # Calculate statistics
        if results["response_times"]:
            times = results["response_times"]
            results["statistics"] = {
                "mean_ms": round(statistics.mean(times), 2),
                "median_ms": round(statistics.median(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
                "stddev_ms": round(statistics.stdev(times), 2) if len(times) > 1 else 0,
            }

            # Calculate percentiles
            sorted_times = sorted(times)
            results["statistics"]["p95_ms"] = round(
                sorted_times[int(len(sorted_times) * 0.95)], 2
            )
            results["statistics"]["p99_ms"] = round(
                sorted_times[int(len(sorted_times) * 0.99)], 2
            )

        return results

    def test_common_endpoints(
        self,
        ltpa_token: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Test common DASH/JazzSM endpoints for availability and performance
        Returns results for each endpoint
        """
        base_url = f"https://{SETTINGS.DASH_HOST_IP}:{SETTINGS.DASH_HOST_PORT}"
        results = {}

        cookies = {}
        if ltpa_token:
            cookies[SETTINGS.LTPA_TOKEN_NAME] = ltpa_token

        for name, path in self.COMMON_ENDPOINTS.items():
            url = urljoin(base_url, path)
            endpoint_result = {
                "url": url,
                "accessible": False,
                "status_code": None,
                "response_time_ms": 0,
                "error": None
            }

            try:
                start = time.time()
                resp = requests.get(
                    url,
                    cookies=cookies,
                    timeout=SETTINGS.TIMEOUT_SECONDS,
                    verify=SETTINGS.requests_verify,
                    allow_redirects=True
                )
                elapsed_ms = (time.time() - start) * 1000

                endpoint_result["status_code"] = resp.status_code
                endpoint_result["response_time_ms"] = round(elapsed_ms, 2)
                endpoint_result["accessible"] = resp.status_code < 500

            except RequestException as e:
                endpoint_result["error"] = str(e)

            results[name] = endpoint_result

        return results

    def analyze_ssl_performance(self) -> Dict[str, Any]:
        """Analyze SSL/TLS handshake performance"""
        import ssl
        import socket

        host = SETTINGS.DASH_HOST_IP
        port = SETTINGS.DASH_HOST_PORT

        if not host:
            return {"error": "DASH host not configured"}

        results = {
            "host": host,
            "port": port,
            "tcp_time_ms": 0,
            "ssl_time_ms": 0,
            "total_time_ms": 0
        }

        try:
            # Measure TCP connection
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SETTINGS.TIMEOUT_SECONDS)
            sock.connect((host, port))
            tcp_time = time.time() - start
            results["tcp_time_ms"] = round(tcp_time * 1000, 2)

            # Measure SSL handshake
            context = ssl.create_default_context()
            if not SETTINGS.VERIFY_TLS:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            ssl_start = time.time()
            ssock = context.wrap_socket(sock, server_hostname=host)
            ssl_time = time.time() - ssl_start
            results["ssl_time_ms"] = round(ssl_time * 1000, 2)

            results["total_time_ms"] = round((tcp_time + ssl_time) * 1000, 2)

            # Get SSL info
            results["ssl_version"] = ssock.version()
            results["cipher"] = ssock.cipher()

            ssock.close()

        except Exception as e:
            results["error"] = str(e)

        return results
