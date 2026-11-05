"""
analisis.py - Fungsi analisis murni (pandas, tanpa Streamlit) untuk dataset pemutusan internet.

Semua fungsi menerima DataFrame hasil `muat_data.muat_shutdown()` dan mengembalikan DataFrame/dict baru,
tanpa mengubah masukan. Karena tidak menyentuh Streamlit, semuanya dapat diuji dengan pytest (lihat tests/).
"""

from __future__ import annotations

import pandas as pd

URUTAN_PEMICU = [
    "Unjuk rasa", "Konflik bersenjata", "Kekerasan komunal", "Instabilitas politik", "Pemilu",
    "Kontrol informasi", "Ujian sekolah", "Hari besar/peringatan", "Kunjungan pejabat", "Lainnya", "Tidak diketahui",
]
PEMICU_KERUSUHAN = ["Unjuk rasa", "Konflik bersenjata", "Kekerasan komunal", "Instabilitas politik", "Pemilu"]


def filter_data(
    df: pd.DataFrame,
    tahun_awal: int,
    tahun_akhir: int,
    pemicu: list[str] | None = None,
    wilayah: list[str] | None = None,
    jenis: list[str] | None = None,
    hanya_seluruh_jaringan: bool = False,
    dasar_tahun: str = "mulai",
) -> pd.DataFrame:
    """Saring menurut rentang tahun, pemicu, wilayah, jenis.

    dasar_tahun="mulai"  : pemutusan dihitung pada tahun ia dimulai (kolom `tahun`).
    dasar_tahun="aktif"  : pemutusan dihitung jika ia tercatat aktif dalam rentang (laporan tahunan Access Now),
                           yakni rentang tahun_laporan_awal..tahun_laporan_akhir bersinggungan dengan rentang filter.
    """
    if dasar_tahun == "aktif":
        topeng = (df["tahun_laporan_awal"] <= tahun_akhir) & (df["tahun_laporan_akhir"] >= tahun_awal)
    else:
        topeng = df["tahun"].between(tahun_awal, tahun_akhir)
    if pemicu is not None:
        topeng &= df["pemicu"].isin(pemicu)
    if wilayah is not None:
        topeng &= df["wilayah"].isin(wilayah)
    if jenis is not None:
        topeng &= df["jenis"].isin(jenis)
    if hanya_seluruh_jaringan:
        topeng &= df["cakupan_layanan"] != "Platform tertentu"
    return df[topeng].copy()


def ringkasan(df: pd.DataFrame) -> dict:
    """Angka-angka utama untuk baris KPI."""
    if df.empty:
        return {
            "jumlah": 0, "negara": 0, "hari": 0.0, "median_hari": 0.0, "persen_kekerasan": 0.0,
            "persen_kerusuhan": 0.0, "negara_teratas": "-", "jumlah_teratas": 0, "berlangsung": 0,
        }
    per_negara = df.groupby("negara").size().sort_values(ascending=False)
    kekerasan_diketahui = df[df["kekerasan"].isin(["Ya", "Tidak"])]
    return {
        "jumlah": int(len(df)),
        "negara": int(df["negara"].nunique()),
        "hari": float(df["durasi_hari"].fillna(0).sum()),
        "median_hari": float(df["durasi_hari"].median()) if df["durasi_hari"].notna().any() else 0.0,
        "persen_kekerasan": float((kekerasan_diketahui["kekerasan"] == "Ya").mean() * 100) if len(kekerasan_diketahui) else 0.0,
        "persen_kerusuhan": float(df["pemicu"].isin(PEMICU_KERUSUHAN).mean() * 100),
        "negara_teratas": str(per_negara.index[0]),
        "jumlah_teratas": int(per_negara.iloc[0]),
        "berlangsung": int((df["status"] == "Berlangsung").sum()),
    }


def per_tahun(df: pd.DataFrame, pecah: str | None = "pemicu") -> pd.DataFrame:
    """Jumlah pemutusan per tahun mulai, opsional dipecah per kolom kategori (pemicu/jenis/wilayah)."""
    if pecah:
        hasil = df.groupby(["tahun", pecah]).size().reset_index(name="jumlah")
    else:
        hasil = df.groupby("tahun").size().reset_index(name="jumlah")
    return hasil.sort_values("tahun").reset_index(drop=True)


def aktif_per_tahun(df: pd.DataFrame, tahun_awal: int = 2016, tahun_akhir: int = 2025) -> pd.DataFrame:
    """Jumlah pemutusan yang tercatat aktif pada tiap tahun (cara Access Now menghitung laporan tahunannya).

    Satu pemutusan yang berlangsung 2019-2021 dihitung di 2019, 2020, dan 2021.
    """
    baris = []
    for th in range(tahun_awal, tahun_akhir + 1):
        aktif = (df["tahun_laporan_awal"] <= th) & (df["tahun_laporan_akhir"] >= th)
        baris.append({"tahun": th, "aktif": int(aktif.sum()), "dimulai": int((df["tahun"] == th).sum())})
    return pd.DataFrame(baris)


def per_negara(df: pd.DataFrame) -> pd.DataFrame:
    """Agregat per negara untuk choropleth: jumlah, total hari, pemicu dominan, tahun pertama/terakhir."""
    if df.empty:
        return pd.DataFrame(columns=["negara", "iso3", "wilayah", "jumlah", "hari", "pemicu_utama", "tahun_awal", "tahun_akhir"])
    grup = df.groupby(["negara", "iso3", "wilayah"])
    hasil = grup.agg(
        jumlah=("id", "size"),
        hari=("durasi_hari", lambda s: float(s.fillna(0).sum())),
        tahun_awal=("tahun", "min"),
        tahun_akhir=("tahun", "max"),
    ).reset_index()
    utama = grup["pemicu"].agg(lambda s: s.value_counts().index[0]).reset_index(name="pemicu_utama")
    hasil = hasil.merge(utama, on=["negara", "iso3", "wilayah"])
    return hasil.sort_values("jumlah", ascending=False).reset_index(drop=True)


def top_negara(df: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    return per_negara(df).head(n)


def peringkat_negara(df: pd.DataFrame, negara: str = "Indonesia") -> tuple[int, int]:
    """(peringkat, jumlah) suatu negara menurut jumlah pemutusan; peringkat 0 jika tidak ada."""
    tabel = per_negara(df)
    if negara not in set(tabel["negara"]):
        return 0, 0
    posisi = tabel.index[tabel["negara"] == negara][0]
    return int(posisi) + 1, int(tabel.loc[posisi, "jumlah"])


def per_kategori(df: pd.DataFrame, kolom: str) -> pd.DataFrame:
    """Jumlah dan persentase per nilai suatu kolom kategori (pemicu, alasan_pemerintah, jaringan, ...)."""
    hasil = df[kolom].value_counts().reset_index()
    hasil.columns = [kolom, "jumlah"]
    hasil["persen"] = (hasil["jumlah"] / max(len(df), 1) * 100).round(1)
    return hasil


def pemicu_vs_alasan(df: pd.DataFrame, minimal: int = 5) -> pd.DataFrame:
    """Pasangan (pemicu sebenarnya -> alasan resmi pemerintah) untuk diagram Sankey."""
    pasangan = df.groupby(["pemicu", "alasan_pemerintah"]).size().reset_index(name="jumlah")
    pasangan = pasangan[pasangan["jumlah"] >= minimal]
    return pasangan.sort_values("jumlah", ascending=False).reset_index(drop=True)


def platform_per_tahun(df: pd.DataFrame) -> pd.DataFrame:
    """Berapa kali tiap platform besar ikut diblokir per tahun (satu pemutusan bisa memblokir beberapa platform)."""
    nama = ["Facebook", "X/Twitter", "WhatsApp", "Instagram", "Telegram", "TikTok", "YouTube", "Signal", "VPN"]
    baris = []
    for th, grup in df.groupby("tahun"):
        teks = grup["platform"].fillna("").str.lower()
        for p in nama:
            kunci = p.lower().replace("x/twitter", "twitter")
            baris.append({"tahun": th, "platform": p, "jumlah": int(teks.str.contains(kunci, regex=False).sum())})
    return pd.DataFrame(baris)


def kategori_durasi(hari: float) -> str:
    """Kelompok durasi agar histogram mudah dibaca."""
    if pd.isna(hari):
        return "Tidak diketahui"
    if hari <= 1:
        return "≤ 1 hari"
    if hari <= 7:
        return "2–7 hari"
    if hari <= 30:
        return "8–30 hari"
    if hari <= 365:
        return "1–12 bulan"
    return "> 1 tahun"


URUTAN_DURASI = ["≤ 1 hari", "2–7 hari", "8–30 hari", "1–12 bulan", "> 1 tahun", "Tidak diketahui"]


def sebaran_durasi(df: pd.DataFrame) -> pd.DataFrame:
    kat = df["durasi_hari"].map(kategori_durasi)
    hasil = kat.value_counts().reindex(URUTAN_DURASI, fill_value=0).reset_index()
    hasil.columns = ["kategori", "jumlah"]
    return hasil


def linimasa(df: pd.DataFrame, maks: int = 60) -> pd.DataFrame:
    """Baris untuk grafik Gantt: pemutusan tanpa tanggal selesai diberi selesai = mulai + durasi atau +1 hari."""
    kerja = df.copy()
    akhir = kerja["selesai"]
    dari_durasi = kerja["mulai"] + pd.to_timedelta(kerja["durasi_hari"].fillna(1).clip(lower=1) - 1, unit="D")
    # Pemutusan yang masih berlangsung tanpa tanggal selesai: bar ditarik sampai akhir tahun laporan terakhirnya
    masih = pd.to_datetime(kerja["tahun_laporan_akhir"].astype(str) + "-12-31")
    dari_durasi = dari_durasi.where(kerja["status"] != "Berlangsung", masih)
    kerja["akhir_gantt"] = akhir.where(akhir.notna(), dari_durasi)
    kerja["akhir_gantt"] = kerja["akhir_gantt"] + pd.Timedelta(days=1)  # bar minimal selebar 1 hari
    kerja["label"] = kerja["negara"] + " · " + kerja["daerah"].str.slice(0, 40).replace("", "nasional")
    kerja = kerja.sort_values("mulai", ascending=False).head(maks)
    return kerja


def profil_negara(df: pd.DataFrame, negara: str) -> dict:
    """Semua yang dibutuhkan tab satu negara."""
    sub = df[df["negara"] == negara].sort_values("mulai")
    return {
        "tabel": sub,
        "ringkasan": ringkasan(sub),
        "per_tahun": per_tahun(sub, "pemicu"),
        "pemicu": per_kategori(sub, "pemicu"),
        "platform": per_kategori(sub[sub["platform"] != ""], "cakupan_layanan"),
    }


def gabung_konflik(df_shutdown: pd.DataFrame, df_konflik: pd.DataFrame, tahun_awal: int, tahun_akhir: int) -> pd.DataFrame:
    """Satu baris per negara-tahun: jumlah pemutusan vs korban konflik bersenjata (UCDP) pada tahun yang sama.

    Negara yang hanya ada di salah satu sumber tetap disertakan (nilai lain diisi 0) agar terlihat negara yang
    berdarah tetapi tidak memutus internet, dan sebaliknya.
    """
    sd = df_shutdown[df_shutdown["tahun"].between(tahun_awal, tahun_akhir)]
    sd = sd.groupby(["iso3", "negara", "tahun"]).size().reset_index(name="shutdown")
    kf = df_konflik[df_konflik["tahun"].between(tahun_awal, tahun_akhir)][["iso3", "negara", "tahun", "korban", "kejadian"]]
    gabung = sd.merge(kf, on=["iso3", "tahun"], how="outer", suffixes=("", "_ucdp"))
    gabung["negara"] = gabung["negara"].fillna(gabung["negara_ucdp"])
    gabung = gabung.drop(columns=["negara_ucdp"])
    for k in ["shutdown", "korban", "kejadian"]:
        gabung[k] = gabung[k].fillna(0).astype(int)
    return gabung.sort_values(["tahun", "shutdown"], ascending=[True, False]).reset_index(drop=True)


def korelasi_konflik(gabung: pd.DataFrame) -> dict:
    """Seberapa sering negara dengan konflik mematikan (≥ 25 korban/tahun) juga memutus internet pada tahun itu."""
    if gabung.empty:
        return {"negara_tahun_konflik": 0, "dengan_shutdown": 0, "persen": 0.0, "shutdown_di_negara_konflik": 0.0}
    konflik = gabung[gabung["korban"] >= 25]
    dengan = konflik[konflik["shutdown"] > 0]
    total_shutdown = gabung["shutdown"].sum()
    return {
        "negara_tahun_konflik": int(len(konflik)),
        "dengan_shutdown": int(len(dengan)),
        "persen": float(len(dengan) / len(konflik) * 100) if len(konflik) else 0.0,
        "shutdown_di_negara_konflik": float(konflik["shutdown"].sum() / total_shutdown * 100) if total_shutdown else 0.0,
    }
