# Runtime Hooks

适合动态代码、动态资源和 worker 侧执行链路。

## 1. Hook `JSON.parse` / `JSON.stringify`

适合请求体或响应体在 JSON 边界被处理时追踪数据。

```js
(function () {
  const rawParse = JSON.parse;
  const rawStringify = JSON.stringify;

  JSON.parse = function (text) {
    console.log('[json:parse]', text);
    return rawParse.apply(this, arguments);
  };

  JSON.stringify = function (value) {
    console.log('[json:stringify]', value);
    return rawStringify.apply(this, arguments);
  };
})();
```

## 2. Hook `eval` 和 `Function`

适合定位动态拼出来的代码。

```js
(function () {
  const rawEval = window.eval;
  const rawFunction = window.Function;

  window.eval = function (code) {
    console.log('[eval]', code);
    debugger;
    return rawEval.apply(this, arguments);
  };
  window.eval.toString = rawEval.toString.bind(rawEval);

  window.Function = function () {
    const source = arguments[arguments.length - 1];
    console.log('[Function]', source);
    debugger;
    return rawFunction.apply(this, arguments);
  };
  window.Function.toString = rawFunction.toString.bind(rawFunction);
})();
```

## 3. Hook `Blob` 和 `URL.createObjectURL`

适合定位动态拼出来的脚本、图片、下载内容。

```js
(function () {
  const RawBlob = window.Blob;
  const rawCreateObjectURL = URL.createObjectURL;

  window.Blob = function (parts, options) {
    console.log('[Blob]', parts, options);
    debugger;
    return new RawBlob(parts, options);
  };
  window.Blob.prototype = RawBlob.prototype;
  window.Blob.toString = RawBlob.toString.bind(RawBlob);

  URL.createObjectURL = function (object) {
    console.log('[URL.createObjectURL]', object);
    debugger;
    return rawCreateObjectURL.apply(this, arguments);
  };
})();
```

如果只想看文本型 Blob 内容：

```js
(function () {
  const RawBlob = window.Blob;
  window.Blob = function (parts, options) {
    const textParts = (parts || []).filter(part => typeof part === 'string');
    if (textParts.length) {
      console.log('[Blob:text]', textParts.join(''));
      debugger;
    }
    return new RawBlob(parts, options);
  };
  window.Blob.prototype = RawBlob.prototype;
})();
```

## 4. Hook `Worker`

适合定位被丢到 worker 里的加密、验签、解码逻辑。

```js
(function () {
  const RawWorker = window.Worker;
  window.Worker = function (scriptURL, options) {
    console.log('[Worker:new]', scriptURL, options);
    debugger;
    const worker = new RawWorker(scriptURL, options);

    const rawPostMessage = worker.postMessage;
    worker.postMessage = function (message, transfer) {
      console.log('[Worker:postMessage]', scriptURL, message, transfer);
      debugger;
      return rawPostMessage.apply(this, arguments);
    };

    worker.addEventListener('message', function (event) {
      console.log('[Worker:message]', scriptURL, event.data);
    });

    return worker;
  };
  window.Worker.prototype = RawWorker.prototype;
  window.Worker.toString = RawWorker.toString.bind(RawWorker);
})();
```

如果直接在 Console 里改写构造器没有生效，优先改成页面上下文注入版本再试。

## 5. Hook `setTimeout` / `setInterval`

适合定位周期性签名刷新、延迟执行逻辑，或只想定向观察含 `debugger` 的反调试定时器。

```js
(function () {
  const rawSetTimeout = window.setTimeout;
  const rawSetInterval = window.setInterval;

  function shouldLog(fn) {
    const source = typeof fn === 'function' ? fn.toString() : String(fn);
    return /debugger|sign|token|cookie/i.test(source);
  }

  window.setTimeout = function (fn, delay) {
    if (shouldLog(fn)) {
      console.log('[setTimeout]', delay, fn);
      console.trace('[setTimeout:stack]');
      debugger;
    }
    return rawSetTimeout.apply(this, arguments);
  };

  window.setInterval = function (fn, delay) {
    if (shouldLog(fn)) {
      console.log('[setInterval]', delay, fn);
      console.trace('[setInterval:stack]');
      debugger;
    }
    return rawSetInterval.apply(this, arguments);
  };
})();
```

默认只做定向观察，不要粗暴清空或拦截所有定时器；那样很容易把页面本身跑坏。
