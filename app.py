"""
app.py - Blackout Watch
=======================
Jalankan dengan:   streamlit run app.py

Alur besar file ini (baca dari atas ke bawah):
  1. Import library + konfigurasi halaman
  2. Muat data (CSV hasil ETL di folder data/) dan klien IODA (live, dengan potret cadangan)
  3. Sidebar: rentang tahun, pemicu, wilayah, jenis
  4. Saring data (src/analisis.py)
  5. Tampilkan: angka ringkasan -> tab peta / tren / Indonesia / live / konflik / data / cara kerja

Setiap bagian diberi komentar "APA" dan "MENGAPA". Penjelasan istilah ada di docs/BELAJAR.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analisis, ioda, muat_data
from src.negara import nama_dari_iso2

# ----------------------------------------------------------------------------
# 0. KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Blackout Watch", page_icon="📵", layout="wide")

TAHUN_MIN, TAHUN_MAX = 2016, 2025
TEMPLATE = "plotly_dark"
UNGU = "#a78bfa"
WARNA_PEMICU = {
    "Unjuk rasa": "#a78bfa",
    "Konflik bersenjata": "#f87171",
    "Kekerasan komunal": "#fb923c",
    "Instabilitas politik": "#facc15",
    "Pemilu": "#34d399",
    "Kontrol informasi": "#60a5fa",
    "Ujian sekolah": "#f472b6",
    "Hari besar/peringatan": "#2dd4bf",
    "Kunjungan pejabat": "#c084fc",
    "Lainnya": "#9ca3af",
    "Tidak diketahui": "#6b7280",
}
URUTAN_PEMICU = analisis.URUTAN_PEMICU
SKALA_UNGU = ["#1a1530", "#3b2a6b", "#5b3fa0", "#7c5cd6", "#a78bfa", "#dcd0ff"]
WARNA_SINYAL = {"bgp": "#a78bfa", "ping-slash24": "#34d399", "merit-nt": "#fb923c", "gtr": "#60a5fa"}
DISCLAIMER = (
    "ℹ️ Sumber data: **#KeepItOn STOP** (Access Now) untuk pemutusan internet yang didokumentasikan 2016–2025, "
    "**IODA** (Georgia Tech) untuk deteksi gangguan konektivitas secara otomatis, dan **UCDP** untuk korban konflik "
    "bersenjata. Pemutusan yang tidak terdokumentasi tidak muncul di sini. Proyek ini bersifat edukatif dan tidak "
    "berafiliasi dengan lembaga mana pun."
)
PENJELASAN_PEMICU = {
    "Unjuk rasa": "Internet diputus saat atau menjelang demonstrasi.",
    "Konflik bersenjata": "Terjadi di wilayah perang atau operasi militer.",
    "Kekerasan komunal": "Bentrokan antar kelompok masyarakat (etnis, agama, kasta).",
    "Instabilitas politik": "Kudeta, krisis pemerintahan, pergolakan politik.",
    "Pemilu": "Menjelang, saat, atau sesudah pemungutan suara.",
    "Kontrol informasi": "Pembatasan konten atau platform tertentu tanpa krisis fisik.",
    "Ujian sekolah": "Dimatikan agar siswa tidak menyontek (Irak, Suriah, Aljazair).",
    "Hari besar/peringatan": "Hari raya, peringatan tragedi, atau tanggal sensitif.",
    "Kunjungan pejabat": "Saat pejabat tinggi berkunjung ke suatu daerah.",
}


def rapikan(fig: go.Figure, tinggi: int = 420, legenda_bawah: bool = False) -> go.Figure:
    """Gaya seragam untuk semua grafik Plotly: latar gelap transparan, grid tipis, legenda di atas.

    legenda_bawah=True memindahkan legenda ke bawah grafik untuk grafik dengan banyak kategori (agar tidak menutupi judul).
    """
    fig.update_layout(
        template=TEMPLATE,
        height=tinggi,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=70, b=10),
        title=dict(y=0.97, yanchor="top", x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif"),
    )
    if legenda_bawah:
        fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, title=None),
                          margin=dict(l=10, r=20, t=50, b=10))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#262b3a", zeroline=False)
    return fig


def gaya_peta_dunia(fig: go.Figure) -> go.Figure:
    """Peta dunia gelap, dipotong di bawah 58°LS agar Antarktika tidak memakan tempat."""
    fig.update_geos(
        showframe=False, showcoastlines=False, showland=True, landcolor="#1b2029",
        showocean=True, oceancolor="#0b0d14", showcountries=True, countrycolor="#2a2f3a",
        showlakes=False, bgcolor="rgba(0,0,0,0)",
        lataxis_range=[-58, 84], lonaxis_range=[-180, 180],
    )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), geo=dict(domain=dict(x=[0, 1], y=[0, 1])))
    return fig


def ribuan(angka: float) -> str:
    """Format 1234567 -> '1.234.567' (gaya Indonesia)."""
    return f"{int(round(angka)):,}".replace(",", ".")


def tanggal_id(ts) -> str:
    if pd.isna(ts):
        return "–"
    return pd.Timestamp(ts).strftime("%d %b %Y")


# ----------------------------------------------------------------------------
# 1. MUAT DATA (di-cache: CSV hanya dibaca sekali meskipun halaman dijalankan ulang)
# ----------------------------------------------------------------------------
@st.cache_data
def ambil_data():
    return muat_data.muat_shutdown(), muat_data.muat_konflik()


@st.cache_data(ttl=3600, show_spinner=False)
def ioda_aman(nama: str, **kw):
    """Panggil IODA live; jika gagal (timeout, API berubah), pakai potret di data/.

    MENGAPA: aplikasi publik tidak boleh mati hanya karena satu API eksternal lambat. Kembalian kedua menandai
    apakah yang tampil data live atau potret.
    """
    fungsi = {
        "ringkasan": ioda.ambil_ringkasan_negara,
        "kejadian_indonesia": lambda **k: ioda.ambil_kejadian("ID", **k),
        "kejadian_dunia": ioda.ambil_kejadian_dunia,
        "sinyal_indonesia": lambda **k: ioda.ambil_sinyal("ID", **k),
    }[nama]
    potret = {
        "ringkasan": "ringkasan_30hari",
        "kejadian_indonesia": "kejadian_indonesia",
        "kejadian_dunia": "kejadian_dunia_30hari",
        "sinyal_indonesia": "sinyal_indonesia_7hari",
    }[nama]
    try:
        df = fungsi(**kw)
        if df.empty and nama == "sinyal_indonesia":
            raise RuntimeError("sinyal kosong")
        return df, "live"
    except Exception:  # noqa: BLE001 - apa pun yang gagal, tampilkan potret
        return muat_data.muat_potret_ioda(potret), "potret"


df_semua, konflik_semua = ambil_data()

# ----------------------------------------------------------------------------
# 2. SIDEBAR: filter
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("📵 Blackout Watch")
    st.caption("Siapa yang mematikan internet, di mana, dan dengan alasan apa. 2016–2025, plus deteksi live.")

    st.subheader("Filter")
    tahun_awal, tahun_akhir = st.slider("Rentang tahun", TAHUN_MIN, TAHUN_MAX, (TAHUN_MIN, TAHUN_MAX))
    pemicu_pilihan = st.multiselect(
        "Pemicu", URUTAN_PEMICU, default=URUTAN_PEMICU,
        help="Penyebab sebenarnya menurut dokumentasi Access Now, bukan alasan resmi pemerintah.",
    )
    semua_wilayah = sorted(df_semua["wilayah"].unique())
    wilayah_pilihan = st.multiselect("Wilayah", semua_wilayah, default=semua_wilayah)
    semua_jenis = ["Pemutusan", "Pelambatan", "Pemutusan & pelambatan", "Tidak diketahui"]
    jenis_pilihan = st.multiselect("Jenis", semua_jenis, default=semua_jenis,
                                   help="Pemutusan = akses hilang total; pelambatan = sengaja dibuat sangat lambat.")
    hanya_jaringan = st.toggle(
        "Hanya pemutusan seluruh jaringan", value=False,
        help="Sembunyikan pemblokiran platform tertentu (misalnya hanya WhatsApp) dan tampilkan pemutusan jaringan penuh saja.",
    )
    sertakan_berjalan = st.toggle(
        "Hitung yang masih berjalan dari tahun sebelumnya", value=False,
        help="Cara Access Now menghitung laporan tahunan: pemutusan 2019–2021 dihitung di tiga tahun. Bawaan: dihitung di tahun mulai saja.",
    )
    mode_belajar = st.toggle("🎓 Mode belajar", value=False, help="Tampilkan penjelasan dan potongan kode di setiap bagian.")
    st.caption("Data: Access Now #KeepItOn, IODA, UCDP. Lihat tab *Data & Sumber*.")

# ----------------------------------------------------------------------------
# 3. SARING DATA
# ----------------------------------------------------------------------------
# APA: terapkan filter sidebar. MENGAPA: df_semua tetap utuh agar tab Indonesia dan pembanding tidak ikut berubah.
df = analisis.filter_data(
    df_semua, tahun_awal, tahun_akhir, pemicu_pilihan, wilayah_pilihan, jenis_pilihan,
    hanya_seluruh_jaringan=hanya_jaringan, dasar_tahun="aktif" if sertakan_berjalan else "mulai",
)
ring = analisis.ringkasan(df)

# ----------------------------------------------------------------------------
# 4. JUDUL + ANGKA RINGKASAN
# ----------------------------------------------------------------------------
st.title("📵 Blackout Watch")
st.markdown(
    "**Someone pulled the plug.** Peta dan linimasa pemutusan internet yang disengaja di seluruh dunia: siapa yang "
    "mematikan, kapan, berapa lama, dan apa yang sedang terjadi di jalanan saat itu. Ditambah deteksi gangguan "
    "konektivitas *live* dari IODA untuk Indonesia dan dunia."
)
st.info(DISCLAIMER)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Pemutusan tercatat", ribuan(ring["jumlah"]), help="Jumlah pemutusan/pelambatan unik sesuai filter.")
k2.metric("Negara", ring["negara"])
k3.metric("Total hari gelap", ribuan(ring["hari"]), help="Jumlah durasi semua pemutusan yang durasinya diketahui.")
k4.metric("Terkait kerusuhan", f"{ring['persen_kerusuhan']:.0f}%",
          help="Pemicu unjuk rasa, konflik bersenjata, kekerasan komunal, instabilitas politik, atau pemilu.")
k5.metric("Terbanyak", ring["negara_teratas"], f"{ribuan(ring['jumlah_teratas'])} kali", delta_color="off")

if df.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Longgarkan filter di sidebar.")
    st.stop()

tab_peta, tab_tren, tab_indo, tab_live, tab_konflik, tab_data, tab_cara = st.tabs(
    ["🗺️ Peta dunia", "📈 Tren & pemicu", "🇮🇩 Indonesia", "📡 Live (IODA)", "⚔️ Shutdown vs konflik", "📋 Data & Sumber", "🧭 Cara Kerja"]
)

# ----------------------------------------------------------------------------
# TAB 1: PETA DUNIA
# ----------------------------------------------------------------------------
with tab_peta:
    negara_agg = analisis.per_negara(df)
    metrik_peta = st.radio("Warna peta menurut", ["jumlah", "hari"], horizontal=True,
                           format_func=lambda m: {"jumlah": "Jumlah pemutusan", "hari": "Total hari gelap"}[m])
    peta = negara_agg[negara_agg["iso3"] != ""].copy()
    peta["log"] = np.log10(peta[metrik_peta].clip(lower=1))
    tik = [1, 3, 10, 30, 100, 300, 1000]
    fig = px.choropleth(
        peta, locations="iso3", color="log", hover_name="negara",
        hover_data={"iso3": False, "log": False, "jumlah": True, "hari": ":.0f", "pemicu_utama": True,
                    "tahun_awal": True, "tahun_akhir": True},
        color_continuous_scale=SKALA_UNGU,
        labels={"jumlah": "Pemutusan", "hari": "Hari gelap", "pemicu_utama": "Pemicu utama",
                "tahun_awal": "Pertama", "tahun_akhir": "Terakhir"},
        title=f"{'Jumlah pemutusan' if metrik_peta == 'jumlah' else 'Total hari gelap'} per negara, {tahun_awal}–{tahun_akhir} (skala log)",
    )
    fig.update_layout(coloraxis_colorbar=dict(title=None, tickvals=np.log10(tik), ticktext=[str(t) for t in tik],
                                              len=0.6, thickness=12, x=0.99))
    st.plotly_chart(gaya_peta_dunia(rapikan(fig, 560)), use_container_width=True)
    st.caption("Negara abu-abu tidak memiliki pemutusan terdokumentasi dalam rentang filter. Skala logaritmik: India "
               "(hampir separuh data dunia) akan membuat negara lain tak terlihat jika skalanya linier.")

    kiri, kanan = st.columns([3, 2])
    with kiri:
        top = analisis.top_negara(df, 12).iloc[::-1]
        fig = px.bar(top, x="jumlah", y="negara", orientation="h", color="pemicu_utama",
                     color_discrete_map=WARNA_PEMICU, text="jumlah",
                     title="12 negara dengan pemutusan terbanyak (warna = pemicu paling sering)",
                     labels={"jumlah": "Pemutusan", "negara": "", "pemicu_utama": "Pemicu utama"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        # MENGAPA: pewarnaan per pemicu memecah data jadi beberapa trace, sehingga urutan sumbu Y harus dipaksa manual
        fig.update_yaxes(categoryorder="array", categoryarray=top["negara"].tolist())
        st.plotly_chart(rapikan(fig, 460, legenda_bawah=True), use_container_width=True)
    with kanan:
        peringkat, jumlah_id = analisis.peringkat_negara(df, "Indonesia")
        if peringkat:
            st.metric("Posisi Indonesia", f"#{peringkat} dari {ring['negara']} negara", f"{jumlah_id} pemutusan", delta_color="off")
        else:
            st.metric("Posisi Indonesia", "tidak ada", "0 pemutusan dalam filter ini", delta_color="off")
        per_wil = analisis.per_kategori(df, "wilayah")
        fig = px.pie(per_wil, names="wilayah", values="jumlah", hole=0.55, title="Pembagian per wilayah",
                     color_discrete_sequence=["#a78bfa", "#60a5fa", "#f87171", "#34d399", "#facc15", "#fb923c", "#9ca3af"])
        fig.update_traces(textinfo="percent+label", textfont_size=11)
        fig.update_layout(showlegend=False)
        st.plotly_chart(rapikan(fig, 380), use_container_width=True)

    if mode_belajar:
        with st.expander("🎓 Di balik peta ini"):
            st.markdown(
                """
**APA yang dihitung.** `analisis.per_negara(df)` mengelompokkan baris per negara, lalu menghitung jumlah baris
(= pemutusan), total `durasi_hari`, dan pemicu yang paling sering muncul (`value_counts().index[0]`).

**MENGAPA skala log.** India punya 900-an pemutusan, negara urutan ke-10 hanya 30-an. Pada skala linier semua
negara selain India berwarna sama gelapnya. Dengan `log10`, selisih 1 → 10 → 100 → 1.000 menjadi langkah yang sama.

```python
peta["log"] = np.log10(peta["jumlah"].clip(lower=1))      # 1 -> 0, 10 -> 1, 100 -> 2
px.choropleth(peta, locations="iso3", color="log", color_continuous_scale=SKALA_UNGU)
```

Plotly mengenali negara dari kode ISO-3 (`IDN`, `IND`). Pemetaan nama Access Now → ISO-3 ada di `src/negara.py`.
"""
            )

# ----------------------------------------------------------------------------
# TAB 2: TREN & PEMICU
# ----------------------------------------------------------------------------
with tab_tren:
    kiri, kanan = st.columns([3, 2])
    with kiri:
        pt = analisis.per_tahun(df, "pemicu")
        pt = pt[pt["tahun"] >= TAHUN_MIN]
        fig = px.bar(pt, x="tahun", y="jumlah", color="pemicu", color_discrete_map=WARNA_PEMICU,
                     category_orders={"pemicu": URUTAN_PEMICU},
                     title="Pemutusan per tahun menurut pemicu", labels={"jumlah": "Pemutusan", "tahun": "", "pemicu": ""})
        aktif = analisis.aktif_per_tahun(df, tahun_awal, tahun_akhir)
        fig.add_trace(go.Scatter(x=aktif["tahun"], y=aktif["aktif"], mode="lines+markers", name="Aktif pada tahun itu (cara Access Now)",
                                 line=dict(color="#e8e8f0", width=2, dash="dot"), marker=dict(size=7)))
        fig.update_layout(barmode="stack", xaxis=dict(dtick=1))
        st.plotly_chart(rapikan(fig, 480, legenda_bawah=True), use_container_width=True)
        st.caption("Batang: pemutusan menurut tahun ia dimulai. Garis putus-putus: jumlah yang tercatat aktif pada tahun itu "
                   "(pemutusan lintas tahun dihitung berulang), yakni angka yang dipakai laporan tahunan Access Now.")
    with kanan:
        pk = analisis.per_kategori(df, "pemicu")
        fig = px.bar(pk.iloc[::-1], x="jumlah", y="pemicu", orientation="h", color="pemicu",
                     color_discrete_map=WARNA_PEMICU, text="persen", title="Pemicu, seluruh rentang",
                     labels={"jumlah": "Pemutusan", "pemicu": ""})
        fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False)
        fig.update_layout(showlegend=False)
        st.plotly_chart(rapikan(fig, 440), use_container_width=True)

    st.subheader("Pemicu sebenarnya vs alasan resmi")
    pasangan = analisis.pemicu_vs_alasan(df, minimal=max(3, len(df) // 150))
    if len(pasangan) >= 2:
        kiri_label = [p for p in URUTAN_PEMICU if p in set(pasangan["pemicu"])]
        kanan_label = list(pasangan.groupby("alasan_pemerintah")["jumlah"].sum().sort_values(ascending=False).index)
        label = kiri_label + kanan_label
        idx = {n: i for i, n in enumerate(label)}
        warna_node = [WARNA_PEMICU.get(n, "#9ca3af") for n in kiri_label] + ["#4b5563"] * len(kanan_label)
        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(label=label, color=warna_node, pad=12, thickness=16, line=dict(width=0)),
            link=dict(
                source=[idx[p] for p in pasangan["pemicu"]],
                target=[idx[a] for a in pasangan["alasan_pemerintah"]],
                value=pasangan["jumlah"],
                color=[WARNA_PEMICU.get(p, "#9ca3af") + "66" for p in pasangan["pemicu"]],  # hex + alpha 40%
            ),
        ))
        fig.update_layout(title="Kiri: apa yang terjadi di lapangan · Kanan: apa kata pemerintah", font=dict(size=12))
        st.plotly_chart(rapikan(fig, 520), use_container_width=True)
        st.caption("Pasangan dengan jumlah sangat kecil disembunyikan agar diagram terbaca. 'Tidak disebutkan' berarti "
                   "tidak ada pernyataan resmi yang ditemukan Access Now.")
    else:
        st.info("Terlalu sedikit data untuk diagram alir pada filter ini.")

    kiri, kanan = st.columns(2)
    with kiri:
        sd = analisis.sebaran_durasi(df)
        fig = px.bar(sd, x="kategori", y="jumlah", text="jumlah", title="Berapa lama internet padam?",
                     labels={"kategori": "", "jumlah": "Pemutusan"}, color_discrete_sequence=[UNGU])
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(rapikan(fig, 380), use_container_width=True)
        st.caption(f"Median {ring['median_hari']:.0f} hari. Durasi tidak diketahui untuk pemutusan tanpa tanggal selesai yang terdokumentasi.")
    with kanan:
        pp = analisis.platform_per_tahun(df)
        pp = pp[pp["tahun"] >= TAHUN_MIN]
        fig = px.line(pp, x="tahun", y="jumlah", color="platform", markers=True,
                      title="Platform yang ikut diblokir, per tahun", labels={"jumlah": "Pemutusan yang menyebut platform", "tahun": "", "platform": ""})
        fig.update_layout(xaxis=dict(dtick=1))
        st.plotly_chart(rapikan(fig, 400, legenda_bawah=True), use_container_width=True)

    st.subheader("Linimasa satu negara")
    daftar_negara = list(analisis.per_negara(df)["negara"])
    bawaan = daftar_negara.index("Myanmar") if "Myanmar" in daftar_negara else 0
    negara_gantt = st.selectbox("Negara", daftar_negara, index=bawaan)
    gantt = analisis.linimasa(df[df["negara"] == negara_gantt], maks=80)
    fig = px.timeline(gantt, x_start="mulai", x_end="akhir_gantt", y="label", color="pemicu",
                      color_discrete_map=WARNA_PEMICU, hover_data={"durasi_hari": True, "jaringan": True, "platform": True, "label": False},
                      title=f"{len(gantt)} pemutusan terbaru di {negara_gantt}", labels={"label": "", "pemicu": ""})
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    st.plotly_chart(rapikan(fig, max(320, 22 * len(gantt) + 120)), use_container_width=True)

    if mode_belajar:
        with st.expander("🎓 Membaca grafik tren dan Sankey"):
            st.markdown(
                """
**Dua cara menghitung "berapa pemutusan tahun ini".** Batang memakai tahun mulai (`df["tahun"]`). Garis putus-putus
memakai `tahun_laporan_awal..tahun_laporan_akhir`: pemutusan yang masih berjalan dihitung lagi tahun berikutnya.
Itulah sebabnya angka Access Now (313 untuk 2025) lebih tinggi daripada jumlah pemutusan yang *dimulai* pada 2025.

```python
aktif = (df["tahun_laporan_awal"] <= th) & (df["tahun_laporan_akhir"] >= th)
```

**Sankey.** `analisis.pemicu_vs_alasan` menghitung pasangan (pemicu, alasan_pemerintah). Node kiri = pemicu, node kanan
= alasan resmi, lebar pita = jumlah pemutusan. Pita dari "Unjuk rasa" ke "Hoaks / ujaran kebencian" adalah pola
klasik: yang terjadi adalah demonstrasi, yang disebut pemerintah adalah hoaks.

**Gantt dengan `px.timeline`.** Butuh kolom mulai dan selesai. Pemutusan tanpa tanggal selesai diberi lebar dari
`durasi_hari` (atau 1 hari) agar tetap terlihat, lihat `analisis.linimasa`.
"""
            )

# ----------------------------------------------------------------------------
# TAB 3: INDONESIA
# ----------------------------------------------------------------------------
with tab_indo:
    prof = analisis.profil_negara(df_semua, "Indonesia")
    tabel_id = prof["tabel"]
    r = prof["ringkasan"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pemutusan tercatat", r["jumlah"], help="Seluruh rentang data, tidak terpengaruh filter sidebar.")
    c2.metric("Masih berlangsung", r["berlangsung"], help="Pemblokiran platform yang belum dicabut menurut catatan terakhir.")
    c3.metric("Pemicu unjuk rasa", int((tabel_id["pemicu"] == "Unjuk rasa").sum()))
    c4.metric("Hari gelap (diketahui)", ribuan(r["hari"]))

    gantt_id = analisis.linimasa(tabel_id, maks=50).sort_values("mulai")
    fig = px.timeline(gantt_id, x_start="mulai", x_end="akhir_gantt", y="label", color="pemicu",
                      color_discrete_map=WARNA_PEMICU, hover_data={"durasi_hari": True, "jaringan": True, "platform": True, "label": False},
                      title="Linimasa pemutusan dan pemblokiran di Indonesia (catatan Access Now)", labels={"label": "", "pemicu": ""})
    # APA: tambah penanda di tanggal mulai. MENGAPA: pemutusan 4 hari pada sumbu 10 tahun lebarnya hanya 1 piksel.
    for pemicu_i, grup in gantt_id.groupby("pemicu"):
        fig.add_trace(go.Scatter(
            x=grup["mulai"], y=grup["label"], mode="markers", name=pemicu_i, showlegend=False,
            marker=dict(symbol="diamond", size=13, color=WARNA_PEMICU.get(pemicu_i, "#9ca3af"), line=dict(width=1, color="#0b0d14")),
            customdata=np.stack([grup["durasi_hari"].fillna(0), grup["jaringan"]], axis=1),
            hovertemplate="%{y}<br>mulai %{x|%d %b %Y}<br>%{customdata[0]:.0f} hari · %{customdata[1]}<extra></extra>",
        ))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
    fig.update_xaxes(range=["2016-01-01", f"{TAHUN_MAX + 1}-06-30"])
    st.plotly_chart(rapikan(fig, 420), use_container_width=True)
    st.caption("Pemblokiran Grindr dkk. (2016) dan Telegram (2018) berstatus 'berlangsung' pada catatan terakhir, "
               "sehingga batangnya memanjang sampai akhir data. Pemutusan jaringan penuh hanya terjadi di Papua.")

    st.subheader("Momen demi momen")
    for _, baris in tabel_id.sort_values("mulai", ascending=False).iterrows():
        judul = f"{tanggal_id(baris['mulai'])} · {baris['daerah'] or 'Nasional'} · {baris['pemicu']}"
        with st.expander(judul):
            a, b = st.columns([2, 3])
            with a:
                st.markdown(
                    f"- **Jenis:** {baris['jenis']} ({baris['cakupan_layanan'].lower()})\n"
                    f"- **Jaringan:** {baris['jaringan']}\n"
                    f"- **Selesai:** {tanggal_id(baris['selesai'])} · "
                    f"{'' if pd.isna(baris['durasi_hari']) else str(int(baris['durasi_hari'])) + ' hari'} {baris['status'].lower()}\n"
                    f"- **Diperintahkan oleh:** {baris['diperintahkan_oleh']}\n"
                    f"- **Alasan resmi:** {baris['alasan_pemerintah']}\n"
                    f"- **Kekerasan di lapangan:** {baris['kekerasan']}\n"
                    f"- **Platform:** {baris['platform'] or '–'}"
                )
            with b:
                if baris["keterangan"]:
                    st.write(baris["keterangan"])
                else:
                    st.write("Access Now tidak menyertakan ringkasan peristiwa untuk baris ini.")
                if baris["sumber_url"]:
                    st.markdown(f"[Sumber]({baris['sumber_url']})")

    st.subheader("Sinyal konektivitas Indonesia 7 hari terakhir (IODA)")
    sinyal, asal_sinyal = ioda_aman("sinyal_indonesia", hari=7)
    sinyal = sinyal[sinyal["sumber"].isin(["bgp", "ping-slash24", "merit-nt", "gtr"])] if not sinyal.empty else sinyal
    if sinyal.empty:
        st.info("Sinyal IODA tidak tersedia saat ini.")
    else:
        norm = ioda.normalisasi_sinyal(sinyal)
        norm["label"] = norm["sumber"].map(ioda.NAMA_SUMBER)
        fig = px.line(norm, x="waktu", y="relatif", color="sumber", color_discrete_map=WARNA_SINYAL,
                      title="Sinyal relatif terhadap median minggu ini (1,0 = normal)",
                      labels={"relatif": "Relatif", "waktu": "", "sumber": ""},
                      hover_data={"nilai": ":,.0f", "label": True, "sumber": False})
        fig.for_each_trace(lambda t: t.update(name=ioda.NAMA_SUMBER.get(t.name, t.name)))
        fig.add_hline(y=1.0, line_dash="dot", line_color="#6b7280")
        fig.update_yaxes(range=[0, max(1.3, float(norm["relatif"].max()) * 1.05 if norm["relatif"].notna().any() else 1.3)])
        st.plotly_chart(rapikan(fig, 360), use_container_width=True)
        waktu_akhir = norm["waktu"].max()
        st.caption(
            f"{'Data live IODA' if asal_sinyal == 'live' else 'Potret tersimpan'}, titik terakhir {tanggal_id(waktu_akhir)} "
            f"{pd.Timestamp(waktu_akhir).strftime('%H:%M')} UTC. Trafik Google turun tiap malam dan akhir pekan secara "
            "alami; yang perlu dicurigai adalah BGP atau ping yang anjlok bersamaan."
        )

    kej_id, asal_kej = ioda_aman("kejadian_indonesia", hari=365)
    st.subheader(f"Gangguan terdeteksi IODA di Indonesia, 12 bulan terakhir ({'live' if asal_kej == 'live' else 'potret'})")
    if kej_id.empty:
        st.write("Tidak ada kejadian terdeteksi pada tingkat negara.")
    else:
        tampil = kej_id.copy()
        tampil["mulai"] = tampil["mulai"].dt.tz_convert("Asia/Jakarta").dt.strftime("%d %b %Y %H:%M WIB")
        tampil["sumber"] = tampil["sumber"].map(ioda.NAMA_SUMBER).fillna(tampil["sumber"])
        st.dataframe(tampil[["mulai", "durasi_menit", "sumber", "skor"]].rename(
            columns={"mulai": "Mulai", "durasi_menit": "Durasi (menit)", "sumber": "Sinyal", "skor": "Skor IODA"}),
            use_container_width=True, hide_index=True, height=min(400, 38 * len(tampil) + 40))
        st.caption("Deteksi tingkat negara hanya menangkap gangguan besar. Pemutusan satu kabupaten di Papua biasanya terlalu kecil "
                   "untuk menggeser sinyal nasional Indonesia; itulah sebabnya catatan manusia (Access Now) tetap diperlukan.")

    if mode_belajar:
        with st.expander("🎓 Dua sumber yang saling melengkapi"):
            st.markdown(
                """
**Access Now mencatat, IODA mengukur.** Tabel atas berasal dari dokumentasi manusia: relawan dan jurnalis melaporkan,
Access Now memverifikasi. Grafik bawah berasal dari pengukuran otomatis tiap 5 menit tanpa ada orang yang menulis apa pun.

**Normalisasi.** Ketiga sinyal IODA punya satuan berbeda (blok /24, paket, permintaan). Supaya bisa digambar bersama,
setiap sinyal dibagi mediannya sendiri dalam seminggu:

```python
median = df.groupby("sumber")["nilai"].transform("median")
df["relatif"] = df["nilai"] / median         # 1,0 = normal, 0,4 = tinggal 40%
```

**Cadangan.** `ioda_aman()` mencoba API live dulu. Jika gagal, ia membaca potret CSV di `data/` yang diperbarui
skrip ETL. Pola *try live, fall back to snapshot* ini membuat aplikasi tidak pernah menampilkan halaman error.
"""
            )

# ----------------------------------------------------------------------------
# TAB 4: LIVE (IODA)
# ----------------------------------------------------------------------------
with tab_live:
    hari_live = st.radio("Jendela waktu", [7, 30], horizontal=True, format_func=lambda h: f"{h} hari terakhir")
    kolom_a, kolom_b = st.columns([5, 1])
    with kolom_b:
        if st.button("🔄 Refresh"):
            ioda_aman.clear()
    ringkasan_live, asal_r = ioda_aman("ringkasan", hari=hari_live)
    kejadian_live, asal_k = ioda_aman("kejadian_dunia", hari=hari_live, batas=500)
    with kolom_a:
        if asal_r == "live":
            st.success(f"Data live dari IODA, diambil {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M')} UTC (cache 1 jam).", icon="📡")
        else:
            st.warning("API IODA tidak terjangkau; menampilkan potret 30 hari yang disimpan bersama repositori.", icon="💾")

    if ringkasan_live.empty:
        st.info("Tidak ada data gangguan.")
    else:
        rl = ringkasan_live.copy()
        rl["nama"] = [nama_dari_iso2(k, n) for k, n in zip(rl["kode"], rl["nama_en"])]
        rl["log_skor"] = np.log10(rl["skor_total"].clip(lower=1))
        fig = px.scatter_geo(
            rl, locations="nama_en", locationmode="country names", size="jumlah_kejadian", color="log_skor",
            hover_name="nama", size_max=34, color_continuous_scale=["#4c1d95", "#a78bfa", "#fde68a", "#f87171"],
            hover_data={"nama_en": False, "log_skor": False, "jumlah_kejadian": True, "skor_total": ":,.0f"},
            labels={"jumlah_kejadian": "Kejadian", "skor_total": "Skor IODA"},
            title=f"Negara dengan gangguan konektivitas terdeteksi, {hari_live} hari terakhir (ukuran = jumlah kejadian, warna = skor)",
        )
        fig.update_layout(coloraxis_showscale=False)
        fig.update_traces(marker=dict(line=dict(width=0.5, color="#0b0d14"), opacity=0.85))
        st.plotly_chart(gaya_peta_dunia(rapikan(fig, 520)), use_container_width=True)
        st.caption("Skor IODA = seberapa jauh dan seberapa lama sinyal menyimpang dari normal; nilainya tidak punya satuan dan "
                   "hanya untuk membandingkan. Pulau kecil sering muncul karena satu kabel putus sudah cukup menggelapkan seluruh sinyal.")

        kiri, kanan = st.columns([2, 3])
        with kiri:
            top_live = rl.sort_values("skor_total", ascending=False).head(15)
            st.dataframe(top_live[["nama", "jumlah_kejadian", "skor_total"]].rename(
                columns={"nama": "Negara", "jumlah_kejadian": "Kejadian", "skor_total": "Skor"}),
                use_container_width=True, hide_index=True, column_config={"Skor": st.column_config.NumberColumn(format="%.0f")})
        with kanan:
            if not kejadian_live.empty:
                kl = kejadian_live.copy()
                kl["nama"] = kl["nama_en"]
                kl["sumber_label"] = kl["sumber"].map(ioda.NAMA_SUMBER).fillna(kl["sumber"])
                fig = px.scatter(kl, x="mulai", y="durasi_menit", color="sumber", color_discrete_map=WARNA_SINYAL,
                                 size=np.log10(kl["skor"].clip(lower=1)) + 1, hover_name="nama",
                                 hover_data={"durasi_menit": True, "skor": ":,.0f", "sumber_label": True, "sumber": False},
                                 log_y=True, title=f"Setiap kejadian: kapan dan berapa lama ({len(kl)} kejadian)",
                                 labels={"mulai": "", "durasi_menit": "Durasi (menit, log)", "sumber": ""})
                fig.for_each_trace(lambda t: t.update(name=ioda.NAMA_SUMBER.get(t.name, t.name)))
                st.plotly_chart(rapikan(fig, 400), use_container_width=True)

    if mode_belajar:
        with st.expander("🎓 Bagaimana IODA tahu internet suatu negara mati?"):
            st.markdown(
                """
IODA tidak bertanya pada siapa pun. Ia membandingkan tiga pengukuran independen dengan pola normalnya:

| Sinyal | Yang diukur | Analogi |
|---|---|---|
| BGP | blok alamat IP yang masih diumumkan router dunia | papan nama toko dicopot dari peta |
| Ping aktif | blok alamat yang membalas ping dari luar | mengetuk pintu, tidak ada yang menjawab |
| Teleskop jaringan | paket nyasar yang biasanya terus mengalir | kota yang tiba-tiba hening |

Jika sinyal turun jauh di bawah ambang (berdasarkan median), IODA mencatat *event* dengan skor = besar penyimpangan ×
durasi. Endpoint yang dipakai: `/outages/summary` (per negara) dan `/outages/events` (per kejadian), tanpa API key.

```python
resp = requests.get(f"{URL_DASAR}/outages/summary", params={"entityType": "country", "from": dari, "until": sampai})
df = ioda.urai_ringkasan(resp.json()["data"])
```

Keterbatasan: deteksi tingkat negara hanya menangkap gangguan besar; pelambatan (throttling) dan pemblokiran satu
aplikasi tidak terlihat sama sekali karena rute dan ping tetap normal.
"""
            )

# ----------------------------------------------------------------------------
# TAB 5: SHUTDOWN VS KONFLIK
# ----------------------------------------------------------------------------
with tab_konflik:
    gab = analisis.gabung_konflik(df, konflik_semua, max(tahun_awal, 2016), min(tahun_akhir, 2025))
    kor = analisis.korelasi_konflik(gab)
    c1, c2, c3 = st.columns(3)
    c1.metric("Negara-tahun dengan konflik mematikan", kor["negara_tahun_konflik"], help="≥ 25 korban konflik bersenjata (ambang UCDP) dalam satu tahun.")
    c2.metric("… yang juga memutus internet", f"{kor['persen']:.0f}%", f"{kor['dengan_shutdown']} negara-tahun", delta_color="off")
    c3.metric("Pemutusan yang terjadi di negara berkonflik", f"{kor['shutdown_di_negara_konflik']:.0f}%",
              help="Porsi semua pemutusan dalam filter yang terjadi pada negara-tahun dengan ≥ 25 korban konflik.")

    titik = gab[(gab["shutdown"] > 0) | (gab["korban"] >= 25)].copy()
    titik["korban_plot"] = titik["korban"].clip(lower=1)
    titik["shutdown_plot"] = titik["shutdown"].clip(lower=0.5)
    titik["sorot"] = np.where(titik["negara"] == "Indonesia", "Indonesia", "Negara lain")
    fig = px.scatter(titik, x="korban_plot", y="shutdown_plot", color="sorot", hover_name="negara",
                     hover_data={"tahun": True, "korban": True, "shutdown": True, "korban_plot": False, "shutdown_plot": False, "sorot": False},
                     color_discrete_map={"Indonesia": "#f87171", "Negara lain": UNGU}, log_x=True, log_y=True, opacity=0.7,
                     title="Setiap titik = satu negara dalam satu tahun: korban konflik (UCDP) vs pemutusan internet (Access Now)",
                     labels={"korban_plot": "Korban konflik bersenjata (log)", "shutdown_plot": "Pemutusan internet (log)", "sorot": ""})
    fig.add_vline(x=25, line_dash="dot", line_color="#6b7280", annotation_text="ambang konflik UCDP (25)", annotation_position="top left")
    fig.update_traces(marker=dict(size=9))
    st.plotly_chart(rapikan(fig, 500), use_container_width=True)
    st.caption("Negara-tahun tanpa pemutusan digambar di 0,5 agar tetap terlihat pada sumbu log. Titik merah = Indonesia.")

    kiri, kanan = st.columns(2)
    with kiri:
        kuadran = titik.copy()
        kuadran["kelompok"] = np.select(
            [(kuadran["korban"] >= 25) & (kuadran["shutdown"] > 0), (kuadran["korban"] >= 25), (kuadran["shutdown"] > 0)],
            ["Konflik + pemutusan", "Konflik tanpa pemutusan", "Pemutusan tanpa konflik mematikan"], default="-",
        )
        kk = kuadran["kelompok"].value_counts().reset_index()
        kk.columns = ["kelompok", "jumlah"]
        fig = px.bar(kk, x="jumlah", y="kelompok", orientation="h", text="jumlah", title="Negara-tahun per kelompok",
                     color="kelompok", color_discrete_map={"Konflik + pemutusan": "#f87171", "Konflik tanpa pemutusan": "#fb923c",
                                                            "Pemutusan tanpa konflik mematikan": UNGU},
                     labels={"jumlah": "Negara-tahun", "kelompok": ""})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(showlegend=False)
        st.plotly_chart(rapikan(fig, 320), use_container_width=True)
    with kanan:
        tanpa = titik[(titik["shutdown"] >= 3) & (titik["korban"] < 25)].sort_values("shutdown", ascending=False).head(10)
        st.markdown("**Rajin memutus internet tanpa perang di dalam negeri** (≥ 3 pemutusan, < 25 korban konflik):")
        st.dataframe(tanpa[["negara", "tahun", "shutdown", "korban"]].rename(
            columns={"negara": "Negara", "tahun": "Tahun", "shutdown": "Pemutusan", "korban": "Korban konflik"}),
            use_container_width=True, hide_index=True)

    if mode_belajar:
        with st.expander("🎓 Menggabungkan dua dataset yang tidak saling kenal"):
            st.markdown(
                """
Access Now dan UCDP tidak pernah berkoordinasi: nama negaranya berbeda ("Iran (Islamic Republic of)" vs "Iran"),
satuannya berbeda (pemutusan vs korban jiwa). Kunci yang menyatukan keduanya adalah **kode ISO-3 + tahun**.

```python
sd = df_shutdown.groupby(["iso3", "negara", "tahun"]).size().reset_index(name="shutdown")
kf = df_konflik[["iso3", "negara", "tahun", "korban", "kejadian"]]
gabung = sd.merge(kf, on=["iso3", "tahun"], how="outer")   # outer: negara yang hanya ada di satu sisi tetap masuk
```

`how="outer"` penting: dengan `inner` kita hanya melihat negara yang berdarah *dan* memutus internet, lalu salah
menyimpulkan bahwa keduanya selalu bersama. Kelompok "konflik tanpa pemutusan" (misalnya Meksiko, Brasil) membuktikan
sebaliknya. Korelasi bukan sebab-akibat: keduanya bisa sama-sama akibat dari pemerintahan yang represif.
"""
            )

# ----------------------------------------------------------------------------
# TAB 6: DATA & SUMBER
# ----------------------------------------------------------------------------
with tab_data:
    st.subheader(f"Pemutusan sesuai filter ({ribuan(len(df))} baris)")
    kolom_tampil = ["tahun", "mulai", "selesai", "durasi_hari", "negara", "daerah", "jenis", "jaringan", "cakupan_layanan",
                    "pemicu", "alasan_pemerintah", "diperintahkan_oleh", "kekerasan", "platform", "status", "keterangan", "sumber_url"]
    tampil = df[kolom_tampil].sort_values("mulai", ascending=False)
    st.dataframe(
        tampil, use_container_width=True, hide_index=True, height=420,
        column_config={
            "mulai": st.column_config.DateColumn("Mulai", format="DD MMM YYYY"),
            "selesai": st.column_config.DateColumn("Selesai", format="DD MMM YYYY"),
            "sumber_url": st.column_config.LinkColumn("Sumber", display_text="buka"),
            "durasi_hari": st.column_config.NumberColumn("Hari", format="%.0f"),
        },
    )
    st.download_button("⬇️ Download CSV (sesuai filter)", df.to_csv(index=False).encode("utf-8"),
                       f"shutdown_{tahun_awal}_{tahun_akhir}.csv", "text/csv")

    st.subheader("Sumber")
    st.markdown(
        """
| Sumber | Isi | Lisensi / akses |
|---|---|---|
| [Access Now #KeepItOn STOP](https://www.accessnow.org/keepiton-data/) | Pemutusan internet terdokumentasi 2016–2025 (spreadsheet publik, 45 kolom) | Publik, diperbarui berkala; kutip Access Now |
| [IODA, Georgia Tech](https://ioda.inetintel.cc.gatech.edu/) | Deteksi gangguan konektivitas otomatis (BGP, ping aktif, teleskop jaringan, trafik Google) | API publik tanpa key |
| [UCDP GED](https://ucdp.uu.se/downloads/) via [global-conflict-tracker](https://github.com/Avalon2222/global-conflict-tracker) | Korban konflik bersenjata per negara-tahun | CC BY 4.0 |

Detail kolom, aturan penggabungan duplikat, dan terjemahan kategori ada di [`data/SUMBER_DATA.md`](https://github.com/Avalon2222/blackout-watch/blob/main/data/SUMBER_DATA.md).
"""
    )
    st.subheader("Keterbatasan yang perlu diingat")
    st.markdown(
        """
1. **Hanya yang terdokumentasi.** Pemutusan yang tidak dilaporkan siapa pun tidak ada di data. Negara tertutup
   (Korea Utara, Turkmenistan, Eritrea) hampir pasti kurang terwakili.
2. **India mendominasi** (sekitar separuh baris) karena pemutusan tingkat distrik di Jammu & Kashmir dan Manipur
   dicatat satu per satu. Itu memang kebijakan India, tetapi juga hasil dari dokumentasi yang lebih rapi.
3. **Durasi tidak selalu diketahui.** Sekitar seperempat baris tidak punya tanggal selesai; total "hari gelap" adalah
   batas bawah.
4. **Satu pemutusan bisa muncul di beberapa lembar tahunan** Access Now. Di sini digabung menjadi satu baris dengan rentang
   tahun laporan; filter sidebar memilih cara menghitungnya.
5. **IODA hanya melihat gangguan besar.** Pelambatan dan pemblokiran aplikasi tidak menggeser sinyal BGP/ping.
6. **Korelasi dengan konflik bukan sebab-akibat.** Lihat catatan di tab Shutdown vs konflik.
"""
    )

# ----------------------------------------------------------------------------
# TAB 7: CARA KERJA
# ----------------------------------------------------------------------------
with tab_cara:
    st.markdown(
        """
### Alur data

```
Google Sheets (STOP, 10 lembar tahunan)   IODA API (/outages, /signals)   UCDP via global-conflict-tracker
            │                                         │                                │
            ▼                                         ▼                                ▼
   src/siapkan_data.py ── gabungkan duplikat, terjemahkan, ISO-3 ──► data/shutdown_dunia.csv
                       ── potret 30 hari / 7 hari ─────────────────► data/ioda_*.csv
                       ── agregasi negara-tahun ───────────────────► data/korban_konflik_negara_tahun.csv
            │
            ▼
   src/muat_data.py ──► src/analisis.py (pandas murni, diuji) ──► app.py (Streamlit + Plotly)
                        src/ioda.py (live, cache 1 jam, cadangan potret)
```

### Istilah

- **Pemutusan (shutdown):** akses internet sengaja dihentikan oleh otoritas untuk suatu wilayah atau layanan.
- **Pelambatan (throttling):** kecepatan dibuat sangat rendah hingga praktis tidak terpakai, tanpa diputus resmi.
- **Pemblokiran platform (service-based):** jaringan hidup, tetapi aplikasi tertentu (WhatsApp, TikTok) tidak bisa diakses.
- **Pemicu (actual cause):** peristiwa di lapangan yang, menurut penelusuran Access Now, melatarbelakangi pemutusan.
- **Alasan resmi (government justification):** pernyataan pemerintah, bila ada. Sering berbeda dari pemicu.
- **Skor IODA:** besarnya penyimpangan sinyal dari normal dikalikan durasi; tanpa satuan, hanya untuk membandingkan.

### Fungsi inti (`src/analisis.py`)

| Fungsi | Yang dihitung |
|---|---|
| `filter_data(df, awal, akhir, pemicu, wilayah, jenis, ...)` | Menyaring sesuai sidebar; dua dasar tahun (mulai / aktif) |
| `ringkasan(df)` | KPI: jumlah, negara, hari gelap, persen terkait kerusuhan, negara teratas |
| `per_tahun(df, pecah)` dan `aktif_per_tahun(df)` | Tren per tahun; versi "aktif" meniru cara hitung laporan Access Now |
| `per_negara(df)`, `top_negara`, `peringkat_negara` | Agregat untuk choropleth dan peringkat |
| `pemicu_vs_alasan(df)` | Pasangan pemicu → alasan resmi untuk Sankey |
| `platform_per_tahun(df)`, `sebaran_durasi(df)` | Platform yang diblokir; kelompok durasi |
| `linimasa(df)` | Baris Gantt dengan tanggal selesai yang diisi bila kosong |
| `gabung_konflik(...)`, `korelasi_konflik(...)` | Silang dengan korban konflik UCDP per negara-tahun |

Fungsi di `src/ioda.py` yang berawalan `urai_` mengubah JSON IODA menjadi DataFrame dan diuji tanpa jaringan.
"""
    )
    if mode_belajar:
        with st.expander("🎓 Mengapa data diolah dulu, bukan dibaca langsung dari spreadsheet?"):
            st.markdown(
                """
1. **Kecepatan dan ketahanan.** Mengunduh xlsx 2 MB dari Google tiap kali halaman dibuka berarti aplikasi mati saat Google
   lambat. CSV di repositori dibaca dalam milidetik.
2. **Duplikat.** Lembar tahunan Access Now memuat ulang pemutusan yang masih berjalan. Tanpa penggabungan, pemblokiran
   Grindr di Indonesia (2016, masih berlangsung) akan dihitung sembilan kali.
3. **Bahasa dan kode.** Kategori Inggris diterjemahkan sekali, negara dipetakan ke ISO-3 sekali, lalu semua grafik memakai
   hasil yang sama.

Semua aturan itu adalah fungsi murni di `src/siapkan_data.py` (`gabungkan_duplikat`, `rapikan`, `hitung_durasi`) dan
punya tesnya di `tests/`.
"""
            )
