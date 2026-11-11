"""Meet Cute art: the reproductive-tract maze, the two lovebirds, the organs
that deliver them, and the contraception that wants to keep them apart.

Drawn with the same canvas, palette and 1px outline as the main cast. The maze
walls are fleshy tubes in the womb's flesh ramp, and every sprite faces right so
the game can rotate it to the way it's swimming.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.palette import INK, OUTLINE, TECH_BRO

from ..womb_rave.art import F

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

OVUM = {"corona": "#ffe0a0", "zona": "#fff4ec", "cyto": "#ffc4b0", "cyto_sh": "#f09a90",
        "nucleus": "#e0708a", "blush": "#ff6a8a", "mouth": "#c85a6a"}


def egg(frame: int) -> Canvas:
    """An ovum: a big round cell in its clear shell, ringed with follicle cells,
    nucleus showing. Rolls rather than swims."""
    c = Canvas(13, 13)
    for i in range(10):                                  # corona radiata
        a = i * math.tau / 10 + frame * 0.4
        c.set(6 + round(math.cos(a) * 5.6), 6 + round(math.sin(a) * 5.6), OVUM["corona"])
    c.oval(1, 1, 11, 11, OVUM["zona"])
    c.oval(2, 2, 9, 9, OVUM["cyto"])
    for x in range(4, 9):
        c.set(x, 10, OVUM["cyto_sh"])
    c.oval(7, 2, 3, 3, OVUM["nucleus"])
    hx, hy = [(4, 3), (3, 5), (4, 4), (5, 3)][frame % 4]
    c.set(hx, hy, "#ffffff")
    c.set(4, 6, INK)
    c.set(8, 6, INK)
    c.set(6, 8, OVUM["mouth"])
    c.outline(OUTLINE)
    return c


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
    c.set(3, 7, OVUM["blush"])
    c.set(9, 7, OVUM["blush"])
    return c


def zygote(cells: int, frame: int) -> Canvas:
    """After the meet cute: a fertilized egg dividing into 1, 2, 4, 8 cells."""
    c = Canvas(19, 19)
    for i in range(14):
        a = i * math.tau / 14 + frame * 0.3
        c.set(9 + round(math.cos(a) * 8.4), 9 + round(math.sin(a) * 8.4), OVUM["corona"])
    c.oval(1, 1, 17, 17, OVUM["zona"])
    c.oval(2, 2, 15, 15, OVUM["cyto"])
    spots = {1: [(9, 9, 9)], 2: [(6, 9, 6), (12, 9, 6)],
             4: [(6, 6, 5), (12, 6, 5), (6, 12, 5), (12, 12, 5)],
             8: [(5, 5, 4), (9, 4, 4), (13, 5, 4), (4, 9, 4), (14, 9, 4), (5, 13, 4), (9, 14, 4), (13, 13, 4)]}[cells]
    for x, y, d in spots:
        c.oval(x - d // 2, y - d // 2, d, d, "#ffd8c8")
        c.set(x - d // 2 + 1, y - d // 2 + 1, "#ffffff")
    c.set(7, 9, INK)
    c.set(11, 9, INK)
    c.hline(8, 10, 11, OVUM["mouth"])
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


# -- the delivery ------------------------------------------------------------------

def _bez(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def tube_path(mouth: tuple[int, int], ovary: tuple[int, int], n: int = 48) -> list[tuple[float, float]]:
    """The fallopian tube from the ovary up to its mouth at the maze, as points."""
    (mx, my), (ox, oy) = mouth, ovary
    return [_bez((ox, oy - 5), (ox - 18, oy - 36), (mx - 24, my), (mx, my), i / n) for i in range(n + 1)]


def fallopian(w: int, h: int, mouth: tuple[int, int], ovary: tuple[int, int]) -> Canvas:
    """The ovary and its fallopian tube, curling up to open into the maze with a
    fringe of fimbriae."""
    c = Canvas(w, h)
    pts = tube_path(mouth, ovary)
    for x, y in pts:
        c.oval(round(x) - 2, round(y) - 2, 5, 5, F["pink"])
    for x, y in pts[::2]:
        c.set(round(x), round(y) - 1, F["light"])
    for x, y in pts:
        c.set(round(x), round(y), F["mid"])               # the lumen
    mx, my = mouth
    for dy in (-4, -2, 0, 2, 4):                          # fimbriae, reaching for the egg
        c.line(mx - 2, my + dy // 2, mx + 2, my + dy, F["light"])
    ox, oy = ovary
    c.oval(ox - 9, oy - 6, 18, 13, F["ovary"])
    c.oval(ox - 7, oy + 2, 15, 4, F["ovary_sh"])
    for fx, fy in ((-4, -2), (2, -4), (4, 1), (-1, 2), (6, -2)):   # follicles
        c.oval(ox + fx - 1, oy + fy - 1, 3, 3, F["follicle"])
    c.outline(OUTLINE)
    return c


PENIS_TIP = (1, 12)              # where the sperm comes out, in the sprite


def penis(droop: float = 0.0, squirt: bool = False) -> Canvas:
    """Pointing left, base and balls off to the right. `droop` 0..1 is how limp."""
    skin, sh, hi = TECH_BRO["skin"], TECH_BRO["skin_sh"], "#f8d4b4"
    c = Canvas(42, 30)
    bx, by = 32, 12
    tx, ty = 8, 12 + droop * 12
    mid_y = by + droop * 3
    pts = [(bx + (tx - bx) * t, (1 - t) ** 2 * by + 2 * (1 - t) * t * mid_y + t * t * ty) for t in [i / 24 for i in range(25)]]
    c.oval(25, 15, 11, 11, sh)                            # balls
    c.oval(30, 16, 11, 11, sh)
    c.oval(31, 17, 6, 4, skin)
    for x, y in pts:
        c.oval(round(x) - 4, round(y) - 4, 9, 8, skin)
    for x, y in pts[3:]:
        c.set(round(x), round(y) + 3, sh)
        c.set(round(x), round(y) - 3, hi)
    for x, y in pts[6:20:6]:                              # a vein
        c.set(round(x), round(y) + 1, "#d8a080")
    gx, gy = round(tx), round(ty)
    c.oval(gx - 7, gy - 4, 10, 8, "#e07a90")              # glans
    c.hline(gx - 5, gx - 3, gy - 3, "#ffb0c0")
    c.vline(gx + 2, gy - 3, gy + 3, "#c05a78")
    c.set(gx - 7, gy, INK)
    for x, y in ((35, 3), (37, 6), (39, 2), (34, 7), (39, 9), (41, 5), (38, 12), (36, 1), (40, 14)):
        c.set(x, y, "#4a2f1b")                            # a little bush
    c.outline(OUTLINE)
    if squirt:
        for x, y in ((0, gy), (0, gy - 1), (0, gy + 1)):
            c.set(x, y, "#ffffff")
    return c


# -- the contraception ---------------------------------------------------------------

ENEMIES = ("condom", "pill", "spermicide", "iud")       # the starting four, one per pen slot
EXTRAS = ("diaphragm", "sponge", "patch")               # turn up later in the round


def enemy(kind: str, frame: int, look: tuple[int, int]) -> Canvas:
    c = Canvas(13, 13)
    if kind == "condom":                                 # unrolled, reservoir tip wagging
        col, hi, sh = "#5ab8ff", "#b8e8ff", "#2a78c8"
        c.rect(5 + frame % 2, 0, 2, 2, col)
        c.oval(2, 1, 9, 6, col)
        c.rect(2, 4, 9, 6, col)
        c.vline(3, 3, 8, hi)
        c.vline(9, 4, 9, sh)
        c.rect(1, 10, 11, 2, sh)                         # the rolled-up ring
        c.hline(2, 10, 10, col)
        _eyes(c, 3, 4, look)
    elif kind == "pill":                                 # birth-control dial pack
        c.oval(0, 0, 13, 13, "#ff9ac8")
        c.oval(2, 2, 9, 9, "#ffc0dc")
        for i in range(10):
            if i == frame % 2 * 5:
                continue                                 # today's pill, already taken
            a = i * math.tau / 10
            c.set(6 + round(math.cos(a) * 5), 6 + round(math.sin(a) * 5), "#ffffff")
        _eyes(c, 3, 4, look)
        c.hline(5, 7, 8, "#c8407f")
    elif kind == "spermicide":                           # squeeze tube of gel, oozing
        tin, ridge, tube, gel, dark = "#c8ccd8", "#8a90a0", "#f4f4f4", "#6ad84a", "#2f8a20"
        c.rect(1, 0, 11, 2, tin)                         # crimped end
        for x in range(2, 11, 2):
            c.set(x, 1, ridge)
        squeeze = frame % 2
        c.rect(2, 2, 9, 7, tube)
        c.vline(2 + squeeze, 5, 6, None if squeeze else tube)    # pinched in the middle
        c.vline(10 - squeeze, 5, 6, None if squeeze else tube)
        c.hline(3, 9, 9, tube)                           # shoulder
        c.rect(2 + squeeze, 6, 9 - 2 * squeeze, 3, gel)  # the label
        c.hline(5, 7, 7, dark)
        c.hline(5, 7, 10, dark)                          # nozzle
        c.hline(5, 7, 11, gel)                           # gel oozing out
        c.hline(4 + squeeze, 8 - squeeze, 12, gel)
        _eyes(c, 3, 2, look)
    elif kind == "iud":                                  # copper T
        cu, sh = "#e08a4a", "#a85a2a"
        c.rect(0, 1, 13, 3, cu)
        c.hline(0, 12, 3, sh)
        c.rect(5, 1, 3, 10, cu)
        c.vline(7, 4, 10, sh)
        c.vline(6, 11, 12, "#d8d8e0" if frame % 2 else "#a8a8b8")   # strings
        c.set(0, 0, cu)
        c.set(12, 0, cu)
        _eyes(c, 2, 0, look, 6)
    elif kind == "diaphragm":                            # rubber dome with a stiff rim
        c.oval(1, 2 + frame % 2, 11, 10, "#f0d8b0")
        c.rect(0, 8, 13, 5, None)
        c.rect(0, 7 + frame % 2, 13, 2, "#c8a878")
        c.set(3, 4, "#fff4e0")
        _eyes(c, 3, 3 + frame % 2, look)
    elif kind == "sponge":                               # with its little loop
        c.rect(1, 3, 11, 9, "#ffd84a")
        c.hline(4, 8, 0 + frame % 2, "#f4f4f4")
        c.vline(4, 1, 3, "#f4f4f4")
        c.vline(8, 1, 3, "#f4f4f4")
        for x, y in ((2, 9), (5, 10), (9, 9), (10, 5), (2, 4), (7, 11)):
            c.set(x, y, "#c89820")
        _eyes(c, 3, 4, look)
    else:                                                # the patch
        c.rect(1, 1, 11, 11, "#e8c8a8")
        c.rect(3, 3, 7, 7, "#f4e0c8")
        for x, y in ((1, 1), (11, 1), (1, 11), (11, 11)):
            c.set(x, y, None)
        c.set(2 + frame % 2 * 8, 11, "#c8a888")          # a corner peeling up
        _eyes(c, 3, 4, look)
    c.outline(OUTLINE)
    return c


def scared(frame: int, flash: bool) -> Canvas:
    """Any contraception once someone's eaten folic acid: blue, wobbly, failing."""
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
