const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
/**
 * Wait for the worker's stage gate. CRITIQUE FIXES:
 *  #1 timeout default is high (turns run 20-30+ min) and a budget timeout while
 *     still running returns phase:"running" (re-inspect / extend), NEVER "failed".
 *  #2 settle is `settled===true` ALONE — the untested nSteps>0 fallback is dropped.
 *  + surface engine error and checkpointSeq bumps; gentle interval backoff.
 */
export async function waitForStop(bridge, tid, opts) {
    const t0 = Date.now();
    let last = null;
    let interval = Math.max(0.2, opts.intervalSec) * 1000;
    const maxInterval = 30_000;
    while ((Date.now() - t0) / 1000 < opts.timeoutSec) {
        const st = await bridge.getState(tid);
        const elapsedSec = Math.round((Date.now() - t0) / 1000);
        opts.log?.turn(tid, elapsedSec, st);
        if (st === null) {
            // thread never touched / reset between runs — keep polling briefly, then report
            if (elapsedSec > 20) {
                return finalize("no-state", elapsedSec, null);
            }
        }
        else {
            last = st;
            if (st.error)
                return finalize("error", elapsedSec, st);
            if (st.settled)
                return finalize("settled", elapsedSec, st); // FIX #2: settled ONLY
        }
        await sleep(interval);
        interval = Math.min(maxInterval, Math.round(interval * 1.3));
    }
    // FIX #1: budget exhausted. If still running, this is NOT a failure — the
    // director should re-inspect (agent_read) and either keep waiting or stop+correct.
    const elapsedSec = Math.round((Date.now() - t0) / 1000);
    return finalize("running", elapsedSec, last);
}
function finalize(phase, elapsedSec, st) {
    return {
        phase,
        elapsedSec,
        running: !!st?.running,
        settled: !!st?.settled,
        nSteps: st?.nSteps ?? 0,
        checkpointSeq: st?.checkpointSeq ?? 0,
        error: st?.error ?? null,
        contentTail: st?.contentTail ?? "",
        stillGrinding: phase === "running",
    };
}
//# sourceMappingURL=settle.js.map