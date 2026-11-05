# 🏋️ Latihan

Kerjakan berurutan; tiap latihan memakai apa yang dibangun latihan sebelumnya. ⭐ = 15–30 menit, ⭐⭐ = sekitar 1 jam,
⭐⭐⭐ = setengah hari. Kunci jawaban ada di bawah setiap soal; coba dulu tanpa membukanya.

---

### Latihan 1 — Mengubah nilai bawaan filter ⭐

Ubah agar aplikasi dibuka dengan rentang tahun 2019–2025 dan hanya pemicu yang berkaitan dengan kerusuhan
(`analisis.PEMICU_KERUSUHAN`).

<details><summary>Kunci</summary>

Di `app.py`, bagian sidebar:

```python
tahun_awal, tahun_akhir = st.slider("Rentang tahun", TAHUN_MIN, TAHUN_MAX, (2019, TAHUN_MAX))
pemicu_pilihan = st.multiselect("Pemicu", URUTAN_PEMICU, default=analisis.PEMICU_KERUSUHAN, ...)
```
</details>

---

### Latihan 2 — KPI baru: rata-rata durasi pemutusan jaringan penuh ⭐

Tambahkan metric keenam: rata-rata `durasi_hari` khusus baris dengan `cakupan_layanan == "Seluruh jaringan"` yang
durasinya diketahui. Tulis dulu fungsinya di `analisis.py`, lalu tesnya, baru tampilkan.

<details><summary>Kunci</summary>

```python
# src/analisis.py
def rata_durasi_jaringan_penuh(df: pd.DataFrame) -> float:
    penuh = df[(df["cakupan_layanan"] == "Seluruh jaringan") & df["durasi_hari"].notna()]
    return float(penuh["durasi_hari"].mean()) if len(penuh) else 0.0

# tests/test_analisis.py
def test_rata_durasi_jaringan_penuh(df_kecil):
    # baris 1,2,3,6 = seluruh jaringan dengan durasi: 213, 3, 15, 1 -> rata-rata 58
    assert analisis.rata_durasi_jaringan_penuh(df_kecil) == pytest.approx(58.0)

# app.py
k6.metric("Rata-rata durasi (jaringan penuh)", f"{analisis.rata_durasi_jaringan_penuh(df):.1f} hari")
```
</details>

---

### Latihan 3 — Fungsi baru + tesnya: negara dengan kenaikan terbesar ⭐⭐

Buat `kenaikan_terbesar(df, tahun_a, tahun_b, n=5)` yang mengembalikan n negara dengan selisih jumlah pemutusan
terbesar antara dua tahun. Negara yang tidak punya pemutusan pada salah satu tahun harus dihitung 0, bukan hilang.

<details><summary>Kunci</summary>

```python
def kenaikan_terbesar(df: pd.DataFrame, tahun_a: int, tahun_b: int, n: int = 5) -> pd.DataFrame:
    hitung = df[df["tahun"].isin([tahun_a, tahun_b])].groupby(["negara", "tahun"]).size().unstack(fill_value=0)
    for th in (tahun_a, tahun_b):
        if th not in hitung.columns:
            hitung[th] = 0
    hitung["selisih"] = hitung[tahun_b] - hitung[tahun_a]
    return hitung.sort_values("selisih", ascending=False).head(n).reset_index()
```

Tes dengan `df_kecil`: antara 2019 dan 2021, Myanmar naik dari 0 ke 2 (selisih +2), India tetap (1 → 1), Indonesia
turun (1 → 0). `unstack(fill_value=0)` adalah kuncinya; tanpa itu Myanmar 2019 menjadi NaN.
</details>

---

### Latihan 4 — Pemutusan per juta pengguna internet ⭐⭐

India "menang" karena penduduknya banyak dan dokumentasinya rapi. Unduh jumlah pengguna internet per negara dari World
Bank (indikator `IT.NET.USER.ZS` × populasi `SP.POP.TOTL`, API `https://api.worldbank.org/v2/country/all/indicator/...?format=json`),
simpan sebagai `data/pengguna_internet.csv` (`iso3`, `tahun`, `pengguna`), lalu tambahkan pilihan metrik ketiga di
peta: pemutusan per 10 juta pengguna.

<details><summary>Kunci (garis besar)</summary>

1. Skrip kecil `scripts/ambil_worldbank.py` yang memanggil API dengan `per_page=20000`, mengambil elemen `[1]` dari
   JSON, dan menyimpan `countryiso3code`, `date`, `value`.
2. Di `analisis.per_negara`, terima argumen opsional `pengguna` (DataFrame) dan tambahkan kolom
   `per_10jt = jumlah / (pengguna_terakhir / 1e7)`.
3. Di app, tambahkan opsi radio `"per_10jt"` dan pakai skala log juga.

Hasil yang menarik: Myanmar, Sudan Selatan, dan Etiopia melesat ke atas; India turun jauh.
</details>

---

### Latihan 5 — Sinyal IODA tingkat provinsi untuk Papua ⭐⭐⭐

IODA punya entitas *region*. Kode Papua = 1745, Jakarta Raya = 1719 (cari lewat
`/entities/query?entityType=region&search=Papua`). Tambahkan di tab Indonesia sebuah selectbox provinsi dan gambar
sinyal 7 harinya, memakai pola `ioda_aman` yang sama.

<details><summary>Kunci (garis besar)</summary>

```python
# src/ioda.py
def ambil_sinyal_region(kode_region: str, hari: int = 7, maks_titik: int = 400) -> pd.DataFrame:
    dari, sampai = _jendela(hari)
    hasil = _get(f"/signals/raw/region/{kode_region}", {"from": dari, "until": sampai, "maxPoints": maks_titik})
    return urai_sinyal(hasil.get("data", []))
```

Di app: `REGION_ID = {"Papua": "1745", "Jakarta Raya": "1719", ...}`, tambahkan kunci baru di dict `fungsi`/`potret`
milik `ioda_aman`, dan simpan potret `data/ioda_sinyal_papua_7hari.csv` lewat `siapkan_data.potret_ioda`. Jangan lupa
menambahkan tes untuk kunci baru itu (cukup pastikan `urai_sinyal` masih dipakai).

Catatan: sinyal tingkat provinsi jauh lebih "berisik" (sedikit blok /24), jadi pertimbangkan rata-rata bergerak
`rolling(6)` sebelum menggambar.
</details>

---

### Latihan 6 — Peringatan otomatis saat sinyal Indonesia anjlok ⭐⭐⭐

Buat skrip `scripts/pantau.py` yang mengambil sinyal BGP dan ping Indonesia 6 jam terakhir, menghitung rasio nilai
terakhir terhadap median 7 hari, dan keluar dengan kode 1 jika rasio < 0,7. Jalankan tiap jam lewat GitHub Actions
(`schedule: cron: "0 * * * *"`), dan buat workflow membuka *issue* otomatis bila skrip gagal
(`actions/github-script` atau `peter-evans/create-issue-from-file`).

<details><summary>Kunci (garis besar)</summary>

```python
# scripts/pantau.py
from src import ioda
sinyal = ioda.normalisasi_sinyal(ioda.ambil_sinyal("ID", hari=7))
terakhir = sinyal.sort_values("waktu").groupby("sumber").tail(12)       # 6 jam terakhir, resolusi 30 menit
rasio = terakhir.groupby("sumber")["relatif"].median()
anjlok = rasio[rasio.index.isin(["bgp", "ping-slash24"])] < 0.7
print(rasio.round(2).to_dict())
raise SystemExit(1 if anjlok.any() else 0)
```

Di workflow, langkah setelahnya memakai `if: failure()` untuk membuka issue berjudul "Sinyal Indonesia anjlok" berisi
output skrip. Uji dulu ambang 0,7 terhadap data seminggu supaya tidak terlalu sering salah alarm (trafik Google turun
tiap malam, karena itu hanya BGP dan ping yang dipakai).
</details>
