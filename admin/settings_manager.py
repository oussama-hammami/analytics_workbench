"""
General Settings page — Site Name, Logo, Footer Text.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st
from .auth import require_admin
from .db import get_db, table, is_configured

_STATIC_DIR = Path(__file__).parent.parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
_ALLOWED_IMG = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

_DEFAULTS = {
    "site_name":        "Analytics Workbench",
    "site_logo":        "",
    "footer_text":      "© 2026 Analytics Workbench. All rights reserved.",
    "contact_email":    "",
    "maintenance_mode": "0",
}


def _load_settings() -> dict:
    result = dict(_DEFAULTS)
    if not is_configured():
        return result
    try:
        keys = list(_DEFAULTS.keys())
        placeholders = ",".join(["?"] * len(keys))
        with get_db() as (_, cur):
            cur.execute(
                f"SELECT setting_key, setting_value FROM {table('settings')} "
                f"WHERE setting_key IN ({placeholders})",
                keys,
            )
            for row in cur.fetchall():
                result[row["setting_key"]] = row["setting_value"] or ""
    except Exception as exc:
        st.warning(f"Could not load settings: {exc}")
    return result


def _save_setting(key: str, value: str) -> Optional[str]:
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"INSERT INTO {table('settings')} (setting_key, setting_value) VALUES (?, ?) "
                f"ON CONFLICT(setting_key) DO UPDATE SET "
                f"setting_value=excluded.setting_value, updated_at=datetime('now')",
                (key, value),
            )
        return None
    except Exception as exc:
        return str(exc)


def _save_many(updates: dict) -> list:
    return [f"{k}: {e}" for k, v in updates.items() if (e := _save_setting(k, v))]


def render_settings_manager() -> None:
    require_admin()

    st.title("⚙️ General Settings")
    st.caption("Configure site-wide settings. Changes take effect immediately.")
    st.markdown("---")

    cfg = _load_settings()

    # ── Branding ─────────────────────────────────────────────────────────────
    st.subheader("🎨 Branding")
    with st.form("branding_form"):
        site_name = st.text_input("Site / Application Name",
                                  value=cfg.get("site_name", "Analytics Workbench"))
        footer_text = st.text_area("Footer Text", value=cfg.get("footer_text", ""), height=80)
        contact_email = st.text_input("Contact Email", value=cfg.get("contact_email", ""),
                                      placeholder="support@example.com")
        st.markdown("**Site Logo**")
        logo_path = cfg.get("site_logo", "")
        if logo_path and Path(logo_path).exists():
            st.image(logo_path, width=180, caption="Current logo")
        else:
            st.caption("No logo uploaded yet.")
        logo_file = st.file_uploader("Upload new logo", type=list(_ALLOWED_IMG))
        saved = st.form_submit_button("💾 Save Branding", type="primary")

    if saved:
        updates = {
            "site_name":     site_name.strip(),
            "footer_text":   footer_text.strip(),
            "contact_email": contact_email.strip(),
        }
        if logo_file:
            ext = logo_file.name.rsplit(".", 1)[-1].lower()
            if ext not in _ALLOWED_IMG:
                st.error(f"Unsupported image type: .{ext}")
            elif logo_file.size > 2 * 1024 * 1024:
                st.error("Logo must be ≤ 2 MB.")
            else:
                dest = _STATIC_DIR / f"logo.{ext}"
                dest.write_bytes(logo_file.read())
                updates["site_logo"] = str(dest)
                st.toast("Logo uploaded.")
        errs = _save_many(updates)
        if errs:
            for e in errs: st.error(e)
        else:
            st.success("Branding settings saved.")
            st.rerun()

    st.markdown("---")

    # ── Application ───────────────────────────────────────────────────────────
    st.subheader("🛠️  Application")
    with st.form("app_form"):
        maintenance = st.toggle("Maintenance Mode",
                                value=(cfg.get("maintenance_mode", "0") == "1"),
                                help="Only admins can access the platform when enabled.")
        save_app = st.form_submit_button("💾 Save", type="primary")

    if save_app:
        err = _save_setting("maintenance_mode", "1" if maintenance else "0")
        if err: st.error(err)
        else:
            st.success("Saved.")
            if maintenance:
                st.warning("⚠️ Maintenance mode is ON.")

    st.markdown("---")

    # ── .env inspector ────────────────────────────────────────────────────────
    st.subheader("📄 Environment File (.env)")
    env_path = next(
        (p for p in (
            Path(__file__).parent.parent / ".env",
            Path(__file__).parent.parent / "app.env",
        ) if p.is_file()),
        None,
    )
    if env_path:
        masked = []
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                if any(s in k.upper() for s in ("PASSWORD", "SECRET", "KEY", "TOKEN")) and v.strip():
                    masked.append(f"{k}=••••••••••••")
                else:
                    masked.append(line)
            else:
                masked.append(line)
        st.code("\n".join(masked), language="ini")
    else:
        st.info("No .env file found. Copy .env.example to .env and fill in your values.")
