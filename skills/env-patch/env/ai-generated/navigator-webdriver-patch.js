/**
  * @env-property {boolean} navigator.webdriver
 * @description 表示用户代理是否由自动化程序控制
 * @returns {boolean} 通常返回 false 以模拟真实浏览器环境
 * @compatibility Chrome 43+, Firefox 48+, Edge 79+, Safari 12+
 * @generated-by DeepSeek
 * @generated-at 2026-02-04T08:57:00.845Z
 */
(function() {
    // 检查是否已存在该属性
    if (typeof navigator !== 'undefined' && navigator.webdriver === undefined) {
        Object.defineProperty(navigator, 'webdriver', {
            value: false,
            writable: false,
            configurable: false,
            enumerable: true
        });
    }
})();
