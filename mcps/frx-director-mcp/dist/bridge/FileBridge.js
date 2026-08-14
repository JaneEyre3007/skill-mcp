import { mkdir, readFile, writeFile, rename } from "node:fs/promises";
import { join } from "node:path";
/**
 * FALLBACK SEAM — file-IPC transport. Node side is implemented (atomic temp+rename
 * command/state files, monotonic seq for dedup). The BROWSER side counterpart —
 * a parent-process `BridgePoll.sys.mjs` that polls the command file, calls
 * agentSession, and writes the state file — is NOT shipped yet.
 *
 * Use only if a future Firefox build breaks the Marionette executeScript→singleton
 * path. Until BridgePoll.sys.mjs lands, connect() throws with that guidance.
 */
export class FileBridge {
    dir;
    seq = 0;
    constructor(dir) {
        this.dir = dir;
    }
    async connect() {
        throw new Error("FileBridge requires a parent-process BridgePoll.sys.mjs in the browser " +
            "(not shipped yet). Use FRX_BRIDGE=marionette. This stub exists as the " +
            "documented fallback seam; the Node side below is ready to pair with it.");
    }
    async close() { }
    /** Atomic write (temp + rename) so the poller never reads a half-written file. */
    async send(op, args) {
        await mkdir(this.dir, { recursive: true });
        const seq = ++this.seq;
        const cmdPath = join(this.dir, "command.json");
        const tmp = cmdPath + ".tmp";
        await writeFile(tmp, JSON.stringify({ seq, op, args }), "utf8");
        await rename(tmp, cmdPath);
        return this.awaitReply(seq);
    }
    async awaitReply(seq, timeoutMs = 30_000) {
        const statePath = join(this.dir, "state.json");
        const t0 = Date.now();
        for (;;) {
            try {
                const s = JSON.parse(await readFile(statePath, "utf8"));
                if (s && s.seq === seq)
                    return s.result;
            }
            catch {
                /* not written yet */
            }
            if (Date.now() - t0 > timeoutMs)
                throw new Error("FileBridge reply timeout");
            await new Promise((r) => setTimeout(r, 150));
        }
    }
    async config(opts) {
        return (await this.send("config", opts));
    }
    async navigate(url) {
        return (await this.send("navigate", { url }));
    }
    async newThread(title, workspace, mode) {
        return (await this.send("new-thread", { title, workspace, mode }));
    }
    async appendMessage(tid, role, content) {
        return (await this.send("append", { tid, role, content }));
    }
    async setThreadWorkspace(tid, workspace) {
        return (await this.send("set-workspace", { tid, workspace }));
    }
    async run(tid, p) {
        return (await this.send("run", { tid, ...p }));
    }
    async getState(tid) {
        return (await this.send("get-state", { tid }));
    }
    async getContent(tid) {
        return (await this.send("get-content", { tid }));
    }
    async stop(tid) {
        return (await this.send("stop", { tid }));
    }
    async runlog() {
        const r = await this.send("runlog", {});
        return Array.isArray(r) ? r : [];
    }
    async listTools() {
        return (await this.send("list-tools", {}));
    }
    async callTool(name, args, opts = {}) {
        return (await this.send("call-tool", { name, args, workspaceRoot: opts.workspaceRoot ?? null }));
    }
}
//# sourceMappingURL=FileBridge.js.map