# -*- coding: utf-8 -*-
"""Security utilities for SSRF protection and input validation"""

import os
import ipaddress
from urllib.parse import urlparse
from typing import List, Optional


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private/internal"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks
    
    Checks:
    - Only HTTP/HTTPS schemes allowed
    - No private/internal IP addresses
    - Hostname must be resolvable
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ['http', 'https']:
            return False
        
        if not parsed.hostname:
            return False
        
        try:
            if is_private_ip(parsed.hostname):
                return False
        except ValueError:
            pass
        
        import socket
        try:
            ip_address = socket.gethostbyname(parsed.hostname)
            if is_private_ip(ip_address):
                return False
        except socket.gaierror:
            return False
        
        return True
        
    except Exception:
        return False


def validate_log_directories(directories: List[str]) -> List[str]:
    """
    Validate log directories against allowlist to prevent path traversal
    
    Only allows predefined safe directories for log searching
    """
    from .diagnostics.system_collector import SystemDataCollector
    
    allowed_dirs = set(SystemDataCollector.LOG_LOCATIONS)
    
    validated = []
    for directory in directories:
        if not directory:
            continue
            
        try:
            normalized = os.path.abspath(directory)
        except Exception:
            continue
        
        is_allowed = False
        for allowed in allowed_dirs:
            try:
                allowed_abs = os.path.abspath(allowed)
                if normalized == allowed_abs or normalized.startswith(allowed_abs + os.sep):
                    is_allowed = True
                    break
            except Exception:
                continue
        
        if is_allowed:
            validated.append(directory)
    
    return validated if validated else None
