"""Art for the cosmic zoom-out at the start of the program.

The zoom is a stack of nested levels, Powers-of-Ten style: each one is drawn
SCALE times bigger than the one inside it, and they're all centred on the same
point (the Earth). Every level is a CW x CH canvas whose centre (CX, CY) is
that point, and whose middle CW/SCALE pixels are left empty for the level
inside it. The game draws the levels on top of each other at the right sizes.

Levels, from the inside out (the scales are a joke, not astronomy):
    0  the Earth, where everyone is at it (the game pops hearts on it)
    1  the solar system: a sun in sunglasses, and Uranus, which is a butt
    2  the Milky Way, which is a pair of boobs
    3  the big bang: two cosmic giants in bed, going at it

Animated props (the stork, the giants, BANG!) are separate sprites the game
puts on top of their level, so they can move.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
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



# -- level 1: the solar system -----------------------------------------------------------

SUN = (CX - 40, CY + 4)          # the Earth (the centre) sits on its third orbit


def _on_orbit(center: tuple[float, float], r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return center[0] + r * math.cos(a), center[1] + r * math.sin(a)


EARTH_ORBIT = math.hypot(CX - SUN[0], CY - SUN[1])
PLANETS = {                      # name: (orbit radius, degrees round it)
    "mercury": (14, 300), "venus": (26, 70), "mars": (54, 100), "jupiter": (72, 150),
    "saturn": (92, 215), "uranus": (112, -20), "neptune": (130, 25),
}
AT = {name: _on_orbit(SUN, r, deg) for name, (r, deg) in PLANETS.items()}
URANUS = AT["uranus"]
CHEEK_R, CHEEK_DX = 8, 6.2       # Uranus's cheeks


def solar_level() -> Canvas:
    c = _blank()
    for r in [r for r, _ in PLANETS.values()] + [EARTH_ORBIT]:
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
    # the rocky ones
    for name, rad, col in (("mercury", 2, "#a89a8a"), ("venus", 3, "#e8c87a"), ("mars", 3, "#d0583a")):
        sphere(c, *AT[name], rad, lambda nx, ny, col=col: col)
    # jupiter, banded, with its red spot
    def jup(nx: float, ny: float) -> str:
        if (nx - 0.3) ** 2 + (ny - 0.3) ** 2 * 3 < 0.04:
            return "#c8462a"
        return ("#e8c8a0", "#c89868", "#f0dcc0", "#b07a50")[int((ny + 1) * 3.5) % 4]
    sphere(c, *AT["jupiter"], 7, jup)
    # saturn and its rings (back half, planet, front half)
    sx, sy = AT["saturn"]
    def saturn_ring(front: bool) -> None:
        for a in range(0, 360, 3):
            rad = math.radians(a)
            if (math.sin(rad) > 0) != front:
                continue
            for rr, col in ((10, "#d8c890"), (9, "#b8a870"), (11, "#a89860")):
                c.set(round(sx + rr * math.cos(rad)), round(sy + rr * 0.32 * math.sin(rad)), col)
    saturn_ring(False)
    sphere(c, sx, sy, 5, lambda nx, ny: "#e8d090" if int((ny + 1) * 3) % 2 else "#d0b878")
    saturn_ring(True)
    # uranus, which is a butt (and it farted)
    ux, uy = URANUS
    for dx in (-CHEEK_DX, CHEEK_DX):
        sphere(c, ux + dx, uy, CHEEK_R, lambda nx, ny: "#8ae8f0", edge="#4ab0c0")
    c.vline(round(ux), round(uy - 4), round(uy + 6), "#2a7a8a")
    for side in (-1, 1):                                  # a shine on each cheek
        c.set(round(ux + side * CHEEK_DX - 2), round(uy - 3), "#e8ffff")
    for i, (fx, fy) in enumerate(((ux + 3, uy + 9), (ux + 7, uy + 11), (ux + 2, uy + 13), (ux + 10, uy + 15))):
        c.oval(round(fx), round(fy), 3 + i % 2, 3, "#9acd32" if i % 2 else "#7aa82a")
    # neptune
    sphere(c, *AT["neptune"], 4, lambda nx, ny: "#3a6ae8" if ny < 0.3 else "#2a4ab8")
    return c


# -- level 2: the Milky Way (two of them) -------------------------------------------------

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



# -- level 3: the big bang ---------------------------------------------------------------------

def big_bang_level(seed: int = 9) -> Canvas:
    """A hot pink flash, and a nebula blowing out from it, behind the giants' bed
    (the giants are a prop, so they can move)."""
    c = _blank()
    rng = random.Random(seed)
    c.rect(0, 0, CW, CH, NIGHT)
    rings = ("#ffffff", "#fff0a8", "#ffb0d8", "#ff6aa8", "#c83a8a", "#6a2a7a", "#2a1640")
    for y in range(CH):
        for x in range(CW):
            dx, dy = (x - CX) / 1.0, (y - CY) / 0.62
            d = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            wob = 1 + 0.22 * math.sin(a * 7 + 1.3) + 0.12 * math.sin(a * 13)
            k = d / (150 * wob)                          # 0 in the middle, 1 at the edge of the cloud
            if k >= 1:
                continue
            band = min(len(rings) - 1, int(k ** 0.55 * len(rings)))
            # thinner the further out: dither, so the stars show through
            if k > 0.25 and rng.random() > (1 - k) ** 1.3:
                continue
            c.set(x, y, rings[band])
    # spikes of the flash
    for i in range(16):
        a = i * math.tau / 16 + rng.uniform(-0.08, 0.08)
        r = rng.uniform(26, 52) if i % 2 else rng.uniform(14, 24)
        for t in range(int(r)):
            col = "#ffffff" if t < r * 0.5 else "#fff0a8" if t < r * 0.8 else "#ffb0d8"
            c.set(round(CX + math.cos(a) * t), round(CY + math.sin(a) * t * 0.7), col)
    c.oval(CX - 10, CY - 7, 21, 15, "#fff0a8")
    c.oval(CX - 7, CY - 5, 15, 11, "#ffffff")
    for _ in range(40):                                  # sparkles
        x, y = rng.randrange(CW), rng.randrange(CH)
        c.set(x, y, rng.choice(("#ffffff", "#fff0a8", "#ffb0d8")))
    return c




GIANTS_W, GIANTS_H, GIANTS_FRAMES = 128, 64, 4
BOUNCE = (0, 2, 4, 2)            # px the covers rise, per frame
KNOCK = (0, 1, 2, 1)             # px the headboard bangs back, per frame


def giants(frame: int) -> Canvas:
    """Two cosmic giants in a bed in space, under a starry quilt, going at it.
    Their heads are on the pillow at the left, their feet stick out at the right."""
    c = Canvas(GIANTS_W, GIANTS_H)
    b, k = BOUNCE[frame % 4], KNOCK[frame % 4]
    wood, wood_hi, wood_dk = "#8a5a34", "#b07a48", "#5a3820"
    # headboard, banging on the wall of the universe
    hx = 3 - k
    c.oval(hx, 6, 9, 9, wood)
    c.rect(hx, 10, 9, 46, wood)
    c.vline(hx + 2, 9, 54, wood_hi)
    c.vline(hx + 7, 10, 55, wood_dk)
    # mattress and frame
    c.rect(10, 42, 114, 10, "#eceaf6")
    c.hline(10, 123, 51, "#b8b4d0")
    c.rect(8, 52, 118, 5, wood)
    c.hline(8, 125, 52, wood_hi)
    for lx in (12, 116):
        c.rect(lx, 57, 4, 6, wood_dk)
    # pillow
    c.oval(11, 31, 28, 13, "#ffffff")
    c.hline(14, 35, 42, "#c8c8dc")
    # giant 1: blue, starry hair, eyes squeezed shut
    hb = b // 2
    blue, blue_sh = "#5a8ae8", "#3a5ab8"
    c.oval(12, 18 - hb, 15, 15, blue)
    c.oval(11, 15 - hb, 17, 8, "#1a1a4a")                  # hair
    for x, y in ((14, 17), (19, 16), (24, 18), (16, 19)):
        c.set(x, y - hb, "#ffffff")
    c.hline(15, 17, 25 - hb, INK)                          # ^ ^
    c.set(16, 24 - hb, INK)
    c.hline(21, 23, 25 - hb, INK)
    c.set(22, 24 - hb, INK)
    c.set(14, 27 - hb, "#ff8ab0")
    c.set(25, 27 - hb, "#ff8ab0")
    c.hline(18, 21, 29 - hb, blue_sh)                      # a grin
    c.set(17, 28 - hb, blue_sh)
    c.set(22, 28 - hb, blue_sh)
    # giant 2: pink, golden hair over the pillow, eyes wide, mouth open
    pink, pink_sh = "#e07ac0", "#a84a90"
    c.oval(24, 25, 22, 8, "#ffd84a")                       # hair, spread out
    c.oval(26, 20 + hb, 15, 15, pink)
    c.oval(26, 18 + hb, 15, 6, "#ffd84a")
    for ex in (30, 36):
        c.rect(ex, 24 + hb, 3, 3, "#ffffff")
        c.set(ex + 1, 25 + hb, INK)
    c.oval(32, 29 + hb, 3, 4, "#6a1a4a")                   # O
    c.set(28, 28 + hb, "#ff5a8a")
    c.set(39, 28 + hb, "#ff5a8a")
    # the quilt, humping up over the middle
    quilt, quilt_hi, quilt_sh = "#6a3aa8", "#9a6ad8", "#4a2a80"
    for x in range(32, 118):
        hip = math.exp(-((x - 64) / 15) ** 2)
        top = round(41 - 7 - 9 * hip - b * hip + 3 * max(0, (x - 100) / 18))
        for y in range(top, 53):
            col = quilt
            if y == top:
                col = quilt_hi
            elif (x * 3 + y * 5) % 23 == 0:
                col = "#ffe8ff"                            # little stars on it
            elif y > 49 or (x - 64) % 17 == 0 and y > top + 2:
                col = quilt_sh
            c.set(x, y, col)
    # feet out the end: pink soles up, blue toes down
    c.oval(114, 26 - b // 2, 6, 9, pink)
    c.oval(119, 27 - b // 2, 6, 9, pink)
    c.oval(116, 41, 9, 6, blue)
    c.oval(120, 43, 8, 6, blue)
    toes = frame % 2
    for x in (115, 117, 120, 122):
        c.set(x, 26 - b // 2 - toes, pink_sh)               # curling toes
    for y in (42, 44, 46):
        c.set(127 - toes, y, blue_sh)
    c.outline(OUTLINE)
    return c
