# Sumber data & catatan metodologi

Dikompilasi 5 November 2026. Tiga sumber dipakai: catatan manusia (Access Now), pengukuran otomatis (IODA), dan
pembanding konflik bersenjata (UCDP).

## 1. Access Now #KeepItOn STOP (Shutdown Tracker Optimization Project)

| Hal | Keterangan |
|---|---|
| Sumber | https://www.accessnow.org/keepiton-data/ (tautan "spreadsheet" menuju Google Sheets publik) |
| Unduhan | Ekspor xlsx otomatis oleh `src/siapkan_data.py`, disimpan di `data/raw/` (diabaikan git) |
| Cakupan | Pemutusan dan pelambatan internet yang didokumentasikan 2016–2025, ditambah beberapa pemblokiran yang dimulai 2009–2013 dan masih berlangsung |
| Struktur | Satu lembar per tahun (2016 … 2025), 45 kolom, 2.102 baris total; lembar "Combined" hanya gabungan |
| Pembaruan terakhir | 31 Maret 2026 (lembar "Data updates (2026)") |
| Lisensi | Data publik; Access Now meminta atribusi "#KeepItOn, Access Now" |

Kutipan: Access Now & #KeepItOn coalition. *Internet shutdowns 2025 annual report* (Maret 2026) dan STOP dataset.

### Mengapa 2.102 baris menjadi 1.888 pemutusan

Lembar tahunan memuat **semua pemutusan yang aktif pada tahun itu**, termasuk yang dimulai tahun sebelumnya. Pemblokiran
Grindr di Indonesia (sejak 2016, masih berlangsung) muncul di sepuluh lembar sekaligus. `gabungkan_duplikat()`
menyatukan baris dengan kunci yang sama:

`country · start_date · area_name · shutdown_type · affected_network · shutdown_extent · actual_cause · other_affected`

Nilai yang dipakai adalah baris dari lembar **terbaru** (status dan tanggal selesai paling mutakhir). Lembar pertama dan
terakhir tempat baris itu muncul disimpan sebagai `tahun_laporan_awal` dan `tahun_laporan_akhir`, sehingga aplikasi
tetap bisa menghitung ala Access Now ("aktif pada tahun X"). Uji silang: jumlah "aktif" hasil rekonstruksi untuk
2025 = 313, sama dengan angka laporan tahunan Access Now; 2024 = 304; 2023 = 288 (lembar: 289).

### Kolom `data/shutdown_dunia.csv` (1.888 baris, 1,2 MB)

| Kolom | Asal (STOP) | Isi |
|---|---|---|
| `id` | – | nomor urut setelah penggabungan |
| `negara`, `iso3`, `wilayah`, `negara_en` | `country` | nama Indonesia, kode ISO-3, wilayah (Asia/Afrika/Eropa/Amerika/Timur Tengah/Oseania), nama asli; pemetaan di `src/negara.py` |
| `tahun`, `mulai`, `selesai` | `start_date`, `end_date` | tahun mulai dan tanggal |
| `durasi_hari` | dihitung | `selesai − mulai + 1`; jika `selesai` kosong, dipakai kolom `duration` STOP (satuan hari); kosong jika keduanya tidak ada |
| `status` | `shutdown_status`, `end_date` | Selesai / Berlangsung / Tidak diketahui. Baris yang punya tanggal selesai selalu "Selesai" |
| `tahun_laporan_awal`, `tahun_laporan_akhir` | nama lembar | rentang lembar tahunan tempat pemutusan tercatat |
| `cakupan_wilayah` | `geo_scope` | Satu kota/kabupaten · Beberapa kota, satu provinsi · Lintas provinsi / nasional |
| `daerah` | `area_name` | nama daerah apa adanya (Inggris), dipotong 160 karakter |
| `jenis` | `shutdown_type` | Pemutusan · Pelambatan · Pemutusan & pelambatan |
| `jaringan` | `affected_network` | Broadband & seluler · Seluler · Broadband |
| `cakupan_layanan` | `shutdown_extent` | Seluruh jaringan · Platform tertentu · Jaringan + platform |
| `pemicu` | `actual_cause` | lihat tabel terjemahan di bawah |
| `alasan_pemerintah` | `gov_justification` | pernyataan resmi, bila ada |
| `diperintahkan_oleh` | `ordered_by` | Pemerintah pusat · negara bagian/provinsi · daerah · Militer · Kepolisian · Pengadilan · Non-pemerintah |
| `pemilu`, `kekerasan`, `pelanggaran_ham` | `election`, `violence`, `hr_abuse_reported` | Ya / Tidak / Tidak diketahui |
| `platform` | `*_affected`, `other_affected` | daftar platform yang diblokir, dipisah `;` |
| `keterangan` | `event` | ringkasan peristiwa versi Access Now (Inggris), dipotong 600 karakter |
| `sumber_url` | `info_source_link` | tautan sumber |
| `tanggal_perkiraan` | `start_date_type` | True jika tanggal mulai hanya perkiraan |

Terjemahan pemicu (`actual_cause`):

| STOP | Di aplikasi |
|---|---|
| Protests | Unjuk rasa |
| Conflict | Konflik bersenjata |
| Communal violence | Kekerasan komunal |
| Political instability | Instabilitas politik |
| Elections | Pemilu |
| Information control | Kontrol informasi |
| Exam cheating | Ujian sekolah |
| Religious holiday/anniversary | Hari besar/peringatan |
| Visits by government officials | Kunjungan pejabat |
| Other / Unknown | Lainnya / Tidak diketahui |

Kolom STOP yang **tidak** dibawa: `decision_maker`, `actual_cause_details`, `gov_just_details`, `legal_just`,
`legal_method`, `gov_ack*`, `telco*`, `users_*`, `econ_impact`, `an_link`, `info_source`. Semuanya tersedia di
spreadsheet asli bila diperlukan.

## 2. IODA (Internet Outage Detection and Analysis), Georgia Tech

| Hal | Keterangan |
|---|---|
| Sumber | https://ioda.inetintel.cc.gatech.edu/ · API https://api.ioda.inetintel.cc.gatech.edu/v2/ |
| Akses | Publik, tanpa API key. Hak cipta data: Georgia Tech Research Corporation |
| Endpoint dipakai | `/outages/summary` (skor per negara dalam satu jendela), `/outages/events` (daftar kejadian), `/signals/raw/country/{kode}` (deret waktu) |
| Sinyal | `bgp` (blok /24 teriklan), `ping-slash24` (blok /24 yang membalas ping), `merit-nt` (teleskop jaringan Merit), `gtr` (Google Transparency Report) |
| Cache | Aplikasi memanggil live dengan `st.cache_data(ttl=3600)`; bila gagal memakai potret di `data/ioda_*.csv` |

Potret yang disimpan skrip ETL (diperbarui tiap Senin oleh GitHub Actions):

| File | Isi |
|---|---|
| `ioda_ringkasan_30hari.csv` | negara dengan gangguan terdeteksi 30 hari terakhir: jumlah kejadian, skor total dan per sinyal |
| `ioda_kejadian_dunia_30hari.csv` | sampai 500 kejadian tingkat negara 30 hari terakhir |
| `ioda_kejadian_indonesia.csv` | kejadian tingkat negara untuk Indonesia 12 bulan terakhir |
| `ioda_sinyal_indonesia_7hari.csv` | deret waktu 4 sinyal Indonesia 7 hari terakhir (resolusi 30 menit) |

Catatan: sinyal `gtr` turun setiap malam dan akhir pekan secara alami. Skor IODA tidak bersatuan dan hanya berguna
untuk membandingkan. Deteksi tingkat negara tidak menangkap pelambatan atau pemblokiran satu aplikasi.

## 3. UCDP via global-conflict-tracker

`korban_konflik_negara_tahun.csv` (706 baris) adalah agregasi korban konflik bersenjata per negara-tahun 2016–2026,
diturunkan dari `korban_negara_tahun.csv` di repositori
[Avalon2222/global-conflict-tracker](https://github.com/Avalon2222/global-conflict-tracker) (UCDP GED 26.1 +
Candidate, CC BY 4.0). Kolom: `iso3`, `negara`, `tahun`, `kejadian`, `korban` (estimasi *best*), `korban_sipil`.
Dipakai hanya untuk tab *Shutdown vs konflik*; ambang 25 korban/tahun mengikuti definisi konflik UCDP.

## 4. Sumber yang sengaja tidak dipakai

- **Cloudflare Radar** (`/radar/annotations/outages`) memerlukan API token Cloudflare. Datanya bagus untuk 2022 ke atas,
  tetapi aplikasi ini sengaja hanya memakai sumber tanpa kunci agar siapa pun bisa menjalankannya.
- **NetBlocks** tidak menyediakan API atau unduhan terstruktur.
- **OONI** mengukur pemblokiran per situs/aplikasi, berbeda jenis data; menjadi kandidat pengembangan berikutnya.

## Keterbatasan

1. Hanya pemutusan yang **terdokumentasi** yang masuk. Negara tertutup hampir pasti kurang terwakili.
2. India mendominasi (908 dari 1.888) karena pemutusan tingkat distrik dicatat satu per satu.
3. 524 pemutusan tidak diketahui durasinya; total "hari gelap" adalah batas bawah.
4. `pemicu` adalah penilaian Access Now atas konteks, bukan pernyataan pemerintah; `alasan_pemerintah` adalah sebaliknya.
5. Baris multi-negara (misalnya "Burundi; Kenya; Rwanda; …") dipetakan ke negara pertama.
6. Korelasi dengan korban konflik adalah korelasi tingkat negara-tahun, bukan hubungan sebab-akibat.
