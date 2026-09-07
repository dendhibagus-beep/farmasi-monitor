"""
Komponen grafik bersama — dipakai di halaman Monitoring maupun landing page publik,
supaya tampilan konsisten dan batas standar selalu terlihat jelas di semua grafik.
"""

import plotly.graph_objects as go
import pandas as pd


def grafik_time_series_dengan_batas(
    df: pd.DataFrame,
    kolom: str,
    batas_min: float,
    batas_max: float,
    satuan: str = "",
    judul: str | None = None,
    tinggi: int = 320,
) -> go.Figure:
    """Grafik garis dengan zona aman diarsir hijau, dan titik yang di luar batas
    otomatis berwarna merah — supaya penyimpangan langsung terlihat jelas."""
    fig = go.Figure()

    fig.add_hrect(y0=batas_min, y1=batas_max, fillcolor="#16a34a", opacity=0.10, line_width=0)
    fig.add_hline(y=batas_min, line_dash="dot", line_color="#16a34a", line_width=1.5,
                  annotation_text=f"Min {batas_min}{satuan}", annotation_font_size=10)
    fig.add_hline(y=batas_max, line_dash="dot", line_color="#16a34a", line_width=1.5,
                  annotation_text=f"Max {batas_max}{satuan}", annotation_font_size=10)

    warna_titik = df[kolom].apply(lambda v: "#dc2626" if (v < batas_min or v > batas_max) else "#2563eb")

    fig.add_trace(
        go.Scatter(
            x=df["waktu"],
            y=df[kolom],
            mode="lines+markers",
            line=dict(color="#2563eb", width=2),
            marker=dict(color=warna_titik, size=6, line=dict(width=0)),
            hovertemplate=f"%{{x|%d-%m %H:%M}}<br>%{{y}}{satuan}<extra></extra>",
        )
    )
    fig.update_layout(
        title=judul,
        height=tinggi,
        margin=dict(l=10, r=10, t=44 if judul else 15, b=10),
        yaxis_title=f"{kolom.capitalize()} ({satuan})" if satuan else kolom.capitalize(),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def gauge_suhu(suhu: float, standar: dict, tinggi: int = 260) -> go.Figure:
    """Gauge (dial) suhu real-time ala alat monitoring komersil — hijau di zona
    aman, merah di luar zona, jarum menunjuk nilai terkini."""
    lebar = max(standar["suhu_max"] - standar["suhu_min"], 1)
    lo = standar["suhu_min"] - lebar * 0.6
    hi = standar["suhu_max"] + lebar * 0.6
    warna = "#16a34a" if standar["suhu_min"] <= suhu <= standar["suhu_max"] else "#dc2626"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=suhu,
            number={"suffix": "°C", "font": {"size": 42}},
            gauge={
                "axis": {"range": [lo, hi], "tickwidth": 1},
                "bar": {"color": warna, "thickness": 0.28},
                "bgcolor": "white",
                "steps": [
                    {"range": [lo, standar["suhu_min"]], "color": "#fee2e2"},
                    {"range": [standar["suhu_min"], standar["suhu_max"]], "color": "#dcfce7"},
                    {"range": [standar["suhu_max"], hi], "color": "#fee2e2"},
                ],
                "threshold": {"line": {"color": "#0f172a", "width": 3}, "thickness": 0.85, "value": suhu},
            },
        )
    )
    fig.update_layout(height=tinggi, margin=dict(l=25, r=25, t=15, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig
