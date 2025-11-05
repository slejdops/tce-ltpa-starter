# -*- coding: utf-8 -*-
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import UserDetails


def check_user_privileges(user: "UserDetails", required_roles: Optional[List[str]] = None) -> bool:
    """Return True if the user has at least one of the required roles."""
    if not required_roles:
        return True
    if not user or not user.roles:
        return False

    req_norm = {r.strip() for r in required_roles if isinstance(r, str) and r.strip()}
    user_norm = {r.strip() for r in user.roles if isinstance(r, str) and r.strip()}
    return bool(req_norm & user_norm)
