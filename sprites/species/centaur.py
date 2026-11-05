"""Centaur: half hero, half dappled-grey horse. Laurel wreath, wild hair, spear.
Four hooves, zero chill."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, CENTAUR as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "centaur"
PREFIX, SUFFIX = "Centa", "taur"


def knee(tx: int, ty: int, hx: int, hy: int, seg: float, forward: bool) -> tuple[int, int]:
    """Two-bone joint between top and hoof: forelegs bend the knee forward, hind legs the hock back."""
    dx, dy = hx - tx, hy - ty
    d = math.hypot(dx, dy) or 1
    off = math.sqrt(max(0.0, seg * seg - d * d / 4))
    px, py = -dy / d, dx / d
    if (px > 0) != forward:
        px, py = -px, -py
    return round(tx + dx / 2 + px * off), round(ty + dy / 2 + py * off)


# Hoof placement per leg, as (dx, lift), for poses the biped swing/lift can't describe.
# Leg order: near fore, far fore, near hind, far hind.
GALLOP = [
    [(5, 2), (3, 1), (-5, 1), (-4, 2)],     # stretched out, all four off the ground
    [(1, 0), (3, 0), (2, 3), (0, 2)],       # front hooves land, hind legs swing under
    [(-1, 4), (-2, 3), (3, 0), (1, 0)],     # bunched up: hind legs planted, forelegs folded
    [(3, 2), (2, 1), (-2, 0), (-4, 1)],     # hind legs shove off, forelegs reach
]
JUMP = {
    0: [(2, 0), (0, 0), (-2, 0), (-3, 0)],  # crouch
    1: [(1, 5), (0, 4), (-5, 0), (-6, 1)],  # forelegs fold, hind legs shove
    2: [(0, 3), (-1, 2), (2, 2), (1, 1)],   # apex: all four folded up under the barrel
    3: [(4, 0), (3, 1), (-3, 1), (-4, 2)],  # forelegs reach for the landing
}


SINK = 3      # the rider's hip sits this far below the horse's back, so tall torsos still fit the frame


class CentaurLegs(Legs):
    """The whole horse: barrel, four legs, tail. The rider's waist sits on its withers."""
    species = SPECIES
    length = 16

    def gait(self, pose: Pose) -> list[tuple[int, int]]:
        if pose.anim == "run":
            return GALLOP[pose.frame % 4]
        if pose.anim == "jump":
            return JUMP[pose.frame]
        s = 3 * pose.swing                                   # walk: diagonal pairs move together
        a_lift = pose.lift * 3 if pose.frame % 4 == 3 else 0
        b_lift = pose.lift * 3 if pose.frame % 4 == 1 else 0
        return [(s, a_lift), (-s, b_lift), (-s, b_lift), (s, a_lift)]

    def leg(self, c: Canvas, tx: int, ty: int, hx: int, ground: int, lift: int, fore: bool, near: bool) -> None:
        coat = P["coat"] if near else P["coat_dk"]
        lower = P["coat_sh"] if near else P["leg_far"]
        bottom = ground - lift
        fx, fy = hx, bottom - 2                              # fetlock
        kx, ky = knee(tx, ty, fx, fy, 5.6 if fore else 6.2, forward=fore)
        if not fore:
            c.oval(tx - 3, ty - 3, 6, 6, coat)               # gaskin muscle
        c.stroke(tx, ty, kx, ky, coat, 3)
        c.stroke(kx, ky, fx, fy, lower, 2)
        c.rect(fx, bottom - 1, 3, 2, P["hoof"])
        if near:
            c.set(fx + 2, bottom - 1, P["hoof_hi"])
            c.set(kx + (1 if fore else 0), ky, P["coat_hi"])

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        g = self.gait(pose)
        back = hip - SINK                                    # the horse's back line
        fore_x, hind_x, top = cx + 1, cx - 12, back + 5
        # far side legs first
        self.leg(c, fore_x - 2, top, fore_x - 2 + g[1][0], ground, g[1][1], True, False)
        self.leg(c, hind_x - 2, top, hind_x - 2 + g[3][0], ground, g[3][1], False, False)
        self.tail(c, cx, back, pose)
        # barrel: rump, belly, chest
        c.oval(cx - 16, back - 2, 9, 8, P["coat"])
        c.oval(cx - 14, back - 1, 19, 8, P["coat"])
        c.oval(cx - 2, back - 1, 8, 8, P["coat"])
        for x in range(cx - 16, cx + 6):                     # belly shadow, back highlight
            span = [y for y in range(back - 3, back + 8) if c.get(x, y) == P["coat"]]
            if span:
                c.set(x, span[-1], P["coat_sh"])
                if cx - 14 <= x <= cx - 2:
                    c.set(x, span[0], P["coat_hi"])
        for dx, dy in ((-13, 2), (-9, 1), (-10, 4), (-5, 3), (-2, 5), (-14, 4), (-6, 5), (2, 3)):  # dapples
            x, y = cx + dx, back + dy
            c.set(x, y, P["coat_hi"])
            c.set(x + 1, y, P["coat_hi"])
            c.set(x, y + 1, P["coat_sh"])
        # near side legs on top
        self.leg(c, hind_x, top, hind_x + g[2][0], ground, g[2][1], False, True)
        self.leg(c, fore_x, top, fore_x + g[0][0], ground, g[0][1], True, True)

    def tail(self, c: Canvas, cx: int, back: int, pose: Pose) -> None:
        """Long silver tail: swishes when idle, streams out behind at a gallop."""
        sway = wave(pose.frame, pose.n, 1.0)
        if pose.anim in ("run", "jump"):
            pts = [(cx - 15, back - 1), (cx - 18, back), (cx - 20, back + 3), (cx - 20, back + 7 + sway)]
        else:
            pts = [(cx - 15, back - 1), (cx - 18, back + 1), (cx - 19 + sway, back + 6), (cx - 18 + sway, back + 12)]
        for i, ((x0, y0), (x1, y1)) in enumerate(zip(pts, pts[1:])):
            c.stroke(x0, y0, x1, y1, P["tail"], 3 if i < 2 else 2)
        (x0, y0), (x1, y1) = pts[1], pts[2]
        c.line(x0 - 1, y0 + 1, x1 - 1, y1 + 1, P["tail_sh"])        # strand shading
        c.set(pts[-1][0] - 1, pts[-1][1] + 1, P["tail_sh"])        # wispy tip


TORSO = [
    "..sSSSSSS..",
    ".bBBBBBBBH.",
    "bBBBBBBBHHH",
    "bBBhhBBhhBH",
    "bBBBBBBBBBH",
    ".bBBBhBBBH.",
    ".bBBBhBBBH.",
    ".bBBBBBBBH.",
    ".bBBBhBBBH.",
    "..rRRRRRRR.",
    "..LRLRLRLR.",
    "..LRLRLRLR.",
]


class CentaurTorso(Torso):
    """Bronze muscle cuirass over a red tunic, leather pteruges at the waist."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        key = {
            "s": P["skin_sh"], "S": P["skin"], "b": P["bronze_sh"], "B": P["bronze"], "H": P["bronze_hi"],
            "h": P["bronze_sh"], "r": P["tunic_sh"], "R": P["tunic"], "L": P["leather"],
        }
        c.stamp(cx - 5, top, TORSO, key)
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "....hhhhh....",
    "..hhHHHHHh...",
    ".hHHHHHHHHH..",
    "lLlLHHHHHHHH.",
    ".HlLlLlLlLL..",
    "HHHHHSSSBBS..",
    "HHHHHSSSSES..",
    "HHHHHsSSSSSN.",
    "HHdHHHSSSSS..",
    "HHdHHHbbMbb..",
    "HHdHHbbbbbb..",
    ".HdHHbbcbbb..",
    ".HHdH.bbcb...",
    "..HH...bb....",
]


class CentaurHead(Head):
    """Wild auburn mane, a beard to match, and a laurel wreath for winning things."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 3, 3, 4, P["skin"])
        c.vline(nx - 1, ny - 3, ny, P["skin_sh"])
        key = {
            "H": P["hair"], "h": P["hair_hi"], "d": P["hair_dk"], "b": P["hair_hi"], "c": P["hair"],
            "L": P["leaf"], "l": P["leaf_dk"], "S": P["skin"], "s": P["skin_sh"],
            "B": P["hair_dk"], "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"], "M": P["skin_sh"],
        }
        c.stamp(nx - 6, ny - 13, HEAD, key)
        c.set(nx - 5 + wave(pose.frame, pose.n), ny + 1, P["hair"])   # loose lock blowing about


SPEAR_TILT = {"up": -3, "reach": -2, "out": -1, "crouch": 1, "flail": 4, "windup": 0, "recover": 1}


def spear(c: Canvas, hx: int, hy: int, tilt: int, back: int = 7, fore: int = 8) -> None:
    """Spear gripped at (hx, hy), pointing forward; `tilt` raises (-) or drops (+) the tip."""
    bx, by = hx - back, hy - round(tilt * back / (back + fore))
    tx, ty = hx + fore, hy + round(tilt * fore / (back + fore))
    c.line(bx, by, tx, ty, P["shaft"])
    c.set(bx, by, P["shaft_sh"])
    c.stamp(tx + 1, ty - 1, ["T.", "tT", "T."], {"T": P["tip"], "t": P["tip_sh"]})


class CentaurArm(Arm):
    """Bare arm with a leather bracer. The front hand never lets go of the spear. Attack: a lunging thrust."""
    species = SPECIES
    reach = 8
    fx_colors = ("#ffffff", P["tip"])
    targets = {
        "windup": ((-0.8, 0.35), (-0.5, 0.8)),               # draw the spear back...
        "strike": ((1.0, 0.25), (-0.7, 0.55)),               # ...and drive it home
        "follow": ((0.95, 0.35), (-0.6, 0.7)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        if front:                                            # spear couched at the hip, bobbing with the stride
            ex, ey = sx - 1, sy + 4
            hx, hy = sx + 3, sy + 6 - abs(pose.swing) // 2
            c.stroke(sx, sy, ex, ey, skin, 2)
            c.stroke(ex, ey, hx, hy, skin, 2)
            spear(c, hx, hy, -1)
            c.rect(hx, hy - 1, 2, 2, skin)
            c.set(ex + 1, ey + 1, P["leather"])
        else:
            dx = 2 * pose.swing
            c.stroke(sx, sy, sx + dx, sy + 7, skin, 2)
            c.rect(sx + dx, sy + 8, 2, 2, skin)
            c.set(sx + dx, sy + 6, P["leather"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        if front:
            lunge = mode in ("strike", "follow")
            spear(c, hx, hy, SPEAR_TILT.get(mode, 0), back=9 if lunge else 7, fore=6 if lunge else 8)
        c.rect(hx, hy - 1, 2, 2, skin)
        c.set(ex, ey, P["leather"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        tip_x = hx + 9                                       # matches the lunging spear in draw_limb
        if pose.fx == "swoosh":                              # speed lines trailing the spear tip
            for dy, x0, col in ((-2, tip_x - 9, "#ffffff"), (2, tip_x - 7, P["tip"]), (4, tip_x - 11, "#ffffff")):
                fx.hline(x0, x0 + 4, hy + dy, col)
        else:
            star(fx, tip_x + 1, hy + 1, *self.fx_colors, r=2)


GENES = dict(legs=CentaurLegs(), torso=CentaurTorso(), head=CentaurHead(), arm=CentaurArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
