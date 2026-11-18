/**
 * Fasih Assignment Scraper - Core Fetching Engine (Fase 2)
 * 
 * Modul ini bertanggung jawab:
 * 1. Menarik data assignment per halaman (pagination) via API internal Fasih.
 * 2. Mengatur jeda adaptif (throttling) & backoff otomatis saat terkena rate-limit (HTTP 429).
 * 3. Memipihkan (flatten) struktur JSON bersarang menjadi objek datar tabular.
 * 4. Menyediakan antarmuka kontrol (onProgress, pause, resume, abort).
 */

const FasihScraperEngine = (() => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const UUID_REGEX = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/;

  /**
   * Deteksi Periode ID secara cerdas dari berbagai sumber:
   * 1. Query parameter (?periodeId=..., ?period=...)
   * 2. Pathname URL (/app/assignment/{uuid})
   * 3. Hash router (#/...)
   * 4. SessionStorage / LocalStorage Fasih SM
   * 5. Elemen dropdown/select di DOM
   */
  function detectPeriode() {
    if (typeof window === 'undefined') return null;

    // 1. Cek query parameter di URL
    try {
      const sp = new URLSearchParams(window.location.search);
      for (const key of ['periodeId', 'periodId', 'periode', 'period', 'id_periode', 'idPeriode']) {
        const val = sp.get(key);
        if (val && UUID_REGEX.test(val)) return val;
      }
    } catch (e) {}

    // 2. Cek pathname URL
    const pathMatch = window.location.pathname.match(UUID_REGEX);
    if (pathMatch) return pathMatch[0];

    // 3. Cek hash router
    const hashMatch = window.location.hash.match(UUID_REGEX);
    if (hashMatch) return hashMatch[0];

    // 4. Cek sessionStorage / localStorage Fasih
    try {
      const storages = [sessionStorage, localStorage];
      for (const st of storages) {
        if (!st) continue;
        for (let i = 0; i < st.length; i++) {
          const k = st.key(i);
          if (/period|survey|assignment/i.test(k)) {
            const v = st.getItem(k);
            if (v) {
              const m = v.match(UUID_REGEX);
              if (m) return m[0];
            }
          }
        }
      }
    } catch (e) {}

    // 5. Cek elemen select / dropdown di DOM jika ada yang memuat UUID periode
    try {
      const selects = document.querySelectorAll('select, [data-value], [role="combobox"]');
      for (const el of selects) {
        const val = el.value || el.getAttribute('data-value') || '';
        if (UUID_REGEX.test(val)) return val.match(UUID_REGEX)[0];
      }
    } catch (e) {}

    return null;
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
        // Jika array berisi string/primitive, gabungkan dengan koma. Jika objek, konversi ke string ringkas.
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
   * Deteksi letak array data & metadata pagination pada respons JSON
   */
  function extractPageMetadata(jsonResponse) {
    let items = [];
    let totalItems = 0;
    let totalPages = 1;
    let currentPage = 0;

    if (!jsonResponse || typeof jsonResponse !== 'object') {
      return { items, totalItems, totalPages, currentPage };
    }

    // Periksa lokasi umum array data di backend Fasih/Spring Boot
    const candidates = [
      jsonResponse.data && jsonResponse.data.content,
      jsonResponse.data && jsonResponse.data.assignments,
      jsonResponse.data && jsonResponse.data.list,
      jsonResponse.data && Array.isArray(jsonResponse.data) ? jsonResponse.data : null,
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

    // Cari info total elemen & halaman
    const root = jsonResponse.data || jsonResponse;
    totalItems = root.totalElements ?? root.totalItems ?? root.total ?? items.length;
    totalPages = root.totalPages ?? root.pageCount ?? (totalItems && root.size ? Math.ceil(totalItems / root.size) : 1);
    currentPage = root.number ?? root.page ?? root.currentPage ?? 0;

    return { items, totalItems, totalPages, currentPage };
  }

  /**
   * Kelas Pengontrol Scraping
   */
  class ScraperTask {
    constructor(options = {}) {
      this.endpoint = options.endpoint || '';
      this.periodeId = options.periodeId || detectPeriode();
      this.pageSize = options.pageSize || 50;
      this.startPage = options.startPage !== undefined ? options.startPage : 0; // 0-based index default
      this.maxPages = options.maxPages || Infinity;
      this.delayMs = options.delayMs || 250;
      this.extraParams = options.extraParams || {};
      
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
     * Mengambil 1 halaman data dengan retry pintar untuk HTTP 429
     */
    async fetchSinglePage(pageIndex) {
      const u = new URL(this.endpoint, window.location.origin);
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

      let attempt = 0;
      const maxAttempts = 5;
      let backoffWait = 10000; // Mulai dari 10 detik bila kena 429

      while (attempt < maxAttempts) {
        if (this.isAborted) throw new Error('Dibatalkan oleh pengguna.');

        while (this.isPaused) {
          if (this.isAborted) throw new Error('Dibatalkan oleh pengguna.');
          await sleep(500);
        }

        try {
          const res = await fetch(u.toString(), {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include'
          });

          if (res.status === 429) {
            attempt++;
            this.onLog(`⚠️ Terkena limitasi akses Fasih (HTTP 429). Menunggu ${backoffWait / 1000} detik sebelum mencoba lagi (Percobaan ${attempt}/${maxAttempts})...`);
            await sleep(backoffWait);
            backoffWait *= 1.5; // Exponential backoff
            continue;
          }

          if (!res.ok) {
            throw new Error(`HTTP Error ${res.status}: ${res.statusText}`);
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

      this.onLog(`🚀 Memulai scraping daftar assignment...`);
      this.onLog(`📍 Endpoint: ${this.endpoint}`);
      if (this.periodeId) this.onLog(`📅 Periode ID: ${this.periodeId}`);

      let pageIndex = this.startPage;
      let totalPages = 1;
      let totalElements = 0;
      let pagesProcessed = 0;

      while (!this.isAborted && pageIndex < totalPages && pagesProcessed < this.maxPages) {
        this.onLog(`📄 Mengambil halaman ${pageIndex + 1}...`);
        
        const rawJson = await this.fetchSinglePage(pageIndex);
        const meta = extractPageMetadata(rawJson);

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
    detectPeriode,
    detectPeriodeFromUrl: detectPeriode, // alias backward compatibility
    flattenRecord,
    extractPageMetadata,
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
