"""
Lapisan akses data bersama. Semua modul (halaman) mengambil data lewat sini,
supaya kalau nanti ada modul baru (inventori, distribusi, dst.) cukup import
fungsi yang sudah ada, tidak perlu tulis ulang koneksi database.
"""

import streamlit as st
import pandas as pd
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


# ── Modul Verifikasi & Tanda Tangan Supervisor ──────────────────────

def simpan_verifikasi(tanggal, lokasi: str, nama: str, jabatan: str, catatan: str, tanda_tangan_b64: str | None):
    supabase = init_connection()
    supabase.table("verifikasi_harian").insert(
        {
            "tanggal": str(tanggal),
            "lokasi": lokasi,
            "nama_supervisor": nama,
            "jabatan": jabatan,
            "catatan": catatan,
            "tanda_tangan_base64": tanda_tangan_b64,
        }
    ).execute()


@st.cache_data(ttl=10)
def get_verifikasi_harian(limit: int = 200) -> pd.DataFrame:
    supabase = init_connection()
    resp = (
        supabase.table("verifikasi_harian")
        .select("*")
        .order("dibuat_pada", desc=True)
        .limit(limit)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if not df.empty and "dibuat_pada" in df.columns:
        df["dibuat_pada"] = pd.to_datetime(df["dibuat_pada"], utc=True).dt.tz_convert(TZ_JAKARTA)
    return df
