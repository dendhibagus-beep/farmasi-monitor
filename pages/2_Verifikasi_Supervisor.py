from datetime import date

import pandas as pd
import streamlit as st

from core.analytics import deteksi_excursion, hitung_mkt
from core.db import (
    get_ambang_batas,
    get_log_suhu,
    get_paraf_harian,
    get_standar,
    get_verifikasi_bulanan,
    hitung_kepatuhan_paraf,
    simpan_paraf_harian,
    simpan_verifikasi_bulanan,
)
from core.report import buat_laporan_bulanan_html, buat_laporan_harian_html
from core.signature import input_tanda_tangan

NAMA_BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
PERAN_PILIHAN = ["Petugas Logistik (Jam Kerja)", "Duty Farmasi (Luar Jam Kerja)"]

st.title("📝 Verifikasi Suhu: Paraf Harian & Tanda Tangan Bulanan")
st.caption(
    "Sistem supervisi dua tingkat untuk kebutuhan **akreditasi rumah sakit**: "
    "setiap hari, petugas logistik (jam kerja) atau duty farmasi (luar jam kerja) memaraf bahwa "
    "suhu sudah diperiksa. Setiap bulan, **Penanggung Jawab** meninjau rekap sebulan penuh dan "
    "menandatangani sekali sebagai verifikasi akhir."
)

df = get_log_suhu()
ambang = get_ambang_batas()

if df.empty:
    st.info("Belum ada data suhu untuk diverifikasi.")
    st.stop()

lokasi_list = sorted(df["lokasi"].unique())
df["tanggal"] = df["waktu"].dt.date

tab_harian, tab_bulanan = st.tabs(["📋 Paraf Harian", "🖋️ Verifikasi Bulanan (Penanggung Jawab)"])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — PARAF HARIAN
# ══════════════════════════════════════════════════════════════════
with tab_harian:
    st.subheader("Konfirmasi Pengecekan Hari Ini")

    c1, c2 = st.columns(2)
    with c1:
        tanggal_paraf = st.date_input("Tanggal pengecekan", value=date.today(), key="tgl_paraf")
        lokasi_paraf = st.selectbox("Ruangan yang diperiksa", lokasi_list, key="lokasi_paraf")
    with c2:
        peran_paraf = st.selectbox("Peran pemeriksa", PERAN_PILIHAN, key="peran_paraf")
        nama_paraf = st.text_input("Nama petugas", key="nama_paraf")

    # Tampilkan cuplikan data suhu ruangan pada tanggal terpilih, supaya jelas
    # apa yang sedang "diperiksa" saat petugas menekan tombol konfirmasi.
    df_cek = df[(df["lokasi"] == lokasi_paraf) & (df["tanggal"] == tanggal_paraf)]
    standar_paraf = get_standar(lokasi_paraf, ambang)

    if df_cek.empty:
        st.warning("Belum ada pembacaan sensor untuk ruangan & tanggal ini.")
    else:
        excs = deteksi_excursion(df_cek, standar_paraf)
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Jumlah Pembacaan", len(df_cek))
        cc2.metric("Min / Max", f"{df_cek['suhu'].min():.1f} / {df_cek['suhu'].max():.1f}°C")
        cc3.metric("Penyimpangan", len(excs))
        cc4.metric("Status", "✅ Patuh" if not excs else "⚠️ Ada penyimpangan")

    catatan_paraf = st.text_area(
        "Catatan (wajib diisi kalau ada penyimpangan)", key="catatan_paraf", height=80
    )

    pakai_ttd = st.checkbox("Sertakan gambar tanda tangan (opsional)", key="pakai_ttd_harian")
    tanda_tangan_paraf = None
    if pakai_ttd:
        tanda_tangan_paraf = input_tanda_tangan(key=f"canvas_paraf_{tanggal_paraf}_{lokasi_paraf}")

    tombol_nonaktif = not nama_paraf
    if st.button("✅ Konfirmasi Sudah Diperiksa (Paraf)", type="primary", disabled=tombol_nonaktif, use_container_width=True):
        simpan_paraf_harian(tanggal_paraf, lokasi_paraf, nama_paraf, peran_paraf, catatan_paraf, tanda_tangan_paraf)
        st.success(f"Paraf tersimpan: {lokasi_paraf} · {tanggal_paraf} · oleh {nama_paraf} ({peran_paraf}).")
        st.rerun()

    st.divider()

    # ── Riwayat paraf tanggal ini ──
    st.subheader(f"Riwayat Paraf — {tanggal_paraf.strftime('%d %B %Y')}")
    df_paraf_semua = get_paraf_harian()
    df_paraf_hari_ini = df_paraf_semua[df_paraf_semua["tanggal"] == tanggal_paraf] if not df_paraf_semua.empty else pd.DataFrame()

    if df_paraf_hari_ini.empty:
        st.caption("Belum ada paraf untuk tanggal ini.")
    else:
        for _, row in df_paraf_hari_ini.sort_values("dibuat_pada").iterrows():
            st.markdown(
                f"- **{row['lokasi']}** — {row['nama_petugas']} ({row['peran']}), "
                f"pukul {row['dibuat_pada'].strftime('%H:%M')} WIB"
                + (f" · _{row['catatan']}_" if row['catatan'] else "")
            )

    st.divider()

    # ── Kelengkapan paraf bulan berjalan ──
    st.subheader("📆 Kelengkapan Paraf Bulan Ini")
    bulan_ini, tahun_ini = date.today().month, date.today().year
    kepatuhan = hitung_kepatuhan_paraf(df_paraf_semua, lokasi_paraf, tahun_ini, bulan_ini)

    persen = (kepatuhan["hari_terisi"] / kepatuhan["hari_berjalan"] * 100) if kepatuhan["hari_berjalan"] else 0
    st.metric(
        f"{lokasi_paraf} — {NAMA_BULAN[bulan_ini - 1]} {tahun_ini}",
        f"{kepatuhan['hari_terisi']} / {kepatuhan['hari_berjalan']} hari",
        help="Dihitung dari hari berjalan bulan ini (bukan sampai akhir bulan), supaya tidak ikut menghitung hari yang belum terjadi.",
    )
    if kepatuhan["tanggal_kosong"]:
        with st.expander(f"⚠️ {len(kepatuhan['tanggal_kosong'])} hari belum diparaf"):
            st.write(", ".join(t.strftime("%d %b") for t in kepatuhan["tanggal_kosong"]))
    else:
        st.success("✅ Semua hari berjalan bulan ini sudah diparaf.")


# ══════════════════════════════════════════════════════════════════
# TAB 2 — VERIFIKASI BULANAN (PENANGGUNG JAWAB)
# ══════════════════════════════════════════════════════════════════
with tab_bulanan:
    st.subheader("Tinjauan & Tanda Tangan Bulanan")
    st.caption(
        "Dilakukan **satu kali per bulan** oleh Penanggung Jawab, setelah meninjau rekap kepatuhan "
        "paraf harian dan ringkasan suhu sepanjang bulan."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        tahun_pilih = st.selectbox("Tahun", list(range(date.today().year - 2, date.today().year + 1))[::-1], key="tahun_bulanan")
    with c2:
        bulan_pilih = st.selectbox("Bulan", list(range(1, 13)), format_func=lambda b: NAMA_BULAN[b - 1], index=date.today().month - 1, key="bulan_bulanan")
    with c3:
        lokasi_pilih_bulanan = st.multiselect("Ruangan ditinjau", lokasi_list, default=lokasi_list, key="lokasi_bulanan")

    bulan_label = f"{NAMA_BULAN[bulan_pilih - 1]} {tahun_pilih}"
    tanggal_awal = date(tahun_pilih, bulan_pilih, 1)
    tanggal_akhir_bulan = date(tahun_pilih, bulan_pilih + 1, 1) if bulan_pilih < 12 else date(tahun_pilih + 1, 1, 1)

    df_bulan = df[(df["tanggal"] >= tanggal_awal) & (df["tanggal"] < tanggal_akhir_bulan) & (df["lokasi"].isin(lokasi_pilih_bulanan))]
    df_paraf_bulan = get_paraf_harian(bulan_awal=tanggal_awal, bulan_akhir=tanggal_akhir_bulan - pd.Timedelta(days=1))

    if df_bulan.empty:
        st.warning("Tidak ada data pembacaan suhu pada bulan & ruangan yang dipilih.")
    else:
        st.subheader(f"Ringkasan {bulan_label}")
        ringkasan_rows = []
        total_excursion = 0
        for lokasi in lokasi_pilih_bulanan:
            df_l = df_bulan[df_bulan["lokasi"] == lokasi]
            if df_l.empty:
                continue
            standar = get_standar(lokasi, ambang)
            excs = deteksi_excursion(df_l, standar)
            total_excursion += len(excs)
            mkt = hitung_mkt(df_l["suhu"])
            kepatuhan = hitung_kepatuhan_paraf(df_paraf_bulan, lokasi, tahun_pilih, bulan_pilih)
            ringkasan_rows.append(
                {
                    "Ruangan": lokasi,
                    "Kepatuhan Paraf Harian": f"{kepatuhan['hari_terisi']}/{kepatuhan['hari_berjalan']} hari",
                    "Min (°C)": round(df_l["suhu"].min(), 1),
                    "Max (°C)": round(df_l["suhu"].max(), 1),
                    "MKT (°C)": mkt if mkt is not None else "-",
                    "Penyimpangan": len(excs),
                    "Status": "✅ Patuh" if len(excs) == 0 and kepatuhan["hari_terisi"] == kepatuhan["hari_berjalan"] else "⚠️ Perlu perhatian",
                }
            )
        st.dataframe(pd.DataFrame(ringkasan_rows), use_container_width=True, hide_index=True)

        ada_bolong_paraf = any(
            hitung_kepatuhan_paraf(df_paraf_bulan, l, tahun_pilih, bulan_pilih)["tanggal_kosong"] for l in lokasi_pilih_bulanan
        )
        if total_excursion == 0 and not ada_bolong_paraf:
            st.success(f"✅ Seluruh ruangan patuh standar dan paraf harian lengkap sepanjang {bulan_label}.")
        else:
            pesan = []
            if total_excursion > 0:
                pesan.append(f"{total_excursion} kejadian penyimpangan suhu")
            if ada_bolong_paraf:
                pesan.append("ada hari yang belum diparaf petugas")
            st.warning(f"⚠️ Ditemukan {' dan '.join(pesan)} pada periode ini. Tinjau catatan sebelum menandatangani.")

        st.divider()
        st.subheader("✍️ Tanda Tangan Penanggung Jawab")

        cc1, cc2 = st.columns(2)
        with cc1:
            nama_pj = st.text_input("Nama lengkap", key="nama_pj")
            jabatan_pj = st.text_input("Jabatan", placeholder="mis. Apoteker Penanggung Jawab", key="jabatan_pj")
        with cc2:
            catatan_pj = st.text_area("Catatan tinjauan bulanan", height=100, key="catatan_pj")

        tanda_tangan_pj = input_tanda_tangan(
            key=f"canvas_bulanan_{tahun_pilih}_{bulan_pilih}",
            label="Gambar tanda tangan pada kotak berikut:",
        )

        tombol_nonaktif_pj = not nama_pj or not jabatan_pj
        if st.button("💾 Simpan Verifikasi Bulanan", type="primary", disabled=tombol_nonaktif_pj, use_container_width=True):
            simpan_verifikasi_bulanan(
                bulan_label, ", ".join(lokasi_pilih_bulanan), nama_pj, jabatan_pj, catatan_pj, tanda_tangan_pj
            )
            st.success(f"Verifikasi bulanan **{bulan_label}** berhasil disimpan.")

            data_url = f"data:image/png;base64,{tanda_tangan_pj}" if tanda_tangan_pj else None
            html_laporan = buat_laporan_bulanan_html(bulan_label, ringkasan_rows, nama_pj, jabatan_pj, catatan_pj, data_url)
            st.download_button(
                "🖨️ Unduh Laporan Bulanan (siap cetak/PDF)",
                html_laporan.encode("utf-8"),
                file_name=f"laporan_bulanan_{tahun_pilih}-{bulan_pilih:02d}.html",
                mime="text/html",
            )
            st.caption("Buka file yang diunduh di browser, lalu Ctrl/Cmd+P → Save as PDF untuk arsip akreditasi.")

    st.divider()
    st.subheader("📜 Riwayat Verifikasi Bulanan Tersimpan")
    df_riwayat_bulanan = get_verifikasi_bulanan()
    if df_riwayat_bulanan.empty:
        st.caption("Belum ada riwayat verifikasi bulanan.")
    else:
        for _, row in df_riwayat_bulanan.iterrows():
            with st.expander(
                f"{row['bulan']} · {row['lokasi']} · ditandatangani oleh {row['nama_penanggung_jawab']} ({row['jabatan']})"
            ):
                st.write(f"**Catatan:** {row['catatan'] or '-'}")
                st.caption(f"Disimpan pada: {row['dibuat_pada']}")
                if row.get("tanda_tangan_base64"):
                    import base64

                    st.image(base64.b64decode(row["tanda_tangan_base64"]), width=250, caption="Tanda tangan digital")
