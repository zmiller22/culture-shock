"""Stork Bomber art: the stork, the baby bundle, the target, and the night sky.

Drawn with the same canvas, palette and 1px outline as the main cast, so the
mini-game drops into the main game without looking out of place.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.rig import elbow
from sprites.palette import BANANA, INK, LAB_BG, LAB_FLOOR, LAB_GRID, MUTANT, OUTLINE, TECH_BRO

P = {
    "white": "#f4f4f4", "white_sh": "#c8c8d8", "white_dk": "#8a8aa8",
    "tip": "#2a2a3a", "tip_back": "#4a4a5a",
    "beak": "#ff9a3a", "beak_sh": "#d0602a", "leg": "#e8703a",
    "cloth": "#9cc4f0", "cloth_sh": "#6a90c4", "cloth_hi": "#d0e6ff",
    "skin": TECH_BRO["skin"], "skin_sh": TECH_BRO["skin_sh"], "cheek": "#ff8a9a", "tear": "#5ff3ff",
    "flesh": MUTANT["flesh"], "flesh_hi": MUTANT["flesh_hi"], "flesh_sh": MUTANT["flesh_sh"],
    "lip": "#e0607a", "lip_hi": "#ff9ab0", "slit": MUTANT["flesh_dk"], "hole": MUTANT["mouth"],
    "hair": TECH_BRO["hair"], "hair_hi": TECH_BRO["hair_hi"],
    "shoe": BANANA["shoe"], "shoe_hi": BANANA["shoe_hi"], "sole": "#ffffff",
    "heart": "#ff6a9a", "heart_hi": "#ffc0d8",
    "moon": "#f0eccc", "moon_sh": "#c8c0a0", "star": "#f4f4f4",
    "cloud": "#3a2f66", "cloud_hi": "#4e4288",
    "city": "#140f26", "window": "#d8c070",
}

STORK_W, STORK_H = 58, 44
STORK_CENTER = (29, 22)          # where the game's (x, y) sits inside the frame
BUNDLE_AT = (49, 25)             # bundle center inside a right-facing frame
BABY_SIZE = 18
TARGET_W, TARGET_H = 58, 46     # room around the body for the arms to reach out
TARGET_PAD = 6                   # rows above the body, for hands thrown up high
TARGET_FEET = 38 + TARGET_PAD    # sole row: sits on the floor
TARGET_HOLE = 18 + TARGET_PAD    # row of the middle of the opening
TARGET_GRAB = 2 + TARGET_PAD     # row where the arms grab a falling baby (its center)
GRAB_REACH = 16                  # px either side of center the hands can reach


# -- helpers -------------------------------------------------------------------

def poly(c: Canvas, pts: list[tuple[float, float]], col: str) -> None:
    """Filled polygon (scanline), with its edges stroked so thin slivers survive."""
    ys = [p[1] for p in pts]
    for y in range(math.floor(min(ys)), math.ceil(max(ys)) + 1):
        yc = y + 0.5
        xs = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for xa, xb in zip(xs[::2], xs[1::2]):
            c.hline(round(xa), round(xb) - 1, y, col)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        c.line(round(x0), round(y0), round(x1), round(y1), col)


def lerp(a: tuple[float, float], b: tuple[float, float], t: float) -> tuple[float, float]:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def shade_rows(c: Canvas, y0: int, y1: int, src: str, dst: str) -> None:
    """Recolor src pixels to dst on rows y0..y1 (cheap bottom shading)."""
    for y in range(y0, y1 + 1):
        for x in range(c.w):
            if c.get(x, y) == src:
                c.set(x, y, dst)


def layered(w: int, h: int, layers) -> Canvas:
    """Draw each layer on its own canvas, outline it, and stack back to front
    (the same trick the rig uses, so overlapping parts stay readable)."""
    out = Canvas(w, h)
    for draw in layers:
        layer = Canvas(w, h)
        draw(layer)
        layer.outline(OUTLINE)
        out.paste(layer)
    return out


def almond(c: Canvas, cx: int, y0: int, h: int, hw: float, col: str) -> dict[int, tuple[int, int]]:
    """A vertical almond (pointed top and bottom). Returns {y: (x0, x1)}."""
    spans = {}
    for i in range(h):
        w = max(0.5, hw * math.sin(math.pi * (i + 0.5) / h) ** 0.75)
        x0, x1 = round(cx - w), round(cx + w) - 1
        if x1 < x0:
            x1 = x0
        c.hline(x0, x1, y0 + i, col)
        spans[y0 + i] = (x0, x1)
    return spans


# -- the stork -----------------------------------------------------------------

# Front wing outline per flap frame, as (back shoulder, front shoulder, leading
# edge, tip, trailing edge). Frame order: up, sweeping down, down, level.
WINGS = [
    [(19, 21), (30, 21), (29, 9), (24, 0), (16, 8)],
    [(19, 21), (31, 21), (23, 12), (7, 8), (11, 17)],
    [(21, 21), (30, 21), (27, 30), (20, 39), (17, 30)],
    [(20, 23), (31, 21), (18, 18), (3, 20), (12, 25)],
]
BUNDLE_SWING = [0, 1, 0, -1]     # the bundle lags behind the flap
PRIMARIES = 0.62                 # the outer part of the wing is black, like a real stork's


def _wing(c: Canvas, frame: int, dx: int, dy: int, base: str, tip: str) -> None:
    pts = [(x + dx, y + dy) for x, y in WINGS[frame]]
    poly(c, pts, base)
    (bx, by), (fx, fy), _, (tx, ty), _ = pts
    rx, ry = (bx + fx) / 2, (by + fy) / 2                # project onto shoulder -> tip
    ax, ay = tx - rx, ty - ry
    n = ax * ax + ay * ay
    for y in range(c.h):
        for x in range(c.w):
            if c.get(x, y) == base and ((x - rx) * ax + (y - ry) * ay) / n > PRIMARIES:
                c.set(x, y, tip)


def stork(frame: int, carrying: bool) -> Canvas:
    """Right-facing stork, STORK_W x STORK_H. frame 0..3 is the flap cycle."""

    def back_wing(c: Canvas) -> None:
        _wing(c, frame, 4, -2, P["white_sh"], P["tip_back"])

    def legs(c: Canvas) -> None:
        c.line(16, 26, 4, 30, P["leg"])
        c.line(17, 27, 5, 32, P["leg"])
        c.set(3, 31, P["leg"])
        c.set(4, 33, P["leg"])

    def body(c: Canvas) -> None:
        poly(c, [(6, 20), (16, 19), (16, 25), (8, 24)], P["white"])     # tail
        c.oval(14, 18, 22, 11, P["white"])
        c.stroke(33, 22, 38, 13, P["white"], 3)                         # neck
        c.oval(35, 8, 8, 7, P["white"])                                 # head
        shade_rows(c, 25, 29, P["white"], P["white_sh"])
        c.hline(7, 9, 23, P["white_dk"])                                # tail feathers
        c.set(40, 10, INK)                                              # eye
        c.set(39, 9, P["white_dk"])                                     # brow
        poly(c, [(42, 10), (53, 13), (53, 14), (42, 13)], P["beak"])
        c.line(42, 13, 53, 14, P["beak_sh"])

    def bundle(c: Canvas) -> None:
        s = BUNDLE_SWING[frame]
        c.line(50, 14, 47 + s, 21, P["cloth"])                          # sling
        c.line(51, 14, 53 + s, 21, P["cloth"])
        c.rect(50, 13, 2, 2, P["cloth_hi"])                             # knot in the beak
        bx, by = BUNDLE_AT[0] + s, BUNDLE_AT[1]
        c.oval(bx - 5, by - 5, 11, 10, P["cloth"])
        shade_rows(c, by + 2, by + 5, P["cloth"], P["cloth_sh"])
        _face(c, bx - 3, by - 3, crying=False, blink=frame == 2)

    def front_wing(c: Canvas) -> None:
        _wing(c, frame, 0, 0, P["white"], P["tip"])

    layers = [back_wing, legs, body] + ([bundle] if carrying else []) + [front_wing]
    return layered(STORK_W, STORK_H, layers)


# -- the baby --------------------------------------------------------------------

def _face(c: Canvas, x: int, y: int, crying: bool, blink: bool = False) -> None:
    """A 7x6 baby face with its top-left at (x, y)."""
    c.oval(x, y, 7, 6, P["skin"])
    c.hline(x + 1, x + 5, y + 5, P["skin_sh"])
    if crying:
        c.hline(x + 1, x + 2, y + 2, INK)                 # screwed-shut eyes
        c.hline(x + 4, x + 5, y + 2, INK)
        c.rect(x + 2, y + 3, 3, 2, P["hole"])             # WAAH
    else:
        eye = P["skin_sh"] if blink else INK
        c.set(x + 2, y + 2, eye)
        c.set(x + 4, y + 2, eye)
        c.set(x + 1, y + 3, P["cheek"])
        c.set(x + 5, y + 3, P["cheek"])
        c.set(x + 3, y + 4, P["slit"])


def baby(frame: int, crying: bool = False) -> Canvas:
    """The bundle on its own (falling, or crying on the floor), BABY_SIZE square."""
    def draw(c: Canvas) -> None:
        c.stamp(6, 0, ["#..#", "####"], {"#": P["cloth_hi"]})     # knot ears
        c.oval(2, 2, 14, 13, P["cloth"])
        shade_rows(c, 11, 15, P["cloth"], P["cloth_sh"])
        c.set(4, 4, P["cloth_hi"])
        _face(c, 6, 5, crying)
        if crying:                                                # tears fly off
            t = 4 + frame
            c.set(5, 6 + frame, P["tear"])
            c.set(12, 6 + (1 - frame), P["tear"])
            c.set(3, t, P["tear"])
            c.set(14, 9 - frame, P["tear"])
    c = layered(BABY_SIZE, BABY_SIZE, [draw])
    return c.flipped() if frame % 2 and not crying else c


# -- the target ---------------------------------------------------------------------

# Body shape per pose: (top row, height, half-width). Chewing squashes and
# stretches it; spitting and squirting rear up tall.
TARGET_SHAPES = {"chew0": (8, 24, 12.0), "chew1": (2, 30, 9.5), "spit": (1, 31, 10.0),
                 "squirt0": (1, 31, 10.0), "squirt1": (3, 29, 11.0)}
TARGET_POSES = ("walk0", "walk1", "open", "chew0", "chew1", "spit", "squirt0", "squirt1", "happy")


# Where the clitoris should be: a little round nub with a question mark on it. Who knows?
QMARK = ["##.", "..#", ".#.", "...", ".#."]
NUB, NUB_RIM, QMARK_COLOR = "#ff6a9a", MUTANT["flesh_dk"], "#ffffff"


def _hands_for(hold: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """(front, back) hand positions gripping a baby centered at hold = (dx, y)."""
    cx = TARGET_W // 2
    dx, y = hold
    return (cx + dx + 8, y + 1), (cx + dx - 8, y + 1)


def target(pose: str, hold: tuple[int, int] | None = None) -> Canvas:
    """A cartoon vulva in red sneakers, TARGET_W x TARGET_H. Faces right (the
    raised hand in front); flip it when it walks left.

    pose: "walk0" / "walk1" (strolling), "open" (incoming!), "chew0" / "chew1"
    (working on a baby), "spit" (here he comes), "squirt0" / "squirt1" (three in
    a row: it lets loose), "happy" (all done).
    hold: (dx, row) of a baby it's grabbing, relative to its center column; the
    arms reach out to it (draw the baby, then target_hands() on top).
    """
    if hold:
        pose = "open"
    swing = {"walk0": 1, "walk1": -1}.get(pose, 0)
    spread = 1 if pose in ("chew0", "squirt1") else 0    # knees buckle
    T = TARGET_PAD
    y0, h, hw = TARGET_SHAPES.get(pose, (4, 28, 10.5))
    y0 += T
    cx = TARGET_W // 2
    sy = y0 + round(h * 0.45)                             # shoulder row
    front, back = {                                       # where each hand goes
        "walk0": ((cx + 15, T + 11), (cx - 14, sy + 8)),
        "walk1": ((cx + 15, T + 10), (cx - 13, sy + 7)),
        "open": ((cx + 16, T + 7), (cx - 15, sy + 3)),
        "chew0": ((cx + 15, y0 + h - 4), (cx - 15, y0 + h - 5)),
        "chew1": ((cx + 13, y0 + h - 6), (cx - 13, y0 + h - 7)),
        "spit": ((cx + 16, y0), (cx - 16, y0 - 2)),
        "squirt0": ((cx + 17, y0 - 1), (cx - 16, y0 + 1)),
        "squirt1": ((cx + 15, y0 + 2), (cx - 17, y0 - 2)),
        "happy": ((cx + 15, T + 8), (cx - 16, y0 + 2)),
    }[pose] if not hold else _hands_for(hold)

    def arms(c: Canvas) -> None:
        for (sx, sy_), (hx, hy) in (((cx - round(hw) + 2, sy), back), ((cx + round(hw) - 2, sy), front)):
            ex, ey = elbow(sx, sy_, hx, hy, 2.0)
            c.stroke(sx, sy_, ex, ey, P["flesh_sh"], 2)
            c.stroke(ex, ey, hx, hy, P["flesh_sh"], 2)
            c.rect(hx - 1, hy - 1, 3, 3, P["flesh"])

    def legs(c: Canvas) -> None:
        for hx, fx in ((cx - 4, cx - 6 + 2 * swing - spread), (cx + 3, cx + 5 - 2 * swing + spread)):
            c.stroke(hx, T + 30, fx, T + 35, P["flesh_sh"], 2)
            c.rect(fx - 2, T + 35, 5, 2, P["shoe"])
            c.set(fx - 1, T + 35, P["shoe_hi"])
            c.hline(fx - 2, fx + 2, T + 37, P["sole"])

    def body(c: Canvas) -> None:
        spans = almond(c, cx, y0, h, hw, P["flesh"])
        for y, (x0, x1) in spans.items():                   # shade left, light right
            c.set(x0, y, P["flesh_sh"])
            if x1 - x0 > 6:
                c.set(x0 + 1, y, P["flesh_sh"])
                c.set(x1 - 1, y, P["flesh_hi"])
        lip_hw = {"open": 5.5, "spit": 6.5, "squirt0": 6.5, "squirt1": 7.0, "chew1": 3.5}.get(pose, 4.5)
        lips = almond(c, cx, y0 + 4, h - 8, lip_hw, P["lip"])
        for y, (x0, x1) in lips.items():
            if x1 - x0 > 3:
                c.set(x1 - 1, y, P["lip_hi"])
        mid = y0 + h // 2
        if pose == "open":
            almond(c, cx, y0 + 9, h - 15, 2.5, P["hole"])
        elif pose in ("spit", "squirt0", "squirt1"):
            almond(c, cx, y0 + 9, h - 14, 4.0, P["hole"])
        elif pose == "chew0":                                # chomping side to side
            for i, y in enumerate(range(y0 + 10, y0 + h - 6)):
                c.set(cx + (1 if (i // 2) % 2 else -1), y, P["slit"])
        elif pose == "chew1":
            c.vline(cx, y0 + 10, y0 + h - 8, P["slit"])
            c.hline(cx - 1, cx + 1, mid, P["slit"])
        elif pose == "happy":
            c.vline(cx, T + 14, T + 23, P["slit"])
            c.set(cx - 1, T + 18, P["slit"])                 # a satisfied little smile
            c.set(cx + 1, T + 18, P["slit"])
        else:
            c.vline(cx, T + 14, T + 24, P["slit"])
        c.oval(cx - 3, y0 + 2, 7, 7, NUB_RIM)
        c.oval(cx - 2, y0 + 3, 5, 5, NUB)
        c.stamp(cx - 1, y0 + 3, QMARK, {"#": QMARK_COLOR})
        # the tuft
        c.stamp(cx - 6, y0 - 3, ["..#.##.#..#.", ".##########.", "############", ".#.######.#.", "...#.##.#..."],
                {"#": P["hair"]})
        for x in (cx - 4, cx, cx + 3):
            c.set(x, y0 - 2, P["hair_hi"])
        if pose in ("happy", "chew0", "chew1", "squirt0", "squirt1"):
            c.set(cx - 7, mid - 4, P["heart"])               # blush
            c.set(cx + 6, mid - 4, P["heart"])

    return layered(TARGET_W, TARGET_H, [arms, legs, body])


def target_hands(hold: tuple[int, int]) -> Canvas:
    """Just the two hands from target(hold=...), to draw over the baby they grip."""
    c = Canvas(TARGET_W, TARGET_H)
    for hx, hy in _hands_for(hold):
        c.rect(hx - 1, hy - 1, 3, 3, P["flesh"])
    c.outline(OUTLINE)
    return c


# -- the flying spaghetti monster -----------------------------------------------------

FSM_W, FSM_H, FSM_FRAMES = 52, 44, 4
FSM_GRAB = (26, 34)              # where a stolen bundle hangs, inside the frame
PASTA, PASTA_SH, PASTA_HI = "#f0d27a", "#c8a050", "#fff0b0"
MEATBALL, MEATBALL_SH, MEATBALL_HI = "#8a4a2a", "#5a2a14", "#b86a3a"


def spaghetti_monster(frame: int) -> Canvas:
    """A tangle of noodles with two meatballs, eyes on stalks, and noodly
    appendages waving underneath. Faces right; frame 0..FSM_FRAMES-1 wiggles."""
    ph = 2 * math.pi * frame / FSM_FRAMES
    rng = random.Random(42)                                  # same tangle every frame

    def appendages(c: Canvas) -> None:
        for i, root in enumerate(range(12, 42, 5)):
            length = 14 + (i * 7) % 9
            for k in range(length):
                y = 22 + k
                x = root + round(2.5 * math.sin(k * 0.45 + ph + i * 1.3)) - k // 5
                c.set(x, y, PASTA if k % 5 else PASTA_SH)

    def stalks(c: Canvas) -> None:
        for bx, tx, ty in ((26, 28, 0), (33, 39, 2)):
            wob = round(math.sin(ph + bx))
            c.line(bx, 12, tx + wob, ty + 5, PASTA, 1)
            c.oval(tx - 3 + wob, ty, 7, 7, "#f4f4f4")
            c.rect(tx + 1 + wob, ty + 2, 2, 3, INK)          # pupils look ahead

    def tangle(c: Canvas) -> None:
        c.oval(9, 10, 34, 16, PASTA)
        for i in range(12):                                  # loops of noodle, drawn as shadow lines
            x0, y0 = rng.randint(12, 38), rng.randint(13, 22)
            r = rng.randint(3, 5)
            a0 = rng.uniform(0, math.tau)
            for k in range(9):
                a = a0 + k * 0.5
                x, y = round(x0 + r * math.cos(a)), round(y0 + 0.6 * r * math.sin(a))
                if c.get(x, y):
                    c.set(x, y, PASTA_SH if i % 3 else PASTA_HI)
        shade_rows(c, 23, 26, PASTA, PASTA_SH)
        for mx, my in ((15, 11), (29, 14)):                  # meatballs
            c.oval(mx, my, 9, 8, MEATBALL)
            c.hline(mx + 2, mx + 6, my + 7, MEATBALL_SH)
            c.rect(mx + 2, my + 1, 2, 2, MEATBALL_HI)
            c.set(mx + 6, my + 4, MEATBALL_SH)
            c.set(mx + 4, my + 5, MEATBALL_SH)

    return layered(FSM_W, FSM_H, [appendages, stalks, tangle])


# -- effects and backdrop -------------------------------------------------------------

def heart() -> Canvas:
    c = Canvas(9, 8)
    c.stamp(1, 1, [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."], {"#": P["heart"]})
    c.set(2, 2, P["heart_hi"])
    c.outline(OUTLINE)
    return c


DNA_W, DNA_H, DNA_FRAMES = 9, 24, 8
DNA_BASES = ("#39ff14", "#ffd93a", "#ff6a9a", "#5ff3ff")    # A, C, G, T


def dna(frame: int) -> Canvas:
    """One twisting double helix; frame 0..DNA_FRAMES-1 spins it a step."""
    c = Canvas(DNA_W, DNA_H)
    spin = 2 * math.pi * frame / DNA_FRAMES
    for y in range(1, DNA_H - 1):
        ph = y * 0.55 + spin
        xa, xb = round(4 + 3 * math.sin(ph)), round(4 - 3 * math.sin(ph))
        if y % 3 == 0:                                       # base-pair rungs
            c.hline(min(xa, xb) + 1, max(xa, xb) - 1, y, DNA_BASES[(y // 3 + frame // 2) % 4])
        front_a = math.cos(ph) > 0                           # whichever strand is nearer goes on top
        for x, col, front in ((xb, P["cloth_sh"], not front_a), (xa, P["white"], front_a)):
            if not front:
                c.set(x, y, mix(col, LAB_BG, 0.35))
        for x, col, front in ((xb, P["cloth_sh"], not front_a), (xa, P["white"], front_a)):
            if front:
                c.set(x, y, col)
    c.outline(OUTLINE)
    return c


SQUIRT, SQUIRT_HI, SQUIRT_SH = "#d8f4ff", "#ffffff", "#8ac8e8"


def droplet(big: bool) -> Canvas:
    """A falling drop, point up."""
    c = Canvas(7, 8)
    if big:
        c.stamp(1, 1, ["..#..", ".###.", "#####", "#####", ".###."], {"#": SQUIRT})
        c.set(2, 3, SQUIRT_HI)
        c.hline(2, 4, 5, SQUIRT_SH)
    else:
        c.stamp(2, 2, [".#.", "###", ".#."], {"#": SQUIRT})
        c.set(3, 3, SQUIRT_HI)
    c.outline(OUTLINE)
    return c


def puddle(w: int) -> Canvas:
    """A splat on the floor."""
    c = Canvas(w + 2, 5)
    c.oval(1, 1, w, 3, SQUIRT)
    c.hline(2, w - 1, 3, SQUIRT_SH)
    c.set(2, 1, SQUIRT_HI)
    c.outline(OUTLINE)
    return c


def cloud(w: int, seed: int) -> Canvas:
    rng = random.Random(seed)
    h = w // 3 + 4
    c = Canvas(w, h)
    for _ in range(w // 6):
        bw = rng.randint(w // 4, w // 2)
        bh = rng.randint(h // 2, h - 1)
        c.oval(rng.randint(0, w - bw), h - bh, bw, bh, P["cloud"])
    for y in range(h):                                       # lit from the moon above
        for x in range(w):
            if c.get(x, y) and not c.get(x, y - 2):
                c.set(x, y, P["cloud_hi"])
    return c


def backdrop(w: int, h: int, floor_y: int, seed: int = 7) -> Canvas:
    """Night sky over a sleepy city, with the lab floor in front."""
    rng = random.Random(seed)
    c = Canvas(w, h)
    sky_lo = mix(LAB_BG, LAB_GRID, 0.45)
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    for y in range(floor_y):                                 # ordered-dither glow toward the horizon
        t = max(0.0, (y / floor_y - 0.4) / 0.6)
        for x in range(w):
            c.set(x, y, sky_lo if bayer[y % 4][x % 4] < t * 16 else LAB_BG)
    for _ in range(70):
        x, y = rng.randrange(w), rng.randrange(floor_y - 40)
        c.set(x, y, P["star"] if rng.random() < 0.3 else LAB_GRID)
    c.oval(262, 14, 22, 22, P["moon"])                       # moon
    for mx, my, r in ((268, 20, 4), (276, 28, 3), (274, 18, 2)):
        c.oval(mx, my, r, r, P["moon_sh"])
    x = 0
    while x < w:                                             # skyline
        bw, bh = rng.randint(14, 30), rng.randint(14, 44)
        c.rect(x, floor_y - bh, bw, bh, P["city"])
        for wy in range(floor_y - bh + 4, floor_y - 3, 5):
            for wx in range(x + 3, x + bw - 3, 4):
                if rng.random() < 0.25:
                    c.rect(wx, wy, 2, 2, P["window"])
        x += bw + rng.randint(0, 4)
    c.rect(0, floor_y, w, h - floor_y, LAB_FLOOR)            # floor, same as the viewer
    c.hline(0, w - 1, floor_y, LAB_GRID)
    for gx in range(-16, w + 16, 16):
        c.line(gx, floor_y, gx - 12, h - 1, LAB_GRID)
    return c
