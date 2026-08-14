import { mkdirSync, appendFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
/** Redact anything resembling an API key, defensively (the server never holds one). */
export function redact(s) {
    return s
        .replace(/sk-[A-Za-z0-9_\-]{12,}/g, "sk-***REDACTED***")
        .replace(/([:\[,]\s*)"([A-Za-z0-9_\-]{40,})"/g, '$1"***REDACTED_LONG_SECRET***"');
}
/**
 * Per-tid turnlog (NDJSON, mirrors reverse-lab/_harness/turnlog-*.ndjson) plus a
 * guidance archive of every director correction — for replay/debug. Keys redacted.
 */
export class TurnLogger {
    dataDir;
    constructor(dataDir) {
        this.dataDir = dataDir;
        mkdirSync(this.dataDir, { recursive: true });
    }
    dir(tid) {
        const d = join(this.dataDir, tid.replace(/[^A-Za-z0-9._-]/g, "_"));
        mkdirSync(d, { recursive: true });
        return d;
    }
    turn(tid, elapsedSec, st) {
        const rec = { at: Math.floor(Date.now() / 1000), el: elapsedSec, st };
        try {
            appendFileSync(join(this.dir(tid), "turnlog.ndjson"), redact(JSON.stringify(rec)) + "\n", "utf8");
        }
        catch {
            /* logging must never break the loop */
        }
    }
    guidance(tid, seq, text) {
        try {
            writeFileSync(join(this.dir(tid), `guidance-${seq}.txt`), redact(text), "utf8");
        }
        catch {
            /* ignore */
        }
    }
    event(tid, kind, data) {
        const rec = { at: Math.floor(Date.now() / 1000), kind, data };
        try {
            appendFileSync(join(this.dir(tid), "events.ndjson"), redact(JSON.stringify(rec)) + "\n", "utf8");
        }
        catch {
            /* ignore */
        }
    }
}
//# sourceMappingURL=logging.js.map