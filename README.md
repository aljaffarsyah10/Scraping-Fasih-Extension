# 🏢 Fasih SM (BPS) Scraping & Building Summary System

Repositori ini menyediakan solusi lengkap untuk ekstraksi (*scraping*), audit, dan analisis data penugasan (*assignment*) survei ekonomi **SE2026** dari portal **Fasih SM BPS** (khususnya wilayah **Kabupaten Kepulauan Siau Tagulandang Biaro - 7108**).

Sistem ini mencakup dua pilar utama:
1. **Python Data Pipeline (CLI & Analytics):** Pipeline penarikan data skala besar (35.585+ data), algoritma penanganan limit Elasticsearch server, dan mesin kalkulasi **Rekapitulasi Jumlah Bangunan Fisik Riil per SLS**.
2. **Browser Extension (Manifest V3):** Ekstensi peramban siap pakai untuk ekspor langsung dari browser (dokumentasi terpisah di [fasih-assignment-scraper/README.md](fasih-assignment-scraper/README.md)).

---

## 📌 Ringkasan Hasil Data Kabupaten Sitaro (SE2026)

Dengan arsitektur sharding dinamis, sistem berhasil menarik **100% data** tanpa ada satu pun baris data yang terlewat:

| Metrik | Angka Server BPS | Hasil di Master Data | Keterangan |
| :--- | :---: | :---: | :--- |
| **Total Assignment (Keluarga/Usaha)** | **35.585** | **35.585** | **100.0% Terpenuhi (Lengkap)** |
| **Total Bangunan Fisik Riil** | - | **21.731** | Dihitung dengan metode *Count Distinct* per SLS |
| **Satuan Lingkungan Setempat (SLS)** | - | **400 SLS** | Terpetakan di 10 kecamatan & tingkat kab |

### Tabel Rekapitulasi per Kecamatan

| Kode Wilayah | Nama Kecamatan | Total Assignment | Total Bangunan Fisik Riil | Rasio Keluarga / Bangunan |
| :---: | :--- | :---: | :---: | :---: |
| `7108000` | *Tingkat Kabupaten (EC / Non-SLS)* | 77 | 0 *(Non-fisik)* | - |
| `7108100` | **BIARO** | 1.572 | **913** | 1.72 |
| `7108030` | **SIAU BARAT** | 5.198 | **2.788** | 1.86 |
| `7108050` | **SIAU BARAT SELATAN** | 2.421 | **1.503** | 1.61 |
| `7108060` | **SIAU BARAT UTARA** | 1.876 | **1.187** | 1.58 |
| `7108040` | **SIAU TENGAH** | 998 | **628** | 1.59 |
| `7108020` | **SIAU TIMUR** | 8.813 | **5.613** | 1.57 |
| `7108010` | **SIAU TIMUR SELATAN** | 4.290 | **2.630** | 1.63 |
| `7108070` | **TAGULANDANG** | 6.026 | **3.784** | 1.59 |
| `7108090` | **TAGULANDANG SELATAN** | 2.308 | **1.382** | 1.67 |
| `7108080` | **TAGULANDANG UTARA** | 2.006 | **1.303** | 1.54 |
| **TOTAL** | **KAB. SITARO** | **35.585** | **21.731** | **1.64** |

---

## 🗂️ Struktur Direktori Proyek

```text
D:\10Project\Scraping-Fasih\
│
├── output/                                              # 📁 FOLDER OUTPUT HASIL AKHIR
│   ├── Master_Rekap_Bangunan_SE2026_Sitaro.xlsx         # 📊 Master Workbook Excel (Rekap SLS + 35k Data)
│   ├── Master_Data_Assignment_SE2026_Sitaro.csv         # 📄 Master Dataset CSV (35.585 baris data)
│   └── raw_archive/                                     # 📦 Arsip CSV mentah historis
│       ├── Raw_Assignment_SE2026_Full_20261118_130132.csv (103 MB)
│       └── ...
│
├── scripts/                                             # 🛠️ SKRIP PENDUKUNG & AUDIT
│   ├── audit_server_exact.py                            # Verifikasi jumlah total hit & agregasi status server
│   ├── compare_server_master.py                         # Cek silang data server vs data lokal per kecamatan
│   ├── harvest_100_percent_sitaro.py                    # Mesin dynamic sharding untuk menarik 100% data
│   ├── export_rekap_final.py                            # Generator file Excel master berformat rapi
│   ├── fetch_complete_35k.py                            # Penarikan berbasis partisi status & wilayah
│   └── diagnosa_open.py                                 # Diagnosa penugasan status OPEN
│
├── fasih_scraper.py                                     # 🚀 Skrip CLI scraper mandiri (Python)
├── rekap_bangunan_sls.py                                # 🏢 Kalkulator Rekapitulasi Bangunan Fisik Riil SLS
├── fresh_cookie.txt                                     # 🔑 Penyimpan header cookie sesi Fasih aktif
├── PRD and playbook.md                                  # 📋 Dokumen PRD dan spesifikasi teknis
│
└── fasih-assignment-scraper/                            # 🧩 Folder Ekstensi Browser Chrome (Manifest V3)
```

---

## ⚙️ Logika Teknis & Solusi Masalah

### 1. Masalah Batas Elasticsearch Fasih SM (`max_result_window = 1000`)
Backend Fasih SM membatasi hasil paginasi data hingga maksimal **1.000 item per kueri** (`start < 1000`). Jika parameter `start >= 1000`, server otomatis mengembalikan `searchData: []` dan `totalHit: 0`.

* **Dampak:** Desa-desa berpenduduk padat (seperti Kelurahan *Balehumara*, *Paniki*, *Tarorane*, *Tatehadeng*, dan *Akesimbeka*) yang memiliki $> 1.000$ s.d. $1.600$ penugasan akan terpotong datanya jika ditarik per desa.
* **Solusi (`scripts/harvest_100_percent_sitaro.py`):**
  Sistem secara otomatis mendeteksi desa dengan `totalHit > 1000`, lalu melakukan **Dynamic Sharding per SLS** (`0000` s.d. `0025`). Setiap SLS rata-rata hanya memiliki 30–300 data, sehingga tidak pernah menyentuh limit 1.000 dan seluruh 35.585 data berhasil terambil 100%.

### 2. Penghitungan Bangunan Fisik Riil (`rekap_bangunan_sls.py`)
Dalam sensus/survei, nomor bangunan fisik dicatat di kolom `data3` (contoh: `"13 / "` atau `"15 / 13084791"`):
- **Bukan Sekadar Nomor Terbesar (Max):** Nomor urut bangunan di lapangan dapat melompat/terlewat akibat dinamika lapangan. Mengambil nilai Max akan menghasilkan angka semu yang berlebih.
- **Bukan Jumlah Baris Penugasan:** Beberapa keluarga/usaha dapat bertempat tinggal di dalam 1 bangunan fisik yang sama (1 bangunan fisik dihuni 2 keluarga). Menghitung total baris akan menyebabkan *double counting*.
- **Metode yang Digunakan:**
  1. Membersihkan string nomor bangunan murni (memotong karakter setelah garis miring `/`).
  2. Melakukan operasi **`COUNT DISTINCT`** pada nomor bangunan bersih di setiap SLS.
  3. Mengurutkan daftar nomor bangunan secara alfanumerik (`1, 2, 3, ..., 13, 13A, 13B`) dengan tuple sorting agar terhindar dari *TypeError*.

---

## 🚀 Panduan Menjalankan Script Python

Pastikan dependensi Python telah terpasang:
```bash
pip install pandas openpyxl requests urllib3
```

### A. Menjalankan Rekapitulasi Bangunan Fisik
Untuk menghitung ulang rekapitulasi bangunan fisik riil per SLS dari dataset master:
```bash
python rekap_bangunan_sls.py
```
*Skrip otomatis membaca [output/Master_Data_Assignment_SE2026_Sitaro.csv](output/Master_Data_Assignment_SE2026_Sitaro.csv) dan menghasilkan rekapitulasi ke format Excel.*

### B. Memeriksa Audit Status Server Fasih
Untuk mengecek agregasi seluruh status penugasan yang tercatat di server BPS:
```bash
python scripts/audit_server_exact.py
```

### C. Menjalankan Pengecekan Selisih Server vs Master Lokal
Untuk membandingkan jumlah data di server BPS dengan file lokal kita per kecamatan:
```bash
python scripts/compare_server_master.py
```

### D. Autentikasi Otomatis SSO BPS & Dukungan 2FA / OTP
Kini Anda **tidak perlu lagi menyalin cookie manual dari DevTools browser**. Sistem telah dilengkapi modul `auth_manager.py` berbasis Playwright yang otomatis menangani autentikasi SSO BPS beserta verifikasi dua langkah (2FA / OTP):

#### 1. Menjalankan Scraper dengan Prompt Interaktif:
Cukup jalankan perintah berikut, lalu masukkan username dan password ketika diminta (password disamarkan demi keamanan):
```bash
python fasih_scraper.py --minimal
```
*Jika terdeteksi halaman 2FA / OTP, konsol terminal akan meminta Anda memasukkan 6 digit kode dari Google Authenticator / FreeOTP di HP Anda, atau Anda dapat mengetikkannya langsung pada jendela Chrome yang terbuka.*

#### 2. Auto-Generate OTP Otomatis 100% via Secret Key (Zero Friction):
Jika Anda memiliki **Secret Key Base32** (kunci rahasia yang biasa diberikan saat awal memasang Authenticator di SSO BPS), sistem dapat **meng-generate kode OTP secara otomatis** tanpa Anda perlu membuka HP:
```bash
python auth_manager.py -u "username_sso" -p "password_sso" --otp-secret "JBSWY3DPEHPK3PXP" --save
```
*Setelah tersimpan di `config_account.json` (lokal), setiap kali cookie kedaluwarsa sistem akan login dan mengisikan OTP secara otomatis tanpa interupsi!*

#### 3. Menjalankan Scraper dengan Argumen Kode OTP Langsung:
```bash
python fasih_scraper.py -u "username_sso" -p "password_sso" --otp "123456" --minimal
```

#### 4. Menjalankan Harvester 100% Data:
```bash
python scripts/harvest_100_percent_sitaro.py
```
*Jika cookie di `fresh_cookie.txt` masih aktif, proses berjalan langsung tanpa membuka browser. Begitu kedaluwarsa, modul auto-login akan aktif secara otomatis.*

---

## 📊 Format Output Data

### 1. Excel Master ([output/Master_Rekap_Bangunan_SE2026_Sitaro.xlsx](output/Master_Rekap_Bangunan_SE2026_Sitaro.xlsx))
- **Sheet `Rekap_Bangunan_per_SLS`:**
  - `nama_kecamatan`, `nama_desa`, `kode_sls`, `nama_sls`
  - `total_assignment`: Jumlah keluarga/penugasan di SLS tersebut.
  - `total_bangunan_fisik`: Jumlah bangunan fisik riil (*Count Distinct*).
  - `daftar_nomor_bangunan`: Daftar seluruh nomor urut bangunan fisik yang terdata (urut alfanumerik).
  - `rasio_keluarga_per_bangunan`: Rata-rata beban keluarga per bangunan.
- **Sheet `Semua_Assignment`:**
  - 35.585 baris data mentah penugasan dengan preservasi teks untuk kolom ID, Kode SLS, Alamat, Nama Keluarga, dan Status Penugasan.

### 2. CSV Master ([output/Master_Data_Assignment_SE2026_Sitaro.csv](output/Master_Data_Assignment_SE2026_Sitaro.csv))
- Dataset tabular lengkap 35.585 baris dengan format standar UTF-8 yang siap diolah untuk analisis data lebih lanjut atau sistem GIS/database spasial.
