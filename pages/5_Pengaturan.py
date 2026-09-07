import streamlit as st

from core.db import get_log_suhu, get_ambang_batas, get_standar, set_ambang_batas, hapus_ambang_batas
from core.auth import require_admin_login

st.title("⚙️ Pengaturan Ambang Batas Suhu & Kelembapan")

if not require_admin_login("mengubah ambang batas suhu"):
    st.stop()

st.caption(
    "Secara default, ruangan yang namanya mengandung kata **\"kulkas\"** memakai standar 2–8°C, "
    "ruangan lain memakai 18–25°C. Atur di sini bila sebuah ruangan butuh ambang batas khusus."
)

df = get_log_suhu()
ambang = get_ambang_batas()

if df.empty:
    st.info("Belum ada ruangan terdeteksi dari data sensor.")
else:
    lokasi_list = sorted(df["lokasi"].unique())
    lokasi_pilih = st.selectbox("Pilih ruangan", lokasi_list)
    standar_saat_ini = get_standar(lokasi_pilih, ambang)
    kustom = lokasi_pilih in ambang

    st.markdown(f"**Status:** {'🔧 Memakai ambang batas kustom' if kustom else '📐 Memakai standar default (kategori)'}")

    with st.form("form_ambang"):
        c1, c2 = st.columns(2)
        with c1:
            suhu_min = st.number_input("Suhu Minimum (°C)", value=float(standar_saat_ini["suhu_min"]), step=0.5)
            lembab_min = st.number_input("Kelembapan Minimum (%)", value=float(standar_saat_ini["lembab_min"]), step=1.0)
        with c2:
            suhu_max = st.number_input("Suhu Maksimum (°C)", value=float(standar_saat_ini["suhu_max"]), step=0.5)
            lembab_max = st.number_input("Kelembapan Maksimum (%)", value=float(standar_saat_ini["lembab_max"]), step=1.0)

        simpan = st.form_submit_button("💾 Simpan Ambang Batas Kustom", type="primary", use_container_width=True)
        if simpan:
            if suhu_min >= suhu_max:
                st.error("Suhu minimum harus lebih kecil dari suhu maksimum.")
            elif lembab_min >= lembab_max:
                st.error("Kelembapan minimum harus lebih kecil dari kelembapan maksimum.")
            else:
                set_ambang_batas(lokasi_pilih, suhu_min, suhu_max, lembab_min, lembab_max)
                st.success(f"Ambang batas untuk **{lokasi_pilih}** disimpan. Perubahan langsung berlaku di semua modul.")
                st.rerun()

    if kustom:
        if st.button("↩️ Kembalikan ke standar default (hapus kustom)", use_container_width=True):
            hapus_ambang_batas(lokasi_pilih)
            st.success(f"Ambang batas kustom untuk **{lokasi_pilih}** dihapus, kembali ke standar default.")
            st.rerun()

    st.divider()
    st.subheader("📋 Semua Ambang Batas Kustom Tersimpan")
    if not ambang:
        st.caption("Belum ada ruangan dengan ambang batas kustom.")
    else:
        rows = [
            {
                "Ruangan": lokasi,
                "Suhu Min": row["suhu_min"],
                "Suhu Max": row["suhu_max"],
                "Kelembapan Min": row["lembab_min"],
                "Kelembapan Max": row["lembab_max"],
            }
            for lokasi, row in ambang.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.caption(
        "⚠️ Edge Function pengirim alarm (`cek-alarm-suhu`) juga membaca tabel `ambang_batas` ini, "
        "jadi perubahan di sini otomatis berlaku pada notifikasi Telegram/WhatsApp — tidak perlu deploy ulang."
    )

st.divider()
st.subheader("🧩 Modul Mendatang (Super App Logistik Farmasi)")
st.markdown(
    """
Sistem ini dibangun modular — setiap fitur baru cukup ditambahkan sebagai modul baru tanpa
mengubah modul yang sudah ada. Beberapa modul yang bisa dikembangkan selanjutnya:

- 📦 **Inventori Obat** — stok, tanggal kedaluwarsa, ambang batas stok minimum
- 🚚 **Distribusi & Pengiriman** — pelacakan pengiriman antar-fasilitas dengan monitoring suhu cold chain
- 🧾 **Pengadaan** — permintaan & persetujuan pembelian
- 👥 **Manajemen Pengguna** — peran admin/supervisor/staf dengan hak akses berbeda
- 📊 **Laporan Terpadu** — gabungan data suhu, stok, dan distribusi dalam satu laporan akreditasi
"""
)
