"""
Analytics Workbench — Admin Management Module
Exports the public surface used by app.py.
"""
from .auth import (
    is_authenticated,
    is_admin,
    get_current_user,
    render_login_page,
    logout,
    require_admin,
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_VIEWER,
    ADMIN_ROLES,
)
from .user_management import render_user_management
from .settings_manager import render_settings_manager
from .api_keys import render_api_keys
from .dashboard import render_dashboard

__all__ = [
    "is_authenticated",
    "is_admin",
    "get_current_user",
    "render_login_page",
    "logout",
    "require_admin",
    "ROLE_SUPERADMIN",
    "ROLE_ADMIN",
    "ROLE_VIEWER",
    "ADMIN_ROLES",
    "render_user_management",
    "render_settings_manager",
    "render_api_keys",
    "render_dashboard",
]
