"""
Komponen tanda tangan digital — dibungkus supaya AMAN dari bug yang dikenal di
`streamlit-drawable-canvas`: library ini melempar RuntimeError saat komponen
belum sempat mengirim data dari browser (terutama di versi Streamlit terbaru).
Tanpa penanganan ini, seluruh halaman bisa crash hanya karena canvas belum
selesai dimuat. Semua halaman yang butuh tanda tangan HARUS memakai fungsi ini,
bukan memanggil st_canvas() langsung.
"""

import base64
import io

import streamlit as st

try:
    from streamlit_drawable_canvas import st_canvas
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False


def input_tanda_tangan(key: str, height: int = 150, width: int = 400, label: str | None = None) -> str | None:
    """Tampilkan kotak gambar tanda tangan dan kembalikan hasilnya sebagai
    base64 PNG. Mengembalikan None kalau kosong, komponen belum siap, atau
    library tidak tersedia — TIDAK PERNAH melempar error ke halaman."""
    if not HAS_CANVAS:
        st.info(
            "Komponen tanda tangan digital belum terpasang di server ini. "
            "Verifikasi tetap bisa disimpan dengan nama & jabatan sebagai bukti otorisasi."
        )
        return None

    if label:
        st.caption(label)

    canvas_result = st_canvas(
        fill_color="rgba(255,255,255,0)",
        stroke_width=2,
        stroke_color="#0f172a",
        background_color="#ffffff",
        height=height,
        width=width,
        drawing_mode="freedraw",
        key=key,
    )

    try:
        image_data = canvas_result.image_data
    except RuntimeError:
        # Komponen belum mengirim data dari browser (misal baru pertama kali
        # render) — ini kondisi normal, bukan error fatal. Anggap saja kosong.
        return None

    if image_data is None:
        return None

    try:
        if image_data[:, :, 3].sum() == 0:
            return None
        from PIL import Image

        img = Image.fromarray(image_data.astype("uint8"))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        # Data gambar tidak valid untuk alasan apa pun — jangan sampai
        # menjatuhkan seluruh halaman hanya karena tanda tangan gagal dibaca.
        return None
