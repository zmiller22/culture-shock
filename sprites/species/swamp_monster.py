"""Swamp monster: hunched, mossy, gill-slitted, dripping toxic slime."""

from ..canvas import Canvas
from ..palette import SWAMP as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso

SPECIES = "swamp_monster"
PREFIX, SUFFIX = "Swamp", "slurp"


class SwampLegs(Legs):
    species = SPECIES
    length = 9

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 2 + 2 * s
            lift = 1 if (pose.anim == "walk" and pose.swing == 0 and not front) else 0
            foot_y = ground - 1 - lift
            col = P["base"] if front else P["dark"]
            c.line(cx - 2, hip, fx, foot_y - 1, col, width=4)
            c.rect(fx - 1, foot_y, 6, 2, col)                 # webbed foot
            c.set(fx + 5, foot_y + 1, P["claw"])
            c.set(fx + 3, foot_y + 1, P["claw"])
            if front:
                c.line(cx + 1, hip, fx + 3, foot_y - 1, P["hi"])
                c.set(fx + 1, hip + 3, P["dark"])
                c.set(fx, hip + 5, P["dark"])


class SwampTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 13
        c.oval(cx - 8, top, 15, 15, P["base"])
        c.oval(cx - 9, top - 1, 10, 9, P["base"])              # hunched back
        c.oval(cx - 1, top + 4, 7, 10, P["belly"])
        for y in range(top + 6, hip + 1, 2):                    # belly scales
            span = c.row_span(y)
            if span:
                c.hline(max(cx, span[0]), span[1] - 1, y, P["belly_sh"])
        # mottled back
        for y in range(top - 1, hip + 1):
            for x in range(cx - 9, cx):
                if c.get(x, y) == P["base"] and (x * 3 + y * 5) % 7 == 0:
                    c.set(x, y, P["dark"])
        # highlight along the hump
        for x in range(cx - 7, cx + 1):
            span = [y for y in range(top - 1, hip) if c.opaque(x, y)]
            if span:
                c.set(x, span[0] + 1, P["hi"])
        # hanging moss strands
        for x, length in ((cx - 7, 4), (cx - 5, 7), (cx - 3, 3), (cx - 1, 5)):
            c.vline(x, top + 1, top + length, P["moss"])
        # slime drip (grows over the animation)
        drip = 1 + (pose.frame % 2)
        c.vline(cx + 3, hip + 1, hip + drip, P["slime"])
        c.set(cx - 6, top + 6, P["slime"])
        return Anchors(neck=(cx + 4, top + 3), shoulder=(cx, top + 4), top=top, bottom=hip)


HEAD = [
    "..f.f.f....",
    ".fFfFfFf...",
    ".GGGGGGGG..",
    "GgGGGGGGGG.",
    "GgGGGYYoGGG",
    "GLGGGYYYGGG",
    "GLGLGGGGGGG",
    "GLGLGGMMMMM",
    "GGGGGMTMTMT",
    ".GGGGGGGGG.",
]


class SwampHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        eye = P["dark"] if pose.blink else P["eye"]
        core = P["dark"] if pose.blink else P["eye_core"]
        key = {
            "f": P["dark"], "F": P["hi"], "G": P["base"], "g": P["hi"], "L": P["dark"],
            "Y": eye, "o": core, "M": P["mouth"], "T": P["teeth"],
        }
        c.stamp(nx - 5, ny - 8, HEAD, key)


class SwampArm(Arm):
    """Long zombie-reach arm with claws."""
    species = SPECIES

    def draw(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        col = P["base"] if front else P["dark"]
        dy = (-pose.swing if front else pose.swing)
        ex, ey = sx + 3, sy + 5
        hx, hy = sx + 8, sy + 6 + dy
        c.line(sx, sy, ex, ey, col, width=3)
        c.line(ex, ey, hx, hy, col, width=2)
        c.line(ex, ey + 1, hx, hy + 1, col, width=2)
        c.set(hx + 2, hy, P["claw"])
        c.set(hx + 2, hy + 2, P["claw"])
        c.set(hx + 1, hy + 3, P["claw"])
        if front:
            c.line(ex, ey, hx, hy, P["hi"])
            if pose.frame % 2:
                c.set(hx, hy + 2, P["slime"])


GENES = dict(legs=SwampLegs(), torso=SwampTorso(), head=SwampHead(), arm=SwampArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
