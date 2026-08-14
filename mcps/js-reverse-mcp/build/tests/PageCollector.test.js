/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { NetworkCollector, responseBodyCacheSymbol } from '../src/PageCollector.js';
// Mirror of MAX_RETAINED_REQUESTS in PageCollector.ts (the FIFO cap is module
// private). Keep in sync if the source constant changes.
const FIFO_CAP = 5000;
function createFakePage() {
    const listeners = new Map();
    const mainFrame = { id: 'main' };
    const page = {
        on(event, cb) {
            const arr = listeners.get(event) ?? [];
            arr.push(cb);
            listeners.set(event, arr);
            return page;
        },
        off() {
            return page;
        },
        mainFrame: () => mainFrame,
        emit(event, arg) {
            for (const cb of listeners.get(event) ?? []) {
                cb(arg);
            }
        },
    };
    return { page: page, mainFrame };
}
function createFakeRequest(url, frame) {
    return {
        url: () => url,
        method: () => 'POST',
        isNavigationRequest: () => false,
        frame: () => frame,
    };
}
// A request whose response body the collector will eagerly cache on
// 'requestfinished', counting `bodyLen` bytes against the page's body budget.
// frame().page() returns the page so the budget WeakMap keys correctly.
function createFakeRequestWithResponse(url, page, bodyLen) {
    const buffer = Buffer.alloc(bodyLen, 0x61);
    const frame = { page: () => page };
    return {
        url: () => url,
        method: () => 'POST',
        isNavigationRequest: () => false,
        frame: () => frame,
        response: async () => ({
            headers: () => ({ 'content-length': String(bodyLen) }),
            body: async () => buffer,
        }),
    };
}
function createCollector() {
    return new NetworkCollector({}, {});
}
function createFakeCdpSession() {
    const handlers = new Map();
    const session = {
        on(event, cb) {
            const arr = handlers.get(event) ?? [];
            arr.push(cb);
            handlers.set(event, arr);
            return session;
        },
        off() {
            return session;
        },
        send: async () => undefined,
        emit(event, payload) {
            for (const cb of handlers.get(event) ?? []) {
                cb(payload);
            }
        },
    };
    return session;
}
const flushMicrotasks = () => new Promise(resolve => setTimeout(resolve, 0));
test('requests survive navigation (FIFO is navigation-agnostic)', () => {
    const collector = createCollector();
    const { page, mainFrame } = createFakePage();
    collector.addPage(page);
    const emit = (event, arg) => page.emit(event, arg);
    // A request that already fired (e.g. the POST that triggers a redirect).
    const subframe = { id: 'sub' };
    const bundle = createFakeRequest('https://x/assets/js/bundle', subframe);
    emit('request', bundle);
    // Navigation no longer splits or trims the queue, so the request stays
    // inspectable however many times the main frame navigates afterwards.
    for (let i = 0; i < 5; i++) {
        emit('framenavigated', mainFrame);
    }
    assert.ok(collector.getData(page).includes(bundle), 'request should stay inspectable after navigations');
});
test('evicts the oldest request once past the FIFO cap', () => {
    const collector = createCollector();
    const { page } = createFakePage();
    collector.addPage(page);
    const emit = (event, arg) => page.emit(event, arg);
    const subframe = { id: 'sub' };
    let firstReq;
    let lastReq;
    // Emit more than the cap; the oldest beyond the cap roll off, newest stay.
    const total = FIFO_CAP + 500;
    for (let i = 0; i < total; i++) {
        const req = createFakeRequest(`https://x/r${i}`, subframe);
        if (i === 0) {
            firstReq = req;
        }
        if (i === total - 1) {
            lastReq = req;
        }
        emit('request', req);
    }
    const all = collector.getData(page);
    assert.equal(all.length, FIFO_CAP, 'queue should be capped at the FIFO cap');
    assert.ok(!all.includes(firstReq), 'the oldest request should be evicted');
    assert.ok(all.includes(lastReq), 'the newest request should be retained');
});
test('clear() empties the queue and reports + releases the body budget', async () => {
    const collector = createCollector();
    const { page } = createFakePage();
    collector.addPage(page);
    const emit = (event, arg) => page.emit(event, arg);
    const req = createFakeRequestWithResponse('https://x/api', page, 1234);
    emit('request', req);
    emit('requestfinished', req);
    // Wait for the eager body capture (fire-and-forget) to count its bytes.
    await req[responseBodyCacheSymbol];
    const result = collector.clear(page);
    assert.equal(result.requestCount, 1, 'should report the cleared request count');
    assert.equal(result.reclaimedBytes, 1234, 'should report the released body budget');
    assert.equal(collector.getData(page).length, 0, 'queue should be empty after clear');
});
test('FIFO eviction reclaims the evicted request body budget (no ratchet)', async () => {
    const collector = createCollector();
    const { page } = createFakePage();
    collector.addPage(page);
    const emit = (event, arg) => page.emit(event, arg);
    const subframe = { id: 'sub' };
    // A request with a cached 1000-byte body, counted against the budget.
    const withBody = createFakeRequestWithResponse('https://x/r0', page, 1000);
    emit('request', withBody);
    emit('requestfinished', withBody);
    await withBody[responseBodyCacheSymbol];
    // Push exactly FIFO_CAP more requests so the body request rolls off the tail.
    for (let i = 0; i < FIFO_CAP; i++) {
        emit('request', createFakeRequest(`https://x/d${i}`, subframe));
    }
    assert.ok(!collector.getData(page).includes(withBody), 'the body request should have been evicted');
    // A new request adds 50 bytes. If eviction reclaimed the 1000 bytes, the
    // budget now holds only these 50; if it ratcheted, it would hold 1050.
    const newBody = createFakeRequestWithResponse('https://x/rn', page, 50);
    emit('request', newBody);
    emit('requestfinished', newBody);
    await newBody[responseBodyCacheSymbol];
    assert.equal(collector.clear(page).reclaimedBytes, 50, 'evicted request bytes must be reclaimed, not ratcheted');
});
test('getInitiator recovers via URL+method when the requestId mapping lost the race', async () => {
    const { page } = createFakePage();
    const cdp = createFakeCdpSession();
    const collector = new NetworkCollector({ pages: () => [page] }, { getSession: async () => cdp });
    collector.addPage(page);
    await collector.initCdp();
    await flushMicrotasks(); // let the fire-and-forget CDP setup finish
    // The CDP requestWillBeSent event arrives before the Playwright request is in
    // storage, so the requestId mapping never tags the request object.
    cdp.emit('Network.requestWillBeSent', {
        requestId: 'req-1',
        request: { url: 'https://x/api', method: 'POST' },
        initiator: {
            type: 'script',
            stack: {
                callFrames: [
                    {
                        functionName: 'doFetch',
                        scriptId: '1',
                        url: 'https://x/page1.html',
                        lineNumber: 1,
                        columnNumber: 1,
                    },
                ],
            },
        },
    });
    // createFakeRequest uses method POST; cdpRequestIdSymbol was never set, so the
    // requestId path yields nothing and the URL+method fallback must recover it.
    const request = createFakeRequest('https://x/api', { id: 'sub' });
    const initiator = collector.getInitiator(page, request);
    assert.ok(initiator, 'initiator should be recovered via the URL+method fallback');
    assert.equal(initiator?.type, 'script');
    assert.equal(initiator?.stack?.callFrames[0].functionName, 'doFetch');
});
