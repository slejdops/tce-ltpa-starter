# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
from functools import wraps
from typing import List, Optional

import requests
from flask import abort, g, request

from .settings import SETTINGS
from .rbac import check_user_privileges

logger = logging.getLogger("tce-auth")


class UserDetails(object):
    def __init__(self, username: str, roles: List[str]):
        self.username = username
        # normalize roles
        seen = set()
        norm = []
        for r in roles or []:
            try:
                s = str(r).strip()
            except Exception:  # noqa
                continue
            if s and s not in seen:
                seen.add(s)
                norm.append(s)
        self.roles = norm

    def as_dict(self):
        return {"username": self.username, "roles": list(self.roles)}


class AuthManager(object):
    def get_user_details(self) -> UserDetails:
        token = self._extract_ltpa_token()
        if not token:
            logger.warning("No LTPA token found in request")
            abort(401, description="Missing LTPA token")

        payload = self._call_dash_servlet(token)
        username, roles = self._extract_identity(payload)
        if not username:
            logger.error("DASH servlet response missing username: %s", payload)
            abort(403, description="Invalid LTPA token or missing identity")

        user = UserDetails(username=username, roles=roles or [])
        logger.info("Authenticated '%s' with roles=%s", user.username, user.roles)
        return user

    def _extract_ltpa_token(self) -> Optional[str]:
        header_names = ["X-Lpta-Token", "X-Ltpa-Token", "X-LTPA-Token"]
        token = None
        for hn in header_names:
            if hn in request.headers:
                token = request.headers.get(hn)
                break
        if not token:
            token = request.cookies.get(SETTINGS.LTPA_TOKEN_NAME)
        if token:
            token = token.strip()
        return token or None

    def _call_dash_servlet(self, ltpa_token: str) -> dict:
        url = SETTINGS.servlet_url
        headers = {
            "Accept": "application/json",
            "Cookie": f"{SETTINGS.LTPA_TOKEN_NAME}={ltpa_token}",
            "X-Lpta-Token": ltpa_token,
        }
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=SETTINGS.TIMEOUT_SECONDS,
                verify=SETTINGS.requests_verify,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to reach DASH servlet: %s", exc)
            abort(502, description="Cannot reach DASH auth service")

        if resp.status_code != 200:
            logger.warning("DASH servlet returned %s: %s", resp.status_code, resp.text[:200])
            abort(403, description="LTPA token rejected by DASH")

        try:
            return resp.json() if resp.content else {}
        except ValueError:
            logger.error("Non-JSON response from DASH servlet: %r", resp.text[:200])
            abort(502, description="Invalid response from DASH auth service")

    def _extract_identity(self, payload: dict):
        if not isinstance(payload, dict):
            return None, []
        candidates = [payload]
        for k in ("data", "result", "user", "principal"):
            if isinstance(payload.get(k), dict):
                candidates.append(payload.get(k))

        username = None
        roles = None

        def _find_first(obj: dict, keys: List[str]):
            for k in keys:
                if k in obj:
                    return obj.get(k)
            return None

        for obj in candidates:
            if username is None:
                u = _find_first(obj, SETTINGS.USERNAME_KEYS)
                if isinstance(u, (str, int)):
                    username = str(u)
            if roles is None:
                r = _find_first(obj, SETTINGS.ROLES_KEYS)
                if isinstance(r, list):
                    roles = [str(x) for x in r]
                elif isinstance(r, (str, int)):
                    roles = [s.strip() for s in str(r).split(",") if s.strip()]

        return username, (roles or [])


auth_manager = AuthManager()


def auth_required(required_roles: Optional[List[str]] = None):
    """Protect a route with DASH SSO + optional role check."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = auth_manager.get_user_details()
            g.user = user
            if not check_user_privileges(user, required_roles):
                abort(403, description="Insufficient privileges")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
