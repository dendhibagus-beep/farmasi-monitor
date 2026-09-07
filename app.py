"""
Command Center Logistik & Perbekalan Farmasi — Entry Point
=============================================================
Arsitektur modular: setiap modul adalah satu file di folder pages/,
didaftarkan lewat st.navigation() di bawah. Untuk berkembang menjadi
Super App Logistik Farmasi, cukup tambah file baru ke pages/ dan
daftarkan di grup modul yang sesuai — tidak perlu ubah struktur lain.
"""

import streamlit as st

from core.theme import inject_css, sidebar_branding
from core.landing import halaman_publik

st.set_page_config(page_title="Command Center Farmasi", page_icon="💊", layout="wide")

# ── Mode publik: halaman landing yang dituju QR Code, tanpa navigasi/login ──
params = st.query_params
if "ruangan" in params:
    halaman_publik(params["ruangan"])
    st.stop()

# ── Mode admin: shell aplikasi modular ──
inject_css()
sidebar_branding()

modul_suhu = [
    st.Page("pages/1_Monitoring.py", title="Monitoring Suhu", icon="🌡️", default=True),
    st.Page("pages/2_Verifikasi_Supervisor.py", title="Verifikasi & TTD Supervisor", icon="📝"),
    st.Page("pages/3_Notifikasi.py", title="Notifikasi Alarm", icon="🔔"),
    st.Page("pages/4_QR_Code.py", title="QR Code Ruangan", icon="🔗"),
    st.Page("pages/5_Pengaturan.py", title="Pengaturan Ambang Batas", icon="⚙️"),
]

# 🔮 Modul lain untuk Super App Logistik Farmasi tinggal ditambah di sini, contoh:
# modul_logistik = [
#     st.Page("pages/6_Inventori_Obat.py", title="Inventori Obat", icon="📦"),
#     st.Page("pages/7_Distribusi.py", title="Distribusi & Pengiriman", icon="🚚"),
# ]

navigasi = st.navigation(
    {
        "🌡️ Modul Monitoring Suhu": modul_suhu,
        # "📦 Modul Logistik": modul_logistik,
    }
)

with st.sidebar:
    st.caption("Ketuk menu di atas untuk berpindah modul.")

navigasi.run()
