"""
User Management page — full CRUD + Active/Inactive toggles.
"""
from __future__ import annotations

import re
from typing import Optional

import streamlit as st
from .auth import require_admin, _hash_password, get_current_user, ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_VIEWER
from .db import get_db, table

_ROLES = [ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_VIEWER]
_ROLE_BADGE = {
    ROLE_SUPERADMIN: "🔴 Superadmin",
    ROLE_ADMIN:      "🟡 Admin",
    ROLE_VIEWER:     "🟢 Viewer",
}


def _valid_email(v: str) -> bool:
    return bool(v.strip())   # email field doubles as username — just non-empty


def _fetch_users() -> list:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"SELECT id, name, email, role, is_active, "
                f"  strftime('%Y-%m-%d', created_at) AS created_at, "
                f"  strftime('%Y-%m-%d %H:%M', last_login) AS last_login "
                f"FROM {table('users')} ORDER BY id ASC"
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        st.error(f"Could not load users: {exc}")
        return []


def _create_user(name: str, email: str, password: str, role: str) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"INSERT INTO {table('users')} (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name.strip(), email.strip(), _hash_password(password), role),
            )
        return None
    except Exception as exc:
        return "A user with that email already exists." if "UNIQUE" in str(exc) else str(exc)


def _update_user(uid: int, name: str, email: str, role: str) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"UPDATE {table('users')} SET name=?, email=?, role=?, "
                f"updated_at=datetime('now') WHERE id=?",
                (name.strip(), email.strip(), role, uid),
            )
        return None
    except Exception as exc:
        return str(exc)


def _reset_password(uid: int, new_pw: str) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"UPDATE {table('users')} SET password=?, updated_at=datetime('now') WHERE id=?",
                (_hash_password(new_pw), uid),
            )
        return None
    except Exception as exc:
        return str(exc)


def _toggle_active(uid: int, state: int) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"UPDATE {table('users')} SET is_active=?, updated_at=datetime('now') WHERE id=?",
                (state, uid),
            )
        return None
    except Exception as exc:
        return str(exc)


def _delete_user(uid: int) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(f"DELETE FROM {table('users')} WHERE id=?", (uid,))
        return None
    except Exception as exc:
        return str(exc)


def render_user_management() -> None:
    require_admin()
    current_user  = get_current_user()
    is_superadmin = current_user and current_user["role"] == ROLE_SUPERADMIN

    st.title("👥 User Management")
    st.caption("Create, edit, toggle status, and delete platform users.")
    st.markdown("---")

    if st.button("🔄 Refresh", key="um_refresh"):
        st.rerun()

    users = _fetch_users()

    total  = len(users)
    active = sum(1 for u in users if u["is_active"])
    admins = sum(1 for u in users if u["role"] in (ROLE_SUPERADMIN, ROLE_ADMIN))
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Users", total)
    c2.metric("Active",      active)
    c3.metric("Admins",      admins)
    st.markdown("---")

    st.subheader("All Users")
    if not users:
        st.info("No users found.")
    else:
        hdr = st.columns([2, 3, 2, 1.5, 1.5, 1.5, 1.5])
        for col, lbl in zip(hdr, ["Name", "Email", "Role", "Status", "Toggle", "Edit", "Delete"]):
            col.markdown(f"**{lbl}**")
        st.divider()

        for user in users:
            uid     = user["id"]
            is_self = current_user and uid == current_user["id"]
            row     = st.columns([2, 3, 2, 1.5, 1.5, 1.5, 1.5])

            row[0].markdown(f"**{user['name']}**")
            row[1].text(user["email"])
            row[2].markdown(_ROLE_BADGE.get(user["role"], user["role"]))
            if user["is_active"]: row[3].success("Active")
            else:                 row[3].error("Inactive")

            if not is_self:
                new_state = 0 if user["is_active"] else 1
                label = "Deactivate" if user["is_active"] else "Activate"
                if row[4].button(label, key=f"tog_{uid}"):
                    err = _toggle_active(uid, new_state)
                    if err: st.error(err)
                    else:
                        st.toast(f"{'Deactivated' if not new_state else 'Activated'} {user['name']}")
                        st.rerun()
            else:
                row[4].caption("(you)")

            if row[5].button("✏️ Edit", key=f"edit_btn_{uid}"):
                st.session_state[f"edit_open_{uid}"] = True

            if is_superadmin and not is_self:
                if row[6].button("🗑️ Delete", key=f"del_btn_{uid}"):
                    st.session_state[f"del_confirm_{uid}"] = True
            else:
                row[6].caption("—")

            # ── Inline edit ─────────────────────────────────────────────────
            if st.session_state.get(f"edit_open_{uid}"):
                with st.expander(f"✏️  Editing: {user['name']}", expanded=True):
                    with st.form(key=f"edit_form_{uid}"):
                        e_name  = st.text_input("Name",  value=user["name"])
                        e_email = st.text_input("Email", value=user["email"])
                        e_role  = st.selectbox("Role", _ROLES,
                                               index=_ROLES.index(user["role"]) if user["role"] in _ROLES else 2,
                                               disabled=not is_superadmin)
                        st.markdown("**Reset Password** *(blank = keep current)*")
                        new_pw  = st.text_input("New Password",     type="password")
                        new_pw2 = st.text_input("Confirm Password", type="password")
                        save   = st.columns([1,1,4])[0].form_submit_button("💾 Save",   type="primary")
                        cancel = st.columns([1,1,4])[1].form_submit_button("✖ Cancel")

                    if save:
                        errs = []
                        if not e_name.strip(): errs.append("Name cannot be empty.")
                        if not _valid_email(e_email): errs.append("Email cannot be empty.")
                        if new_pw and new_pw != new_pw2: errs.append("Passwords do not match.")
                        if new_pw and len(new_pw) < 8:   errs.append("Password must be ≥ 8 chars.")
                        if errs:
                            for e in errs: st.error(e)
                        else:
                            err = _update_user(uid, e_name, e_email, e_role)
                            if err: st.error(err)
                            else:
                                if new_pw: _reset_password(uid, new_pw)
                                st.session_state.pop(f"edit_open_{uid}", None)
                                st.toast(f"User {e_name} updated.")
                                st.rerun()
                    if cancel:
                        st.session_state.pop(f"edit_open_{uid}", None)
                        st.rerun()

            # ── Delete confirm ───────────────────────────────────────────────
            if st.session_state.get(f"del_confirm_{uid}"):
                with st.expander(f"⚠️  Delete {user['name']}?", expanded=True):
                    st.warning("This cannot be undone.")
                    cy, cn = st.columns([1, 1])
                    if cy.button("Yes, Delete", key=f"del_yes_{uid}", type="primary"):
                        err = _delete_user(uid)
                        if err: st.error(err)
                        else:
                            st.session_state.pop(f"del_confirm_{uid}", None)
                            st.toast(f"Deleted {user['name']}.")
                            st.rerun()
                    if cn.button("Cancel", key=f"del_no_{uid}"):
                        st.session_state.pop(f"del_confirm_{uid}", None)
                        st.rerun()

    # ── Create New User ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("➕ Create New User")
    with st.form("create_user_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n_name  = c1.text_input("Full Name",  placeholder="Jane Smith")
        n_email = c2.text_input("Email / Username", placeholder="jane@example.com")
        c3, c4  = st.columns(2)
        n_pw    = c3.text_input("Password", type="password")
        n_pw2   = c4.text_input("Confirm Password", type="password")
        n_role  = st.selectbox("Role", _ROLES if is_superadmin else [ROLE_ADMIN, ROLE_VIEWER], index=2)
        submitted = st.form_submit_button("Create User", type="primary")

    if submitted:
        errs = []
        if not n_name.strip():       errs.append("Name is required.")
        if not _valid_email(n_email): errs.append("Email/username is required.")
        if len(n_pw) < 8:            errs.append("Password must be at least 8 characters.")
        if n_pw != n_pw2:            errs.append("Passwords do not match.")
        if errs:
            for e in errs: st.error(e)
        else:
            err = _create_user(n_name, n_email, n_pw, n_role)
            if err: st.error(err)
            else:
                st.success(f"User **{n_name}** created.")
                st.rerun()
