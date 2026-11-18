/**
 * Fasih Assignment Scraper - Core Fetching Engine (Fase 2)
 * 
 * Modul ini bertanggung jawab:
 * 1. Menarik data assignment per halaman (pagination) via API internal Fasih (Mendukung DataTables POST & REST GET).
 * 2. Mengatur jeda adaptif (throttling) & backoff otomatis saat terkena rate-limit (HTTP 429).
 * 3. Memipihkan (flatten) struktur JSON bersarang menjadi objek datar tabular.
 * 4. Menyediakan antarmuka kontrol (onProgress, pause, resume, abort).
 */

const FasihScraperEngine = (() => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const UUID_REGEX = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/;

  /**
   * Mengambil token XSRF dari berbagai sumber (Cookie, Hook, Meta, Storage)
   */
  function getXsrfToken() {
    // 1. Cek dari window.__fasihSniffedToken (paling akurat dari sniffer)
    if (typeof window !== 'undefined' && window.__fasihSniffedToken) {
      return window.__fasihSniffedToken;
    }

    // 2. Cek cookie peramban
    if (typeof document !== 'undefined' && document.cookie) {
      try {
        const match = document.cookie.match(/(?:^|;\s*)(?:XSRF-TOKEN|XSRF_TOKEN|_csrf|CSRF-TOKEN)=([^;]+)/i);
        if (match && match[1]) return decodeURIComponent(match[1]);
      } catch (e) {}
    }

    // 3. Cek meta tag HTML
    if (typeof document !== 'undefined') {
      try {
        const meta = document.querySelector('meta[name*="csrf"], meta[name*="xsrf"]');
        if (meta && meta.content) return meta.content;
      } catch (e) {}
    }

    // 4. Cek header tersimpan di session / local storage
    if (typeof window !== 'undefined') {
      try {
        for (const st of [sessionStorage, localStorage]) {
          if (!st) continue;
          for (let i = 0; i < st.length; i++) {
            const k = st.key(i);
            if (/xsrf|csrf/i.test(k)) {
              const val = st.getItem(k);
              if (val && val.length > 10) return val;
            }
          }
        }
      } catch (e) {}
    }

    return '';
  }

  /**
   * Deteksi Periode ID (surveyPeriodId) secara cerdas dari berbagai sumber:
   * Pada Fasih SM: /app/surveys/{surveyId}/{periodeId}/...
   * Nilai periodeId yang dibutuhkan API adalah UUID kedua: fd68e454-ba45-4b85-8205-f3bf777ded24
   */
  function detectPeriode() {
    if (typeof window === 'undefined') return 'fd68e454-ba45-4b85-8205-f3bf777ded24';

    // 1. Cek dari sniffer pasif jika sudah menangkap surveyPeriodId
    if (window.__fasihSniffedPeriode) {
      return window.__fasihSniffedPeriode;
    }

    // 2. Cek pola URL /app/surveys/{surveyId}/{periodeId} (UUID kedua adalah surveyPeriodId)
    const surveyPeriodMatch = window.location.pathname.match(/\/app\/surveys\/[0-9a-fA-F-]+\/([0-9a-fA-F-]+)/);
    if (surveyPeriodMatch && surveyPeriodMatch[1]) return surveyPeriodMatch[1];

    // 3. Cek link breadcrumb di DOM yang mengarah ke /app/surveys/{surveyId}/{periodeId}
    try {
      const surveyLinks = document.querySelectorAll('a[href*="/app/surveys/"]');
      for (const a of surveyLinks) {
        const m = (a.getAttribute('href') || '').match(/\/app\/surveys\/[0-9a-fA-F-]+\/([0-9a-fA-F-]+)/);
        if (m && m[1]) return m[1];
      }
    } catch (e) {}

    // 4. Cek query parameter di URL
    try {
      const sp = new URLSearchParams(window.location.search);
      for (const key of ['surveyPeriodId', 'periodeId', 'periodId', 'periode', 'period', 'id_periode', 'idPeriode']) {
        const val = sp.get(key);
        if (val && UUID_REGEX.test(val)) return val;
      }
    } catch (e) {}

    // 5. Fallback UUID pertama jika hanya ada satu
    const singleMatch = window.location.pathname.match(/\/app\/surveys\/([0-9a-fA-F-]+)/);
    if (singleMatch && singleMatch[1]) return singleMatch[1];

    return 'fd68e454-ba45-4b85-8205-f3bf777ded24';
  }

  /**
   * Pemipih objek JSON (Flattening)
   * Mengubah objek bersarang menjadi objek datar dengan pemisah underscore.
   * Contoh: { wilker: { kec: '010', desa: '001' } } -> { 'wilker_kec': '010', 'wilker_desa': '001' }
   */
  function flattenRecord(obj, prefix = '', res = {}) {
    if (!obj || typeof obj !== 'object') return res;

    for (const [key, val] of Object.entries(obj)) {
      const propName = prefix ? `${prefix}_${key}` : key;
      if (val === null || val === undefined) {
        res[propName] = '';
      } else if (typeof val === 'object' && !Array.isArray(val) && !(val instanceof Date)) {
        flattenRecord(val, propName, res);
      } else if (Array.isArray(val)) {
        if (val.length === 0) {
          res[propName] = '';
        } else if (typeof val[0] !== 'object') {
          res[propName] = val.join(', ');
        } else {
          res[propName] = JSON.stringify(val);
        }
      } else {
        res[propName] = val;
      }
    }
    return res;
  }

  /**
   * Deteksi letak array data & metadata pagination pada respons JSON (Mendukung DataTables & Spring Boot)
   */
  function extractPageMetadata(jsonResponse, pageSize = 50) {
    let items = [];
    let totalItems = 0;
    let totalPages = 1;
    let currentPage = 0;

    if (!jsonResponse || typeof jsonResponse !== 'object') {
      return { items, totalItems, totalPages, currentPage };
    }

    // 1. Array data baris
    const candidates = [
      jsonResponse.data && Array.isArray(jsonResponse.data) ? jsonResponse.data : null,
      jsonResponse.data && jsonResponse.data.content,
      jsonResponse.data && jsonResponse.data.assignments,
      jsonResponse.data && jsonResponse.data.list,
      jsonResponse.content,
      jsonResponse.assignments,
      jsonResponse.list,
      Array.isArray(jsonResponse) ? jsonResponse : null
    ];

    for (const cand of candidates) {
      if (Array.isArray(cand)) {
        items = cand;
        break;
      }
    }

    // 2. Info total records & halaman
    const root = (jsonResponse.data && !Array.isArray(jsonResponse.data)) ? jsonResponse.data : jsonResponse;
    totalItems = jsonResponse.recordsTotal ?? jsonResponse.recordsFiltered ?? root.totalElements ?? root.totalItems ?? root.total ?? items.length;
    
    const size = pageSize || root.size || (items.length > 0 ? items.length : 50);
    totalPages = root.totalPages ?? root.pageCount ?? (totalItems && size ? Math.ceil(totalItems / size) : 1);
    currentPage = root.number ?? root.page ?? root.currentPage ?? 0;

    return { items, totalItems, totalPages, currentPage };
  }

  /**
   * Kolom standar DataTables tabel penugasan Fasih SM
   */
  const DEFAULT_DATATABLE_COLUMNS = [
    { data: 'id', orderable: true },
    { data: 'codeIdentity', orderable: true },
    { data: 'data1', orderable: true },
    { data: 'data2', orderable: true },
    { data: 'data3', orderable: true },
    { data: 'data4', orderable: true },
    { data: 'data5', orderable: true },
    { data: 'data6', orderable: true },
    { data: 'data7', orderable: true },
    { data: 'data8', orderable: true },
    { data: 'data9', orderable: true },
    { data: 'data10', orderable: true }
  ];

  /**
   * Kelas Pengontrol Scraping
   */
  class ScraperTask {
    constructor(options = {}) {
      this.endpoint = options.endpoint || '/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode';
      this.periodeId = options.periodeId || detectPeriode();
      this.pageSize = options.pageSize || 10;
      this.startPage = options.startPage !== undefined ? options.startPage : 0; // 0-based index
      this.maxPages = options.maxPages || Infinity;
      this.delayMs = options.delayMs || 300;
      this.extraParams = options.extraParams || {};
      this.customHeaders = options.customHeaders || {};
      this.sniffedBody = options.sniffedBody || (typeof window !== 'undefined' ? window.__fasihSniffedBody : null);
      this.method = options.method || (this.endpoint.includes('datatable') ? 'POST' : 'GET');
      
      // Callback progres
      this.onProgress = options.onProgress || (() => {});
      this.onLog = options.onLog || console.log;
      
      // State kontrol
      this.isPaused = false;
      this.isAborted = false;
      this.isRunning = false;
      this.collectedData = [];
    }

    pause() {
      this.isPaused = true;
      this.onLog('⏸️ Scraping dijeda.');
    }

    resume() {
      this.isPaused = false;
      this.onLog('▶️ Scraping dilanjutkan.');
    }

    abort() {
      this.isAborted = true;
      this.isRunning = false;
      this.onLog('🛑 Scraping dibatalkan.');
    }

    /**
     * Memastikan token CSRF tersedia sebelum request POST
     */
    async ensureCsrfToken() {
      let token = getXsrfToken();
      if (!token && typeof window !== 'undefined') {
        try {
          this.onLog('🔍 Memperbarui token sesi XSRF dari server...');
          await fetch('/app/api/survey/api/v1/users/check-user', {
            method: 'POST',
            headers: {
              'Accept': '*/*',
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include'
          });
          token = getXsrfToken();
        } catch (e) {}
      }
      return token;
    }

    /**
     * Mengambil 1 halaman data dengan retry pintar untuk HTTP 429
     */
    async fetchSinglePage(pageIndex) {
      const origin = (typeof window !== 'undefined' && window.location && window.location.origin) ? window.location.origin : 'https://fasih-sm.bps.go.id';
      const isPost = this.method === 'POST' || this.endpoint.includes('datatable');
      
      const xsrfToken = await this.ensureCsrfToken();
      
      const baseHeaders = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        ...this.customHeaders
      };
      if (xsrfToken) {
        baseHeaders['x-xsrf-token'] = xsrfToken;
        baseHeaders['X-XSRF-TOKEN'] = xsrfToken;
      }

      let fetchUrl = '';
      let fetchOptions = {
        mode: 'cors',
        credentials: 'include'
      };
      if (typeof window !== 'undefined' && window.location && window.location.href) {
        fetchOptions.referrer = window.location.href;
      }

      if (isPost) {
        baseHeaders['Content-Type'] = 'application/json';

        // Siapkan struktur body DataTables JSON
        let bodyPayload = {};
        if (this.sniffedBody) {
          try {
            bodyPayload = typeof this.sniffedBody === 'string' ? JSON.parse(this.sniffedBody) : JSON.parse(JSON.stringify(this.sniffedBody));
          } catch (e) {
            bodyPayload = {};
          }
        }

        bodyPayload.start = pageIndex * this.pageSize;
        bodyPayload.length = this.pageSize;

        if (!bodyPayload.columns || !Array.isArray(bodyPayload.columns) || bodyPayload.columns.length === 0) {
          bodyPayload.columns = DEFAULT_DATATABLE_COLUMNS;
        }

        if (!bodyPayload.order) bodyPayload.order = [];
        if (!bodyPayload.search) bodyPayload.search = { value: '', regex: false };

        const activePeriodeId = this.periodeId || detectPeriode();
        if (!bodyPayload.assignmentExtraParam) {
          bodyPayload.assignmentExtraParam = {
            surveyPeriodId: activePeriodeId,
            assignmentErrorStatusType: -1,
            filterTargetType: 'TARGET_ONLY'
          };
        } else {
          bodyPayload.assignmentExtraParam.surveyPeriodId = activePeriodeId;
        }

        const cleanUrl = new URL(this.endpoint, origin);
        fetchUrl = cleanUrl.origin + cleanUrl.pathname;

        fetchOptions.method = 'POST';
        fetchOptions.headers = baseHeaders;
        fetchOptions.body = JSON.stringify(bodyPayload);
      } else {
        const u = new URL(this.endpoint, origin);
        u.searchParams.set('page', pageIndex);
        u.searchParams.set('size', this.pageSize);
        if (this.periodeId) {
          u.searchParams.set('periodeId', this.periodeId);
        }
        for (const [k, v] of Object.entries(this.extraParams)) {
          if (v !== undefined && v !== null && v !== '') {
            u.searchParams.set(k, v);
          }
        }
        fetchUrl = u.toString();
        fetchOptions.method = 'GET';
        fetchOptions.headers = baseHeaders;
      }

      let attempt = 0;
      const maxAttempts = 5;
      let backoffWait = 10000;

      while (attempt < maxAttempts) {
        if (this.isAborted) throw new Error('Dibatalkan oleh pengguna.');

        while (this.isPaused) {
          if (this.isAborted) throw new Error('Dibatalkan oleh pengguna.');
          await sleep(500);
        }

        try {
          const res = await fetch(fetchUrl, fetchOptions);

          if (res.status === 429) {
            attempt++;
            this.onLog(`⚠️ Terkena limitasi akses Fasih (HTTP 429). Menunggu ${backoffWait / 1000} detik sebelum mencoba lagi (Percobaan ${attempt}/${maxAttempts})...`);
            await sleep(backoffWait);
            backoffWait *= 1.5;
            continue;
          }

          if (!res.ok) {
            let errDetail = '';
            try {
              const errJson = await res.json();
              errDetail = errJson.message || errJson.error || JSON.stringify(errJson);
            } catch (e) {
              try { errDetail = await res.text(); } catch (e2) {}
            }
            console.error('❌ [Fasih Scraper Error Response]', res.status, res.statusText, errDetail, {
              url: fetchUrl,
              headers: baseHeaders
            });
            throw new Error(`HTTP Error ${res.status}: ${res.statusText}${errDetail ? ' (' + errDetail.slice(0, 150) + ')' : ''}`);
          }

          const json = await res.json();
          return json;
        } catch (err) {
          if (attempt >= maxAttempts - 1) throw err;
          attempt++;
          this.onLog(`⚠️ Galat saat mengambil halaman ${pageIndex}: ${err.message}. Mencoba ulang dalam 3 detik...`);
          await sleep(3000);
        }
      }
      throw new Error(`Gagal mengambil halaman ${pageIndex} setelah ${maxAttempts} percobaan.`);
    }

    /**
     * Menjalankan seluruh proses penarikan data
     */
    async run() {
      if (!this.endpoint) {
        throw new Error('Endpoint URL belum ditentukan. Tentukan URL endpoint terlebih dahulu.');
      }

      this.isRunning = true;
      this.isAborted = false;
      this.collectedData = [];

      this.onLog(`🚀 Memulai penarikan data penugasan...`);
      this.onLog(`📍 Endpoint: ${this.endpoint} (${this.method || 'POST'})`);
      if (this.periodeId) this.onLog(`📅 Periode ID: ${this.periodeId}`);

      let pageIndex = this.startPage;
      let totalPages = 1;
      let totalElements = 0;
      let pagesProcessed = 0;

      while (!this.isAborted && pageIndex < totalPages && pagesProcessed < this.maxPages) {
        this.onLog(`📄 Mengambil halaman ${pageIndex + 1} (Offset baris ${pageIndex * this.pageSize})...`);
        
        const rawJson = await this.fetchSinglePage(pageIndex);
        const meta = extractPageMetadata(rawJson, this.pageSize);

        if (meta.totalPages) totalPages = meta.totalPages;
        if (meta.totalItems) totalElements = meta.totalItems;

        if (!meta.items || meta.items.length === 0) {
          this.onLog(`ℹ️ Halaman ${pageIndex + 1} tidak mengembalikan data baru. Selesai.`);
          break;
        }

        // Pipihkan tiap record baris
        for (const item of meta.items) {
          this.collectedData.push(flattenRecord(item));
        }

        pagesProcessed++;
        pageIndex++;

        // Kabari progres
        this.onProgress({
          currentPage: pageIndex,
          totalPages: totalPages,
          totalElements: totalElements,
          fetchedCount: this.collectedData.length,
          percent: Math.min(100, Math.round((pageIndex / totalPages) * 100))
        });

        // Jeda sopan antar request untuk menghormati server Fasih
        await sleep(this.delayMs);
      }

      this.isRunning = false;
      this.onLog(`🎉 Selesai! Berhasil mengumpulkan ${this.collectedData.length} baris data penugasan.`);
      return this.collectedData;
    }
  }

  return {
    getXsrfToken,
    detectPeriode,
    detectPeriodeFromUrl: detectPeriode,
    flattenRecord,
    extractPageMetadata,
    DEFAULT_DATATABLE_COLUMNS,
    ScraperTask
  };
})();

// Ekspor untuk lingkungan browser window atau module
if (typeof window !== 'undefined') {
  window.FasihScraperEngine = FasihScraperEngine;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FasihScraperEngine;
}
