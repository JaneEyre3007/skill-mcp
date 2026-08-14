(() => {
  const path = '{{FUNCTION_PATH}}';
  const maxCaptures = {{MAX_CAPTURES}};
  const logArgs = {{LOG_ARGS}};
  const logReturn = {{LOG_RETURN}};
  const logStack = {{LOG_STACK}};
  window.__mcp_trace_logs = window.__mcp_trace_logs || {};
  const parts = path.split('.');
  let parent = window;
  for (let i = 0; i < parts.length - 1; i++) { parent = parent[parts[i]]; if (!parent) return; }
  const fn = parts[parts.length - 1];
  const orig = parent[fn];
  if (typeof orig !== 'function' || orig.__mcp_traced) return;
  window.__mcp_trace_logs[path] = [];
  function wrapper(...args) {
    const entry = {ts: Date.now()};
    if (logArgs) entry.args = args.map(a => { try { return JSON.parse(JSON.stringify(a)); } catch(e) { return String(a); } });
    if (logStack) entry.stack = (new Error()).stack;
    const ret = orig.apply(this, args);
    if (logReturn) { try { entry.return = JSON.parse(JSON.stringify(ret)); } catch(e) { entry.return = String(ret); } }
    if (window.__mcp_trace_logs[path].length < maxCaptures) window.__mcp_trace_logs[path].push(entry);
    return ret;
  }
  wrapper.__mcp_traced = true;
  wrapper.toString = () => orig.toString();
  parent[fn] = wrapper;
})();
