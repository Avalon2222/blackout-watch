"""
muat_data.py - Membaca CSV di folder data/ dan memastikan kolom pentingnya ada.

Aplikasi hanya memanggil fungsi di sini, sehingga jika nama file atau skema berubah cukup satu tempat yang disesuaikan.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DIR_DATA = Path(__file__).resolve().parent.parent / "data"
KOLOM_WAJIB = [
    "id", "negara", "iso3", "wilayah", "tahun", "mulai", "selesai", "durasi_hari", "status",
    "tahun_laporan_awal", "tahun_laporan_akhir", "cakupan_wilayah", "daerah", "jenis", "jaringan",
    "cakupan_layanan", "pemicu", "alasan_pemerintah", "diperintahkan_oleh", "pemilu", "kekerasan",
    "pelanggaran_ham", "platform", "keterangan", "sumber_url",
]


def muat_shutdown(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or DIR_DATA / "shutdown_dunia.csv")
    hilang = [k for k in KOLOM_WAJIB if k not in df.columns]
    if hilang:
        raise ValueError(f"Kolom hilang di shutdown_dunia.csv: {hilang}")
    df["mulai"] = pd.to_datetime(df["mulai"], errors="coerce")
    df["selesai"] = pd.to_datetime(df["selesai"], errors="coerce")
    df["tahun"] = df["tahun"].astype(int)
    for kolom in ["daerah", "keterangan", "sumber_url", "platform"]:
        df[kolom] = df[kolom].fillna("").astype(str)
    return df


def muat_konflik(path: Path | None = None) -> pd.DataFrame:
    """Korban konflik bersenjata per negara-tahun (UCDP, agregasi dari proyek global-conflict-tracker)."""
    df = pd.read_csv(path or DIR_DATA / "korban_konflik_negara_tahun.csv")
    return df


def muat_potret_ioda(nama: str) -> pd.DataFrame:
    """Potret IODA yang disimpan skrip ETL; dipakai jika API IODA tidak terjangkau."""
    path = DIR_DATA / f"ioda_{nama}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for kolom in ["mulai", "selesai", "waktu"]:
        if kolom in df.columns:
            df[kolom] = pd.to_datetime(df[kolom], utc=True, errors="coerce")
    return df
