import streamlit as st
import pandas as pd

from core.notifications import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, FONNTE_TOKEN, WHATSAPP_NUMBERS,
    kirim_test_telegram, kirim_test_whatsapp, get_alarm_log,
)

st.title("🔔 Notifikasi Alarm")
st.markdown(
    "Notifikasi alarm ke **Telegram** & **WhatsApp** dikirim otomatis oleh Supabase Edge Function "
    "`cek-alarm-suhu` setiap ada data baru di luar standar — tetap jalan 24/7 walau dashboard ini "
    "tidak dibuka. Lihat `README.md` untuk cara deploy & mengisi kredensialnya."
)

status_telegram = "✅ Terkonfigurasi" if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS else "⚪ Belum diisi"
status_wa = "✅ Terkonfigurasi" if FONNTE_TOKEN and WHATSAPP_NUMBERS else "⚪ Belum diisi"
c1, c2 = st.columns(2)
c1.metric("Telegram (uji coba dari dashboard ini)", status_telegram)
c2.metric("WhatsApp / Fonnte (uji coba dari dashboard ini)", status_wa)

st.caption(
    "Kredensial di atas dibaca dari `st.secrets` aplikasi ini dan hanya dipakai untuk tombol "
    "**Test Kirim** di bawah. Edge Function punya secrets-nya sendiri (diisi lewat `supabase secrets set`) "
    "— isi keduanya dengan nilai yang sama."
)

st.divider()
st.subheader("🧪 Test Kirim Notifikasi")
pesan_test = st.text_area(
    "Isi pesan uji coba",
    value="🔧 Ini pesan uji coba dari Command Center Farmasi. Jika Anda menerima ini, konfigurasi notifikasi sudah benar.",
)
colt1, colt2 = st.columns(2)
with colt1:
    if st.button("📨 Kirim Test ke Telegram", use_container_width=True):
        ok, info = kirim_test_telegram(pesan_test)
        (st.success if ok else st.error)(info)
with colt2:
    if st.button("📨 Kirim Test ke WhatsApp", use_container_width=True):
        ok, info = kirim_test_whatsapp(pesan_test)
        (st.success if ok else st.error)(info)

st.divider()
st.subheader("📜 Riwayat Status Notifikasi per Ruangan")
try:
    df_log = get_alarm_log()
    if df_log.empty:
        st.caption("Belum ada riwayat notifikasi (tabel `alarm_log` masih kosong).")
    else:
        df_log["updated_at"] = pd.to_datetime(df_log["updated_at"]).dt.strftime("%d-%m-%Y %H:%M:%S")
        df_log["last_notified_at"] = pd.to_datetime(df_log["last_notified_at"]).dt.strftime("%d-%m-%Y %H:%M:%S")
        st.dataframe(
            df_log[["lokasi", "last_status", "last_notified_at", "updated_at"]].rename(
                columns={
                    "lokasi": "Ruangan",
                    "last_status": "Status Terakhir",
                    "last_notified_at": "Notifikasi Terakhir Dikirim",
                    "updated_at": "Terakhir Diperbarui",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
except Exception as e:
    st.caption(f"Tabel `alarm_log` belum tersedia atau belum bisa diakses ({e}). Buat tabelnya dulu — lihat README.md.")
