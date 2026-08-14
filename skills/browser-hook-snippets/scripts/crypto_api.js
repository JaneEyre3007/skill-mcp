// browser-hook-snippets/scripts/crypto_api.js
// Hook WebCrypto.subtle 调用 + CryptoJS 静态方法
// 注入：DevTools Console（需页面已加载 crypto API）

(function () {
  'use strict';

  const FULL_LOG = false;

  // ---- WebCrypto.subtle ----
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const methods = ['encrypt', 'decrypt', 'sign', 'verify', 'digest', 'importKey', 'exportKey', 'generateKey', 'deriveBits', 'deriveKey'];
    const origSubtle = crypto.subtle;
    methods.forEach(function (m) {
      const origFn = origSubtle[m];
      if (typeof origFn === 'function') {
        origSubtle[m] = function () {
          const entry = {
            api: 'crypto.subtle.' + m,
            algo: arguments[0] ? (arguments[0].name || JSON.stringify(arguments[0]).substring(0, 50)) : '?',
            argCount: arguments.length,
          };
          console.log('[hook-crypto]', JSON.stringify(entry));
          return origFn.apply(origSubtle, arguments).then(function (result) {
            const outLen = result ? (result.byteLength || result.length || Object.keys(result).length) : 0;
            console.log('[hook-crypto-result]', m, 'output len =', outLen);
            return result;
          });
        };
      }
    });
    console.log('[hook] crypto.subtle installed');
  }

  // ---- CryptoJS ----
  if (typeof CryptoJS !== 'undefined') {
    const algos = ['MD5', 'SHA1', 'SHA256', 'SHA512', 'AES', 'DES', 'TripleDES', 'RC4', 'Rabbit', 'HmacMD5', 'HmacSHA1', 'HmacSHA256'];
    algos.forEach(function (algo) {
      if (CryptoJS[algo] && typeof CryptoJS[algo] === 'function') {
        const origFn = CryptoJS[algo];
        CryptoJS[algo] = function () {
          const input = typeof arguments[0] === 'string' ? arguments[0].substring(0, 40) + '...' : '[obj]';
          console.log('[hook-CryptoJS]', algo, 'input:', input);
          const result = origFn.apply(CryptoJS, arguments);
          console.log('[hook-CryptoJS]', algo, 'output:', result.toString().substring(0, 40) + '...');
          return result;
        };
      }
    });
    console.log('[hook] CryptoJS installed');
  }
})();
