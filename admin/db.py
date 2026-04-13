"""
Database layer — SQLite backend.

No server, no credentials, no sudo required.
The database file lives at  data/analytics_workbench.db  next to app.py.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Tuple

# ── Load .env / app.env if present ───────────────────────────────────────────
try:
    from dotenv import load_dotenv
    _root = Path(__file__).parent.parent
    for _candidate in (_root / ".env", _root / "app.env"):
        if _candidate.is_file():
            load_dotenv(_candidate, override=False)
            break
except ImportError:
    pass

# ── DB file path (override via DB_PATH env-var if needed) ─────────────────────
_DEFAULT_DB = Path(__file__).parent.parent / "data" / "analytics_workbench.db"


def _db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(_DEFAULT_DB)))


# ── Public helpers ────────────────────────────────────────────────────────────

def table(name: str) -> str:
    """Return a quoted, prefixed table name.  table('users') → '"aw_users"' """
    prefix = os.getenv("DB_PREFIX", "aw_")
    return f'"{prefix}{name}"'


def is_configured() -> bool:
    """SQLite is always available — True as long as the data dir is writable."""
    try:
        _db_path().parent.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


@contextmanager
def get_db() -> Generator[Tuple, None, None]:
    """Yield (conn, cursor).  Commits on success, rolls back on exception.

    Rows are returned as sqlite3.Row objects (support both dict and index access).
    """
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_admin_schema() -> None:
    """Create all admin tables (idempotent)."""
    p = os.getenv("DB_PREFIX", "aw_")
    with get_db() as (conn, _):
        conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS "{p}users" (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                email      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password   TEXT    NOT NULL,
                role       TEXT    NOT NULL DEFAULT 'viewer'
                           CHECK(role IN ('superadmin','admin','viewer')),
                is_active  INTEGER NOT NULL DEFAULT 1,
                last_login TEXT,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS "{p}settings" (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key   TEXT    NOT NULL UNIQUE,
                setting_value TEXT,
                autoload      INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS "{p}api_keys" (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name      TEXT    NOT NULL UNIQUE,
                service       TEXT    NOT NULL DEFAULT '',
                key_encrypted TEXT    NOT NULL,
                key_preview   TEXT    NOT NULL,
                created_by    INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            INSERT OR IGNORE INTO "{p}settings" (setting_key, setting_value) VALUES
                ('app_version',      '1.0.0'),
                ('install_date',     datetime('now')),
                ('max_upload_mb',    '50'),
                ('maintenance_mode', '0'),
                ('allow_registration','0');
        """)


def seed_superadmin() -> None:
    """Insert a default superadmin if none exists yet.

    Credentials are read from the ADMIN_EMAIL and ADMIN_PASSWORD environment
    variables (set in .env).  This function is a no-op after the first run.
    """
    email    = os.getenv("ADMIN_EMAIL", "admin")
    password = os.getenv("ADMIN_PASSWORD", "")

    if not password:
        return  # refuse to seed an account with no password

    p = os.getenv("DB_PREFIX", "aw_")
    with get_db() as (_, cur):
        cur.execute(f'SELECT COUNT(*) FROM "{p}users" WHERE role="superadmin"')
        if cur.fetchone()[0] > 0:
            return                          # already exists — skip

    try:
        import bcrypt
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
        with get_db() as (_, cur):
            cur.execute(
                f'INSERT OR IGNORE INTO "{p}users" (name, email, password, role) '
                f'VALUES (?, ?, ?, "superadmin")',
                ("Admin", email, hashed),
            )
    except ImportError:
        pass   # bcrypt not installed yet — login will fail gracefully
