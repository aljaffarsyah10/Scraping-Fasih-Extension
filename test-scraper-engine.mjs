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

// 2. Uji Ekstraksi Metadata Pagination Spring Boot / REST
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

// 3. Uji Ekstraksi Metadata DataTables Resmi Fasih SM (POST datatable-all-user-survey-periode)
const sampleDataTablesResponse = {
  draw: 1,
  recordsTotal: 35585,
  recordsFiltered: 35585,
  data: [
    {
      id: 'a1b2c3d4',
      codeIdentity: 'ID-001',
      data1: '7108010001001B',
      data2: 'Toko Maju Jaya',
      data3: '010'
    },
    {
      id: 'e5f6g7h8',
      codeIdentity: 'ID-002',
      data1: '7108010001002B',
      data2: 'Warung Berkah',
      data3: '010'
    }
  ]
};

const dtMeta10 = FasihScraperEngine.extractPageMetadata(sampleDataTablesResponse, 10);
assert(dtMeta10.items.length === 2, 'DataTables: Data array berhasil diekstrak');
assert(dtMeta10.totalItems === 35585, 'DataTables: recordsTotal 35585 terbaca sebagai totalItems');
assert(dtMeta10.totalPages === 3559, 'DataTables: totalPages dihitung dengan benar untuk pageSize 10 (35585/10 = 3559)');

const dtMeta50 = FasihScraperEngine.extractPageMetadata(sampleDataTablesResponse, 50);
assert(dtMeta50.totalPages === 712, 'DataTables: totalPages dihitung dengan benar untuk pageSize 50 (35585/50 = 712)');

// 4. Uji Ekstraksi Skema Riil Fasih SM (searchData & totalHit)
const sampleFasihRealResponse = {
  searchData: [
    { id: 'd8fa7cf7-66f7-4fe9-bca5-182254369408', data1: 'ISWAR KINGKAME' },
    { id: 'e5f6g7h8-1234-5678-9abc-def012345678', data1: 'WARUNG BERKAH' }
  ],
  totalHit: 10000,
  searchAggregation: []
};

const fasihMeta = FasihScraperEngine.extractPageMetadata(sampleFasihRealResponse, 10);
assert(fasihMeta.items.length === 2, 'Fasih SM: searchData berhasil diekstrak');
assert(fasihMeta.totalItems === 10000, 'Fasih SM: totalHit berhasil terbaca sebagai totalItems');
assert(fasihMeta.totalPages === 1000, 'Fasih SM: totalPages dihitung dengan benar (10000/10 = 1000)');

// 5. Uji Default Kolom DataTables
assert(Array.isArray(FasihScraperEngine.DEFAULT_DATATABLE_COLUMNS), 'DEFAULT_DATATABLE_COLUMNS terdefinisi');
assert(FasihScraperEngine.DEFAULT_DATATABLE_COLUMNS.length >= 10, 'DEFAULT_DATATABLE_COLUMNS memuat kolom penugasan');

console.log(`\n📊 Hasil Uji: ${passed} Berhasil, ${failed} Gagal.`);
if (failed > 0) process.exit(1);
