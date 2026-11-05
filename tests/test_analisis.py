"""
Pengujian untuk src/analisis.py, src/siapkan_data.py (fungsi murni), src/ioda.py (parser), src/negara.py,
dan konsistensi data di folder data/.
Jalankan:  python -m pytest tests/ -v
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import analisis, ioda, muat_data, siapkan_data
from src.negara import PETA_NEGARA, info_negara, nama_dari_iso2, nama_dari_iso3


# ----------------------------------------------------------------------------
# Data buatan kecil agar pengujian fungsi tidak bergantung pada CSV besar
# ----------------------------------------------------------------------------
@pytest.fixture
def df_kecil() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6],
            "negara": ["India", "India", "Indonesia", "Myanmar", "Myanmar", "Irak"],
            "iso3": ["IND", "IND", "IDN", "MMR", "MMR", "IRQ"],
            "wilayah": ["Asia", "Asia", "Asia", "Asia", "Asia", "Timur Tengah"],
            "tahun": [2019, 2021, 2019, 2021, 2021, 2023],
            "mulai": pd.to_datetime(["2019-08-05", "2021-05-03", "2019-08-22", "2021-02-01", "2021-03-15", "2023-06-10"]),
            "selesai": pd.to_datetime(["2020-03-04", "2021-05-05", "2019-09-05", pd.NaT, "2021-03-15", "2023-06-10"]),
            "durasi_hari": [213.0, 3.0, 15.0, float("nan"), 1.0, 1.0],
            "status": ["Selesai", "Selesai", "Selesai", "Berlangsung", "Selesai", "Selesai"],
            "tahun_laporan_awal": [2019, 2021, 2019, 2021, 2021, 2023],
            "tahun_laporan_akhir": [2020, 2021, 2019, 2025, 2021, 2023],
            "cakupan_wilayah": ["Lintas provinsi / nasional"] * 6,
            "daerah": ["Jammu & Kashmir", "Lakhimpur", "Papua", "Nationwide", "Yangon", "Nationwide"],
            "jenis": ["Pemutusan", "Pemutusan", "Pemutusan", "Pemutusan", "Pelambatan", "Pemutusan"],
            "jaringan": ["Broadband & seluler", "Seluler", "Seluler", "Broadband & seluler", "Seluler", "Seluler"],
            "cakupan_layanan": ["Seluruh jaringan", "Seluruh jaringan", "Seluruh jaringan", "Seluruh jaringan", "Platform tertentu", "Seluruh jaringan"],
            "pemicu": ["Instabilitas politik", "Unjuk rasa", "Unjuk rasa", "Instabilitas politik", "Unjuk rasa", "Ujian sekolah"],
            "alasan_pemerintah": ["Keamanan nasional / terorisme", "Hoaks / ujaran kebencian", "Keamanan / ketertiban umum",
                                  "Tidak disebutkan", "Tidak disebutkan", "Ujian sekolah"],
            "diperintahkan_oleh": ["Pemerintah pusat"] * 6,
            "pemilu": ["Tidak"] * 6,
            "kekerasan": ["Ya", "Ya", "Ya", "Ya", "Tidak", "Tidak diketahui"],
            "pelanggaran_ham": ["Ya", "Tidak diketahui", "Ya", "Ya", "Tidak", "Tidak"],
            "platform": ["", "", "WhatsApp; Facebook", "Facebook; Instagram; Twitter", "Facebook", ""],
            "keterangan": [""] * 6,
            "sumber_url": [""] * 6,
        }
    )


@pytest.fixture
def df_konflik() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "iso3": ["IND", "IND", "MMR", "MEX", "IDN"],
            "negara": ["India", "India", "Myanmar", "Meksiko", "Indonesia"],
            "tahun": [2019, 2021, 2021, 2021, 2019],
            "kejadian": [300, 250, 900, 2000, 22],
            "korban": [600, 400, 5000, 8000, 41],
            "korban_sipil": [50, 30, 1500, 3000, 10],
        }
    )


# ----------------------------------------------------------------------------
# analisis.py
# ----------------------------------------------------------------------------
def test_filter_tahun_mulai(df_kecil):
    hasil = analisis.filter_data(df_kecil, 2021, 2021)
    assert set(hasil["tahun"]) == {2021}
    assert len(hasil) == 3


def test_filter_dasar_aktif_menghitung_pemutusan_lintas_tahun(df_kecil):
    # Myanmar 2021 masih berlangsung sampai 2025 -> ikut terhitung di 2024 meski dimulai 2021
    mulai = analisis.filter_data(df_kecil, 2024, 2024, dasar_tahun="mulai")
    aktif = analisis.filter_data(df_kecil, 2024, 2024, dasar_tahun="aktif")
    assert len(mulai) == 0
    assert aktif["negara"].tolist() == ["Myanmar"]


def test_filter_pemicu_wilayah_jenis_dan_jaringan(df_kecil):
    hasil = analisis.filter_data(df_kecil, 2016, 2025, pemicu=["Unjuk rasa"], wilayah=["Asia"], jenis=["Pelambatan"])
    assert hasil["id"].tolist() == [5]
    penuh = analisis.filter_data(df_kecil, 2016, 2025, hanya_seluruh_jaringan=True)
    assert 5 not in set(penuh["id"])


def test_ringkasan(df_kecil):
    r = analisis.ringkasan(df_kecil)
    assert r["jumlah"] == 6 and r["negara"] == 4
    assert r["hari"] == 233.0
    assert r["negara_teratas"] in {"India", "Myanmar"} and r["jumlah_teratas"] == 2
    assert r["berlangsung"] == 1
    # 4 dari 5 yang diketahui (Ya/Tidak) = kekerasan
    assert r["persen_kekerasan"] == pytest.approx(80.0)
    # 5 dari 6 pemicu termasuk kerusuhan (bukan ujian sekolah)
    assert r["persen_kerusuhan"] == pytest.approx(5 / 6 * 100)


def test_ringkasan_kosong():
    r = analisis.ringkasan(pd.DataFrame(columns=["negara", "durasi_hari", "kekerasan", "pemicu", "status"]))
    assert r["jumlah"] == 0 and r["negara_teratas"] == "-"


def test_per_tahun_dan_aktif(df_kecil):
    pt = analisis.per_tahun(df_kecil, None)
    assert dict(zip(pt["tahun"], pt["jumlah"])) == {2019: 2, 2021: 3, 2023: 1}
    aktif = analisis.aktif_per_tahun(df_kecil, 2019, 2023).set_index("tahun")
    assert aktif.loc[2020, "aktif"] == 1          # India 2019-2020 masih dihitung di 2020
    assert aktif.loc[2020, "dimulai"] == 0
    assert aktif.loc[2021, "aktif"] == 3


def test_per_negara_dan_peringkat(df_kecil):
    tabel = analisis.per_negara(df_kecil)
    india = tabel[tabel["negara"] == "India"].iloc[0]
    assert india["jumlah"] == 2 and india["hari"] == 216.0
    assert india["tahun_awal"] == 2019 and india["tahun_akhir"] == 2021
    myanmar = tabel[tabel["negara"] == "Myanmar"].iloc[0]
    assert myanmar["pemicu_utama"] in {"Instabilitas politik", "Unjuk rasa"}
    peringkat, jumlah = analisis.peringkat_negara(df_kecil, "Indonesia")
    assert jumlah == 1 and peringkat >= 3
    assert analisis.peringkat_negara(df_kecil, "Atlantis") == (0, 0)


def test_per_kategori_persen(df_kecil):
    pk = analisis.per_kategori(df_kecil, "pemicu").set_index("pemicu")
    assert pk.loc["Unjuk rasa", "jumlah"] == 3
    assert pk.loc["Unjuk rasa", "persen"] == 50.0


def test_pemicu_vs_alasan(df_kecil):
    pasangan = analisis.pemicu_vs_alasan(df_kecil, minimal=1)
    assert pasangan["jumlah"].sum() == 6
    assert set(pasangan.columns) == {"pemicu", "alasan_pemerintah", "jumlah"}
    assert analisis.pemicu_vs_alasan(df_kecil, minimal=3).empty


def test_platform_per_tahun(df_kecil):
    pp = analisis.platform_per_tahun(df_kecil)
    fb_2021 = pp[(pp["tahun"] == 2021) & (pp["platform"] == "Facebook")]["jumlah"].iloc[0]
    assert fb_2021 == 2
    x_2021 = pp[(pp["tahun"] == 2021) & (pp["platform"] == "X/Twitter")]["jumlah"].iloc[0]
    assert x_2021 == 1


@pytest.mark.parametrize(
    "hari,kategori",
    [(float("nan"), "Tidak diketahui"), (1, "≤ 1 hari"), (7, "2–7 hari"), (8, "8–30 hari"), (200, "1–12 bulan"), (400, "> 1 tahun")],
)
def test_kategori_durasi(hari, kategori):
    assert analisis.kategori_durasi(hari) == kategori


def test_sebaran_durasi_urut_dan_lengkap(df_kecil):
    sd = analisis.sebaran_durasi(df_kecil)
    assert sd["kategori"].tolist() == analisis.URUTAN_DURASI
    assert sd["jumlah"].sum() == 6


def test_linimasa_mengisi_tanggal_selesai(df_kecil):
    gantt = analisis.linimasa(df_kecil)
    baris = gantt[gantt["negara"] == "Myanmar"].sort_values("mulai").iloc[0]
    assert baris["akhir_gantt"] == pd.Timestamp("2026-01-01")   # berlangsung: bar sampai akhir tahun laporan 2025 (+1 hari)
    satu_hari = gantt[gantt["id"] == 5].iloc[0]
    assert (satu_hari["akhir_gantt"] - satu_hari["mulai"]).days == 1
    assert gantt["mulai"].is_monotonic_decreasing


def test_profil_negara(df_kecil):
    prof = analisis.profil_negara(df_kecil, "Indonesia")
    assert len(prof["tabel"]) == 1
    assert prof["ringkasan"]["hari"] == 15.0


def test_gabung_konflik_outer_dan_korelasi(df_kecil, df_konflik):
    gab = analisis.gabung_konflik(df_kecil, df_konflik, 2016, 2025)
    meksiko = gab[(gab["iso3"] == "MEX")].iloc[0]
    assert meksiko["shutdown"] == 0 and meksiko["korban"] == 8000          # hanya di UCDP, tetap masuk
    irak = gab[(gab["iso3"] == "IRQ")].iloc[0]
    assert irak["korban"] == 0 and irak["shutdown"] == 1                   # hanya di Access Now
    kor = analisis.korelasi_konflik(gab)
    assert kor["negara_tahun_konflik"] == 5                                # IND19, IND21, MMR21, MEX21, IDN19
    assert kor["dengan_shutdown"] == 4
    assert kor["persen"] == pytest.approx(80.0)


# ----------------------------------------------------------------------------
# siapkan_data.py: fungsi murni
# ----------------------------------------------------------------------------
def test_hitung_durasi():
    assert siapkan_data.hitung_durasi(pd.Timestamp("2019-08-22"), pd.Timestamp("2019-09-05"), None) == 15.0
    assert siapkan_data.hitung_durasi(pd.Timestamp("2019-08-22"), pd.Timestamp("2019-08-22"), None) == 1.0
    assert siapkan_data.hitung_durasi(pd.Timestamp("2019-08-22"), pd.NaT, "3") == 3.0
    assert siapkan_data.hitung_durasi(pd.Timestamp("2019-08-22"), pd.NaT, "0") == 1.0
    assert pd.isna(siapkan_data.hitung_durasi(pd.Timestamp("2019-08-22"), pd.NaT, "abc"))
    assert pd.isna(siapkan_data.hitung_durasi(pd.Timestamp("2019-08-22"), pd.NaT, None))


def test_daftar_platform():
    baris = pd.Series({"facebook_affected": "Yes", "twitter_affected": "No", "whatsapp_affected": "Yes",
                       "instagram_affected": "Unknown", "telegram_affected": "No", "other_affected": "TikTok Live"})
    assert siapkan_data.daftar_platform(baris) == "Facebook; WhatsApp; TikTok Live"
    kosong = pd.Series({"facebook_affected": "No", "other_affected": "None"})
    assert siapkan_data.daftar_platform(kosong) == ""


def _mentah(**ganti):
    dasar = {
        "country": "Indonesia", "start_date": "2016-09-15", "end_date": None, "area_name": "Nationwide",
        "shutdown_type": "Shutdown", "affected_network": "Broadband, Mobile", "shutdown_extent": "Service-based",
        "actual_cause": "Information control", "other_affected": "Grindr", "duration": None, "shutdown_status": "Ongoing",
        "geo_scope": "It affected locations in more than one state, province, or region", "gov_justification": "Other",
        "ordered_by": "Executive government", "election": "No", "violence": "No", "hr_abuse_reported": "No",
        "facebook_affected": "No", "twitter_affected": "No", "whatsapp_affected": "No", "instagram_affected": "No",
        "telegram_affected": "No", "event": "Grindr blocked", "info_source_link": "https://x", "start_date_type": "Estimated",
        "tahun_laporan": 2016,
    }
    dasar.update(ganti)
    return dasar


def test_gabungkan_duplikat_menyatukan_lembar_tahunan():
    mentah = pd.DataFrame([
        _mentah(tahun_laporan=2016), _mentah(tahun_laporan=2017), _mentah(tahun_laporan=2018, shutdown_status="Ended", end_date="2018-02-01"),
        _mentah(area_name="Papua", start_date="2019-08-22", actual_cause="Protests", tahun_laporan=2019),
    ])
    unik = siapkan_data.gabungkan_duplikat(mentah)
    assert len(unik) == 2
    grindr = unik[unik["area_name"] == "Nationwide"].iloc[0]
    assert (grindr["tahun_laporan_awal"], grindr["tahun_laporan_akhir"]) == (2016, 2018)
    assert grindr["shutdown_status"] == "Ended"           # nilai lembar terbaru yang dipakai


def test_rapikan_menerjemahkan_dan_memetakan_negara():
    mentah = pd.DataFrame([_mentah(), _mentah(country="Iran (Islamic Republic of)", area_name="Tehran", start_date="2019-11-16",
                                             end_date="2019-11-23", actual_cause="Protests", shutdown_type="Shutdown",
                                             shutdown_extent="Full network", gov_justification="National security/ Counter-terrorism",
                                             violence="Yes", tahun_laporan=2019)])
    unik = siapkan_data.gabungkan_duplikat(mentah)
    bersih = siapkan_data.rapikan(unik)
    assert bersih.columns.tolist() == siapkan_data.KOLOM_KELUARAN
    iran = bersih[bersih["negara"] == "Iran"].iloc[0]
    assert iran["iso3"] == "IRN" and iran["wilayah"] == "Timur Tengah"
    assert iran["pemicu"] == "Unjuk rasa" and iran["alasan_pemerintah"] == "Keamanan nasional / terorisme"
    assert iran["durasi_hari"] == 8.0 and iran["status"] == "Selesai" and iran["kekerasan"] == "Ya"
    indo = bersih[bersih["negara"] == "Indonesia"].iloc[0]
    assert indo["status"] == "Berlangsung" and indo["platform"] == "Grindr" and bool(indo["tanggal_perkiraan"]) is True
    assert indo["cakupan_layanan"] == "Platform tertentu"


# ----------------------------------------------------------------------------
# ioda.py: parser tanpa jaringan
# ----------------------------------------------------------------------------
def test_urai_ringkasan():
    data = [{"scores": {"bgp.median": 10.5, "overall": 99.0}, "event_cnt": 3, "entity": {"code": "ID", "name": "Indonesia", "type": "country"}}]
    df = ioda.urai_ringkasan(data)
    assert df.iloc[0]["kode"] == "ID" and df.iloc[0]["jumlah_kejadian"] == 3
    assert df.iloc[0]["skor_total"] == 99.0 and df.iloc[0]["skor_ping"] == 0.0
    assert ioda.urai_ringkasan([]).empty


def test_urai_kejadian_urut_terbaru():
    data = [
        {"location": "country/ID", "location_name": "Indonesia", "start": 1700000000, "duration": 600, "datasource": "bgp", "score": 5},
        {"location": "country/ID", "location_name": "Indonesia", "start": 1700100000, "duration": 1800, "datasource": "ping-slash24", "score": 7, "overlaps_window": True},
    ]
    df = ioda.urai_kejadian(data)
    assert df.iloc[0]["sumber"] == "ping-slash24" and df.iloc[0]["durasi_menit"] == 30.0
    assert bool(df.iloc[0]["sedang_berlangsung"]) is True
    assert (df.iloc[0]["selesai"] - df.iloc[0]["mulai"]).total_seconds() == 1800


def test_urai_sinyal_melewati_sumber_berobjek_dan_normalisasi():
    data = [[
        {"datasource": "bgp", "from": 1700000000, "step": 3600, "values": [100, 50, None, 100]},
        {"datasource": "ping-slash24-loss", "from": 1700000000, "step": 3600, "values": [[{"agg_values": {"loss_pct": 1}}]]},
    ]]
    df = ioda.urai_sinyal(data)
    assert set(df["sumber"]) == {"bgp"} and len(df) == 4
    assert (df["waktu"].iloc[1] - df["waktu"].iloc[0]).total_seconds() == 3600
    norm = ioda.normalisasi_sinyal(df)
    assert norm["relatif"].iloc[1] == pytest.approx(0.5)
    assert ioda.normalisasi_sinyal(pd.DataFrame(columns=["waktu", "sumber", "nilai"])).empty


# ----------------------------------------------------------------------------
# negara.py
# ----------------------------------------------------------------------------
def test_info_negara():
    assert info_negara("Indonesia") == ("IDN", "Indonesia", "Asia")
    assert info_negara("Iran (Islamic Republic of)")[0] == "IRN"
    assert info_negara("Cameroon; Central African Republic")[0] == "CMR"
    assert info_negara("Narnia") == ("", "Narnia", "Lainnya")
    assert nama_dari_iso3("MMR") == "Myanmar" and nama_dari_iso2("ID") == "Indonesia"
    assert nama_dari_iso2("ZZ", "Zeta") == "Zeta"


def test_peta_negara_konsisten():
    for nama, (iso3, nama_id, wilayah) in PETA_NEGARA.items():
        assert len(iso3) == 3 and iso3.isupper(), nama
        assert nama_id and wilayah in {"Asia", "Afrika", "Eropa", "Amerika", "Timur Tengah", "Oseania"}


# ----------------------------------------------------------------------------
# Konsistensi file di data/
# ----------------------------------------------------------------------------
def test_data_shutdown_valid():
    df = muat_data.muat_shutdown()
    assert len(df) > 1500
    assert df["iso3"].str.len().eq(3).all()
    assert df["pemicu"].isin(analisis.URUTAN_PEMICU).all()
    assert df["mulai"].notna().all()
    assert (df["tahun_laporan_awal"] <= df["tahun_laporan_akhir"]).all()
    assert df["id"].is_unique
    assert (df[df["negara"] == "Indonesia"]["pemicu"] == "Unjuk rasa").sum() >= 3     # Papua 2019, 2021, protes 2025
    # hasil penggabungan harus mendekati jumlah laporan tahunan Access Now (2025: 313)
    aktif = analisis.aktif_per_tahun(df, 2025, 2025)
    assert 300 <= aktif.loc[0, "aktif"] <= 330


def test_data_konflik_dan_potret_ioda():
    kf = muat_data.muat_konflik()
    assert {"iso3", "negara", "tahun", "korban"} <= set(kf.columns)
    assert kf["tahun"].min() >= 2016
    ring = muat_data.muat_potret_ioda("ringkasan_30hari")
    assert not ring.empty and "skor_total" in ring.columns
    sinyal = muat_data.muat_potret_ioda("sinyal_indonesia_7hari")
    assert not sinyal.empty and str(sinyal["waktu"].dt.tz) == "UTC"
    assert muat_data.muat_potret_ioda("tidak_ada").empty
