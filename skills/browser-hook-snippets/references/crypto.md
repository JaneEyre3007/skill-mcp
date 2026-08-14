# Crypto And Encoding Hooks

适合 base64、WebCrypto、随机数和编码边界。

## 1. Hook `atob` / `btoa`

适合定位 base64 编解码边界。

```js
(function () {
  const rawAtob = window.atob;
  const rawBtoa = window.btoa;

  window.atob = function (input) {
    const output = rawAtob.apply(this, arguments);
    console.log('[atob]', input, output);
    debugger;
    return output;
  };
  window.atob.toString = rawAtob.toString.bind(rawAtob);

  window.btoa = function (input) {
    const output = rawBtoa.apply(this, arguments);
    console.log('[btoa]', input, output);
    debugger;
    return output;
  };
  window.btoa.toString = rawBtoa.toString.bind(rawBtoa);
})();
```

## 2. Hook `crypto.subtle`

适合定位 WebCrypto 的摘要、加密、签名入口。

```js
(function () {
  if (!window.crypto || !window.crypto.subtle || typeof SubtleCrypto === 'undefined') {
    console.warn('crypto.subtle unavailable');
    return;
  }

  const subtleProto = SubtleCrypto.prototype;

  function hookMethod(name) {
    if (typeof subtleProto[name] !== 'function') {
      return;
    }
    const raw = subtleProto[name];
    subtleProto[name] = async function () {
      console.log('[subtle:' + name + ']', arguments[0], arguments[1]);
      debugger;
      return raw.apply(this, arguments);
    };
  }

  ['digest', 'encrypt', 'decrypt', 'sign', 'verify', 'importKey', 'deriveBits', 'deriveKey'].forEach(hookMethod);
})();
```

优先改原型而不是 `window.crypto.subtle` 实例本身，这样在更多浏览器里兼容性更稳。

如果要把 `ArrayBuffer` 参数转成可读十六进制：

```js
function toHex(buffer) {
  const view = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : new Uint8Array(buffer.buffer || buffer);
  return Array.from(view, b => b.toString(16).padStart(2, '0')).join('');
}
```

## 3. Hook `crypto.getRandomValues`

适合定位 nonce、随机挑战值、一次性盐值的来源。

```js
(function () {
  if (!window.crypto || typeof window.crypto.getRandomValues !== 'function' || typeof Crypto === 'undefined') {
    console.warn('crypto.getRandomValues unavailable');
    return;
  }

  const rawGetRandomValues = Crypto.prototype.getRandomValues;
  Crypto.prototype.getRandomValues = function (typedArray) {
    const result = rawGetRandomValues.apply(this, arguments);
    console.log('[crypto.getRandomValues]', typedArray.constructor.name, Array.from(result));
    debugger;
    return result;
  };
})();
```

优先改 `Crypto.prototype`，避免某些浏览器里实例方法不可直接覆写。

## 4. Hook `TextEncoder` / `TextDecoder`

适合数据在进入哈希、签名、加密前先做 UTF-8 编码的情况。

```js
(function () {
  const rawEncode = TextEncoder.prototype.encode;
  TextEncoder.prototype.encode = function (input) {
    const output = rawEncode.apply(this, arguments);
    console.log('[TextEncoder.encode]', input, output);
    return output;
  };

  const rawDecode = TextDecoder.prototype.decode;
  TextDecoder.prototype.decode = function (input) {
    const output = rawDecode.apply(this, arguments);
    console.log('[TextDecoder.decode]', input, output);
    return output;
  };
})();
```
