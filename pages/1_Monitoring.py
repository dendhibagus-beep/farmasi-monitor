import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from core.db import get_log_suhu, get_ambang_batas, get_standar, evaluasi_status
from core.analytics import hitung_mkt, deteksi_excursion
from core.charts import grafik_time_series_dengan_batas
from core.theme import STATUS_ICON

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False


st.title("🌡️ Command Center: Monitoring Suhu & Kelembapan")
st.caption("Pantau stabilitas sediaan secara real-time di seluruh ruangan/kulkas farmasi.")

if HAS_AUTOREFRESH:
    auto = st.sidebar.checkbox("🔄 Auto-refresh (30 detik)", value=True)
    if auto:
        st_autorefresh(interval=30_000, key="dashrefresh")

df = get_log_suhu()
ambang = get_ambang_batas()

if df.empty:
    st.info("Sistem standby. Menunggu transmisi data pertama dari sensor lapangan...")
    st.stop()

# ── Ringkasan semua ruangan ──────────────────────────────────────────
st.subheader("🗺️ Ringkasan Semua Ruangan")
lokasi_list = sorted(df["lokasi"].unique())
kolom = st.columns(min(4, max(1, len(lokasi_list))))
ada_alarm = False

for i, lokasi in enumerate(lokasi_list):
    df_l = df[df["lokasi"] == lokasi].sort_values("waktu")
    terkini = df_l.iloc[-1]
    standar_l = get_standar(lokasi, ambang)
    status, level, _ = evaluasi_status(float(terkini["suhu"]), float(terkini["kelembapan"]), standar_l)
    if level != "ok":
        ada_alarm = True
    icon = STATUS_ICON[level]
    now_ref = datetime.now(terkini["waktu"].tzinfo) if terkini["waktu"].tzinfo else datetime.now()
    offline = (now_ref - terkini["waktu"]) > timedelta(minutes=40)  # sensor kirim tiap 15 menit + buffer

    with kolom[i % len(kolom)]:
        st.markdown(
            f"""
            <div class="room-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div style="font-weight:700; font-size:0.95rem;">{lokasi}</div>
                    <span class="pill pill-{level}">{icon}</span>
                </div>
                <div style="font-size:1.5rem; font-weight:800; margin-top:.25rem;">
                    {terkini['suhu']}°C · {terkini['kelembapan']}%
                </div>
                <div style="color:#94a3b8; font-size:0.76rem;">
                    {terkini['waktu'].strftime('%d-%m %H:%M')} · {'📡 offline' if offline else '📶 online'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.line_chart(df_l.set_index("waktu")["suhu"].tail(30), height=70)

if ada_alarm:
    st.toast("⚠️ Ada ruangan di luar standar suhu/kelembapan!", icon="🚨")

st.divider()

# ── Detail per ruangan ────────────────────────────────────────────────
st.sidebar.header("⚙️ Fokus Pemantauan")
pilihan_lokasi = st.sidebar.selectbox("Pilih ruangan:", lokasi_list)
df_filtered = df[df["lokasi"] == pilihan_lokasi].sort_values("waktu")
standar = get_standar(pilihan_lokasi, ambang)

terkini = df_filtered.iloc[-1]
suhu_terkini = float(terkini["suhu"])
lembab_terkini = float(terkini["kelembapan"])
waktu_terkini = terkini["waktu"]
status, level, pesan_alert = evaluasi_status(suhu_terkini, lembab_terkini, standar)
icon = STATUS_ICON[level]

if level != "ok":
    st.error(f"**{pesan_alert}** — segera tindak lanjuti sesuai SOP kestabilan sediaan.")
else:
    st.success(pesan_alert)

df_24 = df_filtered[df_filtered["waktu"] >= (df_filtered["waktu"].max() - pd.Timedelta(hours=24))]
mkt_24 = hitung_mkt(df_24["suhu"]) if not df_24.empty else None

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Suhu Terkini", f"{suhu_terkini} °C")
c2.metric("Kelembapan", f"{lembab_terkini} %")
c3.metric("Status", f"{icon} {status}")
c4.metric("Min / Max 24 Jam", f"{df_24['suhu'].min():.1f} / {df_24['suhu'].max():.1f}°C" if not df_24.empty else "-")
c5.metric(
    "MKT 24 Jam",
    f"{mkt_24}°C" if mkt_24 is not None else "-",
    help="Mean Kinetic Temperature (formula Haynes) — suhu efektif kumulatif, metrik standar GDP/GSP farmasi.",
)

st.write("")

tab1, tab2, tab3 = st.tabs(["📈 Grafik & Batas Standar", "🚨 Riwayat Penyimpangan (Excursion)", "📋 Tabel & Ekspor Data"])

with tab1:
    fig_suhu = grafik_time_series_dengan_batas(
        df_filtered, "suhu", standar["suhu_min"], standar["suhu_max"], satuan="°C",
        judul=f"Suhu — {pilihan_lokasi} (zona hijau = standar {standar['suhu_min']}–{standar['suhu_max']}°C)",
    )
    st.plotly_chart(fig_suhu, use_container_width=True)

    fig_lembab = grafik_time_series_dengan_batas(
        df_filtered, "kelembapan", standar["lembab_min"], standar["lembab_max"], satuan="%",
        judul=f"Kelembapan — {pilihan_lokasi}",
    )
    st.plotly_chart(fig_lembab, use_container_width=True)

with tab2:
    excursions = deteksi_excursion(df_filtered, standar)
    if not excursions:
        st.success("✅ Tidak ada penyimpangan tercatat untuk ruangan ini.")
    else:
        df_exc = pd.DataFrame(
            [
                {
                    "Mulai": e["mulai"].strftime("%d-%m-%Y %H:%M"),
                    "Selesai": e["selesai"].strftime("%d-%m-%Y %H:%M"),
                    "Durasi (menit)": e["durasi_menit"],
                    "Suhu Puncak": e["suhu_puncak"],
                    "Status": "🔴 Masih berlangsung" if e["_berlangsung"] else "✅ Selesai",
                }
                for e in excursions
            ]
        )
        st.dataframe(df_exc, use_container_width=True, hide_index=True)
        st.caption(
            "Excursion dihitung dari pembacaan berturut-turut yang berada di luar ambang batas. "
            "Durasi mengikuti selisih waktu antar pembacaan pertama & terakhir dalam kejadian tsb."
        )

with tab3:
    st.markdown(f"**Riwayat Suhu: {pilihan_lokasi}**")
    df_display = df_filtered[["waktu", "suhu", "kelembapan"]].copy()
    df_display["waktu"] = df_display["waktu"].dt.strftime("%d-%m-%Y %H:%M:%S")
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Unduh CSV",
        df_display.to_csv(index=False).encode("utf-8"),
        file_name=f"riwayat_suhu_{pilihan_lokasi}.csv",
        mime="text/csv",
    )
