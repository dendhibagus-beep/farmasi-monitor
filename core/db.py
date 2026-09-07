"""
Lapisan akses data bersama. Semua modul (halaman) mengambil data lewat sini,
supaya kalau nanti ada modul baru (inventori, distribusi, dst.) cukup import
fungsi yang sudah ada, tidak perlu tulis ulang koneksi database.
"""

import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client


@st.cache_resource
def init_connection() -> Client:
    url = st.secrets.get("SUPABASE_URL", "PASTE_URL_ANDA_DISINI")
    key = st.secrets.get("SUPABASE_KEY", "PASTE_API_KEY_ANDA_DISINI")
    return create_client(url, key)


TZ_JAKARTA = "Asia/Jakarta"


@st.cache_data(ttl=15)
def get_log_suhu() -> pd.DataFrame:
    supabase = init_connection()
    resp = supabase.table("log_suhu").select("*").order("waktu", desc=False).execute()
    df = pd.DataFrame(resp.data)
    if not df.empty:
        # Database menyimpan waktu dalam UTC (timestamptz) — konversi ke WIB
        # supaya semua jam yang tampil di dashboard sesuai waktu Jakarta.
        df["waktu"] = pd.to_datetime(df["waktu"], utc=True).dt.tz_convert(TZ_JAKARTA)
        df["suhu"] = df["suhu"].astype(float)
        df["kelembapan"] = df["kelembapan"].astype(float)
    return df


@st.cache_data(ttl=30)
def get_ambang_batas() -> dict:
    """Ambang batas kustom per-ruangan yang diatur admin di modul Pengaturan.
    Ruangan yang belum diatur akan memakai standar default berdasarkan kategori."""
    supabase = init_connection()
    resp = supabase.table("ambang_batas").select("*").execute()
    return {row["lokasi"]: row for row in resp.data}


def set_ambang_batas(lokasi: str, suhu_min: float, suhu_max: float, lembab_min: float, lembab_max: float):
    supabase = init_connection()
    supabase.table("ambang_batas").upsert(
        {
            "lokasi": lokasi,
            "suhu_min": suhu_min,
            "suhu_max": suhu_max,
            "lembab_min": lembab_min,
            "lembab_max": lembab_max,
        },
        on_conflict="lokasi",
    ).execute()
    get_ambang_batas.clear()


def hapus_ambang_batas(lokasi: str):
    supabase = init_connection()
    supabase.table("ambang_batas").delete().eq("lokasi", lokasi).execute()
    get_ambang_batas.clear()


DEFAULT_STANDAR = {
    "kulkas": {"suhu_min": 2.0, "suhu_max": 8.0, "lembab_min": 0.0, "lembab_max": 100.0},
    "default": {"suhu_min": 18.0, "suhu_max": 25.0, "lembab_min": 35.0, "lembab_max": 65.0},
}


def get_standar(lokasi: str, ambang_dict: dict | None = None) -> dict:
    """Ambang batas efektif untuk sebuah ruangan: pakai kustom dari database
    jika sudah diatur, kalau belum jatuh ke default berdasarkan kategori nama."""
    if ambang_dict and lokasi in ambang_dict:
        row = ambang_dict[lokasi]
        return {
            "suhu_min": float(row["suhu_min"]),
            "suhu_max": float(row["suhu_max"]),
            "lembab_min": float(row["lembab_min"]),
            "lembab_max": float(row["lembab_max"]),
        }
    kategori = "kulkas" if "kulkas" in lokasi.lower() else "default"
    return dict(DEFAULT_STANDAR[kategori])


def evaluasi_status(suhu: float, lembab: float, standar: dict):
    """Mengembalikan tuple (status, level, pesan). level: ok | warning | danger."""
    if suhu < standar["suhu_min"]:
        return "OVER-CHILLED", "danger", f"Suhu terlalu DINGIN ({suhu}°C)!"
    if suhu > standar["suhu_max"]:
        return "OVER-HEATED", "danger", f"Suhu terlalu PANAS ({suhu}°C)!"
    if lembab < standar["lembab_min"] or lembab > standar["lembab_max"]:
        return "KELEMBAPAN TIDAK STANDAR", "warning", f"Kelembapan di luar rentang ({lembab}%)!"
    return "AMAN TERKENDALI", "ok", "Kondisi suhu & kelembapan terpantau stabil."


# ── Modul Paraf Harian (Petugas Logistik saat jam kerja / Duty Farmasi di luar jam kerja) ──

def simpan_paraf_harian(tanggal, lokasi: str, nama: str, peran: str, catatan: str, tanda_tangan_b64: str | None):
    supabase = init_connection()
    supabase.table("paraf_harian").insert(
        {
            "tanggal": str(tanggal),
            "lokasi": lokasi,
            "nama_petugas": nama,
            "peran": peran,
            "catatan": catatan,
            "tanda_tangan_base64": tanda_tangan_b64,
        }
    ).execute()
    get_paraf_harian.clear()


@st.cache_data(ttl=10)
def get_paraf_harian(bulan_awal=None, bulan_akhir=None) -> pd.DataFrame:
    supabase = init_connection()
    q = supabase.table("paraf_harian").select("*").order("tanggal", desc=True).order("dibuat_pada", desc=True)
    if bulan_awal:
        q = q.gte("tanggal", str(bulan_awal))
    if bulan_akhir:
        q = q.lte("tanggal", str(bulan_akhir))
    resp = q.execute()
    df = pd.DataFrame(resp.data)
    if not df.empty:
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
        df["dibuat_pada"] = pd.to_datetime(df["dibuat_pada"], utc=True).dt.tz_convert(TZ_JAKARTA)
    return df


def hitung_kepatuhan_paraf(df_paraf: pd.DataFrame, lokasi: str, tahun: int, bulan: int) -> dict:
    """Menghitung kelengkapan paraf harian untuk sebuah ruangan dalam satu bulan:
    berapa hari sudah diparaf, dan tanggal mana saja yang masih bolong."""
    import calendar

    jumlah_hari = calendar.monthrange(tahun, bulan)[1]
    semua_tanggal = {date(tahun, bulan, d) for d in range(1, jumlah_hari + 1)}

    if df_paraf.empty:
        tanggal_terisi = set()
    else:
        df_l = df_paraf[df_paraf["lokasi"] == lokasi]
        tanggal_terisi = set(df_l["tanggal"])

    tanggal_terisi = tanggal_terisi & semua_tanggal
    hari_ini = date.today()
    tanggal_kosong = sorted(t for t in (semua_tanggal - tanggal_terisi) if t <= hari_ini)
    hari_berjalan = min(hari_ini.day, jumlah_hari) if (hari_ini.year, hari_ini.month) == (tahun, bulan) else jumlah_hari

    return {
        "jumlah_hari_bulan": jumlah_hari,
        "hari_berjalan": hari_berjalan,
        "hari_terisi": len(tanggal_terisi),
        "tanggal_kosong": tanggal_kosong,
    }


# ── Modul Verifikasi Bulanan (Penanggung Jawab — tanda tangan sekali sebulan) ──

def simpan_verifikasi_bulanan(bulan_label: str, lokasi: str, nama: str, jabatan: str, catatan: str, tanda_tangan_b64: str | None):
    supabase = init_connection()
    supabase.table("verifikasi_bulanan").insert(
        {
            "bulan": bulan_label,
            "lokasi": lokasi,
            "nama_penanggung_jawab": nama,
            "jabatan": jabatan,
            "catatan": catatan,
            "tanda_tangan_base64": tanda_tangan_b64,
        }
    ).execute()
    get_verifikasi_bulanan.clear()


@st.cache_data(ttl=10)
def get_verifikasi_bulanan(limit: int = 100) -> pd.DataFrame:
    supabase = init_connection()
    resp = (
        supabase.table("verifikasi_bulanan")
        .select("*")
        .order("dibuat_pada", desc=True)
        .limit(limit)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if not df.empty:
        df["dibuat_pada"] = pd.to_datetime(df["dibuat_pada"], utc=True).dt.tz_convert(TZ_JAKARTA)
    return df
