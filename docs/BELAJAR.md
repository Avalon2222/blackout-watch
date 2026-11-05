# 🎓 Panduan Belajar: Dari Spreadsheet Access Now ke Peta Pemutusan Internet

Panduan ini ditulis untuk kamu yang sudah bisa Python dasar (variabel, fungsi, list, dict) dan ingin mengerti setiap
baris proyek ini, bukan hanya menjalankannya. Total waktu sekitar 4 jam jika dikerjakan sambil membuka kodenya.

Yang akan kamu pelajari:

1. Membaca spreadsheet multi-lembar dan menyadari bahwa datanya "berbohong" (duplikat lintas tahun).
2. Membangun ETL kecil: unduh → bersihkan → simpan, dengan fungsi murni yang bisa diuji.
3. Choropleth dengan skala log, Sankey, Gantt, dan scatter log-log di Plotly.
4. Memanggil API publik (IODA) dengan cache dan cadangan supaya aplikasi tidak pernah error.
5. Menggabungkan dua dataset yang tidak saling kenal lewat kunci ISO-3 + tahun.

## Gambaran besar: 4 lapisan kode

```
data mentah (xlsx, JSON API)  ──►  src/siapkan_data.py  ──►  data/*.csv
                                   src/ioda.py
                                            │
                       src/muat_data.py  ◄──┘        baca + validasi
                                │
                       src/analisis.py                hitung (pandas murni, diuji)
                                │
                             app.py                   tampilkan (Streamlit + Plotly)
```

Aturan yang dipegang: **app.py tidak pernah menghitung**. Ia hanya memanggil fungsi di `analisis.py` dan menggambar.
Dengan begitu `analisis.py` bisa diuji oleh pytest tanpa membuka browser.

---

## Bagian 1 — Mengenal data Access Now (30 menit)

Buka spreadsheet STOP dari https://www.accessnow.org/keepiton-data/. Ada sepuluh lembar bernama tahun (2016 … 2025)
dengan 45 kolom yang sama. Coba jawab tiga pertanyaan sebelum lanjut:

1. Lembar 2025 punya 313 baris. Apakah itu berarti 313 pemutusan *dimulai* pada 2025?
2. Baris Iran paling atas bertanggal mulai 24 Mei 2009 dan muncul di **semua** lembar. Mengapa?
3. Kolom `actual_cause` dan `gov_justification` keduanya tentang "sebab". Apa bedanya?

Jawabannya: (1) tidak, lembar tahunan memuat semua pemutusan yang *aktif* pada tahun itu; (2) karena pemblokiran
Facebook/Twitter di Iran belum dicabut, jadi ia aktif di setiap tahun; (3) `actual_cause` adalah penilaian Access Now
atas konteks (demonstrasi, perang), `gov_justification` adalah kata pemerintah ("hoaks", "keamanan").

Latihan kecil di Python:

```python
import pandas as pd
xlsx = pd.ExcelFile("data/raw/keepiton_stop.xlsx")
for nama in xlsx.sheet_names:
    print(nama, len(xlsx.parse(nama)))
df25 = xlsx.parse("2025")
print(df25["actual_cause"].value_counts())
print(df25[df25["country"] == "Indonesia"][["start_date", "area_name", "actual_cause", "event"]])
```

---

## Bagian 2 — ETL: mengapa 2.102 baris menjadi 1.888 (45 menit)

Buka `src/siapkan_data.py`. Tiga fungsi murni yang perlu kamu pahami:

### `baca_gabungan`

Membaca tiap lembar tahunan dan menambahkan kolom `tahun_laporan` = nama lembar. Lembar "Combined" sengaja tidak
dipakai karena ia membuang informasi dari lembar mana sebuah baris berasal.

### `gabungkan_duplikat`

Inti masalahnya: satu pemutusan bisa muncul di beberapa lembar. Kita butuh **kunci** yang sama untuk baris yang sama:

```python
KUNCI_UNIK = ["country", "start_date", "area_name", "shutdown_type", "affected_network",
              "shutdown_extent", "actual_cause", "other_affected"]
grup = kerja.sort_values(["tahun_laporan"]).groupby(KUNCI_UNIK)
terakhir = grup.tail(1)                                   # baris dari lembar paling baru
rentang = grup["tahun_laporan"].agg(["min", "max"])       # lembar pertama & terakhir ia muncul
```

Mengapa `tail(1)`? Lembar terbaru berisi status dan tanggal selesai yang paling mutakhir. Mengapa menyimpan
`min`/`max`? Supaya nanti kita masih bisa menghitung "berapa pemutusan aktif pada 2023" tanpa data aslinya.

Uji silang yang meyakinkan: setelah penggabungan, `aktif_per_tahun` untuk 2025 menghasilkan 313, persis angka laporan
resmi Access Now. Kalau kunci kita terlalu longgar (menggabungkan dua pemutusan berbeda), angka itu akan turun; kalau
terlalu ketat, akan naik.

### `rapikan` dan `hitung_durasi`

Terjemahan kategori dilakukan lewat dict (`PEMICU`, `ALASAN`, `JENIS`, …) dan fungsi kecil `_peta()` yang memberi
nilai bawaan jika kosong. Durasi dihitung dari tanggal bila lengkap; jika tidak, dari kolom `duration` (satuan hari);
jika tidak ada juga, `NaN`. Perhatikan `+ 1`: pemutusan 22 Agustus sampai 22 Agustus adalah 1 hari, bukan 0.

Jalankan tes yang menjaga ketiga fungsi itu:

```bash
python -m pytest tests/ -k "durasi or duplikat or rapikan" -v
```

---

## Bagian 3 — Analisis dan tesnya (45 menit)

Buka `src/analisis.py` dan `tests/test_analisis.py` berdampingan. Perhatikan pola yang sama di setiap tes: buat
DataFrame kecil (6 baris) yang jawabannya bisa dihitung di kepala, panggil fungsi, bandingkan.

### `filter_data` dengan dua "dasar tahun"

```python
if dasar_tahun == "aktif":
    topeng = (df["tahun_laporan_awal"] <= tahun_akhir) & (df["tahun_laporan_akhir"] >= tahun_awal)
else:
    topeng = df["tahun"].between(tahun_awal, tahun_akhir)
```

Dua rentang `[a, b]` dan `[c, d]` bersinggungan jika `a <= d` dan `b >= c`. Rumus ini muncul di mana-mana (jadwal,
reservasi, Gantt), jadi layak dihafal.

### `per_negara` dan pemicu dominan

```python
utama = grup["pemicu"].agg(lambda s: s.value_counts().index[0])
```

`value_counts()` mengurutkan dari yang terbanyak, `.index[0]` mengambil labelnya. Satu baris pandas menggantikan loop
dan dict counter manual.

### `gabung_konflik` dan bahaya `inner join`

Dua dataset digabung dengan `merge(on=["iso3", "tahun"], how="outer")`. Coba ganti `outer` menjadi `inner` lalu lihat
tab *Shutdown vs konflik*: kelompok "konflik tanpa pemutusan" lenyap, dan kesimpulanmu berubah total. Pilihan jenis
join adalah keputusan analitis, bukan sekadar teknis.

### Menjalankan dan membaca tes

```bash
python -m pytest tests/ -v
```

Coba rusak satu fungsi (misalnya hapus `+ 1` di `hitung_durasi`) dan lihat tes mana yang gagal dan apa pesannya.

---

## Bagian 4 — Tampilan (60 menit)

### Choropleth dengan skala log

Plotly mengenali negara dari kode ISO-3. Karena India punya 900-an pemutusan dan negara ke-10 hanya 30-an, warnanya
dihitung dari `log10`, lalu colorbar diberi label asli dengan `tickvals`/`ticktext` supaya pembaca tidak perlu tahu
tentang log:

```python
peta["log"] = np.log10(peta["jumlah"].clip(lower=1))
fig.update_layout(coloraxis_colorbar=dict(tickvals=np.log10(tik), ticktext=[str(t) for t in tik]))
```

### Sankey: dua kolom kategori menjadi aliran

Sankey butuh tiga list: `source`, `target`, `value`, semuanya berupa indeks node. Triknya adalah membuat satu list
`label` berisi semua pemicu lalu semua alasan, dan dict `idx = {nama: posisi}`:

```python
label = kiri_label + kanan_label
idx = {n: i for i, n in enumerate(label)}
go.Sankey(node=dict(label=label), link=dict(source=[idx[p] for p in pasangan["pemicu"]],
                                           target=[idx[a] for a in pasangan["alasan_pemerintah"]],
                                           value=pasangan["jumlah"]))
```

Pasangan yang sangat kecil disaring (`minimal=`) agar diagram tidak jadi benang kusut.

### Gantt yang jujur

`px.timeline` menggambar bar dari `x_start` ke `x_end`. Pemutusan 4 hari pada sumbu 10 tahun lebarnya 1 piksel, jadi
di tab Indonesia ditambahkan penanda wajik (`go.Scatter(mode="markers")`) di tanggal mulai. Pemutusan yang masih
berlangsung ditarik sampai akhir tahun laporan terakhirnya; keputusan itu ada di `analisis.linimasa`, bukan di app.

### Scatter log-log dengan nol

Sumbu log tidak bisa menggambar nol. Negara-tahun tanpa pemutusan digambar di 0,5 (`clip(lower=0.5)`) dan hal itu
dituliskan di caption. Menyembunyikan nol akan menghilangkan justru kelompok yang paling menarik.

### Caching dan cadangan untuk API

```python
@st.cache_data(ttl=3600, show_spinner=False)
def ioda_aman(nama, **kw):
    try:
        return fungsi(**kw), "live"
    except Exception:
        return muat_data.muat_potret_ioda(potret), "potret"
```

`ttl=3600` berarti satu jam semua pengunjung memakai hasil yang sama (IODA tidak dibombardir). `try/except` yang
mengembalikan potret berarti halaman tetap tampil ketika IODA lambat. Fungsi `urai_*` di `src/ioda.py` sengaja
dipisah dari fungsi jaringan supaya bisa diuji dengan JSON buatan.

---

## Bagian 5 — Eksperimen kecil (30 menit)

1. Di sidebar, matikan semua pemicu kecuali "Ujian sekolah". Negara mana saja? Tahun berapa puncaknya?
2. Aktifkan "Hitung yang masih berjalan dari tahun sebelumnya" dan bandingkan KPI "Pemutusan tercatat" sebelum dan
   sesudah. Dari mana selisihnya?
3. Di tab Tren, pilih negara Iran pada Gantt. Temukan pemutusan November 2019 dan baca sumbernya.
4. Di tab Live, tekan Refresh, lalu bandingkan dengan https://ioda.inetintel.cc.gatech.edu/dashboard. Sama?
5. Ubah `minimal=` pada Sankey menjadi 1. Apa yang terjadi pada keterbacaan diagram?

## Bacaan lanjutan

- Metodologi STOP Access Now: https://www.accessnow.org/keepiton-data-methodology/
- Dokumentasi IODA dan penjelasan tiap sinyal: https://ioda.inetintel.cc.gatech.edu/
- Plotly: `px.choropleth`, `go.Sankey`, `px.timeline`, `px.scatter_geo`.
- Pandas: `groupby().agg`, `merge(how=...)`, `where`, `clip`, `between`.
