// browser-hook-snippets/scripts/storage.js
// Hook localStorage + sessionStorage 读写
// 注入：DevTools Console

(function () {
  'use strict';

  ['localStorage', 'sessionStorage'].forEach(function (storageName) {
    var storage = window[storageName];
    if (!storage) return;

    var origSetItem = storage.setItem;
    storage.setItem = function (key, value) {
      console.log('[hook-' + storageName + '-set]', key, '=', value.substring(0, 80));
      console.trace('[hook-' + storageName + '-set] call stack');
      return origSetItem.apply(storage, arguments);
    };

    var origGetItem = storage.getItem;
    storage.getItem = function (key) {
      var val = origGetItem.apply(storage, arguments);
      if (val !== null) {
        console.log('[hook-' + storageName + '-get]', key, 'len =', val.length);
      }
      return val;
    };

    var origRemoveItem = storage.removeItem;
    storage.removeItem = function (key) {
      console.log('[hook-' + storageName + '-remove]', key);
      return origRemoveItem.apply(storage, arguments);
    };

    console.log('[hook]', storageName, 'installed');
  });
})();
