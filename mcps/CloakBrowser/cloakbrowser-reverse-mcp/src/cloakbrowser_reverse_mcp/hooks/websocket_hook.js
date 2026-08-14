(() => {
  if (window.__mcp_ws_hooked) return;
  window.__mcp_ws_hooked = true;
  window.__mcp_ws_log = window.__mcp_ws_log || [];
  const OrigWS = window.WebSocket;
  window.WebSocket = function(url, protocols) {
    const ws = protocols === undefined ? new OrigWS(url) : new OrigWS(url, protocols);
    try { window.__mcp_ws_log.push({type:'connect', url:String(url), stack:(new Error()).stack, ts:Date.now()}); } catch(e) {}
    const origSend = ws.send;
    ws.send = function(data) {
      try { window.__mcp_ws_log.push({type:'send', url:String(url), data:String(data).slice(0,5000), ts:Date.now()}); } catch(e) {}
      return origSend.call(this, data);
    };
    ws.addEventListener('message', ev => { try { window.__mcp_ws_log.push({type:'message', url:String(url), data:String(ev.data).slice(0,5000), ts:Date.now()}); } catch(e) {} });
    return ws;
  };
  window.WebSocket.prototype = OrigWS.prototype;
})();
