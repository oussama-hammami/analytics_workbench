"""
Authentication & Role-Based Access Control (RBAC).

Roles
-----
superadmin  Full system access (user management, settings, all analytics).
admin       Manage users and settings; full analytics access.
manager     Create and edit analytics (datasets, preprocessing, model training).
viewer      Read-only access to dashboards and analytics outputs.
"""
from __future__ import annotations

import html as _html
import secrets
from typing import Optional, Tuple
import streamlit as st
from .db import get_db, table, is_configured

ROLE_SUPERADMIN = "superadmin"
ROLE_ADMIN      = "admin"
ROLE_MANAGER    = "manager"
ROLE_VIEWER     = "viewer"

# Roles that may access the admin control panel.
ADMIN_ROLES    = {ROLE_SUPERADMIN, ROLE_ADMIN}
# Roles that may create / edit analytics content.
MANAGER_ROLES  = {ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_MANAGER}


def _hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── Session helpers ──────────────────────────────────────────────────────────

def get_current_user() -> Optional[dict]:
    return st.session_state.get("auth_user")


def is_authenticated() -> bool:
    return get_current_user() is not None


def is_admin() -> bool:
    user = get_current_user()
    return user is not None and user.get("role") in ADMIN_ROLES


def is_manager() -> bool:
    """True for superadmin, admin, and manager roles."""
    user = get_current_user()
    return user is not None and user.get("role") in MANAGER_ROLES


# ── Access guards ────────────────────────────────────────────────────────────

def require_auth() -> None:
    """Stop execution if the user is not logged in."""
    if not is_authenticated():
        st.error("🔒 Please sign in to access this page.")
        st.stop()


def require_admin() -> None:
    """Stop execution unless the user holds an admin role."""
    require_auth()
    if not is_admin():
        st.error("🔒 Access denied — Admin role required.")
        st.stop()


def require_manager_or_above() -> None:
    """Stop execution unless the user can create / edit analytics content."""
    require_auth()
    if not is_manager():
        st.error("🔒 Access denied — Manager role or higher required.")
        st.stop()


# ── CSRF token utilities ─────────────────────────────────────────────────────
# Streamlit uses a persistent WebSocket session (state is server-side), so
# classic cookie-based CSRF cannot occur.  These helpers add a defense-in-depth
# nonce that prevents replay attacks and session-fixation edge cases.

def _init_csrf_token() -> None:
    """Ensure a CSRF token exists for the current Streamlit session."""
    if "_aw_csrf" not in st.session_state:
        st.session_state["_aw_csrf"] = secrets.token_hex(32)


def get_csrf_token() -> str:
    """Return the session-scoped CSRF token, creating it if absent."""
    _init_csrf_token()
    return st.session_state["_aw_csrf"]


def validate_csrf_token(token: str) -> bool:
    """Constant-time comparison of *token* against the session's CSRF token."""
    expected = st.session_state.get("_aw_csrf", "")
    if not expected:
        return False
    return secrets.compare_digest(expected, token)


def login(email: str, password: str) -> Tuple[bool, str]:
    if not is_configured():
        return False, "Database not available."
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"SELECT id, name, email, password, role, is_active "
                f"FROM {table('users')} WHERE email = ? LIMIT 1",
                (email.strip(),),
            )
            row = cur.fetchone()
    except Exception as exc:
        return False, f"Database error: {exc}"

    if not row:
        return False, "Invalid email or password."
    if not row["is_active"]:
        return False, "Your account is inactive. Contact an administrator."
    if not _verify_password(password, row["password"]):
        return False, "Invalid email or password."

    try:
        with get_db() as (_, cur):
            cur.execute(
                f"UPDATE {table('users')} SET last_login = datetime('now') WHERE id = ?",
                (row["id"],),
            )
    except Exception:
        pass

    st.session_state.auth_user = {
        "id":        row["id"],
        "name":      row["name"],
        "email":     row["email"],
        "role":      row["role"],
        "is_active": row["is_active"],
    }
    # Rotate CSRF token on every new login.
    st.session_state["_aw_csrf"] = secrets.token_hex(32)
    return True, f"Welcome back, {_html.escape(row['name'])}!"


def logout() -> None:
    st.session_state.pop("auth_user", None)
    st.rerun()


def render_login_page() -> None:
    st.markdown("""
    <style>
    header[data-testid="stHeader"] { display:none !important; }
    #MainMenu, footer { display:none !important; }
    [data-testid="stAppViewContainer"] > .main { background:#0f172a; }
    </style>""", unsafe_allow_html=True)

    # Bind a CSRF nonce to this page-load so it can be verified on submit.
    _init_csrf_token()
    _page_csrf = st.session_state["_aw_csrf"]

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:16px;
                    padding:2.5rem 2rem;box-shadow:0 25px 50px rgba(0,0,0,.5)">
          <div style="width:64px;height:64px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                      border-radius:16px;display:flex;align-items:center;justify-content:center;
                      margin:0 auto 1rem;font-size:2rem">📊</div>
          <h2 style="text-align:center;color:#f1f5f9;margin:0 0 .25rem">Analytics Workbench</h2>
          <p style="text-align:center;color:#94a3b8;margin:0 0 1.5rem;font-size:.875rem">
            Sign in to your account</p>
        </div>""", unsafe_allow_html=True)

        with st.form("aw_login_form", clear_on_submit=False):
            email    = st.text_input("Email", placeholder="admin")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            # CSRF guard: token must match the one set when this page loaded.
            if not validate_csrf_token(_page_csrf):
                st.error("Session error — please refresh and try again.")
                st.stop()
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                ok, msg = login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
