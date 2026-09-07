"""
Fungsi bantu untuk uji kirim notifikasi (Telegram/WhatsApp) dari dashboard admin,
dan membaca riwayat status alarm. Pengiriman alarm SESUNGGUHNYA dilakukan oleh
Supabase Edge Function `cek-alarm-suhu` (lihat supabase/functions/), bukan di sini —
supaya tetap jalan 24/7 walau dashboard tidak dibuka.
"""

import streamlit as st
import requests
import pandas as pd

from core.db import init_connection

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = [c.strip() for c in st.secrets.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]
FONNTE_TOKEN = st.secrets.get("FONNTE_TOKEN", "")
WHATSAPP_NUMBERS = [n.strip() for n in st.secrets.get("WHATSAPP_NUMBERS", "").split(",") if n.strip()]


def kirim_test_telegram(pesan: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return False, "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_IDS belum diisi di secrets."
    gagal = []
    for chat_id in TELEGRAM_CHAT_IDS:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"},
            timeout=10,
        )
        if not r.ok:
            gagal.append(f"{chat_id}: {r.text}")
    if gagal:
        return False, "; ".join(gagal)
    return True, f"Terkirim ke {len(TELEGRAM_CHAT_IDS)} chat Telegram."


def kirim_test_whatsapp(pesan: str):
    if not FONNTE_TOKEN or not WHATSAPP_NUMBERS:
        return False, "FONNTE_TOKEN / WHATSAPP_NUMBERS belum diisi di secrets."
    r = requests.post(
        "https://api.fonnte.com/send",
        headers={"Authorization": FONNTE_TOKEN},
        data={"target": ",".join(WHATSAPP_NUMBERS), "message": pesan},
        timeout=15,
    )
    if not r.ok:
        return False, r.text
    return True, f"Terkirim ke {len(WHATSAPP_NUMBERS)} nomor WhatsApp."


@st.cache_data(ttl=10)
def get_alarm_log() -> pd.DataFrame:
    supabase = init_connection()
    resp = supabase.table("alarm_log").select("*").order("updated_at", desc=True).execute()
    df = pd.DataFrame(resp.data)
    if not df.empty:
        df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True).dt.tz_convert("Asia/Jakarta")
        if "last_notified_at" in df.columns:
            df["last_notified_at"] = pd.to_datetime(df["last_notified_at"], utc=True, errors="coerce").dt.tz_convert("Asia/Jakarta")
    return df
