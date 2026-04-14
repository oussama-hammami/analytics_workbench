"""
Analytics Workbench — Admin Management Module
Exports the public surface used by app.py.
"""
from .auth import (
    is_authenticated,
    is_admin,
    is_manager,
    get_current_user,
    render_login_page,
    logout,
    require_auth,
    require_admin,
    require_manager_or_above,
    get_csrf_token,
    validate_csrf_token,
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_VIEWER,
    ADMIN_ROLES,
    MANAGER_ROLES,
)
from .user_management import render_user_management
from .settings_manager import render_settings_manager
from .api_keys import render_api_keys
from .dashboard import render_dashboard
from .log_viewer import render_log_viewer

__all__ = [
    "is_authenticated",
    "is_admin",
    "is_manager",
    "get_current_user",
    "render_login_page",
    "logout",
    "require_auth",
    "require_admin",
    "require_manager_or_above",
    "get_csrf_token",
    "validate_csrf_token",
    "ROLE_SUPERADMIN",
    "ROLE_ADMIN",
    "ROLE_MANAGER",
    "ROLE_VIEWER",
    "ADMIN_ROLES",
    "MANAGER_ROLES",
    "render_user_management",
    "render_settings_manager",
    "render_api_keys",
    "render_dashboard",
    "render_log_viewer",
]
