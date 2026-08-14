#!/usr/bin/env node
/**
 * VM browser gap diagnosis tool.
 * 在 VM 沙箱中执行目标 JS，诊断缺失的浏览器环境属性。
 *
 * 用法:
 *   node vm-browser-gap-diagnose.js target.js
 *   node vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js,bom/web-crypto-stub.js target.js
 *   node vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js --env dom/document-dom-runtime.js target.js
 *
 * 输出: JSON 到 stdout
 *   {
 *     "success": true/false,
 *     "error": null | "错误信息",
 *     "undefinedPaths": ["window.crypto.getRandomValues", ...],
 *     "stats": { "get": N, "set": N, "call": N, "construct": N, "total": N },
 *     "consoleOutput": [["log", "msg"], ["error", "msg"], ...]
 *   }
 */

import vm from 'vm';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ─── 参数解析 ─────────────────────────────────────────────
const args = process.argv.slice(2);
let targetFile = null;
let envModules = [];
let timeout = 60000;
let quiet = false;
let profileName = null;
let profileFile = null;

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if ((arg === '--env' || arg === '-e') && i + 1 < args.length) {
    // 支持逗号分隔和多次 --env
    envModules.push(...args[++i].split(',').map(s => s.trim()).filter(Boolean));
  } else if (arg === '--timeout' && i + 1 < args.length) {
    timeout = parseInt(args[++i], 10);
  } else if (arg === '--profile' && i + 1 < args.length) {
    profileName = args[++i];
  } else if (arg === '--profile-file' && i + 1 < args.length) {
    profileFile = args[++i];
  } else if (arg === '--quiet' || arg === '-q') {
    quiet = true;
  } else if (arg === '--help' || arg === '-h') {
    console.log(`用法: node vm-browser-gap-diagnose.js [选项] <目标脚本>

选项:
  --env, -e <模块列表>      加载的 env 模块（逗号分隔或多次指定）
                            路径相对于 skill/env/，如 bom/navigator-fingerprint.js
  --timeout <毫秒>          执行超时（默认 60000）
  --profile <名称>          加载 skill/profiles/<名称>.json
  --profile-file <路径>     加载自定义 profile JSON
  --quiet, -q              不输出日志到 stderr
  --help, -h               显示帮助

示例:
  node vm-browser-gap-diagnose.js target.js
  node vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js,bom/web-crypto-stub.js target.js
  node vm-browser-gap-diagnose.js --profile default --env bom/navigator-fingerprint.js,bom/screen-fingerprint.js target.js
  node vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js --env dom/document-dom-runtime.js target.js`);
    process.exit(0);
  } else if (!targetFile) {
    targetFile = arg;
  }
}

if (!targetFile) {
  console.error('错误: 请提供目标脚本文件');
  process.exit(1);
}

// ─── 定位框架目录 ─────────────────────────────────────────
function findSkillDir() {
  // skill 自包含，env 目录固定在 skill 根目录下
  const skillRoot = path.resolve(__dirname, '..');
  const envDir = path.join(skillRoot, 'env');
  if (!fs.existsSync(path.join(envDir, 'core', 'proxy-access-monitor.js'))) {
    console.error(`错误: env 目录不完整，缺少 core/proxy-access-monitor.js: ${envDir}`);
    process.exit(1);
  }
  return skillRoot;
}

const FRAMEWORK = findSkillDir();
const ENV_DIR = path.join(FRAMEWORK, 'env');
const PROFILE_DIR = path.join(FRAMEWORK, 'profiles');

function log(msg) {
  if (!quiet) process.stderr.write(msg + '\n');
}

function resolveEnvModule(mod) {
  if (path.isAbsolute(mod)) return mod;

  const cwdPath = path.resolve(process.cwd(), mod);
  if (fs.existsSync(cwdPath)) return cwdPath;

  if (mod.startsWith('env/')) return path.join(FRAMEWORK, mod);
  if (mod.startsWith('js_reverse_cache/') || mod.startsWith('js_reverse_cache\\')) return cwdPath;

  const firstSegment = mod.split(/[\\/]/)[0];
  const builtinRoots = new Set(['ai-generated', 'bom', 'core', 'dom', 'encoding', 'timer', 'webapi']);
  if (!builtinRoots.has(firstSegment)) return cwdPath;

  return path.join(ENV_DIR, mod);
}

function isThenable(value) {
  return value && (typeof value === 'object' || typeof value === 'function') && typeof value.then === 'function';
}

async function waitForThenable(value) {
  let timer = null;
  const timeoutPromise = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Async execution timed out after ${timeout}ms`)), timeout);
  });
  try {
    return await Promise.race([value, timeoutPromise]);
  } finally {
    clearTimeout(timer);
  }
}

// ─── 创建沙箱 ─────────────────────────────────────────────
const consoleOutput = [];

const sandbox = {
  console: {
    log:   (...a) => { consoleOutput.push(['log',   ...a]); },
    error: (...a) => { consoleOutput.push(['error', ...a]); },
    warn:  (...a) => { consoleOutput.push(['warn',  ...a]); },
    info:  (...a) => { consoleOutput.push(['info',  ...a]); },
    debug: (...a) => { consoleOutput.push(['debug', ...a]); },
    trace: (...a) => { consoleOutput.push(['trace', ...a]); },
    dir:   (...a) => { consoleOutput.push(['dir',   ...a]); },
    table: (...a) => { consoleOutput.push(['table', ...a]); },
    group:          (...a) => {},
    groupCollapsed: (...a) => {},
    groupEnd:       ()     => {},
    time:           ()     => {},
    timeEnd:        ()     => {},
    timeLog:        ()     => {},
    count:          ()     => {},
    countReset:     ()     => {},
    assert:         ()     => {},
    clear:          ()     => {},
  },
  setTimeout:    (fn, delay) => 0,
  setInterval:   (fn, delay) => 0,
  clearTimeout:  () => {},
  clearInterval: () => {},
  atob: (str) => Buffer.from(str, 'base64').toString('binary'),
  btoa: (str) => Buffer.from(str, 'binary').toString('base64'),
  XMLHttpRequest: class XMLHttpRequest {
    constructor() { this.bdmsInvokeList = []; }
    open() {}
    send() {}
    setRequestHeader() {}
    getResponseHeader() { return null; }
    getAllResponseHeaders() { return ''; }
    addEventListener() {}
    removeEventListener() {}
  },
  __output__: consoleOutput,
};

sandbox.window = sandbox;
sandbox.global = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;

const context = vm.createContext(sandbox);

// ─── 加载 Profile ──────────────────────────────────────────
if (profileName || profileFile) {
  const profilePath = profileFile
    ? path.resolve(profileFile)
    : path.join(PROFILE_DIR, `${profileName}.json`);

  if (!fs.existsSync(profilePath)) {
    console.error(`错误: profile 不存在: ${profilePath}`);
    process.exit(1);
  }

  try {
    sandbox.__profile__ = JSON.parse(fs.readFileSync(profilePath, 'utf-8'));
    log(`[diagnose] 加载 profile: ${sandbox.__profile__.meta?.name || profileName || profilePath}`);
  } catch (e) {
    console.error(`错误: profile 解析失败: ${e.message}`);
    process.exit(1);
  }
}

// ─── 加载 ProxyMonitor ────────────────────────────────────
const proxyMonitorPath = path.join(ENV_DIR, 'core', 'proxy-access-monitor.js');
if (!fs.existsSync(proxyMonitorPath)) {
  console.error(`错误: proxy-access-monitor.js 不存在: ${proxyMonitorPath}`);
  process.exit(1);
}

log('[diagnose] 加载 ProxyMonitor...');
vm.runInContext(fs.readFileSync(proxyMonitorPath, 'utf-8'), context, { timeout });

const profileManagerPath = path.join(ENV_DIR, 'core', 'profile-seed-manager.js');
if ((profileName || profileFile) && fs.existsSync(profileManagerPath)) {
  log('[diagnose] 加载 ProfileManager...');
  vm.runInContext(fs.readFileSync(profileManagerPath, 'utf-8'), context, { timeout });
}

// 仅在没有指定 env 模块时加载 ProxyEnv（提供 watch() 包裹的基本对象）
// 当指定了 env 模块时，ProxyEnv 的 configurable:false 属性会阻止完整模块覆盖
const proxyEnvPath = path.join(ENV_DIR, 'core', 'minimal-proxy-browser-env.js');
if (envModules.length === 0 && fs.existsSync(proxyEnvPath)) {
  log('[diagnose] 加载 ProxyEnv（无 env 模块指定，使用基础代理环境）...');
  vm.runInContext(fs.readFileSync(proxyEnvPath, 'utf-8'), context, { timeout });
}

// ─── 加载用户指定的 env 模块 ──────────────────────────────
const moduleLoadErrors = [];

for (const mod of envModules) {
  // 支持 skill 内模块、项目相对路径或绝对路径
  const modPath = resolveEnvModule(mod);

  if (!fs.existsSync(modPath)) {
    const error = { module: mod, path: modPath, error: 'module not found' };
    moduleLoadErrors.push(error);
    log(`[diagnose] 警告: 模块不存在，跳过: ${modPath}`);
    continue;
  }

  log(`[diagnose] 加载 env 模块: ${mod}`);
  try {
    vm.runInContext(fs.readFileSync(modPath, 'utf-8'), context, { timeout });
  } catch (e) {
    moduleLoadErrors.push({ module: mod, path: modPath, error: e.message || String(e) });
    log(`[diagnose] 加载模块失败 ${mod}: ${e.message}`);
  }
}

// ─── 清空 ProxyMonitor 日志（env 加载期间的日志不算） ──────
try {
  vm.runInContext('__ProxyMonitor__.clearLogs()', context);
} catch (_) {}

// 也清空 console 输出（env 模块的加载日志不算）
consoleOutput.length = 0;

// 抑制 ProxyMonitor 的 console 输出，但保留 LogStore 记录
// 通过替换 sandbox console 为一个过滤版本
const proxyLogPattern = /^方法: (get|set|has|ownKeys|getOwnPropertyDescriptor|defineProperty|deleteProperty|getPrototypeOf|setPrototypeOf|apply|construct)\s+\|/;
const originalLog = sandbox.console.log;
sandbox.console.log = (...a) => {
  // 过滤掉 ProxyMonitor 的结构化日志
  if (typeof a[0] === 'string' && proxyLogPattern.test(a[0])) return;
  if (typeof a[0] === 'string' && a[0].startsWith('[ProxyMonitor]')) return;
  originalLog(...a);
};

// ─── 执行目标脚本 ─────────────────────────────────────────
const targetPath = path.resolve(targetFile);
if (!fs.existsSync(targetPath)) {
  console.error(`错误: 目标脚本不存在: ${targetPath}`);
  process.exit(1);
}

log(`[diagnose] 执行目标脚本: ${targetFile}`);
const code = fs.readFileSync(targetPath, 'utf-8');

let success = true;
let errorMsg = null;

try {
  const result = vm.runInContext(code, context, {
    timeout,
    filename: path.basename(targetFile),
    displayErrors: true,
  });
  if (isThenable(result)) {
    await waitForThenable(result);
  }
} catch (e) {
  success = false;
  // V8 错误格式: "filename:line\n<整行源码>\n<指针>\n\nErrorType: message"
  // 压缩 JS 的源码行可能有几十 KB，必须截断
  const msg = e.message || String(e);
  const MAX_ERROR_LEN = 500;
  if (msg.length > MAX_ERROR_LEN) {
    errorMsg = msg.substring(0, MAX_ERROR_LEN) + '... [truncated]';
  } else {
    errorMsg = msg;
  }
  // 提取 stack 中有用的帧信息（跳过源码行）
  if (e.stack) {
    const frames = e.stack.split('\n').filter(line =>
      line.trim().startsWith('at ') || line.match(/^\w*Error:/)
    ).slice(0, 5);
    if (frames.length > 0) {
      errorMsg = frames.join('\n');
    }
  }
}

// ─── 收集诊断结果 ─────────────────────────────────────────
let stats = { get: 0, set: 0, call: 0, construct: 0, total: 0 };
let undefinedPaths = [];

try {
  stats = vm.runInContext('__ProxyMonitor__.getStats()', context);
} catch (_) {}

// 从 getLogs('get') 中提取 valueType === 'undefined' 的条目
try {
  const getLogs = vm.runInContext('__ProxyMonitor__.getLogs("get")', context);
  if (Array.isArray(getLogs)) {
    const seen = new Set();
    for (const entry of getLogs) {
      if (entry.valueType === 'undefined' && entry.propertyType === 'string') {
        const fullPath = `${entry.object}.${entry.property}`;
        if (!seen.has(fullPath)) {
          seen.add(fullPath);
          undefinedPaths.push(fullPath);
        }
      }
    }
  }
} catch (_) {}

// 对 consoleOutput 做序列化安全处理
const safeConsoleOutput = consoleOutput.map(entry => {
  return entry.map(item => {
    if (typeof item === 'object' && item !== null) {
      try { return JSON.parse(JSON.stringify(item)); }
      catch { return String(item); }
    }
    return item;
  });
});

// ─── 输出 JSON ────────────────────────────────────────────
const result = {
  success,
  error: errorMsg,
  undefinedPaths,
  moduleLoadErrors,
  stats,
  consoleOutput: safeConsoleOutput,
};

console.log(JSON.stringify(result, null, 2));
process.exit(success ? 0 : 1);
