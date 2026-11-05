"""Succubus: a pocket-sized cartoon demon. Little horns, bat wings, spade tail.
Attacks by blowing kisses, which hurt more than you'd think."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, SUCCUBUS as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "succubus"
PREFIX, SUFFIX = "Succu", "cubus"


HEART = ["XX.XX", "XXXXX", ".XXX.", "..X.."]
BIG_HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]


def heart(c: Canvas, x: int, y: int, big: bool = False) -> None:
    """Pixel heart with its top-left at (x, y), with a shine on the left lobe."""
    c.stamp(x, y, BIG_HEART if big else HEART, {"X": P["heart"]})
    if big:
        c.set(x + 1, y + 1, P["heart_hi"])
        c.set(x + 2, y + 1, P["heart_hi"])
        c.hline(x + 2, x + 4, y + 4, P["heart_dk"])
    else:
        c.set(x, y, P["heart_hi"])


def fill_tri(c: Canvas, a: tuple, b: tuple, d: tuple, col: str) -> None:
    """Filled triangle (inclusive edges)."""
    xs, ys = (a[0], b[0], d[0]), (a[1], b[1], d[1])

    def side(p, q, x, y):
        return (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0])

    for y in range(math.floor(min(ys)), math.ceil(max(ys)) + 1):
        for x in range(math.floor(min(xs)), math.ceil(max(xs)) + 1):
            s1, s2, s3 = side(a, b, x, y), side(b, d, x, y), side(d, a, x, y)
            if (s1 >= -0.5 and s2 >= -0.5 and s3 >= -0.5) or (s1 <= 0.5 and s2 <= 0.5 and s3 <= 0.5):
                c.set(x, y, col)


# Bat wing in local coords around the root (x < 0 is behind her): wrist, then finger tips.
WRIST = (-5, -7)
FINGERS = [(-13, -6), (-12, 0), (-6, 4)]

# Wing angle per frame (+ = raised). Missing anims use idle's gentle flutter.
FLAP = {
    "idle": (0.1, 0.3, 0.1, -0.05),
    "walk": (0.35, 0.0, 0.35, 0.0),
    "run": (0.5, -0.2, 0.5, -0.2),
    "jump": (-0.2, 0.55, 0.25, 0.5),
    "attack": (0.0, 0.45, 0.4, 0.15),
    "hurt": (-0.35, -0.45),
}


def bat_wing(c: Canvas, rx: int, ry: int, angle: float) -> None:
    """Scalloped bat wing hinged at (rx, ry), swung up by `angle` radians."""
    ca, sa = math.cos(angle), math.sin(angle)

    def rot(p):
        return rx + p[0] * ca - p[1] * sa, ry + p[0] * sa + p[1] * ca

    root, wrist = (rx, ry), rot(WRIST)
    tips = [rot(f) for f in FINGERS]
    for a, b in zip(tips, tips[1:]):                          # membrane, notched between fingers
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        notch = (mid[0] + (wrist[0] - mid[0]) * 0.3, mid[1] + (wrist[1] - mid[1]) * 0.3)
        fill_tri(c, wrist, a, notch, P["wing"])
        fill_tri(c, wrist, notch, b, P["wing"])
    fill_tri(c, root, wrist, tips[-1], P["wing"])
    w = (round(wrist[0]), round(wrist[1]))
    for t in tips:                                             # finger bones
        c.line(*w, round(t[0]), round(t[1]), P["wing_dk"])
    c.line(rx, ry, *w, P["wing_hi"])                           # leading edge
    c.set(w[0], w[1] - 1, P["wing_hi"])                        # little thumb claw


class SuccubusLegs(Legs):
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1, hip, fx, foot_y - 4, P["outfit"] if front else P["outfit_sh"], width=3)
            boot = P["boot"] if front else P["wing_dk"]
            c.line(fx, foot_y - 3, fx, foot_y - 1, boot, width=3)  # boot shaft
            c.rect(fx, foot_y, 4, 2, boot)
            if front:
                c.vline(fx + 2, foot_y - 3, foot_y, P["boot_hi"])
                c.set(fx + 3, foot_y, P["boot_hi"])


class SuccubusTorso(Torso):
    """Dark top and belt. Also owns the wings and the tail, so they survive splicing."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        flap = FLAP.get(pose.anim, FLAP["idle"])
        bat_wing(c, cx - 3, top + 3, flap[pose.frame % len(flap)])
        # tail: dips down behind her, curls back up, ends in a spade
        sway = wave(pose.frame, pose.n)
        rx, ry = cx - 3, hip - 1
        px, py = rx - 10, hip + sway
        pts = []
        for i in range(13):
            t = i / 12
            x = (1 - t) ** 2 * rx + 2 * (1 - t) * t * (rx - 3) + t * t * px
            y = (1 - t) ** 2 * ry + 2 * (1 - t) * t * (hip + 8) + t * t * py
            pts.append((round(x), round(y)))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            c.line(x0, y0, x1, y1, P["skin_sh"])
        c.stamp(px - 2, py - 4, ["..X..", ".XXX.", "XXXXX", ".X.X."], {"X": P["horn"]})
        c.set(px - 1, py - 2, P["horn_hi"])
        # the outfit
        c.rect(cx - 1, top, 3, 1, P["skin"])
        c.rect(cx - 3, top + 1, 7, 10, P["outfit"])
        c.vline(cx + 3, top + 2, hip - 2, P["outfit_hi"])
        c.vline(cx - 3, top + 1, hip, P["outfit_sh"])
        c.hline(cx - 2, cx + 2, top + 1, P["outfit_hi"])          # neckline trim
        c.hline(cx - 3, cx + 3, hip - 1, P["boot"])               # belt...
        c.stamp(cx + 1, hip - 2, ["X.X", "XXX", ".X."], {"X": P["heart"]})   # ...heart buckle
        c.hline(cx - 3, cx + 3, hip, P["outfit_sh"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "...HHHHH...",
    "..HHhhhHHH.",
    ".HHhHHHHhHH",
    "HHhHHHHHHhH",
    "HHHHHHHHSSh",
    "HHHHHHHSSSS",
    "HHHHHHSSbbS",
    "HHHHHSSSYES",
    "HHHHSSSSSSN",
    "HHHHsSSSSS.",
    "HHHHsSSSMS.",
    ".HH.sSSSFS.",
    "....sSSSS..",
]


class SuccubusHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 5, ny - 13
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "S": P["skin"], "s": P["skin_sh"],
            "b": P["hair"], "Y": P["skin_sh"] if pose.blink else P["eye"],
            "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"],
            "M": P["mouth"], "F": P["fang"],
        }
        c.stamp(x0, y0, HEAD, key)
        # two little horns poking out of the hair, curling forward
        c.stamp(x0 + 6, y0 - 2, [".rr", ".RR"], {"r": P["horn_hi"], "R": P["horn"]})
        c.stamp(x0 + 2, y0 - 2, [".r", "rR"], {"r": P["horn_hi"], "R": P["horn"]})


class SuccubusArm(Arm):
    """Bare arm with a red cuff. Attacks by blowing a kiss: a heart that bursts on contact."""
    species = SPECIES
    reach = 8
    fx_colors = (P["heart"], P["heart_hi"])
    targets = {
        "windup": ((0.55, -0.75), (-0.4, 0.85)),            # fingertips to lips...
        "strike": ((1.0, -0.2), (-0.7, 0.55)),               # ...and blow
        "follow": ((0.95, -0.05), (-0.6, 0.7)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        dx = (-2 if front else 2) * pose.swing
        if front and pose.anim == "idle":                     # hand on hip
            c.line(sx, sy, sx + 3, sy + 4, skin, width=2)
            c.line(sx + 3, sy + 5, sx + 2, sy + 8, skin, width=2)
            c.set(sx + 3, sy + 4, P["boot"])
            c.rect(sx + 1, sy + 8, 2, 2, skin)
            return
        c.line(sx, sy, sx + dx, sy + 6, skin, width=2)
        c.hline(sx + dx, sx + dx + 1, sy + 6, P["boot"] if front else P["wing_dk"])
        c.rect(sx + dx, sy + 7, 2, 2, skin)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        c.rect(hx, hy, 2, 2, skin)
        if front and mode in ("strike", "follow"):            # open palm
            c.vline(hx + 2, hy - 1, hy + 1, skin)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                               # the kiss leaves the hand
            heart(fx, min(hx + 5, 41), hy - 3)
            for dx, dy in ((3, 0), (1, -2)):
                fx.set(hx + dx, hy + dy, P["heart_hi"])
        else:                                                 # ...and lands. Smooch.
            x, y = min(hx + 5, 36), hy - 4                    # stays inside the frame
            heart(fx, x, y, big=True)
            for dx, dy in ((-1, -4), (7, -3), (7, 6), (0, 7)):
                fx.stamp(x + dx, y + dy, ["X.X", ".X."], {"X": P["heart_hi"]})


GENES = dict(legs=SuccubusLegs(), torso=SuccubusTorso(), head=SuccubusHead(), arm=SuccubusArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
