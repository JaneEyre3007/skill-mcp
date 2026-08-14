/**
  * @env-property {string} window.userAgent
 * @description 返回浏览器的用户代理字符串
 * @returns {string} 用户代理字符串
 * @compatibility Chrome, Firefox, Safari, Edge
 * @generated-by DeepSeek
 * @generated-at 2026-02-04T09:00:20.414Z
 */
(function() {
    if (typeof window !== 'undefined' && !window.userAgent) {
        Object.defineProperty(window, 'userAgent', {
            value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            writable: false,
            configurable: true,
            enumerable: true
        });
    }
})();
