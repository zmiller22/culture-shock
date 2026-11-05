"""Wyvern: a two-legged dragon whose wings are its arms. Horns, spines, a tail
like a whip, and a serious heartburn problem."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, OUTLINE, WYVERN as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso

SPECIES = "wyvern"
PREFIX, SUFFIX = "Wyv", "wyrm"


def fill_poly(c: Canvas, pts: list[tuple[float, float]], col: str) -> None:
    """Scanline-fill a polygon (pixel centers inside the outline get painted)."""
    ys = [y for _, y in pts]
    for y in range(math.floor(min(ys)), math.ceil(max(ys)) + 1):
        yc = y + 0.5
        xs = sorted(
            x0 + (yc - y0) * (x1 - x0) / (y1 - y0)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])
            if (y0 <= yc) != (y1 <= yc)
        )
        for a, b in zip(xs[::2], xs[1::2]):
            for x in range(math.ceil(a - 0.5), math.floor(b - 0.5) + 1):
                c.set(x, y, col)


def bezier(p0, p1, p2, t: float) -> tuple[float, float]:
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def joint(tx: int, ty: int, fx: int, fy: int, seg: float, forward: bool) -> tuple[int, int]:
    """Two-bone joint between (tx, ty) and (fx, fy), bending forward (+x) or back."""
    dx, dy = fx - tx, fy - ty
    d = math.hypot(dx, dy) or 1
    off = math.sqrt(max(0.0, seg * seg - d * d / 4))
    px, py = -dy / d, dx / d
    if (px > 0) != forward:
        px, py = -px, -py
    return round(tx + dx / 2 + px * off), round(ty + dy / 2 + py * off)


class WyvernLegs(Legs):
    """Raptor legs: drumstick thigh, backward ankle, three hooked toes."""
    species = SPECIES
    length = 13

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            lift = (0 if front else pose.lift) + pose.tuck // 2
            base = cx - 1 if front else cx - 4
            tx = base + 3 * s                                # toes
            ty = ground - lift
            ax, ay = tx - 2, ty - 4                          # ankle
            kx, ky = joint(base, hip, ax, ay, 6.5, forward=True)
            col, dk = (P["scale"], P["scale_sh"]) if front else (P["scale_sh"], P["scale_dk"])
            c.oval(base - 3, hip - 3, 7, 8, col)             # drumstick thigh
            c.stroke(base, hip + 1, kx, ky, col, 3)
            c.stroke(kx, ky, ax, ay, dk, 2)
            c.stroke(ax, ay, tx, ty - 1, dk, 2)
            c.hline(tx - 1, tx + 3, ty, dk)                  # toes
            c.set(tx + 4, ty, P["claw"])
            c.set(tx + 4, ty - 1, P["claw"])
            c.set(tx - 2, ty, P["claw"])                     # dewclaw
            if front:
                c.set(base + 1, hip - 2, P["scale_hi"])
                c.line(base + 2, hip - 1, kx + 1, ky - 1, P["scale_hi"])


class WyvernTorso(Torso):
    """Barrel-chested, gold-bellied, with a long spiny tail swinging out behind."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        sway = wave(pose.frame, pose.n, 1.0)
        p0, p1, p2 = (cx - 9, hip - 5), (cx - 16, hip + 4), (max(5, cx - 17), hip - 4 + sway)
        n = 16
        for i in range(n + 1):                              # tail, thick to thin
            t = i / n
            x, y = bezier(p0, p1, p2, t)
            w = round(5 - 4 * t)
            c.oval(round(x - w / 2), round(y - w / 2), w, w, P["scale"])
        tip_x, tip_y = round(p2[0]), round(p2[1])
        c.stamp(tip_x - 3, tip_y - 2, ["..S.", ".SS.", "SSSS", ".SS.", "..S."], {"S": P["scale_sh"]})   # spade
        c.oval(cx - 11, top, 16, 13, P["scale"])            # body
        c.oval(cx - 3, top - 1, 9, 11, P["scale"])          # chest
        c.oval(cx - 3, top + 3, 8, 10, P["belly"])          # belly
        for y in range(top + 5, hip + 1, 2):                # belly plates
            span = [x for x in range(cx - 4, cx + 6) if c.get(x, y) == P["belly"]]
            if span:
                c.hline(span[0], span[-1], y, P["belly_sh"])
        for x in range(cx - 20, cx + 5):                    # back shading and dorsal spines
            col = [y for y in range(top - 2, hip + 8) if c.get(x, y) == P["scale"]]
            if not col:
                continue
            c.set(x, col[-1], P["scale_sh"])
            c.set(x, col[0], P["scale_hi"])
            if x % 3 == 0 and x < cx:
                c.set(x, col[0] - 1, P["scale_dk"])
        for x, y in ((cx - 8, top + 4), (cx - 6, top + 7), (cx - 9, top + 8), (cx - 4, top + 3)):   # scales
            c.set(x, y, P["scale_sh"])
        return Anchors(neck=(cx + 2, top + 1), shoulder=(cx - 4, top + 3), top=top, bottom=hip)


UPPER = [
    "hH...........",
    ".hHH.........",
    "..hHHSSs.....",
    "..SSSSSSSs...",
    ".SSSYeSSSSSs.",
    ".SSSSSSSSSSSn",
    "..dSSSSSSSSSs",
]


def head_origin(nx: int, ny: int, pose: Pose) -> tuple[int, int]:
    """Top-left of the head. It rears back on the attack wind-up, then lunges low to
    breathe (cancelling the body's lean so the flames have room)."""
    if pose.arm == "windup":
        return nx - 6 - pose.lean, ny - 14
    if pose.fx:
        return nx - 3 - pose.lean, ny - 11
    return nx - 3, ny - 14


def mouth(nx: int, ny: int, pose: Pose) -> tuple[int, int]:
    """Where the fire comes out."""
    x, y = head_origin(nx, ny, pose)
    return x + 11, y + 8


class WyvernHead(Head):
    """Long neck, swept-back horns, a lot of teeth. Opens wide when breathing fire."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        hx, hy = head_origin(nx, ny, pose)
        p0, p1, p2 = (nx, ny + 1), (nx + 5, ny - 5), (hx + 3, hy + 6)
        n = 10
        for i in range(n + 1):                              # neck
            x, y = bezier(p0, p1, p2, i / n)
            w = 5 if i < 4 else 4
            c.oval(round(x - w / 2), round(y - w / 2), w, w, P["scale"])
        for i in range(n + 1):                              # throat stripe, spines on the nape
            x, y = bezier(p0, p1, p2, i / n)
            c.set(round(x + 1), round(y), P["belly"])
            if i % 3 == 1:
                c.set(round(x - 2), round(y - 1), P["scale_dk"])
        eye = P["scale_sh"] if pose.blink else P["eye"]
        key = {"h": P["horn_sh"], "H": P["horn"], "S": P["scale"], "s": P["scale_sh"],
               "d": P["scale_sh"], "Y": eye, "e": P["scale_sh"] if pose.blink else INK, "n": P["scale_dk"]}
        c.stamp(hx, hy, UPPER, key)
        c.hline(hx + 4, hx + 8, hy + 3, P["scale_hi"])      # brow ridge
        if pose.fx:                                         # jaws wide open
            c.rect(hx + 4, hy + 7, 8, 2, P["mouth"])
            c.stamp(hx + 5, hy + 7, ["T.T.T"], {"T": P["horn"]})
            c.stamp(hx + 2, hy + 9, ["sssTsTs.", ".ssbbbb."], {"s": P["scale_sh"], "T": P["horn"], "b": P["belly"]})
        else:
            c.stamp(hx + 3, hy + 7, ["sssbbbbs", ".ssbbb.."], {"s": P["scale_sh"], "b": P["belly"]})
            c.hline(hx + 6, hx + 11, hy + 6, P["scale_sh"])  # closed-mouth line
            c.set(hx + 10, hy + 7, P["horn"])                # fang


# Wrist offset from the shoulder for each frame of the resting flap cycle.
FLAP = {
    "idle": [(-3, -11), (-3, -11), (-1, -11), (-1, -11)],
    "walk": [(-3, -11), (2, -10), (7, 2), (2, -10)],
    "run": [(-3, -11), (4, -9), (8, 4), (4, -9)],
}
FINGERS = ((30, 11), (70, 12), (110, 9))                    # (degrees back from the arm, length)


class WyvernArm(Arm):
    """Leathery wing: arm bones along the leading edge, three finger bones fanning back,
    membrane between. Attack: a big downbeat that throws a gust of wind (unless the
    head is busy breathing fire)."""
    species = SPECIES
    reach = 12
    fx_colors = ("#ffffff", "#c8f0ff")
    targets = {
        "crouch": ((-0.2, -1.0), (-0.5, -0.85)),             # wings cocked for the first beat
        "up": ((-0.3, -0.95), (-0.6, -0.8)),
        "reach": ((-0.3, 0.95), (-0.65, 0.75)),              # take-off downbeat
        "out": ((-0.15, -1.0), (-0.8, -0.6)),                # spread wide
        "windup": ((-0.3, -0.95), (-0.55, -0.85)),           # wings high...
        "strike": ((-0.45, 0.85), (-0.75, 0.6)),             # ...and BEAT
        "follow": ((-0.6, 0.75), (-0.85, 0.45)),
        "recover": ((-0.2, -0.95), (-0.45, -0.85)),
        "flail": ((-0.35, -0.95), (-0.55, -0.85)),           # flung up by the hit
    }

    def __init__(self, gust: bool = True):
        self.gust = gust

    def wing(self, c: Canvas, sx: int, sy: int, wx: int, wy: int, front: bool) -> None:
        mem, mem2 = (P["mem"], P["mem_sh"]) if front else (P["mem_dk"], P["mem_xdk"])
        arm, bone = (P["scale"], P["scale_sh"]) if front else (P["scale_sh"], P["scale_dk"])
        wx, wy = min(max(wx, 2), c.w - 3), min(max(wy, 3), c.h - 4)   # odd hosts: keep the wing in frame
        root = (sx - 5, sy + 5)                              # trailing edge meets the body here
        dx, dy = wx - sx, wy - sy
        d = math.hypot(dx, dy) or 1
        a = math.atan2(dy, dx)
        turn = -1 if dy <= 0 else 1                          # fingers always fan out toward the tail
        tips = [(wx + math.cos(a + turn * math.radians(deg)) * length,
                 wy + math.sin(a + turn * math.radians(deg)) * length) for deg, length in FINGERS]
        tips = [(min(max(x, 2), c.w - 3), min(max(y, 2), c.h - 3)) for x, y in tips]   # ...and fold the tips in

        def scallop(p, q, sag=0.45):                         # trailing edge sags between fingers
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            return mx + (wx - mx) * sag, my + (wy - my) * sag

        w = (wx + 0.5, wy + 0.5)
        fill_poly(c, [w, tips[0], scallop(tips[0], tips[1]), tips[1]], mem)
        fill_poly(c, [w, tips[1], scallop(tips[1], tips[2]), tips[2]], mem2)
        fill_poly(c, [w, tips[2], scallop(tips[2], root, 0.15), root, (sx + 0.5, sy + 0.5)], mem)
        for tx, ty in tips:                                  # finger bones
            c.line(wx, wy, round(tx), round(ty), bone)
        ex, ey = round(sx + dx * 0.45 - dy / d * 1.5), round(sy + dy * 0.45 + dx / d * 1.5)
        c.stroke(sx, sy, ex, ey, arm, 3)
        c.stroke(ex, ey, wx, wy, arm, 2)
        c.set(wx + 1, wy - 1, P["claw"])                     # thumb claw
        if front:
            c.set(ex, ey - 1, P["scale_hi"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        dx, dy = FLAP.get(pose.anim, FLAP["walk"])[pose.frame % 4]
        if not front:                                        # far wing trails a little behind
            dx, dy = dx - 3, dy + 1
        self.wing(c, sx, sy, sx + dx, sy + dy, front)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        self.wing(c, sx, sy, hx, hy, front)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if not self.gust:
            return
        main, accent = self.fx_colors
        x0, y0 = sx + 7, sy + 1                              # the gust blasts out in front of the body
        if pose.fx == "swoosh":
            for k, (dy, length) in enumerate(((0, 6), (3, 8), (6, 5))):
                x = x0 + k % 2
                fx.hline(x, x + length, y0 + dy, accent if k == 1 else main)
                fx.set(x + length + 1, y0 + dy - 1, main)
        else:                                                # curling wind further out
            for x, y in ((x0 + 6, y0), (x0 + 9, y0 + 4)):
                fx.stamp(x, y, [".a.", "a.a", ".aa"], {"a": main})


def flame(c: Canvas, mx: int, my: int, end: int, flare: float, frame: int) -> None:
    """A jet of fire from the mouth to x=end: thin at the lips, billowing at the far end.
    Red rim, orange body, yellow core."""
    puffs = []
    for x in range(mx, end + 1):
        t = (x - mx) / max(1, end - mx)
        ry = 1 + flare * t * t
        y = my + 1.5 * t + (wave(frame + x, 4, 0.5) if t > 0.3 else 0)
        puffs.append((x, y, ry))
    for col, shrink in ((P["fire_r"], 0), (P["fire_o"], 0.9), (P["fire_y"], 1.9), (P["fire_w"], 3.0)):
        for x, y, ry in puffs:
            r = ry - shrink
            if r > 0.3:
                rx = min(r, end - x + 0.5)                   # stay inside the frame
                c.oval(round(x - rx), round(y - r), max(1, round(2 * rx)), max(1, round(2 * r)), col)
    for k in range(3):                                       # stray embers
        c.set(mx + 3 + 3 * k + frame % 2, round(my - 2 - k - (k + frame) % 2), P["fire_y"])


def fire_breath(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """Decoration: the wing genes don't know where the head is, so the fire lives here."""
    nx, ny = info["anchors"].neck
    mx, my = mouth(nx, ny, pose)
    fire = Canvas(out.w, out.h)
    if pose.fx == "swoosh":
        flame(fire, mx, my, 45, 3.0, pose.frame)
    elif pose.fx == "impact":
        flame(fire, mx, my, 45, 4.5, pose.frame)
    elif pose.arm == "windup":                               # deep breath: embers glowing at the lips
        fire.set(mx, my - 1, P["fire_o"])
        fire.set(mx + 1, my - 2, P["fire_y"])
    elif pose.arm == "recover":                              # smoke rings drifting off the snout
        fire.stamp(mx + 1, my - 5, [".ss.", "s..s", ".sS."], {"s": P["smoke"], "S": P["smoke_hi"]})
        fire.stamp(mx + 5, my - 9, [".s.", "s.s", ".s."], {"s": P["smoke"]})
    else:
        return
    fire.outline(OUTLINE)
    layers["fx"].paste(fire)


GENES = dict(legs=WyvernLegs(), torso=WyvernTorso(), head=WyvernHead(), arm=WyvernArm())


def build() -> BodyPlan:
    g = GENES
    wings = WyvernArm(gust=False)                            # the full wyvern breathes fire instead
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=wings, back_arm=wings,
                    decorations=[fire_breath])
