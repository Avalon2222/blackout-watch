"""
negara.py - Pemetaan nama negara di dataset #KeepItOn ke kode ISO-3 dan nama Indonesia.

Nama negara di STOP (Shutdown Tracker Optimization Project) memakai gaya PBB dalam bahasa Inggris,
misalnya "Iran (Islamic Republic of)". Plotly membutuhkan kode ISO-3 untuk choropleth, dan tampilan
aplikasi memakai nama Indonesia. Tabel ini ditulis manual agar tidak bergantung pada pustaka tambahan.

Beberapa baris STOP menyebut lebih dari satu negara (dipisah titik koma) karena satu pemutusan
melintasi perbatasan. Baris seperti itu dipetakan ke negara pertama dan diberi catatan.
"""

from __future__ import annotations

# nama di STOP -> (ISO-3, nama Indonesia, wilayah)
PETA_NEGARA: dict[str, tuple[str, str, str]] = {
    "Afghanistan": ("AFG", "Afganistan", "Asia"),
    "Albania": ("ALB", "Albania", "Eropa"),
    "Algeria": ("DZA", "Aljazair", "Afrika"),
    "Angola": ("AGO", "Angola", "Afrika"),
    "Armenia": ("ARM", "Armenia", "Asia"),
    "Azerbaijan": ("AZE", "Azerbaijan", "Asia"),
    "Bahrain": ("BHR", "Bahrain", "Timur Tengah"),
    "Bangladesh": ("BGD", "Bangladesh", "Asia"),
    "Belarus": ("BLR", "Belarus", "Eropa"),
    "Benin": ("BEN", "Benin", "Afrika"),
    "Brazil": ("BRA", "Brasil", "Amerika"),
    "Burkina Faso": ("BFA", "Burkina Faso", "Afrika"),
    "Burundi": ("BDI", "Burundi", "Afrika"),
    "Burundi; Kenya; Rwanda; Tanzania, United Republic of; Uganda": ("BDI", "Burundi", "Afrika"),
    "Cambodia": ("KHM", "Kamboja", "Asia"),
    "Cameroon": ("CMR", "Kamerun", "Afrika"),
    "Cameroon; Central African Republic": ("CMR", "Kamerun", "Afrika"),
    "Chad": ("TCD", "Chad", "Afrika"),
    "China": ("CHN", "Tiongkok", "Asia"),
    "Comoros": ("COM", "Komoro", "Afrika"),
    "Congo": ("COG", "Republik Kongo", "Afrika"),
    "Congo (Democratic Republic of the)": ("COD", "Republik Demokratik Kongo", "Afrika"),
    "Cuba": ("CUB", "Kuba", "Amerika"),
    "Côte d'Ivoire": ("CIV", "Pantai Gading", "Afrika"),
    "Ecuador": ("ECU", "Ekuador", "Amerika"),
    "Egypt": ("EGY", "Mesir", "Timur Tengah"),
    "El Salvador": ("SLV", "El Salvador", "Amerika"),
    "Equatorial Guinea": ("GNQ", "Guinea Khatulistiwa", "Afrika"),
    "Eritrea": ("ERI", "Eritrea", "Afrika"),
    "Eswatini": ("SWZ", "Eswatini", "Afrika"),
    "Ethiopia": ("ETH", "Etiopia", "Afrika"),
    "Gabon": ("GAB", "Gabon", "Afrika"),
    "Gambia": ("GMB", "Gambia", "Afrika"),
    "Guinea": ("GIN", "Guinea", "Afrika"),
    "Guinea-Bissau": ("GNB", "Guinea-Bissau", "Afrika"),
    "India": ("IND", "India", "Asia"),
    "Indonesia": ("IDN", "Indonesia", "Asia"),
    "Iran (Islamic Republic of)": ("IRN", "Iran", "Timur Tengah"),
    "Iraq": ("IRQ", "Irak", "Timur Tengah"),
    "Israel": ("ISR", "Israel", "Timur Tengah"),
    "Jordan": ("JOR", "Yordania", "Timur Tengah"),
    "Kazakhstan": ("KAZ", "Kazakhstan", "Asia"),
    "Kenya": ("KEN", "Kenya", "Afrika"),
    "Kyrgyzstan": ("KGZ", "Kirgizstan", "Asia"),
    "Laos; Myanmar": ("MMR", "Myanmar", "Asia"),
    "Latvia": ("LVA", "Latvia", "Eropa"),
    "Lebanon": ("LBN", "Lebanon", "Timur Tengah"),
    "Liberia": ("LBR", "Liberia", "Afrika"),
    "Libya": ("LBY", "Libya", "Afrika"),
    "Lithuania": ("LTU", "Lituania", "Eropa"),
    "Malawi": ("MWI", "Malawi", "Afrika"),
    "Malaysia": ("MYS", "Malaysia", "Asia"),
    "Mali": ("MLI", "Mali", "Afrika"),
    "Mauritania": ("MRT", "Mauritania", "Afrika"),
    "Mauritius": ("MUS", "Mauritius", "Afrika"),
    "Montenegro": ("MNE", "Montenegro", "Eropa"),
    "Morocco": ("MAR", "Maroko", "Afrika"),
    "Mozambique": ("MOZ", "Mozambik", "Afrika"),
    "Myanmar": ("MMR", "Myanmar", "Asia"),
    "Nepal": ("NPL", "Nepal", "Asia"),
    "New Caledonia": ("NCL", "Kaledonia Baru", "Oseania"),
    "Nicaragua": ("NIC", "Nikaragua", "Amerika"),
    "Niger": ("NER", "Niger", "Afrika"),
    "Nigeria": ("NGA", "Nigeria", "Afrika"),
    "North Korea": ("PRK", "Korea Utara", "Asia"),
    "Oman": ("OMN", "Oman", "Timur Tengah"),
    "Pakistan": ("PAK", "Pakistan", "Asia"),
    "Palestine, State of": ("PSE", "Palestina", "Timur Tengah"),
    "Panama": ("PAN", "Panama", "Amerika"),
    "Papua New Guinea": ("PNG", "Papua Nugini", "Oseania"),
    "Philippines": ("PHL", "Filipina", "Asia"),
    "Qatar": ("QAT", "Qatar", "Timur Tengah"),
    "Russian Federation": ("RUS", "Rusia", "Eropa"),
    "Saudi Arabia": ("SAU", "Arab Saudi", "Timur Tengah"),
    "Senegal": ("SEN", "Senegal", "Afrika"),
    "Sierra Leone": ("SLE", "Sierra Leone", "Afrika"),
    "Somaliland": ("SOM", "Somalia (Somaliland)", "Afrika"),
    "South Korea": ("KOR", "Korea Selatan", "Asia"),
    "South Sudan": ("SSD", "Sudan Selatan", "Afrika"),
    "Sri Lanka": ("LKA", "Sri Lanka", "Asia"),
    "Sudan": ("SDN", "Sudan", "Afrika"),
    "Suriname": ("SUR", "Suriname", "Amerika"),
    "Syrian Arab Republic": ("SYR", "Suriah", "Timur Tengah"),
    "Tajikistan": ("TJK", "Tajikistan", "Asia"),
    "Tanzania, United Republic of": ("TZA", "Tanzania", "Afrika"),
    "Togo": ("TGO", "Togo", "Afrika"),
    "Tunisia": ("TUN", "Tunisia", "Afrika"),
    "Turkey": ("TUR", "Turki", "Timur Tengah"),
    "Turkmenistan": ("TKM", "Turkmenistan", "Asia"),
    "Uganda": ("UGA", "Uganda", "Afrika"),
    "Ukraine": ("UKR", "Ukraina", "Eropa"),
    "United Arab Emirates": ("ARE", "Uni Emirat Arab", "Timur Tengah"),
    "United Kingdom": ("GBR", "Inggris", "Eropa"),
    "United States of America": ("USA", "Amerika Serikat", "Amerika"),
    "Uzbekistan": ("UZB", "Uzbekistan", "Asia"),
    "Venezuela (Bolivarian Republic of)": ("VEN", "Venezuela", "Amerika"),
    "Viet Nam": ("VNM", "Vietnam", "Asia"),
    "Yemen": ("YEM", "Yaman", "Timur Tengah"),
    "Zambia": ("ZMB", "Zambia", "Afrika"),
    "Zimbabwe": ("ZWE", "Zimbabwe", "Afrika"),
}

# kode ISO-2 (dipakai IODA) -> nama Indonesia, diturunkan dari tabel di atas + beberapa tambahan
ISO2_KE_ISO3: dict[str, str] = {
    "AF": "AFG", "AL": "ALB", "DZ": "DZA", "AO": "AGO", "AM": "ARM", "AZ": "AZE", "BH": "BHR", "BD": "BGD",
    "BY": "BLR", "BJ": "BEN", "BR": "BRA", "BF": "BFA", "BI": "BDI", "KH": "KHM", "CM": "CMR", "TD": "TCD",
    "CN": "CHN", "KM": "COM", "CG": "COG", "CD": "COD", "CU": "CUB", "CI": "CIV", "EC": "ECU", "EG": "EGY",
    "SV": "SLV", "GQ": "GNQ", "ER": "ERI", "SZ": "SWZ", "ET": "ETH", "GA": "GAB", "GM": "GMB", "GN": "GIN",
    "GW": "GNB", "IN": "IND", "ID": "IDN", "IR": "IRN", "IQ": "IRQ", "IL": "ISR", "JO": "JOR", "KZ": "KAZ",
    "KE": "KEN", "KG": "KGZ", "LV": "LVA", "LB": "LBN", "LR": "LBR", "LY": "LBY", "LT": "LTU", "MW": "MWI",
    "MY": "MYS", "ML": "MLI", "MR": "MRT", "MU": "MUS", "ME": "MNE", "MA": "MAR", "MZ": "MOZ", "MM": "MMR",
    "NP": "NPL", "NC": "NCL", "NI": "NIC", "NE": "NER", "NG": "NGA", "KP": "PRK", "OM": "OMN", "PK": "PAK",
    "PS": "PSE", "PA": "PAN", "PG": "PNG", "PH": "PHL", "QA": "QAT", "RU": "RUS", "SA": "SAU", "SN": "SEN",
    "SL": "SLE", "SO": "SOM", "KR": "KOR", "SS": "SSD", "LK": "LKA", "SD": "SDN", "SR": "SUR", "SY": "SYR",
    "TJ": "TJK", "TZ": "TZA", "TG": "TGO", "TN": "TUN", "TR": "TUR", "TM": "TKM", "UG": "UGA", "UA": "UKR",
    "AE": "ARE", "GB": "GBR", "US": "USA", "UZ": "UZB", "VE": "VEN", "VN": "VNM", "YE": "YEM", "ZM": "ZMB",
    "ZW": "ZWE",
}

_ISO3_KE_NAMA: dict[str, str] = {iso3: nama for iso3, nama, _ in PETA_NEGARA.values()}


def info_negara(nama_stop: str) -> tuple[str, str, str]:
    """Kembalikan (iso3, nama Indonesia, wilayah) untuk nama negara versi STOP.

    Nama yang tidak dikenal tetap dikembalikan apa adanya dengan iso3 kosong dan wilayah "Lainnya",
    sehingga pipeline tidak berhenti hanya karena Access Now menambah negara baru.
    """
    if nama_stop in PETA_NEGARA:
        return PETA_NEGARA[nama_stop]
    bersih = str(nama_stop).strip()
    if bersih in PETA_NEGARA:
        return PETA_NEGARA[bersih]
    # Baris multi-negara ("A; B"): pakai negara pertama
    pertama = bersih.split(";")[0].strip()
    if pertama in PETA_NEGARA:
        return PETA_NEGARA[pertama]
    return ("", bersih, "Lainnya")


def nama_dari_iso3(iso3: str, cadangan: str = "") -> str:
    """Nama Indonesia dari kode ISO-3; jika tidak ada di tabel, pakai `cadangan` (biasanya nama Inggris)."""
    return _ISO3_KE_NAMA.get(iso3, cadangan or iso3)


def nama_dari_iso2(iso2: str, cadangan: str = "") -> str:
    """Nama Indonesia dari kode ISO-2 (format IODA)."""
    return nama_dari_iso3(ISO2_KE_ISO3.get(iso2, ""), cadangan or iso2)
