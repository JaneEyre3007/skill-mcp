# run.js 最小骨架

这份文档给的是“起步骨架”，不是可直接套所有站点的万能模板。

目标只有两个：

1. 保证加载顺序正确
2. 把所有改动集中在 `run.js`

## 最小骨架

```javascript
const env = require('./env_core');
const _process = process;

function makeDocument() {
    const document = {
        cookie: '',
        readyState: 'complete',
        createElement(tag) {
            if (tag === 'canvas') {
                return {
                    getContext() {
                        return {
                            measureText(text) {
                                return { width: String(text).length * 8 };
                            },
                        };
                    },
                };
            }

            return {
                style: {},
                getContext: undefined,
            };
        },
        getElementsByTagName() {
            return [];
        },
        addEventListener() {},
        removeEventListener() {},
    };

    return document;
}

function makeNavigator() {
    return {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        webdriver: false,
        language: 'zh-CN',
        languages: ['zh-CN', 'zh', 'en-US', 'en'],
        platform: 'Win32',
    };
}

function makeLocation() {
    return {
        href: 'https://example.com/',
        origin: 'https://example.com',
        protocol: 'https:',
        host: 'example.com',
        hostname: 'example.com',
        pathname: '/',
        search: '',
        hash: '',
    };
}

const fakeDocument = makeDocument();
const fakeNavigator = makeNavigator();
const fakeLocation = makeLocation();

const fakeWindow = {
    document: fakeDocument,
    navigator: fakeNavigator,
    location: fakeLocation,
    addEventListener() {},
    removeEventListener() {},
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    Math,
    Date,
    JSON,
};

fakeWindow.window = fakeWindow;
fakeWindow.self = fakeWindow;
fakeWindow.top = fakeWindow;
fakeWindow.parent = fakeWindow;
fakeWindow.globalThis = fakeWindow;

env.init({
    window: env.createProxy(fakeWindow, 'window', 0),
    document: env.createProxy(fakeDocument, 'document', 0),
    navigator: env.createProxy(fakeNavigator, 'navigator', 0),
    location: env.createProxy(fakeLocation, 'location', 0),
});

Object.defineProperty(global, 'chrome', {
    value: undefined,
    configurable: true,
    writable: true,
});

_process.on('uncaughtException', (err) => {
    console.error('[uncaughtException]', err && err.stack ? err.stack : err);
});

_process.on('unhandledRejection', (err) => {
    console.error('[unhandledRejection]', err && err.stack ? err.stack : err);
});

require('./main.js');

console.log('entry type =', typeof window.sign);
```

## 应该优先改哪里

先改这些：

1. `makeDocument()`
2. `makeNavigator()`
3. `makeLocation()`
4. `fakeWindow` 上的少量宿主方法
5. 最后的签名调用方式

不要先改这些：

1. `env_core.js`
2. 原始 `source/` 文件
3. 一大段和当前报错无关的宿主对象

## 常见变体

### 1. 需要显式 undefined

如果目标不是判断“值是不是 undefined”，而是区分“属性不存在”和“属性存在但值为 undefined”，用：

```javascript
Object.defineProperty(fakeWindow, 'ActiveXObject', {
    value: undefined,
    configurable: true,
    enumerable: true,
    writable: true,
});
```

### 2. 需要定向日志而不是全局代理

如果你已经知道问题集中在少数对象：

```javascript
const tracedNavigator = env.monitor(fakeNavigator, 'navigator', {
    getLog: true,
    setLog: true,
});

fakeWindow.navigator = tracedNavigator;
global.navigator = tracedNavigator;
```

### 3. 需要同步到 global

有些检测读的是 `globalThis.xxx`，不是 `window.xxx`：

```javascript
Object.defineProperty(global, 'chrome', {
    value: fakeWindow.chrome,
    configurable: true,
    writable: true,
});
```

### 4. 需要最小 XHR 宿主

如果目标只是检测是否存在，不一定要真的发请求：

```javascript
function XMLHttpRequest() {}

XMLHttpRequest.prototype.open = function () {};
XMLHttpRequest.prototype.setRequestHeader = function () {};
XMLHttpRequest.prototype.send = function () {};

env.setFuncNative(XMLHttpRequest);
env.setFuncNative(XMLHttpRequest.prototype.open);
env.setFuncNative(XMLHttpRequest.prototype.setRequestHeader);
env.setFuncNative(XMLHttpRequest.prototype.send);

fakeWindow.XMLHttpRequest = XMLHttpRequest;
global.XMLHttpRequest = XMLHttpRequest;
```

### 5. 需要 Python-Node 三层模板

如果最终业务调度层在 Python，而动态 JS 仍然适合在 Node 里跑，不要硬塞回 `execjs.call()`。优先拆成三层：

1. Python 调度层：抓首页 challenge、提取脚本、调用 Node、回灌 cookie
2. Node 运行模板层：加载 `browser_env.js`，执行动态脚本，输出结构化结果
3. 补环境层：只负责 `window/document/navigator/location` 等宿主对象

适合场景：

1. 首页虽然返回 `412`，但响应体里仍然带 challenge 脚本
2. 业务请求最终仍然由 Python `requests` 发送
3. JS 运行时会打印日志或诊断报告，`execjs` 的 JSON 包装容易被污染

最小结构示例：

```python
CONFIG = {
    'page_url': 'https://example.com/',
    'page_origin': 'https://example.com',
    'runtime_template': 'runtime_template.js',
    'runtime_output': '_runtime_cookie.js',
    'node_result_prefix': '__NODE_RESULT__',
    'inline_script_keyword': '$_ts',
}

def build_runtime_script(template, inline_script, external_script):
    return (template
            .replace("'__INLINE_CHALLENGE_CODE__'", inline_script)
            .replace("'__EXTERNAL_CHALLENGE_CODE__'", external_script)
            .replace('__NODE_RESULT__', CONFIG['node_result_prefix']))
```

```javascript
require('./browser_env');

'__INLINE_CHALLENGE_CODE__';
'__EXTERNAL_CHALLENGE_CODE__';

console.log('__NODE_RESULT__' + JSON.stringify({
    cookie: document.cookie,
}));
```

要点：

1. 首页 `412` 不要直接 `raise_for_status()`，先看响应体里还有没有 challenge 脚本
2. 内联脚本优先按 `$_ts`、`$_ts.cd`、`if(!$_ts)` 这类特征选取，不要默认第一个 `script`
3. Node 输出统一走“前缀 + JSON”，不要靠猜 stdout 哪一行像 cookie
4. 如果需要复盘，把首页 HTML、内联脚本、外链脚本、运行时 JS、Node stdout/stderr 全部落盘
5. 这个模式的详细经验看 `cases/ruishu-python-node-cookie-template.md`

## 最后检查

在首次运行前，最少检查这 6 项：

1. `env.init()` 在 `require('./main.js')` 之前
2. `window/self/top/parent/globalThis` 已互相指向
3. 关键宿主同时考虑了 `window` 和 `global`
4. 有 `uncaughtException` / `unhandledRejection` 输出
5. 没有一上来就全量日志代理整个 `window`
6. 首轮目标只是“跑到能看报告”，不是一步到位补齐所有环境
