# -*- coding: utf-8 -*-
"""System Data Collector - Gather logs, configs, and system information"""

import os
import sys
import platform
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import BaseDiagnostic, DiagnosticResult, DiagnosticLevel
from ..settings import SETTINGS


class SystemDataCollector(BaseDiagnostic):
    """Collect system data, logs, and configuration information"""

    # Common log locations for Netcool/DASH components
    LOG_LOCATIONS = [
        '/opt/IBM/tivoli/netcool/omnibus/log',
        '/opt/IBM/JazzSM/profile/logs',
        '/opt/IBM/WebSphere/AppServer/profiles/*/logs',
        '/var/log/netcool',
        '/var/log/dash',
        'logs/',
        './logs',
    ]

    CONFIG_LOCATIONS = [
        '/opt/IBM/tivoli/netcool/omnibus/etc',
        '/opt/IBM/JazzSM/profile/config',
        '/opt/IBM/WebSphere/AppServer/profiles/*/config',
    ]

    def run_checks(self) -> List[DiagnosticResult]:
        """Execute system data collection"""
        self.clear_results()

        self.collect_environment_info()
        self.collect_configuration()
        self.check_log_locations()

        return self.results

    def collect_environment_info(self):
        """Collect environment and system information"""
        env_data = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
        }

        self.add_result(
            "System - Environment",
            DiagnosticLevel.INFO,
            f"Python {sys.version.split()[0]} on {platform.platform()}",
            details=env_data
        )

    def collect_configuration(self):
        """Collect current configuration settings"""
        config = {
            "DASH_HOST_IP": SETTINGS.DASH_HOST_IP,
            "DASH_HOST_PORT": SETTINGS.DASH_HOST_PORT,
            "DASH_INTEGRATION_SERVICE": SETTINGS.DASH_INTEGRATION_SERVICE,
            "LTPA_TOKEN_NAME": SETTINGS.LTPA_TOKEN_NAME,
            "VERIFY_TLS": SETTINGS.VERIFY_TLS,
            "TIMEOUT_SECONDS": SETTINGS.TIMEOUT_SECONDS,
            "FLASK_SECRET_KEY": "***REDACTED***" if SETTINGS.FLASK_SECRET_KEY else None,
        }

        # Check for optional settings
        if hasattr(SETTINGS, 'CA_BUNDLE_PATH'):
            config["CA_BUNDLE_PATH"] = getattr(SETTINGS, 'CA_BUNDLE_PATH', None)

        self.add_result(
            "System - Configuration",
            DiagnosticLevel.INFO,
            "Current configuration collected",
            details=config
        )

        # Check for missing critical settings
        missing = []
        for key, value in config.items():
            if key != "FLASK_SECRET_KEY" and value is None:
                missing.append(key)

        if missing:
            self.add_result(
                "System - Missing Config",
                DiagnosticLevel.WARNING,
                f"Missing configuration: {', '.join(missing)}",
                details={"missing_vars": missing},
                recommendation="Set missing environment variables"
            )

    def check_log_locations(self):
        """Check for existence of common log directories"""
        found_logs = []
        not_found = []

        for loc in self.LOG_LOCATIONS:
            # Expand wildcards
            if '*' in loc:
                try:
                    parent = str(Path(loc).parent)
                    pattern = Path(loc).name
                    if os.path.exists(parent):
                        matches = list(Path(parent).glob(pattern))
                        for match in matches:
                            if match.is_dir():
                                found_logs.append(str(match))
                except Exception:
                    pass
            else:
                if os.path.exists(loc) and os.path.isdir(loc):
                    found_logs.append(loc)
                else:
                    not_found.append(loc)

        if found_logs:
            self.add_result(
                "System - Log Directories",
                DiagnosticLevel.INFO,
                f"Found {len(found_logs)} log directories",
                details={"found": found_logs}
            )
        else:
            self.add_result(
                "System - Log Directories",
                DiagnosticLevel.WARNING,
                "No standard log directories found",
                details={"searched": self.LOG_LOCATIONS},
                recommendation="Ensure application is installed or check custom log locations"
            )

    def collect_environment_variables(self) -> Dict[str, str]:
        """Collect all environment variables (with sensitive data redacted)"""
        env_vars = {}
        sensitive_keys = ['password', 'secret', 'key', 'token', 'credential']

        for key, value in os.environ.items():
            # Redact sensitive values
            if any(s in key.lower() for s in sensitive_keys):
                env_vars[key] = "***REDACTED***"
            else:
                env_vars[key] = value

        return env_vars

    def find_log_files(
        self,
        search_dirs: Optional[List[str]] = None,
        patterns: Optional[List[str]] = None,
        max_files: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find log files in specified directories
        Returns list of log file metadata
        """
        if search_dirs is None:
            search_dirs = self.LOG_LOCATIONS

        if patterns is None:
            patterns = ['*.log', '*.out', '*.err', '*error*', '*exception*']

        log_files = []

        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue

            try:
                for pattern in patterns:
                    for log_file in Path(search_dir).rglob(pattern):
                        if log_file.is_file():
                            try:
                                stat = log_file.stat()
                                log_files.append({
                                    "path": str(log_file),
                                    "size_bytes": stat.st_size,
                                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    "readable": os.access(log_file, os.R_OK)
                                })

                                if len(log_files) >= max_files:
                                    break
                            except Exception:
                                continue

                    if len(log_files) >= max_files:
                        break
            except Exception as e:
                self.logger.warning(f"Error searching {search_dir}: {e}")

        return log_files

    def read_log_file(
        self,
        file_path: str,
        max_lines: int = 1000,
        tail: bool = True,
        filter_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read a log file with optional filtering
        Returns log content and metadata
        """
        result = {
            "path": file_path,
            "exists": os.path.exists(file_path),
            "readable": False,
            "lines": [],
            "total_lines": 0,
            "truncated": False
        }

        if not result["exists"]:
            result["error"] = "File does not exist"
            return result

        if not os.access(file_path, os.R_OK):
            result["error"] = "File is not readable"
            return result

        result["readable"] = True

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                result["total_lines"] = len(lines)

                # Apply filtering
                if filter_pattern:
                    import re
                    pattern = re.compile(filter_pattern, re.IGNORECASE)
                    lines = [line for line in lines if pattern.search(line)]

                # Get tail or head
                if tail and len(lines) > max_lines:
                    lines = lines[-max_lines:]
                    result["truncated"] = True
                elif len(lines) > max_lines:
                    lines = lines[:max_lines]
                    result["truncated"] = True

                result["lines"] = [line.rstrip() for line in lines]

        except Exception as e:
            result["error"] = str(e)

        return result

    def search_logs_for_errors(
        self,
        search_dirs: Optional[List[str]] = None,
        error_patterns: Optional[List[str]] = None,
        max_matches: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search log files for error patterns
        Returns list of matches with context
        """
        if error_patterns is None:
            error_patterns = [
                r'ERROR',
                r'SEVERE',
                r'FATAL',
                r'Exception',
                r'failed',
                r'timeout',
                r'LTPA.*invalid',
                r'LTPA.*expired',
                r'authentication.*failed',
                r'session.*expired'
            ]

        matches = []
        log_files = self.find_log_files(search_dirs)

        import re
        combined_pattern = re.compile('|'.join(error_patterns), re.IGNORECASE)

        for log_file_info in log_files:
            if len(matches) >= max_matches:
                break

            file_path = log_file_info['path']
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if combined_pattern.search(line):
                            matches.append({
                                "file": file_path,
                                "line_number": line_num,
                                "content": line.rstrip(),
                                "timestamp": log_file_info['modified']
                            })

                            if len(matches) >= max_matches:
                                break
            except Exception as e:
                self.logger.warning(f"Error reading {file_path}: {e}")

        return matches

    def check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity using system tools"""
        results = {
            "dns_resolvers": [],
            "routes": [],
            "interfaces": []
        }

        # Try to get DNS resolvers
        try:
            if os.path.exists('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            results["dns_resolvers"].append(line.split()[1])
        except Exception:
            pass

        # Try to get network interfaces (Linux)
        try:
            import socket
            import fcntl
            import struct

            # This is a simple check for Linux systems
            if platform.system() == 'Linux':
                try:
                    output = subprocess.check_output(['ip', 'addr'], text=True)
                    results["interfaces_output"] = output[:500]
                except Exception:
                    pass
        except Exception:
            pass

        return results

    def generate_diagnostic_report(
        self,
        ltpa_results: List[DiagnosticResult],
        session_results: List[DiagnosticResult],
        performance_results: List[DiagnosticResult],
        include_logs: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive diagnostic report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "system_info": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "hostname": platform.node(),
            },
            "configuration": {
                "dash_host": SETTINGS.DASH_HOST_IP,
                "dash_port": SETTINGS.DASH_HOST_PORT,
                "ltpa_token_name": SETTINGS.LTPA_TOKEN_NAME,
                "verify_tls": SETTINGS.VERIFY_TLS,
            },
            "results": {
                "ltpa": [r.to_dict() for r in ltpa_results],
                "session": [r.to_dict() for r in session_results],
                "performance": [r.to_dict() for r in performance_results],
            },
            "summary": {
                "ltpa": self._summarize_results(ltpa_results),
                "session": self._summarize_results(session_results),
                "performance": self._summarize_results(performance_results),
            }
        }

        if include_logs:
            report["log_errors"] = self.search_logs_for_errors(max_matches=50)

        return report

    def _summarize_results(self, results: List[DiagnosticResult]) -> Dict[str, int]:
        """Summarize results by level"""
        summary = {"success": 0, "info": 0, "warning": 0, "error": 0, "critical": 0}
        for result in results:
            summary[result.level.value] += 1
        return summary
