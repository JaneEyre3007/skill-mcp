/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setupCloak } from './cloak.js';
import { installConsoleBridge } from './consoleBridge.js';
import { logger } from './logger.js';
import { chromium } from './third_party/index.js';
let browserResult;
let runtimeOverrides;
export function setRuntimeLaunchOverrides(overrides) {
    runtimeOverrides = overrides;
}
export function getRuntimeLaunchOverrides() {
    return runtimeOverrides;
}
const BROWSER_OCCUPIED_MESSAGE = 'The MCP browser is currently occupied by another session. Ask the user to close the other MCP/browser debugging window, or start a separate session with --isolated or a different --browserUrl.';
// Persistent user data directories.
//
// IMPORTANT: cloak and non-cloak profiles MUST be physically isolated. They
// use different Chromium binaries with different feature sets — mixing state
// (extensions, shader cache, service workers) across them causes startup
// races and broken sessions. Pick the directory based on whether --cloak is
// set; never share.
//
// Keep js-reverse-mcp profiles local to this MCP checkout so they never lock
// chrome-devtools-mcp's default profile.
const MCP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const DEFAULT_USER_DATA_DIR = path.join(MCP_ROOT, 'chrome-reverse-profile');
const DEFAULT_CLOAK_DATA_DIR = path.join(MCP_ROOT, 'cloak-reverse-profile');
export async function ensureBrowserConnected(options) {
    if (browserResult) {
        return browserResult;
    }
    if (!options.browserURL) {
        throw new Error('browserURL must be provided');
    }
    // Resolve the WebSocket debugger URL from the CDP HTTP endpoint.
    const url = new URL('/json/version', options.browserURL);
    const res = await fetch(url.toString());
    const json = (await res.json());
    const endpoint = json.webSocketDebuggerUrl;
    if (!endpoint) {
        throw new Error(`No webSocketDebuggerUrl in CDP /json/version response from ${options.browserURL}. ` +
            'Make sure the browser was started with --remote-debugging-port.');
    }
    logger('Connecting Patchright via CDP to', endpoint);
    let browser;
    try {
        browser = await chromium.connectOverCDP(endpoint);
    }
    catch (error) {
        if (isBrowserOccupiedError(error)) {
            throw new Error(`${BROWSER_OCCUPIED_MESSAGE} The CDP endpoint ${options.browserURL} appears to be in use.`, { cause: error });
        }
        throw error;
    }
    logger('Connected Patchright');
    const context = browser.contexts()[0];
    if (!context) {
        throw new Error('No browser context found after connecting');
    }
    browserResult = { browser, context, closeMode: 'connected-cdp' };
    // Clear cached result when browser disconnects so we can reconnect.
    browser.on('disconnected', () => {
        logger('Browser disconnected, clearing cached browser result');
        browserResult = undefined;
    });
    return browserResult;
}
/** Block image loading via route interception (mirrors Python's block_images).
 *  Uses resourceType() for accurate detection (catches extensionless image
 *  endpoints and query-string URLs). route.fallback() passes non-image
 *  requests to the next registered handler so instrumentation routes are
 *  not bypassed.
 */
async function blockImages(context) {
    await context.route('**/*', route => {
        if (route.request().resourceType() === 'image') {
            return route.abort();
        }
        return route.fallback();
    });
}
export async function launch(options) {
    const { isolated } = options;
    // --cloak: resolve the CloakBrowser binary and fingerprint seed before
    // anything else. For persistent profiles the seed is persisted there so the
    // virtual identity is stable across launches; --isolated gets a fresh seed.
    //
    // Cloak and non-cloak modes use SEPARATE persistent profile directories —
    // they're different browsers with different feature sets, sharing profile
    // state breaks both.
    const persistentProfileDir = isolated
        ? undefined
        : (options.userDataDir ??
            (options.cloak ? DEFAULT_CLOAK_DATA_DIR : DEFAULT_USER_DATA_DIR));
    const cloakSetup = options.cloak
        ? await setupCloak(persistentProfileDir, options.cloakBinaryPath, options.fingerprintSeed)
        : null;
    const executablePath = cloakSetup?.executablePath;
    const args = [
        '--test-type',
        '--hide-crash-restore-bubble',
        ...(options.windowWidth && options.windowHeight
            ? [`--window-size=${options.windowWidth},${options.windowHeight}`]
            : []),
        ...(cloakSetup?.args ?? []),
        // Disable WebRTC to prevent IP leaks (mirrors Python's block_webrtc option).
        ...(options.blockWebRtc
            ? ['--enforce-webrtc-ip-handling-policy=disable-non-proxied-udp']
            : []),
    ];
    // System Chrome stable when not using cloak; cloak provides its own binary.
    const channel = executablePath ? undefined : 'chrome';
    // Build context options. viewport:null exposes real OS dimensions (avoids
    // the 1280x720 fake-viewport bot signal). New options mirror Python version.
    const contextOptions = {
        viewport: null,
        ignoreHTTPSErrors: true,
        ...(options.proxy ? { proxy: { server: options.proxy } } : {}),
        ...(options.locale ? { locale: options.locale } : {}),
        ...(options.timezone ? { timezoneId: options.timezone } : {}),
    };
    // --isolated mode: launch() + newContext() for clean isolated context.
    // Creates an incognito-like context with no persisted state.
    if (isolated) {
        const browser = await chromium.launch({
            channel,
            executablePath,
            headless: options.headless ?? false,
            chromiumSandbox: true,
            args,
        });
        const context = await browser.newContext(contextOptions);
        await installConsoleBridge(context);
        if (options.blockImages)
            await blockImages(context);
        if (context.pages().length === 0)
            await context.newPage();
        return { browser, context, closeMode: 'launched' };
    }
    // Default: launchPersistentContext for full state persistence
    // (cookies, IndexedDB, Cache Storage, Service Workers, localStorage).
    // persistentProfileDir is non-undefined here because the isolated branch
    // returned above; assert via the non-null assertion to satisfy the type.
    const userDataDir = persistentProfileDir;
    try {
        const context = await chromium.launchPersistentContext(userDataDir, {
            channel,
            executablePath,
            headless: options.headless ?? false,
            chromiumSandbox: true,
            args,
            ...contextOptions,
        });
        await installConsoleBridge(context);
        if (options.blockImages)
            await blockImages(context);
        return { browser: undefined, context, closeMode: 'persistent-context' };
    }
    catch (error) {
        if (isBrowserOccupiedError(error)) {
            throw new Error(`${BROWSER_OCCUPIED_MESSAGE} The persistent browser profile is already in use: ${userDataDir}.`, { cause: error });
        }
        throw error;
    }
}
export async function ensureBrowserLaunched(options) {
    if (browserResult) {
        return browserResult;
    }
    browserResult = await launch(options);
    // Clear cached result when browser is manually closed so we can relaunch.
    const { browser, context } = browserResult;
    if (browser) {
        browser.on('disconnected', () => {
            logger('Browser disconnected, clearing cached browser result');
            browserResult = undefined;
        });
    }
    else {
        // Persistent context mode (no browser object) — listen on context.
        context.on('close', () => {
            logger('Browser context closed, clearing cached browser result');
            browserResult = undefined;
        });
    }
    return browserResult;
}
function isBrowserOccupiedError(error) {
    const message = (error instanceof Error ? error.message : String(error)).toLowerCase();
    return [
        'the browser is already running',
        'processsingleton',
        'another cdp client already connected',
        'already connected',
        'already attached',
        'already in use',
    ].some(fragment => message.includes(fragment));
}
export async function closeBrowser(reason) {
    const result = browserResult;
    if (!result) {
        return;
    }
    browserResult = undefined;
    const closeReason = `MCP shutdown: ${reason}`;
    logger('Closing browser due to', closeReason);
    if (result.closeMode === 'connected-cdp' && result.browser) {
        await closeConnectedCdpBrowser(result.browser, closeReason);
        return;
    }
    if (result.closeMode === 'launched' && result.browser) {
        await result.context.close({ reason: closeReason }).catch(error => {
            logger('Failed to close browser context during shutdown', error);
        });
        await result.browser.close({ reason: closeReason }).catch(error => {
            logger('Failed to close browser during shutdown', error);
        });
        return;
    }
    await result.context.close({ reason: closeReason }).catch(error => {
        logger('Failed to close persistent browser context during shutdown', error);
    });
}
async function closeConnectedCdpBrowser(browser, reason) {
    if (browser.isConnected()) {
        try {
            const session = await browser.newBrowserCDPSession();
            await session.send('Browser.close');
        }
        catch (error) {
            logger('Failed to send Browser.close over CDP during shutdown', error);
        }
    }
    await browser.close({ reason }).catch(error => {
        logger('Failed to close connected browser transport during shutdown', error);
    });
}
