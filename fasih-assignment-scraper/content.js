/**
 * Fasih Assignment Scraper - Content Script Entry Point
 * Berjalan otomatis pada https://fasih-sm.bps.go.id/app/*
 */

(() => {
  if (window.__fasihScraperContentInit) return;
  window.__fasihScraperContentInit = true;

  console.log('%c🚀 [Fasih Assignment Raw Exporter] Ekstensi Aktif', 'background: #2563eb; color: white; font-weight: bold; padding: 4px 8px; border-radius: 4px;');

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
  // Menangkap perubahan URL saat berpindah menu tanpa reload halaman utuh
  let lastUrl = window.location.href;
  const urlObserver = new MutationObserver(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      setupUIOnPage();
    }
  });

  urlObserver.observe(document.body, { childList: true, subtree: true });

  // Tangkap event popstate (tombol Back/Forward browser)
  window.addEventListener('popstate', setupUIOnPage);
})();
