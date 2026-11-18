/**
 * Fasih SM - Phase 1 API Sniffer & Inspector
 * 
 * Cara Penggunaan:
 * 1. Buka browser Chrome dan login ke https://fasih-sm.bps.go.id/app/
 * 2. Masuk ke menu Daftar Penugasan / Assignment.
 * 3. Buka DevTools (tekan tombol F12 atau Ctrl + Shift + I).
 * 4. Pilih tab "Console".
 * 5. Salin (copy) SELURUH isi script ini, lalu tempel (paste) di Console dan tekan ENTER.
 * 6. Lakukan interaksi di web Fasih: ganti halaman tabel (next page), ganti filter status, atau ganti kecamatan/desa.
 * 7. Script akan otomatis menangkap request API, menganalisis struktur JSON-nya, dan menampilkan tombol/perintah unduh spesifikasi.
 */

(() => {
  if (window.__fasihSnifferActive) {
    console.warn('⚠️ Fasih API Sniffer sudah aktif di tab ini.');
    return;
  }
  window.__fasihSnifferActive = true;

  console.log('%c🚀 [Fasih API Sniffer - Fase 1] AKTIF & MENDENGARKAN...', 'background: #2563eb; color: white; font-weight: bold; padding: 4px 8px; border-radius: 4px;');
  console.log('👉 Silakan berinteraksi dengan tabel Fasih (klik Next Page, ubah filter wilayah, dsb).');

  window.__fasihCapturedEndpoints = [];

  function analyzeResponse(url, method, status, body) {
    // Hanya tangkap endpoint API internal Fasih
    if (!url.includes('/api/')) return;

    let parsed = null;
    try {
      parsed = typeof body === 'string' ? JSON.parse(body) : body;
    } catch (e) {
      // Bukan JSON
      return;
    }

    if (!parsed || typeof parsed !== 'object') return;

    const u = new URL(url, window.location.origin);
    const queryParams = Object.fromEntries(u.searchParams.entries());

    // Cari letak array data (candidates: content, data, list, items, assignments)
    let candidateArray = null;
    let arrayKeyPath = '';
    let totalItems = null;
    let totalPages = null;

    function findArray(obj, path = '') {
      if (!obj || typeof obj !== 'object') return;
      for (const [k, v] of Object.entries(obj)) {
        const curPath = path ? `${path}.${k}` : k;
        if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object') {
          if (!candidateArray || v.length > candidateArray.length) {
            candidateArray = v;
            arrayKeyPath = curPath;
          }
        } else if (v && typeof v === 'object' && !Array.isArray(v)) {
          findArray(v, curPath);
        }
      }
    }
    findArray(parsed);

    // Cari info total
    function findTotals(obj) {
      if (!obj || typeof obj !== 'object') return;
      const str = JSON.stringify(obj);
      for (const k of ['totalElements', 'total', 'total_count', 'count', 'totalData', 'recordsTotal']) {
        if (obj[k] != null) totalItems = obj[k];
      }
      for (const k of ['totalPages', 'pages', 'last_page', 'pageCount']) {
        if (obj[k] != null) totalPages = obj[k];
      }
    }
    findTotals(parsed);

    const capturedItem = {
      timestamp: new Date().toISOString(),
      url: u.pathname,
      fullUrl: url,
      method,
      status,
      queryParams,
      arrayKeyPath,
      sampleArrayLength: candidateArray ? candidateArray.length : 0,
      totalItems,
      totalPages,
      sampleRowKeys: candidateArray && candidateArray[0] ? Object.keys(candidateArray[0]) : [],
      sampleRow: candidateArray && candidateArray[0] ? candidateArray[0] : null,
      rawResponseSample: parsed
    };

    window.__fasihCapturedEndpoints.push(capturedItem);

    console.group(`%c🎯 [API TERTANGKAP] ${method} ${u.pathname}`, 'color: #10b981; font-weight: bold;');
    console.log('📌 Full URL:', url);
    console.log('🔍 Query Parameters:', queryParams);
    console.log('📊 Letak Array Data:', arrayKeyPath ? `res.${arrayKeyPath}` : '(Tidak ada array list)');
    console.log('🔢 Info Paging:', { totalItems, totalPages, itemsInPage: candidateArray ? candidateArray.length : 0 });
    if (candidateArray && candidateArray[0]) {
      console.log('📋 Kolom yang Tersedia di Baris:', Object.keys(candidateArray[0]));
      console.log('🔍 Contoh 1 Data Baris:', candidateArray[0]);
    }
    console.log('💡 Ketik `downloadSpec()` di console untuk menyimpan hasil capture ini ke file JSON.');
    console.groupEnd();
  }

  // Intercept window.fetch
  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const res = await originalFetch.apply(this, args);
    try {
      const clone = res.clone();
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      const method = (args[1] && args[1].method) || 'GET';
      clone.text().then((txt) => {
        analyzeResponse(url, method, res.status, txt);
      }).catch(() => {});
    } catch (e) {}
    return res;
  };

  // Intercept XMLHttpRequest
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url) {
    this._url = url;
    this._method = method;
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function () {
    this.addEventListener('load', function () {
      try {
        analyzeResponse(this._url, this._method, this.status, this.responseText);
      } catch (e) {}
    });
    return origSend.apply(this, arguments);
  };

  // Helper fungsi download
  window.downloadSpec = function () {
    if (!window.__fasihCapturedEndpoints.length) {
      console.warn('Belum ada request API Fasih yang tertangkap.');
      return;
    }
    const blob = new Blob([JSON.stringify(window.__fasihCapturedEndpoints, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `fasih_phase1_capture_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    console.log('✅ File spesifikasi API berhasil diunduh!');
  };
})();
