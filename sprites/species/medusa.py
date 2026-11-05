"""Medusa: gorgon on a coiled serpent tail, with a head full of snakes. Don't make eye contact."""

import math

from ..canvas import Canvas, wave
from ..palette import MEDUSA as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star
from .mermaid import spline, tube

SPECIES = "medusa"
PREFIX, SUFFIX = "Medu", "dusa"


class SerpentTail(Legs):
    """Snake from the waist down: drops to the floor, runs back, tip curls up."""
    species = SPECIES
    length = 14

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        h = ground - hip
        speed = {"walk": 1.4, "run": 2}.get(pose.anim, 0)
        ph = 2 * math.pi * pose.frame / pose.n
        hump = [round(speed * 1.6 * max(0, math.sin(ph - k))) for k in (0, 1.6, 3.2)]   # slither humps roll backward
        k = min(1.0, pose.tuck / 5)
        flick = wave(pose.frame, pose.n, 1) if pose.anim == "idle" else 0
        ctrl = [
            (cx - 1, hip), (cx + 2.5, hip + h * 0.45), (cx + 1, ground - 2),
            (cx - 5, ground - 2 - hump[0]), (cx - 10, ground - 2 - hump[1]),
            (cx - 14 + 3 * k, ground - 3 - hump[2] - 2 * k),
            (cx - 16 + 4 * k, ground - 7 - 2 * k + flick),       # tip curls up and over
            (cx - 13 + 4 * k, ground - 10 - 2 * k + flick),
        ]
        pts = spline(ctrl)

        def shade(x, y, ox, oy, s, t):
            if s < -0.4:                                        # belly plates face forward / down
                return P["belly_sh"] if round(t * 40) % 3 == 0 else P["belly"]
            lit = 0.55 * ox - 0.85 * oy
            if lit > 0.55:
                return P["coil_hi"]
            if s > 0.15 and round(t * 22) % 3 == 0:              # dark saddle bands down the back
                return P["coil_dk"]
            if lit < -0.4:
                return P["coil_sh"]
            return P["coil"]

        tube(c, pts, lambda t: 7.5 - 5.5 * t, shade)


class MedusaTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 10
        rows = [
            "..sSSSS..",
            ".sSSSSGW.",
            ".sSSSGWWh",
            ".sSSGWWWh",
            ".wWGWWWWh",
            "..wWWWWh.",
            "..wWWWWh.",
            "..wWWWWh.",
            ".gGGGGGGg",
            ".wWWwWWWh.",
            "wWWwWWwWWh",
        ]
        key = {"s": P["skin_sh"], "S": P["skin"], "W": P["wrap"], "w": P["wrap_sh"], "h": P["wrap_hi"],
               "g": P["gold_sh"], "G": P["gold"]}
        c.stamp(cx - 4, top, rows, key)
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "....DDDD....",
    "..DDDDDDDD..",
    ".DDDDDDDDDD.",
    ".DDDDDDDDDD.",
    "DDDDDDSSSSD.",
    "DDDDDSSSBBS.",
    "DDDDSSSSSES.",
    "DDDDSSSSSSS.",
    ".DDDsSSSSSSN",
    ".DDDSsSSSSS.",
    "..DDSSsSSmS.",
    "...D..sSSS..",
]

# (scalp x, scalp y, heading in degrees) for each hair snake, back to front
SNAKES = [(0, 8, 160), (0, 3, 200), (3, 0, 240), (7, 0, 280), (10, 1, 315)]


def hair_snake(c: Canvas, x: float, y: float, heading: float, pose: Pose, k: int) -> None:
    """A tiny snake sprouting from (x, y): S-wiggling neck, fat head with an eye, flicking tongue."""
    ph = 2 * math.pi * pose.frame / pose.n
    pts = []
    for i in range(5):
        a = math.radians(heading) + 0.7 * math.sin(ph + k * 2.3 + i * 1.4)   # writhe around its heading
        x += math.cos(a) * 1.2
        y += math.sin(a) * 1.2
        pts.append((round(x), round(y)))
    for px, py in pts:
        c.rect(px, py, 2, 2, P["snake"])
        c.set(px + 1, py + 1, P["snake_sh"])
    hx, hy = pts[-1]
    d = 1 if math.cos(math.radians(heading)) >= -0.1 else -1     # which way the snake head faces
    c.rect(hx - 1, hy - 1, 3, 3, P["snake"])
    c.hline(hx - 1, hx + 1, hy - 1, P["snake_hi"])
    c.set(hx + d, hy, P["snake_eye"])
    if (pose.frame + k) % 2:                                       # tongue flick
        c.set(hx + 2 * d, hy + 1, P["tongue"])
        c.set(hx + 3 * d, hy + 1 + (k % 2 * 2 - 1), P["tongue"])


class MedusaHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        x0, y0 = nx - 5, ny - 12
        for k, (sx, sy, heading) in enumerate(SNAKES):
            hair_snake(c, x0 + sx, y0 + sy, heading, pose, k)
        glare = pose.anim == "attack" and pose.fx is not None
        key = {
            "D": P["snake_sh"], "S": P["skin"], "s": P["skin_sh"], "N": P["skin"], "m": P["lips"],
            "B": P["snake_sh"], "E": P["skin_sh"] if pose.blink else P["glow_core"] if glare else P["glow"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.hline(x0 + 4, x0 + 8, y0 + 3, P["gold"])                # diadem
        c.set(x0 + 8, y0 + 2, P["gold"])
        if glare:                                                  # eyes blaze before the stare lands
            c.set(x0 + 10, y0 + 6, P["glow"])
            c.set(x0 + 9, y0 + 5, P["glow"])


class MedusaArm(Arm):
    """Green arm with a gold armlet. Attack: palm out, a petrifying stare-beam turns the air to stone."""
    species = SPECIES
    reach = 9
    fx_colors = (P["stone_hi"], P["glow"])
    targets = {"strike": ((0.8, -0.6), (-0.7, 0.55)), "follow": ((0.85, -0.5), (-0.6, 0.7))}   # hand up by the eyes

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        dx = (-2 if front else 2) * pose.swing
        ex, ey = sx + dx // 2, sy + 5                             # elbow
        hx, hy = sx + 3 + dx, sy + 8                              # hand rests forward, ready to curse
        c.line(sx, sy, ex, ey, skin, width=2)
        c.line(ex, ey, hx, hy, skin, width=2)
        c.rect(hx + 1, hy - 1, 2, 2, skin)
        c.hline(ex, ex + 1, ey - 1, P["gold"] if front else P["gold_sh"])     # armlet

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        c.set(ex, ey, P["gold"] if front else P["gold_sh"])
        if front and mode in ("strike", "follow"):               # palm out, fingers splayed
            c.vline(hx + 2, hy - 1, hy + 2, skin)
            c.set(hx + 1, hy - 2, skin)
        else:
            c.rect(hx, hy, 2, 2, skin)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        x, y = hx + 3, hy - 1
        if pose.fx == "swoosh":                                  # the stare: a widening cone of stone-light
            for i in range(11):
                spread = (i + 1) // 3
                fx.set(x + i, y, P["glow_core"] if i < 6 else P["glow"])
                if i % 2 == 0:
                    fx.set(x + i, y - spread, P["glow"])
                    fx.set(x + i, y + spread, P["glow"])
                if i > 4 and i % 3 == 1:
                    fx.set(x + i, y - spread - 1, P["stone_hi"])
                    fx.set(x + i, y + spread + 1, P["stone_hi"])
        else:                                                    # it lands: a crunchy burst of stone dust
            bx = x + 5
            star(fx, bx, y, P["stone_hi"], P["glow"], r=4)
            for dx, dy in ((-3, -3), (3, -4), (-2, 3), (3, 3), (3, -1)):    # pebbles
                fx.rect(bx + dx, y + dy, 2, 2, P["stone"])
                fx.set(bx + dx, y + dy, P["stone_hi"])


GENES = dict(legs=SerpentTail(), torso=MedusaTorso(), head=MedusaHead(), arm=MedusaArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
