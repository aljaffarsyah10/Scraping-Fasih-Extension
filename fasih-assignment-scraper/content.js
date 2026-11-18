/**
 * Fasih Assignment Scraper - Content Script Entry Point
 * Berjalan otomatis pada https://fasih-sm.bps.go.id/app/*
 */

(() => {
  if (window.__fasihScraperContentInit) return;
  window.__fasihScraperContentInit = true;

  console.log('%c🚀 [Fasih Assignment Raw Exporter] Ekstensi Aktif', 'background: #2563eb; color: white; font-weight: bold; padding: 4px 8px; border-radius: 4px;');

  window.__fasihSniffedEndpoint = null;
  window.__fasihSniffedPeriode = null;
  window.__fasihSniffedParams = {};
  window.__fasihSniffedHeaders = {};
  window.__fasihSniffedBody = null;
  window.__fasihSniffedMethod = null;

  // Tangkap event hasil sniffing dari injected-hook.js
  window.addEventListener('__fasih_api_sniffed', (e) => {
    const detail = e.detail;
    if (detail && detail.pathname) {
      window.__fasihSniffedEndpoint = detail.pathname;
      if (detail.periodeId) {
        window.__fasihSniffedPeriode = detail.periodeId;
      }
      if (detail.params) {
        window.__fasihSniffedParams = detail.params;
      }
      if (detail.headers) {
        window.__fasihSniffedHeaders = detail.headers;
      }
      if (detail.body) {
        window.__fasihSniffedBody = detail.body;
      }
      if (detail.method) {
        window.__fasihSniffedMethod = detail.method;
      }
      console.log('%c🎯 [Fasih Scraper] Request Terdeteksi:', 'color: #10b981; font-weight: bold;', {
        endpoint: detail.pathname,
        method: detail.method,
        periodeId: detail.periodeId,
        params: detail.params,
        headers: detail.headers
      });
    }
  });

  function setupUIOnPage() {
    // Tampilkan UI jika user berada di dalam aplikasi Fasih SM
    if (window.location.pathname.startsWith('/app/')) {
      if (window.FasihUI) {
        window.FasihUI.initUI();
      }
    }
  }

  // Jalankan saat dokumen siap
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupUIOnPage);
  } else {
    setupUIOnPage();
  }

  // Dukungan Navigasi SPA (Single Page Application):
  let lastUrl = window.location.href;
  const urlObserver = new MutationObserver(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      setupUIOnPage();
    }
  });

  urlObserver.observe(document.body, { childList: true, subtree: true });
  window.addEventListener('popstate', setupUIOnPage);
})();
