/**
 * Fasih Assignment Scraper - Exporter Engine (Fase 4)
 * 
 * Fitur:
 * 1. Menjaga Leading Zero pada kode wilayah & nomor identitas (misal: "010", "001").
 * 2. Ekspor CSV UTF-8 dengan Byte Order Mark (\uFEFF) untuk kompatibilitas penuh Microsoft Excel.
 * 3. Ekspor XLSX murni (Native OpenXML Spreadsheet) tanpa dependensi eksternal.
 * 4. Pemicu unduhan otomatis di browser.
 */

const FasihExporter = (() => {
  /**
   * Escape karakter khusus untuk XML
   */
  function escapeXml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  /**
   * Escape nilai untuk CSV sesuai RFC 4180
   */
  function escapeCsv(val) {
    if (val === null || val === undefined) return '""';
    const str = String(val);
    // Jika nilai merupakan kode ber-angka nol di depan (misal "010"), buat formula Excel ="010" agar leading zero tidak hilang
    if (/^0\d+$/.test(str)) {
      return `="""${str}"""`;
    }
    return `"${str.replace(/"/g, '""')}"`;
  }

  /**
   * Mengonversi array of objects menjadi CSV string dengan BOM
   */
  function jsonToCsv(data) {
    if (!data || data.length === 0) return '\uFEFF';

    // Ambil seluruh header unik
    const headers = [...new Set(data.flatMap((row) => Object.keys(row)))];
    const headerLine = headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(',');

    const rows = data.map((row) => {
      return headers.map((h) => escapeCsv(row[h])).join(',');
    });

    return '\uFEFF' + [headerLine, ...rows].join('\r\n');
  }

  /**
   * Mengonversi nomor kolom (0-based) menjadi huruf kolom Excel (A, B, ..., Z, AA, AB...)
   */
  function colToLetter(colIndex) {
    let temp = colIndex + 1;
    let letter = '';
    while (temp > 0) {
      const mod = (temp - 1) % 26;
      letter = String.fromCharCode(65 + mod) + letter;
      temp = Math.floor((temp - mod) / 26);
    }
    return letter;
  }

  /**
   * Membuat file OpenXML (.xlsx) murni menggunakan ZIP Store Method (Zero Dependencies)
   */
  function jsonToXlsx(data, sheetName = 'Data_Assignment') {
    if (!data || data.length === 0) {
      data = [{ Pesan: 'Tidak ada data penugasan.' }];
    }

    const headers = [...new Set(data.flatMap((row) => Object.keys(row)))];

    // Bangun XML sheet1.xml
    let sheetXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
    sheetXml += '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n';
    sheetXml += '<sheetData>\n';

    // Baris Header (Row 1)
    sheetXml += '<row r="1">\n';
    headers.forEach((h, colIdx) => {
      const cellRef = `${colToLetter(colIdx)}1`;
      sheetXml += `<c r="${cellRef}" t="inlineStr"><is><t>${escapeXml(h)}</t></is></c>\n`;
    });
    sheetXml += '</row>\n';

    // Baris Data (Row 2 .. N)
    data.forEach((row, rowIdx) => {
      const rNum = rowIdx + 2;
      sheetXml += `<row r="${rNum}">\n`;
      headers.forEach((h, colIdx) => {
        const cellRef = `${colToLetter(colIdx)}${rNum}`;
        const val = row[h];

        if (val === null || val === undefined || val === '') {
          // Kosong
        } else if (typeof val === 'number') {
          sheetXml += `<c r="${cellRef}"><v>${val}</v></c>\n`;
        } else if (typeof val === 'boolean') {
          sheetXml += `<c r="${cellRef}" t="b"><v>${val ? 1 : 0}</v></c>\n`;
        } else {
          // Selalu simpan string (termasuk kode dengan leading zero "010") sebagai inlineStr agar angka nol tidak dibuang oleh Excel
          sheetXml += `<c r="${cellRef}" t="inlineStr"><is><t>${escapeXml(val)}</t></is></c>\n`;
        }
      });
      sheetXml += '</row>\n';
    });

    sheetXml += '</sheetData>\n</worksheet>';

    // Berkas-berkas pendukung OpenXML
    const contentTypesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>`;

    const relsXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`;

    const workbookXmlRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>`;

    const workbookXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="${escapeXml(sheetName)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>`;

    const files = [
      { name: '[Content_Types].xml', content: contentTypesXml },
      { name: '_rels/.rels', content: relsXml },
      { name: 'xl/_rels/workbook.xml.rels', content: workbookXmlRels },
      { name: 'xl/workbook.xml', content: workbookXml },
      { name: 'xl/worksheets/sheet1.xml', content: sheetXml }
    ];

    return createZip(files);
  }

  /**
   * Pembangun ZIP Murni (Store Method - Uncompressed, 100% valid ZIP specification)
   */
  function createZip(files) {
    const encoder = new TextEncoder();
    const parts = [];
    const cdEntries = [];
    let offset = 0;

    // Hitung CRC32
    function crc32(buf) {
      let c = 0 ^ (-1);
      for (let i = 0; i < buf.length; i++) {
        c = (c >>> 8) ^ CRC_TABLE[(c ^ buf[i]) & 0xFF];
      }
      return (c ^ (-1)) >>> 0;
    }

    const CRC_TABLE = (() => {
      const table = new Uint32Array(256);
      for (let i = 0; i < 256; i++) {
        let c = i;
        for (let j = 0; j < 8; j++) {
          c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
        }
        table[i] = c;
      }
      return table;
    })();

    for (const file of files) {
      const nameBytes = encoder.encode(file.name);
      const dataBytes = encoder.encode(file.content);
      const crc = crc32(dataBytes);
      const size = dataBytes.length;

      // Local File Header (30 byte + nameLen)
      const lfh = new Uint8Array(30 + nameBytes.length);
      const dvLfh = new DataView(lfh.buffer);
      dvLfh.setUint32(0, 0x04034b50, true); // Signature
      dvLfh.setUint16(4, 20, true);         // Version needed
      dvLfh.setUint16(6, 0, true);          // Flags
      dvLfh.setUint16(8, 0, true);          // Method (0 = Store)
      dvLfh.setUint16(10, 0, true);         // Time
      dvLfh.setUint16(12, 0, true);         // Date
      dvLfh.setUint32(14, crc, true);       // CRC32
      dvLfh.setUint32(18, size, true);      // Compressed Size
      dvLfh.setUint32(22, size, true);      // Uncompressed Size
      dvLfh.setUint16(26, nameBytes.length, true); // Name length
      dvLfh.setUint16(28, 0, true);         // Extra field length
      lfh.set(nameBytes, 30);

      parts.push(lfh);
      parts.push(dataBytes);

      // Central Directory Header (46 byte + nameLen)
      const cdh = new Uint8Array(46 + nameBytes.length);
      const dvCdh = new DataView(cdh.buffer);
      dvCdh.setUint32(0, 0x02014b50, true); // Signature
      dvCdh.setUint16(4, 20, true);         // Version made by
      dvCdh.setUint16(6, 20, true);         // Version needed
      dvCdh.setUint16(8, 0, true);          // Flags
      dvCdh.setUint16(10, 0, true);         // Method
      dvCdh.setUint16(12, 0, true);         // Time
      dvCdh.setUint16(14, 0, true);         // Date
      dvCdh.setUint32(16, crc, true);       // CRC32
      dvCdh.setUint32(20, size, true);      // Compressed Size
      dvCdh.setUint32(24, size, true);      // Uncompressed Size
      dvCdh.setUint16(28, nameBytes.length, true); // Name length
      dvCdh.setUint16(30, 0, true);         // Extra length
      dvCdh.setUint16(32, 0, true);         // Comment length
      dvCdh.setUint16(34, 0, true);         // Disk start
      dvCdh.setUint16(36, 0, true);         // Internal attrs
      dvCdh.setUint32(38, 0, true);         // External attrs
      dvCdh.setUint32(42, offset, true);    // Local header offset
      cdh.set(nameBytes, 46);

      cdEntries.push(cdh);
      offset += lfh.length + dataBytes.length;
    }

    const cdStartOffset = offset;
    let cdSize = 0;
    for (const cdh of cdEntries) {
      parts.push(cdh);
      cdSize += cdh.length;
    }

    // End of Central Directory Record (22 byte)
    const eocd = new Uint8Array(22);
    const dvEocd = new DataView(eocd.buffer);
    dvEocd.setUint32(0, 0x06054b50, true); // Signature
    dvEocd.setUint16(4, 0, true);          // Disk number
    dvEocd.setUint16(6, 0, true);          // Start disk
    dvEocd.setUint16(8, files.length, true);  // Disk entries
    dvEocd.setUint16(10, files.length, true); // Total entries
    dvEocd.setUint32(12, cdSize, true);        // Central Directory Size
    dvEocd.setUint32(16, cdStartOffset, true); // Offset of Central Directory
    dvEocd.setUint16(20, 0, true);             // Comment length

    parts.push(eocd);

    // Hitung total panjang dan satukan ke satu Uint8Array
    const totalLength = parts.reduce((sum, p) => sum + p.length, 0);
    const finalBuffer = new Uint8Array(totalLength);
    let curPos = 0;
    for (const p of parts) {
      finalBuffer.set(p, curPos);
      curPos += p.length;
    }

    return finalBuffer;
  }

  /**
   * Pemicu unduhan file di browser
   */
  function downloadBlob(blob, filename) {
    if (typeof document === 'undefined') return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      a.remove();
      URL.revokeObjectURL(url);
    }, 1000);
  }

  /**
   * Ekspor data ke CSV atau XLSX
   */
  async function exportData(data, format = 'xlsx', filenameBase = 'Raw_Assignment_Fasih') {
    const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace('T', '_').slice(0, 15);
    const filename = `${filenameBase}_${timestamp}.${format}`;

    if (format.toLowerCase() === 'csv') {
      const csvStr = jsonToCsv(data);
      const blob = new Blob([csvStr], { type: 'text/csv;charset=utf-8;' });
      downloadBlob(blob, filename);
    } else {
      const xlsxBuffer = jsonToXlsx(data);
      const blob = new Blob([xlsxBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      downloadBlob(blob, filename);
    }

    return filename;
  }

  return {
    jsonToCsv,
    jsonToXlsx,
    exportData
  };
})();

if (typeof window !== 'undefined') {
  window.FasihExporter = FasihExporter;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FasihExporter;
}
