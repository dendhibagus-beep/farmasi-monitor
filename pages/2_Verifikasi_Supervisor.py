import base64
import io
from datetime import date

import streamlit as st
import pandas as pd

from core.db import get_log_suhu, get_ambang_batas, get_standar, simpan_verifikasi, get_verifikasi_harian
from core.analytics import deteksi_excursion, hitung_mkt
from core.report import buat_laporan_html

try:
    from streamlit_drawable_canvas import st_canvas
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False

st.title("📝 Verifikasi Harian & Tanda Tangan Supervisor")
st.caption(
    "Modul kepatuhan (compliance) untuk kebutuhan **akreditasi rumah sakit** — dokumentasi tinjauan "
    "harian suhu penyimpanan sediaan, ditandatangani oleh penanggung jawab/supervisor."
)

df = get_log_suhu()
ambang = get_ambang_batas()

if df.empty:
    st.info("Belum ada data suhu untuk diverifikasi.")
    st.stop()

lokasi_list = sorted(df["lokasi"].unique())
col_a, col_b = st.columns(2)
with col_a:
    tanggal_pilih = st.date_input("Tanggal peninjauan", value=date.today())
with col_b:
    lokasi_pilih = st.multiselect("Ruangan yang ditinjau", lokasi_list, default=lokasi_list)

df["tanggal"] = df["waktu"].dt.date
df_hari = df[(df["tanggal"] == tanggal_pilih) & (df["lokasi"].isin(lokasi_pilih))]

ringkasan_rows = []

if df_hari.empty:
    st.warning("Tidak ada data pembacaan pada tanggal & ruangan yang dipilih.")
else:
    st.subheader("Ringkasan Kepatuhan")
    total_excursion = 0
    for lokasi in lokasi_pilih:
        df_l = df_hari[df_hari["lokasi"] == lokasi]
        if df_l.empty:
            continue
        standar = get_standar(lokasi, ambang)
        excs = deteksi_excursion(df_l, standar)
        total_excursion += len(excs)
        mkt = hitung_mkt(df_l["suhu"])
        ringkasan_rows.append(
            {
                "Ruangan": lokasi,
                "Jumlah Pembacaan": len(df_l),
                "Min (°C)": round(df_l["suhu"].min(), 1),
                "Max (°C)": round(df_l["suhu"].max(), 1),
                "MKT (°C)": mkt if mkt is not None else "-",
                "Penyimpangan": len(excs),
                "Status": "✅ Patuh" if len(excs) == 0 else f"⚠️ {len(excs)} penyimpangan",
            }
        )
    st.dataframe(pd.DataFrame(ringkasan_rows), use_container_width=True, hide_index=True)

    if total_excursion == 0:
        st.success("✅ Semua ruangan yang ditinjau berada dalam standar sepanjang hari ini.")
    else:
        st.warning(
            f"⚠️ Ditemukan total {total_excursion} kejadian penyimpangan pada tanggal ini. "
            "Catat tindak lanjut pada kolom catatan di bawah sebelum menandatangani."
        )

    st.divider()
    st.subheader("✍️ Tanda Tangan Supervisor / Penanggung Jawab")

    c1, c2 = st.columns(2)
    with c1:
        nama = st.text_input("Nama lengkap")
        jabatan = st.text_input("Jabatan", placeholder="mis. Apoteker Penanggung Jawab")
    with c2:
        catatan = st.text_area("Catatan / tindak lanjut (jika ada penyimpangan)", height=100)

    tanda_tangan_b64 = None
    if HAS_CANVAS:
        st.caption("Gambar tanda tangan pada kotak berikut:")
        canvas_result = st_canvas(
            fill_color="rgba(255,255,255,0)",
            stroke_width=2,
            stroke_color="#0f172a",
            background_color="#ffffff",
            height=150,
            width=400,
            drawing_mode="freedraw",
            key=f"canvas_{tanggal_pilih}",
        )
        if canvas_result.image_data is not None and canvas_result.image_data[:, :, 3].sum() > 0:
            from PIL import Image

            img = Image.fromarray(canvas_result.image_data.astype("uint8"))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            tanda_tangan_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    else:
        st.info(
            "Komponen tanda tangan digital (`streamlit-drawable-canvas`) belum terpasang. "
            "Tambahkan ke requirements.txt untuk mengaktifkan gambar tanda tangan. Sementara itu, "
            "verifikasi tetap bisa disimpan dengan nama & jabatan sebagai bukti otorisasi."
        )

    tombol_nonaktif = not nama or not jabatan
    if st.button("💾 Simpan Verifikasi & Tanda Tangan", type="primary", disabled=tombol_nonaktif, use_container_width=True):
        simpan_verifikasi(tanggal_pilih, ", ".join(lokasi_pilih), nama, jabatan, catatan, tanda_tangan_b64)
        st.success("Verifikasi berhasil disimpan dan siap dipakai untuk keperluan audit/akreditasi.")

        data_url = f"data:image/png;base64,{tanda_tangan_b64}" if tanda_tangan_b64 else None
        html_laporan = buat_laporan_html(tanggal_pilih, ringkasan_rows, nama, jabatan, catatan, data_url)
        st.download_button(
            "🖨️ Unduh Laporan (siap cetak/PDF)",
            html_laporan.encode("utf-8"),
            file_name=f"laporan_verifikasi_{tanggal_pilih}.html",
            mime="text/html",
        )
        st.caption("Buka file yang diunduh di browser, lalu Ctrl/Cmd+P → Save as PDF untuk arsip akreditasi.")

st.divider()
st.subheader("📜 Riwayat Verifikasi Tersimpan")
df_riwayat = get_verifikasi_harian()
if df_riwayat.empty:
    st.caption("Belum ada riwayat verifikasi.")
else:
    for _, row in df_riwayat.iterrows():
        with st.expander(
            f"{row['tanggal']} · {row['lokasi']} · ditandatangani oleh {row['nama_supervisor']} ({row['jabatan']})"
        ):
            st.write(f"**Catatan:** {row['catatan'] or '-'}")
            st.caption(f"Disimpan pada: {row['dibuat_pada']}")
            if row.get("tanda_tangan_base64"):
                st.image(base64.b64decode(row["tanda_tangan_base64"]), width=250, caption="Tanda tangan digital")
