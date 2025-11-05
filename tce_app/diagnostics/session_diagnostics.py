# -*- coding: utf-8 -*-
"""Session Diagnostics - Check session management and persistence"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests
from requests.exceptions import RequestException

from .base import BaseDiagnostic, DiagnosticResult, DiagnosticLevel
from ..settings import SETTINGS


class SessionDiagnostics(BaseDiagnostic):
    """Diagnose session management and SSO issues"""

    def run_checks(self) -> List[DiagnosticResult]:
        """Execute all session diagnostic checks"""
        self.clear_results()

        self.check_flask_session_config()
        self.check_session_cookie_security()
        self.check_sso_cookie_domain()

        return self.results

    def check_flask_session_config(self):
        """Check Flask session configuration"""
        if not SETTINGS.FLASK_SECRET_KEY:
            self.add_result(
                "Session - Secret Key",
                DiagnosticLevel.CRITICAL,
                "FLASK_SECRET_KEY is not configured",
                recommendation="Set FLASK_SECRET_KEY to a secure random value (use 'openssl rand -hex 32')"
            )
        elif SETTINGS.FLASK_SECRET_KEY in ['change-me', 'secret', 'dev', 'test']:
            self.add_result(
                "Session - Secret Key",
                DiagnosticLevel.ERROR,
                "FLASK_SECRET_KEY is using a default/weak value",
                details={"key_value": SETTINGS.FLASK_SECRET_KEY[:10] + "..."},
                recommendation="Change FLASK_SECRET_KEY to a strong random value"
            )
        elif len(SETTINGS.FLASK_SECRET_KEY) < 32:
            self.add_result(
                "Session - Secret Key",
                DiagnosticLevel.WARNING,
                f"FLASK_SECRET_KEY is short ({len(SETTINGS.FLASK_SECRET_KEY)} chars)",
                recommendation="Use at least 32 characters for the secret key"
            )
        else:
            self.add_result(
                "Session - Secret Key",
                DiagnosticLevel.SUCCESS,
                f"FLASK_SECRET_KEY is properly configured ({len(SETTINGS.FLASK_SECRET_KEY)} chars)"
            )

    def check_session_cookie_security(self):
        """Check session cookie security settings"""
        # These are best practices for session cookies
        recommendations = []

        # Check if HTTPS is being used
        if SETTINGS.DASH_HOST_PORT == 443 or SETTINGS.DASH_HOST_PORT == 8443:
            self.add_result(
                "Session - HTTPS",
                DiagnosticLevel.SUCCESS,
                f"Using secure port {SETTINGS.DASH_HOST_PORT}",
                details={"port": SETTINGS.DASH_HOST_PORT}
            )
        else:
            self.add_result(
                "Session - HTTPS",
                DiagnosticLevel.WARNING,
                f"Using non-standard port {SETTINGS.DASH_HOST_PORT}",
                details={"port": SETTINGS.DASH_HOST_PORT},
                recommendation="Ensure HTTPS is used in production for secure cookie transmission"
            )

        # General security recommendations
        self.add_result(
            "Session - Cookie Best Practices",
            DiagnosticLevel.INFO,
            "Session cookies should have: Secure flag (HTTPS only), HttpOnly flag (no JS access), SameSite=Strict/Lax",
            recommendation="Configure your web server/proxy to set appropriate cookie flags"
        )

    def check_sso_cookie_domain(self):
        """Check SSO cookie domain configuration"""
        # For SSO to work, cookies must be shared across applications
        self.add_result(
            "Session - SSO Domain",
            DiagnosticLevel.INFO,
            "For SSO to work, ensure LTPA cookies are set for the common domain",
            details={
                "dash_host": SETTINGS.DASH_HOST_IP,
                "token_name": SETTINGS.LTPA_TOKEN_NAME
            },
            recommendation="Verify that DASH and this app share the same cookie domain (e.g., .example.com)"
        )

    def test_session_persistence(
        self,
        test_url: str,
        ltpa_token: str,
        num_requests: int = 5
    ) -> Dict[str, Any]:
        """
        Test session persistence across multiple requests
        Returns detailed results about session behavior
        """
        results = {
            "total_requests": num_requests,
            "successful": 0,
            "failed": 0,
            "requests": [],
            "session_stable": False,
            "average_response_time": 0
        }

        if not ltpa_token:
            results["error"] = "No LTPA token provided"
            return results

        response_times = []
        session_cookies = {}

        for i in range(num_requests):
            request_result = {
                "request_num": i + 1,
                "success": False,
                "status_code": None,
                "response_time_ms": 0,
                "session_cookies": {}
            }

            try:
                start_time = time.time()
                resp = requests.get(
                    test_url,
                    cookies={SETTINGS.LTPA_TOKEN_NAME: ltpa_token, **session_cookies},
                    timeout=SETTINGS.TIMEOUT_SECONDS,
                    verify=SETTINGS.requests_verify,
                    allow_redirects=True
                )
                response_time = (time.time() - start_time) * 1000

                request_result["success"] = resp.status_code == 200
                request_result["status_code"] = resp.status_code
                request_result["response_time_ms"] = round(response_time, 2)

                # Track session cookies
                for cookie_name in resp.cookies.keys():
                    if 'session' in cookie_name.lower() or cookie_name == SETTINGS.LTPA_TOKEN_NAME:
                        session_cookies[cookie_name] = resp.cookies[cookie_name]
                        request_result["session_cookies"][cookie_name] = "present"

                if resp.status_code == 200:
                    results["successful"] += 1
                    response_times.append(response_time)
                else:
                    results["failed"] += 1

            except RequestException as e:
                request_result["error"] = str(e)
                results["failed"] += 1

            results["requests"].append(request_result)

            # Small delay between requests
            if i < num_requests - 1:
                time.sleep(0.5)

        # Calculate statistics
        if response_times:
            results["average_response_time"] = round(sum(response_times) / len(response_times), 2)
            results["min_response_time"] = round(min(response_times), 2)
            results["max_response_time"] = round(max(response_times), 2)

        # Determine if session is stable
        results["session_stable"] = results["successful"] == num_requests

        return results

    def analyze_session_timeout(
        self,
        test_url: str,
        ltpa_token: str,
        check_intervals: List[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze session timeout behavior
        check_intervals: list of seconds to wait between checks (e.g., [0, 60, 300, 600])
        """
        if check_intervals is None:
            check_intervals = [0, 60, 300]  # 0s, 1min, 5min

        results = {
            "checks": [],
            "timeout_detected": False,
            "estimated_timeout_seconds": None
        }

        if not ltpa_token:
            results["error"] = "No LTPA token provided"
            return results

        last_success_time = None

        for interval in check_intervals:
            if interval > 0:
                self.logger.info(f"Waiting {interval} seconds before next check...")
                time.sleep(interval)

            check_result = {
                "elapsed_seconds": interval,
                "timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "status_code": None,
                "message": ""
            }

            try:
                resp = requests.get(
                    test_url,
                    cookies={SETTINGS.LTPA_TOKEN_NAME: ltpa_token},
                    timeout=SETTINGS.TIMEOUT_SECONDS,
                    verify=SETTINGS.requests_verify,
                    allow_redirects=False
                )

                check_result["status_code"] = resp.status_code

                if resp.status_code == 200:
                    check_result["success"] = True
                    check_result["message"] = "Session still valid"
                    last_success_time = interval
                elif resp.status_code in [401, 403]:
                    check_result["message"] = "Session expired/invalid"
                    results["timeout_detected"] = True
                    if last_success_time is not None:
                        results["estimated_timeout_seconds"] = interval
                else:
                    check_result["message"] = f"Unexpected status: {resp.status_code}"

            except RequestException as e:
                check_result["message"] = f"Request failed: {str(e)}"
                check_result["error"] = str(e)

            results["checks"].append(check_result)

            # Stop if timeout detected
            if results["timeout_detected"]:
                break

        return results
