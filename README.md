# Proyek Scraping Web Fasih SM (BPS) — Raw Data Exporter

Proyek ini berisi pengembangan **Ekstensi Google Chrome (Manifest V3)** untuk menarik (*scraping*) daftar penugasan (*assignments*) dan *raw data* dari aplikasi web **Fasih SM (BPS)** secara otomatis, aman, dan mengekspornya langsung ke format **Excel (.xlsx)** atau **CSV**.

Proyek ini dibangun berdasarkan rancangan pada [PRD and playbook.md](PRD%20and%20playbook.md) yang dieksekusi secara terstruktur melalui **5 Fase Pengembangan**.

---

## 📌 Mengapa Menggunakan Ekstensi Chrome?

1. **Zero Auth Friction:** Memanfaatkan sesi login SSO BPS (`sso.bps.go.id`) yang sudah aktif di peramban pengguna. Tidak perlu memprogram ulang alur login Keycloak/OAuth, token refresh, atau menangani captcha.
2. **Aman & Read-Only:** Tidak menggunakan izin berbahaya seperti `debugger` (bebas dari pop-up kuning *"Chrome is being debugged"*). Seluruh proses pengambilan data murni *read-only* langsung dari peramban pengguna tanpa perantara server pihak ketiga.
3. **Preservasi Kode Wilayah (*Leading Zero*):** Kode seperti `"010"` (Kecamatan) dan `"001"` (Desa) tetap tersimpan sebagai string teks di Excel/CSV, tidak terpotong menjadi angka biasa (`10` atau `1`).
4. **Tahan Batas Akses (*Rate-Limit HTTP 429*):** Dilengkapi sistem *smart throttle* dan *exponential backoff* otomatis saat server Fasih membatasi jumlah request.
5. **Zero External Dependencies:** Modul pembaca dan pembuat file `.xlsx` dibangun secara mandiri (*pure native OpenXML via Web APIs*), tanpa dependensi npm berukuran besar atau CDN eksternal.

---

## 🗂️ Struktur Direktori Proyek

```
Scraping-Fasih/
│
├── fasih-assignment-scraper/     # 📦 FOLDER EKSTENSI CHROME SIAP PAKAI
│   ├── manifest.json              # Konfigurasi ekstensi Chrome Manifest V3
│   ├── content.js                 # Entry point & observer navigasi SPA Fasih
│   ├── scraperEngine.js           # Mesin pagination & proteksi rate limit 429
│   ├── uiManager.js               # Antarmuka Floating Action Button & Modal (Shadow DOM)
│   ├── exporter.js                # Generator OpenXML (.xlsx) & CSV dengan UTF-8 BOM
│   ├── icons/                     # Ikon ekstensi (16x16, 48x48, 128x128)
│   └── README.md                  # Panduan khusus pemakaian ekstensi
│
├── Referensi-fasih-inject-lk/    # 📁 Folder referensi ekstensi inject LK sebelumnya
├── PRD and playbook.md           # 📄 Dokumen PRD dan Playbook 5 Fase
├── phase1-sniffer.js             # 🔍 Script inspeksi/sniffer endpoint di Console Fasih (Fase 1)
├── spesifikasi_api_fasih.md      # 📋 Catatan spesifikasi API dan pemetaan kolom (Fase 1)
├── scraperEngine.js              # ⚙️ Modul engine scraping utama (Fase 2)
├── test-scraper-engine.mjs       # 🧪 Unit test Node.js untuk engine (Fase 2)
├── uiManager.js                  # 🎨 Modul antarmuka UI Shadow DOM (Fase 3)
├── demo-ui.html                  # 🖥️ Halaman demo simulasi UI di browser lokal (Fase 3)
├── exporter.js                   # 📊 Modul generator file .xlsx dan .csv (Fase 4)
├── test-exporter.mjs             # 🧪 Unit test Node.js untuk exporter (Fase 4)
└── README.md                     # 📖 Dokumentasi utama proyek ini
```

---

## 🚀 Panduan Instalasi Ekstensi di Chrome

Untuk memasang ekstensi ini ke Google Chrome atau Microsoft Edge:

1. Buka peramban Chrome, lalu buka halaman:
   ```text
   chrome://extensions
   ```
2. Di pojok kanan atas, hidupkan toggle **"Developer mode"** (Mode pengembang).
3. Klik tombol **"Load unpacked"** (Muat yang belum dibongkar) di kiri atas.
4. Pilih folder:
   ```text
   D:\10Project\Scraping-Fasih\fasih-assignment-scraper
   ```
5. Ekstensi **"Fasih Assignment Raw Exporter"** sekarang telah aktif di Chrome Anda!

---

## 💡 Cara Penggunaan di Web Fasih SM

1. Buka dan login ke web Fasih SM di [https://fasih-sm.bps.go.id/app/](https://fasih-sm.bps.go.id/app/).
2. Masuk ke menu **Daftar Penugasan / Assignment** pada periode yang ingin ditarik datanya.
3. Di pojok kanan bawah, klik tombol biru **"📥 Ekspor Raw Assignment"**.
4. Sebuah dialog kontrol akan terbuka:
   * **Periode ID:** Otomatis terbaca dari URL aktif.
   * **Maks Halaman:** Biarkan kosong untuk mengambil seluruh data, atau isi angka (misal: `3`) untuk uji coba awal.
   * **Ukuran Halaman:** Pilih `25`, `50`, atau `100` baris per request.
   * **Format:** Pilih **Excel (.xlsx)** atau **CSV**.
5. Klik **"🚀 Mulai Ekspor"**.
6. Progres penarikan data akan tampil secara real-time. Anda dapat menekan **"⏸️ Jeda"** atau **"🛑 Batalkan"** kapan saja.
7. Setelah selesai, file akan terunduh otomatis ke folder *Downloads* Anda.

---

## 🧪 Pengujian & Validasi

Proyek ini dilengkapi dengan skrip pengujian otomatis (Unit Testing) berbasis Node.js:

### 1. Uji Mesin Scraping (Fase 2)
Menguji logika pemipihan (*flattening*) struktur JSON bersarang dan deteksi pagination:
```bash
node test-scraper-engine.mjs
```
*(Hasil: 10/10 pengujian berhasil)*

### 2. Uji Exporter Spreadsheet (Fase 4)
Menguji validitas file OpenXML `.xlsx`, proteksi *leading zero*, dan kompatibilitas karakter khusus:
```bash
node test-exporter.mjs
```
*(Hasil: 10/10 pengujian berhasil)*

### 3. Uji Pratinjau Antarmuka UI (Fase 3)
Cukup buka berkas [demo-ui.html](demo-ui.html) langsung di peramban web (klik ganda file atau buka via Chrome) untuk mencoba interaksi tombol dan dialog modal tanpa perlu login ke Fasih SM.

---

## 🛡️ Tata Kelola Data & Keamanan
* Ekstensi ini tidak mengirimkan data survei atau kredensial apa pun ke server luar (*100% Client-Side In-Memory*).
* Sesuai dengan prinsip kerahasiaan data statistik dan keamanan operasional BPS.
