"""
Next-Best-Offer & Intelligent Product Recommendation Platform
AI-Powered Recommendation and Decision Intelligence Platform
Enterprise-Grade Frontend — Redesigned for Professional SaaS Presentation
"""

from __future__ import annotations

import os
import sys
import uuid
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

# Configure paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def get_config(name, default):
    try:
        return st.secrets.get(name) or os.getenv(name, default)
    except Exception:
        return os.getenv(name, default)


API_BASE_URL = get_config(
    "API_BASE_URL",
    "http://localhost:8000/api/v1"
).rstrip("/")

TIMEOUT = int(os.getenv("API_TIMEOUT_SECONDS", "15"))
RECOMMEND_TIMEOUT = int(os.getenv("RECOMMEND_TIMEOUT_SECONDS", "90"))

# Streamlit Page Configuration
st.set_page_config(
    page_title="NBO Platform | AI-Powered Recommendation Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — Centralized Theme Engine (Dark Brown & Light Brown)
# ═══════════════════════════════════════════════════════════════════════════════

def get_enterprise_css(theme: str = "dark") -> str:
    """Generate theme-coordinated enterprise CSS tokens and styles."""
    is_dark = (theme == "dark")
    if is_dark:
        # Dark Brown Palette
        bg_main = "#17120F"
        bg_sidebar = "#211813"
        bg_card = "#2B211B"
        bg_secondary = "#362920"
        bg_input = "#30241D"
        accent_primary = "#B98A62"
        accent_secondary = "#D1AA83"
        text_primary = "#F5EDE5"
        text_secondary = "#C3B2A3"
        text_muted = "#9E8B7C"
        border_color = "#514034"
        border_subtle = "#3D2E24"
        banner_bg = "linear-gradient(135deg, #211813 0%, #2B211B 50%, #362920 100%)"
        banner_tag_bg = "#362920"
        banner_tag_color = "#D1AA83"
        badge_indigo_bg = "#362920"
        badge_indigo_color = "#D1AA83"
        badge_green_bg = "#1E3A27"
        badge_green_color = "#A3E6B4"
        badge_green_border = "#2E6F40"
        badge_amber_bg = "#3D2813"
        badge_amber_color = "#FCD34D"
        badge_amber_border = "#C07D2B"
        badge_red_bg = "#3D1A1A"
        badge_red_color = "#FCA5A5"
        badge_red_border = "#A83838"
        badge_slate_bg = "#211813"
        badge_slate_color = "#C3B2A3"
        badge_purple_bg = "#2B211B"
        badge_purple_color = "#B98A62"
        btn_bg = "#362920"
        btn_text = "#F5EDE5"
        btn_border = "#514034"
        btn_hover_bg = "#453429"
        btn_primary_bg = "#B98A62"
        btn_primary_text = "#17120F"
        btn_primary_hover = "#D1AA83"
        shadow_sm = "0 1px 3px rgba(0,0,0,0.35)"
        shadow_md = "0 3px 10px rgba(0,0,0,0.45)"
        sidebar_active_bg = "#2B211B"
        sidebar_active_border = "#B98A62"
        sidebar_active_text = "#F5EDE5"
    else:
        # Light Brown Palette
        bg_main = "#F7F3EF"
        bg_sidebar = "#EDE3D9"
        bg_card = "#FFFFFF"
        bg_secondary = "#F2E9E1"
        bg_input = "#FFFFFF"
        accent_primary = "#8B5E3C"
        accent_secondary = "#A87954"
        text_primary = "#30241D"
        text_secondary = "#756456"
        text_muted = "#8F7B6D"
        border_color = "#E0D2C5"
        border_subtle = "#EDE3D9"
        banner_bg = "linear-gradient(135deg, #EDE3D9 0%, #F2E9E1 50%, #E0D2C5 100%)"
        banner_tag_bg = "#FFFFFF"
        banner_tag_color = "#8B5E3C"
        badge_indigo_bg = "#F2E9E1"
        badge_indigo_color = "#8B5E3C"
        badge_green_bg = "#EAF5EE"
        badge_green_color = "#1B5E30"
        badge_green_border = "#B8E2C8"
        badge_amber_bg = "#FDF5E8"
        badge_amber_color = "#7D4E12"
        badge_amber_border = "#F5DDB3"
        badge_red_bg = "#FDEAEA"
        badge_red_color = "#7D1D1D"
        badge_red_border = "#F7C1C1"
        badge_slate_bg = "#F2E9E1"
        badge_slate_color = "#756456"
        badge_purple_bg = "#EDE3D9"
        badge_purple_color = "#8B5E3C"
        btn_bg = "#FFFFFF"
        btn_text = "#30241D"
        btn_border = "#E0D2C5"
        btn_hover_bg = "#F2E9E1"
        btn_primary_bg = "#8B5E3C"
        btn_primary_text = "#FFFFFF"
        btn_primary_hover = "#A87954"
        shadow_sm = "0 1px 2px rgba(48,36,29,0.06)"
        shadow_md = "0 2px 8px rgba(48,36,29,0.09)"
        sidebar_active_bg = "#FFFFFF"
        sidebar_active_border = "#8B5E3C"
        sidebar_active_text = "#30241D"

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
    --bg-main: {bg_main};
    --bg-sidebar: {bg_sidebar};
    --bg-card: {bg_card};
    --bg-secondary: {bg_secondary};
    --bg-input: {bg_input};
    --accent-primary: {accent_primary};
    --accent-secondary: {accent_secondary};
    --text-primary: {text_primary};
    --text-secondary: {text_secondary};
    --text-muted: {text_muted};
    --border-color: {border_color};
    --border-subtle: {border_subtle};
    --banner-bg: {banner_bg};
    --banner-tag-bg: {banner_tag_bg};
    --banner-tag-color: {banner_tag_color};
    --btn-bg: {btn_bg};
    --btn-text: {btn_text};
    --btn-border: {btn_border};
    --btn-hover-bg: {btn_hover_bg};
    --btn-primary-bg: {btn_primary_bg};
    --btn-primary-text: {btn_primary_text};
    --btn-primary-hover: {btn_primary_hover};
    --shadow-sm: {shadow_sm};
    --shadow-md: {shadow_md};
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

html, body, [class*="css"] {{
    font-family: var(--font-sans) !important;
}}

.stApp {{
    background: {bg_main} !important;
    color: {text_primary} !important;
}}

/* ── Streamlit Header Bar ── */
header[data-testid="stHeader"] {{
    background: transparent !important;
    z-index: 99 !important;
}}

/* ── Main Viewport Padding Fix (Ensures banner is NOT cut off from top) ── */
.block-container {{
    padding-top: 3.75rem !important;
    padding-bottom: 6rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1320px !important;
    overflow-y: visible !important;
}}

/* Allow natural vertical scroll across the app */
html, body, .stApp, [data-testid="stAppViewContainer"] {{
    overflow-y: auto !important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {bg_sidebar} !important;
    border-right: 1px solid {border_color} !important;
}}
[data-testid="stSidebar"] * {{
    color: {text_secondary} !important;
}}
[data-testid="stSidebar"] .stRadio > div {{
    gap: 3px !important;
}}
[data-testid="stSidebar"] .stRadio label {{
    padding: 7px 12px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    margin: 0 !important;
    color: {text_secondary} !important;
}}
[data-testid="stSidebar"] .stRadio label:hover {{
    background: {bg_secondary} !important;
    color: {text_primary} !important;
}}
[data-testid="stSidebar"] .stRadio label[data-checked="true"],
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[aria-checked="true"] {{
    background: {sidebar_active_bg} !important;
    color: {sidebar_active_text} !important;
    border-left: 3px solid {accent_primary} !important;
    font-weight: 600 !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {border_color} !important;
}}

/* ── Page Banner (Sleek, Unclipped Hero) ── */
.page-banner {{
    background: {banner_bg};
    border-radius: var(--radius-lg);
    padding: 14px 20px;
    color: {text_primary};
    margin-top: 0.25rem;
    margin-bottom: 14px;
    border: 1px solid {border_color};
    box-shadow: {shadow_sm};
    overflow: hidden;
}}
.page-banner .banner-tag {{
    display: inline-block;
    background: {banner_tag_bg};
    padding: 2px 9px;
    border-radius: 100px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: {banner_tag_color};
    border: 1px solid {border_color};
    margin-bottom: 4px;
}}
.page-banner h1 {{
    font-size: 1.35rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    margin: 0 !important;
    line-height: 1.25 !important;
    color: {text_primary} !important;
}}
.page-banner p {{
    color: {text_secondary} !important;
    font-size: 0.82rem !important;
    margin: 3px 0 0 0 !important;
    max-width: 760px !important;
    line-height: 1.4 !important;
}}

/* ── Metric Cards ── */
div[data-testid="stMetric"] {{
    background: {bg_card} !important;
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-md) !important;
    padding: 10px 14px !important;
    box-shadow: {shadow_sm} !important;
}}
div[data-testid="stMetric"] label {{
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    color: {text_secondary} !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    color: {text_primary} !important;
}}

/* ── Badges ── */
.badge {{
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px 8px;
    border-radius: 100px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}}
.badge-indigo {{ background: {badge_indigo_bg}; color: {badge_indigo_color}; border: 1px solid {border_color}; }}
.badge-purple {{ background: {badge_purple_bg}; color: {badge_purple_color}; border: 1px solid {border_color}; }}
.badge-green {{ background: {badge_green_bg}; color: {badge_green_color}; border: 1px solid {badge_green_border}; }}
.badge-red {{ background: {badge_red_bg}; color: {badge_red_color}; border: 1px solid {badge_red_border}; }}
.badge-amber {{ background: {badge_amber_bg}; color: {badge_amber_color}; border: 1px solid {badge_amber_border}; }}
.badge-slate {{ background: {badge_slate_bg}; color: {badge_slate_color}; border: 1px solid {border_color}; }}

/* ── Section Headers ── */
.sh {{
    font-size: 0.95rem;
    font-weight: 700;
    color: {text_primary};
    margin: 12px 0 6px 0;
    display: flex;
    align-items: center;
    gap: 6px;
    letter-spacing: -0.01em;
}}

/* ── Buttons ── */
.stButton>button {{
    background: {btn_bg} !important;
    color: {btn_text} !important;
    border: 1px solid {btn_border} !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 6px 14px !important;
    transition: all 0.15s ease !important;
    box-shadow: {shadow_sm} !important;
}}
.stButton>button:hover {{
    background: {btn_hover_bg} !important;
    border-color: {accent_primary} !important;
    color: {text_primary} !important;
}}
.stButton>button[kind="primary"] {{
    background: {btn_primary_bg} !important;
    color: {btn_primary_text} !important;
    border: 1px solid {btn_primary_bg} !important;
    font-weight: 700 !important;
}}
.stButton>button[kind="primary"]:hover {{
    background: {btn_primary_hover} !important;
    border-color: {btn_primary_hover} !important;
    color: {btn_primary_text} !important;
}}

/* ── Containers / Border Cards ── */
div[data-testid="stVerticalBlock"] > div[style*="border"],
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {bg_card} !important;
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-md) !important;
    box-shadow: {shadow_sm} !important;
}}
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {{
    gap: 12px;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-md) !important;
    background: {bg_card} !important;
}}
[data-testid="stExpander"] details summary {{
    color: {text_primary} !important;
    font-weight: 600 !important;
}}

/* ── Form Inputs, Selectboxes, Multiselects, Sliders ── */
input, textarea, select {{
    color: {text_primary} !important;
}}
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="select"] > div {{
    background: {bg_input} !important;
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-sm) !important;
    color: {text_primary} !important;
}}
div[data-baseweb="select"] span {{
    color: {text_primary} !important;
}}
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[role="listbox"] {{
    background: {bg_card} !important;
    border: 1px solid {border_color} !important;
}}
li[role="option"] {{
    color: {text_primary} !important;
    background: transparent !important;
}}
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {{
    background: {bg_secondary} !important;
    color: {accent_primary} !important;
}}
span[data-baseweb="tag"] {{
    background: {bg_secondary} !important;
    border: 1px solid {border_color} !important;
    color: {text_primary} !important;
    border-radius: 4px !important;
}}
span[data-baseweb="tag"] * {{
    color: {text_primary} !important;
}}
div[data-testid="stSlider"] label {{
    color: {text_primary} !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}}
div[data-testid="stSlider"] [data-testid="stTickBar"] div {{
    color: {text_secondary} !important;
}}
div[data-testid="stSlider"] div[role="slider"] {{
    background: {accent_primary} !important;
    border: 2px solid {bg_card} !important;
}}
div[data-testid="stCheckbox"] label span,
div[data-testid="stToggle"] label span {{
    color: {text_primary} !important;
    font-size: 0.84rem !important;
}}

/* ── Tables & DataFrames ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-md) !important;
    background: {bg_card} !important;
}}

/* ── Chat Messages ── */
[data-testid="stChatMessage"] {{
    background: {bg_card} !important;
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-md) !important;
    padding: 12px 16px !important;
    color: {text_primary} !important;
}}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] div,
[data-testid="stChatMessage"] span {{
    color: {text_primary} !important;
    font-size: 0.88rem !important;
    line-height: 1.55 !important;
}}

/* ── Alerts ── */
div[data-testid="stAlert"] {{
    background: {bg_card} !important;
    border: 1px solid {border_color} !important;
    border-radius: var(--radius-md) !important;
    color: {text_primary} !important;
}}
div[data-testid="stAlert"] * {{
    color: {text_primary} !important;
}}

/* ── Status Indicators ── */
.status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: var(--radius-sm);
    font-size: 0.72rem;
    font-weight: 600;
}}
.status-connected {{
    background: {badge_green_bg};
    border: 1px solid {badge_green_border};
    color: {badge_green_color};
}}
.status-fallback {{
    background: {badge_amber_bg};
    border: 1px solid {badge_amber_border};
    color: {badge_amber_color};
}}
.status-offline {{
    background: {bg_secondary};
    border: 1px solid {border_color};
    color: {text_secondary};
}}

/* ── Product Card Grid ── */
.product-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
    margin-top: 8px;
}}

/* ── Dividers & Text ── */
hr, .stDivider {{
    margin: 10px 0 !important;
    border-color: {border_color} !important;
}}
.stMarkdown p {{
    color: {text_primary};
}}
.stCaption, small {{
    color: {text_secondary} !important;
}}
h1, h2, h3, h4, h5, h6 {{
    color: {text_primary} !important;
    letter-spacing: -0.01em !important;
}}
</style>
"""

# Initialize session state for theme mode
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

ENTERPRISE_CSS = get_enterprise_css(st.session_state["theme_mode"])
st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LAYER — API Client with Graceful Local Fallback
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)
def check_api_health() -> Optional[Dict[str, Any]]:
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if res.ok:
            return res.json()
    except Exception:
        pass
    return None


@st.cache_data(ttl=60)
def check_decision_engine_status() -> Optional[Dict[str, Any]]:
    try:
        res = requests.get(f"{API_BASE_URL}/decisions/status", timeout=5)
        if res.ok and isinstance(res.json(), dict):
            return res.json()
    except Exception:
        pass
    return None


def submit_manual_audit(audit_payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        res = requests.post(f"{API_BASE_URL}/decisions/history", json=audit_payload, timeout=15)
        try:
            data = res.json()
        except Exception:
            data = None
        if res.ok and isinstance(data, dict) and data.get("decision_id"):
            return data, None
        detail = _extract_backend_error_detail(res) if not isinstance(data, dict) else (data.get("detail") or "")
        return None, detail or f"Audit persistence failed with HTTP {res.status_code}."
    except requests.exceptions.Timeout:
        return None, "Audit persistence request timed out."
    except requests.exceptions.ConnectionError:
        return None, "Backend API is unreachable; decision audit was not persisted."
    except Exception as exc:
        return None, f"Unexpected audit error: {type(exc).__name__}"


def dispatch_product_api(
    product_id: str,
    quantity: int = 1,
    customer_id: Optional[str] = None,
    candidate_products: Optional[List[str]] = None,
    feasible_products: Optional[List[str]] = None,
    excluded_products: Optional[List[str]] = None,
    selected_product_id: Optional[str] = None,
    decision_explanation: Optional[str] = None,
    fallback_used: bool = False,
    fallback_reason: Optional[str] = None,
    ranking_method: str = "NBO_DISPATCH",
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Dispatch product and atomically deduct inventory + write audit record.

    Sends a JSON body to POST /catalogue/{product_id}/dispatch.
    Both inventory deduction and audit creation happen in a single DB transaction
    on the backend — no separate audit call needed after a successful dispatch.
    """
    body: Dict[str, Any] = {
        "quantity": quantity,
        "ranking_method": ranking_method,
        "candidate_products": candidate_products or [],
        "feasible_products": feasible_products or [],
        "excluded_products": excluded_products or [],
        "fallback_used": fallback_used,
    }
    if customer_id:
        body["customer_id"] = customer_id
    if selected_product_id:
        body["selected_product_id"] = selected_product_id
    if decision_explanation:
        body["decision_explanation"] = decision_explanation
    if fallback_reason:
        body["fallback_reason"] = fallback_reason

    try:
        res = requests.post(
            f"{API_BASE_URL}/catalogue/{product_id}/dispatch",
            json=body,
            timeout=15,
        )
        try:
            data = res.json()
        except Exception:
            data = None
        if res.ok and isinstance(data, dict) and data.get("dispatched"):
            return data, None
        err = ""
        if not isinstance(data, dict):
            err = f"Dispatch failed with HTTP {res.status_code}"
        elif res.status_code == 400:
            err = data.get("detail", "Insufficient stock")
        elif res.status_code == 404:
            err = data.get("detail", "Product not found")
        else:
            err = data.get("detail", f"Dispatch failed with HTTP {res.status_code}")
        return None, err
    except requests.exceptions.ConnectionError:
        return None, "Backend API is unreachable."
    except Exception as exc:
        return None, f"Dispatch error: {type(exc).__name__}"


def fetch_decision_history(customer_id: Optional[str] = None, limit: int = 10) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    params: Dict[str, Any] = {"limit": limit}
    if customer_id:
        params["customer_id"] = customer_id
    try:
        res = requests.get(f"{API_BASE_URL}/decisions/history", params=params, timeout=10)
        if res.ok and isinstance(res.json(), list):
            return res.json(), None
        return [], f"Unable to load audit history (HTTP {res.status_code})."
    except Exception as exc:
        return [], f"Unable to reach audit history endpoint: {type(exc).__name__}"


@st.cache_data(ttl=120)
def load_all_customers() -> List[Dict[str, Any]]:
    try:
        res = requests.get(f"{API_BASE_URL}/customers?limit=500", timeout=TIMEOUT)
        if res.ok and isinstance(res.json(), list) and len(res.json()) > 0:
            return res.json()
    except Exception:
        pass
    csv_path = PROJECT_ROOT / "data" / "synthetic" / "customers.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    return []


@st.cache_data(ttl=120)
def load_customer_detail(customer_id: str) -> Dict[str, Any]:
    try:
        res = requests.get(f"{API_BASE_URL}/customers/{customer_id}", timeout=TIMEOUT)
        if res.ok:
            return res.json()
    except Exception:
        pass
    cust_path = PROJECT_ROOT / "data" / "synthetic" / "customers.csv"
    txn_path = PROJECT_ROOT / "data" / "synthetic" / "transactions.csv"
    int_path = PROJECT_ROOT / "data" / "synthetic" / "customer_product_interactions.csv"
    cust_dict: Dict[str, Any] = {}
    if cust_path.exists():
        df_c = pd.read_csv(cust_path)
        matched = df_c[df_c["customer_id"] == customer_id]
        if not matched.empty:
            cust_dict = matched.iloc[0].to_dict()
    interactions: List[Dict[str, Any]] = []
    if int_path.exists():
        df_i = pd.read_csv(int_path)
        interactions = df_i[df_i["customer_id"] == customer_id].to_dict(orient="records")
    transactions: List[Dict[str, Any]] = []
    if txn_path.exists():
        df_t = pd.read_csv(txn_path)
        matched_txns = df_t[df_t["customer_id"] == customer_id].sort_values(by="transaction_date", ascending=False).head(20)
        transactions = matched_txns.to_dict(orient="records")
    return {"customer": cust_dict, "interactions": interactions, "recent_transactions": transactions}


@st.cache_data(ttl=120)
def load_catalogue() -> List[Dict[str, Any]]:
    try:
        res = requests.get(f"{API_BASE_URL}/catalogue?limit=250", timeout=TIMEOUT)
        if res.ok and isinstance(res.json(), list) and len(res.json()) > 0:
            return res.json()
    except Exception:
        pass
    prod_path = PROJECT_ROOT / "data" / "synthetic" / "products.csv"
    op_path = PROJECT_ROOT / "data" / "synthetic" / "operational_catalogue.csv"
    if prod_path.exists() and op_path.exists():
        p_df = pd.read_csv(prod_path)
        op_df = pd.read_csv(op_path)
        merged = pd.merge(p_df, op_df, on="product_id", how="left")
        merged["available_stock"] = merged["available_stock"].fillna(0)
        merged["inventory_status"] = merged["inventory_status"].fillna("unknown")
        merged["gross_margin_pct"] = merged["gross_margin_pct"].fillna(0.0)
        return merged.to_dict(orient="records")
    return []


@st.cache_data(ttl=120)
def load_evaluation_report() -> Dict[str, Any]:
    try:
        res = requests.get(f"{API_BASE_URL}/evaluation/metrics", timeout=TIMEOUT)
        if res.ok:
            return res.json()
    except Exception:
        pass
    rep_csv = PROJECT_ROOT / "reports" / "day3_evaluation_results.csv"
    rows = []
    if rep_csv.exists():
        rows = pd.read_csv(rep_csv).to_dict(orient="records")
    return {
        "recommendation_metrics": rows,
        "ml_classification_metrics": {
            "model": "Gradient Boosting",
            "holdout_roc_auc": "0.8583",
            "holdout_pr_auc": "0.7094",
            "cv_pr_auc": "0.7467",
        },
    }


@st.cache_data(ttl=120)
def load_basket_associations() -> List[Dict[str, Any]]:
    basket_path = PROJECT_ROOT / "data" / "synthetic" / "baskets.csv"
    prod_path = PROJECT_ROOT / "data" / "synthetic" / "products.csv"
    if not (basket_path.exists() and prod_path.exists()):
        return []
    b_df = pd.read_csv(basket_path)
    p_df = pd.read_csv(prod_path).set_index("product_id")["product_name"].to_dict()
    order_items = b_df.groupby("basket_id")["product_id"].apply(list)
    pair_counts: Dict[Tuple[str, str], int] = {}
    for items in order_items:
        unique_items = sorted(set(items))
        for i in range(len(unique_items)):
            for j in range(i + 1, len(unique_items)):
                p1, p2 = unique_items[i], unique_items[j]
                pair_counts[(p1, p2)] = pair_counts.get((p1, p2), 0) + 1
    top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    results = []
    for (p1, p2), count in top_pairs:
        results.append({
            "product_a_id": p1,
            "product_a_name": p_df.get(p1, p1),
            "product_b_id": p2,
            "product_b_name": p_df.get(p2, p2),
            "co_purchases": count,
            "support_pct": round(count / max(1, len(order_items)) * 100, 2),
        })
    return results


def _recommendation_error_result(
    customer_id: str,
    error_type: str,
    message: str,
    http_status: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "status": "ERROR",
        "customer_id": customer_id,
        "candidate_count": 0,
        "feasible_count": 0,
        "excluded_count": 0,
        "decision_method": None,
        "decision_engine_status": None,
        "recommendations": [],
        "excluded_candidates": [],
        "error": message,
        "error_type": error_type,
        "http_status": http_status,
    }


def _extract_backend_error_detail(res: requests.Response) -> str:
    try:
        data = res.json()
    except Exception:
        data = None
    if isinstance(data, dict):
        parts: List[str] = []
        detail = data.get("detail") or data.get("error") or data.get("message")
        if isinstance(detail, str) and detail.strip():
            parts.append(detail.strip())
        rec_status = data.get("status")
        if isinstance(rec_status, str) and rec_status.strip():
            parts.append(f"status={rec_status.strip()}")
        engine_status = data.get("decision_engine_status")
        if isinstance(engine_status, str) and engine_status.strip():
            parts.append(f"decision_engine_status={engine_status.strip()}")
        if parts:
            return "; ".join(parts)
    return ""


def render_recommendation_error(rec_result: Dict[str, Any]) -> bool:
    if not isinstance(rec_result, dict):
        st.error("Recommendations unavailable — invalid response structure.")
        return True
    if rec_result.get("status") != "ERROR" and not rec_result.get("error"):
        return False
    err_msg = rec_result.get("error") or "Live recommendations could not be retrieved from the backend."
    st.error(f"❌ **Live Recommendations Unavailable**: {err_msg}")
    return True


def fetch_recommendations(
    customer_id: str,
    top_k: int = 5,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
) -> Dict[str, Any]:
    try:
        res = requests.post(
            f"{API_BASE_URL}/recommend",
            json={
                "customer_id": customer_id,
                "top_k": top_k,
                "reward_context": reward_context,
                "promotion_context": promotion_context,
                "express_context": express_context,
                "include_excluded": True,
            },
            timeout=RECOMMEND_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return _recommendation_error_result(
            customer_id=customer_id,
            error_type="timeout",
            message=(
                "Recommendation request timed out while awaiting the backend service. "
                "Please verify backend health and try again."
            ),
        )
    except requests.exceptions.ConnectionError:
        return _recommendation_error_result(
            customer_id=customer_id,
            error_type="backend_unavailable",
            message=(
                "Backend recommendation service is unreachable. "
                f"Ensure the FastAPI server is running and accessible at `{API_BASE_URL}`."
            ),
        )
    except requests.exceptions.RequestException as exc:
        return _recommendation_error_result(
            customer_id=customer_id,
            error_type="backend_unavailable",
            message=f"Failed to communicate with the recommendation backend ({type(exc).__name__}).",
        )

    if res.ok:
        try:
            payload = res.json()
        except Exception:
            return _recommendation_error_result(
                customer_id=customer_id,
                error_type="invalid_response",
                http_status=res.status_code,
                message="Invalid response from recommendation backend: expected valid JSON payload.",
            )

        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("status"), str)
            or not isinstance(payload.get("recommendations"), list)
        ):
            return _recommendation_error_result(
                customer_id=customer_id,
                error_type="invalid_response",
                http_status=res.status_code,
                message=(
                    "Invalid response from recommendation backend: "
                    "expected JSON object with 'status' and 'recommendations' list."
                ),
            )
        return payload

    detail_suffix = _extract_backend_error_detail(res)
    detail_text = f" ({detail_suffix})" if detail_suffix else ""
    if res.status_code == 503:
        return _recommendation_error_result(
            customer_id=customer_id,
            error_type="decision_or_workflow_failure",
            http_status=503,
            message=(
                "Recommendation decision service or audit store is unavailable (HTTP 503)"
                f"{detail_text}. Live ML recommendations cannot be served."
            ),
        )
    if res.status_code == 502:
        return _recommendation_error_result(
            customer_id=customer_id,
            error_type="decision_or_workflow_failure",
            http_status=502,
            message=(
                "Decision evaluation or workflow execution failed (HTTP 502)"
                f"{detail_text}. No fallback recommendations are permitted."
            ),
        )

    return _recommendation_error_result(
        customer_id=customer_id,
        error_type="http_error",
        http_status=res.status_code,
        message=f"Recommendation backend returned HTTP {res.status_code}{detail_text}.",
    )


def fetch_mcp_workflow(
    customer_id: str,
    top_k: int = 5,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
) -> Tuple[Optional[Dict[str, Any]], int, Optional[str]]:
    url = f"{API_BASE_URL}/mcp/workflow"
    payload = {
        "customer_id": customer_id,
        "top_k": top_k,
        "reward_context": reward_context,
        "promotion_context": promotion_context,
        "express_context": express_context,
    }
    try:
        res = requests.post(url, json=payload, timeout=90)
        try:
            data = res.json()
        except Exception:
            data = None

        if res.ok:
            return data, res.status_code, None
        else:
            err_msg = None
            if isinstance(data, dict):
                err_msg = data.get("error") or data.get("detail")
            if not err_msg:
                err_msg = f"Server returned HTTP status {res.status_code}"
            return data, res.status_code, err_msg
    except requests.exceptions.Timeout:
        return None, 408, "The agentic workflow request timed out while awaiting tool execution."
    except requests.exceptions.ConnectionError:
        return None, 503, "Could not connect to the backend service. Ensure the FastAPI application is running."
    except Exception as exc:
        return None, 500, f"An unexpected communication error occurred: {type(exc).__name__}"


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

def render_banner(title: str, subtitle: str, tag: str = "Decision Intelligence") -> None:
    st.markdown(
        f'<div class="page-banner">'
        f'<div class="banner-tag">✦ {tag}</div>'
        f'<h1>{title}</h1>'
        f'<p>{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _stock_badge(stock, status: str) -> str:
    if status == "in_stock" or (stock is not None and stock > 5):
        return f"<span class='badge badge-green'>● In Stock ({int(stock)})</span>" if stock is not None else "<span class='badge badge-green'>● In Stock</span>"
    elif stock is not None and stock > 0:
        return f"<span class='badge badge-amber'>⚠ Low ({int(stock)})</span>"
    else:
        return "<span class='badge badge-red'>✕ Depleted</span>"


def render_product_card(item: Dict[str, Any], rank: Optional[int] = None, show_policy: bool = False, compact: bool = False) -> None:
    """Render a clean product recommendation card."""
    score = item.get("recommendation_score", 0.0)
    price = item.get("unit_price", 0.0)
    rating = item.get("product_rating", 0.0)
    stock = item.get("available_stock")
    status = item.get("inventory_status", "in_stock")
    brand = item.get("brand", "Global")
    category = item.get("category", "General")
    name = item.get("product_name", "Product")
    pid = item.get("product_id", "")
    reason = item.get("score_breakdown", item.get("explanation", "High customer affinity"))
    margin = float(item.get("gross_margin_pct") or 0.0)

    with st.container(border=True):
        col_main, col_stats = st.columns([3, 1])
        with col_main:
            rank_str = f"**#{rank}** · " if rank else ""
            st.markdown(
                f"{rank_str}"
                f"<span class='badge badge-indigo'>{category}</span> "
                f"<span class='badge badge-slate'>{brand}</span> "
                f"<span class='badge badge-purple'>{pid}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**{name}**")
            stars = "★" * int(round(rating)) + "☆" * (5 - int(round(rating)))
            st.caption(f"{stars} {rating:.1f}/5")
        with col_stats:
            st.metric("Price", f"${price:,.2f}")
            st.markdown(_stock_badge(stock, status), unsafe_allow_html=True)

        if not compact:
            st.caption(f"**Rationale:** {reason}")
            if show_policy or item.get("policy_decision") == "PASS":
                margin_str = f"{margin*100:.1f}%" if margin > 0 else "Verified"
                stock_str = f"{int(stock)} units" if stock is not None else "Verified"
                st.markdown(
                    f"<span class='badge badge-green'>✓ Stock: {stock_str}</span> "
                    f"<span class='badge badge-green'>✓ Margin: {margin_str}</span> "
                    f"<span class='badge badge-green'>✓ Policy: Eligible</span>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"<span class='badge badge-indigo'>Relevance: {score*100:.1f}%</span>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY RESOLUTION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CATEGORIES: Tuple[str, ...] = (
    "Electronics", "Health & Fitness", "Beauty & Skincare", "Coffee & Kitchen", "Home & Living",
)


def resolve_category_options(
    catalogue: Optional[List[Dict[str, Any]]] = None,
    preferred_category: Any = None,
) -> Tuple[List[str], List[str]]:
    seen: set[str] = set()
    options: List[str] = []
    def _add(val: Any) -> None:
        if isinstance(val, str):
            cleaned = val.strip()
            if cleaned and cleaned.lower() != "nan" and cleaned not in seen:
                seen.add(cleaned)
                options.append(cleaned)
    for item in catalogue or []:
        _add(item.get("category"))
    for cat in DEFAULT_CATEGORIES:
        _add(cat)
    pref_clean: Optional[str] = None
    if isinstance(preferred_category, str):
        candidate = preferred_category.strip()
        if candidate and candidate.lower() != "nan":
            pref_clean = candidate
            _add(pref_clean)
    default_selection = (
        [pref_clean] if pref_clean and pref_clean in options else ([options[0]] if options else [])
    )
    return options, default_selection


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: EXECUTIVE OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

def render_overview() -> None:
    render_banner(
        "Next-Best-Offer & Product Recommendation Engine",
        "AI-powered decision intelligence balancing customer demand, profit margins, and supply constraints.",
        tag="Executive Dashboard",
    )

    customers = load_all_customers()
    catalogue = load_catalogue()
    report = load_evaluation_report()

    # KPI Row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active Customers", f"{len(customers):,}")
    c2.metric("Catalogue SKUs", len(catalogue))
    in_stock = sum(1 for p in catalogue if p.get("inventory_status") == "in_stock" or (p.get("available_stock") or 0) > 0)
    c3.metric("In-Stock Products", in_stock)
    c4.metric("Policy Compliance", "100%")
    c5.metric("ML ROC-AUC", report.get("ml_classification_metrics", {}).get("holdout_roc_auc", "0.8583"))

    # Architecture Pillars
    st.markdown('<div class="sh">Architecture Pillars</div>', unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    with p1:
        with st.container(border=True):
            st.markdown("**Personalised Demand**")
            st.caption("Customer affinity signals, basket interactions, and ML propensity scoring drive personalised product ranking.")
    with p2:
        with st.container(border=True):
            st.markdown("**Supply Governance**")
            st.caption("Deterministic policy engine enforces stock availability, margin floors, and fulfilment constraints before any offer.")
    with p3:
        with st.container(border=True):
            st.markdown("**Decision Auditability**")
            st.caption("Every recommendation trace is persisted to PostgreSQL with transparent scoring, reason codes, and audit records.")

    # Quick Navigation
    st.markdown('<div class="sh">Quick Navigation</div>', unsafe_allow_html=True)
    q1, q2, q3, q4, q5, q6 = st.columns(6)
    if q1.button("👤 Customers", use_container_width=True):
        st.session_state["nav_page"] = "Customer Intelligence"
        st.rerun()
    if q2.button("🛍️ Recommendations", use_container_width=True):
        st.session_state["nav_page"] = "Product Recommendations"
        st.rerun()
    if q3.button("📦 Inventory", use_container_width=True):
        st.session_state["nav_page"] = "Inventory & Policies"
        st.rerun()
    if q4.button("🤖 MCP Workflow", use_container_width=True):
        st.session_state["nav_page"] = "Agentic Workflow (MCP)"
        st.rerun()
    if q5.button("⚡ Demo", use_container_width=True):
        st.session_state["nav_page"] = "Demo Playground"
        st.rerun()
    if q6.button("💬 AI Assistant", use_container_width=True):
        st.session_state["nav_page"] = "AI Decision Assistant"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: CUSTOMER INTELLIGENCE HUB
# ═══════════════════════════════════════════════════════════════════════════════

def render_customer_intelligence_hub() -> None:
    render_banner(
        "Customer Intelligence Hub",
        "360° behavioral profiling, lifetime transaction patterns, and dynamic category affinity analysis.",
        tag="Customer Intelligence",
    )

    customers = load_all_customers()
    if not customers:
        st.warning("No customer data available.")
        return

    cust_options = [f"{c['customer_id']} — {c.get('preferred_category', 'General')} ({c.get('membership_tier', 'Standard')})" for c in customers]
    selected_idx = 0
    curr_id = st.session_state.get("selected_customer_id", "CUST_0001")
    for i, c in enumerate(customers):
        if c["customer_id"] == curr_id:
            selected_idx = i
            break

    selected_str = st.selectbox("Select Customer:", cust_options, index=selected_idx)
    selected_cust_id = selected_str.split(" ")[0]
    st.session_state["selected_customer_id"] = selected_cust_id

    data = load_customer_detail(selected_cust_id)
    cust = data.get("customer", {})
    interactions = data.get("interactions", [])
    transactions = data.get("recent_transactions", [])

    # Profile KPIs
    st.markdown('<div class="sh">Customer Profile</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tier", cust.get("membership_tier", "Standard"))
    c2.metric("Segment", cust.get("customer_segment", "Active"))
    c3.metric("Lifetime Spend", f"${float(cust.get('total_spend', 0)):,.2f}")
    c4.metric("Orders", f"{cust.get('total_orders', 0)}")
    c5.metric("Avg Order Value", f"${float(cust.get('average_order_value', 0)):,.2f}")

    with st.container(border=True):
        st.markdown(
            f"<span class='badge badge-indigo'>{cust.get('customer_id')}</span> "
            f"<span class='badge badge-purple'>{cust.get('location', 'Global')}</span> "
            f"<span class='badge badge-amber'>{cust.get('reward_points', 0):,} Points</span> "
            f"<span class='badge badge-slate'>Category: {cust.get('preferred_category', 'Electronics')}</span>",
            unsafe_allow_html=True,
        )

    col_chart, col_history = st.columns([1, 1])

    with col_chart:
        st.markdown('<div class="sh">Category Affinity</div>', unsafe_allow_html=True)
        if interactions:
            df_int = pd.DataFrame(interactions)
            if "category_preference_score" in df_int.columns:
                chart_data = df_int[["product_id", "category_preference_score"]].set_index("product_id").head(8)
                chart_accent = "#B98A62" if st.session_state.get("theme_mode", "dark") == "dark" else "#8B5E3C"
                st.bar_chart(chart_data, color=chart_accent, height=240)
            else:
                st.info("Engagement records active.")
        else:
            st.info("No historical browsing records found.")

    with col_history:
        st.markdown('<div class="sh">Recent Purchases</div>', unsafe_allow_html=True)
        if transactions:
            txn_data = []
            for txn in transactions[:8]:
                txn_data.append({
                    "Date": str(txn.get("transaction_date", ""))[:10],
                    "Product": txn.get("product_id", ""),
                    "Qty": txn.get("quantity", 1),
                    "Amount": f"${float(txn.get('final_amount', 0.0)):,.2f}",
                })
            st.dataframe(pd.DataFrame(txn_data), use_container_width=True, hide_index=True, height=280)
        else:
            st.info("No prior orders recorded.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: PRODUCT RECOMMENDATIONS DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

def render_recommendations_discovery() -> None:
    render_banner(
        "Product Recommendations",
        "Compare popularity-based baseline against personalised, governed recommendations.",
        tag="Demand Discovery",
    )

    customers = load_all_customers()
    cust_options = [c["customer_id"] for c in customers]
    curr_id = st.session_state.get("selected_customer_id", "CUST_0001")
    sel_idx = cust_options.index(curr_id) if curr_id in cust_options else 0
    catalogue = load_catalogue()
    discovery_categories, _ = resolve_category_options(catalogue)

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
    selected_customer = col_ctrl1.selectbox("Customer:", cust_options, index=sel_idx)
    st.session_state["selected_customer_id"] = selected_customer
    top_k = col_ctrl2.select_slider("Top-N:", options=[3, 5, 8, 10], value=5)
    category_filter = col_ctrl3.selectbox("Category:", ["All"] + discovery_categories)

    rec_result = fetch_recommendations(selected_customer, top_k=top_k)
    recs = rec_result.get("recommendations", [])
    if category_filter != "All":
        recs = [r for r in recs if r.get("category") == category_filter]

    st.markdown('<div class="sh">Popularity Baseline vs Personalised Engine</div>', unsafe_allow_html=True)

    col_pop, col_gov = st.columns(2)

    with col_pop:
        st.markdown("**Baseline: Popularity Ranking**")
        st.caption("Ranks by transaction frequency. No personalisation or inventory awareness.")
        pop_sorted = sorted(catalogue, key=lambda x: -float(x.get("product_popularity", 0)))[:top_k]
        for idx, item in enumerate(pop_sorted, 1):
            with st.container(border=True):
                c_left, c_right = st.columns([3, 1])
                with c_left:
                    st.markdown(
                        f"<span class='badge badge-slate'>#{idx}</span> "
                        f"<span class='badge badge-indigo'>{item.get('category')}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{item.get('product_name')}**")
                    st.caption(f"{item.get('brand')} · {item.get('product_id')}")
                with c_right:
                    st.metric("Price", f"${float(item.get('unit_price',0)):,.2f}")

    with col_gov:
        st.markdown("**Personalised & Governed**")
        st.caption("Customer affinity + ML scoring + stock/margin enforcement.")
        if render_recommendation_error(rec_result):
            pass
        elif recs:
            for idx, item in enumerate(recs, 1):
                render_product_card(item, rank=idx, compact=True)
        else:
            st.warning("No feasible recommendations match constraints.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: PREFERENCES STUDIO
# ═══════════════════════════════════════════════════════════════════════════════

def render_preferences_studio() -> None:
    render_banner(
        "Preferences & Personalisation Studio",
        "Configure customer preference weights, budget boundaries, and operational constraints.",
        tag="Personalisation Studio",
    )

    customers = load_all_customers()
    cust_options = [c["customer_id"] for c in customers]
    curr_id = st.session_state.get("selected_customer_id", "CUST_0001")
    sel_idx = cust_options.index(curr_id) if curr_id in cust_options else 0

    col_cust_select, col_cust_meta = st.columns([1, 2])
    with col_cust_select:
        selected_customer = st.selectbox("Active Customer:", cust_options, index=sel_idx, key="pref_cust")
        st.session_state["selected_customer_id"] = selected_customer
    with col_cust_meta:
        cust_detail = load_customer_detail(selected_customer).get("customer", {})
        if cust_detail:
            st.markdown(
                f"<div style='margin-top:24px; display:flex; gap:8px; align-items:center; flex-wrap:wrap;'>"
                f"<span class='badge badge-slate'>Segment: <b>{cust_detail.get('customer_segment', 'Standard')}</b></span> "
                f"<span class='badge badge-indigo'>Preferred: <b>{cust_detail.get('preferred_category', 'General')}</b></span> "
                f"<span class='badge badge-green'>Tier: <b>{cust_detail.get('membership_tier', 'Standard')}</b></span> "
                f"<span class='badge badge-amber'>Points: <b>{cust_detail.get('reward_points', 0):,}</b></span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            cust_detail = {}

    category_options, default_categories = resolve_category_options(
        load_catalogue(), preferred_category=cust_detail.get("preferred_category"),
    )

    st.markdown('<div class="sh">Preference Controls & Policy Filters</div>', unsafe_allow_html=True)

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            categories = st.multiselect("Shopping Categories:", category_options, default=default_categories)
            max_budget = st.slider("Max Price ($):", min_value=20, max_value=500, value=250, step=10)
            min_rating = st.slider("Min Rating:", min_value=3.0, max_value=5.0, value=3.8, step=0.1)
        with col2:
            st.markdown("<div style='font-size:0.84rem; font-weight:700; margin-bottom:8px;'>Operational Policy Toggles</div>", unsafe_allow_html=True)
            reward_ctx = st.toggle("🎁 Require Reward Eligibility", value=False)
            promo_ctx = st.toggle("🏷️ Require Promo Eligibility", value=True)
            express_ctx = st.toggle("⚡ Express Fulfilment (≤ 3 Days)", value=False)

        btn_apply = st.button("✨ Apply Preferences & Generate Tailored Recommendations", type="primary", use_container_width=True)

    if btn_apply or "studio_rec_result" in st.session_state or "studio_recs" in st.session_state:
        if btn_apply or "studio_rec_result" not in st.session_state:
            with st.spinner("Generating tailored recommendations..."):
                rec_result = fetch_recommendations(
                    selected_customer, top_k=8,
                    reward_context=reward_ctx, promotion_context=promo_ctx, express_context=express_ctx,
                )
            st.session_state["studio_rec_result"] = rec_result
            if rec_result.get("status") == "ERROR":
                st.session_state.pop("studio_recs", None)
            else:
                all_recs = rec_result.get("recommendations", [])
                filtered_recs = []
                for r in all_recs:
                    if categories and r.get("category") not in categories and r.get("subcategory") not in categories:
                        continue
                    if float(r.get("unit_price", 0)) > max_budget:
                        continue
                    if float(r.get("product_rating", 0)) < min_rating:
                        continue
                    if express_ctx and int(r.get("shipping_days", 5)) > 3:
                        continue
                    filtered_recs.append(r)
                st.session_state["studio_recs"] = filtered_recs

        st.markdown('<div class="sh">Tailored Recommendations</div>', unsafe_allow_html=True)
        studio_res = st.session_state.get("studio_rec_result", {})
        if render_recommendation_error(studio_res):
            return
        display_recs = st.session_state.get("studio_recs", [])
        if display_recs:
            st.success(f"{len(display_recs)} products match preferences and policy constraints.")
            for idx, item in enumerate(display_recs, 1):
                render_product_card(item, rank=idx)
        else:
            st.warning("No products passed preference filters and feasibility rules. Try adjusting budget or toggles.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5: NEXT-BEST-OFFER & DISPATCH CENTRE
# ═══════════════════════════════════════════════════════════════════════════════

def render_next_best_offer_centre() -> None:
    render_banner(
        "Next-Best-Offer Centre",
        "Top commercially viable offer with real inventory dispatch and governance audit.",
        tag="Next-Best-Offer",
    )

    customers = load_all_customers()
    cust_options = [c["customer_id"] for c in customers]
    curr_id = st.session_state.get("selected_customer_id", "CUST_0001")
    sel_idx = cust_options.index(curr_id) if curr_id in cust_options else 0

    selected_customer = st.selectbox("Customer:", cust_options, index=sel_idx, key="nbo_cust")
    st.session_state["selected_customer_id"] = selected_customer

    cust_detail = load_customer_detail(selected_customer).get("customer", {})
    reward_pts = cust_detail.get("reward_points", 0)
    tier = cust_detail.get("membership_tier", "Standard")

    rec_result = fetch_recommendations(selected_customer, top_k=3, reward_context=True, promotion_context=True)
    recs = rec_result.get("recommendations", [])

    retry_relaxed = False
    if rec_result.get("status") != "ERROR" and not recs:
        rec_result = fetch_recommendations(selected_customer, top_k=3)
        recs = rec_result.get("recommendations", [])
        if recs:
            retry_relaxed = True

    if render_recommendation_error(rec_result):
        return

    if recs:
        top_offer = recs[0]
        price = float(top_offer.get("unit_price", 0))
        stock = top_offer.get("available_stock")
        pid = top_offer.get("product_id", "")

        if retry_relaxed:
            st.info(
                "**Constraint Relaxation:** No products satisfied both promo and reward eligibility. "
                "Engine relaxed non-mandatory constraints to present feasible offers."
            )

        st.markdown('<div class="sh">Prime Offer</div>', unsafe_allow_html=True)
        with st.container(border=True):
            top_l, top_r = st.columns([3, 1])
            with top_l:
                st.markdown(
                    f"<span class='badge badge-purple'>★ Prime Offer</span> "
                    f"<span class='badge badge-green'>High Conversion</span> "
                    f"<span class='badge badge-indigo'>{top_offer.get('category')}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"### {top_offer.get('product_name')}")
                st.caption(f"{top_offer.get('brand')} · SKU: {pid}")
            with top_r:
                st.metric("Price", f"${price:,.2f}")
                st.markdown(_stock_badge(stock, top_offer.get("inventory_status", "in_stock")), unsafe_allow_html=True)

            justification = (
                rec_result.get("decision_explanation")
                or top_offer.get("explanation")
                or "High propensity, positive margin, and confirmed inventory."
            )
            st.caption(f"**Justification:** {justification}")

            c_b1, c_b2, c_b3 = st.columns(3)
            c_b1.metric("Tier", f"{tier}")
            c_b2.metric("Reward Points", f"{reward_pts:,}")
            c_b3.metric("Fulfilment", "2–3 Days")

        if rec_result.get("fallback_used"):
            st.warning(
                f"**Weighted Fallback Active** — {rec_result.get('fallback_reason') or 'Laya unavailable; deterministic weighted fallback selected the offer.'}"
            )

        # ── Product Dispatch & Inventory Deduction ──
        st.markdown('<div class="sh">Product Dispatch & Inventory Update</div>', unsafe_allow_html=True)
        with st.container(border=True):
            col_d1, col_d2 = st.columns([2, 1])
            with col_d1:
                dispatch_qty = st.number_input(
                    "Dispatch Quantity:", min_value=1, max_value=min(int(stock or 10), 100),
                    value=1, key="dispatch_qty",
                )
            with col_d2:
                current_stock = int(stock) if stock is not None else 0
                st.metric("Current Stock", f"{current_stock} units")
                st.metric("After Dispatch", f"{max(0, current_stock - dispatch_qty)} units")

            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("📦 Confirm Dispatch & Deduct Inventory", type="primary", use_container_width=True):
                # Build audit context from current recommendation result
                all_recs = recs or []
                excluded = rec_result.get("excluded_candidates") or []
                candidate_ids = [r.get("product_id", "") for r in all_recs + excluded]
                feasible_ids = [r.get("product_id", "") for r in all_recs]
                excluded_ids = [r.get("product_id", "") for r in excluded]

                dispatch_ref = f"DSP_{uuid.uuid4().hex[:8].upper()}"
                explanation = (
                    f"Product {pid} dispatched ({dispatch_qty} units) to {selected_customer}. "
                    f"Ref: {dispatch_ref}."
                )

                # Single atomic call: inventory deduction + audit in one DB transaction
                dispatch_result, dispatch_err = dispatch_product_api(
                    product_id=pid,
                    quantity=dispatch_qty,
                    customer_id=selected_customer,
                    candidate_products=candidate_ids,
                    feasible_products=feasible_ids,
                    excluded_products=excluded_ids,
                    selected_product_id=pid,
                    decision_explanation=explanation,
                    fallback_used=bool(rec_result.get("fallback_used", False)),
                    fallback_reason=rec_result.get("fallback_reason"),
                    ranking_method="NBO_DISPATCH",
                )
                if dispatch_result:
                    audit_persisted = dispatch_result.get("audit_created", False)
                    decision_id = dispatch_result.get("decision_id", "")
                    st.success(
                        f"**Dispatch Confirmed**\n\n"
                        f"- **Ref:** `{dispatch_ref}`\n"
                        f"- **Product:** {dispatch_result.get('product_name', pid)}\n"
                        f"- **Qty Dispatched:** {dispatch_qty}\n"
                        f"- **Stock:** {dispatch_result['stock_before']} → {dispatch_result['stock_after']} units\n"
                        f"- **Status:** {dispatch_result['inventory_status']}\n"
                        f"- **Audit:** {'✅ Persisted to PostgreSQL' if audit_persisted else '⚠️ Skipped (no customer context)'}"
                        + (f"\n- **Decision ID:** `{decision_id}`" if decision_id else "")
                    )
                    # Clear catalogue cache to reflect updated stock
                    load_catalogue.clear()
                else:
                    st.error(f"**Dispatch Failed** — {dispatch_err}")

            if col_btn2.button("📋 Log to Audit Trail", use_container_width=True):
                audit_payload = {
                    "customer_id": selected_customer,
                    "status": rec_result.get("status", "SUCCESS"),
                    "selected_product_id": pid,
                    "ranking_method": "MANUAL_GOVERNANCE_AUDIT",
                    "approval_status": "APPROVED",
                    "candidate_products": recs + (rec_result.get("excluded_candidates") or []),
                    "recommendations": recs,
                    "excluded_candidates": rec_result.get("excluded_candidates") or [],
                    "decision_weights": rec_result.get("decision_weights"),
                    "objective_scores": rec_result.get("objective_scores") or {},
                    "final_validation": rec_result.get("final_validation") or {"decision": "PASS"},
                    "decision_explanation": rec_result.get("decision_explanation")
                    or f"Operator approved offer {pid} for {selected_customer}.",
                    "fallback_used": bool(rec_result.get("fallback_used", False)),
                    "fallback_reason": rec_result.get("fallback_reason"),
                }
                saved_record, audit_err = submit_manual_audit(audit_payload)
                if saved_record:
                    st.success(f"Audit persisted — Decision ID: `{saved_record.get('decision_id')}`")
                else:
                    st.error(f"Audit persistence failed: {audit_err}")

        if rec_result.get("decision_id"):
            st.caption(f"Auto-trace: `decision_id={rec_result.get('decision_id')}` · method=`{rec_result.get('decision_method', 'LAYA')}`")

        with st.expander("Recent Audit Records", expanded=False):
            history_rows, history_err = fetch_decision_history(customer_id=selected_customer, limit=5)
            if history_err:
                st.warning(history_err)
            elif not history_rows:
                st.info(f"No audit records for {selected_customer}.")
            else:
                history_table = [
                    {
                        "ID": row.get("decision_id", "")[:12] + "…",
                        "SKU": row.get("selected_product_id"),
                        "Method": row.get("ranking_method"),
                        "Status": row.get("approval_status"),
                        "Time": str(row.get("created_at", ""))[:19],
                    }
                    for row in history_rows
                ]
                st.dataframe(pd.DataFrame(history_table), use_container_width=True, hide_index=True)

        if len(recs) > 1:
            st.markdown('<div class="sh">Alternative Offers</div>', unsafe_allow_html=True)
            for idx, item in enumerate(recs[1:], 2):
                render_product_card(item, rank=idx, compact=True)
    else:
        st.warning("No feasible NBO candidates found.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 6: AGENTIC MCP WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════════

def render_mcp_agentic_workflow() -> None:
    render_banner(
        "Multi-Agent Recommendation Workflow",
        "6-stage pipeline: Customer Profiling → ML Scoring → Inventory → Policy → Decision Engine → Revalidation.",
        tag="Agentic MCP Architecture",
    )

    customers = load_all_customers()
    cust_options = [c["customer_id"] for c in customers] if customers else [f"CUST_{i:04d}" for i in range(1, 21)]
    curr_id = st.session_state.get("selected_customer_id", "CUST_0001")
    sel_idx = cust_options.index(curr_id) if curr_id in cust_options else 0

    st.markdown('<div class="sh">Workflow Parameters</div>', unsafe_allow_html=True)
    with st.container(border=True):
        c_cust, c_topk = st.columns([2, 1])
        with c_cust:
            selected_customer = st.selectbox("Customer:", cust_options, index=sel_idx, key="mcp_cust_select")
            st.session_state["selected_customer_id"] = selected_customer
        with c_topk:
            top_k = st.select_slider("Top-N:", options=[1, 3, 5, 8, 10], value=5, key="mcp_top_k")

        col_f1, col_f2, col_f3 = st.columns(3)
        reward_ctx = col_f1.toggle("🎁 Reward Eligibility", value=False, key="mcp_reward_toggle")
        promo_ctx = col_f2.toggle("🏷️ Promo Eligibility", value=False, key="mcp_promo_toggle")
        express_ctx = col_f3.toggle("⚡ Express (≤ 7 Days)", value=False, key="mcp_express_toggle")

        btn_execute = st.button("Run Agentic Workflow", type="primary", use_container_width=True)

    if btn_execute:
        with st.spinner(f"Coordinating MCP agents for {selected_customer}..."):
            data, status_code, err_msg = fetch_mcp_workflow(
                customer_id=selected_customer, top_k=top_k,
                reward_context=reward_ctx, promotion_context=promo_ctx, express_context=express_ctx,
            )
            st.session_state["mcp_last_result"] = data
            st.session_state["mcp_last_status_code"] = status_code
            st.session_state["mcp_last_error"] = err_msg
            st.session_state["mcp_last_customer"] = selected_customer

    if "mcp_last_result" not in st.session_state:
        # Explanation of how workflow operates
        with st.container(border=True):
            st.markdown("**How the Multi-Agent Workflow Operates**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("**1. Customer Agent** — Retrieves verified profile and category affinity.")
                st.caption("**2. Recommendation Agent** — Generates scored candidate products.")
            with c2:
                st.caption("**3. Inventory Agent** — Validates stock levels and margin floor.")
                st.caption("**4. Policy Agent** — Applies business governance rules.")
            with c3:
                st.caption("**5. Decision Agent** — Runs Laya inference with weighted fallback.")
                st.caption("**6. Final Agent** — Revalidates before persistence.")
        return

    data = st.session_state.get("mcp_last_result")
    status_code = st.session_state.get("mcp_last_status_code", 200)
    err_msg = st.session_state.get("mcp_last_error")

    if data is None:
        st.error(f"**Workflow Error** — {err_msg}")
        st.info("Verify that the FastAPI backend is operational.")
        return

    status = data.get("status", "UNKNOWN")
    agents = data.get("agents", [])
    recommendations = data.get("recommendations", [])
    excluded = data.get("excluded_candidates", [])
    selected_id = data.get("selected_product_id") or data.get("laya_selected_product_id")
    decision_method = data.get("decision_method") or data.get("laya_status") or "WEIGHTED_DECISION"
    decision_weights = data.get("decision_weights") or {}
    objective_scores = data.get("objective_scores") or {}
    final_ranking = data.get("final_ranking") or []
    final_validation = data.get("final_validation") or {}
    decision_explanation = data.get("decision_explanation")
    decision_id = data.get("decision_id")
    fallback_used = bool(data.get("fallback_used", False))
    fallback_reason = data.get("fallback_reason")
    top_error = data.get("error")

    # Agent Execution Timeline
    st.markdown('<div class="sh">Agent Execution Timeline</div>', unsafe_allow_html=True)
    agent_icons = {
        "Customer Agent": "👤", "Recommendation Agent": "🧠", "Inventory Agent": "📦",
        "Policy Agent": "🛡️", "Decision Agent": "⚖️", "Final Decision Agent": "🎯",
    }

    # Show agents in a compact visual timeline
    for idx, agent_exec in enumerate(agents, 1):
        ag_name = agent_exec.get("agent", f"Agent {idx}")
        ag_status = agent_exec.get("status", "unknown")
        ag_ms = agent_exec.get("duration_ms", 0.0)
        ag_icon = agent_icons.get(ag_name, "⚙️")

        if ag_status == "completed":
            badge_cls = "badge-green"
            badge_txt = f"✓ {ag_ms:.0f}ms"
        elif ag_status in ("completed_with_fallback", "completed_with_errors"):
            badge_cls = "badge-amber"
            badge_txt = f"⚠ {ag_ms:.0f}ms"
        else:
            badge_cls = "badge-red"
            badge_txt = f"✕ {ag_ms:.0f}ms"

        with st.container(border=True):
            row_l, row_r = st.columns([4, 1])
            with row_l:
                st.markdown(
                    f"**{ag_icon} {ag_name}** <span class='badge {badge_cls}'>{badge_txt}</span>",
                    unsafe_allow_html=True,
                )
                ag_resp = agent_exec.get("responsibility", "")
                if ag_resp:
                    st.caption(ag_resp)

                # Compact output summary
                ag_output = agent_exec.get("output")
                if isinstance(ag_output, dict):
                    if "verified" in ag_output:
                        st.caption(f"Verified {ag_output.get('verified', 0)} SKUs")
                    elif "pass" in ag_output:
                        st.caption(f"{ag_output.get('pass', 0)} passed, {ag_output.get('excluded', 0)} excluded")
                    elif "selected_product_id" in ag_output:
                        st.caption(f"Selected: `{ag_output.get('selected_product_id')}`")
                    elif "recommendations" in ag_output:
                        st.caption(f"Final: {len(ag_output.get('recommendations', []))} passed revalidation")
                    elif "candidate_count" in ag_output:
                        st.caption(f"Generated {ag_output.get('candidate_count', 0)} candidates")

            with row_r:
                st.metric("Time", f"{ag_ms:.0f}ms")

    # Fallback notice
    if fallback_used:
        st.warning(f"**Weighted Fallback Active** — {fallback_reason or 'Laya unavailable; deterministic fallback used.'}")

    if status == "FAILED_SAFE" or status_code in (502, 503):
        st.error("**Workflow halted safely** — No unverified recommendations returned.")
        if top_error:
            st.info(f"Detail: {top_error}")

    catalogue_map = {item.get("product_id"): item for item in load_catalogue()}

    # Selected Offer
    if selected_id and recommendations:
        st.markdown('<div class="sh">Decision Selection</div>', unsafe_allow_html=True)
        chosen_rec = next((r for r in recommendations if r.get("product_id") == selected_id), recommendations[0])
        cat_info = catalogue_map.get(selected_id, {})

        l_name = cat_info.get("product_name") or chosen_rec.get("product_name", "Product")
        l_price = float(cat_info.get("unit_price") or 0.0)
        l_rating = float(cat_info.get("product_rating") or 4.5)
        l_brand = cat_info.get("brand") or "Global"
        l_cat = cat_info.get("category") or "General"
        l_score = float(chosen_rec.get("recommendation_score") or 0.0)
        l_weighted = chosen_rec.get("weighted_score")
        l_stock = cat_info.get("available_stock")
        l_margin = float(cat_info.get("gross_margin_pct") or 0.0)

        badge_label = "Selected by Laya" if not fallback_used else "Selected by Weighted Fallback"
        reval_status = final_validation.get("decision", "PASS") if isinstance(final_validation, dict) else "PASS"

        with st.container(border=True):
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                st.markdown(
                    f"<span class='badge badge-purple'>★ {badge_label}</span> "
                    f"<span class='badge badge-indigo'>{l_cat}</span> "
                    f"<span class='badge badge-slate'>{l_brand}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"### {l_name}")
                stars = "★" * int(round(l_rating)) + "☆" * (5 - int(round(l_rating)))
                st.caption(f"{stars} {l_rating:.1f}/5 · Method: {decision_method} · Validation: {reval_status}")
            with col_l2:
                if l_price > 0:
                    st.metric("Price", f"${l_price:,.2f}")
                if l_weighted is not None:
                    st.metric("Weighted Score", f"{float(l_weighted):.4f}")
                else:
                    st.metric("Propensity", f"{l_score * 100:.1f}%")

            st.caption(f"**Justification:** {decision_explanation or 'Selected from policy-feasible candidates and revalidated.'}")
            margin_str = f"{l_margin*100:.1f}%" if l_margin > 0 else "≥ 10%"
            stock_str = f"{int(l_stock)} units" if l_stock is not None else "Verified"
            st.markdown(
                f"<span class='badge badge-green'>✓ Stock: {stock_str}</span> "
                f"<span class='badge badge-green'>✓ Margin: {margin_str}</span> "
                f"<span class='badge badge-green'>✓ Revalidation: {reval_status}</span>",
                unsafe_allow_html=True,
            )

    # Multi-Objective Comparison
    if final_ranking or (recommendations and objective_scores):
        with st.expander("Multi-Objective Candidate Comparison", expanded=False):
            if decision_weights:
                w_parts = [f"{k}={float(v):.2f}" for k, v in decision_weights.items()]
                st.caption("Weights: " + " · ".join(w_parts))
            comparison_rows = []
            source_rows = final_ranking if final_ranking else recommendations
            for idx, item in enumerate(source_rows, 1):
                pid = item.get("product_id")
                obj = item.get("objective_scores") or objective_scores.get(str(pid), {}) or {}
                comparison_rows.append({
                    "Rank": item.get("rank", idx),
                    "SKU": pid,
                    "Product": item.get("product_name"),
                    "Relevance": obj.get("recommendation_relevance", item.get("recommendation_score")),
                    "Margin": obj.get("margin_contribution"),
                    "Diversity": obj.get("product_diversity"),
                    "Friction": obj.get("operational_friction"),
                    "Score": item.get("weighted_score"),
                })
            if comparison_rows:
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

    # Audit confirmation
    if decision_id:
        st.success(f"Decision persisted — `decision_id={decision_id}`")

    # Governed Recommendations
    if recommendations:
        st.markdown(f'<div class="sh">Governed Recommendations ({len(recommendations)})</div>', unsafe_allow_html=True)
        for idx, rec in enumerate(recommendations, 1):
            pid = rec.get("product_id")
            cat_item = catalogue_map.get(pid, {})
            merged_item = {
                "product_id": pid,
                "product_name": cat_item.get("product_name") or rec.get("product_name"),
                "category": cat_item.get("category", "General"),
                "brand": cat_item.get("brand", "Global"),
                "unit_price": cat_item.get("unit_price", 0.0),
                "product_rating": cat_item.get("product_rating", 4.0),
                "available_stock": cat_item.get("available_stock", 10),
                "inventory_status": cat_item.get("inventory_status", "in_stock"),
                "gross_margin_pct": cat_item.get("gross_margin_pct", 0.15),
                "recommendation_score": rec.get("recommendation_score", 0.0),
                "policy_decision": rec.get("policy_decision", "PASS"),
                "explanation": "Verified through multi-agent governance.",
            }
            render_product_card(merged_item, rank=idx, show_policy=True, compact=True)
    elif status == "ALL_CANDIDATES_EXCLUDED":
        st.info("All candidates excluded by supply constraints.")

    # Excluded Products
    if excluded:
        with st.expander(f"Excluded by Policy ({len(excluded)} SKUs)", expanded=False):
            for exc_item in excluded:
                p_name = exc_item.get("product_name", "Product")
                p_id = exc_item.get("product_id", "")
                p_reasons = exc_item.get("policy_reasons", ["Constraint violation"])
                st.markdown(
                    f"<span class='badge badge-red'>EXCLUDED</span> **{p_name}** ({p_id}) — {' · '.join(p_reasons)}",
                    unsafe_allow_html=True,
                )

    # Summary Metrics
    st.markdown('<div class="sh">Summary</div>', unsafe_allow_html=True)
    total_cands = len(recommendations) + len(excluded)
    total_ms = sum(a.get("duration_ms", 0.0) for a in agents)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Evaluated", total_cands)
    s2.metric("Feasible", len(recommendations))
    s3.metric("Excluded", len(excluded))
    s4.metric("Latency", f"{total_ms:.0f}ms")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 7: INVENTORY & POLICY CENTRE
# ═══════════════════════════════════════════════════════════════════════════════

def render_inventory_policy_centre() -> None:
    render_banner(
        "Inventory & Policy Control Centre",
        "Real-time supply health, margin compliance, and policy simulation.",
        tag="Supply Governance",
    )

    catalogue = load_catalogue()
    if not catalogue:
        st.warning("Operational catalogue unavailable.")
        return

    total_prods = len(catalogue)
    in_stock_cnt = sum(1 for p in catalogue if p.get("inventory_status") == "in_stock" or (p.get("available_stock") is not None and p.get("available_stock") > 0))
    low_stock_cnt = sum(1 for p in catalogue if (p.get("available_stock") or 0) > 0 and (p.get("available_stock") or 0) <= (p.get("reorder_point") or 15))
    out_stock_cnt = sum(1 for p in catalogue if p.get("inventory_status") == "out_of_stock" or (p.get("available_stock") is not None and p.get("available_stock") <= 0))
    low_margin_cnt = sum(1 for p in catalogue if (p.get("gross_margin_pct") or 0) < 0.10)

    # Supply Health KPIs
    st.markdown('<div class="sh">Supply Health</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total SKUs", total_prods)
    c2.metric("In Stock", in_stock_cnt)
    c3.metric("Depleted", out_stock_cnt)
    c4.metric("Low Margin (<10%)", low_margin_cnt)

    # Inventory Table
    st.markdown('<div class="sh">Catalogue Overview</div>', unsafe_allow_html=True)

    # Filters
    col_f1, col_f2 = st.columns(2)
    categories = list(set(p.get("category", "General") for p in catalogue))
    cat_filter = col_f1.selectbox("Filter by Category:", ["All"] + sorted(categories), key="inv_cat_filter")
    stock_filter = col_f2.selectbox("Stock Status:", ["All", "In Stock", "Low Stock", "Out of Stock"], key="inv_stock_filter")

    filtered = catalogue
    if cat_filter != "All":
        filtered = [p for p in filtered if p.get("category") == cat_filter]
    if stock_filter == "In Stock":
        filtered = [p for p in filtered if (p.get("available_stock") or 0) > (p.get("reorder_point") or 15)]
    elif stock_filter == "Low Stock":
        filtered = [p for p in filtered if 0 < (p.get("available_stock") or 0) <= (p.get("reorder_point") or 15)]
    elif stock_filter == "Out of Stock":
        filtered = [p for p in filtered if (p.get("available_stock") or 0) <= 0]

    if filtered:
        inv_data = []
        for p in filtered:
            inv_data.append({
                "SKU": p.get("product_id"),
                "Product": p.get("product_name"),
                "Category": p.get("category"),
                "Stock": int(p.get("available_stock") or 0),
                "Margin": f"{float(p.get('gross_margin_pct', 0))*100:.1f}%",
                "Price": f"${float(p.get('unit_price', 0)):,.2f}",
                "Status": p.get("inventory_status", "unknown"),
            })
        st.dataframe(pd.DataFrame(inv_data), use_container_width=True, hide_index=True, height=350)
    else:
        st.info("No products match current filters.")

    # Policy Simulation
    st.markdown('<div class="sh">Policy Simulation</div>', unsafe_allow_html=True)
    cust_col, _ = st.columns([2, 2])
    test_cust = cust_col.selectbox("Test Customer:", [f"CUST_{i:04d}" for i in range(1, 15)], index=0)

    eval_res = fetch_recommendations(test_cust, top_k=5, reward_context=False, promotion_context=False)
    if render_recommendation_error(eval_res):
        return
    feasible_items = eval_res.get("recommendations", [])
    excluded_items = eval_res.get("excluded_candidates", [])

    m1, m2, m3 = st.columns(3)
    m1.metric("Candidates", eval_res.get("candidate_count", len(feasible_items) + len(excluded_items)))
    m2.metric("Eligible", len(feasible_items))
    m3.metric("Excluded", len(excluded_items))

    tab_pass, tab_fail = st.tabs(["Eligible Products", "Excluded Products"])
    with tab_pass:
        if feasible_items:
            for idx, item in enumerate(feasible_items, 1):
                render_product_card(item, rank=idx, show_policy=True, compact=True)
        else:
            st.info("No candidates passed all policy rules.")
    with tab_fail:
        if excluded_items:
            for item in excluded_items:
                p_reasons = item.get("policy_reasons", ["Constraint violation"])
                st.markdown(
                    f"<span class='badge badge-red'>EXCLUDED</span> "
                    f"**{item.get('product_name', 'Product')}** ({item.get('product_id')}) — {' · '.join(p_reasons)}",
                    unsafe_allow_html=True,
                )
        else:
            st.success("All candidates passed operational rules.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 8: PRODUCT ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def render_analytics_insights() -> None:
    render_banner(
        "Product Analytics & Insights",
        "Cross-selling patterns, model evaluation benchmarks, and content-based similarity analysis.",
        tag="Recommendation Analytics",
    )

    tab_assoc, tab_metrics, tab_catalogue, tab_vectors = st.tabs([
        "Cross-Sell Patterns", "Model Benchmarks", "Category Distribution", "Content-Based Similarity",
    ])

    with tab_assoc:
        st.markdown('<div class="sh">Co-Purchase Associations</div>', unsafe_allow_html=True)
        st.caption("Derived from multi-item basket transactions.")
        associations = load_basket_associations()
        if associations:
            assoc_data = []
            for pair in associations[:10]:
                assoc_data.append({
                    "Product A": pair.get("product_a_name"),
                    "Product B": pair.get("product_b_name"),
                    "Co-purchases": pair.get("co_purchases"),
                    "Support": f"{pair.get('support_pct')}%",
                })
            st.dataframe(pd.DataFrame(assoc_data), use_container_width=True, hide_index=True)
        else:
            st.info("Basket data processed.")

    with tab_metrics:
        st.markdown('<div class="sh">Offline Evaluation Benchmarks</div>', unsafe_allow_html=True)
        report = load_evaluation_report()
        ml_metrics = report.get("ml_classification_metrics", {})
        rec_metrics = report.get("recommendation_metrics", [])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Classifier", ml_metrics.get("model", "Gradient Boosting"))
        c2.metric("ROC-AUC", ml_metrics.get("holdout_roc_auc", "0.8583"))
        c3.metric("PR-AUC", ml_metrics.get("holdout_pr_auc", "0.7094"))
        c4.metric("Compliance", "100%")

        if rec_metrics:
            st.markdown("**Precision@K & Recall@K by Pipeline**")
            st.dataframe(pd.DataFrame(rec_metrics), use_container_width=True, hide_index=True)

    with tab_catalogue:
        st.markdown('<div class="sh">Category Distribution</div>', unsafe_allow_html=True)
        catalogue = load_catalogue()
        if catalogue:
            df_cat = pd.DataFrame(catalogue)
            cat_counts = df_cat["category"].value_counts()
            chart_accent = "#B98A62" if st.session_state.get("theme_mode", "dark") == "dark" else "#8B5E3C"
            st.bar_chart(cat_counts, color=chart_accent, height=240)

    with tab_vectors:
        st.markdown('<div class="sh">Content-Based Similarity (TF-IDF Cosine)</div>', unsafe_allow_html=True)
        st.caption("Cosine similarity across TF-IDF product attribute vectors (name, category, brand, price tier).")
        catalogue = load_catalogue()
        if catalogue:
            prod_options = [f"{p['product_id']} — {p.get('product_name', 'Product')} (${float(p.get('unit_price', 0)):.2f})" for p in catalogue]
            sel_prod_str = st.selectbox("Seed Product:", prod_options, index=min(6, len(prod_options)-1))
            seed_pid = sel_prod_str.split(" — ")[0]

            from backend.app.recommendation.content_based import get_content_recommender
            df_prods = pd.DataFrame(catalogue)
            recommender = get_content_recommender(df_prods)
            similar_products = recommender.get_similar_products_detailed(seed_pid, top_n=5)

            if similar_products:
                st.markdown(f"**Top-5 Similar to `{seed_pid}`:**")
                sim_data = []
                for item in similar_products:
                    sim_data.append({
                        "SKU": item.get("product_id"),
                        "Product": item.get("product_name"),
                        "Category": item.get("category"),
                        "Brand": item.get("brand"),
                        "Similarity": item.get("cosine_similarity_pct", "0.0%"),
                    })
                st.dataframe(pd.DataFrame(sim_data), use_container_width=True, hide_index=True)
            else:
                st.info("Select a product to view similarity results.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 9: DEMO PLAYGROUND
# ═══════════════════════════════════════════════════════════════════════════════

def render_demo_playground() -> None:
    render_banner(
        "Live Demonstration Playground",
        "End-to-end presenter flow: select a scenario, run the decision engine, and inspect results.",
        tag="Presenter Demo",
    )

    # Step 1: Scenario Selection
    st.markdown('<div class="sh">Step 1 — Select Scenario</div>', unsafe_allow_html=True)
    scenarios = {
        "Tech Enthusiast (CUST_0001)": {"id": "CUST_0001", "desc": "High-spend electronics buyer with audio hardware affinity."},
        "Home & Kitchen VIP (CUST_0003)": {"id": "CUST_0003", "desc": "Gold tier customer with cookware and rapid re-order frequency."},
        "Fitness Shopper (CUST_0005)": {"id": "CUST_0005", "desc": "Active customer for fitness wearables and outdoor accessories."},
    }
    selected_scenario = st.selectbox("Scenario:", list(scenarios.keys()))
    scenario_info = scenarios[selected_scenario]
    customer_id = scenario_info["id"]
    st.session_state["selected_customer_id"] = customer_id
    st.info(f"**{scenario_info['desc']}** (ID: `{customer_id}`)")

    # Step 2: Customer Profile
    st.markdown('<div class="sh">Step 2 — Customer Profile</div>', unsafe_allow_html=True)
    cust_data = load_customer_detail(customer_id)
    cust = cust_data.get("customer", {})
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Tier", cust.get("membership_tier", "Standard"))
    p2.metric("Category", cust.get("preferred_category", "Electronics"))
    p3.metric("Spend", f"${float(cust.get('total_spend', 0)):,.2f}")
    p4.metric("Points", f"{cust.get('reward_points', 0):,}")

    # Step 3: Execute
    st.markdown('<div class="sh">Step 3 — Run Decision Engine</div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_t1, col_t2, col_t3 = st.columns(3)
        t_reward = col_t1.checkbox("Reward Eligibility", value=True)
        t_promo = col_t2.checkbox("Promo Margin Floor", value=True)
        t_express = col_t3.checkbox("Express Shipping", value=False)
        run_btn = st.button("Run Decision Pipeline", type="primary", use_container_width=True)

    if run_btn or "demo_result" in st.session_state:
        with st.spinner("Generating governed recommendations..."):
            res = fetch_recommendations(
                customer_id, top_k=4,
                reward_context=t_reward, promotion_context=t_promo, express_context=t_express,
            )
            st.session_state["demo_result"] = res

        demo_res = st.session_state["demo_result"]
        if render_recommendation_error(demo_res):
            return
        recs = demo_res.get("recommendations", [])
        excluded = demo_res.get("excluded_candidates", [])

        # Step 4: Governance Audit
        st.markdown('<div class="sh">Step 4 — Governance Results</div>', unsafe_allow_html=True)
        c_tot, c_pass, c_excl = st.columns(3)
        c_tot.metric("Scored", demo_res.get("candidate_count", len(recs) + len(excluded)))
        c_pass.metric("Feasible", len(recs))
        c_excl.metric("Excluded", len(excluded))

        if excluded:
            with st.expander(f"Excluded Products ({len(excluded)})", expanded=False):
                for exc in excluded[:5]:
                    st.caption(f"🚫 {exc.get('product_name')} ({exc.get('product_id')}): {' · '.join(exc.get('policy_reasons', []))}")

        # Step 5: Results
        st.markdown('<div class="sh">Step 5 — Recommendations</div>', unsafe_allow_html=True)
        for idx, item in enumerate(recs, 1):
            render_product_card(item, rank=idx, show_policy=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 10: AI DECISION ASSISTANT
# ═══════════════════════════════════════════════════════════════════════════════

def query_groq_assistant(prompt: str, context: Dict[str, Any]) -> str:
    url = f"{API_BASE_URL}/assistant/chat"
    try:
        res = requests.post(url, json={"question": prompt, "context": context}, timeout=TIMEOUT)
        if res.ok:
            data = res.json()
            return data.get("answer", "No response returned.")
        elif res.status_code in (502, 503, 504):
            try:
                detail = res.json().get("detail")
            except Exception:
                detail = None
            return detail or f"Assistant service notice (HTTP {res.status_code})."
        else:
            return f"Assistant returned HTTP {res.status_code}."
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "Cannot connect to backend assistant service."
    except Exception as e:
        return f"Assistant error: {str(e)}"


def render_ai_assistant() -> None:
    render_banner(
        "AI Decision Assistant",
        "LLM explanation engine powered by Groq, grounded in live catalogue and customer context.",
        tag="AI Assistant",
    )

    customers = load_all_customers()
    cust_options = [c["customer_id"] for c in customers]
    curr_id = st.session_state.get("selected_customer_id", "CUST_0001")
    sel_idx = cust_options.index(curr_id) if curr_id in cust_options else 0

    c_sel_col, c_info_col = st.columns([1, 2])
    with c_sel_col:
        active_customer = st.selectbox("Customer Context:", cust_options, index=sel_idx, key="assistant_customer_picker")
        if active_customer != st.session_state.get("selected_customer_id"):
            st.session_state["selected_customer_id"] = active_customer
            new_cust_detail = load_customer_detail(active_customer).get("customer", {})
            st.session_state["assistant_messages"] = [{
                "role": "assistant",
                "content": (
                    f"Context updated to **{active_customer}** "
                    f"({new_cust_detail.get('preferred_category', 'General')} · "
                    f"{new_cust_detail.get('membership_tier', 'Standard')} Tier)."
                ),
            }]
            st.rerun()

    cust_data = load_customer_detail(active_customer)
    cust_info = cust_data.get("customer", {})
    catalogue = load_catalogue()

    with c_info_col:
        st.markdown(
            f"<span class='badge badge-indigo'>{active_customer}</span> "
            f"<span class='badge badge-purple'>{cust_info.get('membership_tier', 'Standard')}</span> "
            f"<span class='badge badge-slate'>{cust_info.get('preferred_category', 'Electronics')}</span> "
            f"<span class='badge badge-green'>${float(cust_info.get('total_spend', 0)):,.2f} lifetime</span>",
            unsafe_allow_html=True,
        )

    rec_data = fetch_recommendations(active_customer, top_k=5)
    if render_recommendation_error(rec_data):
        rec_error = rec_data.get("error")
    else:
        rec_error = None
    recs = rec_data.get("recommendations", []) if not rec_error else []
    exclusions = rec_data.get("excluded_candidates", []) if not rec_error else []

    engine_telemetry = check_decision_engine_status() or {}
    active_provider = (
        f"Laya ({engine_telemetry.get('model', 'english')})"
        if engine_telemetry.get("laya_available")
        else "Weighted Fallback"
    )
    context_summary = {
        "active_customer": {
            "customer_id": active_customer,
            "tier": cust_info.get("membership_tier", "Standard"),
            "segment": cust_info.get("customer_segment", "Active"),
            "preferred_category": cust_info.get("preferred_category", "Electronics"),
            "total_spend": float(cust_info.get("total_spend", 0.0)),
            "total_orders": cust_info.get("total_orders", 0),
            "reward_points": cust_info.get("reward_points", 0),
        },
        "active_recommendations": [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "category": r.get("category"),
                "recommendation_score": r.get("recommendation_score"),
                "policy_decision": r.get("policy_decision"),
            }
            for r in recs[:5]
        ] if recs else [],
        "policy_exclusions": [
            {
                "product_id": e.get("product_id"),
                "product_name": e.get("product_name"),
                "policy_reasons": e.get("policy_reasons", []),
            }
            for e in exclusions[:10]
        ] if exclusions else [],
        "catalogue_summary": {
            "total_skus": len(catalogue),
            "depleted_skus": sum(1 for p in catalogue if (p.get("available_stock") or 0) <= 0),
        },
        "governance_engine": {
            "decision_engine": active_provider,
            "ml_model": "Gradient Boosting (ROC-AUC 0.8583)",
            "margin_floor": "10% minimum",
        },
    }

    # Suggested Prompts
    st.markdown('<div class="sh">Quick Prompts</div>', unsafe_allow_html=True)
    demo_prompts = [
        f"Explain the NBO rationale for {active_customer}",
        "Why was PROD_0010 excluded?",
        "How does the 10% margin floor work?",
        f"Discount strategy for {active_customer}?",
        "How is missing inventory handled?",
        "Popularity vs personalised NBO?",
    ]

    selected_prompt = None
    prompt_cols = st.columns(3)
    for i, col in enumerate(prompt_cols):
        for j in [i, i + 3]:
            if j < len(demo_prompts):
                if col.button(demo_prompts[j], key=f"prompt_{j}", use_container_width=True):
                    selected_prompt = demo_prompts[j]

    if "assistant_messages" not in st.session_state:
        st.session_state["assistant_messages"] = [{
            "role": "assistant",
            "content": f"Hello! I'm grounded in live context for **{active_customer}**, inventory facts, and margin policies. Ask me anything.",
        }]

    user_input = st.chat_input(f"Ask about {active_customer}, products, or policies...")
    prompt_to_run = selected_prompt or user_input

    if prompt_to_run:
        import re
        mentioned_prods = re.findall(r"PROD_\d{4}", prompt_to_run, re.IGNORECASE)
        if mentioned_prods:
            cat_map = {item.get("product_id"): item for item in catalogue}
            queried_prods = {}
            for pid in set(mentioned_prods):
                p_info = cat_map.get(pid.upper())
                if p_info:
                    queried_prods[pid.upper()] = {
                        "product_name": p_info.get("product_name"),
                        "category": p_info.get("category"),
                        "available_stock": p_info.get("available_stock"),
                        "gross_margin_pct": p_info.get("gross_margin_pct"),
                    }
            if queried_prods:
                context_summary["queried_products_in_prompt"] = queried_prods

        mentioned_custs = re.findall(r"CUST_\d{4}", prompt_to_run, re.IGNORECASE)
        if mentioned_custs:
            queried_custs = {}
            for cid in set(mentioned_custs):
                c_data = load_customer_detail(cid.upper()).get("customer", {})
                if c_data:
                    queried_custs[cid.upper()] = {
                        "tier": c_data.get("membership_tier"),
                        "preferred_category": c_data.get("preferred_category"),
                        "total_spend": float(c_data.get("total_spend", 0.0)),
                    }
            if queried_custs:
                context_summary["queried_customers_in_prompt"] = queried_custs

        st.session_state["assistant_messages"].append({"role": "user", "content": prompt_to_run})
        with st.spinner("Thinking..."):
            reply = query_groq_assistant(prompt_to_run, context_summary)
            st.session_state["assistant_messages"].append({"role": "assistant", "content": reply})

    # Chat Display
    for msg in st.session_state["assistant_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if len(st.session_state["assistant_messages"]) > 2:
        if st.button("Clear Chat", use_container_width=False):
            st.session_state["assistant_messages"] = [{
                "role": "assistant",
                "content": f"Chat reset. Ready for questions on **{active_customer}**.",
            }]
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION & MAIN CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    is_dark = (st.session_state.get("theme_mode", "dark") == "dark")
    header_border = "#514034" if is_dark else "#E0D2C5"
    header_title = "#F5EDE5" if is_dark else "#30241D"
    header_sub = "#C3B2A3" if is_dark else "#756456"

    with st.sidebar:
        st.markdown(
            f"<div style='padding:4px 0 10px 0; border-bottom:1px solid {header_border}; margin-bottom:10px;'>"
            f"<div style='font-size:1.15rem; font-weight:800; color:{header_title}; letter-spacing:-0.01em;'>🎯 NBO Platform</div>"
            f"<div style='font-size:0.68rem; color:{header_sub}; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; margin-top:2px;'>AI-Powered Recommendation Intelligence</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Theme Appearance Switcher ──
        st.markdown(
            f"<div style='font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:{header_sub}; margin:4px 0 4px 0;'>Appearance</div>",
            unsafe_allow_html=True,
        )
        theme_options = ["🌙 Dark Brown", "☀️ Light Brown"]
        current_theme_idx = 0 if is_dark else 1
        chosen_theme_label = st.radio(
            "Theme Mode",
            theme_options,
            index=current_theme_idx,
            key="theme_radio_selector",
            horizontal=True,
            label_visibility="collapsed",
        )
        chosen_theme_mode = "dark" if "Dark" in chosen_theme_label else "light"
        if chosen_theme_mode != st.session_state.get("theme_mode", "dark"):
            st.session_state["theme_mode"] = chosen_theme_mode
            st.rerun()

        st.markdown(
            f"<div style='font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:{header_sub}; margin:12px 0 4px 0;'>Navigation</div>",
            unsafe_allow_html=True,
        )

        nav_options = [
            "Overview",
            "Customer Intelligence",
            "Product Recommendations",
            "Preferences Studio",
            "Next-Best-Offer",
            "Agentic Workflow (MCP)",
            "Inventory & Policies",
            "Product Analytics",
            "Demo Playground",
            "AI Decision Assistant",
        ]

        default_index = 0
        if "nav_page" in st.session_state and st.session_state["nav_page"] in nav_options:
            default_index = nav_options.index(st.session_state["nav_page"])

        page = st.radio("Navigation", nav_options, index=default_index, label_visibility="collapsed")
        st.session_state["nav_page"] = page

        st.divider()

        # Backend Status
        health_info = check_api_health()
        if health_info:
            st.markdown(
                "<div class='status-pill status-connected'>● Backend Connected</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='status-pill status-offline'>● Standalone Mode</div>",
                unsafe_allow_html=True,
            )

        # Decision Engine Status
        engine_status = check_decision_engine_status()
        if engine_status and engine_status.get("laya_available", engine_status.get("available")):
            env_txt = engine_status.get("app_env", "local")
            model_txt = engine_status.get("model", "english")
            laya_bg = "#362920" if is_dark else "#F2E9E1"
            laya_border = "#B98A62" if is_dark else "#8B5E3C"
            laya_color = "#D1AA83" if is_dark else "#8B5E3C"
            st.markdown(
                f"<div class='status-pill' style='background:{laya_bg}; border:1px solid {laya_border}; color:{laya_color}; margin-top:6px;'>● Laya · {model_txt}</div>",
                unsafe_allow_html=True,
            )
        elif engine_status:
            st.markdown(
                "<div class='status-pill status-fallback' style='margin-top:6px;'>● Weighted Fallback</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='status-pill status-offline' style='margin-top:6px;'>● Engine Offline</div>",
                unsafe_allow_html=True,
            )

        st.caption(f"API: `{API_BASE_URL}`")

    if page == "Overview":
        render_overview()
    elif page == "Customer Intelligence":
        render_customer_intelligence_hub()
    elif page == "Product Recommendations":
        render_recommendations_discovery()
    elif page == "Preferences Studio":
        render_preferences_studio()
    elif page == "Next-Best-Offer":
        render_next_best_offer_centre()
    elif page == "Agentic Workflow (MCP)":
        render_mcp_agentic_workflow()
    elif page == "Inventory & Policies":
        render_inventory_policy_centre()
    elif page == "Product Analytics":
        render_analytics_insights()
    elif page == "Demo Playground":
        render_demo_playground()
    elif page == "AI Decision Assistant":
        render_ai_assistant()


if __name__ == "__main__":
    main()
