# Analytics Workbench — Technical Documentation

> **Version 1.0.0** · CodeCanyon Regular / Extended License  
> Last Updated: April 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Server Requirements](#2-server-requirements)
3. [Installation Guide](#3-installation-guide)
4. [Feature Guide](#4-feature-guide)
5. [Troubleshooting](#5-troubleshooting)
6. [Changelog](#6-changelog)

---

## 1. Introduction

**Analytics Workbench** is a self-hosted, browser-based AI/ML platform built on Python and Streamlit. It provides a complete end-to-end workflow for data scientists, analysts, and developers — from raw data ingestion through model training, evaluation, and live prediction — all within a single, unified interface.

### What's Included

| Area | Capability |
|---|---|
| **Data Management** | Upload CSV / Excel, explore datasets, manage multiple datasets in session |
| **Preprocessing** | Handle missing values, encode categoricals, scale features, train/test split |
| **Visualization** | Distribution plots, correlation heatmaps, scatter plots, pair plots |
| **Outlier Detection** | IQR, Z-score, and Isolation Forest methods with visual summaries |
| **Machine Learning** | 6 scikit-learn models (Linear/Logistic Regression, Random Forest, Extra Trees, KNN, SVM) |
| **Deep Learning — Keras** | MLP, CNN, LSTM, GRU, RNN architectures (CPU-optimised, TensorFlow backend) |
| **Deep Learning — PyTorch** | MLP, CNN, LSTM, GRU, RNN architectures (CPU-optimised) |
| **Admin Panel** | User management, role-based access control, API key vault, site settings |
| **Analytics Dashboard** | Live KPI cards, traffic charts, role distribution, module usage analytics |

### Architecture Overview

```
analytics_workbench/
├── app.py                  # Main Streamlit entry point
├── setup.sh                # One-command setup & launch script
├── requirements.txt        # Python dependencies
├── .env                    # Runtime configuration (generated at setup, gitignored)
│
├── admin/                  # Admin module (auth, RBAC, settings, dashboard)
│   ├── auth.py             # Login, session, bcrypt password hashing
│   ├── db.py               # SQLite context manager, schema bootstrap
│   ├── dashboard.py        # Premium analytics dashboard
│   ├── user_management.py  # User CRUD
│   ├── settings_manager.py # Branding & maintenance settings
│   └── api_keys.py         # Fernet-encrypted API key vault
│
├── core/                   # Data pipeline
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── visualization.py
│   └── outliers.py
│
├── models/                 # Model implementations
│   ├── sklearn/            # 6 classical ML models
│   ├── keras/              # 5 Keras/TensorFlow models
│   └── pytorch/            # 5 PyTorch models
│
├── data/                   # SQLite database (auto-created)
├── static/                 # Uploaded assets (logos, etc.)
└── session_data/           # Persisted session state
```

---

## 2. Server Requirements

### Minimum Specifications

| Resource | Minimum | Recommended |
|---|---|---|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 5 GB free | 20 GB free |
| **OS** | Ubuntu 20.04 / Debian 11 | Ubuntu 22.04 LTS |

> **Note on deep learning:** TensorFlow and PyTorch are included as CPU-only builds. GPU acceleration is not required but can significantly improve training times on large datasets if a CUDA-compatible GPU is available.

### Software Requirements

| Dependency | Minimum Version | Notes |
|---|---|---|
| **Python** | 3.9 | 3.10 or 3.11 recommended |
| **pip** | 22.0+ | Bundled with Python |
| **SQLite** | 3.35+ | Bundled with Python's `sqlite3` module |
| **Git** | any | Optional, for source installs |
| **lsof** | any | Used by `setup.sh` for port detection |

> MySQL / PostgreSQL are **not** required. Analytics Workbench uses SQLite for all internal data by default — zero database configuration needed.

### Python Package Requirements

```
numpy>=1.24.0          pandas>=2.0.0
scikit-learn>=1.3.0    tensorflow>=2.13.0
torch>=2.0.0           streamlit>=1.25.0
matplotlib>=3.7.0      seaborn>=0.12.0
plotly>=5.14.0         openpyxl>=3.1.0
xlrd>=2.0.0            joblib>=1.3.0
pyyaml>=6.0            cryptography>=41.0.0
bcrypt>=4.0.0          python-dotenv>=1.0.0
```

All packages are installed automatically by `setup.sh`.

### Network & Firewall

| Port | Purpose | Required |
|---|---|---|
| **8501** (default) | Streamlit web UI | Yes — open to end users |
| **22** | SSH for deployment | Recommended |

---

## 3. Installation Guide

### Step 1 — Upload & Extract

**Via FTP / SFTP (shared hosting or VPS):**

1. Download the product ZIP from CodeCanyon.
2. Extract the archive locally — you should see `analytics_workbench/` as the root folder.
3. Upload the entire `analytics_workbench/` folder to your server, e.g. `/var/www/analytics_workbench/`.

**Via Git (recommended for VPS):**

```bash
cd /var/www
git clone <your-repo-url> analytics_workbench
cd analytics_workbench
```

---

### Step 2 — Run the Setup Script

The included `setup.sh` handles everything: virtual environment creation, dependency installation, configuration, database bootstrapping, and launch.

```bash
cd /var/www/analytics_workbench
chmod +x setup.sh
./setup.sh
```

The script performs these steps automatically:

| Step | Action |
|---|---|
| **Preflight** | Checks Python ≥ 3.9, pip, lsof are available |
| **Virtual Environment** | Creates `.venv/` Python venv if not present |
| **Dependencies** | Runs `pip install -r requirements.txt` inside the venv |
| **Configuration** | Prompts for settings, writes `.env`, generates a random `APP_SECRET_KEY` |
| **Database** | Bootstraps SQLite schema (tables: `aw_users`, `aw_settings`, `aw_api_keys`) |
| **Superadmin** | Creates default admin account if none exists |
| **Launch** | Starts Streamlit on the first available port (default 8501) |

> **First-time setup only.** On subsequent restarts use `./setup.sh --run-only` to skip setup steps and go straight to launching.

---

### Step 3 — Access the Application

Open your browser and navigate to:

```
http://<your-server-ip>:8501
```

You will be greeted by the login screen. Default credentials:

| Field | Value |
|---|---|
| **Email / Username** | `admin` |
| **Password** | `admin` |

> **Important:** Change the default admin password immediately after first login via **Admin → User Management → Edit**.

---

### Step 4 — Configuration (`.env`)

All runtime settings live in `.env` in the project root. It is created by `setup.sh` on first run. You can also create it manually:

```bash
cp .env.example .env
# then edit .env with your preferred editor
```

Key variables:

```ini
# Security — CHANGE THIS before going to production
APP_SECRET_KEY=<auto-generated-64-char-hex>

# SQLite database path (leave blank for default: data/analytics_workbench.db)
DB_PATH=

# Table prefix — useful if sharing a database with other apps
DB_PREFIX=aw_

# Streamlit server
STREAMLIT_SERVER_PORT=8501

# Initial superadmin — used only on the first launch
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong-password>
```

After editing `.env`, restart the application:

```bash
./setup.sh --run-only
```

---

### Step 5 — Running as a Background Service (Recommended for Production)

To keep Analytics Workbench running after you close your terminal, create a `systemd` service:

```bash
sudo nano /etc/systemd/system/analytics-workbench.service
```

Paste the following (adjust paths as needed):

```ini
[Unit]
Description=Analytics Workbench
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/analytics_workbench
ExecStart=/var/www/analytics_workbench/.env/bin/streamlit run app.py \
          --server.port=8501 \
          --server.address=0.0.0.0 \
          --server.headless=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable analytics-workbench
sudo systemctl start analytics-workbench
sudo systemctl status analytics-workbench
```

---

### Step 6 — Cron Jobs (Optional)

Analytics Workbench does not require scheduled tasks for core operation. However, you may wish to set up the following:

**Automated database backup (daily at 2 AM):**

```cron
0 2 * * * cp /var/www/analytics_workbench/data/analytics_workbench.db \
             /var/backups/aw_db_$(date +\%Y\%m\%d).db
```

**Prune old session data (weekly):**

```cron
0 3 * * 0 find /var/www/analytics_workbench/session_data -name "*.pkl" \
               -mtime +30 -delete
```

Add these lines to your crontab with `crontab -e`.

---

## 4. Feature Guide

### 4.1 Analytics Dashboard

Navigate to **Admin → 📊 Dashboard** after logging in with an admin or superadmin account.

The dashboard provides real-time platform health metrics:

| Widget | Description |
|---|---|
| **KPI Cards** | Total Users, Active Users, Stored API Keys, Admin count — each with delta indicators showing change vs previous period |
| **Traffic Over Time** | Line chart showing daily activity for the current 30-day window vs the prior 30-day window |
| **User Role Distribution** | Doughnut chart breaking down the platform user base by role (Superadmin / Admin / Viewer) |
| **Top Platform Modules** | Horizontal bar chart showing which ML modules are used most frequently |

**Live vs Sample data:** When sufficient usage data exists in the database the dashboard displays a green **Live** badge. A yellow **Sample** badge indicates the chart is using illustrative demo data (typical on a fresh install).

**Skeleton loaders:** On first load a shimmer animation is displayed while charts render — this is expected behaviour and does not indicate an error.

---

### 4.2 User Management

Navigate to **Admin → 👥 User Management**.

#### Roles

| Role | Access Level |
|---|---|
| **Superadmin** | Full access: can create/edit/delete any user, assign any role |
| **Admin** | Can manage users but cannot assign Superadmin role or delete other admins |
| **Viewer** | Read-only access to the ML platform; no access to admin pages |

#### Creating a User

1. Scroll to **➕ Create New User** at the bottom of the page.
2. Fill in Full Name, Email / Username, Password (min. 8 characters), and Role.
3. Click **Create User**.

#### Editing a User

1. Locate the user in the table and click **✏️ Edit**.
2. Modify Name, Email, or Role inline.
3. To reset the password, enter a new password in the **Reset Password** field (leave blank to keep the current password).
4. Click **💾 Save**.

#### Activating / Deactivating

Click **Deactivate** or **Activate** next to any user. Deactivated users cannot log in but their data is preserved.

---

### 4.3 API Key Vault

Navigate to **Admin → 🔑 API Keys**.

The API Key Vault stores credentials for external services (OpenAI, Stripe, AWS, etc.) encrypted at rest using **Fernet symmetric encryption (AES-128-CBC)** with a key derived from your `APP_SECRET_KEY`.

#### Storing a Key

1. Scroll to **➕ Add New API Key**.
2. Enter a unique **Key Name** (e.g. `openai_production`), the **Service** (e.g. `OpenAI`), and paste the raw **API Key**.
3. Click **🔒 Encrypt & Save** — the plaintext key is never stored; only the encrypted ciphertext and a masked preview (`sk-••••••••••••abcd`) are persisted.

#### Revealing a Key

Click **👁 Reveal** next to any key. The decrypted value appears in an expandable panel and is only visible for the current session. Click **✖ Hide** to dismiss it or navigate away — it will not be shown again automatically.

> **Security note:** Revealed keys exist only in the browser session and are never logged. Rotate your `APP_SECRET_KEY` with care — changing it will invalidate all stored encrypted keys (they cannot be decrypted with a different key).

---

### 4.4 Site Settings

Navigate to **Admin → ⚙️ Site Settings**.

| Setting | Description |
|---|---|
| **Site Name** | Displayed in the browser tab and platform header |
| **Footer Text** | Shown at the bottom of every page |
| **Contact Email** | Support contact address displayed to users |
| **Site Logo** | Upload a PNG / JPG / SVG / WebP ≤ 2 MB; stored in `static/` |
| **Maintenance Mode** | When enabled, only admins can access the platform; other users see a maintenance notice |

---

### 4.5 ML Platform Modules

#### Data Management

Upload CSV or Excel files via **📁 Data Management**. Multiple datasets can be loaded into a session and switched between using the dataset selector. The built-in explorer shows shape, dtypes, missing value counts, and a statistical summary.

#### Preprocessing

The **🔧 Preprocessing** module provides:
- Missing value handling (drop rows, fill with mean/median/mode, or a constant)
- Categorical encoding (Label Encoding, One-Hot Encoding)
- Feature scaling (Standard Scaler, Min-Max Scaler, Robust Scaler)
- Train / test split with configurable ratio and random seed

#### Visualization

The **📊 Visualization** module generates:
- Distribution histograms per feature
- Correlation heatmaps
- Scatter plot matrices (pair plots)
- Box plots for outlier visibility

#### Outlier Detection

The **🔍 Outlier Detection** module supports three strategies:
- **IQR method** — marks values outside 1.5× the interquartile range
- **Z-score method** — marks values more than N standard deviations from the mean
- **Isolation Forest** — unsupervised tree-based anomaly detection

Each method shows affected row counts and offers one-click removal.

#### Model Training

Choose a framework tab (**Scikit-learn**, **Keras**, or **PyTorch**), select a model, configure hyperparameters, pick your target column, and click **Train**. The platform automatically detects whether the task is classification or regression based on the target column's cardinality.

**Available models:**

| Framework | Models |
|---|---|
| **Scikit-learn** | Linear Regression, Logistic Regression, Random Forest, Extra Trees, KNN, SVM |
| **Keras** | MLP, CNN, LSTM, GRU, RNN |
| **PyTorch** | MLP, CNN, LSTM, GRU, RNN |

#### Model Evaluation

After training, the **📈 Evaluation** page shows accuracy/R², confusion matrix (classification), feature importances (tree models), and training history curves (deep learning).

#### Prediction

Upload a new CSV or enter values manually in **🔮 Prediction** to get inference results from any previously trained model. Predictions can be downloaded as CSV.

---

## 5. Troubleshooting

### 5.1 "Database not configured — run the web installer first"

**Cause:** The application cannot locate or initialise the SQLite database file.

**Fix:**
1. Ensure `.env` exists in the project root. If missing, copy the example file:
   ```bash
   cp .env.example .env
   ```
2. Check that the `data/` directory is writable:
   ```bash
   chmod 755 /var/www/analytics_workbench/data
   ```
3. Run the setup script to bootstrap the schema:
   ```bash
   ./setup.sh --reset-admin
   ```

---

### 5.2 Login fails with correct credentials

**Possible causes and fixes:**

| Symptom | Fix |
|---|---|
| User account was deactivated | Log in as a superadmin and re-activate the user via User Management |
| Password was reset and new one is unknown | Run `./setup.sh --reset-admin` or set `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env` and delete the database to reseed |
| `APP_SECRET_KEY` changed after initial setup | The bcrypt hashes are independent of `APP_SECRET_KEY`; this only affects API keys — check `.env` for typos |

---

### 5.3 "Permission denied" errors

**File permission issues on Linux:**

```bash
# Ensure the app directory is owned by the process user
sudo chown -R www-data:www-data /var/www/analytics_workbench

# Ensure writable directories have correct permissions
chmod 755 /var/www/analytics_workbench/data
chmod 755 /var/www/analytics_workbench/static
chmod 755 /var/www/analytics_workbench/session_data
```

**Virtual environment permission issues:**

```bash
# Re-create the venv with the correct user
rm -rf .env
python3 -m venv .env
.env/bin/pip install -r requirements.txt
```

---

### 5.4 404 / Page Not Found after deploying behind a reverse proxy

If you are using **Nginx** or **Apache** as a reverse proxy in front of Streamlit, WebSocket upgrades must be forwarded correctly.

**Nginx configuration:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass         http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_read_timeout 86400;
    }
}
```

After editing, reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

### 5.5 Streamlit port already in use

If port 8501 is occupied, `setup.sh` will automatically detect and use the next available port (8502, 8503, …). The chosen port is printed to the console:

```
[OK]  Launching on port 8502
      → http://localhost:8502
```

To manually free a port:
```bash
# Find which process is using port 8501
lsof -i :8501

# Kill it by PID
kill -9 <PID>
```

---

### 5.6 Deep Learning models are very slow

TensorFlow and PyTorch are installed as **CPU-only** builds. Training deep learning models on large datasets without a GPU will be slow. Recommendations:

- Start with smaller datasets (< 50,000 rows) for interactive use.
- Reduce epoch counts during exploration.
- Use `scikit-learn` models for tabular data — they are dramatically faster and often equally accurate.
- For production GPU training, install the CUDA-enabled builds of TensorFlow and PyTorch after confirming your CUDA version.

---

### 5.7 "ModuleNotFoundError" on startup

This means a package is missing from the virtual environment.

```bash
cd /var/www/analytics_workbench
.env/bin/pip install -r requirements.txt
```

If using `setup.sh`:
```bash
./setup.sh   # re-runs dependency installation safely
```

---

### 5.8 API keys cannot be decrypted after moving the server

API keys are encrypted using a key derived from `APP_SECRET_KEY`. If you move your installation to a new server you **must** copy `.env` alongside the database file — both must match.

Checklist when migrating:

- [ ] Copy `data/analytics_workbench.db` to the new server
- [ ] Copy `.env` (with the same `APP_SECRET_KEY`) to the new server
- [ ] Do **not** regenerate `APP_SECRET_KEY` after migration

---

## 6. Changelog

### Version 1.0.0 — April 2026

**Initial Release**

- Core ML platform with 16 models across 3 frameworks (scikit-learn, Keras/TensorFlow, PyTorch)
- Data management: CSV / Excel upload, multi-dataset session management
- Preprocessing pipeline: missing values, encoding, scaling, train/test split
- Visualization module: distributions, heatmaps, scatter matrices, box plots
- Outlier detection: IQR, Z-score, Isolation Forest
- Model training, evaluation, and prediction export
- Admin panel with Role-Based Access Control (Superadmin / Admin / Viewer)
- User Management: full CRUD, active/inactive toggle, inline password reset
- API Key Vault: Fernet-encrypted storage, masked preview, one-time reveal
- Site Settings: branding, logo upload, footer, maintenance mode
- Premium Analytics Dashboard: KPI cards, traffic chart, role distribution, module usage
- SQLite backend — zero-configuration database, no MySQL/PostgreSQL required
- `setup.sh` one-command installer with `--run-only` and `--reset-admin` flags
- bcrypt password hashing (cost factor 12)
- Dark-theme UI throughout

---

> For support, feature requests, or bug reports please use the **Comments** tab on the CodeCanyon product page.

---

*Analytics Workbench is provided under the CodeCanyon Regular / Extended License. Redistribution, resale, or sub-licensing of the source code is prohibited.*
