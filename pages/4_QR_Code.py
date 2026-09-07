import io

import streamlit as st

from core.db import get_log_suhu

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

st.title("🔗 QR Code Ruangan")
st.markdown(
    "Buat **QR Code** untuk ditempel fisik di tiap ruangan. Saat di-scan, staf/petugas langsung "
    "diarahkan ke halaman publik yang menampilkan kondisi suhu ruangan tsb secara real-time — "
    "tanpa perlu login atau buka dashboard penuh."
)

if not HAS_QRCODE:
    st.error("Library `qrcode` belum terpasang. Tambahkan `qrcode[pil]` ke requirements.txt lalu deploy ulang.")
    st.stop()

df = get_log_suhu()
if df.empty:
    st.info("Belum ada data ruangan. QR Code akan muncul otomatis setelah sensor pertama mengirim data.")
    st.stop()

base_url = st.text_input(
    "URL aplikasi yang sudah di-deploy (contoh: https://farmasi-monitor.streamlit.app)",
    value=st.session_state.get("base_url", ""),
    key="base_url",
    help="Alamat publik aplikasi Streamlit Anda setelah di-deploy (Streamlit Community Cloud, dsb).",
)

if not base_url:
    st.info("Masukkan URL aplikasi terlebih dahulu untuk membuat QR Code.")
    st.stop()

base_url = base_url.rstrip("/")
daftar_lokasi = sorted(df["lokasi"].unique())
kolom = st.columns(3)

for i, lokasi in enumerate(daftar_lokasi):
    target_url = f"{base_url}/?ruangan={lokasi.replace(' ', '%20')}"
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    with kolom[i % 3]:
        st.markdown(f"<div class='room-card' style='text-align:center;'>", unsafe_allow_html=True)
        st.image(buf.getvalue(), caption=lokasi, use_container_width=True)
        st.caption(target_url)
        st.download_button(
            "⬇️ Unduh PNG",
            buf.getvalue(),
            file_name=f"qr_{lokasi}.png",
            mime="image/png",
            key=f"dl_{lokasi}",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
