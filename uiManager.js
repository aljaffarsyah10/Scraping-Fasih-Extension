/**
 * Fasih Assignment Scraper - UI & Progress Modal (Fase 3)
 * 
 * Modul ini bertanggung jawab:
 * 1. Menyisipkan Tombol Aksi Terapung (Floating Action Button) di halaman Fasih SM.
 * 2. Menampilkan Dialog Modal Progres yang elegan menggunakan Web Components / Shadow DOM
 *    sehingga tidak bentrok dengan CSS/Tailwind bawaan Fasih SM.
 * 3. Menyediakan kontrol interaktif: Mulai, Jeda (Pause), Lanjut (Resume), dan Batal (Cancel).
 */

const FasihUI = (() => {
  let activeTask = null;
  let shadowRoot = null;
  let uiContainer = null;

  // Template HTML & CSS terisolasi (Shadow DOM)
  const styles = `
    :host {
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --bg: #ffffff;
      --text: #1e293b;
      --text-muted: #64748b;
      --border: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }

    /* Floating Trigger Button */
    .fasih-fab {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      background: linear-gradient(135deg, var(--primary), #1e40af);
      color: #ffffff;
      border: none;
      border-radius: 50px;
      padding: 12px 20px;
      box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.4), 0 8px 10px -6px rgba(37, 99, 235, 0.2);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      font-size: 14px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .fasih-fab:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 28px -5px rgba(37, 99, 235, 0.5);
    }

    .fasih-fab svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
    }

    /* Modal Backdrop */
    .fasih-modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.55);
      backdrop-filter: blur(3px);
      z-index: 1000000;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transition: all 0.25s ease;
    }

    .fasih-modal-backdrop.open {
      opacity: 1;
      visibility: visible;
    }

    /* Modal Dialog Box */
    .fasih-modal-card {
      background: var(--bg);
      border-radius: 16px;
      width: 480px;
      max-width: 92vw;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      overflow: hidden;
      border: 1px solid var(--border);
      transform: scale(0.95);
      transition: transform 0.25s ease;
    }

    .fasih-modal-backdrop.open .fasih-modal-card {
      transform: scale(1);
    }

    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #f8fafc;
    }

    .modal-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 20px;
      color: var(--text-muted);
      cursor: pointer;
      line-height: 1;
      padding: 4px;
      border-radius: 6px;
    }

    .close-btn:hover {
      background: #e2e8f0;
      color: var(--text);
    }

    .modal-body {
      padding: 20px;
    }

    /* Form Inputs */
    .form-group {
      margin-bottom: 14px;
    }

    .form-group label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--text);
    }

    .form-group input, .form-group select {
      width: 100%;
      box-sizing: border-box;
      padding: 9px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      font-size: 13px;
      color: var(--text);
      background: #ffffff;
      outline: none;
      transition: border-color 0.15s;
    }

    .form-group input:focus, .form-group select:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
    }

    .form-row {
      display: flex;
      gap: 12px;
    }

    .form-row .form-group {
      flex: 1;
    }

    /* Progress Display */
    .progress-box {
      margin-top: 16px;
      padding: 14px;
      background: #f8fafc;
      border-radius: 10px;
      border: 1px solid var(--border);
    }

    .progress-stats {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 8px;
    }

    .progress-bar-bg {
      height: 8px;
      background: #e2e8f0;
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 8px;
    }

    .progress-bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--primary), var(--success));
      border-radius: 4px;
      transition: width 0.3s ease;
    }

    .progress-status-text {
      font-size: 12px;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Modal Footer Buttons */
    .modal-footer {
      padding: 14px 20px;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      background: #f8fafc;
    }

    .btn {
      padding: 9px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }

    .btn-primary {
      background: var(--primary);
      color: white;
    }

    .btn-primary:hover {
      background: var(--primary-hover);
    }

    .btn-outline {
      background: white;
      border-color: var(--border);
      color: var(--text);
    }

    .btn-outline:hover {
      background: #f1f5f9;
    }

    .btn-warning {
      background: var(--warning);
      color: white;
    }

    .btn-danger {
      background: var(--danger);
      color: white;
    }

    .hidden {
      display: none !important;
    }
  `;

  function initUI() {
    if (document.getElementById('fasih-scraper-host')) return;

    uiContainer = document.createElement('div');
    uiContainer.id = 'fasih-scraper-host';
    document.body.appendChild(uiContainer);

    shadowRoot = uiContainer.attachShadow({ mode: 'open' });

    const styleEl = document.createElement('style');
    styleEl.textContent = styles;
    shadowRoot.appendChild(styleEl);

    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <!-- Floating Button -->
      <button class="fasih-fab" id="fab-trigger" title="Ekspor Data Assignment">
        <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
        <span>Ekspor Raw Assignment</span>
      </button>

      <!-- Modal Dialog -->
      <div class="fasih-modal-backdrop" id="modal-backdrop">
        <div class="fasih-modal-card">
          <div class="modal-header">
            <h3>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
              Ekspor Daftar Assignment (Raw)
            </h3>
            <button class="close-btn" id="btn-close">&times;</button>
          </div>
          
          <div class="modal-body">
            <div id="config-section">
              <div class="form-group">
                <label>Periode ID (Otomatis)</label>
                <input type="text" id="inp-periode" placeholder="Mendeteksi dari URL..." readonly />
              </div>

              <div class="form-group">
                <label>Endpoint API</label>
                <input type="text" id="inp-endpoint" value="/app/api/assignment-general/api/assignment/list" placeholder="/app/api/..." />
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>Maks Halaman</label>
                  <input type="number" id="inp-max-pages" placeholder="Semua (kosongkan)" min="1" />
                </div>
                <div class="form-group">
                  <label>Ukuran Halaman (Size)</label>
                  <select id="inp-page-size">
                    <option value="25">25 per hal</option>
                    <option value="50" selected>50 per hal</option>
                    <option value="100">100 per hal</option>
                  </select>
                </div>
              </div>

              <div class="form-group">
                <label>Format Unduhan</label>
                <select id="inp-format">
                  <option value="xlsx" selected>Excel Spreadsheet (.xlsx)</option>
                  <option value="csv">Comma Separated Values (.csv)</option>
                </select>
              </div>
            </div>

            <!-- Bagian Progres (Tampil saat scraping berlangsung) -->
            <div class="progress-box hidden" id="progress-section">
              <div class="progress-stats">
                <span id="stat-pages">Halaman 0 / 0</span>
                <span id="stat-rows">0 data</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progress-fill"></div>
              </div>
              <div class="progress-status-text" id="status-text">Siap memulai...</div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-outline" id="btn-cancel-modal">Tutup</button>
            <button class="btn btn-warning hidden" id="btn-pause">⏸️ Jeda</button>
            <button class="btn btn-danger hidden" id="btn-abort">🛑 Batalkan</button>
            <button class="btn btn-primary" id="btn-start">
              <span>🚀 Mulai Ekspor</span>
            </button>
          </div>
        </div>
      </div>
    `;

    shadowRoot.appendChild(wrapper);
    bindEvents();
  }

  function bindEvents() {
    const $ = (id) => shadowRoot.getElementById(id);

    const backdrop = $('modal-backdrop');
    const fab = $('fab-trigger');
    const btnClose = $('btn-close');
    const btnCancel = $('btn-cancel-modal');
    const btnStart = $('btn-start');
    const btnPause = $('btn-pause');
    const btnAbort = $('btn-abort');

    const inpPeriode = $('inp-periode');
    const inpEndpoint = $('inp-endpoint');
    const inpMaxPages = $('inp-max-pages');
    const inpPageSize = $('inp-page-size');
    const inpFormat = $('inp-format');

    const configSection = $('config-section');
    const progressSection = $('progress-section');
    const statPages = $('stat-pages');
    const statRows = $('stat-rows');
    const progressFill = $('progress-fill');
    const statusText = $('status-text');

    // Buka Modal
    fab.onclick = () => {
      // Auto detect periode
      if (window.FasihScraperEngine) {
        const detected = FasihScraperEngine.detectPeriodeFromUrl();
        inpPeriode.value = detected || '(Tidak terdeteksi di URL)';
      }
      backdrop.classList.add('open');
    };

    // Tutup Modal
    const closeModal = () => {
      if (activeTask && activeTask.isRunning) {
        if (!confirm('Scraping sedang berjalan. Apakah Anda yakin ingin menutup modal?')) return;
      }
      backdrop.classList.remove('open');
    };

    btnClose.onclick = closeModal;
    btnCancel.onclick = closeModal;

    // Mulai Scraping
    btnStart.onclick = async () => {
      if (!window.FasihScraperEngine) {
        alert('Modul FasihScraperEngine belum terpasang.');
        return;
      }

      const endpoint = inpEndpoint.value.trim();
      const periodeId = inpPeriode.value.includes('(') ? '' : inpPeriode.value.trim();
      const maxPages = inpMaxPages.value ? parseInt(inpMaxPages.value, 10) : Infinity;
      const pageSize = parseInt(inpPageSize.value, 10) || 50;

      activeTask = new FasihScraperEngine.ScraperTask({
        endpoint,
        periodeId,
        maxPages,
        pageSize,
        delayMs: 250,
        onProgress: (info) => {
          statPages.textContent = `Halaman ${info.currentPage} / ${info.totalPages || '?'}`;
          statRows.textContent = `${info.fetchedCount} / ${info.totalElements || '?'} data`;
          progressFill.style.width = `${info.percent}%`;
          statusText.textContent = `Mengambil data baris ${info.fetchedCount}... (${info.percent}%)`;
        },
        onLog: (msg) => {
          statusText.textContent = msg;
        }
      });

      // Update Tampilan ke Mode Running
      configSection.classList.add('hidden');
      progressSection.classList.remove('hidden');
      btnStart.classList.add('hidden');
      btnCancel.classList.add('hidden');
      btnPause.classList.remove('hidden');
      btnAbort.classList.remove('hidden');

      try {
        const results = await activeTask.run();
        statusText.textContent = `✅ Berhasil mengekstrak ${results.length} data.`;
        progressFill.style.width = '100%';

        // Trigger Callback untuk Fase 4 (Exporter)
        if (window.FasihExporter) {
          const fmt = inpFormat.value;
          statusText.textContent = `Menyiapkan unduhan ${fmt.toUpperCase()}...`;
          await FasihExporter.exportData(results, fmt, `Raw_Assignment_${periodeId || 'Fasih'}_${Date.now()}`);
        } else {
          // Fallback sederhana jika Fase 4 belum digabung
          console.log('Data terambil:', results);
          alert(`Scraping selesai! Terkumpul ${results.length} data baris.`);
        }
      } catch (err) {
        statusText.textContent = `❌ Terjadi kesalahan: ${err.message}`;
      } finally {
        btnPause.classList.add('hidden');
        btnAbort.classList.add('hidden');
        btnStart.classList.remove('hidden');
        btnStart.querySelector('span').textContent = '🔄 Mulai Ulang';
        btnCancel.classList.remove('hidden');
      }
    };

    // Jeda / Lanjut
    btnPause.onclick = () => {
      if (!activeTask) return;
      if (activeTask.isPaused) {
        activeTask.resume();
        btnPause.textContent = '⏸️ Jeda';
        btnPause.classList.remove('btn-success');
        btnPause.classList.add('btn-warning');
      } else {
        activeTask.pause();
        btnPause.textContent = '▶️ Lanjut';
        btnPause.classList.remove('btn-warning');
        btnPause.classList.add('btn-success');
      }
    };

    // Batalkan
    btnAbort.onclick = () => {
      if (!activeTask) return;
      if (confirm('Apakah Anda yakin ingin membatalkan scraping yang sedang berlangsung? Data yang sudah terambil tetap dapat diunduh.')) {
        activeTask.abort();
      }
    };
  }

  return {
    initUI
  };
})();

if (typeof window !== 'undefined') {
  window.FasihUI = FasihUI;
}
