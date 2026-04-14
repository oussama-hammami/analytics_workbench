"""
Admin-only log viewer for Analytics Workbench.

Renders a Streamlit page that lets Admins browse, filter, and download the
daily log files written by  admin/error_logger.py.
"""
from __future__ import annotations

import math
from typing import Optional

import streamlit as st

from .auth import require_admin
from .error_logger import get_log_files, parse_log_entries, read_log_file

# Entries shown per paginated page.
_PAGE_SIZE = 25

# ── Design tokens (mirrors dashboard.py palette) ─────────────────────────────
_CSS = """
<style>
.aw-log-entry {
    background: linear-gradient(145deg, #1e293b 0%, #162032 100%);
    border: 1px solid rgba(99,102,241,0.12);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.aw-log-entry.level-error   { border-left: 3px solid #f43f5e; }
.aw-log-entry.level-warning { border-left: 3px solid #f59e0b; }
.aw-log-entry.level-info    { border-left: 3px solid #22d3ee; }

.aw-log-ts   { font-size:.72rem; color:#475569; font-family:monospace; }
.aw-log-eid  { font-size:.75rem; font-weight:700; color:#fca5a5;
               font-family:'JetBrains Mono','Fira Code',monospace;
               background:rgba(239,68,68,.08); border-radius:4px;
               padding:1px 6px; margin-left:6px; }
.aw-log-ctx  { font-size:.78rem; color:#94a3b8; margin-top:4px; }

.aw-stat-pill {
    display:inline-block;
    background:rgba(99,102,241,.1);
    border:1px solid rgba(99,102,241,.2);
    border-radius:20px;
    padding:3px 12px;
    font-size:.72rem;
    font-weight:600;
    color:#a5b4fc;
    margin-right:6px;
}
.aw-stat-pill.red   { background:rgba(244,63,94,.1); border-color:rgba(244,63,94,.2); color:#fca5a5; }
.aw-stat-pill.amber { background:rgba(245,158,11,.1); border-color:rgba(245,158,11,.2); color:#fcd34d; }
.aw-stat-pill.green { background:rgba(52,211,153,.1); border-color:rgba(52,211,153,.2); color:#6ee7b7; }
</style>
"""

_LEVEL_ICON = {
    "ERROR":   "🔴",
    "WARNING": "🟡",
    "INFO":    "🔵",
    "DEBUG":   "⚪",
}

_LEVEL_CSS_CLASS = {
    "ERROR":   "level-error",
    "WARNING": "level-warning",
    "INFO":    "level-info",
    "DEBUG":   "level-info",
}


# ── Internal helpers ─────────────────────────────────────────────────────────

def _stat_pills(entries: list[dict]) -> str:
    total    = len(entries)
    errors   = sum(1 for e in entries if e["level"] == "ERROR")
    warnings = sum(1 for e in entries if e["level"] == "WARNING")
    infos    = total - errors - warnings
    parts = [
        f'<span class="aw-stat-pill">{total} entries</span>',
        f'<span class="aw-stat-pill red">{errors} errors</span>',
    ]
    if warnings:
        parts.append(f'<span class="aw-stat-pill amber">{warnings} warnings</span>')
    if infos > 0:
        parts.append(f'<span class="aw-stat-pill green">{infos} info</span>')
    return "".join(parts)


def _render_entry(entry: dict, idx: int) -> None:
    """Render a single log entry as a styled expander."""
    level     = entry.get("level", "ERROR")
    icon      = _LEVEL_ICON.get(level, "⚪")
    eid       = entry.get("error_id", "")
    ts        = entry.get("timestamp", "")
    ctx       = entry.get("context", "")
    tb        = entry.get("traceback", "").strip()

    # Build the expander title.
    eid_part  = f" · {eid}" if eid else ""
    ts_part   = f" · {ts}"  if ts  else ""
    title     = f"{icon} {level}{eid_part}{ts_part}"

    with st.expander(title, expanded=False):
        if ctx:
            st.markdown(f'<p class="aw-log-ctx">{ctx}</p>', unsafe_allow_html=True)
        if tb:
            st.code(tb, language="python")
        elif not ctx:
            raw = entry.get("raw", "")
            if raw:
                st.code(raw, language="text")


# ── Main renderer ─────────────────────────────────────────────────────────────

def render_log_viewer() -> None:
    """Streamlit page — admin-only error log browser."""
    require_admin()

    st.markdown(_CSS, unsafe_allow_html=True)
    st.title("📋 Error Logs")
    st.caption("Daily log files · Admins only · Stack traces never shown to end-users.")
    st.markdown("---")

    # ── File list ──────────────────────────────────────────────────────────────
    log_files = get_log_files()

    if not log_files:
        st.info("No log files found yet.  Errors will be logged here automatically.")
        return

    # Metadata table above the file selector.
    with st.expander("📁 All Log Files", expanded=False):
        rows = [
            {"Date": f["date"], "Size (KB)": f["size_kb"], "Last Modified": f["modified"]}
            for f in log_files
        ]
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── File selector ──────────────────────────────────────────────────────────
    col_sel, col_ref = st.columns([4, 1])
    with col_sel:
        selected_name = st.selectbox(
            "Select log date",
            options=[f["name"] for f in log_files],
            format_func=lambda n: n.replace(".log", ""),   # show bare date
        )
    with col_ref:
        st.write("")    # vertical alignment
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # ── Read + parse ───────────────────────────────────────────────────────────
    content = read_log_file(selected_name) if selected_name else None

    if content is None:
        st.error("Could not read the selected log file.")
        return

    if not content.strip():
        st.success("This log file is empty — no errors recorded on this date.")
        return

    entries = parse_log_entries(content)

    # ── Download button ───────────────────────────────────────────────────────
    dl_col, stat_col = st.columns([1, 3])
    with dl_col:
        st.download_button(
            label="⬇️ Download raw log",
            data=content.encode("utf-8"),
            file_name=selected_name,
            mime="text/plain",
            use_container_width=True,
        )
    with stat_col:
        if entries:
            st.markdown(_stat_pills(entries), unsafe_allow_html=True)
        else:
            st.caption("No structured entries found (raw log shown below).")

    st.markdown("---")

    if not entries:
        # Fall back to raw text display for unstructured content.
        st.subheader("Raw Log Content")
        st.code(content, language="text")
        return

    # ── Filter ────────────────────────────────────────────────────────────────
    filter_col, level_col = st.columns([3, 1])
    with filter_col:
        search = st.text_input(
            "Search",
            placeholder="Filter by Error ID, page, user, or any keyword…",
            label_visibility="collapsed",
        )
    with level_col:
        level_filter = st.selectbox(
            "Level",
            options=["All", "ERROR", "WARNING", "INFO", "DEBUG"],
            label_visibility="collapsed",
        )

    # Apply filters.
    filtered = entries
    if level_filter != "All":
        filtered = [e for e in filtered if e["level"] == level_filter]
    if search.strip():
        q = search.strip().lower()
        filtered = [e for e in filtered if q in e["raw"].lower()]

    if not filtered:
        st.info("No entries match the current filter.")
        return

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, math.ceil(len(filtered) / _PAGE_SIZE))
    page_key    = f"log_page_{selected_name}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    # Clamp in case filter reduced the count.
    st.session_state[page_key] = min(st.session_state[page_key], total_pages)
    current_page = st.session_state[page_key]

    st.caption(
        f"Showing {len(filtered)} of {len(entries)} entries · "
        f"Page {current_page} of {total_pages}"
    )

    # Pagination controls (top).
    if total_pages > 1:
        p_prev, _, p_next = st.columns([1, 6, 1])
        with p_prev:
            if st.button("← Prev", disabled=(current_page <= 1), key="log_prev_top"):
                st.session_state[page_key] -= 1
                st.rerun()
        with p_next:
            if st.button("Next →", disabled=(current_page >= total_pages), key="log_next_top"):
                st.session_state[page_key] += 1
                st.rerun()

    # Slice for current page.
    start = (current_page - 1) * _PAGE_SIZE
    page_entries = filtered[start : start + _PAGE_SIZE]

    for idx, entry in enumerate(page_entries):
        _render_entry(entry, start + idx)

    # Pagination controls (bottom).
    if total_pages > 1:
        b_prev, _, b_next = st.columns([1, 6, 1])
        with b_prev:
            if st.button("← Prev", disabled=(current_page <= 1), key="log_prev_bot"):
                st.session_state[page_key] -= 1
                st.rerun()
        with b_next:
            if st.button("Next →", disabled=(current_page >= total_pages), key="log_next_bot"):
                st.session_state[page_key] += 1
                st.rerun()
