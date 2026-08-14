// browser-hook-snippets/scripts/xhr_fetch.js
// 同时 hook XHR 和 fetch，输出请求 URL/method/headers，带调用栈
// 注入：DevTools Console（页面加载前最早注入时机：Sources 首个脚本暂停后注入）

(function () {
  'use strict';

  const FULL_LOG = false; // true = 完整 body/headers；false = 摘要

  // ---- XHR ----
  const origXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    this._hooked = { method, url };
    return origXHROpen.apply(this, arguments);
  };

  const origXHRSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function (body) {
    const h = this._hooked || {};
    const meta = {
      target: 'xhr',
      event: 'send',
      method: h.method || '?',
      url: h.url || '?',
      bodyLen: body ? (body.length || body.byteLength || '?') : 0,
    };
    if (FULL_LOG) meta.body = body;
    console.log('[hook-xhr]', JSON.stringify(meta));
    console.trace('[hook-xhr] call stack');

    this.addEventListener('load', function () {
      const rmeta = {
        target: 'xhr',
        event: 'response',
        method: h.method || '?',
        url: h.url || '?',
        status: this.status,
        respLen: this.responseText ? this.responseText.length : 0,
      };
      console.log('[hook-xhr-resp]', JSON.stringify(rmeta));
    });
    return origXHRSend.apply(this, arguments);
  };

  // ---- fetch ----
  const origFetch = window.fetch;
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input.url || '?');
    const method = (init && init.method) || 'GET';
    const meta = {
      target: 'fetch',
      event: 'send',
      method,
      url,
      bodyLen: init && init.body ? init.body.length : 0,
    };
    console.log('[hook-fetch]', JSON.stringify(meta));
    console.trace('[hook-fetch] call stack');

    return origFetch.apply(this, arguments).then(function (resp) {
      const rmeta = {
        target: 'fetch',
        event: 'response',
        method,
        url,
        status: resp.status,
      };
      console.log('[hook-fetch-resp]', JSON.stringify(rmeta));
      return resp;
    });
  };

  console.log('[hook] xhr+fetch installed');
})();
