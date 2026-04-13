"""
API Keys — Fernet-encrypted storage in SQLite.
"""
from __future__ import annotations

import base64, hashlib, os
from typing import Optional, Tuple

import streamlit as st
from .auth import require_admin, get_current_user
from .db import get_db, table, ensure_admin_schema


def _fernet():
    from cryptography.fernet import Fernet
    secret = os.getenv("APP_SECRET_KEY", "default-insecure-key-change-me")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def _decrypt(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode()).decode()


def _preview(plain: str) -> str:
    if len(plain) <= 8:
        return "•" * len(plain)
    return plain[:4] + "•" * max(4, len(plain) - 8) + plain[-4:]


def _list_keys() -> list:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"SELECT id, key_name, service, key_preview, created_by, "
                f"  strftime('%Y-%m-%d %H:%M', created_at) AS created_at "
                f"FROM {table('api_keys')} ORDER BY id ASC"
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        st.error(f"Could not load API keys: {exc}")
        return []


def _add_key(key_name: str, service: str, plain: str, user_id: int) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"INSERT INTO {table('api_keys')} "
                f"(key_name, service, key_encrypted, key_preview, created_by) "
                f"VALUES (?, ?, ?, ?, ?)",
                (key_name.strip(), service.strip(), _encrypt(plain), _preview(plain), user_id),
            )
        return None
    except Exception as exc:
        return f"Key '{key_name}' already exists." if "UNIQUE" in str(exc) else str(exc)


def _delete_key(kid: int) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(f"DELETE FROM {table('api_keys')} WHERE id=?", (kid,))
        return None
    except Exception as exc:
        return str(exc)


def _reveal_key(kid: int) -> Tuple[Optional[str], Optional[str]]:
    try:
        with get_db() as (_, cur):
            cur.execute(f"SELECT key_encrypted FROM {table('api_keys')} WHERE id=?", (kid,))
            row = cur.fetchone()
        if not row:
            return None, "Key not found."
        return _decrypt(row["key_encrypted"]), None
    except Exception as exc:
        return None, str(exc)


def render_api_keys() -> None:
    require_admin()
    ensure_admin_schema()

    user    = get_current_user()
    user_id = user["id"] if user else 0

    st.title("🔑 API Keys")
    st.caption("Store credentials for external services — encrypted with Fernet (AES-128) at rest.")
    st.info("🔐 Keys are encrypted using your `APP_SECRET_KEY`. Revealed keys are shown once only.", icon="🔒")
    st.markdown("---")

    st.subheader("Stored Keys")
    if st.button("🔄 Refresh", key="ak_refresh"):
        for k in [k for k in st.session_state if k.startswith("reveal_")]:
            del st.session_state[k]
        st.rerun()

    keys = _list_keys()
    if not keys:
        st.info("No API keys stored yet.")
    else:
        for col, lbl in zip(
            st.columns([2, 2, 3, 2, 1.5, 1.5]),
            ["Name", "Service", "Key Preview", "Added", "Reveal", "Delete"]
        ):
            col.markdown(f"**{lbl}**")
        st.divider()

        for k in keys:
            kid = k["id"]
            row = st.columns([2, 2, 3, 2, 1.5, 1.5])
            row[0].markdown(f"**{k['key_name']}**")
            row[1].text(k["service"] or "—")
            row[2].code(k["key_preview"], language=None)
            row[3].caption(k["created_at"])

            reveal_key = f"reveal_{kid}"
            if row[4].button("👁 Reveal", key=f"rev_btn_{kid}"):
                plain, err = _reveal_key(kid)
                if err: st.error(err)
                else:   st.session_state[reveal_key] = plain

            if row[5].button("🗑️ Delete", key=f"del_ak_{kid}"):
                st.session_state[f"del_ak_{kid}"] = True

            if st.session_state.get(reveal_key):
                with st.expander(f"🔓 Plaintext — {k['key_name']}", expanded=True):
                    st.warning("Copy now — disappears on next navigation.")
                    st.code(st.session_state[reveal_key], language=None)
                    if st.button("✖ Hide", key=f"hide_{kid}"):
                        del st.session_state[reveal_key]; st.rerun()

            if st.session_state.get(f"del_ak_{kid}"):
                with st.expander(f"⚠️  Delete **{k['key_name']}**?", expanded=True):
                    st.warning("This permanently removes the encrypted key.")
                    cy, cn = st.columns([1, 1])
                    if cy.button("Yes, Delete", key=f"del_ak_yes_{kid}", type="primary"):
                        err = _delete_key(kid)
                        if err: st.error(err)
                        else:
                            st.session_state.pop(f"del_ak_{kid}", None)
                            st.session_state.pop(reveal_key, None)
                            st.toast(f"Deleted '{k['key_name']}'."); st.rerun()
                    if cn.button("Cancel", key=f"del_ak_no_{kid}"):
                        st.session_state.pop(f"del_ak_{kid}", None); st.rerun()

    st.markdown("---")
    st.subheader("➕ Add New API Key")
    with st.form("add_key_form", clear_on_submit=True):
        c1, c2   = st.columns(2)
        key_name = c1.text_input("Key Name *", placeholder="openai_production")
        service  = c2.text_input("Service",    placeholder="OpenAI")
        plain    = st.text_input("API Key *", type="password",
                                 placeholder="Paste key — encrypted before saving")
        add_ok   = st.form_submit_button("🔒 Encrypt & Save", type="primary")

    if add_ok:
        errs = []
        if not key_name.strip(): errs.append("Key name is required.")
        if not plain.strip():    errs.append("API key value is required.")
        if errs:
            for e in errs: st.error(e)
        else:
            err = _add_key(key_name, service, plain, user_id)
            if err: st.error(err)
            else:
                st.success(f"Key **{key_name}** encrypted and stored.")
                st.rerun()
