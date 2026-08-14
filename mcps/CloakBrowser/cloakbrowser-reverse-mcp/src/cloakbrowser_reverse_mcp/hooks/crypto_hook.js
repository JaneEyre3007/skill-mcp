(() => {
  if (window.__mcp_crypto_hooked) return;
  window.__mcp_crypto_hooked = true;
  window.__mcp_crypto_log = window.__mcp_crypto_log || [];
  for (const name of ['btoa','atob']) {
    const orig = window[name];
    if (typeof orig !== 'function') continue;
    window[name] = function(v) {
      const r = orig.apply(this, arguments);
      try { window.__mcp_crypto_log.push({fn:name, input:String(v).slice(0,1000), output:String(r).slice(0,1000), stack:(new Error()).stack, ts:Date.now()}); } catch(e) {}
      return r;
    };
    window[name].toString = () => orig.toString();
  }
  const origStringify = JSON.stringify;
  JSON.stringify = function(v) {
    const r = origStringify.apply(this, arguments);
    try { window.__mcp_crypto_log.push({fn:'JSON.stringify', input:String(v).slice(0,1000), output:String(r).slice(0,1000), stack:(new Error()).stack, ts:Date.now()}); } catch(e) {}
    return r;
  };
  JSON.stringify.toString = () => origStringify.toString();
})();
