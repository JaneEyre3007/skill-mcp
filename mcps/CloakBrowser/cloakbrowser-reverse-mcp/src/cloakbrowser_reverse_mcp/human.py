from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from typing import Any, Literal, Tuple

Range = Tuple[float, float]
HumanPreset = Literal["default", "careful"]


@dataclass
class HumanConfig:
    typing_delay: float = 70
    typing_delay_spread: float = 40
    typing_pause_chance: float = 0.1
    typing_pause_range: Range = (400, 1000)
    key_hold: Range = (15, 35)
    shift_down_delay: Range = (30, 70)
    shift_up_delay: Range = (20, 50)
    mistype_chance: float = 0.02
    mistype_delay_notice: Range = (100, 300)
    mistype_delay_correct: Range = (50, 150)
    mouse_steps_divisor: float = 8
    mouse_min_steps: int = 25
    mouse_max_steps: int = 80
    mouse_wobble_max: float = 1.5
    mouse_overshoot_chance: float = 0.15
    mouse_overshoot_px: Range = (3, 6)
    mouse_burst_size: Range = (3, 5)
    mouse_burst_pause: Range = (8, 18)
    click_aim_delay_input: Range = (60, 140)
    click_aim_delay_button: Range = (80, 200)
    click_hold_input: Range = (40, 100)
    click_hold_button: Range = (60, 150)
    click_input_x_range: Range = (0.05, 0.30)
    scroll_delta_base: Range = (80, 130)
    scroll_pause_fast: Range = (30, 80)
    scroll_pause_slow: Range = (80, 200)
    scroll_settle_delay: Range = (300, 600)
    initial_cursor_x: Range = (400, 700)
    initial_cursor_y: Range = (45, 60)


def _rr(r: Range) -> float:
    return random.uniform(r[0], r[1])


def _ri(r: Range) -> int:
    return random.randint(int(r[0]), int(r[1]))


async def _sleep_ms(ms: float) -> None:
    if ms > 0:
        await asyncio.sleep(ms / 1000.0)


def resolve_config(preset: HumanPreset = "default", overrides: dict | None = None) -> HumanConfig:
    cfg = HumanConfig()
    if preset == "careful":
        cfg.typing_delay = 100
        cfg.typing_pause_chance = 0.15
        cfg.mouse_overshoot_chance = 0.10
        cfg.click_aim_delay_input = (80, 180)
        cfg.click_aim_delay_button = (120, 280)
        cfg.scroll_pause_fast = (100, 200)
        cfg.scroll_pause_slow = (250, 600)
    if overrides:
        for key, value in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
    return cfg


class Point:
    __slots__ = ("x", "y")
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _ease(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def _bezier(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1 - t
    return Point(
        (u ** 3) * p0.x + 3 * (u ** 2) * t * p1.x + 3 * u * (t ** 2) * p2.x + (t ** 3) * p3.x,
        (u ** 3) * p0.y + 3 * (u ** 2) * t * p1.y + 3 * u * (t ** 2) * p2.y + (t ** 3) * p3.y,
    )


def _control_points(start: Point, end: Point) -> tuple[Point, Point]:
    dx, dy = end.x - start.x, end.y - start.y
    dist = math.hypot(dx, dy) or 1
    px, py = -dy / dist, dx / dist
    return (
        Point(start.x + dx * 0.25 + px * random.uniform(-0.3, 0.3) * dist, start.y + dy * 0.25 + py * random.uniform(-0.3, 0.3) * dist),
        Point(start.x + dx * 0.75 + px * random.uniform(-0.3, 0.3) * dist, start.y + dy * 0.75 + py * random.uniform(-0.3, 0.3) * dist),
    )


async def human_move(page: Any, state: dict[str, float | bool], x: float, y: float, cfg: HumanConfig) -> None:
    if not state.get("initialized"):
        state["x"] = _rr(cfg.initial_cursor_x)
        state["y"] = _rr(cfg.initial_cursor_y)
        state["initialized"] = True
    sx, sy = float(state["x"]), float(state["y"])
    dist = math.hypot(x - sx, y - sy)
    if dist < 1:
        return
    steps = max(cfg.mouse_min_steps, min(cfg.mouse_max_steps, round(dist / cfg.mouse_steps_divisor)))
    start, end = Point(sx, sy), Point(x, y)
    cp1, cp2 = _control_points(start, end)
    burst = _ri(cfg.mouse_burst_size)
    counter = 0
    for i in range(steps + 1):
        progress = i / steps
        pt = _bezier(start, cp1, cp2, end, _ease(progress))
        wobble = math.sin(math.pi * progress) * cfg.mouse_wobble_max
        await page.mouse.move(round(pt.x + random.uniform(-wobble, wobble)), round(pt.y + random.uniform(-wobble, wobble)))
        counter += 1
        if counter >= burst and i < steps:
            await _sleep_ms(_rr(cfg.mouse_burst_pause))
            counter = 0
    if random.random() < cfg.mouse_overshoot_chance:
        angle = math.atan2(y - sy, x - sx)
        over = _rr(cfg.mouse_overshoot_px)
        await page.mouse.move(round(x + math.cos(angle) * over), round(y + math.sin(angle) * over))
        await _sleep_ms(random.uniform(30, 70))
        await page.mouse.move(round(x + random.uniform(-2, 2)), round(y + random.uniform(-2, 2)))
    state["x"], state["y"] = x, y


async def human_click_selector(page: Any, state: dict[str, float | bool], selector: str, cfg: HumanConfig) -> None:
    loc = page.locator(selector).first
    await loc.wait_for(state="visible", timeout=30000)
    box = await loc.bounding_box()
    if not box:
        raise RuntimeError("element has no bounding box")
    tag = await loc.evaluate("el => el.tagName.toLowerCase()")
    is_input = tag in ("input", "textarea") or bool(await loc.evaluate("el => el.isContentEditable"))
    if is_input:
        x = box["x"] + box["width"] * _rr(cfg.click_input_x_range)
        y = box["y"] + box["height"] * random.uniform(0.30, 0.70)
    else:
        x = box["x"] + box["width"] * random.uniform(0.35, 0.65)
        y = box["y"] + box["height"] * random.uniform(0.35, 0.65)
    await human_move(page, state, x, y, cfg)
    await _sleep_ms(_rr(cfg.click_aim_delay_input if is_input else cfg.click_aim_delay_button))
    await page.mouse.down()
    await _sleep_ms(_rr(cfg.click_hold_input if is_input else cfg.click_hold_button))
    await page.mouse.up()


SHIFT_SYMBOLS = frozenset('@#!$%^&*()_+{}|:"<>?~')


async def human_type_text(page: Any, text: str, cfg: HumanConfig, cdp_session: Any = None) -> None:
    for i, ch in enumerate(text):
        if not ch.isascii():
            await _sleep_ms(_rr(cfg.key_hold))
            await page.keyboard.insert_text(ch)
        elif ch.isupper() and ch.isalpha():
            await page.keyboard.down("Shift")
            await _sleep_ms(_rr(cfg.shift_down_delay))
            await page.keyboard.press(ch)
            await _sleep_ms(_rr(cfg.shift_up_delay))
            await page.keyboard.up("Shift")
        elif ch in SHIFT_SYMBOLS and cdp_session is not None:
            await page.keyboard.down("Shift")
            await _sleep_ms(_rr(cfg.shift_down_delay))
            await cdp_session.send("Input.dispatchKeyEvent", {"type": "char", "text": ch, "unmodifiedText": ch})
            await _sleep_ms(_rr(cfg.shift_up_delay))
            await page.keyboard.up("Shift")
        else:
            await page.keyboard.down(ch)
            await _sleep_ms(_rr(cfg.key_hold))
            await page.keyboard.up(ch)
        if i < len(text) - 1:
            if random.random() < cfg.typing_pause_chance:
                await _sleep_ms(_rr(cfg.typing_pause_range))
            else:
                await _sleep_ms(max(10, cfg.typing_delay + random.uniform(-cfg.typing_delay_spread, cfg.typing_delay_spread)))


async def human_scroll(page: Any, state: dict[str, float | bool], delta_y: int, cfg: HumanConfig) -> None:
    remaining = abs(delta_y)
    sign = 1 if delta_y >= 0 else -1
    while remaining > 0:
        chunk = min(random.randint(20, 45), remaining)
        await page.mouse.wheel(0, chunk * sign)
        remaining -= chunk
        await _sleep_ms(random.uniform(8, 25))
    await _sleep_ms(_rr(cfg.scroll_settle_delay))
