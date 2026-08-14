# Network Hooks

适合请求链路、请求头、实时消息和页面上下文注入。

## 1. Hook `XMLHttpRequest.open`

适合按 URL 片段盯请求。

```js
(function () {
  const rawOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    if (String(url).includes('MmEwMD')) {
      debugger;
      console.log('[xhr:open]', method, url);
    }
    return rawOpen.apply(this, arguments);
  };
})();
```

## 2. Hook `XMLHttpRequest.setRequestHeader`

适合盯 `Authorization`、`x-sign` 之类的头。

```js
(function () {
  const rawSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.setRequestHeader = function (key, value) {
    if (key === 'Authorization') {
      debugger;
      console.log('[xhr:header]', key, value);
    }
    return rawSetHeader.apply(this, arguments);
  };
})();
```

## 3. Hook `fetch`

适合现代站点不用 XHR 的情况。

```js
(function () {
  const rawFetch = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : input.url;
    if (url && url.includes('/api/')) {
      debugger;
      console.log('[fetch]', url, init);
      console.trace('[fetch:stack]');
    }
    return rawFetch.apply(this, arguments);
  };
})();
```

如果用户要的是“这个请求到底是谁发起的”，默认优先补 `console.trace()`，因为很多环境里没有现成的 request initiator 能力。

如果目标站点疑似 SDK 拦截器或双通道请求，不要只贴这一段；应同时给出 `XMLHttpRequest` 和 `fetch` 两个 hook，避免只盯到一半链路。

## 4. Hook `WebSocket.send`

适合盯实时推送的数据上行。

```js
(function () {
  const rawSend = WebSocket.prototype.send;
  WebSocket.prototype.send = function (data) {
    console.log('[ws:send]', data);
    debugger;
    return rawSend.apply(this, arguments);
  };
})();
```

## 4.5 Hook `$.ajax`

适合老站点或 jQuery 包装层里统一加参数、改 header 的情况。

```js
(function () {
  if (!window.jQuery || typeof window.jQuery.ajax !== 'function') {
    console.warn('jQuery.ajax unavailable');
    return;
  }

  const rawAjax = window.jQuery.ajax;
  window.jQuery.ajax = function (options) {
    if (options && typeof options === 'object') {
      console.log('[jquery:ajax]', {
        url: options.url,
        method: options.type || options.method,
        data: options.data,
        headers: options.headers
      });
      console.trace('[jquery:ajax:stack]');
      debugger;
    }
    return rawAjax.apply(this, arguments);
  };
})();
```

如果页面明显走 jQuery 包装层，优先 hook `$.ajax`，再决定是否继续下钻到 `xhr`。

如果还要看下行消息：

```js
(function () {
  const rawAddEventListener = WebSocket.prototype.addEventListener;
  WebSocket.prototype.addEventListener = function (type, listener) {
    if (type === 'message') {
      const wrapped = function (event) {
        console.log('[ws:message]', event.data);
        return listener.apply(this, arguments);
      };
      return rawAddEventListener.call(this, type, wrapped);
    }
    return rawAddEventListener.apply(this, arguments);
  };
})();
```

## 5. Hook `window.postMessage`

适合 iframe、页面与扩展、页面与 worker 包装层之间的数据传递。

```js
(function () {
  const rawPostMessage = window.postMessage;
  window.postMessage = function (message, targetOrigin, transfer) {
    console.log('[window.postMessage:send]', message, targetOrigin, transfer);
    debugger;
    return rawPostMessage.apply(this, arguments);
  };

  window.addEventListener('message', function (event) {
    console.log('[window.postMessage:recv]', event.origin, event.data);
  }, true);
})();
```

## 页面上下文注入模板

当 DevTools Console 作用域不够时，用这个模板把 hook 注入页面上下文：

```js
const inject = function () {
  const rawOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function () {
    console.log('[xhr:open]', arguments[1]);
    console.trace('[xhr:stack]');
    return rawOpen.apply(this, arguments);
  };
};

const script = document.createElement('script');
script.textContent = '(' + inject + ')()';
(document.head || document.documentElement).appendChild(script);
script.remove();
```
