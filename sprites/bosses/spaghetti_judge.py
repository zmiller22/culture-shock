"""The Honorable Judge Spaghetti: a Flying Spaghetti Monster in a powdered wig.

Bosses don't fit the 48x48 body-plan rig, so this one is drawn directly into a
bigger frame. Same conventions as the cast otherwise: facing right, one row per
state, outlined layers composited back to front.

A tangle of noodles with two meatballs, eyes on noodly stalks, a barrister's
wig, white court bands, and a gavel held in one noodly appendage. Dozens more
noodles dangle underneath, because that is how it flies.
"""

from __future__ import annotations

import math

from ..canvas import Canvas, wave
from ..effects import hit_flash
from ..palette import INK, OUTLINE, SPAGHETTI_JUDGE as P
from ..rig import star
from ..species.wyvern import bezier, fill_poly

NAME = "The Honorable Judge Spaghetti"
SLUG = "spaghetti_judge"
W = H = 80
CX, CY = 40, 38            # center of the noodle mass when hovering

ANIMATIONS = {"idle": 4, "fly": 4, "attack": 4, "hurt": 2, "death": 6}
FPS = {"idle": 6, "fly": 10, "attack": 10, "hurt": 10, "death": 6}
LOOP = {"idle": True, "fly": True, "attack": False, "hurt": False, "death": False}
NOTES = {
    "idle": "hover in place (the bob is baked in)",
    "fly": "loop while moving; noodles trail behind",
    "attack": "gavel slam: wind-up, swing, impact, recover. The hit lands on frame 2 at `attack_point`. "
              "Draw ORDER! over it yourself (text baked into a sprite would read backwards when flipped)",
    "hurt": "play once; frame 1 is the white hit-flash",
    "death": "play once and hold the last frame (a plate of spaghetti, wig on top)",
}

# Where the gavel hand goes per attack frame, relative to (CX, CY), and the handle angle in degrees
# (0 = pointing right, 90 = pointing down).
SWING = [((12, -18), -115), ((22, -10), -15), ((26, 18), 75), ((24, 2), -60)]
IMPACT = (CX + 30, 74)     # where the gavel lands on attack frame 2

# Dangling noodles: (x offset from CX, length, phase)
DANGLE = [(-15, 13, 0.0), (-11, 19, 1.9), (-7, 15, 3.1), (-3, 21, 0.7),
          (1, 17, 2.4), (5, 22, 4.0), (9, 16, 1.2), (13, 18, 5.1), (16, 12, 2.9)]


def noodle(c: Canvas, pts: list[tuple[float, float]], col: str = P["noodle"], hi: str = P["noodle_hi"]) -> None:
    """A 2px noodle through `pts`, with a highlight running along its top edge."""
    ipts = [(round(x), round(y)) for x, y in pts]
    for (x0, y0), (x1, y1) in zip(ipts, ipts[1:]):
        c.stroke(x0, y0, x1, y1, col, 2)
    for (x0, y0), (x1, y1) in zip(ipts, ipts[1:]):
        c.line(x0, y0, x1, y1, hi)


def curve(p0, p1, p2, n: int = 14) -> list[tuple[float, float]]:
    return [bezier(p0, p1, p2, i / n) for i in range(n + 1)]


# ---------------------------------------------------------------- body parts

def noodle_mass(c: Canvas, cx: int, cy: int, phase: float, squash: float = 1.0) -> None:
    """A lumpy heap of tangled noodles, with strands drawn across it."""
    h = max(4, round(18 * squash))
    w = round(34 + (1 - squash) * 18)
    mask = Canvas(W, H)
    mask.oval(cx - w // 2, cy - h // 2, w, h, P["noodle"])
    for dx, dy, r in ((-12, 3, 9), (11, 4, 10), (-2, 6, 10), (3, -5, 9)):    # lumps
        mask.oval(cx + dx - r // 2, cy + round(dy * squash) - r // 2, r, max(3, round(r * squash)), P["noodle"])
    c.paste(mask)
    for s in range(-4, 5):                          # strands: long lazy squiggles
        for x in range(cx - w // 2 - 4, cx + w // 2 + 5):
            y = cy + round((s * 2.2 + 1.2 * math.sin(x * 0.28 + s * 2.3 + phase)) * squash)
            if mask.opaque(x, y) and mask.opaque(x, y + 1):
                c.set(x, y, P["noodle_sh"])
                if (x + s) % 3:
                    c.set(x, y - 1, P["noodle_hi"])
    for x in range(W):                              # shade the underside
        ys = [y for y in range(H) if mask.opaque(x, y)]
        if ys:
            c.set(x, ys[-1], P["noodle_dk"])
            c.set(x, ys[-1] - 1, P["noodle_sh"])


def meatball(c: Canvas, x: int, y: int, r: int = 5) -> None:
    c.oval(x - r, y - r, 2 * r, 2 * r, P["meat"])
    c.oval(x - r + 1, y - r + 1, r, r - 1, P["meat_hi"])
    c.oval(x - r + 2, y - r + 2, r - 1, r - 2, P["meat"])     # leaves a crescent highlight
    for dx, dy in ((2, 1), (-2, 2), (1, -2), (3, -1), (-1, 3)):
        c.set(x + dx, y + dy, P["meat_sh"])
    c.hline(x - r + 1, x + r - 2, y + r - 1, P["meat_sh"])
    c.hline(x - 2, x + 2, y - r, P["sauce"])                  # marinara on top...
    c.set(x - 1, y - r + 1, P["sauce"])
    c.vline(x + 2, y - r + 1, y - r + 3, P["sauce"])          # ...dripping
    c.set(x - 1, y - r, P["sauce_hi"])


def wig(c: Canvas, x: int, y: int) -> None:
    """A barrister's powdered wig, centered at x, top at y: a curly crown, rolls of curls
    down each side, and a little ribboned queue at the back."""
    c.oval(x - 8, y, 17, 8, P["wig"])                          # crown
    for row, yy in enumerate((y + 3, y + 5)):                  # rows of tight curls
        for xx in range(x - 7 + row, x + 8, 3):
            if c.get(xx, yy) == P["wig"]:
                c.set(xx, yy, P["wig_sh"])
                c.set(xx + 1, yy, P["wig_dk"])
    for sx in (x - 10, x + 6):                                 # side rolls
        for k in range(3):
            c.oval(sx, y + 4 + 3 * k, 5, 4, P["wig"])
            c.hline(sx + 1, sx + 3, y + 6 + 3 * k, P["wig_sh"])
            c.set(sx + 3, y + 6 + 3 * k, P["wig_dk"])
    c.hline(x - 5, x + 3, y + 1, "#ffffff")                    # shine
    c.stamp(x - 14, y + 5, ["RR.RR", ".RRR.", "RR.RR"], {"R": P["ribbon"]})   # bow on the queue
    c.vline(x - 12, y + 8, y + 12, P["wig_sh"])
    c.vline(x - 13, y + 8, y + 11, P["wig"])


def eyeball(c: Canvas, x: int, y: int, look: tuple[int, int], mode: str) -> None:
    c.oval(x - 4, y - 4, 8, 8, P["eye_w"])
    c.hline(x - 2, x + 2, y + 3, P["eye_sh"])
    if mode == "blink":
        c.oval(x - 4, y - 4, 8, 5, P["noodle"])                # noodle eyelid
        c.hline(x - 3, x + 3, y, P["noodle_dk"])
    elif mode == "x":
        for d in range(-2, 3):
            c.set(x + d, y + d, INK)
            c.set(x + d, y - d, INK)
    else:
        px, py = x + look[0], y + look[1]
        c.rect(px - 1, py - 1, 3, 3, INK)
        c.set(px - 1, py - 1, "#ffffff")


def gavel(c: Canvas, hx: int, hy: int, deg: float) -> tuple[int, int]:
    """Gavel gripped at (hx, hy), handle pointing along `deg`. Returns the head's center."""
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)                         # along the handle
    px, py = -uy, ux                                          # across it
    ex, ey = hx + ux * 12, hy + uy * 12
    c.stroke(hx, hy, round(ex), round(ey), P["wood_sh"], 2)
    c.line(hx, hy, round(ex), round(ey), P["wood"])

    def box(along0, along1, across):
        return [(ex + ux * s + px * t, ey + uy * s + py * t)
                for s, t in ((along0, -across), (along1, -across), (along1, across), (along0, across))]

    fill_poly(c, box(-4, 4, 7), P["wood"])
    fill_poly(c, box(-4, -1.5, 7), P["wood_hi"])
    fill_poly(c, box(2.5, 4, 7), P["wood_sh"])
    for t in (-6, 4.5):                                       # brass bands near each end
        fill_poly(c, [(ex + ux * s + px * (t + d), ey + uy * s + py * (t + d))
                      for s, d in ((-4, 0), (4, 0), (4, 1.5), (-4, 1.5))], P["brass"])
    return round(ex), round(ey)


def arm_curve(sx: int, sy: int, hx: int, hy: int, curl: float) -> list[tuple[float, float]]:
    mx, my = (sx + hx) / 2, (sy + hy) / 2
    dx, dy = hx - sx, hy - sy
    return curve((sx, sy), (mx - dy * curl, my + dx * curl), (hx, hy))


# ---------------------------------------------------------------- frames

def hover(anim: str, f: int, n: int) -> dict:
    """Everything that varies per frame, as plain numbers."""
    s = dict(ox=0, oy=0, trail=0.0, eyes="open", look=(1, 0), stalk=0.0, wig=(0, 0),
             hand=None, deg=-90.0, fx=None, phase=f * math.pi / 2, back=(-26, 4), flash=False)
    if anim == "idle":
        s["oy"] = wave(f, n, 2)
        s["eyes"] = "blink" if f == 3 else "open"
        s["stalk"] = wave(f, n, 1.5, 1.0)
        s["back"] = (-25, 2 + wave(f, n, 3, 2.0))
    elif anim == "fly":
        s["oy"] = wave(f, n, 1)
        s["trail"] = 1.0
        s["stalk"] = -2.0
        s["look"] = (2, 0)
        s["back"] = (-28, 10 + wave(f, n, 2))
    elif anim == "attack":
        s["oy"] = (-2, 0, 3, 1)[f]
        s["ox"] = (-2, 2, 3, 0)[f]
        s["hand"], s["deg"] = SWING[f]
        s["look"] = ((1, -1), (2, 1), (2, 2), (1, 1))[f]
        s["stalk"] = (-1.5, 1.5, 2.5, 0.5)[f]
        s["fx"] = (None, "swoosh", "impact", None)[f]
        s["back"] = ((-26, -8), (-26, 6), (-24, 12), (-26, 4))[f]
    elif anim == "hurt":
        s["ox"], s["oy"] = -3, 1
        s["eyes"] = "x"
        s["stalk"] = -3.0
        s["trail"] = -0.6
        s["wig"] = (-1, -3)
        s["flash"] = f == 1
        s["back"] = (-24, -10)
    return s


def draw_hover(s: dict) -> Canvas:
    cx, cy = CX + s["ox"], CY + s["oy"]
    layers = {k: Canvas(W, H) for k in ("dangle", "back_arm", "body", "wig", "stalks", "meatballs", "front_arm", "fx")}

    # dangling noodles: wiggle, and sweep back when flying
    for dx, length, ph in DANGLE:
        x0, y0 = cx + dx, cy + 6
        pts = []
        for t in range(0, length + 1, 2):
            sway = 1.8 * math.sin(t * 0.35 + ph + s["phase"])
            pts.append((x0 + sway - s["trail"] * t * 0.9, y0 + t * (1 - 0.35 * abs(s["trail"]))))
        noodle(layers["dangle"], pts, P["noodle_sh"], P["noodle"])

    # back appendage, just waving
    bx, by = s["back"]
    noodle(layers["back_arm"], arm_curve(cx - 14, cy + 1, cx + bx, cy + by, 0.35), P["noodle_sh"], P["noodle"])
    layers["back_arm"].oval(cx + bx - 2, cy + by - 1, 4, 3, P["noodle_sh"])      # a little curled tip

    body = layers["body"]
    noodle_mass(body, cx, cy, s["phase"])
    meatball(layers["meatballs"], cx - 13, cy - 2, 6)
    meatball(layers["meatballs"], cx + 13, cy - 1, 6)
    body.rect(cx - 1, cy + 2, 6, 2, P["band"])                 # white court bands
    body.rect(cx - 1, cy + 4, 2, 4, P["band"])
    body.rect(cx + 3, cy + 4, 2, 4, P["band"])

    wx, wy = cx + s["wig"][0], cy - 17 + s["wig"][1]
    wig(layers["wig"], wx, wy)

    # eyestalks, sprouting up through the wig
    st = layers["stalks"]
    eyes = []
    for side, base_dx in ((-1, -4), (1, 5)):
        bx0, by0 = cx + base_dx, cy - 14
        ex = cx + base_dx + side * 7 + round(s["stalk"] * (1 if side > 0 else 0.6))
        ey = cy - 30 - (1 if side > 0 else 0) + round(abs(s["stalk"]) * 0.3)
        noodle(st, curve((bx0, by0), (bx0 + side * 1, by0 - 10), (ex, ey + 3), 10))
        eyes.append((ex, ey))
    for ex, ey in eyes:
        eyeball(st, ex, ey, s["look"], s["eyes"])

    # gavel arm
    fa = layers["front_arm"]
    if s["hand"] is None:
        hx, hy = cx + 24, cy - 6 + wave(round(s["phase"] / (math.pi / 2)), 4, 1)
        deg = -95.0 if s["trail"] >= 0 else -150.0
        if s["trail"] > 0:
            hx, hy, deg = cx + 22, cy + 2, -60.0
    else:
        hx, hy = cx + s["hand"][0], cy + s["hand"][1]
        deg = s["deg"]
    noodle(fa, arm_curve(cx + 14, cy + 1, hx, hy, -0.3))
    head = gavel(fa, hx, hy, deg)
    fa.oval(hx - 2, hy - 2, 5, 4, P["noodle"])                 # noodle wrapped round the handle
    fa.hline(hx - 1, hx + 1, hy - 1, P["noodle_hi"])

    fx = layers["fx"]
    if s["fx"] == "swoosh":
        a0, a1 = math.radians(-120), math.radians(30)
        for i in range(4, 14):
            a = a0 + (a1 - a0) * i / 14
            fx.set(cx + 14 + round(math.cos(a) * 24), cy + round(math.sin(a) * 24), "#ffffff" if i % 3 else P["text"])
    elif s["fx"] == "impact":
        ix, iy = IMPACT
        star(fx, ix, iy, "#ffffff", P["text"], r=4)
        fx.hline(ix - 12, ix - 7, iy + 3, "#ffffff")           # shockwave along the floor
        fx.hline(ix + 6, ix + 9, iy + 3, "#ffffff")

    out = Canvas(W, H)
    for name, layer in layers.items():
        layer.outline(OUTLINE)
        if name != "fx":
            out.paste(layer)
    if s["flash"]:
        hit_flash(out)
    out.paste(layers["fx"])
    return out


def plate(c: Canvas, cx: int, y: int, heap: int) -> None:
    """A dinner plate with a heap of `heap` px of spaghetti on it."""
    c.oval(cx - 18, y - 2, 36, 8, P["plate"])
    c.oval(cx - 13, y - 1, 26, 5, P["plate_sh"])
    c.hline(cx - 14, cx + 14, y + 4, P["plate_rim"])
    if heap:
        noodle_mass(c, cx, y - heap // 2 + 1, 0.8, squash=heap / 18)


def draw_death(f: int) -> Canvas:
    if f == 0:                                                # the gavel comes down on itself
        s = hover("hurt", 0, 2)
        s["flash"] = True
        return draw_hover(s)
    layers = {k: Canvas(W, H) for k in ("dangle", "body", "wig", "stalks")}
    if f in (1, 2):                                           # wig pops off, everything goes limp, down it goes
        cy = CY + (6, 20)[f - 1]
        cx = CX
        for dx, length, ph in DANGLE:                         # noodles stream upward as it drops
            pts = [(cx + dx + math.sin(t * 0.4 + ph) * 1.5, cy + 4 - t * (0.4 if f == 2 else -0.6))
                   for t in range(0, length + 1, 2)]
            noodle(layers["dangle"], pts, P["noodle_sh"], P["noodle"])
        noodle_mass(layers["body"], cx, cy, 1.3)
        meatball(layers["body"], cx - 12, cy - 5)
        meatball(layers["body"], cx + 12, cy - 4)
        wig(layers["wig"], cx - 6 - 6 * f, cy - 30 - 4 * f)
        for side in (-1, 1):
            ex, ey = cx + side * 10, cy - 12 + (4 if f == 2 else -6)
            noodle(layers["stalks"], curve((cx + side * 3, cy - 8), (cx + side * 8, cy - 14), (ex, ey + 3), 8))
            eyeball(layers["stalks"], ex, ey, (0, 0), "x")
    else:                                                     # splat, then plated
        heap = (6, 10, 10)[f - 3]
        y = 72
        c = layers["body"]
        if f == 3:
            noodle_mass(c, CX, y - 2, 0.4, squash=0.35)
            for dx in (-22, -18, 19, 23):                     # splatter
                c.rect(CX + dx, y + 1, 2, 1, P["sauce"])
        else:
            plate(c, CX, y, heap)
            c.oval(CX - 9, y - 9, 7, 3, P["sauce"])           # sauce on top
            c.oval(CX + 2, y - 10, 7, 3, P["sauce"])
        mx = (-9, 10) if f == 3 else (-6, 6)
        my = y - (6 if f == 3 else heap + 2)
        meatball(c, CX + mx[0], my)
        meatball(c, CX + mx[1], my + 1)
        if f >= 4:
            for side in (-1, 1):                              # wilted eyestalks flopped over the rim
                ex, ey = CX + side * 20, y - 4
                noodle(layers["stalks"], curve((CX + side * 3, my - 3), (CX + side * 14, my - 12), (ex, ey - 2), 8))
                eyeball(layers["stalks"], ex, ey - 3, (0, 0), "x")
        wy = (y - 30, my - 12, my - 10)[f - 3]                # the wig settles on top, last
        wig(layers["wig"], CX + (8, 1, 0)[f - 3], wy)
        if f == 5:
            c.stamp(CX + 1, my - 3, [".G", "GG"], {"G": P["basil"]})    # garnish
            for k, sx in enumerate((CX - 16, CX + 14)):       # steam
                for t in range(6):
                    layers["stalks"].set(sx + round(math.sin(t * 1.2 + k)), wy - 2 - t, P["steam"])
    out = Canvas(W, H)
    for layer in layers.values():
        layer.outline(OUTLINE)
        out.paste(layer)
    return out


def render(anim: str, f: int) -> Canvas:
    if anim == "death":
        return draw_death(f)
    return draw_hover(hover(anim, f, ANIMATIONS[anim]))


def all_frames() -> dict[str, list[Canvas]]:
    return {anim: [render(anim, i) for i in range(n)] for anim, n in ANIMATIONS.items()}
