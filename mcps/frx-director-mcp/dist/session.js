import { mkdirSync, readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
/**
 * Owns per-tid session state: the workspace binding, the assist/auto mode, and
 * the authoritative convo array (the user turns the director authored + the
 * assistant conclusions carried forward). Persisted to <dataDir>/<tid>/convo.json,
 * mirroring frx_drive.py's convo-*.json so a crashed director can resume.
 */
export class SessionManager {
    dataDir;
    sessions = new Map();
    constructor(dataDir) {
        this.dataDir = dataDir;
        mkdirSync(this.dataDir, { recursive: true });
        this.loadAll();
    }
    dir(tid) {
        return join(this.dataDir, tid.replace(/[^A-Za-z0-9._-]/g, "_"));
    }
    loadAll() {
        for (const name of readdirSync(this.dataDir)) {
            const f = join(this.dataDir, name, "session.json");
            if (!existsSync(f))
                continue;
            try {
                const s = JSON.parse(readFileSync(f, "utf8"));
                this.sessions.set(s.tid, s);
            }
            catch {
                /* skip corrupt */
            }
        }
    }
    persist(s) {
        const d = this.dir(s.tid);
        mkdirSync(d, { recursive: true });
        writeFileSync(join(d, "session.json"), JSON.stringify(s, null, 1), "utf8");
        writeFileSync(join(d, "convo.json"), JSON.stringify(s.convo, null, 1), "utf8");
    }
    create(tid, workspaceRoot, mode, model) {
        const s = { tid, workspaceRoot, mode, model, convo: [], createdAt: Date.now() };
        this.sessions.set(tid, s);
        this.persist(s);
        return s;
    }
    get(tid) {
        return this.sessions.get(tid);
    }
    require(tid) {
        const s = this.sessions.get(tid);
        if (!s)
            throw new Error(`unknown tid "${tid}" — call agent_start first`);
        return s;
    }
    setConvo(tid, convo) {
        const s = this.require(tid);
        s.convo = convo;
        this.persist(s);
    }
    setMode(tid, mode) {
        const s = this.require(tid);
        s.mode = mode;
        this.persist(s);
    }
}
//# sourceMappingURL=session.js.map