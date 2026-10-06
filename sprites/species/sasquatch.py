"""Sasquatch: big, shaggy, conical head, knuckle-length arms. A classic."""

from ..canvas import Canvas
from ..palette import INK, SASQUATCH as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "sasquatch"
PREFIX, SUFFIX = "Squatch", "squatch"


def fur_strokes(c: Canvas, x0: int, y0: int, x1: int, y1: int, base: str, stroke: str, step: int = 3) -> None:
    """Short diagonal fur flicks wherever `base` is painted."""
    for y in range(y0, y1, step):
        off = (y // step) % 2 * 2
        for x in range(x0 + off, x1, 4):
            if c.get(x, y) == base and c.get(x + 1, y + 1) == base:
                c.set(x, y, stroke)
                c.set(x + 1, y + 1, stroke)


class SasquatchLegs(Legs):
    species = SPECIES
    length = 14

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 3 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            fur = P["fur"] if front else P["fur_dk"]
            c.line(cx - 3, hip, fx, foot_y - 2, fur, width=5)
            c.rect(fx - 1, foot_y, 8, 2, P["foot"])
            c.rect(fx, foot_y - 1, 5, 1, P["foot"])
            for i in range(0, 6, 2):                           # shaggy ankle fringe
                c.set(fx - 1 + i, foot_y - 1, fur)
            if front:
                c.set(fx + 6, foot_y, P["foot_hi"])
                c.set(fx + 4, foot_y, P["foot_hi"])
                fur_strokes(c, cx - 6, hip + 1, cx + 6, foot_y - 2, fur, P["fur_dk"])


class SasquatchTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 16
        c.oval(cx - 8, top, 16, 18, P["fur"])
        c.oval(cx - 9, top - 1, 12, 10, P["fur"])              # shoulder hump
        c.oval(cx + 1, top + 4, 6, 11, P["chest"])
        fur_strokes(c, cx - 9, top, cx + 8, hip + 1, P["fur"], P["fur_dk"])
        fur_strokes(c, cx - 7, top + 1, cx + 3, top + 6, P["fur_dk"], P["fur_hi"], step=2)
        for y in range(top + 2, hip, 3):                       # shaggy back edge
            span = c.row_span(y)
            if span:
                c.set(span[0] - 1, y, P["fur"])
                c.set(span[0] - 1, y + 1, P["fur_dk"])
        return Anchors(neck=(cx + 4, top + 3), shoulder=(cx, top + 4), top=top, bottom=hip)


HEAD = [
    "....ff......",
    "...fFFf.....",
    "..fFFFFf....",
    ".fFFFFFFF...",
    ".FFFFFFFFF..",
    "FFFFFFbbbbb.",
    "FdFFFFcwEcc.",
    "FdFFFFcccccc",
    "FFdFFFccccnc",
    "FFdFFFccccc.",
    ".FFFFFcMMMc.",
    ".FFFFFFcccc.",
    "..FFFFFFFF..",
]


class SasquatchHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        key = {
            "f": P["fur_hi"], "F": P["fur"], "d": P["fur_dk"], "b": P["fur_xdk"],
            "c": P["face"], "n": P["face_sh"], "M": P["face_sh"],
            "w": P["face_sh"] if pose.blink else P["eye"], "E": P["face_sh"] if pose.blink else INK,
        }
        c.stamp(nx - 6, ny - 11, HEAD, key)


class SasquatchArm(Arm):
    """Knuckle-dragging arms. Attacks with an overhead ground-pound."""
    species = SPECIES
    reach = 13
    fx_colors = ("#f4f0e0", P["fur_hi"])
    targets = {
        "windup": ((-0.25, -1.0), (-0.45, 0.85)),            # raise it high...
        "strike": ((0.8, 0.6), (-0.6, 0.7)),                  # ...and bring it down
        "follow": ((0.75, 0.7), (-0.5, 0.8)),
        "reach": ((0.95, -0.15), (-0.8, -0.3)),               # long arms: keep them below the face
        "out": ((0.95, 0.1), (-0.9, 0.1)),
        "up": ((0.7, -0.45), (-0.4, -0.8)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        fur = P["fur"] if front else P["fur_dk"]
        dx = (-2 if front else 2) * pose.swing
        ex, ey = sx + 2 + dx // 2, sy + 7                      # elbow
        hx, hy = sx + 3 + dx, sy + 13                          # hand
        c.oval(sx - 2, sy - 2, 6, 6, fur)                      # rounded shoulder
        c.line(sx - 1, sy, ex - 1, ey, fur, width=4)
        c.line(ex - 1, ey, hx, hy, fur, width=3)
        c.set(ex - 2, ey + 1, fur)                             # elbow tuft
        c.rect(hx - 1, hy, 4, 3, P["foot"])
        c.set(hx + 3, hy + 1, P["foot"])                       # thumb
        if front:
            c.line(sx + 2, sy - 1, ex + 1, ey, P["fur_hi"])
            c.set(sx - 1, sy + 3, P["fur_dk"])
            c.set(sx, sy + 5, P["fur_dk"])
            c.set(hx, hy + 2, P["foot_hi"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        fur = P["fur"] if front else P["fur_dk"]
        ex, ey = elbow(sx, sy, hx, hy, 2)
        c.oval(sx - 2, sy - 2, 6, 6, fur)
        c.stroke(sx, sy, ex, ey, fur, 4)
        c.stroke(ex, ey, hx, hy, fur, 3)
        c.rect(hx - 1, hy - 1, 4, 3, P["foot"])
        if front:
            c.line(sx + 1, sy - 1, ex + 1, ey - 1, P["fur_hi"])
            c.set(hx, hy + 1, P["foot_hi"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":
            super().attack_fx(fx, sx, sy, hx, hy, pose)
            return
        for x, w in ((hx - 1, 5), (hx + 4, 3), (hx - 7, 4)):  # dust kicked up by the slam
            fx.oval(x, GROUND - 2, w, 3, "#c8b090")
            fx.set(x + 1, GROUND - 2, "#f4f0e0")
        star(fx, hx + 3, hy + 2, *self.fx_colors)


GENES = dict(legs=SasquatchLegs(), torso=SasquatchTorso(), head=SasquatchHead(), arm=SasquatchArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
