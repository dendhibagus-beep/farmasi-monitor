"""
Tema visual bersama untuk seluruh modul Super App Logistik Farmasi.
Panggil inject_css() sekali di awal setiap halaman untuk konsistensi visual.
"""

import streamlit as st

WARNA = {
    "primary": "#2563eb",
    "primary_dark": "#1d4ed8",
    "ok": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "ink": "#0f172a",
    "muted": "#64748b",
}

STATUS_ICON = {"ok": "🟢", "warning": "🟡", "danger": "🔴"}


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stMarkdown, .stMetric, .stButton button {
            font-family: 'Inter', -apple-system, sans-serif;
        }
        .stApp { background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); }

        .brand-header { display:flex; align-items:center; gap:0.7rem; margin-bottom:0.4rem; }
        .brand-header .logo { font-size:2rem; }
        .brand-header .title { font-size:1.35rem; font-weight:800; color:#0f172a; line-height:1.15; }
        .brand-header .subtitle { color:#64748b; font-size:0.82rem; }

        .kpi-card {
            background:#fff; border-radius:16px; padding:1rem 1.15rem;
            box-shadow:0 1px 3px rgba(15,23,42,0.06); border:1px solid #eef0f3;
        }
        .kpi-label { color:#64748b; font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
        .kpi-value { font-size:1.65rem; font-weight:800; color:#0f172a; margin-top:0.1rem; }

        .room-card {
            background:#fff; border-radius:16px; padding:1rem 1.1rem;
            box-shadow:0 1px 3px rgba(15,23,42,0.06); border:1px solid #eef0f3; margin-bottom:0.85rem;
        }

        .pill { display:inline-block; padding:0.22rem 0.65rem; border-radius:999px; font-size:0.74rem; font-weight:700; }
        .pill-ok { background:#dcfce7; color:#166534; }
        .pill-warning { background:#fef3c7; color:#92400e; }
        .pill-danger { background:#fee2e2; color:#991b1b; }

        .module-chip {
            display:inline-block; background:#eff6ff; color:#1d4ed8; border-radius:8px;
            padding:0.15rem 0.55rem; font-size:0.72rem; font-weight:700; margin-right:0.3rem;
        }

        [data-testid="stSidebar"] { background:#0f172a; }
        [data-testid="stSidebar"] * { color:#e2e8f0 !important; }
        [data-testid="stSidebar"] .brand-header .title { color:#f8fafc; }
        [data-testid="stSidebar"] .brand-header .subtitle { color:#94a3b8; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_branding(versi: str = "v2.0 · Modular"):
    with st.sidebar:
        st.markdown(
            f"""
            <div class="brand-header">
                <div class="logo">💊</div>
                <div>
                    <div class="title">Farmasi Command Center</div>
                    <div class="subtitle">Super App Logistik Farmasi</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(versi)
        st.divider()
