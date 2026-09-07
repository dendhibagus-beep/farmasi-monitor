"""
Landing page publik — inilah halaman yang terbuka saat QR Code di ruangan di-scan.
Tidak butuh login, didesain untuk dibaca sekilas dari jarak agak jauh.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from core.db import get_log_suhu, get_ambang_batas, get_standar, evaluasi_status
from core.analytics import hitung_mkt, deteksi_excursion
from core.charts import grafik_time_series_dengan_batas, gauge_suhu
from core.theme import inject_css, STATUS_ICON
from alarm_sound import ALARM_SOUND_B64

REFRESH_INTERVAL_DETIK = 30


def _render_alarm_audio():
    st.markdown(
        f'<audio autoplay><source src="data:audio/wav;base64,{ALARM_SOUND_B64}" type="audio/wav"></audio>',
        unsafe_allow_html=True,
    )


def halaman_publik(lokasi_target: str):
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=REFRESH_INTERVAL_DETIK * 1000, key="publicrefresh")
    except ImportError:
        st.markdown(f'<meta http-equiv="refresh" content="{REFRESH_INTERVAL_DETIK}">', unsafe_allow_html=True)

    inject_css()
    st.markdown(
        """<style>
        [data-testid="stSidebar"] {display:none;}
        .block-container {max-width:840px; margin:auto; padding-top:1.6rem;}
        </style>""",
        unsafe_allow_html=True,
    )

    df = get_log_suhu()
    ambang = get_ambang_batas()

    if df.empty or lokasi_target not in df["lokasi"].unique():
        st.markdown(f"### 📍 {lokasi_target}")
        st.warning("Belum ada data suhu untuk ruangan ini. Menunggu transmisi dari sensor lapangan...")
        return

    df_r = df[df["lokasi"] == lokasi_target].sort_values("waktu")
    terkini = df_r.iloc[-1]
    suhu, lembab, waktu = float(terkini["suhu"]), float(terkini["kelembapan"]), terkini["waktu"]
    standar = get_standar(lokasi_target, ambang)
    status, level, pesan = evaluasi_status(suhu, lembab, standar)
    icon = STATUS_ICON[level]

    now_ref = datetime.now(waktu.tzinfo) if waktu.tzinfo else datetime.now()
    offline = (now_ref - waktu) > timedelta(minutes=40)  # sensor kirim tiap 15 menit + buffer keterlambatan jaringan

    st.markdown(
        f"""
        <div class="brand-header">
            <div class="logo">📍</div>
            <div>
                <div class="title">{lokasi_target}</div>
                <div class="subtitle">Update terakhir {waktu.strftime('%d %b %Y, %H:%M:%S')}
                {' · ⚠️ sensor offline &gt;15 menit' if offline else ' · 📡 sensor online'}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if offline:
        st.warning("⚠️ Data terakhir diterima lebih dari 15 menit lalu — periksa koneksi sensor.")

    df_24 = df_r[df_r["waktu"] >= (df_r["waktu"].max() - pd.Timedelta(hours=24))]
    mkt_24 = hitung_mkt(df_24["suhu"]) if not df_24.empty else None

    col_kiri, col_kanan = st.columns([1.1, 1])
    with col_kiri:
        st.plotly_chart(gauge_suhu(suhu, standar), use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"<div style='text-align:center; margin-top:-0.8rem;'>"
            f"<span class='pill pill-{level}' style='font-size:0.95rem; padding:0.4rem 1rem;'>{icon} {status}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_kanan:
        st.markdown(
            f"""<div class="kpi-card" style="margin-bottom:0.7rem;">
                <div class="kpi-label">Kelembapan Saat Ini</div>
                <div class="kpi-value">{lembab}%</div>
                <div style="color:#94a3b8; font-size:0.75rem;">Standar: {standar['lembab_min']}–{standar['lembab_max']}%</div>
            </div>""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""<div class="kpi-card"><div class="kpi-label">Min 24 Jam</div>
                <div class="kpi-value" style="font-size:1.3rem;">{df_24['suhu'].min():.1f}°C</div></div>"""
                if not df_24.empty else "-",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""<div class="kpi-card"><div class="kpi-label">Max 24 Jam</div>
                <div class="kpi-value" style="font-size:1.3rem;">{df_24['suhu'].max():.1f}°C</div></div>"""
                if not df_24.empty else "-",
                unsafe_allow_html=True,
            )
        st.write("")
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">MKT 24 Jam</div>
                <div class="kpi-value" style="font-size:1.3rem;">{mkt_24 if mkt_24 is not None else '-'}°C</div>
                <div style="color:#94a3b8; font-size:0.72rem;">Mean Kinetic Temperature — suhu efektif kumulatif standar farmasi</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.write("")
    if level != "ok":
        _render_alarm_audio()
        st.error(f"**{pesan}** — segera tindak lanjuti sesuai SOP kestabilan sediaan.")
    else:
        st.success(pesan)

    with st.expander("📈 Grafik 24 jam & riwayat penyimpangan (excursion)"):
        if not df_24.empty:
            fig = grafik_time_series_dengan_batas(
                df_24, "suhu", standar["suhu_min"], standar["suhu_max"], satuan="°C", tinggi=280
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            excursions = deteksi_excursion(df_24, standar)
            if excursions:
                st.markdown("**Kejadian penyimpangan 24 jam terakhir:**")
                for e in excursions[:5]:
                    status_e = "🔴 masih berlangsung" if e["_berlangsung"] else "✅ selesai"
                    st.caption(
                        f"{e['mulai'].strftime('%H:%M')}–{e['selesai'].strftime('%H:%M')} "
                        f"[{e['jenis']}] (durasi {e['durasi_menit']} menit, "
                        f"suhu puncak {e['suhu_puncak']}°C, kelembapan puncak {e['lembab_puncak']}%) — {status_e}"
                    )
            else:
                st.caption("Tidak ada penyimpangan dalam 24 jam terakhir. ✅")
        else:
            st.caption("Belum cukup data untuk 24 jam terakhir.")

    st.markdown(
        f"<p style='text-align:center;color:#94a3b8;font-size:0.78rem;margin-top:1.5rem;'>"
        f"Halaman ini otomatis diperbarui setiap {REFRESH_INTERVAL_DETIK} detik · "
        f"Command Center Logistik &amp; Perbekalan Farmasi</p>",
        unsafe_allow_html=True,
    )
