"""
Gerbang login sederhana untuk fitur-fitur sensitif (admin-only):
- Mengisi paraf untuk tanggal selain hari ini (backdating)
- Verifikasi bulanan (tanda tangan Penanggung Jawab)
- Mengubah/menghapus ambang batas suhu

CATATAN JUJUR SOAL KEAMANAN: ini satu password bersama (disimpan di st.secrets),
BUKAN sistem akun per-individu. Ini cukup untuk mencegah orang yang kebetulan
tahu URL dashboard mengubah pengaturan kritis — tapi TIDAK melindungi dari
seseorang yang punya akses langsung ke SUPABASE_KEY (anon key) dan memanggil
API Supabase langsung dari luar aplikasi ini. Untuk kontrol akses per-individu
yang lebih kuat (siapa tepatnya yang mengubah apa), upgrade ke Supabase Auth
di masa depan adalah langkah lanjutan yang disarankan.
"""

import streamlit as st


def _sudah_login() -> bool:
    return st.session_state.get("is_admin", False)


def require_admin_login(alasan: str = "mengakses fitur ini") -> bool:
    """Tampilkan gerbang login kalau belum login sebagai admin.
    Mengembalikan True kalau sudah/berhasil login, False kalau belum —
    pemanggil sebaiknya menyembunyikan/menonaktifkan aksi terkait saat False,
    bukan selalu memanggil st.stop() (supaya bagian lain halaman tetap tampil)."""
    if _sudah_login():
        return True

    admin_password = st.secrets.get("ADMIN_PASSWORD", "")
    if not admin_password:
        st.warning(
            "⚠️ `ADMIN_PASSWORD` belum diatur di secrets aplikasi. Untuk sementara, "
            "fitur ini tetap terbuka tanpa proteksi login — atur secrets untuk mengaktifkannya."
        )
        return True

    st.info(f"🔒 Login sebagai Admin/Penanggung Jawab diperlukan untuk {alasan}.")
    with st.form(f"form_login_admin_{alasan}"):
        password_input = st.text_input("Password Admin", type="password")
        submit = st.form_submit_button("Masuk")
    if submit:
        if password_input == admin_password:
            st.session_state["is_admin"] = True
            st.rerun()
        else:
            st.error("Password salah.")
    return False


def render_logout_button():
    if _sudah_login():
        with st.sidebar:
            st.success("🔓 Mode Admin aktif")
            if st.button("Keluar dari mode Admin", use_container_width=True):
                st.session_state["is_admin"] = False
                st.rerun()
