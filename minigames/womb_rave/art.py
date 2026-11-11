"""Womb Rave art: the gallery with the womb sculpture, the inside of the womb,
and the things that come down the lanes.

Drawn with the same canvas, palette and 1px outline as the main cast. The
inside is laid out like a diagram of a uterus seen from within: the placenta
up top with the umbilical cord hanging down, a fallopian tube (and its ovary)
coming in from each side, and the cervix at the bottom. The dancer floats in
an amniotic sac in the middle, and everything arrives at the membrane around it.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.font import draw_text, text_width
from sprites.palette import INK, LAB_BG, LAB_FLOOR, LAB_GRID, OUTLINE
from sprites.viewer import H, W

from ..stork_bomber.art import poly

F = {   # flesh, darkest to lightest
    "void": "#1a0410", "deep": "#3a0a1e", "dark": "#5c1230", "mid": "#7e1d3e",
    "warm": "#a3304f", "pink": "#c84a64", "light": "#e87a8a", "pale": "#f29aa8", "hi": "#ffc0cc",
    "vein": "#4a0c22", "vein_hi": "#8a2040",
    "cord": "#d8c8e8", "cord_sh": "#a898c0", "artery": "#c83a5a", "vessel": "#5a5ab8",
    "ovary": "#f0b8c0", "ovary_sh": "#c88090", "follicle": "#fff0d8",
}
LANE_COLOR = {"L": "#ffe14d", "R": "#ffe14d", "U": "#9dff5a", "D": "#5ff3ff", "B": "#ff6a9a"}
RAVE = ("#ff6a9a", "#5ff3ff", "#ffe14d", "#b46bff", "#9dff5a")

# -- inside: where everything is ---------------------------------------------------
CX, CY = W // 2, 94              # middle of the sac; the dancer floats here
SAC_RX, SAC_RY = 29, 28          # the amniotic sac
MEM_RX, MEM_RY = 44, 36          # the membrane: every lane ends on it, and the squeeze ring closes onto it
RECEPTOR = {"L": (CX - MEM_RX, CY), "R": (CX + MEM_RX, CY), "U": (CX, CY - MEM_RY), "D": (CX, CY + MEM_RY)}
PLACENTA_Y = 10
OVARY = (26, 58)                 # left one; the right one is mirrored


def _bezier(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def _raw_path(lane: str, s: float) -> tuple[float, float]:
    rx, ry = RECEPTOR[lane]
    if lane in "LR":
        p = _bezier(OVARY, (48, 4), (86, ry), (rx if lane == "L" else W - rx, ry), s)
        return (p[0], p[1]) if lane == "L" else (W - p[0], p[1])
    if lane == "U":                                           # down the umbilical cord, which wiggles
        return CX + 8 * math.sin(s * 7.5) * (1 - s), PLACENTA_Y + (ry - PLACENTA_Y) * s
    return CX, H + 16 - (H + 16 - ry) * s                     # up from the cervix


def _arc_table(lane: str, n: int = 240) -> list[tuple[float, float]]:
    """The lane resampled so equal steps cover equal distance (notes keep a steady speed)."""
    pts = [_raw_path(lane, i / n) for i in range(n + 1)]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    out, j = [], 0
    for i in range(n + 1):
        want = cum[-1] * i / n
        while j < n - 1 and cum[j + 1] < want:
            j += 1
        seg = cum[j + 1] - cum[j] or 1
        k = (want - cum[j]) / seg
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * k, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * k))
    return out


_PATHS = {lane: _arc_table(lane) for lane in "LRUD"}


def lane_pos(lane: str, u: float) -> tuple[float, float]:
    """Point along a lane: u=0 where things appear, u=1 at the membrane. Past 1 it
    carries on in a straight line toward the dancer."""
    pts = _PATHS[lane]
    n = len(pts) - 1
    if u <= 1:
        f = max(0.0, u) * n
        i = min(n - 1, int(f))
        k = f - i
        return pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k
    rx, ry = RECEPTOR[lane]
    return rx + (CX - rx) * (u - 1), ry + (CY - ry) * (u - 1)


# -- inside: the static layer over the pulsing tunnel ------------------------------

def _tube(c: Canvas, pts: list[tuple[float, float]], w: int, fill: str, edge: str, hi: str | None) -> None:
    for pw, col in ((w + 2, edge), (w, fill)):
        for x, y in pts:
            c.oval(round(x - pw / 2), round(y - pw / 2), pw, pw, col)
    if hi:
        for x, y in pts:
            c.set(round(x - w / 4), round(y - w / 4), hi)


def _veins(c: Canvas, rng: random.Random) -> None:
    """Branching veins creeping in from the edges of the screen."""
    def grow(x: float, y: float, ang: float, life: int, width: int) -> None:
        for step in range(life):
            ex, ey = (x - CX) / 150, (y - CY) / 90
            if ex * ex + ey * ey < 0.45:                       # keep the middle clear
                return
            nx, ny = x + math.cos(ang) * 2, y + math.sin(ang) * 2
            c.stroke(round(x), round(y), round(nx), round(ny), F["vein"], width)
            if width == 1 and step % 3 == 0:
                c.set(round(x), round(y) - 1, F["vein_hi"])
            x, y = nx, ny
            ang += rng.uniform(-0.35, 0.35)
            if rng.random() < 0.08 and life - step > 6:
                grow(x, y, ang + rng.choice((-0.9, 0.9)), (life - step) // 2, 1)
    for _ in range(14):
        side = rng.randrange(4)
        if side == 0:
            x, y, ang = rng.uniform(0, W), H + 2, -math.pi / 2
        elif side == 1:
            x, y, ang = -2, rng.uniform(0, H), 0.0
        elif side == 2:
            x, y, ang = W + 2, rng.uniform(0, H), math.pi
        else:
            x, y, ang = rng.uniform(0, W), -2, math.pi / 2
        ang += math.atan2(CY - y, CX - x) * 0 + rng.uniform(-0.5, 0.5)
        grow(x, y, ang, rng.randrange(18, 34), 2)


def interior_overlay() -> Canvas:
    rng = random.Random(4)
    c = Canvas(W, H)
    _veins(c, rng)

    # cervix: a muscular ring at the bottom, with the way out in the middle
    c.oval(CX - 46, H - 22, 92, 34, F["dark"])
    c.oval(CX - 38, H - 18, 76, 26, F["warm"])
    c.oval(CX - 28, H - 14, 56, 20, F["pink"])
    for i in range(10):                                       # folds radiating out of the hole
        a = math.pi + i * math.pi / 9
        c.line(CX + round(math.cos(a) * 12), H - 3 + round(math.sin(a) * 4),
               CX + round(math.cos(a) * 34), H - 3 + round(math.sin(a) * 12), F["warm"])
    c.oval(CX - 14, H - 9, 28, 12, F["deep"])
    c.oval(CX - 10, H - 7, 20, 9, F["void"])

    # fallopian tubes and ovaries
    for lane in "LR":
        pts = [lane_pos(lane, i / 120) for i in range(0, 104)]
        _tube(c, pts, 7, F["light"], F["dark"], F["hi"])
        for i in range(8, 100, 9):                            # ribbing
            x, y = pts[i]
            c.set(round(x), round(y) + 2, F["pink"])
        ox, oy = OVARY if lane == "L" else (W - OVARY[0], OVARY[1])
        c.oval(round(ox) - 11, round(oy) - 8, 22, 16, F["ovary_sh"])
        c.oval(round(ox) - 10, round(oy) - 8, 20, 14, F["ovary"])
        for dx, dy in ((-5, -3), (3, -4), (-2, 2), (5, 1), (0, -1)):
            c.oval(round(ox) + dx - 1, round(oy) + dy - 1, 3, 3, F["follicle"])
        for k in range(5):                                    # the frilly fimbriae reaching for the ovary
            a = -2.2 + k * 0.45
            fx, fy = pts[3]
            c.stroke(round(fx), round(fy), round(fx + math.cos(a) * 7), round(fy + math.sin(a) * 7), F["pale"], 2)

    # umbilical cord hanging from the placenta
    pts = [lane_pos("U", i / 120) for i in range(0, 121)]
    _tube(c, pts, 5, F["cord"], F["cord_sh"], None)
    for i, (x, y) in enumerate(pts[::3]):                     # vessels spiralling around it
        c.set(round(x) + (1 if i % 2 else -1), round(y), F["artery"] if i % 4 < 2 else F["vessel"])

    # placenta: a spongy lump on the ceiling
    for dx, w, h in ((-46, 34, 18), (-24, 40, 24), (0, 48, 28), (22, 40, 22), (44, 32, 16)):
        c.oval(CX + dx - w // 2, -12, w, h + 6, F["dark"])
    for dx, w, h in ((-40, 22, 12), (-20, 26, 16), (2, 30, 20), (24, 24, 14), (42, 18, 10)):
        c.oval(CX + dx - w // 2, -10, w, h + 4, F["mid"])
    for i in range(16):
        x = CX + rng.randrange(-56, 56)
        c.oval(x, rng.randrange(-2, 8), 3, 2, F["warm"])
    for k in range(-3, 4):                                    # vessels fanning out from the cord
        c.line(CX, PLACENTA_Y + 2, CX + k * 13, rng.randrange(0, 6), F["artery"] if k % 2 else F["vessel"])
    c.outline(OUTLINE)
    return c


# -- the things that come down the lanes --------------------------------------------

def _eyes(c: Canvas, x: int, y: int, gap: int = 3) -> None:
    c.set(x, y, INK)
    c.set(x + gap, y, INK)


def egg(frame: int) -> Canvas:
    """An ovum rolling down a fallopian tube. Smug."""
    c = Canvas(13, 13)
    for i in range(12):                                       # corona radiata
        a = i * math.tau / 12 + frame * 0.5
        c.set(6 + round(math.cos(a) * 5.4), 6 + round(math.sin(a) * 5.4), "#fff0b0")
    c.oval(2, 2, 9, 9, "#ffe14d")
    c.oval(3, 3, 7, 6, "#fff5a8")
    hx, hy = [(4, 4), (7, 4), (8, 7), (4, 7)][frame % 4]
    c.set(hx, hy, "#ffffff")
    _eyes(c, 5, 6)
    c.set(6, 8, "#d8a020")
    c.outline(OUTLINE)
    return c


def sperm(frame: int) -> Canvas:
    """Swimming up from the cervix, head first, tail lashing."""
    c = Canvas(11, 20)
    for row in range(9):
        x = 5 + round(1.6 * math.sin(row * 0.8 + frame * 2.1) * row / 8)
        c.set(x, 8 + row, "#e8e8f8" if row < 6 else "#b8b8d8")
    c.oval(2, 0, 7, 9, "#f4f4f4")
    c.oval(3, 5, 5, 3, "#c8c8e0")
    _eyes(c, 3, 3, 4)
    c.hline(4, 6, 6, INK)                                     # grimly determined
    c.outline(OUTLINE)
    return c


SNACKS = ("pickle", "ice cream", "pizza", "donut")


def snack(kind: int) -> Canvas:
    """Mom's cravings, coming down the cord."""
    c = Canvas(11, 11)
    if kind == 0:                                             # pickle
        c.oval(2, 0, 7, 11, "#5a9a2a")
        c.oval(3, 1, 4, 9, "#7ac83a")
        for x, y in ((4, 2), (6, 4), (4, 6), (6, 8)):
            c.set(x, y, "#3a6a1a")
    elif kind == 1:                                           # ice cream cone
        poly(c, [(2, 4), (8, 4), (5, 10)], "#d8a060")
        for y in (6, 8):
            c.hline(4, 6, y, "#a87040")
        c.oval(1, 0, 9, 6, "#ff9ac8")
        c.set(4, 1, "#ffe0f0")
        c.set(6, 2, "#e83b3b")
    elif kind == 2:                                           # pizza slice
        poly(c, [(1, 1), (9, 1), (5, 10)], "#ffd060")
        c.hline(1, 9, 1, "#c88030")
        c.hline(1, 9, 0, "#a86020")
        for x, y in ((4, 3), (6, 5), (5, 7)):
            c.set(x, y, "#c83a3a")
            c.set(x + 1, y, "#c83a3a")
    else:                                                     # donut
        c.oval(0, 1, 11, 9, "#d8a060")
        c.oval(1, 1, 9, 7, "#ff8ab8")
        c.oval(4, 4, 3, 3, None)
        for x, y, col in ((2, 3, "#5ff3ff"), (7, 2, "#ffe14d"), (8, 5, "#9dff5a"), (3, 6, "#ffffff")):
            c.set(x, y, col)
    c.outline(OUTLINE)
    return c


_ARROW = ["....#....", "...###...", "..#####..", ".#######.", "#########", "...###...", "...###...",
          "...###...", "...###..."]


def _rot(rows: list[str]) -> list[str]:
    """Rotate ASCII art 90 degrees clockwise."""
    return ["".join(rows[len(rows) - 1 - j][i] for j in range(len(rows))) for i in range(len(rows[0]))]


ARROWS = {"U": _ARROW}
ARROWS["R"] = _rot(ARROWS["U"])
ARROWS["D"] = _rot(ARROWS["R"])
ARROWS["L"] = _rot(ARROWS["D"])


def receptor(lane: str, state: str) -> Canvas:
    """The arrow socket on the membrane. state: idle | held | flash"""
    rows = ARROWS[lane]
    col = LANE_COLOR[lane]
    c = Canvas(11, 11)
    filled = {(x, y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == "#"}
    for x, y in filled:
        edge = any((x + dx, y + dy) not in filled for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if state == "flash":
            c.set(x + 1, y + 1, "#ffffff")
        elif state == "held":
            c.set(x + 1, y + 1, col if edge else mix(col, "#ffffff", 0.4))
        else:
            c.set(x + 1, y + 1, col if edge else mix(col, F["deep"], 0.75))
    c.outline(OUTLINE)
    return c


def burst(frame: int, col: str) -> Canvas:
    """A splash of sparkles where a note got hit."""
    c = Canvas(21, 21)
    r = 3 + frame * 2.5
    for i in range(8):
        a = i * math.tau / 8 + frame * 0.2
        x, y = 10 + round(math.cos(a) * r), 10 + round(math.sin(a) * r)
        c.set(x, y, "#ffffff" if frame < 2 else col)
        if frame < 3:
            c.set(x + 1, y, col)
    return c


# -- outside: the gallery and the sculpture --------------------------------------------
FLOOR_Y = 150
DOOR_X = 196                     # the sculpture's middle, and the door at its foot
DOOR_TOP = 124
DOOR_FRAMES = 6                  # closed .. wide open


def _sculpture(c: Canvas) -> None:
    sx = DOOR_X
    # fallopian tubes curling out like ram's horns, ovaries hanging below
    for side in (-1, 1):
        pts = [(sx + side * (44 + 44 * t), 52 - 26 * math.sin(t * math.pi * 0.9) + 18 * t * t)
               for t in (i / 50 for i in range(51))]
        _tube(c, pts, 7, F["light"], F["warm"], F["hi"])
        ex, ey = pts[-1]
        for k in range(6):                                    # fimbriae
            a = math.pi / 2 + side * (-0.4 + k * 0.32)
            c.stroke(round(ex), round(ey), round(ex + math.cos(a) * 7), round(ey + math.sin(a) * 8), F["pale"], 2)
        ox = sx + side * 66
        c.line(round(ox), 74, sx + side * 30, 70, F["warm"])  # ligament
        c.oval(round(ox) - 10, 68, 20, 14, F["ovary_sh"])
        c.oval(round(ox) - 9, 68, 18, 12, F["ovary"])
        for dx, dy in ((-4, 3), (2, 2), (5, 6), (-1, 7)):
            c.oval(round(ox) + dx - 1, 68 + dy, 3, 3, F["follicle"])
    # the body: an upside-down pear standing on its cervix
    body = [(sx - 48, 50), (sx - 28, 42), (sx, 47), (sx + 28, 42), (sx + 48, 50), (sx + 50, 64),
            (sx + 42, 86), (sx + 28, 104), (sx + 17, 118), (sx + 15, FLOOR_Y), (sx - 15, FLOOR_Y),
            (sx - 17, 118), (sx - 28, 104), (sx - 42, 86), (sx - 50, 64)]
    poly(c, body, F["light"])
    poly(c, [(sx + 30, 44), (sx + 48, 50), (sx + 50, 64), (sx + 42, 86), (sx + 28, 104), (sx + 17, 118),
             (sx + 15, FLOOR_Y), (sx + 10, FLOOR_Y), (sx + 11, 118), (sx + 22, 103), (sx + 35, 85),
             (sx + 42, 64)], F["pink"])                                     # shade down the right side
    poly(c, [(sx - 30, 56), (sx - 12, 52), (sx, 55), (sx + 12, 52), (sx + 30, 56), (sx + 12, 84),
             (sx + 4, 100), (sx - 4, 100), (sx - 12, 84)], F["warm"])          # the cavity, in relief
    poly(c, [(sx - 22, 59), (sx, 58), (sx + 22, 59), (sx + 4, 92), (sx - 4, 92)], F["pink"])
    for x, y in ((sx - 40, 58), (sx - 36, 72), (sx - 30, 88)):
        c.hline(x, x + 3, y, F["hi"])
    c.vline(sx, 100, DOOR_TOP - 2, F["warm"])


def door(open_: float) -> Canvas:
    """The way in: layered folds around a slit that dilates as you walk up."""
    c = Canvas(30, FLOOR_Y - DOOR_TOP + 2)
    h = c.h - 2
    for w, col in ((24, F["pale"]), (18, F["light"]), (12 + 8 * open_, F["warm"])):
        w = round(w)
        c.oval(15 - w // 2, 0, w, h + 4, col)
    slit = round(2 + 12 * open_)
    c.oval(15 - slit // 2, 3, slit, h, F["void"] if open_ > 0.3 else F["deep"])
    if open_ > 0.5:                                           # club lights glowing deep inside
        c.oval(15 - slit // 4, 8, max(2, slit // 2), h - 10, mix(F["void"], "#b46bff", 0.35))
    c.set(15, 0, F["hi"])
    c.outline(OUTLINE)
    return c


def gallery() -> Canvas:
    """The room: a dark gallery wall, spotlights, the sculpture and its plaque."""
    c = Canvas(W, H)
    c.rect(0, 0, W, FLOOR_Y, LAB_BG)
    for y in range(0, FLOOR_Y, 6):                            # faint wall paneling
        c.hline(0, W, y, mix(LAB_BG, LAB_GRID, 0.25))
    for x in range(0, W, 40):
        c.vline(x, 0, FLOOR_Y - 1, mix(LAB_BG, LAB_GRID, 0.4))
    for y in range(26, FLOOR_Y):                              # spotlight cone on the sculpture
        half = 18 + (y - 26) * 0.75
        for x in range(round(DOOR_X - half), round(DOOR_X + half)):
            if c.inside(x, y):
                c.set(x, y, mix(c.get(x, y) or LAB_BG, "#ffd0e0", 0.10))
    c.rect(DOOR_X - 8, 0, 16, 4, LAB_GRID)                    # the lamp
    c.rect(DOOR_X - 4, 4, 8, 3, "#f0eccc")
    c.rect(0, FLOOR_Y, W, H - FLOOR_Y, LAB_FLOOR)
    for gx in range(-16, W + 16, 16):
        c.line(gx, FLOOR_Y, gx - 12, H, LAB_GRID)
    c.hline(0, W, FLOOR_Y, LAB_GRID)
    c.oval(DOOR_X - 60, FLOOR_Y - 2, 120, 8, mix(LAB_FLOOR, "#ffd0e0", 0.12))   # pool of light
    plinth = Canvas(W, H)
    _sculpture(plinth)
    plinth.outline(OUTLINE)
    c.paste(plinth)

    # the plaque
    px, py = 262, 104
    c.rect(px, py, 50, 22, "#e8e4d0")
    c.hline(px, px + 49, py + 21, "#a8a490")
    for i, line in enumerate(("UNTITLED", "'HOME'", "MIXED MEDIA")):
        draw_text(c, px + 25 - text_width(line) // 2, py + 2 + i * 6, line, INK)
    c.vline(px + 25, py + 22, FLOOR_Y - 1, LAB_GRID)
    # velvet rope and stanchions, on the far side from where you walk in
    for x in (252, 300):
        c.rect(x, FLOOR_Y - 18, 2, 18, "#d8b040")
        c.rect(x - 2, FLOOR_Y - 2, 6, 2, "#d8b040")
        c.oval(x - 1, FLOOR_Y - 21, 4, 4, "#ffe070")
    for x in range(254, 300):
        c.set(x, FLOOR_Y - 17 + round(4 * math.sin((x - 254) / 46 * math.pi)), "#a82434")
    return c


def neon(on: bool) -> Canvas:
    """The flickering WOMB RAVE sign over the sculpture."""
    text = "WOMB RAVE"
    c = Canvas(text_width(text) + 4, 9)
    draw_text(c, 2, 2, text, "#ff6a9a" if on else "#6a2a44")
    if on:
        c.outline("#7a2a5a")
    c.outline("#3a1a3a" if on else LAB_GRID)
    return c


def heart_icon() -> Canvas:
    c = Canvas(9, 8)
    c.stamp(1, 1, [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."], {"#": "#ff4a6a"})
    c.set(2, 2, "#ffc0cc")
    c.outline(OUTLINE)
    return c


def lane_guide() -> Canvas:
    """A faint dotted line up the birth canal, so you can see where the sperm swim."""
    c = Canvas(W, H)
    for lane in "D":
        for i in range(0, 100, 4):
            x, y = lane_pos(lane, i / 100)
            c.set(round(x), round(y), mix(LANE_COLOR[lane], F["deep"], 0.55))
    return c

