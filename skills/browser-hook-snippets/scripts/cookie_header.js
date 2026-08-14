// browser-hook-snippets/scripts/cookie_header.js
// Hook document.cookie 写入 + header 注入观察
// 注入：DevTools Console（越早越好，建议页面加载前注入）

(function () {
  'use strict';

  const FULL_LOG = false; // true = 完整 cookie value；false = 仅 key + 长度

  // ---- document.cookie 写入 ----
  const desc = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie') ||
    Object.getOwnPropertyDescriptor(HTMLDocument.prototype, 'cookie');
  if (desc && desc.configurable) {
    Object.defineProperty(document, 'cookie', {
      get: function () { return desc.get.call(document); },
      set: function (val) {
        const parts = val.split(';')[0].split('=');
        const key = parts[0].trim();
        const value = parts.slice(1).join('=');
        const entry = {
          key,
          valLen: value.length,
          valPreview: FULL_LOG ? value : (value.substring(0, 20) + '...'),
        };
        console.log('[hook-cookie-set]', JSON.stringify(entry));
        console.trace('[hook-cookie-set] call stack');
        desc.set.call(document, val);
      },
      configurable: true,
    });
    console.log('[hook] cookie installed');
  } else {
    console.warn('[hook] cookie descriptor not configurable');
  }

  // ---- Headers 构造（观察 fetch/XHR 注入哪些 header）----
  const OrigHeaders = window.Headers;
  if (OrigHeaders) {
    window.Headers = function (init) {
      const headers = new OrigHeaders(init);
      const origSet = headers.set;
      headers.set = function (name, value) {
        console.log('[hook-header-set]', name, '=', FULL_LOG ? value : (value.substring(0, 40) + '...'));
        return origSet.call(headers, name, value);
      };
      const origAppend = headers.append;
      headers.append = function (name, value) {
        console.log('[hook-header-append]', name, '=', FULL_LOG ? value : (value.substring(0, 40) + '...'));
        return origAppend.call(headers, name, value);
      };
      return headers;
    };
    console.log('[hook] Headers constructor installed');
  }
})();
