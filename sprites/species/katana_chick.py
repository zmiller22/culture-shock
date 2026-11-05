"""Katana chick: yellow jumpsuit, black ponytail, red headband, very sharp sword.
Says nothing. Doesn't need to."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, KATANA_CHICK as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "katana_chick"
PREFIX, SUFFIX = "Kata", "tana"


BLADE = 11          # blade length past the guard, in px


def katana(c: Canvas, hx: int, hy: int, dx: float, dy: float) -> None:
    """Katana gripped at (hx, hy), blade pointing along (dx, dy). Hand goes on top."""
    n = math.hypot(dx, dy) or 1
    dx, dy = dx / n, dy / n

    def at(t: float) -> tuple[int, int]:
        return round(hx + dx * t), round(hy + dy * t)

    c.line(*at(-3), *at(1), P["wrap"])                         # wrapped hilt
    c.set(*at(-2), P["wrap_hi"])
    c.set(*at(-3), P["guard"])                                 # pommel cap
    gx, gy = at(2)
    c.set(gx, gy, P["guard"])                                  # tsuba, across the blade
    c.set(gx + round(-dy), gy + round(dx), P["guard"])
    c.set(gx - round(-dy), gy - round(dx), P["guard"])
    for t in range(3, 3 + BLADE):                              # the blade stops at the floor
        x, y = at(t)
        if y > GROUND:
            break
        c.set(x, y, P["edge"] if t % 3 == 1 or t == 2 + BLADE else P["steel"])


class KatanaChickLegs(Legs):
    """Jumpsuit legs with the black side stripe. Fighting stance when standing still."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        stance = 1 if pose.swing == 0 and not pose.tuck else 0
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s + (stance if front else -2 * stance)
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            suit = P["suit"] if front else P["suit_sh"]
            c.line(cx - 1, hip, fx, foot_y - 1, suit, width=3)
            if front:
                c.line(cx, hip, fx + 1, foot_y - 1, P["stripe"])
            c.rect(fx, foot_y, 4, 1, P["shoe"])
            c.rect(fx - 1, foot_y + 1, 6, 1, P["shoe"])
            if front:
                c.set(fx + 2, foot_y, P["sole"])               # stripe on the sneaker


class KatanaChickTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 2, top, 6, 1, P["suit"])
        c.rect(cx - 3, top + 1, 7, 10, P["suit"])
        c.rect(cx - 3, hip, 7, 1, P["suit_sh"])
        c.vline(cx + 3, top + 1, hip - 1, P["suit_hi"])
        c.vline(cx - 3, top + 1, hip, P["suit_sh"])
        c.vline(cx, top + 2, hip, P["stripe"])                 # the stripe, all the way down
        c.hline(cx + 1, cx + 3, top, P["stripe"])              # black collar
        c.set(cx + 3, top + 1, P["stripe"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "...hhhhh...",
    "..hHHHHHhh.",
    ".HHHHHHHHHH",
    "RRRRRRRRRRR",
    "HHHHHHHHHSS",
    "HHHHHHHSSSS",
    "HHHHHHSSBBS",
    "HHHHHSSSSES",
    ".HHHSSSSSSN",
    ".HHHsSSSSS.",
    "..HHsSSSMS.",
    "...sSSSSS..",
    "....sSSS...",
]


class KatanaChickHead(Head):
    """Ponytail and headband tails trail behind her and react to how fast she moves."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 5, ny - 13
        sway = wave(pose.frame, pose.n)
        # (launch angle, gravity): angles from straight down, pi/2 = straight back
        a, curl = {
            "walk": (1.2, 0.05), "run": (1.75, 0.04), "jump": (1.95, 0.02),
            "hurt": (0.5, 0.03), "death": (0.5, 0.03),
        }.get(pose.anim, (0.95, 0.04))
        a += 0.1 * sway
        if pose.anim == "jump" and not pose.tuck:              # crouch: hair hangs
            a, curl = 0.95, 0.04
        # ponytail: tied high at the back, arcs out, then falls (or streams)
        rx, ry = x0, y0 + 2
        x, y = float(rx), float(ry)
        for i in range(13):
            w = 3 if i < 4 else 2 if i < 10 else 1
            xi, yi = round(x), round(y)
            c.rect(xi - w // 2, yi - w // 2, w, w, P["hair"])
            if 2 <= i <= 8:
                c.set(xi, yi - w // 2, P["hair_hi"])
            x -= math.sin(a)
            y += math.cos(a)
            a -= curl
        # headband tails, fluttering off the knot
        fast = pose.anim in ("walk", "run", "jump")
        for k, length in enumerate((5, 4)):
            flap = wave(pose.frame + 2 * k, pose.n) if fast else 0
            ex = rx - 1 - length + (0 if fast else 2)
            ey = ry + 3 + 2 * k + (1 if fast else 3) + flap
            c.line(rx - 1, ry + 2, ex, ey, P["band"] if k == 0 else P["band_sh"])
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "S": P["skin"], "s": P["skin_sh"],
            "R": P["band"], "B": P["hair"], "E": P["skin_sh"] if pose.blink else INK,
            "N": P["skin"], "M": P["skin_sh"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.set(rx, ry + 2, P["band_sh"])                        # knot
        c.set(rx - 1, ry, P["band"])                           # hair tie


# Blade direction for every draw_limb pose (the hand position comes from `targets`).
BLADE_DIR = {
    "crouch": (-1.0, 0.2), "up": (0.2, -1.0), "reach": (0.5, -0.85), "out": (0.85, -0.45),
    "windup": (-0.8, -0.6), "strike": (1.0, 0.12), "follow": (0.55, 0.85),
    "recover": (0.8, 0.6), "flail": (-0.3, -0.95), "use": (0.85, -0.45),
}


class KatanaChickArm(Arm):
    """Front hand never lets go of the katana. Attacks with a huge overhead slash."""
    species = SPECIES
    reach = 8
    fx_colors = (P["edge"], P["trail"])
    targets = {
        "windup": ((-0.35, -0.95), (-0.4, 0.85)),            # blade raised behind her head...
        "strike": ((0.75, 0.15), (-0.7, 0.55)),               # ...and brought all the way through
        "follow": ((0.7, 0.65), (-0.6, 0.7)),
    }

    def blade_tip(self, mode: str, sx: int, sy: int) -> tuple[float, float]:
        dx, dy = self.direction(mode, True)
        bx, by = BLADE_DIR[mode]
        n = math.hypot(bx, by)
        r = self.reach
        return sx + dx * r + bx / n * (BLADE + 2), sy + dy * r + by / n * (BLADE + 2)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if not front:
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 6, P["suit_sh"], width=2)
            c.rect(sx + dx, sy + 7, 2, 2, P["skin_sh"])
            return
        if pose.anim == "run":                                 # blade trails behind her
            hx, hy, blade = sx + 3, sy + 5, (-1.0, 0.25)
        else:                                                  # low ready
            hx, hy, blade = sx + 3 - pose.swing, sy + 6, (0.8, 0.55)
        c.line(sx, sy, sx + 1, sy + 3, P["suit"], width=2)
        c.line(sx + 1, sy + 4, hx, hy, P["suit"], width=2)
        katana(c, hx, hy, *blade)
        c.rect(hx, hy - 1, 2, 2, P["skin"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = P["suit"] if front else P["suit_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        if front:
            katana(c, hx, hy, *BLADE_DIR[mode])
        c.rect(hx, hy, 2, 2, P["skin"] if front else P["skin_sh"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        """Strike: a fat crescent from the wind-up to the strike. Follow: a thin tail
        of that arc plus a glint where the blade stopped."""
        if pose.fx == "swoosh":
            a0, a1, thick = "windup", "strike", 4
        else:
            a0, a1, thick = "strike", "follow", 1
        x0, y0 = self.blade_tip(a0, sx, sy)
        x1, y1 = self.blade_tip(a1, sx, sy)
        t0, t1 = math.atan2(y0 - sy, x0 - sx), math.atan2(y1 - sy, x1 - sx)
        if t1 < t0:
            t1 += math.tau
        r = math.hypot(x1 - sx, y1 - sy) - 1
        steps = 40
        for i in range(steps + 1):
            u = i / steps
            a = t0 + (t1 - t0) * u
            w = max(1, round(thick * math.sin(math.pi * min(1.0, u * 1.3))))   # fat in the middle
            for k in range(w):
                rr = r - k
                col = P["edge"] if k == 0 else P["trail"]
                x, y = round(sx + math.cos(a) * rr), round(sy + math.sin(a) * rr)
                if 2 <= x <= 45 and 2 <= y <= 45:                # clip, leaving room for the outline
                    fx.set(x, y, col)
        if pose.fx == "impact":
            star(fx, round(x1) + 1, min(round(y1), GROUND - 3), P["edge"], P["trail"], r=2)


GENES = dict(legs=KatanaChickLegs(), torso=KatanaChickTorso(), head=KatanaChickHead(), arm=KatanaChickArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
