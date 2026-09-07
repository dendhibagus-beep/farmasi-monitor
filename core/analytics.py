"""
Analitik ala aplikasi monitoring suhu komersil (Testo, ELPRO, Dickson, dsb):
- Mean Kinetic Temperature (MKT): suhu efektif kumulatif, metrik standar GDP/GSP farmasi.
- Deteksi excursion (penyimpangan): mengelompokkan pembacaan berturut-turut yang
  di luar standar menjadi kejadian dengan durasi & puncak deviasi.
"""

import math
import pandas as pd


def hitung_mkt(suhu_celsius: pd.Series, delta_h: float = 83144.0, r: float = 8.3144):
    """Mean Kinetic Temperature memakai formula Haynes.
    delta_h = energi aktivasi standar (J/mol) yang lazim dipakai industri farmasi.
    Mengembalikan suhu MKT dalam °C, atau None jika data tidak cukup."""
    s = pd.Series(suhu_celsius).dropna()
    if s.empty:
        return None
    kelvin = s + 273.15
    n = len(kelvin)
    try:
        jumlah = sum(math.exp(-delta_h / (r * t)) for t in kelvin)
        mkt_kelvin = delta_h / (r * math.log(n / jumlah))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    return round(mkt_kelvin - 273.15, 2)


def deteksi_excursion(df_room: pd.DataFrame, standar: dict) -> list[dict]:
    """Kelompokkan pembacaan berturut-turut yang di luar standar — SUHU MAUPUN
    KELEMBAPAN — menjadi daftar kejadian penyimpangan (excursion), lengkap
    durasi, jenis parameter yang menyimpang, dan puncak deviasi masing-masing.
    df_room harus punya kolom 'waktu', 'suhu', 'kelembapan', terurut waktu."""
    if df_room.empty:
        return []

    df_room = df_room.sort_values("waktu").reset_index(drop=True)
    tengah_suhu = (standar["suhu_min"] + standar["suhu_max"]) / 2
    tengah_lembab = (standar["lembab_min"] + standar["lembab_max"]) / 2

    def status_baris(row):
        suhu_diluar = row["suhu"] < standar["suhu_min"] or row["suhu"] > standar["suhu_max"]
        lembab_diluar = row["kelembapan"] < standar["lembab_min"] or row["kelembapan"] > standar["lembab_max"]
        return suhu_diluar, lembab_diluar

    hasil = []
    grup = None
    for _, row in df_room.iterrows():
        suhu_diluar, lembab_diluar = status_baris(row)
        if suhu_diluar or lembab_diluar:
            if grup is None:
                grup = {
                    "mulai": row["waktu"],
                    "selesai": row["waktu"],
                    "suhu_puncak": row["suhu"],
                    "lembab_puncak": row["kelembapan"],
                    "jenis": set(),
                }
            else:
                grup["selesai"] = row["waktu"]
                if abs(row["suhu"] - tengah_suhu) > abs(grup["suhu_puncak"] - tengah_suhu):
                    grup["suhu_puncak"] = row["suhu"]
                if abs(row["kelembapan"] - tengah_lembab) > abs(grup["lembab_puncak"] - tengah_lembab):
                    grup["lembab_puncak"] = row["kelembapan"]
            if suhu_diluar:
                grup["jenis"].add("Suhu")
            if lembab_diluar:
                grup["jenis"].add("Kelembapan")
        else:
            if grup is not None:
                hasil.append(grup)
                grup = None
    if grup is not None:
        grup["_berlangsung"] = True
        hasil.append(grup)

    for g in hasil:
        g.setdefault("_berlangsung", False)
        g["durasi_menit"] = round((g["selesai"] - g["mulai"]).total_seconds() / 60, 1)
        g["jenis"] = " & ".join(sorted(g["jenis"]))

    return list(reversed(hasil))
