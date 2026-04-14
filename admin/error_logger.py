"""
Production error logging for Analytics Workbench.

Writes one log file per calendar day to  logs/YYYY-MM-DD.log
(or the directory set by the LOG_DIR environment variable).

Public API
----------
generate_error_id()                     → "ERR-{8 uppercase hex chars}"
log_exception(exc, error_id, **ctx)     → append full traceback to today's log
get_log_files()                         → list of log-file metadata dicts (newest first)
read_log_file(filename)                 → safe contents of one log file (None on error)
parse_log_entries(content)              → list of structured entry dicts
render_error_page(error_id, tb_str)     → Streamlit production-safe error page
"""
from __future__ import annotations

import logging
import os
import re
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Directory resolution ──────────────────────────────────────────────────────

def _log_dir() -> Path:
    val = os.getenv("LOG_DIR", "").strip()
    return Path(val) if val else Path(__file__).parent.parent / "logs"


# ── Logger cache (one logger per calendar date) ───────────────────────────────

_loggers: dict[str, logging.Logger] = {}
_LOG_ENTRY_SEP = "---END---"


def _get_logger() -> logging.Logger:
    """Return a date-scoped logger, switching files automatically at midnight."""
    today = datetime.now().strftime("%Y-%m-%d")

    if today in _loggers:
        return _loggers[today]

    # Close and evict any logger for a previous date.
    for stale_key in list(_loggers):
        stale = _loggers.pop(stale_key)
        for h in stale.handlers[:]:
            h.close()
            stale.removeHandler(h)

    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"aw.{today}")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(
        str(log_dir / f"{today}.log"),
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)

    _loggers[today] = logger
    return logger


# ── Public helpers ────────────────────────────────────────────────────────────

def generate_error_id() -> str:
    """Return a short, human-readable error token like  ERR-3F9A1C2B."""
    return "ERR-" + uuid.uuid4().hex[:8].upper()


def log_exception(
    exc: Exception,
    error_id: str,
    page: Optional[str] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    tb_str: Optional[str] = None,
) -> None:
    """Append a structured error entry to today's log file.

    *tb_str* should be ``traceback.format_exc()`` captured at the call site.
    If omitted we attempt to format the live exception context.
    """
    if tb_str is None:
        tb_str = traceback.format_exc()

    ctx_parts: list[str] = [f"Error ID: {error_id}"]
    if page:       ctx_parts.append(f"Page: {page}")
    if user_email: ctx_parts.append(f"User: {user_email}")
    if user_role:  ctx_parts.append(f"Role: {user_role}")
    ctx_line = " | ".join(ctx_parts)

    try:
        logger = _get_logger()
        # Emit a single log record whose message contains the full structured block.
        logger.error(
            "\n%s\n%s\n%s",
            ctx_line,
            tb_str.rstrip(),
            _LOG_ENTRY_SEP,
        )
        # Flush immediately so entries are visible even if the process crashes.
        for h in logger.handlers:
            h.flush()
    except Exception:
        # Logging must never itself crash the application.
        pass


def get_log_files() -> list[dict]:
    """Return log-file metadata sorted newest-first.

    Each dict has keys: ``name``, ``date``, ``size_kb``, ``modified``.
    """
    ld = _log_dir()
    if not ld.exists():
        return []

    results: list[dict] = []
    for path in sorted(ld.glob("*.log"), reverse=True):
        try:
            stat = path.stat()
            results.append(
                {
                    "name":     path.name,
                    "date":     path.stem,          # "YYYY-MM-DD"
                    "size_kb":  round(stat.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )
        except OSError:
            pass
    return results


def read_log_file(filename: str) -> Optional[str]:
    """Safely read a log file by bare name (no path traversal allowed).

    Returns ``None`` if the file does not exist or is not a ``.log`` file.
    """
    safe_name = Path(filename).name          # strip any directory component
    if not safe_name.endswith(".log"):
        return None

    target = _log_dir() / safe_name
    # Resolve to guard against symlink escapes.
    try:
        resolved = target.resolve()
        log_dir_resolved = _log_dir().resolve()
        if not str(resolved).startswith(str(log_dir_resolved)):
            return None                      # path-traversal attempt
        return resolved.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None


def parse_log_entries(content: str) -> list[dict]:
    """Parse a log file's text content into a list of structured entry dicts.

    Each dict contains:
        ``timestamp``, ``level``, ``error_id``, ``context``, ``traceback``, ``raw``
    Entries are returned newest-first (the list is reversed from file order).
    """
    raw_blocks = content.split(_LOG_ENTRY_SEP)
    entries: list[dict] = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        entry: dict = {
            "timestamp": "",
            "level":     "ERROR",
            "error_id":  "",
            "context":   "",
            "traceback": "",
            "raw":       block,
        }

        lines = block.splitlines()

        # Line 0 pattern: [2024-01-15 14:32:05] [ERROR] [aw.2024-01-15]
        if lines:
            m = re.match(
                r"\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+"
                r"\[(?P<lvl>\w+)\]",
                lines[0],
            )
            if m:
                entry["timestamp"] = m.group("ts")
                entry["level"]     = m.group("lvl")

        # Line 1: "Error ID: ERR-XXXX | Page: ... | User: ..."
        if len(lines) > 1:
            ctx = lines[1]
            entry["context"] = ctx
            eid_m = re.search(r"Error ID:\s+(ERR-[A-F0-9]+)", ctx)
            if eid_m:
                entry["error_id"] = eid_m.group(1)

        # Remaining lines: traceback
        if len(lines) > 2:
            entry["traceback"] = "\n".join(lines[2:])

        entries.append(entry)

    entries.reverse()   # newest first
    return entries


# ── Production error page (Streamlit) ────────────────────────────────────────

_ERROR_CSS = """
<style>
.aw-err-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 20px 40px;
}
.aw-err-card {
    background: linear-gradient(145deg, #1e293b, #162032);
    border: 1px solid rgba(239,68,68,.25);
    border-radius: 20px;
    padding: 3rem 3.5rem;
    max-width: 560px;
    width: 100%;
    text-align: center;
    box-shadow: 0 25px 60px rgba(0,0,0,.5);
}
.aw-err-icon  { font-size: 3.5rem; margin-bottom: 1rem; }
.aw-err-title { font-size: 1.6rem; font-weight: 700; color: #f1f5f9; margin: 0 0 .5rem; }
.aw-err-sub   { font-size: .9rem; color: #94a3b8; margin: 0 0 2rem; }
.aw-err-id-label { font-size: .7rem; font-weight: 600; letter-spacing: .08em;
                   text-transform: uppercase; color: #64748b; margin-bottom: .35rem; }
.aw-err-id-box  {
    display: inline-block;
    background: rgba(239,68,68,.08);
    border: 1px solid rgba(239,68,68,.2);
    border-radius: 8px;
    padding: .45rem 1.2rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 1.05rem;
    font-weight: 600;
    color: #fca5a5;
    letter-spacing: .06em;
    margin-bottom: 1.5rem;
    user-select: all;
}
.aw-err-hint { font-size: .78rem; color: #475569; margin: 0; }
</style>
"""


def render_error_page(error_id: str, tb_str: Optional[str] = None) -> None:
    """Render a production-safe error page in the current Streamlit context.

    *tb_str* — the formatted traceback string.  When provided (admins only)
    it is shown in a collapsed debug expander.  Never shown to end-users.
    """
    import streamlit as st  # imported here so the module is usable without Streamlit

    st.markdown(_ERROR_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="aw-err-wrap">
          <div class="aw-err-card">
            <div class="aw-err-icon">⚠️</div>
            <h2 class="aw-err-title">Something went wrong</h2>
            <p class="aw-err-sub">
              An unexpected error occurred while processing your request.<br>
              Our team has been notified automatically.
            </p>
            <p class="aw-err-id-label">Error Reference</p>
            <div class="aw-err-id-box">{error_id}</div>
            <p class="aw-err-hint">
              Please quote this ID when contacting support.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if tb_str:
        with st.expander("🔧 Debug Details  (visible to Admins only)"):
            st.code(tb_str, language="python")
