/**
 * @license
 * Copyright 2026
 * SPDX-License-Identifier: Apache-2.0
 */
// ---------------------------------------------------------------------------
// Defaults / presets
// ---------------------------------------------------------------------------
export function defaultHumanConfig() {
    return {
        typingDelay: 70,
        typingDelaySpread: 40,
        typingPauseChance: 0.1,
        typingPauseRange: [400, 1000],
        keyHold: [15, 35],
        shiftDownDelay: [30, 70],
        shiftUpDelay: [20, 50],
        mistypeChance: 0.02,
        mistypeDelayNotice: [100, 300],
        mistypeDelayCorrect: [50, 150],
        mouseStepsDivisor: 8,
        mouseMinSteps: 25,
        mouseMaxSteps: 80,
        mouseWobbleMax: 1.5,
        mouseOvershootChance: 0.15,
        mouseOvershootPx: [3, 6],
        mouseBurstSize: [3, 5],
        mouseBurstPause: [8, 18],
        clickAimDelayInput: [60, 140],
        clickAimDelayButton: [80, 200],
        clickHoldInput: [40, 100],
        clickHoldButton: [60, 150],
        clickInputXRange: [0.05, 0.3],
        scrollDeltaBase: [80, 130],
        scrollPauseFast: [30, 80],
        scrollPauseSlow: [80, 200],
        scrollSettleDelay: [300, 600],
        initialCursorX: [400, 700],
        initialCursorY: [45, 60],
    };
}
export function carefulHumanConfig() {
    const cfg = defaultHumanConfig();
    cfg.typingDelay = 100;
    cfg.typingPauseChance = 0.15;
    cfg.mouseOvershootChance = 0.1;
    cfg.clickAimDelayInput = [80, 180];
    cfg.clickAimDelayButton = [120, 280];
    cfg.scrollPauseFast = [100, 200];
    cfg.scrollPauseSlow = [250, 600];
    return cfg;
}
export function resolveHumanConfig(preset = 'default', overrides) {
    const cfg = preset === 'careful' ? carefulHumanConfig() : defaultHumanConfig();
    if (overrides)
        Object.assign(cfg, overrides);
    return cfg;
}
export function newCursorState() {
    return { x: 0, y: 0, initialized: false };
}
// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------
function rr([min, max]) {
    return Math.random() * (max - min) + min;
}
function ri([min, max]) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
function sleepMs(ms) {
    return new Promise(resolve => setTimeout(resolve, Math.max(0, ms)));
}
function ease(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
function bezier(p0, p1, p2, p3, t) {
    const u = 1 - t;
    return {
        x: u ** 3 * p0.x +
            3 * u ** 2 * t * p1.x +
            3 * u * t ** 2 * p2.x +
            t ** 3 * p3.x,
        y: u ** 3 * p0.y +
            3 * u ** 2 * t * p1.y +
            3 * u * t ** 2 * p2.y +
            t ** 3 * p3.y,
    };
}
function controlPoints(start, end) {
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const dist = Math.hypot(dx, dy) || 1;
    const px = -dy / dist;
    const py = dx / dist;
    return [
        {
            x: start.x + dx * 0.25 + px * (Math.random() * 0.6 - 0.3) * dist,
            y: start.y + dy * 0.25 + py * (Math.random() * 0.6 - 0.3) * dist,
        },
        {
            x: start.x + dx * 0.75 + px * (Math.random() * 0.6 - 0.3) * dist,
            y: start.y + dy * 0.75 + py * (Math.random() * 0.6 - 0.3) * dist,
        },
    ];
}
// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
/** Move the mouse cursor in a human-like Bezier curve path. */
export async function humanMove(page, state, x, y, cfg) {
    if (!state.initialized) {
        state.x = rr(cfg.initialCursorX);
        state.y = rr(cfg.initialCursorY);
        state.initialized = true;
    }
    const sx = state.x;
    const sy = state.y;
    const dist = Math.hypot(x - sx, y - sy);
    if (dist < 1)
        return;
    const steps = Math.max(cfg.mouseMinSteps, Math.min(cfg.mouseMaxSteps, Math.round(dist / cfg.mouseStepsDivisor)));
    const start = { x: sx, y: sy };
    const end = { x, y };
    const [cp1, cp2] = controlPoints(start, end);
    let burst = ri(cfg.mouseBurstSize);
    let counter = 0;
    for (let i = 0; i <= steps; i++) {
        const progress = i / steps;
        const pt = bezier(start, cp1, cp2, end, ease(progress));
        const wobble = Math.sin(Math.PI * progress) * cfg.mouseWobbleMax;
        await page.mouse.move(Math.round(pt.x + (Math.random() * 2 - 1) * wobble), Math.round(pt.y + (Math.random() * 2 - 1) * wobble));
        counter++;
        if (counter >= burst && i < steps) {
            await sleepMs(rr(cfg.mouseBurstPause));
            counter = 0;
            burst = ri(cfg.mouseBurstSize);
        }
    }
    if (Math.random() < cfg.mouseOvershootChance) {
        const angle = Math.atan2(y - sy, x - sx);
        const over = rr(cfg.mouseOvershootPx);
        await page.mouse.move(Math.round(x + Math.cos(angle) * over), Math.round(y + Math.sin(angle) * over));
        await sleepMs(Math.random() * 40 + 30);
        await page.mouse.move(Math.round(x + (Math.random() * 4 - 2)), Math.round(y + (Math.random() * 4 - 2)));
    }
    state.x = x;
    state.y = y;
}
/** Click an element by selector using human-like cursor movement. */
export async function humanClickSelector(page, state, selector, cfg) {
    const loc = page.locator(selector).first();
    await loc.waitFor({ state: 'visible', timeout: 30000 });
    const box = await loc.boundingBox();
    if (!box)
        throw new Error('element has no bounding box');
    const tag = (await loc.evaluate((el) => el.tagName.toLowerCase()));
    const isInput = ['input', 'textarea'].includes(tag) ||
        (await loc.evaluate((el) => el.isContentEditable));
    let x;
    let y;
    if (isInput) {
        x = box.x + box.width * rr(cfg.clickInputXRange);
        y = box.y + box.height * (Math.random() * 0.4 + 0.3);
    }
    else {
        x = box.x + box.width * (Math.random() * 0.3 + 0.35);
        y = box.y + box.height * (Math.random() * 0.3 + 0.35);
    }
    await humanMove(page, state, x, y, cfg);
    await sleepMs(rr(isInput ? cfg.clickAimDelayInput : cfg.clickAimDelayButton));
    await page.mouse.down();
    await sleepMs(rr(isInput ? cfg.clickHoldInput : cfg.clickHoldButton));
    await page.mouse.up();
}
const SHIFT_SYMBOLS = new Set('@#!$%^&*()_+{}|:"<>?~'.split(''));
/** Type text with human-like variable delays and occasional pauses. */
export async function humanTypeText(page, text, cfg) {
    for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (ch.charCodeAt(0) > 0x7f) {
            // Non-ASCII: insertText handles composition
            await sleepMs(rr(cfg.keyHold));
            await page.keyboard.insertText(ch);
        }
        else if (/^[A-Z]$/.test(ch)) {
            // Uppercase letter — Shift + lowercase key name is valid in Playwright
            await page.keyboard.down('Shift');
            await sleepMs(rr(cfg.shiftDownDelay));
            await page.keyboard.press(ch.toLowerCase());
            await sleepMs(rr(cfg.shiftUpDelay));
            await page.keyboard.up('Shift');
        }
        else if (SHIFT_SYMBOLS.has(ch)) {
            // Symbols that require Shift — keyboard.press() doesn't accept symbol
            // chars as key names, so use insertText with surrounding timing instead.
            await sleepMs(rr(cfg.shiftDownDelay));
            await page.keyboard.insertText(ch);
            await sleepMs(rr(cfg.shiftUpDelay));
        }
        else {
            await page.keyboard.down(ch);
            await sleepMs(rr(cfg.keyHold));
            await page.keyboard.up(ch);
        }
        if (i < text.length - 1) {
            if (Math.random() < cfg.typingPauseChance) {
                await sleepMs(rr(cfg.typingPauseRange));
            }
            else {
                const delay = cfg.typingDelay + (Math.random() * 2 - 1) * cfg.typingDelaySpread;
                await sleepMs(Math.max(10, delay));
            }
        }
    }
}
/** Scroll with human-like burst chunks and settle delay. */
export async function humanScroll(page, deltaY, cfg) {
    let remaining = Math.abs(deltaY);
    const sign = deltaY >= 0 ? 1 : -1;
    while (remaining > 0) {
        // Use scrollDeltaBase from config for chunk size
        const [chunkMin, chunkMax] = cfg.scrollDeltaBase;
        const chunk = Math.min(Math.floor(Math.random() * (chunkMax - chunkMin + 1)) + chunkMin, remaining);
        await page.mouse.wheel(0, chunk * sign);
        remaining -= chunk;
        // Alternate between fast and slow pauses like the Python version
        const pause = Math.random() < 0.7 ? rr(cfg.scrollPauseFast) : rr(cfg.scrollPauseSlow);
        await sleepMs(pause);
    }
    await sleepMs(rr(cfg.scrollSettleDelay));
}
