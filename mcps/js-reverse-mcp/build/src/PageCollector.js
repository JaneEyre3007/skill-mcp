/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
import { createIssuesFromProtocolIssue, IssueAggregator, } from '../node_modules/chrome-devtools-frontend/mcp/mcp.js';
import { addCdpEventListener, removeCdpEventListener } from './CdpEvents.js';
import { FakeIssuesManager } from './DevtoolsUtils.js';
import { features } from './features.js';
import { logger } from './logger.js';
function pageListenerEntries(listeners) {
    return Object.entries(listeners);
}
function addPageListener(page, name, listener) {
    const onPageEvent = page.on.bind(page);
    onPageEvent(name, listener);
}
function removePageListener(page, name, listener) {
    const offPageEvent = page.off.bind(page);
    offPageEvent(name, listener);
}
function createIdGenerator() {
    let i = 1;
    return () => {
        if (i === Number.MAX_SAFE_INTEGER) {
            i = 0;
        }
        return i++;
    };
}
export const stableIdSymbol = Symbol('stableIdSymbol');
export const networkRequestObservedAtSymbol = Symbol('networkRequestObservedAtSymbol');
/**
 * Caches the response body buffer eagerly captured at `requestfinished` time,
 * before a subsequent navigation lets the browser evict it. Stored as a
 * Promise so concurrent readers dedupe onto a single capture. Lives on the
 * request object, so it is GC'd together with the request when its navigation
 * bucket is dropped.
 */
export const responseBodyCacheSymbol = Symbol('responseBodyCacheSymbol');
/**
 * Resolved size in bytes of the cached response body that was counted against
 * the per-page budget. Read synchronously when a request is evicted, so its
 * bytes can be reclaimed from the budget.
 */
const responseBodySizeSymbol = Symbol('responseBodySizeSymbol');
function consoleTypeFromCdp(type) {
    return type === 'warning' ? 'warn' : type;
}
function remoteObjectValue(arg) {
    if (arg.type === 'undefined')
        return undefined;
    if ('value' in arg)
        return arg.value;
    if (arg.unserializableValue !== undefined)
        return arg.unserializableValue;
    if (arg.description !== undefined)
        return arg.description;
    return arg.type;
}
function remoteObjectText(arg) {
    const value = remoteObjectValue(arg);
    if (value === undefined)
        return 'undefined';
    if (typeof value === 'string')
        return value;
    if (typeof value === 'object' && value !== null) {
        try {
            return JSON.stringify(value) ?? String(value);
        }
        catch {
            return String(value);
        }
    }
    return String(value);
}
function syntheticConsoleMessage(event) {
    const callFrame = event.stackTrace?.callFrames?.[0];
    const args = event.args.map((arg) => ({
        jsonValue: async () => remoteObjectValue(arg),
    }));
    return {
        type: () => consoleTypeFromCdp(event.type),
        text: () => event.args.map(remoteObjectText).join(' '),
        location: () => ({
            url: callFrame?.url ?? '',
            lineNumber: callFrame?.lineNumber ?? 0,
            columnNumber: callFrame?.columnNumber ?? 0,
        }),
        args: () => args,
    };
}
/**
 * Per-response size cap. Responses larger than this are not cached (they would
 * dominate memory); reads fall back to a live fetch instead.
 */
export const MAX_CACHED_BODY_BYTES = 5 * 1024 * 1024;
/**
 * Per-page total budget for cached response bodies. Once exceeded, further
 * responses are marked skipped rather than cached.
 */
export const MAX_CACHED_TOTAL_BYTES = 50 * 1024 * 1024;
/**
 * Upper bound on retained network request records per page. The network
 * collector keeps a single flat FIFO queue (navigation-agnostic): once the
 * queue exceeds this cap the oldest request is evicted, and evicting a record
 * also reclaims its cached body bytes from the per-page budget so that budget is
 * a rolling window rather than a one-way ratchet. The analyst establishes a
 * clean baseline on demand via clear_network_requests, not via navigation — so
 * this is a memory backstop, not the workflow.
 */
const MAX_RETAINED_REQUESTS = 5000;
const BODY_CAPTURE_TIMEOUT_MS = 5000;
/**
 * Upper bound on retained per-page initiator entries, sized to match the request
 * queue cap so an in-queue request still finds its initiator: initiators are
 * recorded on a different CDP event than the request record, so the two FIFOs
 * trim in lockstep rather than one stranding the other. Bounded by a FIFO cap
 * (oldest dropped first) and wiped wholesale by clear_network_requests.
 */
const MAX_INITIATOR_ENTRIES = 5000;
export class PageCollector {
    #context;
    #listenersInitializer;
    #listeners = new WeakMap();
    #maxNavigationSaved = 3;
    #maxItemsPerNavigation = 1000;
    /**
     * This maps a Page to a list of navigations with a sub-list
     * of all collected resources.
     * The newer navigations come first.
     */
    storage = new WeakMap();
    constructor(context, listeners) {
        this.#context = context;
        this.#listenersInitializer = listeners;
    }
    get context() {
        return this.#context;
    }
    async init() {
        const pages = this.#context.pages();
        for (const page of pages) {
            this.addPage(page);
        }
        this.#context.on('page', this.#onPageCreated);
    }
    dispose() {
        this.#context.off('page', this.#onPageCreated);
    }
    #onPageCreated = (page) => {
        this.addPage(page);
        page.on('close', () => {
            this.cleanupPageDestroyed(page);
        });
    };
    addPage(page) {
        this.#initializePage(page);
    }
    #initializePage(page) {
        if (this.storage.has(page)) {
            return;
        }
        const idGenerator = createIdGenerator();
        const storedLists = [[]];
        this.storage.set(page, storedLists);
        const listeners = this.#listenersInitializer(value => {
            const withId = value;
            withId[stableIdSymbol] = idGenerator();
            this.store(page, withId);
        });
        listeners['framenavigated'] = (frame) => {
            // Only split the storage on main frame navigation
            if (frame !== page.mainFrame()) {
                return;
            }
            this.splitAfterNavigation(page);
        };
        for (const [name, listener] of pageListenerEntries(listeners)) {
            addPageListener(page, name, listener);
        }
        this.#listeners.set(page, listeners);
    }
    /**
     * Append a collected item to the page's storage. Default implementation keeps
     * the bucketed-by-navigation model (current bucket capped at
     * #maxItemsPerNavigation). NetworkCollector overrides this with a flat FIFO.
     */
    store(page, withId) {
        const navigations = this.storage.get(page) ?? [[]];
        navigations[0].push(withId);
        if (navigations[0].length > this.#maxItemsPerNavigation) {
            navigations[0].shift();
        }
    }
    splitAfterNavigation(page) {
        const navigations = this.storage.get(page);
        if (!navigations) {
            return;
        }
        // Add the latest navigation first
        navigations.unshift([]);
        navigations.splice(this.#maxNavigationSaved);
    }
    cleanupPageDestroyed(page) {
        const listeners = this.#listeners.get(page);
        if (listeners) {
            for (const [name, listener] of pageListenerEntries(listeners)) {
                removePageListener(page, name, listener);
            }
        }
        this.storage.delete(page);
    }
    getData(page, includePreservedData) {
        const navigations = this.storage.get(page);
        if (!navigations) {
            return [];
        }
        if (!includePreservedData) {
            return navigations[0];
        }
        const data = [];
        // Return every retained navigation bucket, not a fixed window. Collectors
        // that trim on navigation (e.g. console) stay bounded; the network
        // collector keeps all buckets until the page closes, so a request stays
        // reachable as long as its object is alive — which is also what the eagerly
        // cached response body relies on.
        for (let index = navigations.length - 1; index >= 0; index--) {
            if (navigations[index]) {
                data.push(...navigations[index]);
            }
        }
        return data;
    }
    getIdForResource(resource) {
        return resource[stableIdSymbol] ?? -1;
    }
    getById(page, stableId) {
        const navigations = this.storage.get(page);
        if (!navigations) {
            throw new Error('No requests found for selected page');
        }
        const item = this.find(page, item => item[stableIdSymbol] === stableId);
        if (item) {
            return item;
        }
        throw new Error('Request not found for selected page');
    }
    find(page, filter) {
        const navigations = this.storage.get(page);
        if (!navigations) {
            return;
        }
        for (const navigation of navigations) {
            const item = navigation.find(filter);
            if (item) {
                return item;
            }
        }
        return;
    }
}
export class ConsoleCollector extends PageCollector {
    #subscribedPages = new WeakMap();
    #runtimeConsoleSubscribers = new WeakMap();
    #sessionProvider;
    // Per-page issue collectors that feed into the PageCollector's storage
    #pageIssueCollectors = new WeakMap();
    #cdpReady = false;
    constructor(context, sessionProvider, listeners) {
        // Wrap the original listener initializer to capture per-page collectors
        const wrappedListeners = (collector) => {
            // Call the original to get the base listeners
            const baseListeners = listeners(collector);
            // The 'issue' key in baseListeners calls collector(event)
            // We'll also use this collector reference for PageIssueSubscriber
            return baseListeners;
        };
        super(context, wrappedListeners);
        this.#sessionProvider = sessionProvider;
    }
    addPage(page) {
        super.addPage(page);
        // Only set up CDP issue subscriber if CDP has been initialized
        if (this.#cdpReady) {
            this.#setupIssueSubscriber(page);
            void this.#setupRuntimeConsoleSubscriber(page);
        }
    }
    /**
     * Initialize CDP-dependent features (Audits.enable for issue collection).
     * Called lazily to avoid leaking CDP signals during navigation.
     */
    async initCdp() {
        if (this.#cdpReady)
            return;
        this.#cdpReady = true;
        // Set up issue subscribers for all already-tracked pages
        const runtimeSubscriptions = [];
        for (const page of this.context.pages()) {
            if (this.storage.has(page)) {
                this.#setupIssueSubscriber(page);
                runtimeSubscriptions.push(this.#setupRuntimeConsoleSubscriber(page));
            }
        }
        await Promise.all(runtimeSubscriptions);
    }
    async #setupRuntimeConsoleSubscriber(page) {
        if (this.#runtimeConsoleSubscribers.has(page)) {
            return;
        }
        try {
            const session = await this.#sessionProvider.getSession(page);
            const handler = (event) => {
                this.#storeCdpConsoleMessage(page, syntheticConsoleMessage(event));
            };
            this.#runtimeConsoleSubscribers.set(page, { session, handler });
            addCdpEventListener(session, 'Runtime.consoleAPICalled', handler);
            await session.send('Runtime.enable');
        }
        catch (error) {
            const subscriber = this.#runtimeConsoleSubscribers.get(page);
            if (subscriber) {
                removeCdpEventListener(subscriber.session, 'Runtime.consoleAPICalled', subscriber.handler);
                this.#runtimeConsoleSubscribers.delete(page);
            }
            logger('Error subscribing to console runtime events', error);
        }
    }
    #storeCdpConsoleMessage(page, message) {
        const navigations = this.storage.get(page);
        if (!navigations) {
            return;
        }
        const withId = message;
        withId[stableIdSymbol] = this.#nextStableId(page);
        this.store(page, withId);
    }
    #nextStableId(page) {
        const navigations = this.storage.get(page) ?? [];
        let max = 0;
        for (const navigation of navigations) {
            for (const item of navigation) {
                const id = item[stableIdSymbol];
                if (typeof id === 'number' && id > max) {
                    max = id;
                }
            }
        }
        return max + 1;
    }
    #setupIssueSubscriber(page) {
        if (!features.issues) {
            return;
        }
        if (!this.#subscribedPages.has(page)) {
            // Create a direct collector that adds issues to this page's storage with stable IDs
            const idGen = createIdGenerator();
            const issueCollector = (issue) => {
                const navigations = this.storage.get(page);
                if (navigations && navigations[0]) {
                    const withId = issue;
                    withId[stableIdSymbol] = idGen();
                    navigations[0].push(withId);
                }
            };
            this.#pageIssueCollectors.set(page, issueCollector);
            const subscriber = new PageIssueSubscriber(page, this.#sessionProvider, issueCollector);
            this.#subscribedPages.set(page, subscriber);
            void subscriber.subscribe();
        }
    }
    cleanupPageDestroyed(page) {
        super.cleanupPageDestroyed(page);
        const runtimeSubscriber = this.#runtimeConsoleSubscribers.get(page);
        if (runtimeSubscriber) {
            removeCdpEventListener(runtimeSubscriber.session, 'Runtime.consoleAPICalled', runtimeSubscriber.handler);
            this.#runtimeConsoleSubscribers.delete(page);
        }
        this.#subscribedPages.get(page)?.unsubscribe();
        this.#subscribedPages.delete(page);
    }
}
class PageIssueSubscriber {
    #issueManager = new FakeIssuesManager();
    #issueAggregator = new IssueAggregator(this.#issueManager);
    #seenKeys = new Set();
    #seenIssues = new Set();
    #page;
    #sessionProvider;
    #session = null;
    #onIssueCallback;
    constructor(page, sessionProvider, onIssue) {
        this.#page = page;
        this.#sessionProvider = sessionProvider;
        this.#onIssueCallback = onIssue;
    }
    #resetIssueAggregator() {
        this.#issueManager = new FakeIssuesManager();
        if (this.#issueAggregator) {
            this.#issueAggregator.removeEventListener("AggregatedIssueUpdated" /* IssueAggregatorEvents.AGGREGATED_ISSUE_UPDATED */, this.#onAggregatedissue);
        }
        this.#issueAggregator = new IssueAggregator(this.#issueManager);
        this.#issueAggregator.addEventListener("AggregatedIssueUpdated" /* IssueAggregatorEvents.AGGREGATED_ISSUE_UPDATED */, this.#onAggregatedissue);
    }
    async subscribe() {
        this.#resetIssueAggregator();
        this.#page.on('framenavigated', this.#onFrameNavigated);
        try {
            this.#session = await this.#sessionProvider.getSession(this.#page);
            addCdpEventListener(this.#session, 'Audits.issueAdded', this.#onIssueAdded);
            await this.#session.send('Audits.enable');
        }
        catch (error) {
            logger('Error subscribing to issues', error);
        }
    }
    unsubscribe() {
        this.#seenKeys.clear();
        this.#seenIssues.clear();
        this.#page.off('framenavigated', this.#onFrameNavigated);
        if (this.#session) {
            removeCdpEventListener(this.#session, 'Audits.issueAdded', this.#onIssueAdded);
        }
        if (this.#issueAggregator) {
            this.#issueAggregator.removeEventListener("AggregatedIssueUpdated" /* IssueAggregatorEvents.AGGREGATED_ISSUE_UPDATED */, this.#onAggregatedissue);
        }
        if (this.#session) {
            void this.#session.send('Audits.disable').catch(() => {
                // might fail.
            });
        }
    }
    #onAggregatedissue = (event) => {
        if (this.#seenIssues.has(event.data)) {
            return;
        }
        this.#seenIssues.add(event.data);
        this.#onIssueCallback(event.data);
    };
    // On navigation, we reset issue aggregation.
    #onFrameNavigated = (frame) => {
        // Only split the storage on main frame navigation
        if (frame !== frame.page().mainFrame()) {
            return;
        }
        this.#seenKeys.clear();
        this.#seenIssues.clear();
        this.#resetIssueAggregator();
    };
    #onIssueAdded = (data) => {
        try {
            const inspectorIssue = data.issue;
            // @ts-expect-error Types of protocol from Playwright and CDP are
            // incomparable for InspectorIssueCode, one is union, other is enum.
            const issue = createIssuesFromProtocolIssue(null, inspectorIssue)[0];
            if (!issue) {
                logger('No issue mapping for for the issue: ', inspectorIssue.code);
                return;
            }
            const primaryKey = issue.primaryKey();
            if (this.#seenKeys.has(primaryKey)) {
                return;
            }
            this.#seenKeys.add(primaryKey);
            this.#issueManager.dispatchEventToListeners("IssueAdded" /* IssuesManagerEvents.ISSUE_ADDED */, {
                issue,
                // @ts-expect-error We don't care that issues model is null
                issuesModel: null,
            });
        }
        catch (error) {
            logger('Error creating a new issue', error);
        }
    };
}
const cdpRequestIdSymbol = Symbol('cdpRequestId');
/**
 * Per-page running total of cached response body bytes. Keyed weakly so it is
 * released when the page is GC'd; also cleared explicitly on page destroy.
 */
const responseBodyBudget = new WeakMap();
function pageForRequest(req) {
    try {
        // frame() can throw for service worker requests.
        return req.frame()?.page();
    }
    catch {
        return undefined;
    }
}
function withCaptureTimeout(promise) {
    return Promise.race([
        promise,
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timed out capturing response body')), BODY_CAPTURE_TIMEOUT_MS)),
    ]);
}
/**
 * Eagerly fetch and cache a response body while the producing loader is still
 * alive (called from `requestfinished`). After a navigation the browser evicts
 * the body and a later `body()` call would fail; the cache lets inspect/export
 * still return it. Fire-and-forget: the Promise is stored on the request so
 * concurrent readers await the same capture.
 */
function captureResponseBody(req) {
    const request = req;
    if (request[responseBodyCacheSymbol]) {
        return;
    }
    request[responseBodyCacheSymbol] = (async () => {
        try {
            const resp = await req.response();
            if (!resp) {
                return { ok: false, error: 'No response available' };
            }
            const declared = Number(resp.headers()['content-length'] ?? 0);
            if (declared > MAX_CACHED_BODY_BYTES) {
                return {
                    ok: 'skipped',
                    reason: `content-length ${declared} exceeds cache limit`,
                };
            }
            const buffer = await withCaptureTimeout(resp.body());
            if (buffer.length > MAX_CACHED_BODY_BYTES) {
                return {
                    ok: 'skipped',
                    reason: `body ${buffer.length} bytes exceeds cache limit`,
                };
            }
            const page = pageForRequest(req);
            if (page) {
                const budget = responseBodyBudget.get(page) ?? { bytes: 0 };
                if (budget.bytes + buffer.length > MAX_CACHED_TOTAL_BYTES) {
                    return { ok: 'skipped', reason: 'page cache budget exhausted' };
                }
                budget.bytes += buffer.length;
                responseBodyBudget.set(page, budget);
                // Record the counted size so eviction can reclaim it from the budget.
                request[responseBodySizeSymbol] = buffer.length;
            }
            return { ok: true, buffer };
        }
        catch (error) {
            return {
                ok: false,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    })();
}
function initiatorKey(url, method) {
    return `${method} ${url}`;
}
/**
 * Detect Patchright's internal addInitScript injection request.
 *
 * When addInitScript is used (persistent hooks, import_state), Patchright issues
 * a sentinel navigation to `patchright-init-script-inject.internal` as its
 * injection mechanism. This request is not real page traffic — it pollutes the
 * network list and, because it is typed as a document request, can mask the real
 * document request. It is filtered out of all network collection.
 */
function isInternalInjectionRequest(req) {
    try {
        return req.url().includes('patchright-init-script-inject.internal');
    }
    catch {
        return false;
    }
}
export class NetworkCollector extends PageCollector {
    // Initiators keyed by CDP requestId. Requires cdpRequestIdSymbol to have been
    // mapped onto the request, which races against event delivery.
    #initiators = new WeakMap();
    // Initiators keyed by "METHOD url". Order-independent fallback used when the
    // requestId mapping lost the race, so the initiator is still recoverable.
    #initiatorsByKey = new WeakMap();
    #cdpListeners = new WeakMap();
    #sessionProvider;
    #cdpReady = false;
    constructor(context, sessionProvider, listeners) {
        const baseListeners = listeners ??
            (collect => {
                return {
                    request: req => {
                        const request = req;
                        request[networkRequestObservedAtSymbol] = Date.now();
                        collect(req);
                    },
                };
            });
        // Always capture the response body at requestfinished — before a navigation
        // can evict it — regardless of which listeners variant is supplied.
        super(context, collect => {
            // Filter out internal Patchright addInitScript injection requests
            // (patchright-init-script-inject.internal). These are produced when
            // addInitScript is used (persistent hooks, import_state) and otherwise
            // pollute the network list and can mask the real document request.
            const filteredCollect = (item) => {
                if (isInternalInjectionRequest(item))
                    return;
                collect(item);
            };
            const map = baseListeners(filteredCollect);
            const existingFinished = map.requestfinished;
            map.requestfinished = req => {
                if (isInternalInjectionRequest(req))
                    return;
                captureResponseBody(req);
                existingFinished?.(req);
            };
            return map;
        });
        this.#sessionProvider = sessionProvider;
    }
    addPage(page) {
        super.addPage(page);
        // Only set up CDP initiator collection if CDP has been initialized
        if (this.#cdpReady) {
            void this.#setupInitiatorCollection(page);
        }
    }
    /**
     * Initialize CDP-dependent features (initiator collection).
     * Called lazily to avoid leaking CDP signals during navigation.
     */
    async initCdp() {
        if (this.#cdpReady)
            return;
        this.#cdpReady = true;
        // Set up CDP initiator collection for all already-tracked pages
        for (const page of this.context.pages()) {
            if (this.storage.has(page)) {
                void this.#setupInitiatorCollection(page);
            }
        }
    }
    async #setupInitiatorCollection(page) {
        if (this.#initiators.has(page)) {
            return;
        }
        const initiatorMap = new Map();
        this.#initiators.set(page, initiatorMap);
        const initiatorByKey = new Map();
        this.#initiatorsByKey.set(page, initiatorByKey);
        try {
            const client = await this.#sessionProvider.getSession(page);
            await client.send('Network.enable');
            // Listen to CDP events for initiator info and request ID mapping
            const onRequestWillBeSent = (event) => {
                if (event.initiator) {
                    initiatorMap.set(event.requestId, event.initiator);
                    // Also key by URL+method so getInitiator can recover the initiator
                    // even when the requestId mapping below loses the delivery race.
                    initiatorByKey.set(initiatorKey(event.request.url, event.request.method), event.initiator);
                    // Bound memory: drop oldest entries beyond the cap (Map preserves
                    // insertion order, so the first key is the oldest).
                    while (initiatorMap.size > MAX_INITIATOR_ENTRIES) {
                        const oldest = initiatorMap.keys().next().value;
                        if (oldest === undefined) {
                            break;
                        }
                        initiatorMap.delete(oldest);
                    }
                    while (initiatorByKey.size > MAX_INITIATOR_ENTRIES) {
                        const oldest = initiatorByKey.keys().next().value;
                        if (oldest === undefined) {
                            break;
                        }
                        initiatorByKey.delete(oldest);
                    }
                }
                // Map CDP request ID to Playwright Request via URL+method matching
                // This allows us to correlate Playwright Request objects with CDP request IDs
                const navigations = this.storage.get(page);
                if (navigations) {
                    for (const navigation of navigations) {
                        for (const request of navigation) {
                            const req = request;
                            if (!req[cdpRequestIdSymbol] &&
                                req.url() === event.request.url &&
                                req.method() === event.request.method) {
                                req[cdpRequestIdSymbol] = event.requestId;
                                break;
                            }
                        }
                    }
                }
            };
            addCdpEventListener(client, 'Network.requestWillBeSent', onRequestWillBeSent);
            const cleanup = () => {
                removeCdpEventListener(client, 'Network.requestWillBeSent', onRequestWillBeSent);
            };
            this.#cdpListeners.set(page, cleanup);
        }
        catch {
            // Page might already be closed
        }
    }
    cleanupPageDestroyed(page) {
        super.cleanupPageDestroyed(page);
        const cleanup = this.#cdpListeners.get(page);
        if (cleanup) {
            try {
                cleanup();
            }
            catch {
                // Page might already be closed
            }
        }
        this.#cdpListeners.delete(page);
        this.#initiators.delete(page);
        this.#initiatorsByKey.delete(page);
        responseBodyBudget.delete(page);
    }
    /**
     * Get the CDP request ID for a request.
     */
    getCdpRequestId(request) {
        return request[cdpRequestIdSymbol];
    }
    /**
     * Get the initiator info for a request.
     * @param page The page the request belongs to
     * @param request The HTTP request
     * @returns The initiator info or undefined if not found
     */
    getInitiator(page, request) {
        // Preferred: exact CDP requestId match (when the mapping won the race).
        const requestId = this.getCdpRequestId(request);
        const byId = requestId
            ? this.#initiators.get(page)?.get(requestId)
            : undefined;
        if (byId) {
            return byId;
        }
        // Fallback: URL+method correlation. The requestId mapping requires the
        // Playwright request to already be in storage when the CDP event fires,
        // which races against event delivery; this lookup is order-independent.
        let url;
        let method;
        try {
            url = request.url();
            method = request.method();
        }
        catch {
            return undefined;
        }
        return this.#initiatorsByKey.get(page)?.get(initiatorKey(url, method));
    }
    /**
     * Get initiator by CDP request ID.
     */
    getInitiatorByRequestId(page, requestId) {
        const initiatorMap = this.#initiators.get(page);
        return initiatorMap?.get(requestId);
    }
    /**
     * Append a request to the page's flat FIFO queue. The network collector is
     * navigation-agnostic: a single bucket (index 0) holds the most recent
     * MAX_RETAINED_REQUESTS requests. Evicting the oldest reclaims its cached
     * response body bytes from the per-page budget, so the 50MB budget is a
     * rolling window, never a one-way ratchet.
     */
    store(page, withId) {
        const navigations = this.storage.get(page) ?? [[]];
        const queue = navigations[0];
        queue.push(withId);
        while (queue.length > MAX_RETAINED_REQUESTS) {
            const evicted = queue.shift();
            if (evicted) {
                this.#reclaimResponseBodyBudget(page, [evicted]);
            }
        }
    }
    /**
     * Navigation does not split or trim the network queue. Requests accumulate in
     * one FIFO bucket regardless of navigation, so a request that already fired
     * (e.g. the POST that triggered a redirect) stays inspectable afterwards. The
     * analyst trims on demand via clear(), not on navigation — see the method doc
     * and MAX_RETAINED_REQUESTS.
     */
    splitAfterNavigation(_page) {
        // Intentionally a no-op.
    }
    /**
     * Drop all collected requests for a page and release every parallel structure
     * that tracks them: the cached response body budget and both initiator maps.
     * Lets the analyst establish a clean baseline before the action they want to
     * study (the DevTools "clear, then act" workflow). The per-page stable-id
     * counter lives in a closure in #initializePage and is intentionally out of
     * reach here, so reqids stay monotonic and are never reused after a clear.
     */
    clear(page) {
        const navigations = this.storage.get(page);
        let requestCount = 0;
        if (navigations) {
            for (const bucket of navigations) {
                requestCount += bucket.length;
            }
        }
        const budget = responseBodyBudget.get(page);
        const reclaimedBytes = budget?.bytes ?? 0;
        if (budget) {
            budget.bytes = 0;
        }
        if (navigations) {
            navigations.length = 1;
            navigations[0] = [];
        }
        this.#initiators.get(page)?.clear();
        this.#initiatorsByKey.get(page)?.clear();
        return { requestCount, reclaimedBytes };
    }
    #reclaimResponseBodyBudget(page, evicted) {
        const budget = responseBodyBudget.get(page);
        if (!budget) {
            return;
        }
        for (const request of evicted) {
            const size = request[responseBodySizeSymbol];
            if (typeof size === 'number') {
                budget.bytes -= size;
            }
        }
        if (budget.bytes < 0) {
            budget.bytes = 0;
        }
    }
}
