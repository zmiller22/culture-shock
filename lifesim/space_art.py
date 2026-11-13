"""Art for the cosmic zoom-out at the start of the program.

The zoom is a stack of nested levels, Powers-of-Ten style: each one is drawn
SCALE times bigger than the one inside it, and they're all centred on the same
point (the Earth). Every level is a CW x CH canvas whose centre (CX, CY) is
that point, and whose middle CW/SCALE pixels are left empty for the level
inside it. The game draws the levels on top of each other at the right sizes.

Levels, from the inside out:
    0  the Earth, with a stork in orbit
    1  the Moon, and the cow that jumps over it
    2  the inner planets, a sun in sunglasses, Russell's teapot and a lost dildo
    3  the outer planets: Saturn, Uranus (a butt), the Flying Spaghetti Monster
    4  the Milky Way, which is a pair of boobs
    5  the cosmic web, which is a brain
    6  the brain is in a jar on a shelf in the lab: UNIVERSE 7

Animated props (stork, cow, teapot, FSM...) are separate sprites the game puts
on top of their level, so they can move.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.font import draw_text_centered
from sprites.palette import INK, OUTLINE

SCALE = 6                       # each level is this many times bigger than the one inside it
CW, CH = 288, 162               # every level canvas; wider than the screen's aspect so it always fills it
CX, CY = CW // 2, CH // 2
NIGHT = "#050818"
LIGHT = (-0.55, -0.45, 0.70)    # sunlight comes from the upper left


def _blank() -> Canvas:
    return Canvas(CW, CH)


def sphere(c: Canvas, x: float, y: float, r: float, color, shade: bool = True, edge: str | None = None) -> None:
    """A lit ball. `color(nx, ny)` gives the base colour at a point on the disc
    (nx, ny in -1..1); the night side is shaded in three bands, 8-bit style."""
    lx, ly, lz = LIGHT
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    for py in range(int(y - r) - 1, int(y + r) + 2):
        for px in range(int(x - r) - 1, int(x + r) + 2):
            nx, ny = (px + 0.5 - x) / r, (py + 0.5 - y) / r
            d = nx * nx + ny * ny
            if d > 1:
                continue
            col = color(nx, ny)
            if shade:
                lit = nx * lx + ny * ly + math.sqrt(1 - d) * lz
                band = 0 if lit > 0.35 else 1 if lit > 0.05 else 2 if lit > -0.25 else 3
                col = mix(col, NIGHT, (0, 0.25, 0.5, 0.75)[band])
            if edge and d > (1 - 1.6 / r) ** 2:
                col = mix(col, edge, 0.6 if not shade else 0.4)
            c.set(px, py, col)


def ring(c: Canvas, x: float, y: float, r: float, col: str, step: float = 1.0) -> None:
    """A thin orbit circle (dotted if step > 1)."""
    n = max(12, int(2 * math.pi * r / step))
    for i in range(n):
        a = i / n * math.tau
        c.set(round(x + r * math.cos(a)), round(y + r * math.sin(a)), col)


# -- level 0: the Earth --------------------------------------------------------------

def earth_level() -> Canvas:
    c = _blank()
    ocean, deep, land, land_dk, ice = "#2a62c8", "#1d4a9e", "#49a84a", "#2f7d3a", "#eef6ff"

    def color(nx: float, ny: float) -> str:
        x, y = nx * 9, ny * 9
        h = math.sin(x * 0.9 + 1.3) * math.cos(y * 0.8 - 0.4) + math.sin((x + y) * 0.55 + 2) + \
            0.5 * math.sin(x * 2.1 - y * 1.7)
        if abs(ny) > 0.86:
            return ice
        if h > 0.75:
            return land_dk if h > 1.35 else land
        cloud = math.sin(x * 1.3 + y * 0.4) + math.sin(y * 2.2 - x * 0.3)
        if cloud > 1.55:
            return "#f4f8ff"
        return ocean if h > -0.4 else deep

    sphere(c, CX, CY, 50, color, edge="#8ad0ff")
    for a in range(0, 360, 2):                           # a thin glow of atmosphere
        rad = math.radians(a)
        c.set(round(CX + 51 * math.cos(rad)), round(CY + 51 * math.sin(rad)),
              "#5aa8ff" if 110 < a < 340 else "#1d3a7a")
    return c


# -- level 1: the Moon -----------------------------------------------------------------

MOON = (CX + 50, CY - 22)


def moon_level() -> Canvas:
    c = _blank()
    ring(c, CX, CY, math.hypot(MOON[0] - CX, MOON[1] - CY), "#141c38", step=3)
    craters = [(-0.3, -0.2), (0.35, 0.3), (-0.1, 0.5), (0.4, -0.4)]

    def color(nx: float, ny: float) -> str:
        for cx, cy in craters:
            if (nx - cx) ** 2 + (ny - cy) ** 2 < 0.06:
                return "#8a8a94"
        return "#c8c8cc"

    sphere(c, MOON[0], MOON[1], 5, color)
    return c


# -- level 2: the inner solar system ---------------------------------------------------

SUN = (CX - 58, CY + 16)         # the Earth (the centre) sits on its third orbit
INNER_ORBITS = (22, 38, math.hypot(58, 16), 88)


def _on_orbit(center: tuple[float, float], r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return center[0] + r * math.cos(a), center[1] + r * math.sin(a)


def inner_level() -> Canvas:
    c = _blank()
    for r in INNER_ORBITS:
        ring(c, SUN[0], SUN[1], r, "#1a2448", step=2)
    # the sun, wearing sunglasses
    sphere(c, SUN[0], SUN[1], 9, lambda nx, ny: "#ffd84a" if nx * nx + ny * ny < 0.55 else "#ffb03a",
           shade=False, edge="#ff7a1a")
    for i in range(12):
        a = i / 12 * math.tau
        c.line(round(SUN[0] + 11 * math.cos(a)), round(SUN[1] + 11 * math.sin(a)),
               round(SUN[0] + 13 * math.cos(a)), round(SUN[1] + 13 * math.sin(a)), "#ffb03a")
    sx, sy = round(SUN[0]), round(SUN[1])
    c.rect(sx - 6, sy - 3, 5, 3, INK)
    c.rect(sx + 1, sy - 3, 5, 3, INK)
    c.hline(sx - 7, sx + 6, sy - 3, INK)
    c.set(sx - 5, sy - 3, "#6a7a9a")
    c.set(sx + 2, sy - 3, "#6a7a9a")
    c.hline(sx - 3, sx + 3, sy + 4, "#c85a1a")
    c.set(sx - 4, sy + 3, "#c85a1a")
    c.set(sx + 4, sy + 3, "#c85a1a")
    # mercury, venus, mars
    for r, deg, rad, col in ((22, 300, 2, "#a89a8a"), (38, 70, 3, "#e8c87a"), (88, -28, 3, "#d0583a")):
        x, y = _on_orbit(SUN, r, deg)
        sphere(c, x, y, rad, lambda nx, ny, col=col: col)
    return c


TEAPOT_AT = _on_orbit(SUN, 74, 18)
DILDO_AT = (CX + 84, CY - 48)


# -- level 3: the outer solar system ----------------------------------------------------

SUN3 = (CX + (SUN[0] - CX) / SCALE, CY + (SUN[1] - CY) / SCALE)
JUPITER = _on_orbit(SUN3, 22, 205)
SATURN = _on_orbit(SUN3, 36, 330)
URANUS = _on_orbit(SUN3, 52, 120)
NEPTUNE = _on_orbit(SUN3, 66, 250)
FSM_AT = (CX + 78, CY - 34)


def outer_level() -> Canvas:
    c = _blank()
    for r in (22, 36, 52, 66):
        ring(c, SUN3[0], SUN3[1], r, "#1a2448", step=2)
    # jupiter, banded, with its red spot
    def jup(nx: float, ny: float) -> str:
        if (nx - 0.3) ** 2 + (ny - 0.3) ** 2 * 3 < 0.04:
            return "#c8462a"
        return ("#e8c8a0", "#c89868", "#f0dcc0", "#b07a50")[int((ny + 1) * 3.5) % 4]
    sphere(c, *JUPITER, 6, jup)
    # saturn and its rings (back half, planet, front half)
    sx, sy = SATURN
    def saturn_ring(front: bool) -> None:
        for a in range(0, 360, 3):
            rad = math.radians(a)
            if (math.sin(rad) > 0) != front:
                continue
            for rr, col in ((9, "#d8c890"), (8, "#b8a870"), (10, "#a89860")):
                c.set(round(sx + rr * math.cos(rad)), round(sy + rr * 0.32 * math.sin(rad)), col)
    saturn_ring(False)
    sphere(c, sx, sy, 5, lambda nx, ny: "#e8d090" if int((ny + 1) * 3) % 2 else "#d0b878")
    saturn_ring(True)
    # uranus, which is a butt
    ux, uy = URANUS
    for dx in (-3.0, 3.0):
        sphere(c, ux + dx, uy, 4.2, lambda nx, ny: "#8ae8f0", edge="#4ab0c0")
    c.vline(round(ux), round(uy - 2), round(uy + 2), "#2a7a8a")
    for i, (fx, fy) in enumerate(((ux + 2, uy + 6), (ux + 5, uy + 8), (ux + 1, uy + 9))):   # and it farted
        c.oval(round(fx), round(fy), 3 + i % 2, 3, "#9acd32" if i % 2 else "#7aa82a")
    # neptune
    sphere(c, *NEPTUNE, 4, lambda nx, ny: "#3a6ae8" if ny < 0.3 else "#2a4ab8")
    return c


# -- level 4: the Milky Way (two of them) -------------------------------------------------

BOOBS = ((CX - 28, CY + 10), (CX + 32, CY + 10))     # the solar system sits on the left one's edge
BOOB_R = 30


def milky_way_level(seed: int = 4) -> Canvas:
    c = _blank()
    rng = random.Random(seed)
    for bx, by in BOOBS:
        # a soft, round, starry disc, fuller at the bottom
        for py in range(by - BOOB_R, by + BOOB_R + 1):
            for px in range(bx - BOOB_R, bx + BOOB_R + 1):
                dx, dy = px - bx, py - by
                ang = math.atan2(dy, dx)
                d = math.hypot(dx, dy) / (BOOB_R * (1 + 0.12 * max(0.0, math.sin(ang))))   # a little fuller below
                if d > 1:
                    continue
                arm = math.sin(2 * ang - 5.0 * d)                 # two spiral arms
                dens = (1 - d) * 0.75 + max(0.0, arm) * 0.45 + (0.15 if dy > 0 else 0)
                roll = rng.random()
                if roll < dens * 0.55:
                    col = "#fff0ff" if roll < dens * 0.12 else "#d8b8f0" if arm > 0.3 else "#8a6ab8"
                    c.set(px, py, col)
                elif roll < dens * 0.9:
                    c.set(px, py, "#3a2a5a")
        # underside shadow
        for a in range(15, 165):
            rad = math.radians(a)
            r = BOOB_R * (1 + 0.12 * math.sin(rad))
            c.set(round(bx + r * math.cos(rad)), round(by + r * math.sin(rad)), "#7a5aa0")
        for a in range(200, 250):                               # a shine on the upper left
            rad = math.radians(a)
            c.set(round(bx + 0.7 * BOOB_R * math.cos(rad)), round(by + 0.7 * BOOB_R * math.sin(rad)), "#fff0ff")
        # the core: areola and nipple
        c.oval(bx - 6, by - 4, 12, 11, "#e87aa0")
        c.oval(bx - 4, by - 2, 8, 7, "#ff9abc")
        c.oval(bx - 2, by, 4, 4, "#ff5a8a")
        c.set(bx - 1, by, "#ffd0e0")
    return c


YOU_ARE_HERE = (CX, CY)


# -- level 5: the cosmic web, which is a brain -----------------------------------------------

BRAIN = (CX, CY + 2, 66, 50)      # centre x, y and the half-width / half-height


def brain_level(seed: int = 5) -> Canvas:
    c = _blank()
    rng = random.Random(seed)
    bx, by, rx, ry = BRAIN
    pink, dark, hi = "#e88aa8", "#a84a6a", "#ffc0d4"
    inside = lambda x, y: ((x - bx) / rx) ** 2 + ((y - by) / ry) ** 2 <= 1
    # a sparse dither for the body, so the galaxies behind still show
    for y in range(by - ry, by + ry + 1):
        for x in range(bx - rx, bx + rx + 1):
            if inside(x, y) and (x + 2 * y) % 5 == 0:
                c.set(x, y, "#3a1a2a")
    # folds (gyri): wavy filaments, dotted with galaxies
    for k in range(-5, 6):
        y0 = by + k * 9
        for x in range(bx - rx, bx + rx + 1):
            y = round(y0 + 3.5 * math.sin(x * 0.22 + k * 1.7) + 2 * math.sin(x * 0.07 + k))
            if inside(x, y) and abs(x - bx) > 1:
                c.set(x, y, pink)
                c.set(x, y + 1, dark)
                if rng.random() < 0.12:
                    c.set(x, y, rng.choice(("#ffffff", "#fff2a0", hi)))
    # the outline and the fissure down the middle
    for a in range(0, 720):
        rad = math.radians(a / 2)
        x, y = round(bx + rx * math.cos(rad)), round(by + ry * math.sin(rad))
        c.set(x, y, pink)
        c.set(x - round(math.cos(rad)), y - round(math.sin(rad)), dark)
    for y in range(by - ry, by + ry - 10):
        c.set(round(bx + 1.5 * math.sin(y * 0.3)), y, dark)
    # the cerebellum and brain stem, bottom right
    c.oval(bx + 30, by + 34, 26, 16, dark)
    c.oval(bx + 31, by + 35, 24, 14, "#c86a8a")
    for i in range(4):
        c.hline(bx + 34, bx + 52, by + 38 + i * 3, dark)
    c.rect(bx + 14, by + ry - 6, 10, 18, "#c86a8a")
    c.vline(bx + 14, by + ry - 6, by + ry + 11, dark)
    return c


# -- level 6: it's in a jar ----------------------------------------------------------------

JAR = (CX - 34, CY - 44, 68, 92)          # glass, x y w h: the inside stays see-through
SHELF_Y = CY + 50


def jar_level() -> Canvas:
    c = _blank()
    x0, y0, w, h = JAR
    wall, wall_dk, tile = "#26352f", "#1c2824", "#2f4239"
    inside = lambda x, y: x0 + 1 <= x < x0 + w - 1 and y0 + 6 <= y < y0 + h - 1
    for y in range(CH):
        for x in range(CW):
            if inside(x, y):
                continue
            col = wall
            if x % 24 == 0 or y % 24 == 0:
                col = wall_dk
            elif (x // 24 + y // 24) % 2:
                col = tile
            c.set(x, y, col)
    # the shelf
    c.rect(0, SHELF_Y, CW, 6, "#6a4428")
    c.hline(0, CW - 1, SHELF_Y, "#8a5a38")
    c.rect(0, SHELF_Y + 6, CW, 2, "#3a2414")
    for bx in (30, CW - 40):
        c.rect(bx, SHELF_Y + 8, 4, 14, "#3a3a44")
    # neighbouring jars on the shelf
    for jx, liquid in ((CX - 100, "#3a7a3a"), (CX + 62, "#7a6a2a"), (CX + 104, "#3a5a7a")):
        jw, jh = 26, 34
        c.rect(jx, SHELF_Y - jh, jw, jh, liquid)
        c.rect(jx - 1, SHELF_Y - jh - 4, jw + 2, 4, "#8a8a94")
        c.vline(jx + 3, SHELF_Y - jh + 3, SHELF_Y - 4, mix(liquid, "#ffffff", 0.4))
        c.rect(jx + 6, SHELF_Y - 12, 14, 8, "#e8dcb0")
    # the brain floating in it, solid enough to read at this size (the cosmic web level draws over it)
    bx, by = CX, CY
    brx, bry = BRAIN[2] // SCALE, BRAIN[3] // SCALE
    c.oval(bx - brx, by - bry, brx * 2 + 1, bry * 2 + 1, "#c86a8a")
    c.oval(bx - brx + 1, by - bry + 1, brx * 2 - 1, bry * 2 - 2, "#e88aa8")
    for k in range(-1, 2):
        c.hline(bx - brx + 3, bx + brx - 3, by + k * 4, "#a84a6a")
    c.vline(bx, by - bry + 1, by + bry - 2, "#a84a6a")
    c.rect(bx + 2, by + bry, 2, 4, "#c86a8a")
    # the big jar: glass edges and lid
    c.rect(x0 - 3, y0, w + 6, 6, "#9a9aa4")
    c.hline(x0 - 3, x0 + w + 2, y0, "#d0d0d8")
    c.rect(x0 - 3, y0 + 5, w + 6, 1, "#5a5a64")
    for y in range(y0 + 6, y0 + h):
        c.set(x0, y, "#8ad0c8")
        c.set(x0 + w - 1, y, "#5a9a92")
    c.hline(x0, x0 + w - 1, y0 + h - 1, "#5a9a92")
    return c


def jar_front() -> Canvas:
    """Drawn over everything inside the jar: glare and the label."""
    c = _blank()
    x0, y0, w, h = JAR
    c.vline(x0 + 4, y0 + 10, y0 + h - 8, "#bff0e8")
    c.vline(x0 + 6, y0 + 14, y0 + 30, "#bff0e8")
    c.vline(x0 + w - 6, y0 + 20, y0 + h - 14, "#5a9a92")
    lx, ly = CX - 18, y0 + h - 20
    c.rect(lx, ly, 36, 15, "#e8dcb0")
    c.hline(lx, lx + 35, ly, "#fff4d0")
    c.rect(lx, ly + 14, 36, 1, "#b8a880")
    draw_text_centered(c, CX, ly + 2, "UNIVERSE", "#3a2414")
    draw_text_centered(c, CX, ly + 8, "NO. 7", "#a83a2a")
    return c


# -- props -------------------------------------------------------------------------------------

def cow(frame: int) -> Canvas:
    """A cow mid-jump, legs out. Two frames: legs tucked and stretched."""
    c = Canvas(18, 13)
    w, blk, pink = "#f4f4f0", "#2a2a2a", "#f0a0b0"
    c.rect(3, 4, 10, 5, w)
    c.rect(5, 4, 3, 2, blk)
    c.rect(9, 6, 2, 3, blk)
    c.rect(12, 2, 4, 5, w)                     # head
    c.rect(14, 5, 3, 2, pink)                  # muzzle
    c.set(13, 3, blk)                          # eye
    c.set(12, 1, "#d8c8a0")
    c.set(15, 1, "#d8c8a0")                    # horns
    c.set(2, 4, w)
    c.vline(1, 4, 6, blk)                      # tail
    c.rect(7, 9, 2, 1, pink)                   # udder
    if frame == 0:
        for x0, x1 in ((4, 1), (5, 3), (11, 14), (12, 16)):
            c.line(x0, 9, x1, 11, w)
    else:
        for x0, x1 in ((4, 4), (6, 6), (10, 10), (12, 12)):
            c.line(x0, 9, x1, 10, w)
    c.outline(OUTLINE)
    return c


def teapot() -> Canvas:
    c = Canvas(13, 9)
    body, sh = "#f4f0e8", "#c8c0b0"
    c.oval(2, 2, 8, 6, body)
    c.hline(3, 8, 7, sh)
    c.rect(4, 1, 4, 1, body)
    c.set(5, 0, "#4a7ac8")                     # knob
    c.line(9, 4, 11, 2, body)                  # spout
    c.set(11, 1, body)
    c.vline(1, 3, 5, body)                     # handle
    c.set(0, 4, body)
    c.rect(4, 4, 4, 1, "#4a7ac8")              # a band of blue china
    c.outline(OUTLINE)
    return c
