# 定向代理日志

当你已经习惯“先看日志，再决定补什么”，可以在 `env-patch` 的默认诊断流程之外，开启这一调试分支。

这个分支的定位不是替代 `createProxy() + report()`，而是：

1. 结构化报告已经把范围缩小了
2. 你还需要确认访问顺序、参数、返回值流向
3. 你只想盯住少数关键对象，而不是让全局日志刷屏

## 何时使用

适合：

1. 你已经知道问题集中在 `navigator`、`document`、`location`、`XMLHttpRequest`、`localStorage`
2. 报告里没有明显 `UNDEFINED/ERRORS`，但签名仍然不对
3. 你想确认 `createElement('canvas')`、`setRequestHeader()`、`getItem()` 这类关键调用链

不适合：

1. 首轮启动就全量监控 `window`
2. 用字符串 + `eval` 动态给变量名包 Proxy
3. 希望只靠日志替代格式校验

## 原则

1. 首轮先跑 `env.createProxy()` 看报告
2. 第二轮才开定向日志
3. 一次只监控少数对象
4. 优先监控“对象级”或“方法级”，不要默认递归所有子对象
5. 瑞数 challenge 类目标如果出现卡死、极慢、空转，优先减少 Proxy 覆盖面，必要时完全关闭日志代理，只保留最小补环境

## 方式一：直接用 `monitor()`

`env_core.js` 已经内置了适合精查的 `monitor()`：

```javascript
const env = require('./env_core');

const fakeNavigator = { webdriver: false, userAgent: 'Mozilla/5.0 ...' };

const tracedNavigator = env.monitor(fakeNavigator, 'navigator', {
    getLog: true,
    setLog: true,
});

Object.defineProperty(global, 'navigator', {
    value: tracedNavigator,
    configurable: true,
});
```

如果只关心几个属性：

```javascript
const tracedNavigator = env.monitor(fakeNavigator, 'navigator', {
    getCb(prop, name) {
        if (prop === 'webdriver' || prop === 'plugins') {
            console.log(`[trace] ${name}.${prop} GET`);
        }
    },
});
```

## 方式二：用显式 helper 批量挂日志

如果你喜欢“给几个对象统一开日志”的工作流，可以在 `run.js` 顶部放一个小 helper。注意：只写 helper，不要重写 `env_core.js` 里已有能力。

```javascript
const env = require('./env_core');

function traceTargets(targetMap, options) {
    const traced = {};
    options = options || {};
    const { get = true, set = true, only = null } = options;

    for (const [name, target] of Object.entries(targetMap)) {
        traced[name] = new Proxy(target, {
            get(obj, prop, receiver) {
                if (typeof prop !== 'symbol' && get && (!only || only.includes(prop))) {
                    console.log('[trace:get]', `${name}.${String(prop)}`, '=>', obj[prop]);
                }
                return Reflect.get(obj, prop, receiver);
            },
            set(obj, prop, value, receiver) {
                if (typeof prop !== 'symbol' && set && (!only || only.includes(prop))) {
                    console.log('[trace:set]', `${name}.${String(prop)}`, '=>', value);
                }
                return Reflect.set(obj, prop, value, receiver);
            },
        });
    }

    return traced;
}

const traced = traceTargets({
    navigator: fakeNavigator,
    location: fakeLocation,
}, {
    only: ['webdriver', 'userAgent', 'href', 'pathname'],
});

fakeWindow.navigator = traced.navigator;
fakeWindow.location = traced.location;
```

这个 helper 保留了“批量开日志”的体验，但避免了字符串 + `eval`。

## 方式三：方法级监控

很多场景真正有价值的不是整个对象，而是少数方法：

1. `document.createElement`
2. `document.createEvent`
3. `XMLHttpRequest.prototype.open`
4. `XMLHttpRequest.prototype.setRequestHeader`
5. `XMLHttpRequest.prototype.send`
6. `localStorage.getItem`

优先用 `wrapFunc()` 包这些方法：

```javascript
env.wrapFunc(fakeDocument, 'createElement', function (orig, tag) {
    console.log('[trace] document.createElement(', tag, ')');
    return orig(tag);
});

env.wrapFunc(XMLHttpRequest.prototype, 'send', function (orig, body) {
    console.log('[trace] xhr.send body =', body);
    return orig(body);
});
```

## 推荐组合

推荐这样组合：

1. `createProxy()` 负责首轮摸底
2. `monitor()` 或 `traceTargets()` 负责第二轮定点追踪
3. `wrapFunc()` 负责方法级调用日志

如果目标是瑞数 challenge 这类容易被日志和代理放大的场景，建议把顺序改成：

1. 最小环境 + 少量 `createProxy()`
2. 若卡死则先关掉大范围 Proxy
3. 只保留 `document.createElement`、`getElementsByTagName`、`cookie`、`setInterval`、外链 JS 装载这类关键点日志
4. 跑通后再逐步恢复更细的观察

对应问题类型：

1. “还缺什么” → `report()`
2. “它先读了谁、后调了谁” → `monitor()` / `traceTargets()`
3. “这个方法到底收到了什么参数” → `wrapFunc()`

## 关于显式 undefined

某些目标不会只判断“值是不是 `undefined`”，而是会同时区分：

1. 属性根本不存在
2. 属性存在，但值是 `undefined`

瑞数 challenge 类案例中第二种情况并不少见，所以不要机械地看到 `undefined` 就不补。需要按运行结果判断是否应显式定义：

```javascript
Object.defineProperty(window, 'ActiveXObject', {
    value: undefined,
    configurable: true,
    enumerable: true,
    writable: true,
});
```

同理，也可以用于 `navigator.plugins`、`document.all`、`chrome` 等可疑字段。

## 实战建议

1. 默认不要追整个 `window`
2. 优先追 `navigator`、`location`、`document.createElement`、`XMLHttpRequest`
3. 发现日志噪音太大时，立刻收缩到单对象或单方法
4. 日志稳定后关闭追踪，回到签名格式验证
