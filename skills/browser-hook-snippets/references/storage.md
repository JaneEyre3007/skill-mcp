# Storage Hooks

适合 cookie、浏览器存储和表单值追踪。

## 1. Hook `document.cookie`

适合定位 cookie 是谁写进去的。

注意：这个 hook 只能看到 JS 侧的 `document.cookie = ...`。如果页面里的最终 cookie 实际来自服务端响应头 `Set-Cookie`，这里不会命中，必须同时去 Network 看对应响应头。

```js
(function () {
  function findCookieDescriptor() {
    let proto = Object.getPrototypeOf(document);
    while (proto) {
      const descriptor = Object.getOwnPropertyDescriptor(proto, 'cookie');
      if (descriptor) {
        return { owner: proto, descriptor };
      }
      proto = Object.getPrototypeOf(proto);
    }
    return null;
  }

  const found = findCookieDescriptor();
  if (!found || !found.descriptor || !found.descriptor.configurable) {
    console.warn('cookie descriptor unavailable');
    return;
  }

  const cookieDesc = found.descriptor;

  Object.defineProperty(found.owner, 'cookie', {
    configurable: true,
    enumerable: cookieDesc.enumerable,
    get() {
      const value = cookieDesc.get.call(this);
      console.log('[cookie:get]', value);
      return value;
    },
    set(value) {
      debugger;
      console.log('[cookie:set]', value);
      console.trace('[cookie:stack]');
      return cookieDesc.set.call(this, value);
    }
  });

  window.__restoreCookieHook = function () {
    Object.defineProperty(found.owner, 'cookie', cookieDesc);
    delete window.__restoreCookieHook;
  };
})();
```

优先沿原型链寻找 `cookie` 描述符并在真正的 owner 上覆写，不要默认假设一定挂在 `document` 实例或某个固定原型上。

如果用户怀疑“可能是 HTTP 写入，不是 JS 写入”，回答时应同时建议：

1. 盯产生该 cookie 前后的 XHR / fetch / document 请求。
2. 打开 Network 详情检查 `set-cookie` 响应头。
3. 只有确认不是 HTTP 头写入后，再继续扩大 `document.cookie` / storage / 拦截器 hook。

## 2. Hook `localStorage` / `sessionStorage`

适合定位 token、设备指纹缓存、一次性挑战值写入的位置。

```js
(function () {
  const rawSetItem = Storage.prototype.setItem;
  const rawGetItem = Storage.prototype.getItem;
  const rawRemoveItem = Storage.prototype.removeItem;

  Storage.prototype.setItem = function (key, value) {
    console.log('[storage:setItem]', this === localStorage ? 'local' : 'session', key, value);
    debugger;
    return rawSetItem.apply(this, arguments);
  };

  Storage.prototype.getItem = function (key) {
    const value = rawGetItem.apply(this, arguments);
    console.log('[storage:getItem]', this === localStorage ? 'local' : 'session', key, value);
    return value;
  };

  Storage.prototype.removeItem = function (key) {
    console.log('[storage:removeItem]', this === localStorage ? 'local' : 'session', key);
    return rawRemoveItem.apply(this, arguments);
  };

  window.__restoreStorageHook = function () {
    Storage.prototype.setItem = rawSetItem;
    Storage.prototype.getItem = rawGetItem;
    Storage.prototype.removeItem = rawRemoveItem;
    delete window.__restoreStorageHook;
  };
})();
```

如果目标站点直接用 `localStorage.foo = value` 这类属性赋值，`setItem` hook 不会命中；优先改盯调用方、请求上下文或具体 key 的读写路径，不要误判为没有写入。

```js
(function () {
  console.warn('Direct property assignment on Storage is not covered by setItem hooks. Use a request/header hook or a targeted breakpoint on the writer instead.');
})();
```

## 3. Hook 表单值

适合某个输入框的值被脚本反复读写的情况。

```js
(function () {
  const input = document.querySelector('#username');
  if (!input) {
    console.warn('target input not found');
    return;
  }

  let currentValue = input.value;
  Object.defineProperty(input, 'value', {
    configurable: true,
    get() {
      console.log('[input:get]', currentValue);
      return currentValue;
    },
    set(value) {
      console.log('[input:set]', value);
      debugger;
      currentValue = value;
    }
  });
})();
```
