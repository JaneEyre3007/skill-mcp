# DOM Hooks

适合定位元素创建、节点插入、canvas 绘制和 DOM 变化来源。

## 1. Hook `document.createElement`

适合定位 `script`、`iframe`、`canvas` 等元素是谁创建的。

```js
(function () {
  const rawCreateElement = document.createElement.bind(document);
  document.createElement = function (tagName, options) {
    if (tagName === 'script' || tagName === 'canvas') {
      debugger;
      console.log('[createElement]', tagName);
    }
    return rawCreateElement(tagName, options);
  };
})();
```

## 2. Hook `appendChild` / `insertBefore`

适合定位动态插入的 `script`、`iframe`、隐藏节点。

```js
(function () {
  const rawAppendChild = Node.prototype.appendChild;
  const rawInsertBefore = Node.prototype.insertBefore;

  function logNode(prefix, node, parent) {
    if (!node || !node.tagName) {
      return;
    }
    const tag = node.tagName.toLowerCase();
    if (tag === 'script' || tag === 'iframe' || tag === 'canvas') {
      console.log('[' + prefix + ']', tag, node, parent);
      debugger;
    }
  }

  Node.prototype.appendChild = function (node) {
    logNode('appendChild', node, this);
    return rawAppendChild.apply(this, arguments);
  };

  Node.prototype.insertBefore = function (node) {
    logNode('insertBefore', node, this);
    return rawInsertBefore.apply(this, arguments);
  };
})();
```

## 3. Hook `MutationObserver`

适合页面不停改 DOM，想知道新增节点来自哪里。

```js
(function () {
  const observer = new MutationObserver(function (mutations) {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === 1) {
          console.log('[MutationObserver:add]', node.tagName, node);
          if (/^(SCRIPT|IFRAME|CANVAS)$/i.test(node.tagName)) {
            debugger;
          }
        }
      }
    }
  });

  observer.observe(document.documentElement || document, {
    childList: true,
    subtree: true
  });

  window.__hookMutationObserver = observer;
})();
```

停止观察：

```js
window.__hookMutationObserver && window.__hookMutationObserver.disconnect();
```

## 4. Hook `HTMLCanvasElement` / `CanvasRenderingContext2D`

适合定位指纹绘制和验证码、图片生成逻辑。

```js
(function () {
  const rawGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type) {
    console.log('[canvas:getContext]', type, this);
    if (type === '2d' || type === 'webgl') {
      debugger;
    }
    return rawGetContext.apply(this, arguments);
  };
})();
```

如果要盯绘制文本：

```js
(function () {
  const rawFillText = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y) {
    console.log('[canvas:fillText]', text, x, y);
    debugger;
    return rawFillText.apply(this, arguments);
  };
})();
```

如果要看导出结果：

```js
(function () {
  const rawToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function () {
    const result = rawToDataURL.apply(this, arguments);
    console.log('[canvas:toDataURL]', result);
    debugger;
    return result;
  };
})();
```
