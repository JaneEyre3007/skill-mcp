(() => {
  if (window.__mcp_jsvmp_transparent_hooked) return;
  window.__mcp_jsvmp_transparent_hooked = true;
  window.__mcp_jsvmp_log = window.__mcp_jsvmp_log || [];
  const maxEntries = {{MAX_ENTRIES}};
  function push(e) { try { if (window.__mcp_jsvmp_log.length < maxEntries) window.__mcp_jsvmp_log.push({...e, ts:Date.now(), stack:(new Error()).stack}); } catch(_) {} }
  const origGet = Reflect.get;
  Reflect.get = function(target, prop, recv) { const val = origGet.apply(this, arguments); try { push({type:'reflect_get', key:String(prop), value:String(val).slice(0,200)}); } catch(e) {} return val; };
  Reflect.get.toString = () => origGet.toString();
})();
