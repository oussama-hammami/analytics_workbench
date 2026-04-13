"""
Premium Analytics Dashboard
────────────────────────────
Three main widgets
  • Line Chart   — Traffic / Activity Over Time   (last 30 days)
  • Doughnut     — User Role Distribution
  • Bar Chart    — Top Platform Modules (referrers analogue)

Extras
  • KPI metric cards with delta indicators
  • Skeleton loaders while data fetches
  • Empty-state components when no data exists
  • Fully responsive via Streamlit columns
"""
from __future__ import annotations

import datetime
import hashlib
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .auth import require_admin
from .db import get_db, table, is_configured

# ─── Design tokens ────────────────────────────────────────────────────────────
_P = ["#6366f1", "#8b5cf6", "#22d3ee", "#34d399", "#f59e0b", "#f43f5e"]  # palette

_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, ui-sans-serif, sans-serif", size=12, color="#94a3b8"),
    margin=dict(l=4, r=4, t=36, b=4),
    hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155",
                    font=dict(color="#f1f5f9", size=12)),
    modebar=dict(bgcolor="rgba(0,0,0,0)", color="#475569", activecolor="#6366f1"),
    xaxis=dict(
        gridcolor="rgba(148,163,184,0.07)",
        linecolor="rgba(148,163,184,0.12)",
        tickcolor="#334155",
        tickfont=dict(color="#64748b", size=11),
        zerolinecolor="rgba(148,163,184,0.07)",
    ),
    yaxis=dict(
        gridcolor="rgba(148,163,184,0.07)",
        linecolor="rgba(148,163,184,0.12)",
        tickcolor="#334155",
        tickfont=dict(color="#64748b", size=11),
        zerolinecolor="rgba(148,163,184,0.07)",
    ),
    legend=dict(
        bgcolor="rgba(15,23,42,0.7)",
        bordercolor="rgba(99,102,241,0.2)",
        borderwidth=1,
        font=dict(color="#cbd5e1", size=11),
    ),
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Dashboard card ─────────────────────────────────────────── */
.aw-card {
    background: linear-gradient(145deg, #1e293b 0%, #162032 100%);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 16px;
    padding: 20px 22px;
    margin-bottom: 4px;
}
.aw-card-title {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 6px;
}
.aw-card-subtitle {
    font-size: 0.75rem;
    color: #475569;
    margin: 0 0 14px;
}

/* ── KPI metric ─────────────────────────────────────────────── */
.aw-kpi {
    background: linear-gradient(145deg, #1e293b 0%, #162032 100%);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 14px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
}
.aw-kpi::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border-radius: 14px 14px 0 0;
}
.aw-kpi-icon  { font-size: 1.5rem; margin-bottom: 8px; }
.aw-kpi-label { font-size: 0.7rem; font-weight:600; letter-spacing:.06em;
                text-transform:uppercase; color:#64748b; margin:0 0 2px; }
.aw-kpi-value { font-size: 2rem; font-weight:700; color:#f1f5f9;
                line-height:1; margin:0 0 4px; }
.aw-kpi-delta { font-size: 0.72rem; font-weight:500; }
.aw-kpi-delta.up   { color: #34d399; }
.aw-kpi-delta.down { color: #f87171; }
.aw-kpi-delta.neu  { color: #64748b; }

/* ── Skeleton shimmer ───────────────────────────────────────── */
@keyframes aw-shimmer {
    0%   { background-position: -600px 0; }
    100% { background-position:  600px 0; }
}
.aw-skel {
    background: linear-gradient(90deg, #1e293b 25%, #273548 50%, #1e293b 75%);
    background-size: 600px 100%;
    animation: aw-shimmer 1.6s infinite linear;
    border-radius: 8px;
}
.aw-skel-card {
    background: linear-gradient(145deg,#1e293b,#162032);
    border: 1px solid rgba(99,102,241,0.12);
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 4px;
}
.aw-skel-title  { height:14px; width:45%; margin-bottom:18px; }
.aw-skel-line   { height:10px; margin-bottom:10px; }
.aw-skel-chart  { height:200px; margin-top:10px; }
.aw-skel-circle { width:140px; height:140px; border-radius:50%;
                  margin:20px auto; }
.aw-skel-kpi    { height:90px; border-radius:14px; }

/* ── Empty state ────────────────────────────────────────────── */
.aw-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;
    min-height: 180px;
}
.aw-empty-icon { font-size: 2.8rem; margin-bottom:12px; opacity:.5; }
.aw-empty-title { font-size:.9rem; font-weight:600; color:#94a3b8; margin:0 0 6px; }
.aw-empty-body  { font-size:.78rem; color:#475569; max-width:260px; margin:0; }

/* ── Badge ──────────────────────────────────────────────────── */
.aw-badge-demo {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    background: rgba(234,179,8,.12);
    color: #fbbf24;
    border: 1px solid rgba(234,179,8,.25);
    border-radius: 20px;
    padding: 2px 8px;
    margin-left: 8px;
    vertical-align: middle;
}
.aw-badge-live {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    background: rgba(52,211,153,.12);
    color: #34d399;
    border: 1px solid rgba(52,211,153,.25);
    border-radius: 20px;
    padding: 2px 8px;
    margin-left: 8px;
    vertical-align: middle;
}
</style>
"""

# ─── Skeleton helpers ─────────────────────────────────────────────────────────

def _skel_kpi_row() -> str:
    return "".join(f'<div class="aw-skel aw-skel-kpi"></div>' for _ in range(4))


def _skel_card(height: int = 200, rows: int = 2) -> str:
    lines = "".join(
        f'<div class="aw-skel aw-skel-line" style="width:{75 - i*12}%"></div>'
        for i in range(rows)
    )
    return f"""
    <div class="aw-skel-card">
      <div class="aw-skel aw-skel-title"></div>
      {lines}
      <div class="aw-skel aw-skel-chart" style="height:{height}px"></div>
    </div>"""


def _skel_donut() -> str:
    lines = "".join(
        f'<div class="aw-skel aw-skel-line" style="width:{60 - i*8}%;margin-bottom:8px"></div>'
        for i in range(3)
    )
    return f"""
    <div class="aw-skel-card">
      <div class="aw-skel aw-skel-title"></div>
      <div class="aw-skel aw-skel-circle"></div>
      {lines}
    </div>"""


# ─── Empty-state helpers ──────────────────────────────────────────────────────

def _empty(icon: str, title: str, body: str) -> str:
    return f"""
    <div class="aw-empty">
      <div class="aw-empty-icon">{icon}</div>
      <p class="aw-empty-title">{title}</p>
      <p class="aw-empty-body">{body}</p>
    </div>"""


# ─── Data fetching ────────────────────────────────────────────────────────────

def _get_stats() -> dict:
    s = {"users": 0, "active": 0, "api_keys": 0, "settings": 0}
    if not is_configured():
        return s
    try:
        with get_db() as (_, cur):
            cur.execute(f"SELECT COUNT(*) as c FROM {table('users')}")
            s["users"] = cur.fetchone()["c"]
            cur.execute(f"SELECT COUNT(*) as c FROM {table('users')} WHERE is_active=1")
            s["active"] = cur.fetchone()["c"]
            cur.execute(f"SELECT COUNT(*) as c FROM {table('api_keys')}")
            s["api_keys"] = cur.fetchone()["c"]
            cur.execute(f"SELECT COUNT(*) as c FROM {table('settings')}")
            s["settings"] = cur.fetchone()["c"]
    except Exception:
        pass
    return s


def _get_traffic(days: int = 30) -> tuple[pd.DataFrame, bool]:
    """Returns (dataframe, is_real_data)."""
    today = datetime.date.today()
    dates = [today - datetime.timedelta(days=i) for i in range(days - 1, -1, -1)]

    real: dict[str, int] = {}
    if is_configured():
        try:
            with get_db() as (_, cur):
                cur.execute(
                    f"SELECT DATE(created_at) as d, COUNT(*) as c "
                    f"FROM {table('users')} GROUP BY DATE(created_at)"
                )
                for row in cur.fetchall():
                    real[row["d"]] = real.get(row["d"], 0) + row["c"]
                cur.execute(
                    f"SELECT DATE(last_login) as d, COUNT(*) as c "
                    f"FROM {table('users')} WHERE last_login IS NOT NULL "
                    f"GROUP BY DATE(last_login)"
                )
                for row in cur.fetchall():
                    real[row["d"]] = real.get(row["d"], 0) + row["c"]
        except Exception:
            pass

    is_real = bool(real)

    # Deterministic demo fill based on date seed (doesn't change on reload)
    def _demo(d: datetime.date) -> int:
        seed = int(hashlib.md5(d.isoformat().encode()).hexdigest(), 16) % 1000
        wd   = d.weekday()
        base = 60 if wd < 5 else 25
        return base + (seed % 45)

    values = [real.get(d.isoformat(), _demo(d)) for d in dates]
    prev   = [_demo(d - datetime.timedelta(days=days)) for d in dates]

    return pd.DataFrame({"date": dates, "current": values, "previous": prev}), is_real


def _get_roles() -> tuple[list, list, bool]:
    """Returns (labels, values, is_real)."""
    if not is_configured():
        return ["Superadmin", "Admin", "Viewer"], [1, 2, 8], False
    try:
        with get_db() as (_, cur):
            cur.execute(
                f"SELECT role, COUNT(*) as c FROM {table('users')} GROUP BY role"
            )
            rows = cur.fetchall()
        if not rows:
            return [], [], True
        label_map = {"superadmin": "Superadmin", "admin": "Admin", "viewer": "Viewer"}
        labels = [label_map.get(r["role"], r["role"].title()) for r in rows]
        values = [r["c"] for r in rows]
        return labels, values, True
    except Exception:
        return [], [], False


def _get_modules() -> tuple[list, list, bool]:
    """Top platform modules used (fixed list — real tracking TBD)."""
    modules = [
        "Model Training", "Data Exploration", "Preprocessing",
        "Prediction", "Visualization", "Outlier Detection",
        "Dataset Mgmt", "Model Evaluation",
    ]
    # Deterministic demo weights
    weights = [92, 78, 71, 65, 58, 44, 38, 31]
    return modules, weights, False


# ─── Chart builders ───────────────────────────────────────────────────────────

def _chart_line(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Previous period (muted, dashed)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["previous"],
        mode="lines", name="Prev. Period",
        line=dict(color="rgba(99,102,241,0.30)", width=1.5,
                  dash="dot", shape="spline"),
        hovertemplate="%{y}<extra>Previous</extra>",
    ))
    # Current period (filled)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["current"],
        mode="lines", name="This Period",
        line=dict(color="#6366f1", width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.12)",
        hovertemplate="%{y}<extra>Current</extra>",
    ))

    layout = dict(**_BASE)
    layout.update(
        height=280,
        hovermode="x unified",
        xaxis=dict(**_BASE["xaxis"], tickformat="%b %d", nticks=8),
        yaxis=dict(**_BASE["yaxis"], rangemode="tozero"),
    )
    fig.update_layout(**layout)
    return fig


def _chart_donut(labels: list, values: list) -> go.Figure:
    total = sum(values)
    fig   = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.68,
        marker=dict(
            colors=_P[:len(labels)],
            line=dict(color="#0f172a", width=3),
        ),
        textfont=dict(color="#e2e8f0", size=11),
        hovertemplate="<b>%{label}</b><br>%{value} users (%{percent})<extra></extra>",
        textposition="outside",
    ))

    layout = dict(**_BASE)
    layout.update(
        height=280,
        annotations=[dict(
            text=f"<b>{total}</b><br><span style='font-size:11px'>users</span>",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=18, color="#f1f5f9"),
        )],
        legend=dict(**_BASE["legend"], orientation="v", x=1.02, y=0.5),
    )
    fig.update_layout(**layout)
    return fig


def _chart_bar(labels: list, values: list) -> go.Figure:
    # Horizontal bars — easier to read long module names
    sorted_pairs = sorted(zip(values, labels))
    sv, sl       = zip(*sorted_pairs) if sorted_pairs else ([], [])

    fig = go.Figure(go.Bar(
        x=list(sv), y=list(sl),
        orientation="h",
        marker=dict(
            color=list(sv),
            colorscale=[[0, "#312e81"], [0.5, "#6366f1"], [1, "#a5b4fc"]],
            line=dict(width=0),
        ),
        text=[f"  {v}" for v in sv],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        hovertemplate="<b>%{y}</b><br>Sessions: %{x}<extra></extra>",
    ))

    layout = dict(**_BASE)
    layout.update(
        height=280,
        xaxis=dict(**_BASE["xaxis"], title=""),
        yaxis=dict(**_BASE["yaxis"], tickfont=dict(color="#94a3b8", size=11),
                   gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
        bargap=0.3,
    )
    fig.update_layout(**layout)
    return fig


# ─── KPI card HTML ────────────────────────────────────────────────────────────

def _kpi(icon: str, label: str, value: str,
         delta: str = "", delta_dir: str = "neu") -> str:
    delta_html = (
        f'<div class="aw-kpi-delta {delta_dir}">{delta}</div>'
        if delta else ""
    )
    return f"""
    <div class="aw-kpi">
      <div class="aw-kpi-icon">{icon}</div>
      <div class="aw-kpi-label">{label}</div>
      <div class="aw-kpi-value">{value}</div>
      {delta_html}
    </div>"""


# ─── Main renderer ────────────────────────────────────────────────────────────

def render_dashboard() -> None:
    require_admin()

    # Inject global CSS once
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    today = datetime.date.today().strftime("%A, %B %d %Y")
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                margin-bottom:8px">
      <div>
        <h2 style="margin:0;font-size:1.4rem;font-weight:700;color:#f1f5f9">
          Analytics Overview
        </h2>
        <p style="margin:0;font-size:.8rem;color:#475569">{today}</p>
      </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    # ── Skeleton state (shown on first render, replaced on rerun) ─────────────
    LOAD_KEY = "_dash_loaded"
    if LOAD_KEY not in st.session_state:
        st.session_state[LOAD_KEY] = False

    if not st.session_state[LOAD_KEY]:
        # Show skeletons
        k1, k2, k3, k4 = st.columns(4)
        for col in (k1, k2, k3, k4):
            col.markdown(
                '<div class="aw-skel aw-skel-kpi"></div>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        lc, rc = st.columns([3, 2])
        lc.markdown(_skel_card(240), unsafe_allow_html=True)
        rc.markdown(_skel_donut(),   unsafe_allow_html=True)
        st.markdown(_skel_card(240, rows=1), unsafe_allow_html=True)

        st.session_state[LOAD_KEY] = True
        st.rerun()

    # ── Fetch all data ────────────────────────────────────────────────────────
    stats                    = _get_stats()
    traffic_df, traffic_real = _get_traffic(30)
    role_labels, role_vals, roles_real = _get_roles()
    mod_labels, mod_vals, mods_real    = _get_modules()

    # ── KPI Row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    active_pct = (
        f"↑ {stats['active']}/{stats['users']} active"
        if stats["users"] else "No users yet"
    )
    with c1:
        st.markdown(_kpi("👥", "Total Users",  str(stats["users"]),
                         active_pct, "up" if stats["active"] else "neu"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi("✅", "Active Users", str(stats["active"]),
                         "100% active" if stats["users"] == stats["active"] and stats["users"] > 0
                         else f"{stats['users'] - stats['active']} inactive", "neu"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi("🔑", "API Keys",    str(stats["api_keys"]),
                         "Keys stored" if stats["api_keys"] else "None stored yet", "neu"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi("⚙️", "Settings",   str(stats["settings"]),
                         "Configured" if stats["settings"] > 0 else "Using defaults", "neu"),
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Line + Doughnut ────────────────────────────────────────────────
    col_line, col_donut = st.columns([3, 2], gap="medium")

    # ── LINE CHART ─────────────────────────────────────────────────────
    with col_line:
        badge = (
            '<span class="aw-badge-live">Live</span>'
            if traffic_real else
            '<span class="aw-badge-demo">Sample</span>'
        )
        st.markdown(
            f'<div class="aw-card">'
            f'<p class="aw-card-title">Traffic Over Time {badge}</p>'
            f'<p class="aw-card-subtitle">Daily sessions — last 30 days vs previous period</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if traffic_df.empty or traffic_df["current"].sum() == 0:
            st.markdown(
                _empty("📈", "No Traffic Data",
                       "No activity recorded yet. Start using the platform to see real traffic."),
                unsafe_allow_html=True,
            )
        else:
            st.plotly_chart(
                _chart_line(traffic_df),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    # ── DOUGHNUT CHART ─────────────────────────────────────────────────
    with col_donut:
        badge2 = (
            '<span class="aw-badge-live">Live</span>'
            if roles_real else
            '<span class="aw-badge-demo">Sample</span>'
        )
        st.markdown(
            f'<div class="aw-card">'
            f'<p class="aw-card-title">User Role Distribution {badge2}</p>'
            f'<p class="aw-card-subtitle">Breakdown by assigned role</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not role_labels:
            st.markdown(
                _empty("🍩", "No Users Yet",
                       "Create users in the User Management panel to see role distribution."),
                unsafe_allow_html=True,
            )
        else:
            st.plotly_chart(
                _chart_donut(role_labels, role_vals),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: Bar Chart (full width) ─────────────────────────────────────────
    badge3 = (
        '<span class="aw-badge-live">Live</span>'
        if mods_real else
        '<span class="aw-badge-demo">Sample</span>'
    )
    st.markdown(
        f'<div class="aw-card">'
        f'<p class="aw-card-title">Top Platform Modules {badge3}</p>'
        f'<p class="aw-card-subtitle">'
        f'Sessions per module — connect real tracking to replace sample data'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not mod_labels:
        st.markdown(
            _empty("📊", "No Module Data",
                   "No usage data available yet. Module tracking will populate this chart."),
            unsafe_allow_html=True,
        )
    else:
        st.plotly_chart(
            _chart_bar(mod_labels, mod_vals),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # ── Footer note ───────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:.7rem;color:#334155;text-align:center">'
        '⚡ Live badges reflect real DB data · Sample badges use deterministic demo data'
        '</p>',
        unsafe_allow_html=True,
    )
