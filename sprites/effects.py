"""Whole-sprite effects applied after the body is composited."""

from __future__ import annotations

import math

from .canvas import Canvas, mix
from .palette import INK, OUTLINE
from .rig import CX, GROUND

GOO = "#7fd13b"
GOO_HI = "#d4ff7a"
EYE_W = "#f4f4f4"


def hit_flash(c: Canvas, amount: float = 0.8) -> None:
    """Classic arcade hit flash: everything but the outline goes nearly white."""
    for y in range(c.h):
        for x in range(c.w):
            p = c.px[y][x]
            if p is not None and p != OUTLINE:
                c.px[y][x] = mix(p, "#ffffff", amount)


def _noise(x: int) -> float:
    """Smooth 0..1 wobble across columns, so neighbors droop together."""
    return 0.5 + 0.5 * math.sin(x * 0.55) * math.cos(x * 0.21 + 1.0)


def melt(c: Canvas, t: float) -> None:
    """Dissolve the sprite into a puddle of lab goo. t: 0 (solid) .. 1 (puddle).

    Each column sags toward the floor by a slightly different amount (drippy
    edges), loses most of its height, spreads sideways and turns green.
    """
    src = [[p if p != OUTLINE else None for p in row] for row in c.px]
    cols = [x for x in range(c.w) if any(src[y][x] for y in range(c.h))]
    if not cols:
        return
    mid = (cols[0] + cols[-1]) / 2
    width = cols[-1] - cols[0] + 1
    spread = min(1 + 0.9 * t * t, (c.w - 6) / width)   # puddle stays inside the frame
    out = Canvas(c.w, c.h)
    tops: dict[int, int] = {}
    for ox in range(c.w):
        sx = round(mid + (ox - CX) / spread)          # the puddle pools under the body center
        if not 0 <= sx < c.w:
            continue
        col = [(y, src[y][sx]) for y in range(c.h) if src[y][sx]]
        if not col:
            continue
        keep = max(1, round(len(col) * (1 - 0.86 * t)))
        picked = [col[round(i * (len(col) - 1) / max(1, keep - 1))] for i in range(keep)]
        top = col[0][0]
        new_top = round(top + t * (GROUND - top) * (0.55 + 0.45 * _noise(sx)))
        if t >= 0.75 or new_top + keep - 1 > GROUND:
            new_top = GROUND - keep + 1                 # late frames: everything is on the floor
        for i, (_, color) in enumerate(picked):
            out.set(ox, new_top + i, mix(color, GOO, min(1.0, 0.75 * t)))
        bottom = new_top + keep - 1
        if bottom < GROUND and _noise(sx) > 0.75:       # drips hanging off sagging bits
            out.vline(ox, bottom + 1, min(GROUND, bottom + 1 + round(3 * t)), GOO)
        tops[ox] = new_top

    xs = sorted(tops)
    if 0.4 <= t < 1.0:                                 # bubbles popping on the surface
        for k, x in enumerate(xs[2::5]):
            if (k + round(t * 8)) % 2 == 0:
                out.set(x, tops[x] - 1, GOO_HI)
    if t >= 1.0 and xs:                                # one eyeball bobbing in the puddle
        ex = xs[len(xs) // 2]
        ey = tops[ex] - 2
        out.stamp(ex - 1, ey, [".ww", "wwP"], {"w": EYE_W, "P": INK})

    out.outline(OUTLINE)
    c.px = out.px
