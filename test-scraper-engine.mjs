/**
 * Unit Test untuk scraperEngine.js (Node.js)
 * Menjalankan validasi logika pemipihan (flattening) dan ekstraksi metadata.
 */

import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const FasihScraperEngine = require('./scraperEngine.js');

console.log('🧪 Menjalankan pengujian unit scraperEngine.js...');

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ GAGAL: ${message}`);
    failed++;
  }
}

// 1. Uji Pemipihan Objek Bersarang (Flattening)
const sampleNested = {
  id: 'assignment-123',
  wilayah: {
    provinsi: '71',
    kabupaten: '08',
    kecamatan: {
      kode: '010',
      nama: 'TABUKAN UTARA'
    }
  },
  petugas: {
    pcl: { id: 1, nama: 'Budi' },
    pml: { id: 2, nama: 'Siti' }
  },
  tags: ['SE2026', 'PRIORITAS_1'],
  status: 'APPROVED',
  catatanKosong: null
};

const flattened = FasihScraperEngine.flattenRecord(sampleNested);

assert(flattened['id'] === 'assignment-123', 'ID dipertahankan dengan benar');
assert(flattened['wilayah_kecamatan_kode'] === '010', 'Nested property 3 tingkat berhasil dipipihkan');
assert(flattened['wilayah_kecamatan_nama'] === 'TABUKAN UTARA', 'Nama wilayah tersimpan utuh');
assert(flattened['petugas_pcl_nama'] === 'Budi', 'Objek petugas tersimpan sebagai kolom datar');
assert(flattened['tags'] === 'SE2026, PRIORITAS_1', 'Array primitive digabungkan dengan pemisah koma');
assert(flattened['catatanKosong'] === '', 'Nilai null dikonversi menjadi string kosong');

// 2. Uji Ekstraksi Metadata Pagination Spring Boot / Fasih
const sampleSpringResponse = {
  status: 'SUCCESS',
  data: {
    content: [
      { id: '1', nama: 'Usaha A' },
      { id: '2', nama: 'Usaha B' }
    ],
    totalElements: 120,
    totalPages: 6,
    number: 0,
    size: 20
  }
};

const meta = FasihScraperEngine.extractPageMetadata(sampleSpringResponse);
assert(meta.items.length === 2, 'Array content berhasil diekstrak');
assert(meta.totalItems === 120, 'Total elements berhasil terbaca');
assert(meta.totalPages === 6, 'Total pages berhasil terbaca');
assert(meta.currentPage === 0, 'Current page index berhasil terbaca');

console.log(`\n📊 Hasil Uji: ${passed} Berhasil, ${failed} Gagal.`);
if (failed > 0) process.exit(1);
