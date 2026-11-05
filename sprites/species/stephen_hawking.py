"""Stephen Hawking: the lab's resident genius. Tweed jacket, big square glasses, a
motorized chair with a speech computer, and a working knowledge of black holes.
Mostly theoretical. Mostly."""

import math

from ..canvas import Canvas
from ..font import draw_text, text_width
from ..palette import INK, OUTLINE, STEPHEN_HAWKING as P
from ..rig import GROUND, SIZE, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow
from .succubus import fill_tri

SPECIES = "stephen_hawking"
PREFIX, SUFFIX = "Hawk", "king"


# -- the chair -------------------------------------------------------------------

# Wheelie angle (radians, front up) per frame.
WHEELIE = {"jump": (0.0, 0.2, 0.3, 0.16)}


class HawkingChair(Legs):
    """The motorized chair, standing in for legs: big rear wheel, little front caster,
    battery box, footrest, headrest, joystick, and the speech computer on its arm.
    His own legs come along too, seated. Jumping is a wheelie."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        floor = min(GROUND, hip + self.length)                # lifts off with the body when airborne
        seat = floor - self.length
        tilt = WHEELIE.get(pose.anim, (0.0,) * 6)[pose.frame]
        px, py = cx - 5, floor - 6                            # pivot: the big wheel's axle
        ca, sa = math.cos(tilt), math.sin(tilt)

        def T(x: float, y: float) -> tuple[int, int]:
            dx, dy = x - px, y - py
            return round(px + dx * ca + dy * sa), round(py - dx * sa + dy * ca)

        def quad(x0: int, y0: int, x1: int, y1: int, col: str) -> None:
            a, b, d, e = T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)
            fill_tri(c, a, b, d, col)
            fill_tri(c, a, d, e, col)

        # backrest, push handle and headrest
        c.stroke(*T(cx - 6, seat), *T(cx - 6, seat - 11), P["chair"], 2)
        c.line(*T(cx - 7, seat - 11), *T(cx - 9, seat - 11), P["metal"])
        c.line(*T(cx - 6, seat - 11), *T(cx - 6, seat - 15), P["metal"])
        quad(cx - 8, seat - 19, cx - 6, seat - 14, P["chair"])
        c.line(*T(cx - 6, seat - 19), *T(cx - 6, seat - 15), P["chair_hi"])
        # battery box under the seat, with a charge light
        quad(cx - 4, floor - 10, cx + 4, floor - 5, P["chair_sh"])
        c.line(*T(cx - 3, floor - 9), *T(cx + 3, floor - 9), P["chair"])
        c.set(*T(cx + 3, floor - 7), P["led"] if pose.frame % 2 or pose.anim != "idle" else P["chair"])
        # front caster
        c.line(*T(cx + 3, floor - 5), *T(cx + 3, floor - 3), P["metal"])
        caster = T(cx + 3, floor - 2)
        c.oval(caster[0] - 2, caster[1] - 2, 5, 5, P["tire"])
        c.set(*caster, P["metal_hi"])
        # seat cushion
        quad(cx - 6, seat, cx + 4, seat + 1, P["chair"])
        c.line(*T(cx - 6, seat), *T(cx + 4, seat), P["chair_hi"])
        # footrest bracket and plate
        c.line(*T(cx + 4, seat + 1), *T(cx + 8, floor - 3), P["metal"])
        c.line(*T(cx + 7, floor - 3), *T(cx + 11, floor - 3), P["metal_hi"])
        # his legs: thighs along the cushion, shins down to the footrest
        knee = T(cx + 7, seat - 1)
        ankle = T(cx + 8, floor - 6)
        c.stroke(cx, hip - 1, *knee, P["pants"], 3)
        c.stroke(*knee, *ankle, P["pants"], 3)
        c.line(knee[0] + 1, knee[1] - 1, ankle[0] + 1, ankle[1], P["pants_sh"])
        sh = T(cx + 8, floor - 5)
        c.rect(sh[0] - 1, sh[1], 4, 2, P["shoe"])
        c.set(sh[0] + 2, sh[1], P["shoe_hi"])
        # the big rear wheel, spokes turning as he drives
        self.wheel(c, *T(cx - 5, floor - 6), pose)
        # armrest with the joystick, and the speech computer on its swing arm
        quad(cx - 2, seat - 4, cx + 6, seat - 3, P["chair"])
        c.line(*T(cx - 2, seat - 4), *T(cx + 6, seat - 4), P["chair_hi"])
        c.line(*T(cx + 5, seat - 2), *T(cx + 5, seat + 1), P["metal"])
        push = {"walk": 1, "run": 1}.get(pose.anim, 0)       # stick pushed forward to drive
        c.line(*T(cx + 4, seat - 5), *T(cx + 4 + push, seat - 6), P["metal"])
        c.set(*T(cx + 4 + push, seat - 7), INK)               # knob
        c.line(*T(cx + 6, seat - 3), *T(cx + 8, seat - 4), P["metal"])
        self.screen(c, *T(cx + 8, seat - 7), pose)

    def wheel(self, c: Canvas, wx: int, wy: int, pose: Pose) -> None:
        c.oval(wx - 6, wy - 6, 13, 13, P["tire"])
        c.oval(wx - 5, wy - 5, 11, 11, P["rim"])
        c.oval(wx - 4, wy - 4, 9, 9, P["spoke_bg"])
        step = {"walk": 15, "run": 30}.get(pose.anim, 0)      # six spokes: these loop seamlessly
        a0 = math.radians(step * pose.frame)
        for k in range(3):
            a = a0 + k * math.pi / 3
            dx, dy = round(math.cos(a) * 4), round(math.sin(a) * 4)
            c.line(wx - dx, wy - dy, wx + dx, wy + dy, P["metal"])
        c.rect(wx - 1, wy - 1, 3, 3, P["metal_hi"])
        c.set(wx, wy, P["metal"])
        spin = math.radians(90 * pose.frame if step else 0) - math.pi / 4
        c.set(wx + round(math.cos(spin) * 5), wy + round(math.sin(spin) * 5), P["reflector"])
        c.set(wx - 4, wy - 4, P["rim"])                        # rim glint
        if pose.anim == "run":                                # dust kicked up behind
            d = 2 + pose.frame % 2
            c.rect(wx - 7 - d, wy + 4 - d % 2, 2, 2, P["debris"])

    def screen(self, c: Canvas, x: int, y: int, pose: Pose) -> None:
        """The speech computer: a little green screen, typing away."""
        c.rect(x, y, 5, 5, P["frame"])
        lit = pose.anim == "attack" and 0 < pose.frame < 3
        c.rect(x + 1, y + 1, 3, 3, P["screen_hi"] if lit else P["screen"])
        if not lit:
            n = (pose.frame % 3) + 1                          # words appear one by one
            for i in range(n):
                c.set(x + 1 + i % 3, y + 1 + i // 3 * 2, P["screen_txt"])
            c.set(x + 1, y + 3, P["screen_hi"])


# -- the man ---------------------------------------------------------------------

class HawkingTorso(Torso):
    """Seated: tweed jacket, open shirt collar, a knitted tie."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 10
        cx -= {"jump": (0, 1, 1, 1)}.get(pose.anim, (0,) * 6)[pose.frame]   # leans back into the wheelie
        c.rect(cx - 3, top, 6, 1, P["tweed"])
        c.rect(cx - 4, top + 1, 8, 10, P["tweed"])
        c.vline(cx - 4, top + 1, hip, P["tweed_sh"])
        c.vline(cx + 3, top + 3, hip - 1, P["tweed_hi"])
        for y in range(top + 2, hip, 2):                      # herringbone flecks
            c.set(cx - 2 + (y // 2) % 3, y, P["fleck"])
        c.stamp(cx, top, ["SSSs", ".STs", ".ST.", "..T.", "..T."],     # shirt collar and tie
                {"S": P["shirt"], "s": P["shirt_sh"], "T": P["tie"]})
        c.line(cx, top + 2, cx + 2, top + 6, P["tweed_sh"])   # lapel
        c.hline(cx - 4, cx + 3, hip, P["tweed_sh"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


# Side-parted hair, big square glasses, a sly smile. The head tips gently forward.
HEAD = [
    "...hhhhh.....",
    "..hHHHHHhh...",
    ".hHHHHHHHHh..",
    ".HHHHHHHHHHh.",
    "HHHHHHHHHHHS.",
    "HHHHHHHHSSSS.",
    "HHHHHHSGGGGG.",
    "HHHTTTTGLLLG.",
    "HHHEESSGLELGn",
    "HHsEESSGGGGGn",
    ".HsSSSSSMSSS.",
    ".ssSSSSSSmmS.",
    "..sSSSSSSSS..",
    "...ssSSSSS...",
]


class HawkingHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        x0, y0 = nx - 5, ny - 13
        key = {
            "h": P["hair_hi"], "H": P["hair"], "S": P["skin"], "s": P["skin_sh"], "n": P["skin"],
            "G": P["frame"], "T": P["frame"], "L": P["lens"], "E": P["skin_sh"],
            "M": P["mouth"], "m": P["mouth"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 9, y0 + 8, P["lens"] if pose.blink else INK)    # eye behind the lens
        c.set(x0 + 10, y0 + 7, P["glint"])
        if pose.anim == "jump" and pose.frame:                    # wheeee: a big grin
            c.hline(x0 + 8, x0 + 11, y0 + 11, P["mouth"])
            c.hline(x0 + 9, x0 + 10, y0 + 11, P["teeth"])
            c.hline(x0 + 9, x0 + 10, y0 + 12, P["mouth"])


class HawkingArm(Arm):
    """Tweed sleeve. At rest the hand stays on the joystick. Attack: he holds out a hand
    and a tiny black hole opens in front of it, swallowing whatever's nearby."""
    species = SPECIES
    reach = 8
    fx_colors = (P["disk"], P["disk_hi"])
    targets = {
        "windup": ((0.6, -0.1), (0.5, 0.75)),               # hand lifts off the joystick...
        "strike": ((1.0, -0.15), (0.5, 0.75)),              # ...then an open palm: there
        "follow": ((0.75, 0.25), (0.5, 0.75)),              # and back down, to watch it work
        "recover": ((0.75, 0.5), (0.5, 0.75)),
        "flail": ((0.2, 0.9), (0.4, 0.8)),                  # knocked off the joystick
    }

    def hand(self, c: Canvas, hx: int, hy: int, front: bool, open_: bool = False) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        c.rect(hx, hy, 2, 2, skin)
        if open_:
            c.vline(hx + 2, hy - 1, hy + 1, skin)               # palm out, fingers up
            c.set(hx + 1, hy + 1, P["skin_sh"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        sleeve = P["tweed"] if front else P["tweed_sh"]
        drive = 1 if front and pose.anim in ("walk", "run") else 0
        ex, ey = sx - (0 if front else 1), sy + 5
        hx, hy = sx + 5 + drive - (0 if front else 1), sy + 3
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx - 1, hy + 1, sleeve, 2)
        c.set(hx - 1, hy + 1, P["shirt"] if front else P["shirt_sh"])    # cuff
        self.hand(c, hx, hy, front)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        if pose.anim == "jump":                                # both hands stay on the chair for the wheelie
            self.draw_swing(c, sx, sy, pose, front)
            return
        sleeve = P["tweed"] if front else P["tweed_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx - 1, hy, sleeve, 2)
        self.hand(c, hx, hy, front, front and mode in ("strike", "follow"))

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                                # the singularity forms, matter spiralling in
            x, y = min(hx + 8, SIZE - 9), hy
            for k in (0, 1):                                   # two arms, wound tight around the middle
                pts = []
                for i in range(9):
                    t = i / 8
                    a = k * math.pi - t * 3.4
                    r = 1.5 + 4 * t
                    pts.append((x + round(math.cos(a) * r), y + round(math.sin(a) * r * 0.7)))
                for i, (a, b) in enumerate(zip(pts, pts[1:])):
                    fx.line(*a, *b, P["disk_hi"] if i < 3 else P["disk"])
            fx.oval(x - 1, y - 1, 3, 3, INK)
        else:
            black_hole(fx, min(hx + 10, SIZE - 10), hy, pose)


def black_hole(fx: Canvas, x: int, y: int, pose: Pose) -> None:
    """A miniature black hole: the far side of the disk bent up over the top by gravity,
    a black core, the near side of the disk across the front, debris streaking in."""
    rx, ry = 6, 2
    for dx in range(-rx, rx + 1):                              # far half of the disk
        h = ry * math.sqrt(max(0.0, 1 - (dx / rx) ** 2))
        fx.set(x + dx, y - round(h), P["disk"])
    for dx in range(-3, 4):                                    # lensed light arcing over the top
        fx.set(x + dx, y - 3 - round(math.sqrt(9 - dx * dx) * 0.6), P["lensing"] if abs(dx) > 1 else P["disk_hi"])
    fx.oval(x - 2, y - 2, 5, 5, INK)                           # the event horizon
    for dx in range(-rx, rx + 1):                              # near half of the disk, hot in the middle
        h = ry * math.sqrt(max(0.0, 1 - (dx / rx) ** 2))
        col = P["disk_w"] if abs(dx) <= 1 else P["disk_hi"] if abs(dx) <= 3 else P["disk"]
        fx.set(x + dx, y + round(h) - 1, col)
        fx.set(x + dx, y, col if abs(dx) > 2 else fx.get(x + dx, y))
    for a, r in ((0.5, 9), (2.3, 8), (3.6, 9), (5.1, 8)):    # debris pulled in, each with a streak
        bx, by = x + round(math.cos(a) * r), y + round(math.sin(a) * r * 0.7)
        tx, ty = x + round(math.cos(a - 0.35) * (r - 3)), y + round(math.sin(a - 0.35) * (r - 3) * 0.7)
        if 2 <= bx <= SIZE - 3 and 2 <= by <= GROUND:
            fx.line(bx, by, tx, ty, P["debris"])
            fx.set(bx, by, "#ffffff")


# -- the speech bubble -----------------------------------------------------------

EQUALS = ["...", "###", "...", "###", "..."]


def say(c: Canvas, x: int, y: int, text: str) -> None:
    """draw_text, plus an '=' sign (the house font doesn't have one)."""
    for ch in text:
        if ch == "=":
            c.stamp(x, y, EQUALS, {"#": INK})
            x += 4
        else:
            draw_text(c, x, y, ch, INK)
            x += text_width(ch) + 1


def speech(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """The speech computer gets the last word while he winds up the black hole."""
    if pose.anim != "attack" or pose.frame > 2:
        return
    text = "E=MC2"
    w, h = sum(4 if ch == "=" else text_width(ch) + 1 for ch in text) + 3, 9
    nx, ny = info["anchors"].neck
    x, y = max(2, min(SIZE - 3 - w, nx - 9)), max(1, ny - 24)
    out.rect(x + 1, y, w - 2, h, OUTLINE)                       # rounded corners
    out.rect(x, y + 1, w, h - 2, OUTLINE)
    out.rect(x + 1, y + 1, w - 2, h - 2, P["bubble"])
    say(out, x + 2, y + 2, text)
    tx = nx - 3                                                # tail points down at his head
    out.stamp(tx, y + h - 1, ["KWWK", ".KWK", "..K."], {"W": P["bubble"], "K": OUTLINE})


GENES = dict(legs=HawkingChair(), torso=HawkingTorso(), head=HawkingHead(), arm=HawkingArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"],
                    decorations=[speech])
