#!/usr/bin/env bash
# =============================================================================
#  Analytics Workbench — MySQL Setup (requires sudo)
#  Run with:  sudo bash db_setup.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

[[ $EUID -eq 0 ]] || error "This script must be run as root:  sudo bash db_setup.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ENV="$SCRIPT_DIR/app.env"
PYTHON="$SCRIPT_DIR/.env/bin/python3"

# ── Config ────────────────────────────────────────────────────────────────────
DB_NAME="analytics_workbench"
DB_USER="aw_user"
DB_PASS="a0S47pU_HujRMXstPAD8Ug"   # generated — change if you like
DB_PREFIX="aw_"

# ── Step 1: Create DB and app user ────────────────────────────────────────────
info "Creating database '${DB_NAME}' and MySQL user '${DB_USER}'…"

mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost'
  IDENTIFIED BY '${DB_PASS}';

GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';

FLUSH PRIVILEGES;
SQL

success "Database and user ready."

# ── Step 2: Apply schema ──────────────────────────────────────────────────────
info "Applying schema…"
mysql -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" < "$SCRIPT_DIR/install/install.sql"
success "Schema applied."

# ── Step 3: Create superadmin ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Create your superadmin account${RESET}"
read -rp "  Name     : " ADMIN_NAME;  ADMIN_NAME="${ADMIN_NAME:-Admin}"
read -rp "  Email    : " ADMIN_EMAIL; ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
while true; do
    read -srp " Password (min 8 chars): " ADMIN_PASS;  echo ""
    read -srp " Confirm Password       : " ADMIN_PASS2; echo ""
    [[ "$ADMIN_PASS" == "$ADMIN_PASS2" && ${#ADMIN_PASS} -ge 8 ]] && break
    echo "Passwords do not match or are too short. Try again."
done

HASHED=$("$PYTHON" -c "
import bcrypt, sys
print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt(12)).decode())
" "$ADMIN_PASS")

mysql -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" <<SQL
INSERT IGNORE INTO \`${DB_PREFIX}users\` (name, email, password, role)
VALUES ('${ADMIN_NAME}', '${ADMIN_EMAIL}', '${HASHED}', 'superadmin');
SQL

success "Superadmin '${ADMIN_EMAIL}' created."

# ── Step 4: Update app.env ────────────────────────────────────────────────────
info "Updating app.env with new DB credentials…"

if [[ -f "$APP_ENV" ]]; then
    # Update DB credentials in-place
    sed -i "s|^DB_USERNAME=.*|DB_USERNAME=${DB_USER}|"  "$APP_ENV"
    sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASS}|"  "$APP_ENV"
    sed -i "s|^DB_DATABASE=.*|DB_DATABASE=${DB_NAME}|"  "$APP_ENV"
else
    # Write fresh app.env
    APP_SECRET_KEY=$("$PYTHON" -c "import secrets; print(secrets.token_hex(32))")
    cat > "$APP_ENV" <<EOF
APP_NAME="Analytics Workbench"
APP_ENV=production
APP_DEBUG=false
APP_URL=http://localhost
APP_SECRET_KEY=${APP_SECRET_KEY}

DB_CONNECTION=mysql
DB_HOST=localhost
DB_PORT=3306
DB_DATABASE=${DB_NAME}
DB_USERNAME=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_PREFIX=${DB_PREFIX}

STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
EOF
fi

success "app.env updated."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo -e "  ${GREEN}Setup complete!${RESET}"
echo -e "  Admin email : ${ADMIN_EMAIL}"
echo -e "  DB user     : ${DB_USER}"
echo -e "  DB password : ${DB_PASS}  (saved in app.env)"
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo ""
echo "  Now launch the app:"
echo "    cd $SCRIPT_DIR"
echo "    ./setup.sh --run-only"
echo ""
