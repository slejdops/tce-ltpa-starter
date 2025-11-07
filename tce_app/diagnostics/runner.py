# -*- coding: utf-8 -*-
"""Diagnostic Runner - Orchestrates all diagnostic checks"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .base import DiagnosticLevel
from .ltpa_diagnostics import LTPADiagnostics
from .session_diagnostics import SessionDiagnostics
from .performance_diagnostics import PerformanceDiagnostics
from .system_collector import SystemDataCollector


logger = logging.getLogger(__name__)


class DiagnosticRunner:
    """Main runner to execute all diagnostic checks"""

    def __init__(self):
        self.ltpa = LTPADiagnostics()
        self.session = SessionDiagnostics()
        self.performance = PerformanceDiagnostics()
        self.system = SystemDataCollector()

    def run_all_checks(self, quick: bool = False) -> Dict[str, Any]:
        """
        Run all diagnostic checks

        Args:
            quick: If True, skip time-consuming checks

        Returns:
            Dictionary containing all results and summary
        """
        logger.info("Starting diagnostic checks...")
        start_time = datetime.now(timezone.utc)

        results = {
            "started_at": start_time.isoformat(),
            "checks": {},
            "summary": {},
            "overall_status": "unknown"
        }

        # Run LTPA diagnostics
        logger.info("Running LTPA diagnostics...")
        try:
            ltpa_results = self.ltpa.run_checks()
            results["checks"]["ltpa"] = [r.to_dict() for r in ltpa_results]
            results["summary"]["ltpa"] = self.ltpa.get_summary()
        except Exception as e:
            logger.exception("Error running LTPA diagnostics")
            results["checks"]["ltpa"] = {"error": str(e)}

        # Run session diagnostics
        logger.info("Running session diagnostics...")
        try:
            session_results = self.session.run_checks()
            results["checks"]["session"] = [r.to_dict() for r in session_results]
            results["summary"]["session"] = self.session.get_summary()
        except Exception as e:
            logger.exception("Error running session diagnostics")
            results["checks"]["session"] = {"error": str(e)}

        # Run performance diagnostics
        logger.info("Running performance diagnostics...")
        try:
            perf_results = self.performance.run_checks()
            results["checks"]["performance"] = [r.to_dict() for r in perf_results]
            results["summary"]["performance"] = self.performance.get_summary()
        except Exception as e:
            logger.exception("Error running performance diagnostics")
            results["checks"]["performance"] = {"error": str(e)}

        # Run system data collection
        logger.info("Collecting system data...")
        try:
            system_results = self.system.run_checks()
            results["checks"]["system"] = [r.to_dict() for r in system_results]
            results["summary"]["system"] = self.system.get_summary()
        except Exception as e:
            logger.exception("Error collecting system data")
            results["checks"]["system"] = {"error": str(e)}

        # Calculate overall status
        results["overall_status"] = self._calculate_overall_status(results["summary"])

        end_time = datetime.now(timezone.utc)
        results["completed_at"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(f"Diagnostic checks completed in {results['duration_seconds']:.2f}s")
        logger.info(f"Overall status: {results['overall_status']}")

        return results

    def run_ltpa_checks(self) -> Dict[str, Any]:
        """Run only LTPA-related checks"""
        logger.info("Running LTPA diagnostics...")
        results = self.ltpa.run_checks()
        return {
            "checks": [r.to_dict() for r in results],
            "summary": self.ltpa.get_summary()
        }

    def run_session_checks(self) -> Dict[str, Any]:
        """Run only session-related checks"""
        logger.info("Running session diagnostics...")
        results = self.session.run_checks()
        return {
            "checks": [r.to_dict() for r in results],
            "summary": self.session.get_summary()
        }

    def run_performance_checks(self) -> Dict[str, Any]:
        """Run only performance-related checks"""
        logger.info("Running performance diagnostics...")
        results = self.performance.run_checks()
        return {
            "checks": [r.to_dict() for r in results],
            "summary": self.performance.get_summary()
        }

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a specific LTPA token"""
        logger.info("Validating LTPA token...")
        return self.ltpa.validate_ltpa_token(token)

    def test_session_persistence(
        self,
        test_url: str,
        ltpa_token: str,
        num_requests: int = 5
    ) -> Dict[str, Any]:
        """Test session persistence"""
        logger.info(f"Testing session persistence with {num_requests} requests...")
        return self.session.test_session_persistence(test_url, ltpa_token, num_requests)

    def benchmark_endpoint(
        self,
        url: str,
        num_requests: int = 10,
        ltpa_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Benchmark a specific endpoint"""
        logger.info(f"Benchmarking {url} with {num_requests} requests...")
        cookies = {}
        if ltpa_token:
            from ..settings import SETTINGS
            cookies[SETTINGS.LTPA_TOKEN_NAME] = ltpa_token
        return self.performance.benchmark_endpoint(url, num_requests, cookies=cookies)

    def search_logs(
        self,
        search_dirs: Optional[list] = None,
        error_patterns: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
        max_matches: int = 100
    ) -> list:
        """Search logs for errors"""
        logger.info("Searching logs for errors...")
        return self.system.search_logs_for_errors(
            search_dirs, error_patterns, exclude_dirs, max_matches
        )

    def generate_report(
        self,
        include_logs: bool = False,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Generate a comprehensive diagnostic report"""
        logger.info("Generating diagnostic report...")

        # Run all checks
        all_results = self.run_all_checks()

        # Add additional system information
        report = {
            "report_type": "netcool_dash_diagnostics",
            "format_version": "1.0",
            **all_results
        }

        if include_logs:
            report["log_analysis"] = {
                "errors": self.search_logs(max_matches=50)
            }

        # Add recommendations based on findings
        report["recommendations"] = self._generate_recommendations(report)

        return report

    def _calculate_overall_status(self, summary: Dict[str, Dict[str, int]]) -> str:
        """Calculate overall status from all check summaries"""
        total_critical = sum(s.get("critical", 0) for s in summary.values())
        total_errors = sum(s.get("error", 0) for s in summary.values())
        total_warnings = sum(s.get("warning", 0) for s in summary.values())

        if total_critical > 0:
            return "critical"
        elif total_errors > 0:
            return "error"
        elif total_warnings > 0:
            return "warning"
        else:
            return "success"

    def _generate_recommendations(self, report: Dict[str, Any]) -> list:
        """Generate recommendations based on diagnostic results"""
        recommendations = []

        overall_status = report.get("overall_status", "unknown")

        if overall_status == "critical":
            recommendations.append({
                "priority": "critical",
                "message": "Critical issues detected. Address these immediately before proceeding.",
                "category": "general"
            })

        # Analyze each category
        for category, checks in report.get("checks", {}).items():
            if isinstance(checks, list):
                for check in checks:
                    if check.get("recommendation"):
                        recommendations.append({
                            "priority": check.get("level", "info"),
                            "message": check.get("recommendation"),
                            "category": category,
                            "check_name": check.get("name")
                        })

        return recommendations

    def get_health_status(self) -> Dict[str, Any]:
        """Get a quick health status (fast check)"""
        from ..settings import SETTINGS
        import socket

        status = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Quick DASH connectivity check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((SETTINGS.DASH_HOST_IP, SETTINGS.DASH_HOST_PORT))
            sock.close()
            status["checks"]["dash_connectivity"] = result == 0
            if result != 0:
                status["healthy"] = False
        except Exception as e:
            status["checks"]["dash_connectivity"] = False
            status["checks"]["dash_connectivity_error"] = str(e)
            status["healthy"] = False

        # Check configuration
        config_ok = all([
            SETTINGS.DASH_HOST_IP,
            SETTINGS.LTPA_TOKEN_NAME,
            SETTINGS.DASH_INTEGRATION_SERVICE,
            SETTINGS.FLASK_SECRET_KEY
        ])
        status["checks"]["configuration"] = config_ok
        if not config_ok:
            status["healthy"] = False

        return status
