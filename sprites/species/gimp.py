"""Gimp: head-to-toe black leather, zippered hood, studded harness, a chain he
keeps handing you. Lives in a box in the basement. Very excited to be out."""

import math

from ..canvas import Canvas, line_points, wave
from ..palette import INK, GIMP as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star
from .dominatrix import bezier
from .tech_bro import speech_bubble

SPECIES = "gimp"
PREFIX, SUFFIX = "Gimp", "gimp"


def chain(c: Canvas, pts: list[tuple[int, int]]) -> None:
    """Steel chain along a polyline: alternating bright/dark links, clipped to the frame."""
    pts = [(min(45, max(2, x)), min(GROUND, max(2, y))) for x, y in pts]
    k = 0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for x, y in line_points(x0, y0, x1, y1)[:-1]:
            c.set(x, y, P["steel"] if k % 2 == 0 else P["steel_sh"])
            k += 1
    c.set(*pts[-1], P["steel"])


class GimpLegs(Legs):
    """Knees bent, weight forward, ready to scurry. Chunky buckled boots."""
    species = SPECIES
    length = 11

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            suit = P["suit"] if front else P["suit_sh"]
            kx, ky = (cx + fx) // 2 + 2, (hip + foot_y) // 2      # knee pokes forward
            c.line(cx - 1, hip, kx, ky, suit, width=3)
            c.line(kx, ky, fx, foot_y - 1, suit, width=3)
            c.rect(fx, foot_y - 1, 4, 2, suit)                    # boot
            c.rect(fx - 1, foot_y + 1, 6, 1, P["strap"] if front else INK)
            if front:
                c.set(kx + 2, ky, P["gloss"])                     # shiny kneecap
                c.set(kx + 1, ky + 1, P["suit_hi"])
                c.set(fx + 1, foot_y - 1, P["steel"])             # boot buckle
                c.set(fx + 4, foot_y, P["suit_hi"])


class GimpTorso(Torso):
    """Hunched over, studded harness with a steel O-ring on the chest."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 10
        for y in range(top, hip):                                 # hunched: shoulders roll forward
            off = (hip - y) // 4
            hump = 1 if top < y < top + 5 else 0                  # rounded back...
            paunch = 1 if hip - 5 < y < hip - 1 else 0            # ...and a little belly
            x0 = cx - 4 + off + (1 if y == top else 0) - hump
            x1 = cx + 4 + off - (1 if y == top else 0) + paunch
            c.hline(x0, x1, y, P["suit"])
            c.set(x0, y, P["suit_sh"])
            if y > top:
                c.set(x1, y, P["suit_hi"])
        c.hline(cx - 4, cx + 4, hip, P["strap"])                  # belt...
        c.set(cx + 2, hip, P["steel"])                            # ...buckle
        # harness: strap over the shoulder and one round the chest, meeting at a ring
        off = (hip - top - 4) // 4
        rx, ry = cx + 1 + off, top + 4
        c.line(cx - 1 + (hip - top) // 4, top, rx, ry, P["strap"])
        c.line(rx, ry, cx, hip - 1, P["strap"])
        c.hline(cx - 4 + off, cx + 4 + off, ry, P["strap"])
        for x in range(cx - 3 + off, cx + 4 + off, 2):            # studs
            c.set(x, ry, P["steel"])
        c.set(cx, hip - 3, P["steel"])
        c.stamp(rx - 1, ry - 1, [".o.", "o.o", ".o."], {"o": P["steel"]})   # O-ring
        c.set(rx, ry, P["strap"])
        c.set(rx + 1, ry + 1, P["steel_sh"])
        c.set(cx + 3 + (hip - top - 2) // 4, top + 2, P["gloss"])  # shiny shoulder
        return Anchors(neck=(cx + 3, top + 1), shoulder=(cx + 1, top + 2), top=top, bottom=hip)


HEAD = [
    "...gggggg..",
    "..gHHHHHHg.",
    ".gHgHHHHHHg",
    ".HHgHHHHHHH",
    "lHHHHHHHHHH",
    "HlHHHWWHWWH",
    "lHHHHWWHWWH",
    "HlHHHHHHHHN",
    "lHHHHHHHHHH",
    "HHHHzZzZzZz",
    ".HHHHHHHtHH",
    "..sHHHHHtH.",
    "...sHHHHH..",
]


class GimpHead(Head):
    """Full hood: laced up the back, two eye holes, zipper for a mouth.
    Twitches. Constantly. The collar has a ring and a bit of chain."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        idle = pose.anim == "idle"
        twitch = (0, 1, 0, -1)[pose.frame % 4] if idle else 0
        x0, y0 = nx - 5 + twitch, ny - 12 + (pose.frame % 2 if idle else 0)
        c.rect(nx - 1, ny - 2, 3, 3, P["suit"])
        key = {
            "g": P["suit_hi"], "H": P["suit"], "s": P["suit_sh"], "N": P["suit_hi"],
            "W": P["suit_sh"] if pose.blink else P["eye"],
            "l": P["steel_sh"], "z": P["steel_sh"], "Z": P["steel"], "t": P["steel"],
        }
        c.stamp(x0, y0, HEAD, key)
        if pose.blink:                                           # squeezed shut
            c.hline(x0 + 5, x0 + 6, y0 + 6, P["eye"])
            c.hline(x0 + 8, x0 + 9, y0 + 6, P["eye"])
        else:                                                    # pupils, darting about
            dart = (1, 0, 1, 0)[pose.frame % 4] if idle else 1
            for ex in (x0 + 5, x0 + 8):
                c.set(ex + dart, y0 + 6 - (pose.anim == "attack"), INK)
        c.set(x0 + 4, y0 + 1, P["gloss"])                        # shine on the dome
        c.set(x0 + 5, y0 + 1, P["gloss"])
        # collar with a D-ring and a short dangling chain
        c.hline(nx - 1, nx + 2, ny, P["strap"])
        c.set(nx + 1, ny, P["steel"])
        swing = wave(pose.frame, pose.n)
        chain(c, [(nx + 2, ny + 1), (nx + 2 + swing, ny + 4)])


class GimpArm(Arm):
    """Studded wristband, leather mitt, and the end of his own leash, offered to anyone.
    Attacks by whirling the chain overhead and bringing it down. CLANK."""
    species = SPECIES
    reach = 9
    fx_colors = (P["steel"], P["spark"])
    targets = {
        "windup": ((-0.5, -0.85), (-0.4, 0.85)),              # chain up behind his head...
        "strike": ((0.9, -0.45), (-0.7, 0.55)),               # ...whirled overhead...
        "follow": ((1.0, 0.15), (-0.6, 0.7)),                 # ...and slammed down
    }

    def chain_path(self, mode: str, hx: int, hy: int, frame: int) -> list[tuple[int, int]]:
        if mode == "windup":
            return bezier((hx, hy + 1), (hx - 6, hy + 1), (hx - 7, hy + 8))
        if mode == "strike":
            return bezier((hx + 1, hy), (hx + 6, hy - 5), (hx + 11, hy - 2))
        if mode == "follow":
            return bezier((hx + 2, hy + 1), (hx + 7, hy), (min(42, hx + 11), hy + 6))
        sway = wave(frame, 4)                                  # dangling, swaying
        return bezier((hx + 1, hy + 2), (hx + 5, hy + 7), (hx + 2 + sway, hy + 10))

    def mitt(self, c: Canvas, hx: int, hy: int, front: bool) -> None:
        c.rect(hx, hy, 2, 2, P["suit"] if front else P["suit_sh"])
        c.set(hx + 1, hy - 1, P["suit"] if front else P["suit_sh"])   # thumb up, eager

    def sleeve(self, c: Canvas, sx: int, sy: int, ex: int, ey: int, hx: int, hy: int, front: bool) -> None:
        suit = P["suit"] if front else P["suit_sh"]
        c.stroke(sx, sy, ex, ey, suit, 2)
        c.stroke(ex, ey, hx, hy, suit, 2)
        # studded wristband just behind the hand
        bx, by = round(hx + (ex - hx) * 0.35), round(hy + (ey - hy) * 0.35)
        c.set(bx, by, P["steel"] if front else P["steel_sh"])
        if front:                                             # leather shine along the top
            c.line(sx, sy, ex, ey, P["suit_hi"])
            c.set(ex, ey, P["gloss"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if not front:
            dx = 2 * pose.swing
            self.sleeve(c, sx, sy, sx + dx // 2 + 1, sy + 4, sx + dx + 1, sy + 7, False)
            self.mitt(c, sx + dx + 1, sy + 7, False)
            return
        # holds the leash out in front, hopefully
        jit = (0, 1, 0, 1)[pose.frame % 4] if pose.anim == "idle" else 0
        dx = -pose.swing
        hx, hy = sx + 6 + dx, sy + 3 - jit
        self.sleeve(c, sx, sy, sx + 2 + dx, sy + 5, hx, hy, True)
        path = self.chain_path("hang", hx, hy, pose.frame)
        chain(c, path)
        tx, ty = path[-1]
        c.stamp(tx - 1, ty + 1, ["o.o", ".o."], {"o": P["steel_sh"]})   # leash clip
        self.mitt(c, hx, hy, True)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        self.sleeve(c, sx, sy, ex, ey, hx, hy, front)
        if front:
            chain(c, self.chain_path(mode, hx, hy, pose.frame))
        self.mitt(c, hx, hy, front)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                                  # the chain's arc, link by link
            r = self.reach + 8
            for i in range(30):
                a = -2.4 + 1.8 * i / 29
                x, y = sx + round(math.cos(a) * r), sy + round(math.sin(a) * r)
                if 2 <= x <= 45 and y >= 2:
                    fx.set(x, y, P["steel"] if i % 3 else P["steel_sh"])
            return
        x, y = self.chain_path("follow", hx, hy, pose.frame)[-1]  # CLANK
        x, y = min(42, x), min(GROUND - 3, y)
        star(fx, x, y, P["steel"], P["spark"], r=3)
        for dx, dy in ((-3, -2), (3, -3), (2, 3)):
            fx.set(x + dx, y + dy, P["spark"])


def mmph(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """Something muffled from under the hood. Nobody knows what."""
    if pose.flash or pose.melt:
        return
    if (pose.anim == "idle" and pose.frame >= 2) or (pose.anim == "hurt" and pose.frame == 0):
        nx, ny = info["anchors"].neck
        speech_bubble(out, min(nx + 1, 23), max(1, ny - 21), "MMPH")


GENES = dict(legs=GimpLegs(), torso=GimpTorso(), head=GimpHead(), arm=GimpArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"],
                    decorations=[mmph])
