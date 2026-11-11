"""Meet Cute art: the reproductive-tract maze, the two lovebirds and the
immune system that wants to keep them apart.

Drawn with the same canvas, palette and 1px outline as the main cast. The maze
walls are fleshy tubes in the womb's flesh ramp, and every sprite faces right so
the game can rotate it to the way it's swimming.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.palette import INK, OUTLINE

from ..womb_rave.art import F, egg  # noqa: F401  (egg is re-exported for the game)
from ..stork_bomber.art import poly

TILE = 8


def _eyes(c: Canvas, x: int, y: int, look: tuple[int, int], gap: int = 4) -> None:
    """Two googly eyes, pupils shifted toward `look`."""
    lx, ly = look
    for ex in (x, x + gap):
        c.rect(ex, y, 3, 3, "#ffffff")
        c.set(ex + 1 + lx, y + 1 + ly, INK)


# -- the maze ----------------------------------------------------------------------

def maze(grid: list[str], ox: int, oy: int, w: int, h: int, seed: int = 0) -> Canvas:
    """The walls of the maze ('#' tiles) as flesh tubes, on a transparent floor.
    `ox, oy` is where tile (0, 0) sits on the screen-sized canvas."""
    rng = random.Random(seed)
    c = Canvas(w, h)
    rows, cols = len(grid), len(grid[0])
    wall = lambda tx, ty: 0 <= ty < rows and 0 <= tx < cols and grid[ty][tx] == "#"
    for ty in range(rows):
        for tx in range(cols):
            if not wall(tx, ty):
                continue
            x, y = ox + tx * TILE, oy + ty * TILE
            # inset the sides that face a corridor so walls read as round tubes
            l = 0 if wall(tx - 1, ty) else 1
            r = 0 if wall(tx + 1, ty) else 1
            t = 0 if wall(tx, ty - 1) else 1
            b = 0 if wall(tx, ty + 1) else 1
            c.rect(x + l, y + t, TILE - l - r, TILE - t - b, F["warm"])
            if t:
                c.hline(x + l + 1, x + TILE - r - 2, y + t, F["light"])
            if b:
                c.hline(x + l, x + TILE - r - 1, y + TILE - b - 1, F["mid"])
            if l:
                c.vline(x + l, y + t + 1, y + TILE - b - 2, F["pink"])
            if r:
                c.vline(x + TILE - r - 1, y + t, y + TILE - b - 1, F["mid"])
            if rng.random() < 0.18:                      # a vein or two
                vx, vy = x + rng.randint(2, 5), y + rng.randint(2, 5)
                c.set(vx, vy, F["vein_hi"])
                c.set(vx + 1, vy + rng.choice((-1, 0, 1)), F["vein_hi"])
    # round off the outer corners of every wall run
    for ty in range(rows):
        for tx in range(cols):
            if not wall(tx, ty):
                continue
            x, y = ox + tx * TILE, oy + ty * TILE
            for dx, dy, px, py in ((-1, -1, 1, 1), (1, -1, TILE - 2, 1), (-1, 1, 1, TILE - 2), (1, 1, TILE - 2, TILE - 2)):
                if not wall(tx + dx, ty) and not wall(tx, ty + dy):
                    c.set(x + px, y + py, None)
    c.outline(OUTLINE)
    return c


def pen_door(w: int) -> Canvas:
    """The membrane across the door of the enemies' pen."""
    c = Canvas(w, 2)
    for x in range(w):
        c.set(x, 0, "#ffc0cc" if x % 2 else "#e87a8a")
        c.set(x, 1, "#e87a8a")
    return c


def nutrient(frame: int) -> Canvas:
    c = Canvas(3, 3)
    col = ("#ffe8a8", "#fff5d8")[frame % 2]
    c.set(1, 0, col)
    c.hline(0, 2, 1, col)
    c.set(1, 2, col)
    c.set(1, 1, "#ffffff")
    return c


def folic(frame: int) -> Canvas:
    """A folic-acid capsule. Eat one and the immune system panics."""
    c = Canvas(9, 6)
    c.oval(0, 0, 9, 6, "#ff5a8a")
    for y in range(6):
        for x in range(4, 9):
            if c.get(x, y):
                c.set(x, y, "#ffe14d")
    c.hline(2, 6, 1, "#ffffff" if frame % 2 else "#ffd8e4")
    c.outline(OUTLINE)
    return c


# -- the lovebirds -----------------------------------------------------------------

def sperm(frame: int, look: tuple[int, int] = (1, 0)) -> Canvas:
    """Swimming right, tail lashing behind. Determined."""
    c = Canvas(16, 11)
    for i in range(9):                                   # tail, wiggling more toward the tip
        x = 8 - i
        y = 5 + round(2.0 * math.sin(i * 0.9 - frame * 2.0) * i / 8)
        c.set(x, y, "#e8e8f8" if i < 5 else "#b8b8d8")
        if i < 3:
            c.set(x, y + 1, "#d0d0e8")
    c.oval(7, 1, 9, 9, "#f4f4f4")
    c.oval(8, 5, 6, 3, "#c8c8e0")
    c.set(14, 4, "#ffffff")
    c.set(10, 3, INK)
    c.set(13, 3, INK)
    c.hline(10, 12, 6, INK)                              # grim little mouth
    c.outline(OUTLINE)
    return c


def egg_blush(frame: int) -> Canvas:
    """The egg, flushed: she's spotted him."""
    c = egg(frame)
    c.set(3, 7, "#ff7a9a")
    c.set(9, 7, "#ff7a9a")
    return c


def zygote(cells: int, frame: int) -> Canvas:
    """After the meet cute: a fertilized egg dividing into 1, 2, 4, 8 cells."""
    c = Canvas(19, 19)
    for i in range(14):
        a = i * math.tau / 14 + frame * 0.3
        c.set(9 + round(math.cos(a) * 8.4), 9 + round(math.sin(a) * 8.4), "#fff0b0")
    c.oval(2, 2, 15, 15, "#ffe14d")
    spots = {1: [(9, 9, 9)], 2: [(6, 9, 6), (12, 9, 6)],
             4: [(6, 6, 5), (12, 6, 5), (6, 12, 5), (12, 12, 5)],
             8: [(5, 5, 4), (9, 4, 4), (13, 5, 4), (4, 9, 4), (14, 9, 4), (5, 13, 4), (9, 14, 4), (13, 13, 4)]}[cells]
    for x, y, d in spots:
        c.oval(x - d // 2, y - d // 2, d, d, "#fff5a8")
        c.set(x - d // 2 + 1, y - d // 2 + 1, "#ffffff")
    c.set(7, 9, INK)
    c.set(11, 9, INK)
    c.hline(8, 10, 11, "#d8a020")
    c.outline(OUTLINE)
    return c


def heart(big: bool = False) -> Canvas:
    rows = ([".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."] if big
            else [".#.#.", "#####", ".###.", "..#.."])
    c = Canvas(len(rows[0]), len(rows))
    c.stamp(0, 0, rows, {"#": "#ff4a7a", ".": None})
    c.set(1, 1, "#ffc0cc")
    if big:
        c.outline(OUTLINE)
    return c


# -- the immune system -------------------------------------------------------------

ENEMIES = ("macrophage", "antibody", "spermicide", "iud")


def enemy(kind: str, frame: int, look: tuple[int, int]) -> Canvas:
    c = Canvas(13, 13)
    if kind == "macrophage":                             # white blood cell: lumpy, hungry
        c.oval(1, 2, 11, 10, "#f0eef8")
        for i in range(5):
            a = i * math.tau / 5 + frame * 0.6
            px, py = 6 + round(math.cos(a) * 5), 7 + round(math.sin(a) * 4.5)
            c.oval(px - 1, py - 1, 3, 3, "#f0eef8")
        c.oval(3, 7, 4, 3, "#b48ad8")                    # lobed nucleus
        c.oval(6, 8, 4, 3, "#9a6ac8")
        _eyes(c, 2, 3, look)
    elif kind == "antibody":                             # Y-shaped, grabby
        col, sh = "#b46bff", "#7a3ac8"
        c.stroke(6, 12, 6, 7, col, 3)
        c.stroke(6, 7, 1 + (frame % 2), 1, col, 3)
        c.stroke(6, 7, 11 - (frame % 2), 1, col, 3)
        c.vline(7, 8, 12, sh)
        c.rect(4, 5, 5, 4, col)
        _eyes(c, 2, 4, look, 5)
    elif kind == "spermicide":                           # gel blob, dripping
        col = "#6ad84a"
        c.oval(1, 1, 11, 9, col)
        c.oval(3, 2, 4, 2, "#b8ff8a")
        for i, x in enumerate((2, 5, 8, 10)):
            drop = 2 + (frame + i) % 3
            c.vline(x, 8, 8 + drop, col)
            c.set(x, 9 + drop, "#3a9a2a")
        _eyes(c, 2, 3, look)
        c.hline(4, 8, 7, "#1e5a14")
    else:                                                # copper IUD
        cu, sh = "#e08a4a", "#a85a2a"
        c.rect(0, 1, 13, 3, cu)
        c.hline(0, 12, 3, sh)
        c.rect(5, 1, 3, 10, cu)
        c.vline(7, 4, 10, sh)
        c.vline(6, 11, 12, "#d8d8e0" if frame % 2 else "#a8a8b8")   # strings
        c.set(0, 0, cu)
        c.set(12, 0, cu)
        _eyes(c, 2, 0, look, 6)
    c.outline(OUTLINE)
    return c


def scared(frame: int, flash: bool) -> Canvas:
    """Any enemy once someone's eaten folic acid: blue, wobbly, sorry."""
    body, face = ("#e8e8ff", "#ff4a6a") if flash else ("#3a4ad8", "#ffc0cc")
    c = Canvas(13, 13)
    c.oval(1, 1, 11, 10, body)
    for x in range(1, 12, 2):
        c.vline(x + (frame % 2), 9, 11, body)
    c.rect(3, 4, 2, 2, face)
    c.rect(8, 4, 2, 2, face)
    for x in range(3, 10):
        c.set(x, 8 - (x + frame) % 2, face)
    c.outline(OUTLINE)
    return c


def eyes_only(look: tuple[int, int]) -> Canvas:
    """What's left of an eaten enemy, scurrying back to the pen."""
    c = Canvas(13, 13)
    _eyes(c, 2, 4, look, 5)
    c.outline(OUTLINE)
    return c


def pop(frame: int, col: str) -> Canvas:
    """A burst when someone gets caught or eats an enemy."""
    c = Canvas(17, 17)
    r = 2 + frame * 2
    for i in range(8):
        a = i * math.tau / 8
        x, y = 8 + round(math.cos(a) * r), 8 + round(math.sin(a) * r)
        c.set(x, y, col)
        c.set(x + (1 if math.cos(a) > 0.3 else -1 if math.cos(a) < -0.3 else 0), y, mix(col, "#ffffff", 0.5))
    return c
