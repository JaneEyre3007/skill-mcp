(() => {
  if (window.__mcp_runtime_probe) return;
  window.__mcp_runtime_probe = true;
  window.__mcp_runtime_log = window.__mcp_runtime_log || [];
  for (const objName of ['navigator','screen','document','window']) {
    try {
      const obj = objName === 'window' ? window : window[objName];
      for (const k of Object.keys(obj).slice(0, 200)) {
        try { window.__mcp_runtime_log.push({object:objName, key:k, value:String(obj[k]).slice(0,200), ts:Date.now()}); } catch(e) {}
      }
    } catch(e) {}
  }
})();
