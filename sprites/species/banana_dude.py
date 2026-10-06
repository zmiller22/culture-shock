"""Banana dude: a sentient banana in shades and red sneakers. Thumbs up, always."""

import math

from ..canvas import Canvas
from ..palette import BANANA as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, star

SPECIES = "banana_dude"
PREFIX, SUFFIX = "Bana", "nana"

LENGTH = 27   # whole banana, rows 0 (stem) .. 26 (tip)
SPLIT = 13    # rows < SPLIT belong to the head gene, the rest to the torso gene


def _bend(i: int) -> float:
    return max(0.0, math.sin(math.pi * i / (LENGTH - 1)))


def curve(i: int) -> int:
    """Horizontal offset of the banana's center line at row i (back-bulging crescent)."""
    return round(-4 * _bend(i))


def edges(i: int) -> tuple[int, int]:
    """Left/right x offsets of row i, rounded once so the outline stays smooth."""
    mid = -4 * _bend(i)
    hw = max(1.0, 5.6 * _bend(i) ** 0.7)
    return round(mid - hw), round(mid + hw) - 1


def banana_rows(c: Canvas, base_x: int, y0: int, rows: range) -> dict[int, tuple[int, int]]:
    """Paint banana rows (y = y0 + i) and return {i: (x0, x1)} spans."""
    spans = {}
    for i in rows:
        e0, e1 = edges(i)
        x0, x1 = base_x + e0, base_x + e1
        y = y0 + i
        c.hline(x0, x1, y, P["yel"])
        if x1 - x0 >= 4:
            c.set(x0, y, P["dk"])
            c.hline(x0 + 1, x0 + 2, y, P["sh"])
            c.set(x1 - 1, y, P["hi"])
        spans[i] = (x0, x1)
    return spans


class BananaLegs(Legs):
    species = SPECIES
    length = 7

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 2 * s + (0 if front else -1)
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1 + (0 if front else -1), hip, fx, foot_y - 1, P["limb"])
            shoe = P["shoe"] if front else P["dk"]
            c.rect(fx - 1, foot_y, 4, 2, shoe)
            c.set(fx + 3, foot_y + 1, shoe)
            if front:
                c.set(fx, foot_y, P["shoe_hi"])
                c.hline(fx - 1, fx + 3, foot_y + 1, P["glove"])   # white sole


class BananaTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - (LENGTH - 1 - SPLIT)
        y0 = top - SPLIT
        spans = banana_rows(c, cx, y0, range(SPLIT, LENGTH))
        c.hline(*spans[LENGTH - 1], hip, P["stem"])           # brown tip
        for i, dx in ((16, 3), (20, 5), (21, 5), (23, 2)):     # ripeness spots
            c.set(spans[i][0] + dx, y0 + i, P["spot"])
        return Anchors(neck=(cx + curve(SPLIT), top), shoulder=(cx + curve(16) - 1, top + 3), top=top, bottom=hip)


class BananaHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        base_x = nx - curve(SPLIT)
        y0 = ny - SPLIT
        spans = banana_rows(c, base_x, y0, range(0, SPLIT + 1))
        for i in (0, 1):                                       # stem
            c.hline(*spans[i], y0 + i, P["stem"])
        c.set(spans[0][1], y0 - 1, P["stem"])
        # wraparound shades: strap across the back, lenses hanging off the front
        c.hline(spans[6][0] + 1, spans[6][1] + 1, y0 + 6, P["shades"])
        r = spans[7][1]
        c.hline(r - 4, r + 1, y0 + 7, P["shades"])
        c.hline(r - 3, r, y0 + 8, P["shades"])
        c.set(r - 3 + pose.frame % 3, y0 + 7, P["shades_hi"])
        # big grin
        r = spans[10][1]
        c.set(r - 5, y0 + 10, P["mouth"])
        c.hline(r - 4, r, y0 + 11, P["mouth"])
        c.hline(r - 3, r - 1, y0 + 12, P["mouth"])
        c.set(r - 2, y0 + 12, P["tongue"])


class BananaArm(Arm):
    """Noodle arm with a cartoon glove. Thumbs-up when idle, haymaker when angry."""
    species = SPECIES
    reach = 7
    fx_colors = (P["hi"], P["shoe"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        glove = P["glove"] if front else P["glove_sh"]
        if front and pose.anim == "idle":
            c.line(sx, sy, sx + 4, sy + 3, P["limb"])
            c.rect(sx + 4, sy + 1, 3, 3, glove)
            c.set(sx + 5, sy, glove)                           # thumb
            c.set(sx + 5, sy - 1 + (pose.bob > 0), glove)
            return
        dx = (-2 if front else 2) * pose.swing
        hx, hy = sx + 1 + dx, sy + 6
        c.line(sx, sy, hx, hy, P["limb"])
        c.rect(hx - 1, hy, 3, 3, glove)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        glove = P["glove"] if front else P["glove_sh"]
        c.line(sx, sy, hx, hy, P["limb"])
        big = front and mode in ("strike", "follow")
        c.rect(hx - 1, hy - 1, 4 if big else 3, 3, glove)
        if big:
            c.vline(hx + 2, hy - 1, hy + 1, P["glove_sh"])     # knuckle line

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "impact":                                # POW
            star(fx, hx + 7, hy, P["hi"], P["shoe"], r=4)
            fx.rect(hx + 6, hy - 1, 3, 3, P["shoe"])
        else:
            super().attack_fx(fx, sx, sy, hx, hy, pose)


GENES = dict(legs=BananaLegs(), torso=BananaTorso(), head=BananaHead(), arm=BananaArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
