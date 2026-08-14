(() => {
  if (window.__mcp_jsvmp_hooked) return;
  window.__mcp_jsvmp_hooked = true;
  window.__mcp_jsvmp_log = window.__mcp_jsvmp_log || [];
  const maxEntries = {{MAX_ENTRIES}};
  const proxyObjects = JSON.parse('{{PROXY_OBJECTS}}');
  function push(e) { try { if (window.__mcp_jsvmp_log.length < maxEntries) window.__mcp_jsvmp_log.push({...e, ts:Date.now(), stack:(new Error()).stack}); } catch(_) {} }
  for (const name of proxyObjects) {
    try {
      const obj = window[name];
      if (!obj || typeof obj !== 'object') continue;
      window[name] = new Proxy(obj, {
        get(target, prop, recv) { const val = Reflect.get(target, prop, recv); push({type:'get', object:name, key:String(prop), value:String(val).slice(0,200)}); return val; },
        apply(target, thisArg, args) { push({type:'apply', object:name, argc:args.length}); return Reflect.apply(target, thisArg, args); }
      });
    } catch(e) {}
  }
})();
