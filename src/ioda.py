"""
ioda.py - Klien ringan untuk API publik IODA (Internet Outage Detection and Analysis), Georgia Tech.

IODA mendeteksi gangguan konektivitas secara otomatis dari tiga sinyal independen:
  - bgp          : jumlah blok alamat IP (/24) yang masih diumumkan di tabel routing global
  - ping-slash24 : jumlah blok /24 yang masih membalas ping (pengukuran aktif)
  - merit-nt     : lalu lintas "latar" yang sampai ke teleskop jaringan Merit (gelap = tidak ada paket)
  - gtr          : volume trafik Google (Google Transparency Report), tersedia untuk sebagian negara

API tidak memerlukan kunci. Dokumentasi: https://api.ioda.inetintel.cc.gatech.edu/v2/
Semua fungsi `urai_*` adalah fungsi murni (tanpa jaringan) agar mudah diuji; fungsi `ambil_*`
hanya membungkus requests + urai.
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

URL_DASAR = "https://api.ioda.inetintel.cc.gatech.edu/v2"
TIMEOUT = 25
NAMA_SUMBER = {
    "bgp": "BGP (routing)",
    "ping-slash24": "Ping aktif",
    "merit-nt": "Teleskop jaringan",
    "gtr": "Trafik Google",
    "gtr-norm": "Trafik Google (normal)",
}
PENJELASAN_SUMBER = {
    "bgp": "Berapa banyak blok alamat IP negara itu yang masih diumumkan ke internet global. Turun tajam = jaringan 'dicabut' dari peta routing.",
    "ping-slash24": "Berapa banyak blok alamat yang masih membalas ping dari luar. Turun = perangkat tidak terjangkau meskipun rute masih ada.",
    "merit-nt": "Paket 'nyasar' yang biasanya terus-menerus datang dari suatu negara. Hening = tidak ada lalu lintas keluar.",
    "gtr": "Volume permintaan ke layanan Google dari negara tersebut (data Google Transparency Report).",
}


def _get(jalur: str, params: dict[str, Any]) -> dict[str, Any]:
    resp = requests.get(f"{URL_DASAR}{jalur}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    hasil = resp.json()
    if hasil.get("error"):
        raise RuntimeError(f"IODA: {hasil['error']}")
    return hasil


# ----------------------------------------------------------------------------
# Fungsi murni: mengubah JSON IODA menjadi DataFrame
# ----------------------------------------------------------------------------
def _angka(nilai: Any, bawaan: float = 0.0) -> float:
    """Ubah nilai JSON jadi float; teks berdesimal ("12.0") diterima, sampah/NaN/inf jadi `bawaan`."""
    try:
        hasil = float(nilai)
    except (TypeError, ValueError):
        return bawaan
    return hasil if pd.notna(hasil) and abs(hasil) != float("inf") else bawaan


def urai_ringkasan(data: list[dict[str, Any]]) -> pd.DataFrame:
    """Ringkasan gangguan per entitas (negara) dalam satu jendela waktu.

    Setiap baris IODA: {"scores": {"bgp.median": .., "overall": ..}, "event_cnt": n, "entity": {...}}.
    """
    baris = []
    for item in data:
        ent = item.get("entity") or {}
        skor = item.get("scores") or {}
        baris.append(
            {
                "kode": ent.get("code", ""),
                "nama_en": ent.get("name", ""),
                "tipe": ent.get("type", ""),
                "jumlah_kejadian": int(_angka(item.get("event_cnt"))),
                "skor_total": _angka(skor.get("overall")),
                "skor_bgp": _angka(skor.get("bgp.median")),
                "skor_ping": _angka(skor.get("ping-slash24.median")),
                "skor_teleskop": _angka(skor.get("merit-nt.median")),
                "skor_google": _angka(skor.get("gtr.sarima")),
            }
        )
    kolom = ["kode", "nama_en", "tipe", "jumlah_kejadian", "skor_total", "skor_bgp", "skor_ping", "skor_teleskop", "skor_google"]
    return pd.DataFrame(baris, columns=kolom)


def urai_kejadian(data: list[dict[str, Any]]) -> pd.DataFrame:
    """Daftar kejadian gangguan (outage events) terdeteksi.

    Setiap baris IODA: {"location": "country/ID", "start": epoch, "duration": detik, "datasource": .., "score": ..}.
    """
    baris = []
    for e in data:
        # Kejadian tanpa waktu mulai tidak bisa digambar; jangan sampai jatuh ke 1970.
        if not isinstance(e, dict) or e.get("start") in (None, ""):
            continue
        # Epoch kadang datang sebagai teks berdesimal ("1731900000.0"); int() langsung akan gagal.
        try:
            mulai = pd.to_datetime(int(float(e["start"])), unit="s", utc=True)
            durasi = int(float(e.get("duration", 0) or 0))
        except (TypeError, ValueError):
            continue
        baris.append(
            {
                "lokasi": e.get("location", ""),
                "nama_en": e.get("location_name", ""),
                "mulai": mulai,
                "selesai": mulai + pd.Timedelta(seconds=durasi),
                "durasi_menit": round(durasi / 60, 1),
                "sumber": e.get("datasource", ""),
                "skor": _angka(e.get("score")),
                "sedang_berlangsung": bool(e.get("overlaps_window", False)),
            }
        )
    kolom = ["lokasi", "nama_en", "mulai", "selesai", "durasi_menit", "sumber", "skor", "sedang_berlangsung"]
    df = pd.DataFrame(baris, columns=kolom)
    if not df.empty:
        df = df.sort_values("mulai", ascending=False).reset_index(drop=True)
    return df


def urai_sinyal(data: list[Any]) -> pd.DataFrame:
    """Deret waktu sinyal mentah. IODA mengembalikan list (per entitas) berisi list (per sumber data).

    Hanya sumber bernilai skalar yang diambil (bgp, ping-slash24, merit-nt, gtr, gtr-norm). Sumber yang
    nilainya berupa objek (ping-slash24-loss, mozilla, gtr-sarima) dilewati.
    """
    baris = []
    for grup in data:
        seri_list = grup if isinstance(grup, list) else [grup]
        for seri in seri_list:
            # Entitas tanpa data kadang berisi null di dalam list.
            if not isinstance(seri, dict):
                continue
            sumber = seri.get("datasource", "")
            nilai = seri.get("values") or []
            if not nilai or not all(v is None or isinstance(v, (int, float)) for v in nilai):
                continue
            langkah = int(seri.get("step", 0) or 0)
            awal = int(seri.get("from", 0) or 0)
            for i, v in enumerate(nilai):
                baris.append(
                    {
                        "waktu": pd.to_datetime(awal + i * langkah, unit="s", utc=True),
                        "sumber": sumber,
                        "nilai": None if v is None else float(v),
                    }
                )
    df = pd.DataFrame(baris, columns=["waktu", "sumber", "nilai"])
    return df


def normalisasi_sinyal(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan kolom `relatif` = nilai / median per sumber, agar tiga sinyal bisa digambar pada satu sumbu.

    Nilai 1,0 berarti normal; 0,5 berarti sinyal tinggal separuh dari biasanya.
    """
    if df.empty:
        return df.assign(relatif=pd.Series(dtype=float))
    hasil = df.copy()
    median = hasil.groupby("sumber")["nilai"].transform("median")
    hasil["relatif"] = hasil["nilai"] / median.where(median > 0)
    return hasil


# ----------------------------------------------------------------------------
# Fungsi jaringan
# ----------------------------------------------------------------------------
def _jendela(hari: int) -> tuple[int, int]:
    sekarang = int(time.time())
    return sekarang - hari * 86400, sekarang


def ambil_ringkasan_negara(hari: int = 7, batas: int = 400) -> pd.DataFrame:
    """Negara-negara dengan gangguan terdeteksi dalam `hari` terakhir, diurutkan IODA menurut skor."""
    dari, sampai = _jendela(hari)
    hasil = _get("/outages/summary", {"entityType": "country", "from": dari, "until": sampai, "limit": batas})
    return urai_ringkasan(hasil.get("data", []))


def ambil_kejadian(kode_negara: str = "ID", hari: int = 90, batas: int = 200) -> pd.DataFrame:
    """Kejadian gangguan untuk satu negara (kode ISO-2) dalam `hari` terakhir."""
    dari, sampai = _jendela(hari)
    hasil = _get(
        "/outages/events",
        {"entityType": "country", "entityCode": kode_negara, "from": dari, "until": sampai, "limit": batas},
    )
    return urai_kejadian(hasil.get("data", []))


def ambil_kejadian_dunia(hari: int = 7, batas: int = 300) -> pd.DataFrame:
    """Semua kejadian tingkat negara di dunia dalam `hari` terakhir."""
    dari, sampai = _jendela(hari)
    hasil = _get("/outages/events", {"entityType": "country", "from": dari, "until": sampai, "limit": batas})
    return urai_kejadian(hasil.get("data", []))


def ambil_sinyal(kode_negara: str = "ID", hari: int = 7, maks_titik: int = 400) -> pd.DataFrame:
    """Deret waktu sinyal bgp / ping / teleskop / Google untuk satu negara."""
    dari, sampai = _jendela(hari)
    hasil = _get(f"/signals/raw/country/{kode_negara}", {"from": dari, "until": sampai, "maxPoints": maks_titik})
    return urai_sinyal(hasil.get("data", []))
