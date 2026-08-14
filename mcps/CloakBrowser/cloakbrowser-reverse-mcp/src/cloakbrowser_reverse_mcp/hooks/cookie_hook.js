(() => {
  if (window.__mcp_cookie_hooked) return;
  window.__mcp_cookie_hooked = true;
  window.__mcp_cookie_log = window.__mcp_cookie_log || [];
  const desc = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie') || Object.getOwnPropertyDescriptor(HTMLDocument.prototype, 'cookie');
  if (!desc || !desc.configurable) return;
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    get() { return desc.get.call(document); },
    set(v) { try { window.__mcp_cookie_log.push({value:String(v), stack:(new Error()).stack, ts:Date.now()}); } catch(e) {} return desc.set.call(document, v); }
  });
})();
