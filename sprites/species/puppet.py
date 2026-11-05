"""Puppet: a wooden marionette on strings. Ball joints, painted cheeks, a nutcracker
jaw that clacks. Nobody has ever seen who's holding the bar."""

import math

from ..canvas import Canvas, line_points, wave
from ..palette import INK, OUTLINE, PUPPET as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "puppet"
PREFIX, SUFFIX = "Pup", "pet"


def dowel(c: Canvas, x0: int, y0: int, x1: int, y1: int, front: bool) -> None:
    """A turned-wood limb segment, 2px thick: lit on the front, a grain streak down the back."""
    wood, sh = (P["wood"], P["wood_sh"]) if front else (P["wood_sh"], P["wood_dk"])
    c.stroke(x0, y0, x1, y1, wood, 2)
    steep = abs(y1 - y0) >= abs(x1 - x0)
    for i, (x, y) in enumerate(line_points(x0, y0, x1, y1)):
        if steep:
            c.set(x, y, sh if i % 4 != 2 else wood)           # back edge, with a knot of grain now and then
            if front and i % 4 == 1:
                c.set(x + 1, y, P["wood_hi"])
        else:
            c.set(x, y + 1, sh)


def ball(c: Canvas, x: int, y: int, front: bool) -> None:
    """A round ball joint centred on (x, y): darker than the limbs so it reads as a separate part."""
    c.stamp(x - 1, y - 1, [".B.", "BBb", ".b."], {"B": P["wood_sh"] if front else P["wood_dk"],
                                                   "b": P["wood_dk"]})
    if front:
        c.set(x - 1, y, P["wood"])


def knee_point(hx: int, hy: int, ax: int, ay: int, thigh: float, shin: float) -> tuple[int, int]:
    """Two-bone IK: where the knee goes so the leg reaches from hip to ankle, bending forward."""
    dx, dy = ax - hx, ay - hy
    d = math.hypot(dx, dy) or 1
    d2 = min(d, thigh + shin - 0.01)
    a = (thigh * thigh - shin * shin + d2 * d2) / (2 * d2)
    h = math.sqrt(max(0.0, thigh * thigh - a * a))
    ux, uy = dx / d, dy / d
    mx, my = hx + ux * a, hy + uy * a
    px, py = -uy, ux                                          # perpendicular...
    if px < 0:                                                # ...pointing forward (knees bend that way)
        px, py = -px, -py
    return round(mx + px * h), round(my + py * h)


THIGH, SHIN = 5, 4.6


class PuppetLegs(Legs):
    """Peg legs with ball-jointed knees. Lifted feet go limp, toes pointing at the floor."""
    species = SPECIES
    length = 11

    def leg(self, c: Canvas, hx: int, hy: int, kx: int, ky: int, ax: int, ay: int, front: bool, ground: int) -> None:
        dowel(c, hx, hy, kx, ky, front)
        dowel(c, kx, ky, ax, ay, front)
        c.hline(ax, ax + 1, ay, P["trim"] if front else P["trim_sh"])      # painted sock
        shoe, shoe_hi = (P["shoe"], P["shoe_hi"]) if front else (P["shoe"], P["shoe"])
        if ay + 2 >= ground:                                  # planted: a flat wooden clog
            c.rect(ax - 1, ay + 1, 5, 2, shoe)
            c.set(ax + 2, ay + 1, shoe_hi)
        else:                                                 # dangling: toe droops
            c.stamp(ax - 1, ay + 1, ["SSS.", ".SSS", "..Sh"], {"S": shoe, "h": shoe_hi})
        ball(c, kx, ky, front)

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        hx = cx - 1
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            lift = 0 if front else pose.lift
            if pose.tuck:                                     # airborne: knees yanked up, shins dangle
                a = 0.35 + 0.2 * pose.tuck + (0.25 if front else 0)
                kx, ky = round(hx + math.sin(a) * THIGH), round(hip + math.cos(a) * THIGH)
                ax, ay = kx - 1 + (pose.frame % 2), min(round(ky + SHIN), ground - 2)
            elif lift:                                        # passing: the knee string pulls, foot hangs
                a = 0.55 + 0.25 * lift
                kx, ky = round(hx + math.sin(a) * THIGH), round(hip + math.cos(a) * THIGH)
                ax, ay = kx - 1, min(round(ky + SHIN), ground - 3)
            else:                                             # planted
                ax, ay = hx + 3 * s + (1 if front else 0), ground - 2
                kx, ky = knee_point(hx, hip, ax, ay, THIGH, SHIN)
            self.leg(c, hx, hip, kx, ky, ax, ay, front, ground)
        ball(c, hx, hip, True)                                # hip joint (the shorts usually hide it)


class PuppetTorso(Torso):
    """Two wooden blocks, chest and pelvis, pinned at the waist. Painted jacket and shorts."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 10
        sway = 1 if pose.anim in ("walk", "run") and pose.frame % 2 else 0   # the chest block rocks on its pin
        # pelvis block: painted shorts
        c.rect(cx - 3, hip - 2, 7, 3, P["pants"])
        c.vline(cx - 3, hip - 2, hip, P["pants_sh"])
        c.hline(cx - 3, cx + 3, hip, P["pants_sh"])
        # waist pin: bare wood showing between the blocks
        c.hline(cx - 2, cx + 2, hip - 3, P["wood_sh"])
        c.set(cx, hip - 3, P["wood_dk"])
        # chest block: red jacket with brass buttons and a white collar
        x0 = cx - 4 + sway
        c.rect(x0 + 1, top, 6, 1, P["coat"])
        c.rect(x0, top + 1, 8, 6, P["coat"])
        c.vline(x0, top + 1, top + 6, P["coat_sh"])
        c.vline(x0 + 7, top + 2, top + 6, P["coat_hi"])
        c.hline(x0 + 1, x0 + 6, top + 6, P["coat_sh"])
        c.set(x0 + 2, top + 3, P["coat_sh"])                  # wood grain under the paint
        c.set(x0 + 3, top + 4, P["coat_sh"])
        c.hline(x0 + 3, x0 + 7, top, P["trim"])              # collar
        c.set(x0 + 6, top + 1, P["trim"])
        c.set(x0 + 7, top + 1, P["trim_sh"])
        for y in (top + 2, top + 4):                          # buttons
            c.set(x0 + 6, y, P["button"])
        return Anchors(neck=(cx + 1 + sway, top), shoulder=(cx - 1 + sway, top + 2), top=top, bottom=hip)


# Painted hair, a big painted eye, a round knob nose and a rosy cheek. The jaw is separate.
HEAD = [
    "....hhhhh...",
    "..hhHHHHHhh.",
    ".hHHHHHHHHw.",
    ".HHHHHHHWWWw",
    "HHHHHHHWWWWW",
    "HHHHHHWWWbbW",
    "HHHHHWWWWEEW",
    "sHHHWWWWWEPWn",
    "sHHWWWWWWWWWn",
    ".sHWWWWRRWWW.",
    ".ssWWWWRRWWW.",
]
JAW = [
    "sWWWWWW",
    ".sWWWWW",
]

# How far the jaw hangs open, per frame. Missing anims keep it shut.
JAW_OPEN = {
    "idle": (0, 0, 1, 0),
    "walk": (0, 1, 0, 1),
    "run": (1, 0, 1, 0),
    "jump": (0, 2, 2, 1),
    "attack": (1, 2, 0, 0),        # snaps shut on the impact frame: CLACK
    "hurt": (2, 2),
    "death": (2,),
}
# Little lags and nods so the head never quite moves with the body.
NOD = {
    "idle": ((0, 0), (0, 0), (0, 1), (0, 0)),
    "walk": ((0, 1), (1, 0), (0, 1), (-1, 0)),
    "run": ((1, 1), (0, 0), (1, 1), (0, 0)),
    "jump": ((1, 1), (-1, 0), (0, 0), (0, 0)),
}


class PuppetHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        dx, dy = NOD.get(pose.anim, ((0, 0),) * 4)[pose.frame % 4]
        c.rect(nx - 1, ny - 2, 2, 3, P["wood_sh"])            # neck peg
        x0, y0 = nx - 6 + dx, ny - 13 + dy
        opens = JAW_OPEN.get(pose.anim, (0,))
        o = opens[min(pose.frame, len(opens) - 1)]
        jx, jy = x0 + 5, y0 + 12 + o
        c.rect(jx + 2, y0 + 11, 5, o + 1, P["mouth"])          # mouth slot (a gap when the jaw drops)
        if o:
            c.hline(jx + 3, jx + 5, y0 + 11, P["teeth"])      # painted teeth
            c.set(jx + 1, y0 + 11, P["wood_sh"])
        c.stamp(jx, jy, JAW, {"W": P["wood"], "s": P["wood_sh"]})
        c.set(jx + 6, jy, P["wood_hi"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "W": P["wood"], "w": P["wood_hi"], "s": P["wood_sh"],
            "E": P["wood_sh"] if pose.blink else P["eye_w"],
            "P": P["wood_sh"] if pose.blink else INK, "n": P["wood"],
            "R": P["cheek"], "r": P["cheek_hi"], "b": P["hair"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 8, y0 + 9, P["cheek_hi"])
        c.vline(jx, y0 + 11, jy, P["wood_dk"])                # the hinge slot down the back of the jaw
        c.set(x0 + 5, y0 - 1, P["wood_sh"])                   # screw eye on top of the head
        c.set(x0 + 5, y0 - 2, P["eyelet"])


class PuppetArm(Arm):
    """Bare wooden arm, ball-jointed at shoulder and elbow, a mitten hand with a screw eye for the string.
    Attack: the string yanks the arm straight out, stiff as a plank. CLACK."""
    species = SPECIES
    reach = 9
    fx_colors = ("#ffffff", P["wood_hi"])
    targets = {
        "windup": ((-0.5, -0.6), (-0.4, 0.85)),              # yanked up and back by the string...
        "strike": ((1.0, -0.1), (-0.7, 0.55)),               # ...then snapped out dead straight
        "follow": ((1.0, 0.1), (-0.6, 0.7)),
        "flail": ((-0.4, -0.8), (-0.8, -0.5)),              # arms fly up when the strings go slack
    }

    def limb(self, c: Canvas, sx: int, sy: int, ex: int, ey: int, hx: int, hy: int, front: bool, droop: int) -> None:
        dowel(c, sx, sy, ex, ey, front)
        dowel(c, ex, ey, hx, hy, front)
        # mitten hand: hangs limp from the wrist unless the string is pulling it
        hand = P["wood"] if front else P["wood_sh"]
        c.rect(hx, hy, 2, 2 + droop, hand)
        if front:
            c.set(hx + 1, hy + 1 + droop, P["wood_sh"])
        c.set(hx, hy, P["eyelet"])
        ball(c, ex, ey, front)
        ball(c, sx, sy, front)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        d = pose.swing if front else -pose.swing
        jerk = -1 if pose.anim in ("walk", "run") and pose.frame % 2 else 0   # string tugs on the pass frames
        if front:                                             # forearm held out by the string
            ex, ey = sx + 1 + d, sy + 5
            hx, hy = sx + 7 + 2 * d, sy + 4 + jerk - (pose.bob > 0)
        else:
            ex, ey = sx - 1 + d, sy + 5
            hx, hy = sx + 2 + 2 * d, sy + 5 + jerk
        self.limb(c, sx, sy, ex, ey, hx, hy, front, 1)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        stiff = front and mode in ("strike", "follow")
        ex, ey = elbow(sx, sy, hx, hy, 0 if stiff else 2.5)   # dead straight on the punch
        self.limb(c, sx, sy, ex, ey, hx, hy, front, 0 if stiff else 1)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        x, y = hx + 4, hy
        if pose.fx == "swoosh":                               # stiff chop lines above and below the fist
            for dy, x0 in ((-3, hx - 4), (4, hx - 5)):
                fx.hline(x0, hx - 1, hy + dy, "#ffffff")
            fx.set(hx + 3, hy - 2, P["wood_hi"])
            fx.set(hx + 3, hy + 3, P["wood_hi"])
        else:                                                 # CLACK: a burst, and splinters flying
            star(fx, x, y, "#ffffff", P["button"], r=3)
            for ddx, ddy, col in ((4, -4, P["wood"]), (5, 2, P["wood_sh"]), (1, -6, P["wood_hi"]),
                                  (2, 5, P["wood"]), (6, -1, P["wood_hi"])):
                fx.set(x + ddx, y + ddy, col)
                fx.set(x + ddx + (1 if ddx > 3 else 0), y + ddy + (1 if ddy > 0 else -1), col)


# -- the control bar and its strings (painted after compositing, so no thick outlines) --

BAR = 11            # half-length of the control bar


def _thread(out: Canvas, pts: list[tuple[int, int]]) -> None:
    """A 1px string. It passes behind the puppet, so it only shows against empty space."""
    for x, y in pts:
        if out.get(x, y) is None:
            out.set(x, y, P["string"])


def _curve(x0: int, y0: int, x1: int, y1: int, sag: float) -> list[tuple[int, int]]:
    """Points along a string from (x0, y0) to (x1, y1), bowed sideways by `sag` px."""
    ctrl, n = [], 6
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t - sag * 4 * t * (1 - t)
        y = y0 + (y1 - y0) * t + abs(sag) * 1.5 * t * (1 - t)
        ctrl.append((round(x), round(y)))
    pts = []
    for a, b in zip(ctrl, ctrl[1:]):
        pts += line_points(*a, *b)
    return list(dict.fromkeys(pts))


def strings(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """The wooden control bar at the top of the frame, with a string down to every screw eye.
    The bar rocks as the puppet walks; the strings go slack when he's hit, and snap when he dies."""
    if pose.melt:
        return
    knots = [(x, y) for y in range(out.h) for x in range(out.w) if out.get(x, y) == P["eyelet"]]
    nx, _ = info["anchors"].neck
    bx, by = nx, 4
    rock = {"walk": wave(pose.frame, pose.n), "run": wave(pose.frame, pose.n), "attack": (0, 1, 1, 0)[pose.frame],
            "hurt": -1}.get(pose.anim, 0)
    hurt, dead = pose.anim == "hurt", pose.anim == "death"
    if dead:
        rock = -2

    def bar_y(x: int) -> int:
        return by - round(rock * (x - bx) / BAR)

    for x, y in knots:
        tx = max(bx - BAR + 1, min(bx + BAR - 1, round(bx + (x - bx) * 1.8)))
        ty = bar_y(tx) + 2
        if dead:                                              # snapped: loose ends curl off the bar and the puppet
            _thread(out, _curve(tx, ty, tx - 2, ty + 4, 1))
            _thread(out, _curve(x, y - 1, x - 2, y - 4, -1))
        else:
            _thread(out, _curve(tx, ty, x, y - 1, 3 if hurt else 0))
    bar = Canvas(out.w, out.h)
    for x in range(bx - BAR, bx + BAR + 1):
        y = bar_y(x)
        bar.set(x, y, P["bar_hi"])
        bar.set(x, y + 1, P["bar"] if abs(x - bx) < BAR else P["bar_sh"])
    bar.rect(bx - 1, bar_y(bx) - 1, 3, 3, P["bar"])           # cross-piece, seen end-on
    bar.set(bx - 1, bar_y(bx) - 1, P["bar_hi"])
    bar.set(bx + 1, bar_y(bx) + 1, P["bar_sh"])
    bar.outline(OUTLINE)
    out.paste(bar)


GENES = dict(legs=PuppetLegs(), torso=PuppetTorso(), head=PuppetHead(), arm=PuppetArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"],
                    decorations=[strings])
