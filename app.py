"""
Main Streamlit application entry point for the modular AI/ML platform.

This comprehensive application provides:
- Dataset management and exploration
- Data preprocessing and visualization
- Outlier detection and handling
- Classical ML and deep learning model training
- Model evaluation and prediction
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import html as _html_mod
import traceback as _traceback
from pathlib import Path
from typing import Optional, Any
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import json

# ── Install gate ──────────────────────────────────────────────────────────────
# Must run before any heavy imports and before the first st.* call.
_INSTALLED = (Path(__file__).parent / ".installed").exists()

st.set_page_config(
    page_title="Analytics Workbench — Setup" if not _INSTALLED
               else "Comprehensive Modular AI/ML Platform",
    page_icon="⚙️" if not _INSTALLED else "🤖",
    layout="wide",
    initial_sidebar_state="collapsed" if not _INSTALLED else "expanded",
)

if not _INSTALLED:
    from install.wizard import render_wizard as _render_wizard
    _render_wizard()
    st.stop()

# Import core modules
from core.data_loader import DatasetManager
from core.preprocessing import Preprocessor
from core.visualization import Visualizer
from core.outliers import OutlierDetector
from models import get_model, list_models, load_model_from_path, load_all_models_from_path, FRAMEWORK_MODELS, MODEL_SUPPORTED_TASKS
from utils.helpers import save_object, load_object, save_json
import pickle
import os as os_module

# ── Admin / Auth module ───────────────────────────────────────────────────────
from admin import (
    is_authenticated,
    is_admin,
    is_manager,
    get_current_user,
    render_login_page,
    logout,
    require_auth,
    require_admin,
    require_manager_or_above,
    get_csrf_token,
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_VIEWER,
    render_user_management,
    render_settings_manager,
    render_api_keys,
    render_dashboard,
    render_log_viewer,
)
from admin.db import ensure_admin_schema, seed_superadmin
from admin.error_logger import (
    generate_error_id as _gen_error_id,
    log_exception     as _log_exc,
    render_error_page as _render_err_page,
)

# Bootstrap SQLite DB on every cold start (idempotent — safe to call always)
ensure_admin_schema()
seed_superadmin()  # reads ADMIN_EMAIL / ADMIN_PASSWORD from .env

# Base directory for saving/loading models (absolute, next to app.py)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE_DIR = os.path.join(_APP_DIR, "saved_models")

# Persistence directory
PERSISTENCE_DIR = Path("./session_data")
PERSISTENCE_DIR.mkdir(exist_ok=True)
PERSISTENCE_FILE = PERSISTENCE_DIR / "session_state.pkl"

# Helper functions for persistence
def save_session_state():
    """Save important session state data to disk."""
    try:
        state_to_save = {
            'datasets': st.session_state.dataset_manager.datasets if hasattr(st.session_state.dataset_manager, 'datasets') else {},
            'current_dataset': st.session_state.get('current_dataset', None),
            'preprocessing_pipeline': st.session_state.get('preprocessing_pipeline', []),
            'trained_models': {},
            'target_column': st.session_state.get('target_column', None),
        }

        # Save train/test splits if they exist
        if 'X_train' in st.session_state:
            state_to_save['X_train'] = st.session_state.X_train
            state_to_save['X_val'] = st.session_state.X_val
            state_to_save['X_test'] = st.session_state.X_test
            state_to_save['y_train'] = st.session_state.y_train
            state_to_save['y_val'] = st.session_state.y_val
            state_to_save['y_test'] = st.session_state.y_test

        # Save trained models using unified interface
        for model_name, model_obj in st.session_state.get('trained_models', {}).items():
            model_dir = PERSISTENCE_DIR / model_name
            try:
                model_obj.save(str(model_dir))
                state_to_save['trained_models'][model_name] = {
                    'registry_key': model_obj.get_config()['registry_key'],
                    'metrics': model_obj.metrics,
                    'history': model_obj.history,
                }
            except Exception as e:
                print(f"Error saving model {model_name}: {e}")

        with open(PERSISTENCE_FILE, 'wb') as f:
            pickle.dump(state_to_save, f)
    except Exception as e:
        print(f"Error saving session state: {e}")

def load_session_state():
    """Load session state data from disk."""
    try:
        if PERSISTENCE_FILE.exists():
            with open(PERSISTENCE_FILE, 'rb') as f:
                saved_state = pickle.load(f)

            # Restore datasets
            if saved_state.get('datasets'):
                st.session_state.dataset_manager.datasets = saved_state['datasets']

            # Restore other state
            st.session_state.current_dataset = saved_state.get('current_dataset')
            st.session_state.preprocessing_pipeline = saved_state.get('preprocessing_pipeline', [])
            st.session_state.target_column = saved_state.get('target_column')

            # Restore train/test splits
            if 'X_train' in saved_state:
                st.session_state.X_train = saved_state['X_train']
                st.session_state.X_val = saved_state['X_val']
                st.session_state.X_test = saved_state['X_test']
                st.session_state.y_train = saved_state['y_train']
                st.session_state.y_val = saved_state['y_val']
                st.session_state.y_test = saved_state['y_test']

            # Restore trained models using unified interface
            for model_name, model_meta in saved_state.get('trained_models', {}).items():
                model_dir = PERSISTENCE_DIR / model_name
                try:
                    if 'registry_key' in model_meta and (model_dir / "config.json").exists():
                        model = load_model_from_path(str(model_dir))
                        model.metrics = model_meta.get('metrics', {})
                        model.history = model_meta.get('history', {})
                        st.session_state.trained_models[model_name] = model
                except Exception as e:
                    print(f"Error loading model {model_name}: {e}")

    except Exception as e:
        print(f"Error loading session state: {e}")

# Initialize session state
if 'dataset_manager' not in st.session_state:
    st.session_state.dataset_manager = DatasetManager()
if 'preprocessor' not in st.session_state:
    st.session_state.preprocessor = Preprocessor()
if 'visualizer' not in st.session_state:
    st.session_state.visualizer = Visualizer()
if 'outlier_detector' not in st.session_state:
    st.session_state.outlier_detector = OutlierDetector()
if 'trained_models' not in st.session_state:
    st.session_state.trained_models = {}
if 'current_dataset' not in st.session_state:
    st.session_state.current_dataset = None
if 'preprocessing_pipeline' not in st.session_state:
    st.session_state.preprocessing_pipeline = []

# Load persisted state on first run
if 'state_loaded' not in st.session_state:
    load_session_state()
    st.session_state.state_loaded = True

# ── Authentication gate ───────────────────────────────────────────────────────
# Renders the login page and stops execution until the user is authenticated.
if not is_authenticated():
    render_login_page()
    st.stop()

# ── Maintenance mode check ────────────────────────────────────────────────────
# Regular users are blocked when maintenance mode is active.
def _check_maintenance():
    if is_admin():
        return  # admins always pass through
    try:
        from admin.db import get_db, table, is_configured
        if not is_configured():
            return
        with get_db() as (_, cur):
            cur.execute(
                f"SELECT setting_value FROM {table('settings')} "
                f"WHERE setting_key='maintenance_mode' LIMIT 1"
            )
            row = cur.fetchone()
        if row and row.get("setting_value") == "1":
            st.warning("🔧 The platform is currently under maintenance. Please check back later.")
            st.stop()
    except Exception:
        pass  # Non-fatal

_check_maintenance()

# Main title
_current_user = get_current_user()
st.title("🤖 Comprehensive Modular AI/ML Platform")
st.markdown("---")

# ── Sidebar: user identity + logout ──────────────────────────────────────────
with st.sidebar:
    _u = get_current_user()
    if _u:
        role_badge = {
            ROLE_SUPERADMIN: "🔴",
            ROLE_ADMIN:      "🟡",
            ROLE_MANAGER:    "🔵",
            ROLE_VIEWER:     "🟢",
        }.get(_u.get("role", ""), "⚪")
        # Escape user-controlled values before injecting into HTML to prevent XSS.
        _safe_name = _html_mod.escape(_u["name"])
        _safe_role = _html_mod.escape(_u["role"])
        st.markdown(
            f"<div style='padding:8px 0 4px'>"
            f"<span style='font-size:.8rem;color:#94a3b8'>Signed in as</span><br>"
            f"<b>{_safe_name}</b>&nbsp;{role_badge} "
            f"<span style='font-size:.75rem;color:#64748b'>{_safe_role}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()

# Sidebar navigation
st.sidebar.title("Navigation")

# Pages that require Manager-or-above (create / edit analytics).
_MANAGER_PAGES = {
    "📁 Dataset Management",
    "🚨 Outlier Detection",
    "⚙️ Preprocessing",
    "🎯 Model Training",
}
# Pages available to every authenticated user (read-only analytics).
_VIEWER_PAGES = [
    "🔍 Data Exploration",
    "📊 Visualization",
    "📈 Model Evaluation",
    "🔮 Prediction",
]

if is_manager():
    # Managers and above see all eight analytics pages.
    _platform_pages = [
        "📁 Dataset Management",
        "🔍 Data Exploration",
        "📊 Visualization",
        "🚨 Outlier Detection",
        "⚙️ Preprocessing",
        "🎯 Model Training",
        "📈 Model Evaluation",
        "🔮 Prediction",
    ]
else:
    # Viewers see only the read-only pages.
    _platform_pages = _VIEWER_PAGES

_admin_pages = [
    "📊 Dashboard",
    "👥 User Management",
    "⚙️ Site Settings",
    "🔑 API Keys",
    "📋 Error Logs",
] if is_admin() else []

page = st.sidebar.radio(
    "Select a module:",
    _platform_pages + (_admin_pages and ["─── Admin ───"] + _admin_pages or []),
)

# Session persistence controls
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Session Persistence")
if PERSISTENCE_FILE.exists():
    st.sidebar.success("✓ Auto-save enabled")
    if st.sidebar.button("🗑️ Clear All Saved Data"):
        import shutil
        if PERSISTENCE_DIR.exists():
            shutil.rmtree(PERSISTENCE_DIR)
            PERSISTENCE_DIR.mkdir(exist_ok=True)
        st.sidebar.success("Cleared! Refresh the page.")
else:
    st.sidebar.info("Data will be saved automatically")

if st.sidebar.button("💾 Save Now"):
    save_session_state()
    st.sidebar.success("Saved!")


# ============================================================================
# PAGE RENDERING — wrapped in a try/except so uncaught exceptions show a
# professional error page instead of a raw Python stack trace.
# ============================================================================
_content_area = st.empty()

try:
    with _content_area.container():
        # DATASET MANAGEMENT
        # ============================================================================
        if page == "📁 Dataset Management":
            require_manager_or_above()
            st.header("Dataset Management")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Upload Dataset")
                uploaded_file = st.file_uploader(
                    "Choose a file (CSV, Excel, JSON, NumPy)",
                    type=['csv', 'xlsx', 'xls', 'json', 'npy', 'npz']
                )

                if uploaded_file is not None:
                    dataset_name = st.text_input("Dataset name:", value=uploaded_file.name.split('.')[0])

                    if st.button("Load Dataset"):
                        try:
                            file_extension = uploaded_file.name.split('.')[-1].lower()

                            # Save temporarily
                            temp_path = f"/tmp/{uploaded_file.name}"
                            with open(temp_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())

                            # Load based on file type
                            if file_extension == 'csv':
                                st.session_state.dataset_manager.load_csv(temp_path, dataset_name)
                            elif file_extension in ['xlsx', 'xls']:
                                st.session_state.dataset_manager.load_excel(temp_path, dataset_name)
                            elif file_extension == 'json':
                                st.session_state.dataset_manager.load_json(temp_path, dataset_name)
                            elif file_extension in ['npy', 'npz']:
                                st.session_state.dataset_manager.load_numpy(temp_path, dataset_name)

                            st.success(f"✅ Dataset '{dataset_name}' loaded successfully!")
                            st.session_state.current_dataset = dataset_name
                            save_session_state()  # Persist after loading dataset

                        except Exception as e:
                            st.error(f"❌ Error loading dataset: {str(e)}")

            with col2:
                st.subheader("Loaded Datasets")
                datasets = st.session_state.dataset_manager.list_datasets()

                if datasets:
                    for ds_name in datasets:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            if st.button(f"📊 {ds_name}", key=f"select_{ds_name}"):
                                st.session_state.current_dataset = ds_name
                        with col_b:
                            if st.button("🗑️", key=f"delete_{ds_name}"):
                                st.session_state.dataset_manager.remove_dataset(ds_name)
                                save_session_state()  # Persist after deletion
                                st.rerun()
                else:
                    st.info("No datasets loaded yet")

            # Display current dataset info
            if st.session_state.current_dataset:
                st.markdown("---")
                st.subheader(f"Current Dataset: {st.session_state.current_dataset}")

                try:
                    info = st.session_state.dataset_manager.get_dataset_info(st.session_state.current_dataset)
                    df = st.session_state.dataset_manager.get_dataset(st.session_state.current_dataset)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Rows", info['shape'][0])
                    with col2:
                        st.metric("Columns", info['shape'][1])
                    with col3:
                        st.metric("Missing Values", sum(info['missing_values'].values()))
                    with col4:
                        st.metric("Memory (MB)", f"{info['memory_usage']:.2f}")

                    # Display data preview
                    st.subheader("Data Preview")
                    st.dataframe(df.head(10), width='stretch')

                    # Column information
                    st.subheader("Column Information")
                    col_info = pd.DataFrame({
                        'Column': info['columns'],
                        'Type': [info['dtypes'][col] for col in info['columns']],
                        'Missing': [info['missing_values'][col] for col in info['columns']],
                        'Missing %': [f"{info['missing_percentage'][col]:.2f}%" for col in info['columns']]
                    })
                    st.dataframe(col_info, width='stretch')

                except Exception as e:
                    st.error(f"Error displaying dataset info: {str(e)}")

        # ============================================================================
        # DATA EXPLORATION
        # ============================================================================
        elif page == "🔍 Data Exploration":
            st.header("Data Exploration")

            if st.session_state.current_dataset:
                df = st.session_state.dataset_manager.get_dataset(st.session_state.current_dataset)

                st.subheader("Summary Statistics")
                st.dataframe(df.describe(include='all'), width='stretch')

                st.subheader("Data Types and Missing Values")
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Data Types:**")
                    st.write(df.dtypes)

                with col2:
                    st.write("**Missing Values:**")
                    missing = df.isnull().sum()
                    missing_df = pd.DataFrame({
                        'Column': missing.index,
                        'Missing Count': missing.values,
                        'Percentage': (missing.values / len(df) * 100).round(2)
                    })
                    st.dataframe(missing_df, width='stretch')

                # Correlation matrix
                st.subheader("Correlation Analysis")
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if len(numeric_cols) > 1:
                    fig = st.session_state.visualizer.plot_interactive_correlation(df[numeric_cols])
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info("Need at least 2 numeric columns for correlation analysis")

            else:
                st.warning("⚠️ Please load a dataset first in Dataset Management")

        # ============================================================================
        # PREPROCESSING
        # ============================================================================
        elif page == "⚙️ Preprocessing":
            require_manager_or_above()
            st.header("Data Preprocessing")

            if st.session_state.current_dataset:
                df = st.session_state.dataset_manager.get_dataset(st.session_state.current_dataset)

                tab1, tab2, tab3, tab4 = st.tabs([
                    "Missing Values",
                    "Feature Scaling",
                    "Categorical Encoding",
                    "Train/Test Split"
                ])

                # Missing values
                with tab1:
                    st.subheader("Handle Missing Values")
                    strategy = st.selectbox(
                        "Strategy:",
                        ['mean', 'median', 'mode', 'constant']
                    )
                    fill_value = None
                    if strategy == 'constant':
                        fill_value = st.text_input("Fill value:", "0")

                    if st.button("Apply Missing Value Handling"):
                        try:
                            df_processed = st.session_state.preprocessor.handle_missing(
                                df, strategy, fill_value
                            )
                            # Update dataset
                            st.session_state.dataset_manager.datasets[st.session_state.current_dataset] = df_processed
                            st.success("✅ Missing values handled!")
                            st.session_state.preprocessing_pipeline.append({
                                'step': 'handle_missing',
                                'params': {'strategy': strategy, 'fill_value': fill_value}
                            })
                            save_session_state()  # Persist after preprocessing
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                # Feature scaling
                with tab2:
                    st.subheader("Scale Features")
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    selected_cols = st.multiselect("Select columns to scale:", numeric_cols)
                    scaling_method = st.selectbox("Scaling method:", ['standard', 'minmax'])

                    if st.button("Apply Scaling"):
                        if selected_cols:
                            try:
                                df_processed = st.session_state.preprocessor.scale_features(
                                    df, selected_cols, scaling_method
                                )
                                st.session_state.dataset_manager.datasets[st.session_state.current_dataset] = df_processed
                                st.success("✅ Features scaled!")
                                st.session_state.preprocessing_pipeline.append({
                                    'step': 'scale_features',
                                    'params': {'columns': selected_cols, 'method': scaling_method}
                                })
                                save_session_state()  # Persist after preprocessing
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("Please select at least one column")

                # Categorical encoding
                with tab3:
                    st.subheader("Encode Categorical Features")
                    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                    selected_cols = st.multiselect("Select columns to encode:", categorical_cols)
                    encoding_method = st.selectbox("Encoding method:", ['onehot', 'label'])

                    if st.button("Apply Encoding"):
                        if selected_cols:
                            try:
                                df_processed = st.session_state.preprocessor.encode_categorical(
                                    df, selected_cols, encoding_method
                                )
                                st.session_state.dataset_manager.datasets[st.session_state.current_dataset] = df_processed
                                st.success("✅ Features encoded!")
                                st.session_state.preprocessing_pipeline.append({
                                    'step': 'encode_categorical',
                                    'params': {'columns': selected_cols, 'method': encoding_method}
                                })
                                save_session_state()  # Persist after preprocessing
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("Please select at least one column")

                # Train/test split
                with tab4:
                    st.subheader("Split Data")
                    target_col = st.selectbox("Select target column:", df.columns.tolist())
                    test_size = st.slider("Test size:", 0.1, 0.4, 0.2, 0.05)
                    val_size = st.slider("Validation size:", 0.0, 0.3, 0.1, 0.05)

                    if st.button("Split Data"):
                        try:
                            X_train, X_val, X_test, y_train, y_val, y_test = st.session_state.preprocessor.split_data(
                                df, target_col, test_size, val_size
                            )
                            # Store splits in session state
                            st.session_state.X_train = X_train
                            st.session_state.X_val = X_val
                            st.session_state.X_test = X_test
                            st.session_state.y_train = y_train
                            st.session_state.y_val = y_val
                            st.session_state.y_test = y_test
                            st.session_state.target_column = target_col

                            st.success("✅ Data split successfully!")
                            st.write(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
                            save_session_state()  # Persist after data split
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            else:
                st.warning("⚠️ Please load a dataset first")

        # ============================================================================
        # VISUALIZATION
        # ============================================================================
        elif page == "📊 Visualization":
            st.header("Data Visualization")

            if st.session_state.current_dataset:
                df = st.session_state.dataset_manager.get_dataset(st.session_state.current_dataset)

                viz_type = st.selectbox(
                    "Select visualization type:",
                    ["Histogram", "Box Plot", "Scatter Plot", "Pairplot"]
                )

                if viz_type == "Histogram":
                    col = st.selectbox("Select column:", df.select_dtypes(include=[np.number]).columns.tolist())
                    if st.button("Generate"):
                        fig = st.session_state.visualizer.plot_interactive_histogram(df, col)
                        st.plotly_chart(fig, width='stretch')

                elif viz_type == "Scatter Plot":
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    col1, col2 = st.columns(2)
                    with col1:
                        x_col = st.selectbox("X-axis:", numeric_cols)
                    with col2:
                        y_col = st.selectbox("Y-axis:", numeric_cols)
                    color_col = st.selectbox("Color by (optional):", [None] + df.columns.tolist())

                    if st.button("Generate"):
                        fig = st.session_state.visualizer.plot_interactive_scatter(df, x_col, y_col, color_col)
                        st.plotly_chart(fig, width='stretch')

            else:
                st.warning("⚠️ Please load a dataset first")

        # ============================================================================
        # OUTLIER DETECTION
        # ============================================================================
        elif page == "🚨 Outlier Detection":
            require_manager_or_above()
            st.header("Outlier Detection")

            if st.session_state.current_dataset:
                df = st.session_state.dataset_manager.get_dataset(st.session_state.current_dataset)

                method = st.selectbox(
                    "Detection method:",
                    ["Z-Score", "IQR", "Isolation Forest", "DBSCAN"]
                )

                if method == "Z-Score":
                    st.info(
                        "**Z-Score** measures how many standard deviations a data point is from the mean. "
                        "Points beyond the threshold are flagged as outliers. Works best with normally distributed data."
                    )
                elif method == "IQR":
                    st.info(
                        "**IQR (Interquartile Range)** uses the range between the 25th and 75th percentiles. "
                        "Points below Q1 - factor*IQR or above Q3 + factor*IQR are flagged as outliers. "
                        "Robust to non-normal distributions."
                    )
                elif method == "Isolation Forest":
                    st.info(
                        "**Isolation Forest** isolates observations by randomly selecting a feature and a split value. "
                        "Outliers require fewer splits to be isolated, making them easier to detect. "
                        "Effective for high-dimensional data."
                    )
                else:
                    st.info(
                        "**DBSCAN (Density-Based Spatial Clustering)** groups together closely packed points "
                        "and marks points in low-density regions as outliers. Useful when outliers form irregular patterns "
                        "that distance-based methods might miss."
                    )

                if method in ["Z-Score", "IQR"]:
                    col = st.selectbox("Select column:", df.select_dtypes(include=[np.number]).columns.tolist())

                    if method == "Z-Score":
                        threshold = st.slider("Z-score threshold:", 1.0, 5.0, 3.0, 0.5)
                        if st.button("Detect Outliers"):
                            outlier_mask = st.session_state.outlier_detector.z_score(df, col, threshold)
                            st.session_state.outlier_mask = outlier_mask
                    else:  # IQR
                        factor = st.slider("IQR factor:", 1.0, 3.0, 1.5, 0.5)
                        if st.button("Detect Outliers"):
                            outlier_mask = st.session_state.outlier_detector.iqr(df, col, factor)
                            st.session_state.outlier_mask = outlier_mask

                else:  # Isolation Forest or DBSCAN
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    selected_cols = st.multiselect("Select columns:", numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])

                    if method == "Isolation Forest":
                        contamination = st.slider("Contamination:", 0.01, 0.2, 0.05, 0.01)
                        if st.button("Detect Outliers"):
                            if selected_cols:
                                outlier_mask = st.session_state.outlier_detector.isolation_forest(df, selected_cols, contamination)
                                st.session_state.outlier_mask = outlier_mask
                    else:  # DBSCAN
                        eps = st.slider("Epsilon:", 0.1, 2.0, 0.5, 0.1)
                        min_samples = st.slider("Min samples:", 2, 20, 5)
                        if st.button("Detect Outliers"):
                            if selected_cols:
                                outlier_mask = st.session_state.outlier_detector.dbscan(df, selected_cols, eps, min_samples)
                                st.session_state.outlier_mask = outlier_mask

                # Display results
                if 'outlier_mask' in st.session_state:
                    summary = st.session_state.outlier_detector.get_outlier_summary(st.session_state.outlier_mask)
                    st.write(f"**Total outliers detected:** {summary['total_outliers']} ({summary['outlier_percentage']:.2f}%)")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Remove Outliers"):
                            df_clean = st.session_state.outlier_detector.remove_outliers(df, st.session_state.outlier_mask)
                            st.session_state.dataset_manager.datasets[st.session_state.current_dataset] = df_clean
                            st.success(f"✅ Removed {summary['total_outliers']} outliers!")
                            del st.session_state.outlier_mask
                            save_session_state()  # Persist after removing outliers
                            st.rerun()
                    with col2:
                        if st.button("✅ Keep All Data"):
                            del st.session_state.outlier_mask
                            st.rerun()

            else:
                st.warning("⚠️ Please load a dataset first")

        # ============================================================================
        # MODEL TRAINING
        # ============================================================================
        elif page == "🎯 Model Training":
            require_manager_or_above()
            st.header("Model Training")

            # Model information table
            st.subheader("📋 Available Models for Your Data")

            # Determine task type and data shape if data is available
            if 'X_train' in st.session_state:
                unique_values = st.session_state.y_train.nunique() if hasattr(st.session_state.y_train, 'nunique') else len(np.unique(st.session_state.y_train))
                is_classification = unique_values < 20
                data_shape = st.session_state.X_train.shape
                is_tabular = len(data_shape) == 2  # (samples, features)

                # Build available models based on data characteristics
                model_info_data = {}

                if is_tabular:
                    # Add sklearn models based on task type
                    if not is_classification:  # Regression
                        model_info_data["Linear Regression"] = [
                            "Scikit-Learn",
                            "Regression tasks with linear relationships",
                            f"({data_shape[0]}, {data_shape[1]})",
                            f"({data_shape[0]}, 1)"
                        ]
                        model_info_data["Random Forest"] = [
                            "Scikit-Learn",
                            "Regression with ensemble learning",
                            f"({data_shape[0]}, {data_shape[1]})",
                            f"({data_shape[0]}, 1)"
                        ]
                    else:  # Classification
                        model_info_data["Logistic Regression"] = [
                            "Scikit-Learn",
                            f"Classification ({unique_values} classes)",
                            f"({data_shape[0]}, {data_shape[1]})",
                            f"({data_shape[0]}, {unique_values})"
                        ]
                        model_info_data["Random Forest"] = [
                            "Scikit-Learn",
                            f"Classification with ensemble ({unique_values} classes)",
                            f"({data_shape[0]}, {data_shape[1]})",
                            f"({data_shape[0]}, {unique_values})"
                        ]
                        model_info_data["SVM"] = [
                            "Scikit-Learn",
                            f"Classification with decision boundaries ({unique_values} classes)",
                            f"({data_shape[0]}, {data_shape[1]})",
                            f"({data_shape[0]}, {unique_values})"
                        ]
                        model_info_data["KNN"] = [
                            "Scikit-Learn",
                            f"Nearest neighbors classification ({unique_values} classes)",
                            f"({data_shape[0]}, {data_shape[1]})",
                            f"({data_shape[0]}, {unique_values})"
                        ]

                    # Add MLP for both tasks
                    task_name = "Regression" if not is_classification else f"Classification ({unique_values} classes)"
                    model_info_data["MLP"] = [
                        "Keras/PyTorch",
                        f"Neural network for tabular data - {task_name}",
                        f"({data_shape[0]}, {data_shape[1]})",
                        f"({data_shape[0]}, {1 if not is_classification else unique_values})"
                    ]

                st.info(f"🎯 **Detected Task:** {'Classification' if is_classification else 'Regression'} | **Data Shape:** {data_shape}")

            else:
                # Show all models if no data is loaded yet
                model_info_data = {
                    "Linear Regression": ["Scikit-Learn", "Regression tasks", "(n_samples, n_features)", "(n_samples, 1)"],
                    "Logistic Regression": ["Scikit-Learn", "Classification", "(n_samples, n_features)", "(n_samples, n_classes)"],
                    "Random Forest": ["Scikit-Learn", "Classification/Regression", "(n_samples, n_features)", "(n_samples, 1 or n_classes)"],
                    "SVM": ["Scikit-Learn", "Classification", "(n_samples, n_features)", "(n_samples, n_classes)"],
                    "KNN": ["Scikit-Learn", "Classification", "(n_samples, n_features)", "(n_samples, n_classes)"],
                    "MLP": ["Keras/PyTorch", "Tabular data", "(n_samples, n_features)", "(n_samples, n_classes)"],
                    "CNN": ["Keras/PyTorch", "Image data", "(n_samples, height, width, channels)", "(n_samples, n_classes)"],
                    "RNN": ["Keras/PyTorch", "Sequential data", "(n_samples, timesteps, n_features)", "(n_samples, n_classes)"],
                    "LSTM": ["Keras/PyTorch", "Sequential data", "(n_samples, timesteps, n_features)", "(n_samples, n_classes)"],
                    "GRU": ["Keras/PyTorch", "Sequential data", "(n_samples, timesteps, n_features)", "(n_samples, n_classes)"]
                }
                st.warning("⚠️ Load and split your data to see models suitable for your specific dataset")

            # Create dataframe with categories as rows
            model_info_df = pd.DataFrame(model_info_data, index=["Framework", "Purpose", "Input Shape", "Output Shape"])
            st.dataframe(model_info_df, width='stretch')

            st.markdown("---")

            if 'X_train' not in st.session_state:
                st.warning("⚠️ Please split your data first in the Preprocessing module. Option available in preprocessing.")
            else:
                # Display current data split information
                st.subheader("📊 Your Data Configuration")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🎓 Training Samples", st.session_state.X_train.shape[0])
                with col2:
                    st.metric("✓ Validation Samples", st.session_state.X_val.shape[0])
                with col3:
                    st.metric("🧪 Test Samples", st.session_state.X_test.shape[0])

                # Input features information
                st.subheader("📥 Input Features (X)")

                # Get feature names and create transposed table
                feature_names = st.session_state.X_train.columns.tolist() if hasattr(st.session_state.X_train, 'columns') else [f"Feature_{i}" for i in range(st.session_state.X_train.shape[1])]

                # Build dictionary with each feature as a column
                input_features_data = {}
                for i, feature_name in enumerate(feature_names):
                    dtype = str(st.session_state.X_train.dtypes[i]) if hasattr(st.session_state.X_train, 'dtypes') else "numeric"
                    sample_value = str(st.session_state.X_train.iloc[0, i]) if hasattr(st.session_state.X_train, 'iloc') else str(st.session_state.X_train[0, i])

                    input_features_data[feature_name] = [
                        str(i),  # Feature Index (convert to string)
                        dtype,  # Data Type
                        sample_value  # Sample Value
                    ]

                # Create dataframe with categories as rows
                input_features_df = pd.DataFrame(input_features_data, index=["Feature Index", "Data Type", "Sample Value"])
                st.dataframe(input_features_df, width='stretch')

                st.info(f"**Input Shape:** {st.session_state.X_train.shape} → (samples, features)")

                # Output target information
                st.subheader("📤 Output Target (y)")

                target_col_name = st.session_state.get('target_column', 'target')
                unique_values = st.session_state.y_train.nunique() if hasattr(st.session_state.y_train, 'nunique') else len(np.unique(st.session_state.y_train))

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Target Column:** `{target_col_name}`")
                    st.write(f"**Unique Values:** {unique_values}")
                with col2:
                    if unique_values < 20:  # Classification
                        st.write(f"**Task Type:** Classification ({unique_values} classes)")
                        if hasattr(st.session_state.y_train, 'value_counts'):
                            st.write("**Class Distribution:**")
                            st.write(st.session_state.y_train.value_counts().to_dict())
                        else:
                            unique, counts = np.unique(st.session_state.y_train, return_counts=True)
                            st.write("**Class Distribution:**")
                            st.write(dict(zip(unique, counts)))
                    else:  # Regression
                        st.write("**Task Type:** Regression")
                        st.write(f"**Min:** {st.session_state.y_train.min():.4f}")
                        st.write(f"**Max:** {st.session_state.y_train.max():.4f}")

                st.info(f"**Output Shape:** {st.session_state.y_train.shape} → (samples,)")

                st.markdown("---")

                framework = st.selectbox("Select framework:", ["Scikit-Learn", "Keras", "PyTorch"])
                model_key = st.selectbox("Model type:", FRAMEWORK_MODELS[framework])

                # Framework-specific hyperparameter UI
                st.subheader("Hyperparameters")
                build_kwargs = {}
                train_kwargs = {}

                num_classes = st.session_state.y_train.nunique() if hasattr(st.session_state.y_train, 'nunique') else len(np.unique(st.session_state.y_train))
                is_classification = num_classes < 20

                # Determine effective task type for compatibility check
                compatible = True

                if framework == "Scikit-Learn":
                    task = st.radio("Task type:", ["classification", "regression"])
                    build_kwargs['task'] = task
                    supported = MODEL_SUPPORTED_TASKS.get(model_key, ["classification", "regression"])
                    if task not in supported:
                        supported_str = ", ".join(supported)
                        st.error(
                            f"**Incompatible configuration:** `{model_key.replace('_', ' ').title()}` "
                            f"only supports **{supported_str}**, but you selected **{task}**. "
                            f"Please choose a compatible model or change the task type."
                        )
                        compatible = False
                    if model_key in ("random_forest", "extra_trees"):
                        build_kwargs['n_estimators'] = st.slider("Number of trees:", 10, 200, 100)
                        build_kwargs['max_depth'] = st.slider("Max depth:", 1, 20, 10)
                    elif model_key == "knn":
                        build_kwargs['n_neighbors'] = st.slider("Number of neighbors:", 1, 20, 5)
                    elif model_key == "svm":
                        build_kwargs['C'] = st.slider("C:", 0.1, 10.0, 1.0)

                elif framework == "Keras":
                    task = "classification" if is_classification else "regression"
                    supported = MODEL_SUPPORTED_TASKS.get(model_key, ["classification", "regression"])
                    if task not in supported:
                        supported_str = ", ".join(supported)
                        st.error(
                            f"**Incompatible configuration:** `{model_key.replace('_', ' ').title()}` "
                            f"only supports **{supported_str}**, but your data requires **{task}**. "
                            f"Please choose a compatible model."
                        )
                        compatible = False
                    input_shape = st.session_state.X_train.shape[1]
                    build_kwargs['hidden_units'] = st.slider("Hidden units:", 16, 256, 64)
                    build_kwargs['optimizer'] = st.selectbox("Optimizer:", ["adam", "sgd", "rmsprop"])
                    build_kwargs['input_shape'] = input_shape
                    build_kwargs['output_shape'] = num_classes if is_classification else 1
                    build_kwargs['loss'] = 'sparse_categorical_crossentropy' if is_classification else 'mse'
                    build_kwargs['output_activation'] = 'softmax' if is_classification else 'linear'
                    train_kwargs['epochs'] = st.slider("Epochs:", 5, 100, 10)
                    train_kwargs['batch_size'] = st.slider("Batch size:", 8, 128, 32)

                else:  # PyTorch
                    task = "classification" if is_classification else "regression"
                    supported = MODEL_SUPPORTED_TASKS.get(model_key, ["classification", "regression"])
                    if task not in supported:
                        supported_str = ", ".join(supported)
                        st.error(
                            f"**Incompatible configuration:** `{model_key.replace('_', ' ').title()}` "
                            f"only supports **{supported_str}**, but your data requires **{task}**. "
                            f"Please choose a compatible model."
                        )
                        compatible = False
                    input_dim = st.session_state.X_train.shape[1]
                    build_kwargs['input_dim'] = input_dim
                    build_kwargs['output_dim'] = num_classes if is_classification else 1
                    build_kwargs['task'] = task
                    build_kwargs['hidden_units'] = st.slider("Hidden units:", 16, 256, 64)
                    train_kwargs['epochs'] = st.slider("Epochs:", 5, 100, 10)
                    train_kwargs['batch_size'] = st.slider("Batch size:", 8, 128, 32)
                    train_kwargs['lr'] = st.slider("Learning rate:", 0.0001, 0.1, 0.001, step=0.0001, format="%.4f")

                # Unified training button
                if not compatible:
                    st.button("🚀 Train Model", disabled=True)
                elif st.button("🚀 Train Model"):
                    with st.spinner("Training..."):
                        try:
                            model = get_model(model_key)
                            model.build(**build_kwargs)

                            # Prepare y data for training
                            y_train_prepared = st.session_state.y_train
                            y_val_prepared = st.session_state.y_val

                            # For classification, remap labels to 0..n-1 so models don't crash on
                            # negative or non-contiguous target values (e.g. -2, 3, 7 → 0, 1, 2)
                            if is_classification:
                                from sklearn.preprocessing import LabelEncoder
                                _le = LabelEncoder()
                                _le.fit(pd.concat([st.session_state.y_train, st.session_state.y_val]))
                                y_train_prepared = pd.Series(_le.transform(st.session_state.y_train), index=st.session_state.y_train.index)
                                y_val_prepared = pd.Series(_le.transform(st.session_state.y_val), index=st.session_state.y_val.index)

                            if framework == "Keras" and is_classification:
                                from tensorflow.keras.utils import to_categorical
                                y_train_prepared = to_categorical(y_train_prepared, num_classes)
                                y_val_prepared = to_categorical(y_val_prepared, num_classes)
                            elif framework == "Keras" and not is_classification:
                                y_train_prepared = st.session_state.y_train.values.reshape(-1, 1)
                                y_val_prepared = st.session_state.y_val.values.reshape(-1, 1)

                            model.train(
                                st.session_state.X_train, y_train_prepared,
                                st.session_state.X_val, y_val_prepared,
                                **train_kwargs
                            )

                            # Evaluate (use remapped labels for classification)
                            task = build_kwargs.get('task', 'classification' if is_classification else 'regression')
                            y_train_eval = _le.transform(st.session_state.y_train) if is_classification else st.session_state.y_train
                            y_val_eval = _le.transform(st.session_state.y_val) if is_classification else st.session_state.y_val
                            train_metrics = model.evaluate(st.session_state.X_train, y_train_eval, task)
                            val_metrics = model.evaluate(st.session_state.X_val, y_val_eval, task)
                            model.metrics = {'train': train_metrics, 'val': val_metrics}

                            # Store in session state
                            st.session_state.trained_models[model_key] = model

                            st.success("✅ Model trained successfully!")

                            # Display metrics
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Training Metrics:**")
                                st.json(train_metrics)
                            with col2:
                                st.write("**Validation Metrics:**")
                                st.json(val_metrics)

                            # Plot learning curves if history exists
                            if model.history:
                                fig = st.session_state.visualizer.plot_learning_curves(model.history)
                                st.plotly_chart(fig, width='stretch')

                            save_session_state()

                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                # Save trained model to disk
                if model_key in st.session_state.trained_models:
                    st.markdown("---")
                    st.subheader("Save Trained Model")
                    col_path, col_btn = st.columns([3, 1])
                    with col_path:
                        save_dir = st.text_input("Save directory:", DEFAULT_SAVE_DIR, key="training_save_dir")
                    with col_btn:
                        st.write("")
                        st.write("")
                        if st.button("💾 Save Model", key="training_save_btn"):
                            try:
                                abs_dir = os.path.abspath(save_dir)
                                st.session_state.trained_models[model_key].save(abs_dir)
                                config = st.session_state.trained_models[model_key].get_config()
                                key = config['registry_key']
                                fw = config['framework']
                                ext = {'sklearn': 'pkl', 'keras': 'h5', 'pytorch': 'pth'}[fw]
                                st.success(
                                    f"✅ Model saved to `{abs_dir}/`\n\n"
                                    f"**Files:** `{key}_config.json`, `{key}_weights.{ext}`"
                                )
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

        # ============================================================================
        # MODEL EVALUATION
        # ============================================================================
        elif page == "📈 Model Evaluation":
            st.header("Model Evaluation")

            if st.session_state.trained_models:
                model_name = st.selectbox("Select model:", list(st.session_state.trained_models.keys()))
                model = st.session_state.trained_models[model_name]

                if model.metrics:
                    st.subheader("Performance Metrics")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Training Metrics:**")
                        for key, value in model.metrics.get('train', {}).items():
                            if key != 'confusion_matrix':
                                st.metric(key.upper(), f"{value:.4f}")
                    with col2:
                        st.write("**Validation Metrics:**")
                        for key, value in model.metrics.get('val', {}).items():
                            if key != 'confusion_matrix':
                                st.metric(key.upper(), f"{value:.4f}")

                if model.history:
                    st.subheader("Learning Curves")
                    fig = st.session_state.visualizer.plot_learning_curves(model.history)
                    st.plotly_chart(fig, width='stretch')
            else:
                st.warning("⚠️ No trained models available. Train a model first!")

        # ============================================================================
        # PREDICTION
        # ============================================================================
        elif page == "🔮 Prediction":
            st.header("Make Predictions")

            # --- Load a saved model ---
            st.subheader("Load a Saved Model")
            load_dir = st.text_input("Model directory path:", DEFAULT_SAVE_DIR, key="prediction_load_dir")
            abs_load = os.path.abspath(load_dir)

            # Scan for available config files in the directory
            import glob as _glob_ui
            available_configs = sorted(_glob_ui.glob(os.path.join(abs_load, "*_config.json"))) if os.path.isdir(abs_load) else []
            available_models = []
            for cfg_path in available_configs:
                try:
                    with open(cfg_path, 'r') as _f:
                        cfg = json.load(_f)
                    available_models.append((cfg['registry_key'], cfg.get('name', cfg['registry_key']), cfg.get('framework', '?')))
                except Exception:
                    pass

            if available_models:
                model_options = [f"{name} ({fw}) — {key}" for key, name, fw in available_models]
                selected_idx = st.selectbox("Available models:", range(len(model_options)), format_func=lambda i: model_options[i], key="prediction_load_select")
                selected_key = available_models[selected_idx][0]

                if st.button("📂 Load Model", key="prediction_load_btn"):
                    try:
                        model = get_model(selected_key)
                        model.load(abs_load)
                        st.session_state.trained_models[selected_key] = model
                        st.session_state['_prediction_loaded_key'] = selected_key
                        st.success(f"✅ Loaded **{model.name}** ({model.framework}) from `{abs_load}/`")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.info(f"No saved models found in `{abs_load}/`. Train and save a model first.")

            # --- Show loaded model configuration ---
            loaded_key = st.session_state.get('_prediction_loaded_key')
            if loaded_key and loaded_key in st.session_state.trained_models:
                loaded_model = st.session_state.trained_models[loaded_key]
                config = loaded_model.get_config()
                st.subheader(f"Model Configuration — {config.get('name', loaded_key)}")
                st.json(config)

                st.markdown("---")

                st.subheader("Upload New Data")
                pred_file = st.file_uploader("Upload CSV for prediction:", type=['csv'])

                if pred_file:
                    pred_df = pd.read_csv(pred_file)
                    st.write("**Data Preview:**")
                    st.dataframe(pred_df.head())

                    # Let user choose target column
                    col_options = ["None (use all columns as input)"] + list(pred_df.columns)
                    target_choice = st.selectbox("Target column (output):", col_options, key="prediction_target_col")

                    if st.button("🔮 Generate Predictions"):
                        try:
                            if target_choice != "None (use all columns as input)":
                                input_df = pred_df.drop(columns=[target_choice])
                                actual = pred_df[target_choice]
                            else:
                                input_df = pred_df
                                actual = None

                            # Apply the same scaling used during training
                            input_values = input_df.values
                            scaler = st.session_state.preprocessor.scalers.get('default')
                            if scaler is not None:
                                try:
                                    input_values = scaler.transform(input_values)
                                    st.info("Scaling applied to input data using the training scaler.")
                                except Exception as scale_err:
                                    st.warning(f"Could not apply scaler: {scale_err}. Using raw data.")

                            predictions = loaded_model.predict(input_values)

                            # Convert probabilities to class indices if needed
                            if len(predictions.shape) > 1 and predictions.shape[1] > 1:
                                predictions = predictions.argmax(axis=1)

                            result_df = input_df.copy()
                            if actual is not None:
                                result_df['actual'] = actual.values
                            result_df['predictions'] = predictions

                            st.success("✅ Predictions generated!")
                            st.dataframe(result_df)

                            # Download predictions
                            csv = result_df.to_csv(index=False)
                            st.download_button(
                                "📥 Download Predictions",
                                csv,
                                "predictions.csv",
                                "text/csv"
                            )

                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            elif not available_models:
                st.warning("⚠️ No saved models found. Train and save a model first.")

        # ============================================================================
        # ADMIN PAGES  (only reachable by users with admin / superadmin role)
        # ============================================================================
        elif page == "📊 Dashboard":
            render_dashboard()

        elif page == "👥 User Management":
            render_user_management()

        elif page == "⚙️ Site Settings":
            render_settings_manager()

        elif page == "🔑 API Keys":
            render_api_keys()

        elif page == "📋 Error Logs":
            render_log_viewer()

        # ─── Separator pages (non-selectable dividers in radio) ──────────────────────
        elif page == "─── Admin ───":
            st.info("Select an admin module from the sidebar.")



except Exception as _page_exc:
    _err_id  = _gen_error_id()
    _tb_str  = _traceback.format_exc()
    _u_ctx   = get_current_user() or {}
    _log_exc(
        exc        = _page_exc,
        error_id   = _err_id,
        page       = page,
        user_email = _u_ctx.get('email'),
        user_role  = _u_ctx.get('role'),
        tb_str     = _tb_str,
    )
    _content_area.empty()  # clear any partial page output
    with _content_area.container():
        _render_err_page(_err_id, _tb_str if is_admin() else None)

# Footer
st.markdown("---")
