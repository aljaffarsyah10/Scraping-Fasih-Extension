/**
 * Fasih Injected Hook (Main World)
 * Berjalan langsung di window context halaman Fasih SM sebelum skrip web berjalan.
 * Mengamati request API Fasih secara pasif untuk menangkap endpoint, parameter, dan header asli.
 */

(() => {
  if (window.__fasihMainHookLoaded) return;
  window.__fasihMainHookLoaded = true;

  window.__fasihLastCaptured = null;

  function notifyDetected(url, method, headers, body) {
    if (!url || typeof url !== 'string') return;
    if (url.includes('/api/') && (url.includes('assignment') || url.includes('penugasan') || url.includes('filter') || url.includes('list'))) {
      try {
        const u = new URL(url, window.location.origin);
        const endpointPath = u.pathname;
        const periodeId = u.searchParams.get('periodeId') || u.searchParams.get('periodId') || u.searchParams.get('periode');

        // Normalisasi headers
        const plainHeaders = {};
        if (headers instanceof Headers) {
          headers.forEach((v, k) => { plainHeaders[k] = v; });
        } else if (headers && typeof headers === 'object') {
          Object.assign(plainHeaders, headers);
        }

        const detail = {
          fullUrl: url,
          pathname: endpointPath,
          periodeId: periodeId || null,
          params: Object.fromEntries(u.searchParams.entries()),
          headers: plainHeaders,
          method: method || 'GET',
          body: body || null,
          timestamp: new Date().toISOString()
        };

        window.__fasihLastCaptured = detail;

        window.dispatchEvent(new CustomEvent('__fasih_api_sniffed', { detail }));
      } catch (e) {}
    }
  }

  // Intercept window.fetch
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
    const options = args[1] || {};
    const method = options.method || 'GET';
    const headers = options.headers || {};
    notifyDetected(url, method, headers, options.body);
    return origFetch.apply(this, args);
  };

  // Intercept XMLHttpRequest
  const origOpen = XMLHttpRequest.prototype.open;
  const origSetReqHeader = XMLHttpRequest.prototype.setRequestHeader;
  const origSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url) {
    this._url = url;
    this._method = method;
    this._headers = {};
    return origOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.setRequestHeader = function (header, value) {
    if (!this._headers) this._headers = {};
    this._headers[header] = value;
    return origSetReqHeader.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function (body) {
    notifyDetected(this._url, this._method, this._headers, body);
    return origSend.apply(this, arguments);
  };
})();
