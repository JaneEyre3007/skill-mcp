(() => {
  if (window.__mcp_fetch_hooked) return;
  window.__mcp_fetch_hooked = true;
  window.__mcp_fetch_log = window.__mcp_fetch_log || [];
  window.__mcp_fetch_initiator_log = window.__mcp_fetch_initiator_log || [];
  const origFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    const method = (init && init.method) || (input && input.method) || 'GET';
    const entry = { url, method, headers: (init && init.headers) || null, body: init && init.body ? String(init.body).slice(0,5000) : null, stack: (new Error()).stack, timestamp: Date.now() };
    try { window.__mcp_fetch_log.push(entry); window.__mcp_fetch_initiator_log.push({url, method, stack: entry.stack, ts: entry.timestamp}); } catch(e) {}
    return origFetch.apply(this, arguments);
  };
  window.fetch.toString = () => origFetch.toString();
})();
