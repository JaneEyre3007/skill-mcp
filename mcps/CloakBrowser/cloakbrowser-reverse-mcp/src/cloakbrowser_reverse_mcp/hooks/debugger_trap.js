(() => {
  if (window.__mcp_debugger_bypass) return;
  window.__mcp_debugger_bypass = true;
  const origSetInterval = window.setInterval;
  const origSetTimeout = window.setTimeout;
  function safeTimer(orig) {
    return function(fn, delay, ...rest) {
      const src = String(fn);
      if (src.includes('debugger')) return 0;
      return orig.call(this, fn, delay, ...rest);
    };
  }
  window.setInterval = safeTimer(origSetInterval);
  window.setTimeout = safeTimer(origSetTimeout);
})();
