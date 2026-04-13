#!/usr/bin/env bash
# =============================================================================
#  Analytics Workbench — Setup & Launch Script
#  Usage:
#    chmod +x setup.sh && ./setup.sh          # full interactive setup
#    ./setup.sh --run-only                    # skip setup, just launch
#    ./setup.sh --reset-admin                 # create/replace superadmin only
# =============================================================================

# Safer flags: exit on unset vars, but NOT on every non-zero command
# (we handle errors explicitly below)
set -uo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }
header()  { echo -e "\n${BOLD}${CYAN}$*${RESET}"; echo "────────────────────────────────────────"; }
step_skip() { echo -e "${YELLOW}[SKIP]${RESET}  $*"; }

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.env"
PYTHON="$VENV_DIR/bin/python3"
PIP="$VENV_DIR/bin/pip"
STREAMLIT="$VENV_DIR/bin/streamlit"
APP_ENV="$SCRIPT_DIR/app.env"
ENV_EXAMPLE="$SCRIPT_DIR/app.env.example"

cd "$SCRIPT_DIR"

# ── Flags ─────────────────────────────────────────────────────────────────────
MODE="${1:-setup}"   # setup | --run-only | --reset-admin

# ── Helper: load app.env into current shell ───────────────────────────────────
load_env() {
    if [[ -f "$APP_ENV" ]]; then
        # Export each non-comment, non-empty line
        set -a
        # shellcheck disable=SC1090
        source "$APP_ENV"
        set +a
    fi
}

# ── Helper: find a free port starting at $1 ──────────────────────────────────
find_free_port() {
    local port="${1:-8501}"
    while lsof -i :"$port" &>/dev/null 2>&1; do
        port=$((port + 1))
    done
    echo "$port"
}

# ── Helper: kill any Streamlit already bound to a port ───────────────────────
kill_streamlit_on_port() {
    local port="$1"
    local pid
    pid=$(lsof -ti :"$port" 2>/dev/null | head -1 || true)
    if [[ -n "$pid" ]]; then
        local cmd
        cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        if [[ "$cmd" == *"streamlit"* ]] || [[ "$cmd" == *"python"* ]]; then
            warn "Killing existing Streamlit process on port $port (PID $pid)…"
            kill "$pid" 2>/dev/null || true
            sleep 1
            return 0
        else
            warn "Port $port is used by '$cmd' (PID $pid) — not a Streamlit process."
            return 1
        fi
    fi
    return 0
}

# ── Helper: check if MySQL is reachable ──────────────────────────────────────
mysql_reachable() {
    local host="${DB_HOST:-localhost}"
    local port="${DB_PORT:-3306}"
    local user="${DB_USERNAME:-root}"
    local pass="${DB_PASSWORD:-}"
    local db="${DB_DATABASE:-}"
    mysql -h"$host" -P"$port" -u"$user" ${pass:+-p"$pass"} \
          -e "SELECT 1;" "$db" &>/dev/null 2>&1
}

# ── Helper: try to start MySQL/MariaDB service ────────────────────────────────
try_start_mysql() {
    for svc in mysql mariadb mysqld; do
        if systemctl list-units --type=service 2>/dev/null | grep -q "$svc"; then
            info "Attempting to start $svc service…"
            if sudo systemctl start "$svc" 2>/dev/null; then
                sleep 2
                success "$svc started."
                return 0
            fi
        fi
    done
    return 1
}

# =============================================================================
#  --run-only: skip all setup, just launch
# =============================================================================
if [[ "$MODE" == "--run-only" ]]; then
    load_env
    header "Launching Analytics Workbench (--run-only)"
    STREAMLIT_PORT="${STREAMLIT_SERVER_PORT:-8501}"

    if lsof -i :"$STREAMLIT_PORT" &>/dev/null 2>&1; then
        warn "Port $STREAMLIT_PORT is occupied."
        read -rp "  Kill existing process and restart? [Y/n]: " KILL_CHOICE
        if [[ "${KILL_CHOICE:-Y}" =~ ^[Yy]$ ]]; then
            kill_streamlit_on_port "$STREAMLIT_PORT" || STREAMLIT_PORT=$(find_free_port $((STREAMLIT_PORT+1)))
        else
            STREAMLIT_PORT=$(find_free_port $((STREAMLIT_PORT+1)))
            info "Using port $STREAMLIT_PORT instead."
        fi
    fi

    info "Starting on http://localhost:${STREAMLIT_PORT}"
    exec "$STREAMLIT" run app.py --server.port "$STREAMLIT_PORT"
fi

# =============================================================================
#  --reset-admin: only recreate the superadmin account
# =============================================================================
if [[ "$MODE" == "--reset-admin" ]]; then
    load_env
    header "Reset Superadmin Account"

    if ! command -v mysql &>/dev/null; then
        error "mysql CLI not found. Install it and try again."
    fi

    read -rp "  Admin Name   : " ADMIN_NAME
    read -rp "  Admin Email  : " ADMIN_EMAIL
    while true; do
        read -srp " Admin Password (min 8 chars): " ADMIN_PASS; echo ""
        read -srp " Confirm Password            : " ADMIN_PASS2; echo ""
        [[ "$ADMIN_PASS" == "$ADMIN_PASS2" && ${#ADMIN_PASS} -ge 8 ]] && break
        warn "Passwords do not match or are too short. Try again."
    done

    HASHED=$("$PYTHON" -c "
import bcrypt, sys
print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt(12)).decode())
" "$ADMIN_PASS")

    PREFIX="${DB_PREFIX:-aw_}"
    mysql -h"${DB_HOST:-localhost}" -P"${DB_PORT:-3306}" \
          -u"${DB_USERNAME:-root}" ${DB_PASSWORD:+-p"${DB_PASSWORD}"} \
          "${DB_DATABASE}" <<SQL
INSERT INTO \`${PREFIX}users\` (name, email, password, role)
VALUES ('${ADMIN_NAME}', '${ADMIN_EMAIL}', '${HASHED}', 'superadmin')
ON DUPLICATE KEY UPDATE
    name     = VALUES(name),
    password = VALUES(password),
    role     = 'superadmin',
    is_active = 1;
SQL
    success "Superadmin '${ADMIN_EMAIL}' saved."
    exit 0
fi

# =============================================================================
#  FULL SETUP
# =============================================================================

header "Analytics Workbench — Setup"
echo -e "  ${CYAN}Project:${RESET} $SCRIPT_DIR"
echo -e "  ${CYAN}Mode:${RESET}    Full interactive setup"

# =============================================================================
#  STEP 0 — Preflight
# =============================================================================
header "STEP 0 · Preflight checks"

# Python
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Please install Python 3.8+."
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [[ "$PY_MAJOR" -lt 3 || ("$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 8) ]]; then
    error "Python 3.8+ required. Found $PY_VER."
fi
success "Python $PY_VER"

# MySQL CLI
MYSQL_AVAILABLE=false
if command -v mysql &>/dev/null; then
    success "MySQL CLI found: $(mysql --version 2>&1 | head -1)"
    MYSQL_AVAILABLE=true
else
    warn "MySQL CLI not found."
    echo "       Install it with one of:"
    echo "         sudo apt install mysql-client     # Ubuntu/Debian"
    echo "         sudo dnf install mysql            # Fedora/RHEL"
    echo "         brew install mysql-client         # macOS"
    echo "       DB setup steps will be skipped — you can run them later."
fi

# Venv
if [[ ! -x "$PYTHON" ]]; then
    info "Creating virtual environment at .env/ …"
    python3 -m venv "$VENV_DIR" || error "Failed to create virtual environment."
    success "Virtual environment created."
else
    success "Virtual environment found at .env/"
fi

# =============================================================================
#  STEP 1 — Install Python dependencies
# =============================================================================
header "STEP 1 · Python dependencies"

info "Upgrading pip…"
"$PIP" install --quiet --upgrade pip || warn "pip upgrade failed (non-fatal)."

info "Installing from requirements.txt…"
if "$PIP" install -r "$SCRIPT_DIR/requirements.txt"; then
    success "All packages installed."
else
    error "pip install failed. Check the output above."
fi

# =============================================================================
#  STEP 2 — Configure app.env
# =============================================================================
header "STEP 2 · Environment configuration"

if [[ -f "$APP_ENV" ]]; then
    step_skip "app.env already exists."
    warn "To reconfigure, delete app.env and re-run this script."
    load_env
else
    [[ -f "$ENV_EXAMPLE" ]] || error "app.env.example not found."

    echo ""
    echo -e "${BOLD}MySQL connection details${RESET}  (Enter = use default)"
    echo ""

    read -rp "  DB Host     [localhost]           : " DB_HOST;     DB_HOST="${DB_HOST:-localhost}"
    read -rp "  DB Port     [3306]                : " DB_PORT;     DB_PORT="${DB_PORT:-3306}"
    read -rp "  DB Name     [analytics_workbench] : " DB_DATABASE; DB_DATABASE="${DB_DATABASE:-analytics_workbench}"
    read -rp "  DB Username [root]                : " DB_USERNAME; DB_USERNAME="${DB_USERNAME:-root}"
    read -srp " DB Password                       : " DB_PASSWORD; echo ""; DB_PASSWORD="${DB_PASSWORD:-}"
    read -rp "  Table Prefix [aw_]                : " DB_PREFIX;   DB_PREFIX="${DB_PREFIX:-aw_}"
    read -rp "  App URL [http://localhost]         : " APP_URL;     APP_URL="${APP_URL:-http://localhost}"

    APP_SECRET_KEY=$("$PYTHON" -c "import secrets; print(secrets.token_hex(32))")

    cat > "$APP_ENV" <<EOF
# Analytics Workbench — Environment Configuration
# Generated by setup.sh on $(date '+%Y-%m-%d %H:%M:%S')
# Keep this file secret. Do NOT commit it to version control.

APP_NAME="Analytics Workbench"
APP_ENV=production
APP_DEBUG=false
APP_URL=${APP_URL}
APP_SECRET_KEY=${APP_SECRET_KEY}

DB_CONNECTION=mysql
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_DATABASE=${DB_DATABASE}
DB_USERNAME=${DB_USERNAME}
DB_PASSWORD=${DB_PASSWORD}
DB_PREFIX=${DB_PREFIX}

STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
EOF

    load_env
    success "app.env written."
fi

# =============================================================================
#  STEP 3 — MySQL: start service, create DB, run migrations
# =============================================================================
header "STEP 3 · Database setup"

if [[ "$MYSQL_AVAILABLE" == "false" ]]; then
    step_skip "MySQL CLI not available — skipping DB setup."
    echo "       Run the following after installing the MySQL CLI:"
    echo "         mysql -u root -p -e \"CREATE DATABASE IF NOT EXISTS \`${DB_DATABASE:-analytics_workbench}\`;\""
    echo "         mysql -u root -p ${DB_DATABASE:-analytics_workbench} < install/install.sql"
else
    # Try to reach MySQL; if it fails, try starting the service
    if ! mysql_reachable; then
        warn "MySQL is not reachable. Attempting to start the service…"
        if try_start_mysql; then
            mysql_reachable || error "MySQL started but connection still failed. Check credentials in app.env."
        else
            warn "Could not start MySQL automatically."
            echo ""
            echo "  Start it manually with:"
            echo "    sudo systemctl start mysql   # or: sudo service mysql start"
            echo "  Then re-run:  ./setup.sh --run-only"
            echo ""
            MYSQL_AVAILABLE=false
        fi
    fi

    if [[ "$MYSQL_AVAILABLE" == "true" ]]; then
        MYSQL_CMD="mysql -h${DB_HOST:-localhost} -P${DB_PORT:-3306} -u${DB_USERNAME:-root}"
        [[ -n "${DB_PASSWORD:-}" ]] && MYSQL_CMD="$MYSQL_CMD -p${DB_PASSWORD}"

        info "Creating database '${DB_DATABASE:-analytics_workbench}' if not exists…"
        if $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS \`${DB_DATABASE:-analytics_workbench}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null; then
            success "Database ready."
        else
            warn "Could not create database (may already exist — continuing)."
        fi

        info "Applying schema (install/install.sql)…"
        if $MYSQL_CMD "${DB_DATABASE:-analytics_workbench}" < "$SCRIPT_DIR/install/install.sql" 2>/dev/null; then
            success "Schema applied."
        else
            warn "Schema migration skipped (tables may already exist)."
        fi
    fi
fi

# =============================================================================
#  STEP 4 — Create superadmin
# =============================================================================
header "STEP 4 · Superadmin account"

ADMIN_EMAIL="${ADMIN_EMAIL:-}"   # may already be set from app.env

if [[ "$MYSQL_AVAILABLE" == "false" ]]; then
    step_skip "MySQL not available — skipping admin account creation."
    echo "       Run  ./setup.sh --reset-admin  after MySQL is set up."
else
    # Check for existing superadmin
    EXISTING=0
    EXISTING=$(mysql -h"${DB_HOST:-localhost}" -P"${DB_PORT:-3306}" \
        -u"${DB_USERNAME:-root}" ${DB_PASSWORD:+-p"${DB_PASSWORD}"} \
        "${DB_DATABASE:-analytics_workbench}" -sNe \
        "SELECT COUNT(*) FROM \`${DB_PREFIX:-aw_}users\` WHERE role='superadmin';" \
        2>/dev/null || echo "0")

    if [[ "$EXISTING" -gt 0 ]]; then
        success "Superadmin already exists — skipping."
        # Fetch the email for display later
        ADMIN_EMAIL=$(mysql -h"${DB_HOST:-localhost}" -P"${DB_PORT:-3306}" \
            -u"${DB_USERNAME:-root}" ${DB_PASSWORD:+-p"${DB_PASSWORD}"} \
            "${DB_DATABASE:-analytics_workbench}" -sNe \
            "SELECT email FROM \`${DB_PREFIX:-aw_}users\` WHERE role='superadmin' LIMIT 1;" \
            2>/dev/null || echo "see app.env")
    else
        echo ""
        echo -e "${BOLD}Create your superadmin account${RESET}"
        echo ""
        read -rp "  Name           : " ADMIN_NAME;  ADMIN_NAME="${ADMIN_NAME:-Admin}"
        read -rp "  Email          : " ADMIN_EMAIL; ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"

        while true; do
            read -srp " Password (min 8 chars): " ADMIN_PASS;  echo ""
            read -srp " Confirm Password       : " ADMIN_PASS2; echo ""
            if [[ "$ADMIN_PASS" == "$ADMIN_PASS2" && ${#ADMIN_PASS} -ge 8 ]]; then
                break
            fi
            warn "Passwords do not match or are too short. Try again."
        done

        HASHED=$("$PYTHON" -c "
import bcrypt, sys
print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt(12)).decode())
" "$ADMIN_PASS")

        if mysql -h"${DB_HOST:-localhost}" -P"${DB_PORT:-3306}" \
               -u"${DB_USERNAME:-root}" ${DB_PASSWORD:+-p"${DB_PASSWORD}"} \
               "${DB_DATABASE:-analytics_workbench}" \
               -e "INSERT IGNORE INTO \`${DB_PREFIX:-aw_}users\`
                   (name, email, password, role)
                   VALUES ('${ADMIN_NAME}', '${ADMIN_EMAIL}', '${HASHED}', 'superadmin');" \
               2>/dev/null; then
            success "Superadmin '${ADMIN_EMAIL}' created."
        else
            error "Failed to create superadmin. Check your MySQL credentials."
        fi
    fi
fi

# =============================================================================
#  STEP 5 — Launch
# =============================================================================
header "STEP 5 · Launch"
success "Setup complete!"

echo ""
echo -e "  ${BOLD}Admin email :${RESET} ${ADMIN_EMAIL:-run ./setup.sh --reset-admin after MySQL setup}"
echo -e "  ${BOLD}App URL     :${RESET} http://localhost:8501"
echo ""

# Handle port conflicts
STREAMLIT_PORT="${STREAMLIT_SERVER_PORT:-8501}"
if lsof -i :"$STREAMLIT_PORT" &>/dev/null 2>&1; then
    warn "Port $STREAMLIT_PORT is already in use."
    read -rp "  Kill existing process and use port $STREAMLIT_PORT? [Y/n]: " KILL_CHOICE
    if [[ "${KILL_CHOICE:-Y}" =~ ^[Yy]$ ]]; then
        if kill_streamlit_on_port "$STREAMLIT_PORT"; then
            success "Cleared port $STREAMLIT_PORT."
        else
            STREAMLIT_PORT=$(find_free_port $((STREAMLIT_PORT + 1)))
            info "Switching to port $STREAMLIT_PORT."
        fi
    else
        STREAMLIT_PORT=$(find_free_port $((STREAMLIT_PORT + 1)))
        info "Using port $STREAMLIT_PORT."
    fi
fi

info "Starting Streamlit on http://localhost:${STREAMLIT_PORT}  (Ctrl+C to stop)"
echo ""
exec "$STREAMLIT" run app.py --server.port "$STREAMLIT_PORT"
