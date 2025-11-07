# -*- coding: utf-8 -*-
"""Base classes for diagnostic checks"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional
import logging


class DiagnosticLevel(Enum):
    """Severity levels for diagnostic findings"""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticResult:
    """Represents a single diagnostic check result"""

    def __init__(
        self,
        name: str,
        level: DiagnosticLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recommendation: Optional[str] = None
    ):
        self.name = name
        self.level = level
        self.message = message
        self.details = details or {}
        self.recommendation = recommendation
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format"""
        return {
            'name': self.name,
            'level': self.level.value,
            'message': self.message,
            'details': self.details,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat()
        }

    def __repr__(self):
        return f"DiagnosticResult({self.name}, {self.level.value}, {self.message})"


class BaseDiagnostic(ABC):
    """Base class for all diagnostic modules"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.results: List[DiagnosticResult] = []

    @abstractmethod
    def run_checks(self) -> List[DiagnosticResult]:
        """Execute all diagnostic checks and return results"""
        pass

    def add_result(
        self,
        name: str,
        level: DiagnosticLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recommendation: Optional[str] = None
    ):
        """Add a diagnostic result"""
        result = DiagnosticResult(name, level, message, details, recommendation)
        self.results.append(result)
        self.logger.log(
            self._level_to_logging(level),
            f"{name}: {message}"
        )
        return result

    @staticmethod
    def _level_to_logging(level: DiagnosticLevel) -> int:
        """Convert DiagnosticLevel to logging level"""
        mapping = {
            DiagnosticLevel.SUCCESS: logging.INFO,
            DiagnosticLevel.INFO: logging.INFO,
            DiagnosticLevel.WARNING: logging.WARNING,
            DiagnosticLevel.ERROR: logging.ERROR,
            DiagnosticLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(level, logging.INFO)

    def get_summary(self) -> Dict[str, int]:
        """Get summary of results by level"""
        summary = {level.value: 0 for level in DiagnosticLevel}
        for result in self.results:
            summary[result.level.value] += 1
        return summary

    def clear_results(self):
        """Clear all stored results"""
        self.results = []
