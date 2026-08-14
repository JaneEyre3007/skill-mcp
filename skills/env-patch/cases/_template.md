# Case Name

## Summary

一句话说明这是哪类目标、最后走的是什么路径。

## Keywords

列出能快速命中的关键词：

1. 域名或站点类型
2. 参数名
3. SDK 字符串
4. 报错特征
5. 文件特征

## Anti-Bot Type

填写其一：

1. 签名型
2. 行为型
3. 纯混淆

## Recommended Path

填写其一或组合：

1. 纯算法还原
2. 最小环境复现
3. vm 沙箱
4. jsdom 环境伪装
5. WASM 加载

## Entry Clues

记录最有效的入口线索：

1. 入口函数名
2. 关键模块名
3. 关键请求路径
4. 关键宿主对象
5. 首跳文档或动态脚本如何固定

## Required Environment Items

只记录被诊断报告、调用日志或浏览器对照证明“缺了就跑不通/结果不对”的项。
建议写成“对象/属性/方法 + 证据或用途”，不要只写大类名。

1. 例如：`document.createElement` - 首轮直接报 `is not a function`
2. 例如：`document.cookie` - 目标会写 challenge cookie
3. 例如：`navigator.userAgent` - 签名链会读取

## Explicit Undefined Items

记录必须“存在但值为 undefined”的项。
适合写那些“省略会报错/分支变化，显式设 `undefined` 才接近浏览器”的字段。

1. 例如：`window.ActiveXObject`
2. 例如：目标脚本探测的占位属性

## Unnecessary Items

记录明确试过但当前目标不需要补的项。
优先写那些很容易让人误补的大项，避免下次重复走弯路。

1. 例如：完整 `jsdom` / 全量 DOM
2. 例如：`screen` / `plugins` / `mimeTypes` 全家桶

## Key Pitfalls

记录最容易重踩的坑。
尽量写成“错误做法 -> 后果”的形式，方便下次快速规避。

1. 例如：代理开太大 -> 运行极慢或卡死
2. 例如：补丁顺序晚于 `require()` -> 实际未生效
3. 例如：只看 HTTP 200，不看签名格式 -> 误判已跑通
4. 例如：把页面代码格式化后再调试 -> 命中格式化检测或破坏原始执行链

## Minimal Verifiable Facts

尽量写成可以快速复验的事实。
优先写“某字段会被访问/某方法会被调用/某结果应出现”的短句，不写模糊经验判断。

1. 例如：`location.href` 会参与签名链
2. 例如：`document.createElement('div')` 会被调用
3. 例如：浏览器里该属性本身就是 `undefined`
4. 例如：关闭大范围代理后运行时间明显下降
5. 例如：补上 `XMLHttpRequest` 后开始出现真实请求链

## Validation

记录最后怎么确认跑通：

1. 签名格式
2. 请求结果
3. 稳定性

## Notes

其他补充说明。

如果目标存在“首跳文档动态变化”或“复制出来的代码不能格式化”这类特征，也建议在这里明确写出来。
