# Fasih Assignment Raw Exporter (Chrome Extension v1.0.0)

Ekstensi Google Chrome (Manifest V3) untuk menarik (*scraping*) daftar penugasan (*assignments*) dan *raw data* dari platform survei web **Fasih SM (BPS)** secara otomatis ke dalam format **Excel Spreadsheet (.xlsx)** dan **CSV**.

---

## 🌟 Fitur Utama

1. **One-Click Export:** Tombol terapung (*Floating Button*) muncul otomatis di pojok kanan bawah halaman Fasih SM.
2. **Preservasi Kode Wilayah (*Leading Zero*):** Kode wilayah seperti `"010"` (Kecamatan) dan `"001"` (Desa) tetap tersimpan sebagai teks, tidak akan terpotong menjadi angka `10` atau `1` di Excel.
3. **Murni Tanpa Server Pihak Ketiga (*Client-Side Only*):** Menjamin keamanan dan kerahasiaan data survei BPS. Seluruh proses pengambilan data berjalan langsung di peramban menggunakan sesi login Anda yang aktif.
4. **Proteksi Limitasi Akses (Rate-Limit HTTP 429):** Dilengkapi fitur jeda adaptif (*exponential backoff*) otomatis agar tidak membebani server Fasih SM dan mencegah pemblokiran sesi.
5. **Kontrol Interaktif:** Dilengkapi progress bar visual, estimasi jumlah data, serta tombol **Jeda (Pause)** dan **Batalkan (Cancel)**.

---

## 🚀 Panduan Instalasi (Hanya 1 Menit)

Ekstensi ini dapat dipasang di **Google Chrome**, **Microsoft Edge**, atau peramban berbasis Chromium lainnya:

1. Buka browser Chrome, lalu ketik di bilah alamat:
   ```text
   chrome://extensions
   ```
2. Di pojok kanan atas, aktifkan sakelar **"Developer mode"** (Mode pengembang).
3. Klik tombol **"Load unpacked"** (Muat yang belum dibongkar) di pojok kiri atas.
4. Pilih folder:
   ```text
   D:\10Project\Scraping-Fasih\fasih-assignment-scraper
   ```
5. Ekstensi **"Fasih Assignment Raw Exporter"** sekarang telah aktif dan siap digunakan!

---

## 📖 Cara Penggunaan

1. Buka web Fasih SM di [https://fasih-sm.bps.go.id/app/](https://fasih-sm.bps.go.id/app/) dan login menggunakan akun SSO BPS Anda.
2. Buka menu **Daftar Penugasan / Assignment** pada periode yang diinginkan.
3. Di pojok kanan bawah layar, klik tombol biru **"📥 Ekspor Raw Assignment"**.
4. Sebuah dialog pengaturan akan muncul:
   * **Periode ID:** Terdeteksi otomatis dari URL.
   * **Endpoint API:** Default `/app/api/assignment-general/api/assignment/list` (dapat disesuaikan jika diperlukan).
   * **Maks Halaman:** Kosongkan jika ingin mengambil semua data penugasan, atau isi angka (misal `2`) untuk pengujian awal.
   * **Format:** Pilih **Excel (.xlsx)** atau **CSV**.
5. Klik **"🚀 Mulai Ekspor"**.
6. Pantau bar progres. Setelah selesai, file Excel/CSV akan terunduh otomatis ke folder *Downloads* komputer Anda.

---

## 📁 Struktur Berkas Ekstensi

```
fasih-assignment-scraper/
├── manifest.json       # Konfigurasi ekstensi Chrome Manifest V3
├── content.js          # Entry point yang mendeteksi navigasi halaman Fasih
├── scraperEngine.js    # Mesin scraping & pagination loop dengan proteksi rate limit
├── uiManager.js        # Antarmuka floating button & modal progres (Shadow DOM)
├── exporter.js         # Generator native OpenXML (.xlsx) & CSV UTF-8 dengan BOM
└── icons/              # Ikon ekstensi (16x16, 48x48, 128x128)
```

---

## 🛡️ Catatan Teknis & Keamanan

* **Bebas Pesan Peringatan Debugger:** Berbeda dengan ekstensi yang mengontrol mouse/keyboard, ekstensi ini murni *read-only* (menggunakan API `fetch` dengan cookie aktif), sehingga tidak memerlukan izin `debugger` dan tidak memunculkan baris peringatan *"Chrome is being debugged"*.
* **Tampilan Terisolasi (Shadow DOM):** Seluruh styling modal terbungkus di dalam Shadow DOM terpisah, sehingga tidak akan merusak atau terpengaruh oleh framework CSS (Tailwind) bawaan web Fasih SM.
