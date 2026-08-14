(() => {
  if (window.__mcp_xhr_hooked) return;
  window.__mcp_xhr_hooked = true;
  window.__mcp_xhr_log = window.__mcp_xhr_log || [];
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  const origSet = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this.__mcp = { method, url: String(url), headers: {}, stack: (new Error()).stack, ts: Date.now() };
    return origOpen.call(this, method, url, ...rest);
  };
  XMLHttpRequest.prototype.setRequestHeader = function(k, v) {
    try { if (this.__mcp) this.__mcp.headers[k] = v; } catch(e) {}
    return origSet.call(this, k, v);
  };
  XMLHttpRequest.prototype.send = function(body) {
    try {
      const info = this.__mcp || {};
      info.body = body == null ? null : String(body).slice(0, 5000);
      window.__mcp_xhr_log.push(info);
    } catch(e) {}
    return origSend.call(this, body);
  };
})();
