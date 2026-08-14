import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { MarionetteWire, MarionetteError } from "./marionetteWire.js";
import { MarionetteLock } from "./marionetteLock.js";
import { JS_CONFIG, JS_NAV, JS_RUN, JS_STATE, JS_CONTENT, JS_RUNLOG, JS_STOP, JS_NEWTHREAD, JS_APPEND, JS_SETWORKSPACE, JS_TOOLS, JS_CALLTOOL, } from "./chromeScripts.js";
/** How long connect() waits for the cross-process Marionette lock before giving
 *  up and surfacing a clear "another session owns the browser" error. Kept short
 *  so a degraded session never hangs; the owner may hold it for its whole
 *  lifetime and hands off cleanly on exit. */
const LOCK_WAIT_MS = 4000;
const DEFAULT_STATE_HOME = resolve(dirname(fileURLToPath(import.meta.url)), "../..", ".frx-director-mcp");
/** A dropped/never-established connection (reconnect+retry) vs. a real Marionette
 *  protocol error (surface as-is — retrying it would just fail again). */
function isConnLost(e) {
    if (e instanceof MarionetteError)
        return false;
    const m = e?.message || "";
    return /marionette (not connected|closed|socket timeout)|bad marionette frame|ECONNRESET|ECONNREFUSED|EPIPE/i.test(m);
}
/**
 * The v1 bridge: drives the parent-process agentSession singleton over Marionette
 * (port 2828) via chrome-context ExecuteScript. TS port of frx_drive.py.
 *
 * Requires the browser launched with `-marionette -remote-allow-system-access`
 * (chrome SetContext requires system access). Keep the port loopback-only.
 *
 * Robustness (2026-06-11): connection is LAZY (only opened on first real use, so
 * idle sessions never contend), arbitrated by a cross-process {@link MarionetteLock}
 * (one owner at a time — no more slot-stealing between sessions), and self-healing
 * (a dropped socket is reconnected + retried ONCE per call, keeping ownership).
 */
export class MarionetteBridge {
    host;
    port;
    timeoutMs;
    stateHome;
    wire = null;
    lock;
    connecting = null;
    constructor(host, port, timeoutMs = 180_000, stateHome = DEFAULT_STATE_HOME) {
        this.host = host;
        this.port = port;
        this.timeoutMs = timeoutMs;
        this.stateHome = stateHome;
        const lockPath = join(this.stateHome, `marionette-${host}-${port}.lock`);
        this.lock = new MarionetteLock(lockPath, { pid: process.pid, ppid: process.ppid, host, port });
    }
    isLive() {
        return !!this.wire && this.wire.isConnected();
    }
    /** Ensure a live connection (acquiring the lock if we don't own it). Single-flight
     *  so concurrent callers share one in-progress connect. */
    async connect() {
        if (this.isLive())
            return;
        if (this.connecting)
            return this.connecting;
        this.connecting = this.doConnect().finally(() => {
            this.connecting = null;
        });
        return this.connecting;
    }
    async doConnect() {
        if (!this.lock.isHeld()) {
            const got = await this.lock.acquire(LOCK_WAIT_MS);
            if (!got) {
                const h = this.lock.currentHolder();
                throw new Error(`另一个 frx-director 会话正持有浏览器 Marionette 连接（PID ${h?.pid ?? "?"}）。` +
                    "Marionette 是单客户端:请关掉那个会话、或等它结束后重试(它退出时会自动让出锁)。");
            }
        }
        const w = new MarionetteWire();
        try {
            await w.connect(this.host, this.port, this.timeoutMs);
        }
        catch (e) {
            // Couldn't actually connect — never squat on the lock (else an owner that
            // can't reach Firefox would block every other session indefinitely).
            this.lock.release();
            throw e;
        }
        this.wire = w;
    }
    async close() {
        const w = this.wire;
        this.wire = null;
        if (w) {
            try {
                await w.close();
            }
            catch {
                /* ignore */
            }
        }
        this.lock.release();
    }
    /**
     * Every browser op funnels through here. Two explicit phases:
     *  1. connect lazily (via the lock) then run; a CONNECT failure (degraded lock,
     *     Firefox down) propagates as-is — retrying connect would just fail again.
     *  2. only if the op itself drops the socket mid-flight (isConnLost, not a real
     *     MarionetteError) do we discard the dead wire, reconnect ONCE, and retry the
     *     op ONCE. A second failure propagates. Each success renews the lock lease.
     */
    async exec(fn) {
        await this.connect();
        const w1 = this.wire;
        if (!w1)
            throw new Error("marionette not connected");
        try {
            const r = await fn(w1);
            this.lock.renew();
            return r;
        }
        catch (e) {
            if (!isConnLost(e))
                throw e; // real protocol/app error — surface it
            this.wire = null; // dead wire already tore down its own socket in fail()
            await this.connect();
            const w2 = this.wire;
            if (!w2)
                throw new Error("marionette not connected");
            const r = await fn(w2);
            this.lock.renew();
            return r;
        }
    }
    async config(opts) {
        return (await this.exec((w) => w.execute(JS_CONFIG, [opts.provider || null, opts.model || null, opts.ensureConfirmOff !== false])));
    }
    async navigate(url) {
        return (await this.exec((w) => w.execute(JS_NAV, [url])));
    }
    async newThread(title, workspace, mode) {
        return (await this.exec((w) => w.executeAsync(JS_NEWTHREAD, [title, workspace, mode])));
    }
    async appendMessage(tid, role, content) {
        return (await this.exec((w) => w.executeAsync(JS_APPEND, [tid, role, content])));
    }
    async setThreadWorkspace(tid, workspace) {
        return (await this.exec((w) => w.executeAsync(JS_SETWORKSPACE, [tid, workspace])));
    }
    async run(tid, p) {
        return (await this.exec((w) => w.execute(JS_RUN, [tid, p.systemPrompt, p.convo, p.workspaceRoot || null, !!p.assist, p.maxRounds || 80])));
    }
    async getState(tid) {
        return (await this.exec((w) => w.execute(JS_STATE, [tid])));
    }
    async getContent(tid) {
        return (await this.exec((w) => w.execute(JS_CONTENT, [tid])));
    }
    async stop(tid) {
        return (await this.exec((w) => w.execute(JS_STOP, [tid])));
    }
    async runlog() {
        const r = await this.exec((w) => w.execute(JS_RUNLOG, []));
        return Array.isArray(r) ? r : [];
    }
    async listTools() {
        const r = (await this.exec((w) => w.execute(JS_TOOLS, [])));
        const tools = Array.isArray(r?.tools) ? r.tools : [];
        const declaredNames = Array.isArray(r?.declaredNames) ? r.declaredNames : [];
        return { tools, declaredNames, count: typeof r?.count === "number" ? r.count : tools.length };
    }
    async callTool(name, args, opts = {}) {
        // Async chrome JS (callTool returns a Promise). A trace on a hot path / run_node
        // can run long → generous scriptTimeout; the exec() funnel keeps the lock and
        // reconnects once on a mid-op socket drop.
        return (await this.exec((w) => w.executeAsync(JS_CALLTOOL, [name, args || {}, opts.workspaceRoot ?? null], 300_000)));
    }
}
//# sourceMappingURL=MarionetteBridge.js.map