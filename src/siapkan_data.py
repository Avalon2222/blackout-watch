"""
siapkan_data.py - ETL: unduh dataset #KeepItOn STOP (Access Now) + potret IODA, lalu simpan ke data/.

Jalankan:   python -m src.siapkan_data            # semua
            python -m src.siapkan_data --tanpa-ioda

Langkah untuk STOP:
  1. Unduh spreadsheet publik (ekspor xlsx dari Google Sheets) ke data/raw/.
  2. Baca sheet "Combined (2016-2025)" yang menggabungkan lembar tahunan.
  3. Bersihkan: lembar tahunan memuat ulang pemutusan yang masih berlangsung, sehingga satu pemutusan
     bisa muncul beberapa kali. Baris digabung menjadi satu pemutusan unik dengan rentang tahun laporan.
  4. Terjemahkan kategori ke bahasa Indonesia, petakan negara ke ISO-3, hitung durasi.
  5. Simpan data/shutdown_dunia.csv.

Potret IODA (ringkasan 30 hari, kejadian Indonesia 365 hari, sinyal Indonesia 7 hari) disimpan agar
aplikasi tetap tampil ketika API IODA tidak terjangkau.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src import ioda
from src.negara import info_negara

DIR_DATA = Path(__file__).resolve().parent.parent / "data"
DIR_RAW = DIR_DATA / "raw"
ID_SHEET = "1DvPAuHNLp5BXGb0nnZDGNoiIwEeu2ogdXEIDvT4Hyfk"
URL_STOP = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/export?format=xlsx"
NAMA_SHEET = "Combined (2016-2025)"
URL_KONFLIK = "https://raw.githubusercontent.com/Avalon2222/global-conflict-tracker/main/data/korban_negara_tahun.csv"

PEMICU = {
    "Protests": "Unjuk rasa",
    "Conflict": "Konflik bersenjata",
    "Political instability": "Instabilitas politik",
    "Information control": "Kontrol informasi",
    "Communal violence": "Kekerasan komunal",
    "Exam cheating": "Ujian sekolah",
    "Elections": "Pemilu",
    "Religious holiday/anniversary": "Hari besar/peringatan",
    "Visits by government officials": "Kunjungan pejabat",
    "Other": "Lainnya",
    "Unknown": "Tidak diketahui",
}
URUTAN_PEMICU = [
    "Unjuk rasa", "Konflik bersenjata", "Kekerasan komunal", "Instabilitas politik", "Pemilu",
    "Kontrol informasi", "Ujian sekolah", "Hari besar/peringatan", "Kunjungan pejabat", "Lainnya", "Tidak diketahui",
]
ALASAN = {
    "Fake news/ Hate speech/ Incendiary content/ Promoting violence": "Hoaks / ujaran kebencian",
    "Public safety/ Quell unrest/ Restore public order": "Keamanan / ketertiban umum",
    "National security/ Counter-terrorism": "Keamanan nasional / terorisme",
    "Precautionary measure": "Langkah pencegahan",
    "Sabotage/ Third-party Action": "Sabotase / pihak ketiga",
    "School exams": "Ujian sekolah",
    "School Exams": "Ujian sekolah",
    "Technical problems/ Infrastructure failure": "Gangguan teknis",
    "Illegal content": "Konten ilegal",
    "Other": "Lainnya",
    "Unknown": "Tidak disebutkan",
    "No": "Tidak disebutkan",
}
JENIS = {
    "Shutdown": "Pemutusan",
    "Throttle": "Pelambatan",
    "Shutdown, Throttle": "Pemutusan & pelambatan",
    "Unknown": "Tidak diketahui",
}
JARINGAN = {
    "Broadband, Mobile": "Broadband & seluler",
    "Mobile": "Seluler",
    "Broadband": "Broadband",
    "Unknown": "Tidak diketahui",
}
CAKUPAN_LAYANAN = {
    "Full network": "Seluruh jaringan",
    "Service-based": "Platform tertentu",
    "Full network, Service-based": "Jaringan + platform",
}
CAKUPAN_WILAYAH = {
    "It only affected one city, county, or village": "Satu kota/kabupaten",
    "It affected more than one city in the same state, province, or region": "Beberapa kota, satu provinsi",
    "It affected locations in more than one state, province, or region": "Lintas provinsi / nasional",
    "Not sure": "Tidak pasti",
}
PEMBERI_PERINTAH = {
    "Executive government": "Pemerintah pusat",
    "State government": "Pemerintah negara bagian/provinsi",
    "Local government": "Pemerintah daerah",
    "Military": "Militer",
    "Law enforcement": "Kepolisian",
    "Judiciary": "Pengadilan",
    "Non-government": "Non-pemerintah",
    "Unknown": "Tidak diketahui",
}
YA_TIDAK = {"Yes": "Ya", "No": "Tidak", "Unknown": "Tidak diketahui"}
KOLOM_PLATFORM = {
    "facebook_affected": "Facebook",
    "twitter_affected": "X/Twitter",
    "whatsapp_affected": "WhatsApp",
    "instagram_affected": "Instagram",
    "telegram_affected": "Telegram",
}
KUNCI_UNIK = [
    "country", "start_date", "area_name", "shutdown_type", "affected_network",
    "shutdown_extent", "actual_cause", "other_affected",
]
KOLOM_KELUARAN = [
    "id", "negara", "iso3", "wilayah", "negara_en", "tahun", "mulai", "selesai", "durasi_hari", "status",
    "tahun_laporan_awal", "tahun_laporan_akhir", "cakupan_wilayah", "daerah", "jenis", "jaringan",
    "cakupan_layanan", "pemicu", "alasan_pemerintah", "diperintahkan_oleh", "pemilu", "kekerasan",
    "pelanggaran_ham", "platform", "keterangan", "sumber_url", "tanggal_perkiraan",
]


# ----------------------------------------------------------------------------
# Fungsi murni (diuji)
# ----------------------------------------------------------------------------
def _peta(nilai, tabel: dict[str, str], bawaan: str = "Tidak diketahui") -> str:
    if pd.isna(nilai):
        return bawaan
    return tabel.get(str(nilai).strip(), str(nilai).strip())


def daftar_platform(baris: pd.Series) -> str:
    """Gabungkan kolom *_affected + other_affected menjadi teks 'Facebook; WhatsApp; TikTok'."""
    nama = [label for kolom, label in KOLOM_PLATFORM.items() if str(baris.get(kolom, "")).strip() == "Yes"]
    lain = baris.get("other_affected")
    if isinstance(lain, str) and lain.strip() and lain.strip().lower() not in {"none", "nan", "no", "unknown"}:
        teks = lain.strip()
        nama.append(teks if len(teks) <= 60 else teks[:57] + "...")
    return "; ".join(nama)


def hitung_durasi(mulai, selesai, durasi_mentah) -> float:
    """Durasi dalam hari: dari tanggal jika lengkap, jika tidak dari kolom `duration` STOP (satuan hari)."""
    if pd.notna(mulai) and pd.notna(selesai):
        selisih = (pd.Timestamp(selesai).normalize() - pd.Timestamp(mulai).normalize()).days
        if selisih >= 0:
            return float(selisih + 1)
    try:
        nilai = float(durasi_mentah)
    except (TypeError, ValueError):
        return float("nan")
    if pd.isna(nilai) or nilai < 0:
        return float("nan")
    return max(nilai, 1.0)


def gabungkan_duplikat(df: pd.DataFrame) -> pd.DataFrame:
    """Satu pemutusan yang muncul di beberapa lembar tahunan digabung menjadi satu baris.

    Baris terakhir (lembar tahun paling baru) dipakai sebagai nilai, karena berisi pembaruan status dan tanggal
    selesai. Rentang lembar tempat ia muncul disimpan sebagai tahun_laporan_awal / tahun_laporan_akhir.
    """
    kerja = df.copy()
    for k in KUNCI_UNIK:
        kerja[k] = kerja[k].astype(str).str.strip().replace({"nan": "", "None": ""})
    kerja["_urut"] = range(len(kerja))
    kerja = kerja.sort_values(["tahun_laporan", "_urut"])
    grup = kerja.groupby(KUNCI_UNIK, sort=False, dropna=False)
    terakhir = grup.tail(1).copy()
    rentang = grup["tahun_laporan"].agg(["min", "max"]).reset_index()
    rentang = rentang.rename(columns={"min": "tahun_laporan_awal", "max": "tahun_laporan_akhir"})
    hasil = terakhir.merge(rentang, on=KUNCI_UNIK, how="left").drop(columns=["_urut"])
    return hasil.sort_values(["start_date", "country"]).reset_index(drop=True)


def rapikan(df: pd.DataFrame) -> pd.DataFrame:
    """Terjemahkan kolom STOP (sudah digabung) menjadi tabel keluaran berbahasa Indonesia."""
    keluaran = pd.DataFrame(index=df.index)
    info = df["country"].map(info_negara)
    keluaran["negara"] = info.map(lambda t: t[1])
    keluaran["iso3"] = info.map(lambda t: t[0])
    keluaran["wilayah"] = info.map(lambda t: t[2])
    keluaran["negara_en"] = df["country"].astype(str).str.strip()
    mulai = pd.to_datetime(df["start_date"], errors="coerce")
    selesai = pd.to_datetime(df["end_date"], errors="coerce")
    keluaran["tahun"] = mulai.dt.year.astype("Int64")
    keluaran["mulai"] = mulai.dt.date
    keluaran["selesai"] = selesai.dt.date
    keluaran["durasi_hari"] = [hitung_durasi(m, s, d) for m, s, d in zip(mulai, selesai, df["duration"])]
    # Status: tanggal selesai yang tercatat lebih dipercaya daripada label status (yang kadang lupa diperbarui)
    status = df["shutdown_status"].map(lambda v: _peta(v, {"Ended": "Selesai", "Ongoing": "Berlangsung", "Unknown": "Tidak diketahui"}))
    status = status.where(status.isin(["Selesai", "Berlangsung"]), other="Tidak diketahui")
    status = status.where(selesai.isna(), other="Selesai")
    keluaran["status"] = status
    keluaran["tahun_laporan_awal"] = df["tahun_laporan_awal"].astype(int)
    keluaran["tahun_laporan_akhir"] = df["tahun_laporan_akhir"].astype(int)
    keluaran["cakupan_wilayah"] = df["geo_scope"].map(lambda v: _peta(v, CAKUPAN_WILAYAH, "Tidak pasti"))
    keluaran["daerah"] = df["area_name"].fillna("").astype(str).str.strip().str.slice(0, 160)
    keluaran["jenis"] = df["shutdown_type"].map(lambda v: _peta(v, JENIS))
    keluaran["jaringan"] = df["affected_network"].map(lambda v: _peta(v, JARINGAN))
    keluaran["cakupan_layanan"] = df["shutdown_extent"].map(lambda v: _peta(v, CAKUPAN_LAYANAN))
    keluaran["pemicu"] = df["actual_cause"].map(lambda v: _peta(v, PEMICU))
    keluaran["alasan_pemerintah"] = df["gov_justification"].map(lambda v: _peta(v, ALASAN, "Tidak disebutkan"))
    keluaran["diperintahkan_oleh"] = df["ordered_by"].map(lambda v: _peta(v, PEMBERI_PERINTAH))
    keluaran["pemilu"] = df["election"].map(lambda v: _peta(v, YA_TIDAK))
    keluaran["kekerasan"] = df["violence"].map(lambda v: _peta(v, YA_TIDAK))
    keluaran["pelanggaran_ham"] = df["hr_abuse_reported"].map(lambda v: _peta(v, YA_TIDAK))
    keluaran["platform"] = df.apply(daftar_platform, axis=1)
    keluaran["keterangan"] = df["event"].fillna("").astype(str).str.strip().replace({"NA": "", "None": ""}).str.slice(0, 600)
    keluaran["sumber_url"] = df["info_source_link"].fillna("").astype(str).str.strip().replace({"NA": "", "None": ""})
    keluaran["tanggal_perkiraan"] = df["start_date_type"].map(lambda v: str(v).strip() == "Estimated")
    keluaran = keluaran[keluaran["mulai"].notna()].copy()
    keluaran.insert(0, "id", range(1, len(keluaran) + 1))
    return keluaran[KOLOM_KELUARAN].reset_index(drop=True)


def baca_gabungan(path_xlsx: Path) -> pd.DataFrame:
    """Baca semua lembar tahunan (2016..2025) dan tandai tahun laporannya.

    Lembar "Combined" tidak menyimpan dari lembar mana tiap baris berasal, jadi lembar tahunan dibaca satu per satu.
    """
    xlsx = pd.ExcelFile(path_xlsx)
    potongan = []
    for nama in xlsx.sheet_names:
        if len(nama) == 4 and nama.isdigit():
            lembar = xlsx.parse(nama)
            lembar.columns = [str(c).strip().replace(" ", "_") for c in lembar.columns]
            lembar["tahun_laporan"] = int(nama)
            potongan.append(lembar)
    if not potongan:
        raise ValueError("Tidak ada lembar tahunan di spreadsheet STOP")
    return pd.concat(potongan, ignore_index=True)


# ----------------------------------------------------------------------------
# Jaringan + penulisan file
# ----------------------------------------------------------------------------
def unduh_stop(tujuan: Path) -> Path:
    import requests

    tujuan.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(URL_STOP, timeout=120)
    resp.raise_for_status()
    tujuan.write_bytes(resp.content)
    return tujuan


def bangun_stop(path_xlsx: Path | None = None) -> pd.DataFrame:
    path_xlsx = path_xlsx or unduh_stop(DIR_RAW / "keepiton_stop.xlsx")
    mentah = baca_gabungan(path_xlsx)
    unik = gabungkan_duplikat(mentah)
    bersih = rapikan(unik)
    keluar = DIR_DATA / "shutdown_dunia.csv"
    bersih.to_csv(keluar, index=False)
    print(f"STOP: {len(mentah)} baris lembar tahunan -> {len(bersih)} pemutusan unik -> {keluar}")
    return bersih


def bangun_konflik(url: str = URL_KONFLIK) -> pd.DataFrame:
    """Korban konflik bersenjata per negara-tahun 2016+ (agregat UCDP dari proyek global-conflict-tracker)."""
    df = pd.read_csv(url)
    agg = (
        df[df["tahun"] >= 2016]
        .groupby(["iso3", "negara", "tahun"], as_index=False)[["kejadian", "korban", "korban_sipil"]]
        .sum()
    )
    keluar = DIR_DATA / "korban_konflik_negara_tahun.csv"
    agg.to_csv(keluar, index=False)
    print(f"UCDP: {len(agg)} baris negara-tahun -> {keluar}")
    return agg


def potret_ioda() -> None:
    ringkasan = ioda.ambil_ringkasan_negara(hari=30)
    ringkasan.to_csv(DIR_DATA / "ioda_ringkasan_30hari.csv", index=False)
    kejadian = ioda.ambil_kejadian("ID", hari=365)
    kejadian.to_csv(DIR_DATA / "ioda_kejadian_indonesia.csv", index=False)
    dunia = ioda.ambil_kejadian_dunia(hari=30, batas=500)
    dunia.to_csv(DIR_DATA / "ioda_kejadian_dunia_30hari.csv", index=False)
    sinyal = ioda.ambil_sinyal("ID", hari=7)
    sinyal.to_csv(DIR_DATA / "ioda_sinyal_indonesia_7hari.csv", index=False)
    print(f"IODA: {len(ringkasan)} negara, {len(kejadian)} kejadian ID, {len(dunia)} kejadian dunia, {len(sinyal)} titik sinyal")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--xlsx", type=Path, default=None, help="pakai file STOP lokal, jangan unduh")
    parser.add_argument("--tanpa-ioda", action="store_true", help="lewati potret IODA")
    parser.add_argument("--hanya-ioda", action="store_true", help="hanya perbarui potret IODA")
    args = parser.parse_args(argv)
    DIR_DATA.mkdir(exist_ok=True)
    if not args.hanya_ioda:
        bangun_stop(args.xlsx)
        bangun_konflik()
    if not args.tanpa_ioda:
        potret_ioda()
    return 0


if __name__ == "__main__":
    sys.exit(main())
