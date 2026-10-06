"""A tiny pixel canvas with just enough primitives for hand-placed 8-bit art.

Pixels hold hex color strings (or None for transparent). Everything is integer
pixel coordinates with (0, 0) at the top-left, x growing right and y growing down.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

from PIL import Image


def hex_to_rgba(c: str) -> tuple[int, int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255


def mix(a: str, b: str, t: float) -> str:
    """Blend hex color a toward b by t (0..1)."""
    ra, ga, ba, _ = hex_to_rgba(a)
    rb, gb, bb, _ = hex_to_rgba(b)
    return "#%02x%02x%02x" % (
        round(ra + (rb - ra) * t),
        round(ga + (gb - ga) * t),
        round(ba + (bb - ba) * t),
    )


class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.px: list[list[str | None]] = [[None] * w for _ in range(h)]

    # -- basic access -----------------------------------------------------
    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x: int, y: int) -> str | None:
        return self.px[y][x] if self.inside(x, y) else None

    def set(self, x: int, y: int, c: str | None) -> None:
        if self.inside(x, y):
            self.px[y][x] = c

    def opaque(self, x: int, y: int) -> bool:
        return self.get(x, y) is not None

    # -- primitives -------------------------------------------------------
    def rect(self, x: int, y: int, w: int, h: int, c: str | None) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def hline(self, x0: int, x1: int, y: int, c: str | None) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.set(x, y, c)

    def vline(self, x: int, y0: int, y1: int, c: str | None) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.set(x, y, c)

    def line(self, x0: int, y0: int, x1: int, y1: int, c: str | None, width: int = 1) -> None:
        """Bresenham line; `width` paints a horizontal run starting at each point."""
        for x, y in line_points(x0, y0, x1, y1):
            for i in range(width):
                self.set(x + i, y, c)

    def stroke(self, x0: int, y0: int, x1: int, y1: int, c: str | None, w: int = 1) -> None:
        """Line drawn with a square w x w brush (good for limbs at any angle)."""
        o = (w - 1) // 2
        for x, y in line_points(x0, y0, x1, y1):
            self.rect(x - o, y - o, w, w, c)

    def oval(self, x: int, y: int, w: int, h: int, c: str | None) -> None:
        """Filled ellipse inscribed in the box (x, y, w, h)."""
        cx, cy = x + w / 2, y + h / 2
        rx, ry = w / 2, h / 2
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                dx = (xx + 0.5 - cx) / rx
                dy = (yy + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1.08:
                    self.set(xx, yy, c)

    def stamp(self, x: int, y: int, rows: Iterable[str], key: Mapping[str, str | None]) -> None:
        """Paint ASCII art. Characters missing from `key` (e.g. '.') are skipped."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in key:
                    self.set(x + i, y + j, key[ch])

    def recolor_where(self, mask: "Canvas", c: str) -> None:
        """Paint c wherever this canvas is opaque AND mask is opaque."""
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None and mask.px[y][x] is not None:
                    self.px[y][x] = c

    # -- whole-canvas ops -------------------------------------------------
    def outline(self, c: str, diagonal: bool = False) -> None:
        """Add a 1px outline of color c around every opaque region."""
        nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diagonal:
            nbrs += [(1, 1), (-1, -1), (1, -1), (-1, 1)]
        w, h, px = self.w, self.h, self.px
        edge = set()
        for y, row in enumerate(px):          # visit filled pixels, mark empty neighbors
            for x, p in enumerate(row):
                if p is None:
                    continue
                for dx, dy in nbrs:
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and px[yy][xx] is None:
                        edge.add((xx, yy))
        for x, y in edge:
            px[y][x] = c

    def tint(self, c: str, t: float) -> None:
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None:
                    self.px[y][x] = mix(self.px[y][x], c, t)

    def paste(self, other: "Canvas", dx: int = 0, dy: int = 0) -> None:
        for y in range(other.h):
            for x in range(other.w):
                if other.px[y][x] is not None:
                    self.set(x + dx, y + dy, other.px[y][x])

    def flipped(self) -> "Canvas":
        out = Canvas(self.w, self.h)
        out.px = [list(reversed(row)) for row in self.px]
        return out

    def row_span(self, y: int) -> tuple[int, int] | None:
        xs = [x for x in range(self.w) if self.px[y][x] is not None] if 0 <= y < self.h else []
        return (xs[0], xs[-1]) if xs else None

    def bbox(self) -> tuple[int, int, int, int] | None:
        pts = [(x, y) for y in range(self.h) for x in range(self.w) if self.px[y][x] is not None]
        if not pts:
            return None
        xs, ys = zip(*pts)
        return min(xs), min(ys), max(xs), max(ys)

    def to_image(self, scale: int = 1) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        img.putdata([hex_to_rgba(c) if c else (0, 0, 0, 0) for row in self.px for c in row])
        if scale != 1:
            img = img.resize((self.w * scale, self.h * scale), Image.NEAREST)
        return img


def line_points(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def wave(frame: int, n: int, amp: float = 1.0, offset: float = 0.0) -> int:
    """Integer sine for wiggly animations: frame in 0..n-1."""
    return round(amp * math.sin(2 * math.pi * (frame / n) + offset))
