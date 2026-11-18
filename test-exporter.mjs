/**
 * Unit Test untuk exporter.js (Node.js)
 * Memverifikasi pembuatan CSV (dengan BOM & leading zeros) serta file XLSX murni.
 */

import { writeFileSync, unlinkSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

const FasihExporter = require('./exporter.js');
const LK = require('./Referensi-fasih-inject-lk/lk-core.js');

console.log('🧪 Menjalankan pengujian unit exporter.js...');

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

const sampleData = [
  {
    assignment_id: 'c0fcb836-7108-410a',
    kode_prov: '71',
    kode_kab: '08',
    kode_kec: '010',
    kode_desa: '001',
    nama_usaha: 'Kios Bunga & Sayur',
    pendapatan: 15000000,
    is_active: true
  },
  {
    assignment_id: 'c0fcb836-7108-410b',
    kode_prov: '71',
    kode_kab: '08',
    kode_kec: '020',
    kode_desa: '005',
    nama_usaha: 'Toko "Sumber Rejeki", Sejahtera',
    pendapatan: 32500000,
    is_active: false
  }
];

// 1. Uji CSV Generator
const csv = FasihExporter.jsonToCsv(sampleData);
assert(csv.startsWith('\uFEFF'), 'CSV memiliki UTF-8 BOM untuk kompatibilitas Excel');
assert(csv.includes('="""010"""'), 'Leading zero pada CSV diformat dengan proteksi formula Excel');
assert(csv.includes('"Toko ""Sumber Rejeki"", Sejahtera"'), 'Karakter kutip dan koma pada string di-escape dengan benar');

// 2. Uji Native XLSX Generator
const xlsxBytes = FasihExporter.jsonToXlsx(sampleData, 'Daftar_Assignment');
assert(xlsxBytes instanceof Uint8Array, 'XLSX menghasilkan Uint8Array');
assert(xlsxBytes.length > 500, `Ukuran file XLSX valid (${xlsxBytes.length} bytes)`);

// Verifikasi integritas ZIP XLSX menggunakan pembaca LK (lk-core.js)
async function verifyXlsx() {
  try {
    const lkRead = await LK.unzip(xlsxBytes);
    assert(lkRead.names.includes('xl/workbook.xml'), 'ZIP XLSX memuat xl/workbook.xml');
    assert(lkRead.names.includes('xl/worksheets/sheet1.xml'), 'ZIP XLSX memuat xl/worksheets/sheet1.xml');
    
    const sheet1Xml = await lkRead.read('xl/worksheets/sheet1.xml');
    assert(sheet1Xml.includes('<is><t>010</t></is>'), 'Leading zero "010" tersimpan sebagai inlineStr XML');
    assert(sheet1Xml.includes('<v>15000000</v>'), 'Nilai angka tersimpan sebagai numerik XML');
    assert(sheet1Xml.includes('Kios Bunga &amp; Sayur'), 'Karakter ampersand (&) ter-escape XML dengan aman');
  } catch (err) {
    assert(false, `Pembacaan ZIP XLSX gagal: ${err.message}`);
  }
}

await verifyXlsx();

console.log(`\n📊 Hasil Uji Exporter: ${passed} Berhasil, ${failed} Gagal.`);
if (failed > 0) process.exit(1);
