"""Fly Man: a lab scientist who stepped into the teleporter with a housefly.
Lab coat, pocket pens, and a giant fly head. Rubs his hands together a lot."""

import math

from ..canvas import Canvas
from ..palette import INK, FLY_MAN as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "fly_man"
PREFIX, SUFFIX = "Fly", "fly"


def wing(c: Canvas, rx: int, ry: int, ang: float, length: int, width: float, near: bool) -> None:
    """A rotated, root-pinched ellipse: one fly wing growing from (rx, ry) at angle `ang`."""
    ux, uy = math.cos(ang), math.sin(ang)
    half = length / 2
    mx, my = rx + 0.5 + ux * half, ry + 0.5 + uy * half
    membrane = P["wing"] if near else P["wing_sh"]
    for y in range(ry - length - 1, ry + length + 2):
        for x in range(rx - length - 1, rx + length + 2):
            dx, dy = x + 0.5 - mx, y + 0.5 - my
            u, v = (dx * ux + dy * uy) / half, (-dx * uy + dy * ux) / (width / 2)
            v *= 1 + 0.6 * max(0.0, -u)                        # pinch toward the root
            if u * u + v * v <= 1.0:
                c.set(x, y, membrane)
    if not near:
        return
    for t, side, col in ((0.55, -0.35, P["wing_hi"]), (0.75, 0.3, P["sheen_a"]), (0.85, -0.1, P["sheen_b"])):
        c.set(round(mx - 0.5 + ux * half * (2 * t - 1) - uy * side * width / 2),
              round(my - 0.5 + uy * half * (2 * t - 1) + ux * side * width / 2), col)
    for k in range(1, length - 1):                              # main vein, root to tip
        if k % 3 != 2:
            c.set(round(rx + ux * k + uy * 0.6), round(ry + uy * k - ux * 0.6), P["vein"])


def wing_angles(pose: Pose) -> tuple[float, float]:
    """(near, far) wing angles: buzz between up and back every frame, spread when airborne."""
    if pose.anim == "jump" and pose.frame in (1, 2):
        return -1.9, -2.6
    if pose.anim in ("hurt", "death"):
        return 2.75, 2.45                                       # drooping
    if pose.frame % 2:
        return 2.95, -2.8
    return -2.45, -2.8


class FlyManLegs(Legs):
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1, hip, fx, foot_y - 1, P["pants"] if front else P["pants_sh"], width=3)
            c.rect(fx, foot_y, 4, 1, P["shoe"] if front else P["sole"])
            c.rect(fx - 1, foot_y + 1, 6, 1, P["sole"])
            if front:
                c.set(fx + 2, foot_y, P["shoe_hi"])            # polished loafers


class FlyManTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        near, far = wing_angles(pose)                          # wings first: the coat covers their roots
        wing(c, cx - 3, top + 2, far, 11, 4.5, near=False)
        wing(c, cx - 3, top + 3, near, 13, 5, near=True)
        # lab coat, hanging past the hips
        c.rect(cx - 3, top, 7, 1, P["coat"])
        c.rect(cx - 4, top + 1, 9, hip + 3 - top, P["coat"])
        c.hline(cx - 5, cx - 4, hip + 3, P["coat"])
        flap = pose.lift > 0 or abs(pose.swing) > 1             # tails flap when moving fast
        if flap:
            c.set(cx - 5, hip + 2, P["coat"])
            c.hline(cx - 6, cx - 5, hip + 3, P["coat_sh"])
        c.vline(cx - 4, top + 1, hip + 3, P["coat_sh"])
        c.vline(cx, hip, hip + 3, P["coat_sh"])                # back vent
        c.set(cx - 1, top - 1, P["coat"])                      # popped collar
        c.set(cx, top - 1, P["coat_sh"])
        # open front: shirt, tie, lapel
        c.vline(cx + 3, top, top + 1, P["shirt"])
        c.vline(cx + 4, top + 1, top + 5, P["tie"])
        c.line(cx + 2, top, cx + 3, top + 6, P["coat_sh"])
        # pocket protector with pens
        c.hline(cx, cx + 2, top + 5, P["coat_sh"])
        c.set(cx + 1, top + 4, P["pen_r"])
        c.set(cx + 2, top + 4, P["pen_b"])
        for y in (top + 8, hip + 1):                           # buttons
            c.set(cx + 4, y, P["coat_sh"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


class FlyManHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 3, 3, 4, P["chit_dk"])             # bristly neck
        c.oval(nx - 6, ny - 12, 12, 11, P["chit"])             # skull
        c.hline(nx - 4, nx - 1, ny - 11, P["chit_hi"])
        c.set(nx - 5, ny - 10, P["chit_hi"])
        for x, y in ((nx - 5, ny - 13), (nx - 2, ny - 14), (nx - 7, ny - 9)):
            c.set(x, y, P["chit_dk"])                          # bristles
        # huge compound eye: a lattice of facets, darker toward the back
        ex, ey, ew, eh = nx - 2, ny - 13, 10, 10
        c.oval(ex, ey, ew, eh, P["eye"])
        for y in range(ey, ey + eh):
            for x in range(ex, ex + ew):
                if c.get(x, y) == P["eye"] and (x + 2 * y) % 4 == 0:
                    c.set(x, y, P["eye_dk"] if (x - ex) + (ey + eh - y) < 10 else P["eye_hi"])
        c.oval(ex + 4, ey + 1, 4, 3, P["eye_hi"])
        c.set(ex + 5, ey + 2, P["glint"])
        c.set(ex + 6, ey + 1, P["glint"])
        # face plate and mouthparts
        c.rect(nx + 3, ny - 3, 3, 2, P["face"])
        attack = pose.anim == "attack" and pose.frame in (1, 2)
        if attack:                                             # proboscis shoots out
            c.line(nx + 4, ny - 2, nx + 8, ny - 1, P["prob"], width=1)
            c.vline(nx + 9, ny - 2, ny, P["prob_tip"])
            c.set(nx + 10, ny - 1, P["prob_tip"])
        else:
            c.vline(nx + 4, ny - 2, ny, P["prob"])
            c.hline(nx + 4, nx + 6, ny + 1, P["prob_tip"])
            if pose.anim == "idle" and pose.frame >= 2:        # drool
                c.set(nx + 5, ny + 2, P["goo"])
        # antennae
        for dx, col in ((0, P["chit_dk"]), (2, P["chit"])):
            c.line(nx + 3 + dx, ny - 13, nx + 4 + dx, ny - 15, col)
        c.set(nx + 7, ny - 16, P["chit_dk"])                   # arista


class FlyManArm(Arm):
    """Rolled-up sleeve over a bristly fly forearm. Idle: rubs hands together.
    Attacks by hurling a handful of digestive goo."""
    species = SPECIES
    reach = 9
    fx_colors = (P["goo"], P["goo_hi"])

    def forearm(self, c: Canvas, ex: int, ey: int, hx: int, hy: int, front: bool) -> None:
        skin = P["limb"] if front else P["limb_dk"]
        c.stroke(ex, ey, hx, hy, skin, 2)
        c.rect(ex, ey, 2, 1, P["coat_sh"] if front else P["coat_dk"])   # cuff
        c.rect(hx, hy, 2, 2, skin)
        c.set(hx + 2 if hx >= ex else hx - 1, hy + 1, P["claw"])         # hooked claw
        if front:
            mx, my = (ex + hx) // 2, (ey + hy) // 2                      # bristles
            c.set(mx, my, P["bristle"])
            c.set(hx, hy, P["bristle"])
            c.set(mx - 1 if hx >= ex else mx + 2, my + 1, skin)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        sleeve = P["coat"] if front else P["coat_sh"]
        if pose.anim == "idle":                                # rub-a-dub
            r = pose.frame % 2 if front else 1 - pose.frame % 2
            ex, ey = sx, sy + 5
            hx, hy = sx + 5 + (0 if front else 1), sy + 3 + r
        else:
            dx = (-2 if front else 2) * pose.swing
            ex, ey = sx + dx // 2, sy + 5
            hx, hy = sx + 1 + dx, sy + 9
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        self.forearm(c, ex, ey, hx, hy, front)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, P["coat"] if front else P["coat_sh"], 2)
        self.forearm(c, ex, ey, hx, hy, front)
        if front and mode == "windup":                         # scooping up goo
            c.rect(hx - 1, hy - 1, 2, 2, P["goo"])
            c.set(hx - 1, hy - 1, P["goo_hi"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                                # glob in flight, dripping
            x, y = hx + 5, hy - 1
            fx.oval(x, y, 5, 4, P["goo"])
            fx.set(x + 3, y + 1, P["goo_hi"])
            fx.set(x + 2, y + 3, P["goo_dk"])
            for dx, dy in ((-2, 2), (-4, 1), (-5, 3)):
                fx.set(x + dx, y + dy, P["goo"])
        else:                                                  # SPLAT
            x, y = min(hx + 9, fx.w - 7), hy
            fx.oval(x - 2, y - 2, 5, 5, P["goo"])
            fx.set(x, y - 1, P["goo_hi"])
            for dx, dy in ((-3, -3), (3, -3), (-4, 1), (4, 0), (3, 3), (-1, 4)):
                fx.set(x + dx, y + dy, P["goo"])
            fx.vline(x + 1, y + 3, y + 5, P["goo_dk"])         # drip


GENES = dict(legs=FlyManLegs(), torso=FlyManTorso(), head=FlyManHead(), arm=FlyManArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
