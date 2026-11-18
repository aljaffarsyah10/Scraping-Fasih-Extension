/**
 * Fasih Injected Hook (Main World)
 * Berjalan langsung di window context halaman Fasih SM sebelum skrip web berjalan.
 * Mengamati request API Fasih secara pasif untuk menangkap endpoint daftar penugasan asli.
 */

(() => {
  if (window.__fasihMainHookLoaded) return;
  window.__fasihMainHookLoaded = true;

  function notifyDetected(url, method) {
    if (!url || typeof url !== 'string') return;
    // Cari request yang berkaitan dengan assignment/penugasan
    if (url.includes('/api/') && (url.includes('assignment') || url.includes('penugasan') || url.includes('filter') || url.includes('list'))) {
      try {
        const u = new URL(url, window.location.origin);
        const endpointPath = u.pathname;
        const periodeId = u.searchParams.get('periodeId') || u.searchParams.get('periodId') || u.searchParams.get('periode');

        window.dispatchEvent(new CustomEvent('__fasih_api_sniffed', {
          detail: {
            fullUrl: url,
            pathname: endpointPath,
            periodeId: periodeId || null,
            params: Object.fromEntries(u.searchParams.entries())
          }
        }));
      } catch (e) {}
    }
  }

  // Intercept window.fetch
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
    const method = (args[1] && args[1].method) || 'GET';
    notifyDetected(url, method);
    return origFetch.apply(this, args);
  };

  // Intercept XMLHttpRequest
  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    notifyDetected(url, method);
    return origOpen.apply(this, arguments);
  };
})();
