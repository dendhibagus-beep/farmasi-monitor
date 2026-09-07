"""
Generator laporan kepatuhan harian dalam format HTML siap cetak (bisa disimpan
sebagai PDF lewat dialog Print di browser: Ctrl/Cmd+P -> Save as PDF).
Dipakai modul Verifikasi & Tanda Tangan Supervisor untuk kebutuhan akreditasi.
"""

from datetime import datetime


def buat_laporan_html(tanggal, ringkasan_rows: list[dict], nama: str, jabatan: str, catatan: str,
                       tanda_tangan_data_url: str | None) -> str:
    baris_tabel = "\n".join(
        f"""<tr>
            <td>{r['Ruangan']}</td>
            <td>{r['Jumlah Pembacaan']}</td>
            <td>{r['Min (°C)']}</td>
            <td>{r['Max (°C)']}</td>
            <td>{r['MKT (°C)']}</td>
            <td>{r['Penyimpangan']}</td>
            <td>{r['Status']}</td>
        </tr>"""
        for r in ringkasan_rows
    )

    tanda_tangan_html = (
        f'<img src="{tanda_tangan_data_url}" style="height:90px; border-bottom:1px solid #333;">'
        if tanda_tangan_data_url
        else '<div style="height:90px; border-bottom:1px solid #333;"></div>'
    )

    dibuat = datetime.now().strftime("%d-%m-%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Laporan Verifikasi Suhu — {tanggal}</title>
<style>
    body {{ font-family: Arial, Helvetica, sans-serif; color:#111; padding:2rem; max-width:800px; margin:auto; }}
    h1 {{ font-size:1.3rem; margin-bottom:0; }}
    .sub {{ color:#555; margin-top:0.2rem; margin-bottom:1.5rem; }}
    table {{ width:100%; border-collapse:collapse; margin-bottom:1.5rem; }}
    th, td {{ border:1px solid #ccc; padding:6px 8px; font-size:0.85rem; text-align:left; }}
    th {{ background:#f2f2f2; }}
    .ttd-box {{ margin-top:2rem; display:flex; justify-content:flex-end; }}
    .ttd-inner {{ text-align:center; width:260px; }}
    .footer {{ margin-top:2rem; font-size:0.75rem; color:#888; }}
    @media print {{ body {{ padding:0; }} }}
</style>
</head>
<body>
    <h1>💊 Laporan Verifikasi Harian Suhu & Kelembapan</h1>
    <div class="sub">Command Center Logistik &amp; Perbekalan Farmasi — Tanggal: <b>{tanggal}</b></div>

    <table>
        <thead>
            <tr>
                <th>Ruangan</th><th>Jumlah Pembacaan</th><th>Min</th><th>Max</th>
                <th>MKT</th><th>Penyimpangan</th><th>Status</th>
            </tr>
        </thead>
        <tbody>
            {baris_tabel}
        </tbody>
    </table>

    <p><b>Catatan / Tindak Lanjut:</b><br>{catatan or '-'}</p>

    <div class="ttd-box">
        <div class="ttd-inner">
            {tanda_tangan_html}
            <div style="margin-top:0.4rem;"><b>{nama}</b></div>
            <div>{jabatan}</div>
        </div>
    </div>

    <div class="footer">Dokumen ini dihasilkan otomatis oleh sistem pada {dibuat}. Gunakan Ctrl/Cmd+P
    di browser lalu pilih "Save as PDF" untuk menyimpan sebagai dokumen PDF untuk keperluan audit/akreditasi.</div>
</body>
</html>"""
