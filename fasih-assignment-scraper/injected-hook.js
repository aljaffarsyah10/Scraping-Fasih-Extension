/**
 * Fasih Injected Hook (Main World)
 * Berjalan langsung di window context halaman Fasih SM sebelum skrip web berjalan.
 * Mengamati request API Fasih secara pasif untuk menangkap endpoint, parameter, XSRF token, dan payload asli.
 */

(() => {
  if (window.__fasihMainHookLoaded) return;
  window.__fasihMainHookLoaded = true;

  window.__fasihLastCaptured = null;
  window.__fasihSniffedToken = null;

  // 1. Ekstrak XSRF token dari cookie langsung saat script mulai
  function tryReadXsrfCookie() {
    try {
      const m = document.cookie.match(/(?:^|;\s*)(?:XSRF-TOKEN|XSRF_TOKEN|_csrf|CSRF-TOKEN)=([^;]+)/i);
      if (m && m[1]) {
        window.__fasihSniffedToken = decodeURIComponent(m[1]);
      }
    } catch (e) {}
  }
  tryReadXsrfCookie();

  function notifyDetected(url, method, headers, body) {
    if (!url || typeof url !== 'string') return;

    // Normalisasi headers
    const plainHeaders = {};
    if (headers instanceof Headers) {
      headers.forEach((v, k) => { plainHeaders[k.toLowerCase()] = v; });
    } else if (headers && typeof headers === 'object') {
      for (const [k, v] of Object.entries(headers)) {
        if (v) plainHeaders[k.toLowerCase()] = v;
      }
    }

    // Tangkap XSRF token dari header apapun yang lewat
    for (const [k, v] of Object.entries(plainHeaders)) {
      if (/xsrf|csrf/i.test(k) && v) {
        window.__fasihSniffedToken = v;
      }
    }

    // Tangkap endpoint daftar penugasan
    if (url.includes('/api/') && (url.includes('assignment') || url.includes('datatable') || url.includes('penugasan'))) {
      try {
        const origin = window.location.origin;
        const u = new URL(url, origin);
        const endpointPath = u.pathname;
        let periodeId = u.searchParams.get('surveyPeriodId') || u.searchParams.get('periodeId') || u.searchParams.get('periodId') || u.searchParams.get('periode');

        // Cek jika surveyPeriodId ada di dalam payload body POST
        let bodyObj = null;
        if (body && typeof body === 'string') {
          try {
            bodyObj = JSON.parse(body);
          } catch (e) {}
        } else if (body && typeof body === 'object') {
          bodyObj = body;
        }

        if (!periodeId && bodyObj && bodyObj.assignmentExtraParam && bodyObj.assignmentExtraParam.surveyPeriodId) {
          periodeId = bodyObj.assignmentExtraParam.surveyPeriodId;
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

        // Simpan hanya request datatable utama ke global
        if (endpointPath.includes('datatable-all-user-survey-periode') && !endpointPath.includes('aggregation')) {
          window.__fasihLastCaptured = detail;
          window.__fasihSniffedEndpoint = endpointPath;
          if (periodeId) window.__fasihSniffedPeriode = periodeId;
          if (body) window.__fasihSniffedBody = body;
        }

        window.dispatchEvent(new CustomEvent('__fasih_api_sniffed', { detail }));
      } catch (e) {}
    }
  }

  // Intercept window.fetch
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    let url = '';
    let options = {};
    if (typeof args[0] === 'string' || (args[0] && typeof args[0].toString === 'function')) {
      url = args[0].toString();
      options = args[1] || {};
    } else if (args[0] && typeof args[0] === 'object') {
      url = args[0].url || '';
      options = args[0];
    }

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
    if (/xsrf|csrf/i.test(header) && value) {
      window.__fasihSniffedToken = value;
    }
    return origSetReqHeader.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function (body) {
    notifyDetected(this._url, this._method, this._headers, body);
    return origSend.apply(this, arguments);
  };
})();
