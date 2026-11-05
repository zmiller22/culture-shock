"""Crawling baby: a diapered infant on all fours, built entirely out of head. One curl,
one pacifier, one rattle, zero fear. The lab's youngest subject, and its most dangerous.

The baby is horizontal, so the genes split like the slug's: the legs are the knees
and shins in the crawl plus the diaper they carry, the torso is the chubby back
with its bib, the head is the oversized head, and the arms are the hands that plant
on the floor (the front one never lets go of its rattle).
"""

import math

from ..canvas import Canvas
from ..palette import INK, CRAWLING_BABY as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "crawling_baby"
PREFIX, SUFFIX = "Baby", "babe"


FOOT = [".ff", "fFf", "fFs", ".ss"]          # little foot, sole up
BIB = ["TTTTT", "BBBBB", "BBBbB", "BBBBB", ".BBB."]


class BabyLegs(Legs):
    """Knees on the floor, shins trailing behind, little feet soles-up. The diaper
    rides on top. Crawls on the diagonal: near knee with the far hand."""
    species = SPECIES
    length = 7

    def leg(self, c: Canvas, cx: int, hip: int, kx: int, ky: int, near: bool) -> None:
        skin, sh = (P["skin"], P["skin_sh"]) if near else (P["skin_sh"], P["skin_dk"])
        c.stroke(cx - 4, hip + 1, kx, ky - 1, skin, 4)            # chubby thigh
        c.oval(kx - 2, ky - 2, 5, 4, skin)                        # knee
        c.stroke(kx - 1, ky, kx - 7, ky - 1, skin, 3)             # shin along the floor
        c.stamp(kx - 10, ky - 4, FOOT, {"f": skin, "F": P["skin_hi"] if near else skin, "s": sh})
        if near:
            c.set(kx, ky, sh)                                     # knee dimple
            c.hline(kx - 6, kx - 2, ky + 1, sh)

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        stride = {"run": 4}.get(pose.anim, 2)
        for near in (False, True):
            s = (-pose.swing if near else pose.swing) * stride // 2
            lifting = pose.lift and (pose.frame % 4 == (1 if near else 3))
            kx = cx - 3 + s - (0 if near else 2)
            ky = ground - 1 - (pose.lift if lifting else 0)
            self.leg(c, cx, hip, kx, ky, near)
        # the diaper: puffy, with a waistband and a safety pin
        x0, y0 = cx - 10, hip - 6
        c.oval(x0, y0, 12, 10, P["diaper"])
        for x in range(x0, x0 + 12):                               # shade the underside
            col = [y for y in range(y0, y0 + 10) if c.get(x, y) == P["diaper"]]
            if col:
                c.vline(x, col[-2], col[-1], P["diaper_sh"])
        c.hline(x0 + 3, x0 + 10, y0 + 1, P["diaper_sh"])           # waistband
        c.line(x0 + 2, y0 + 6, x0 + 5, y0 + 8, P["diaper_sh"])     # leg crease
        c.stamp(x0 + 8, y0 + 2, ["pP", ".p"], {"p": P["pin"], "P": P["diaper"]})


class BabyBack(Torso):
    """Chubby back and round belly, horizontal, with a bib hanging under the chin."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        breath = 1 if pose.anim == "idle" and pose.bob else 0
        top = hip - 8
        c.oval(cx - 3, top, 14, 10 + breath, P["skin"])
        for x in range(cx - 3, cx + 11):                           # back highlight, belly shadow
            col = [y for y in range(top, hip + 3) if c.get(x, y) == P["skin"]]
            if col:
                c.set(x, col[-1], P["skin_sh"])
                if cx - 1 <= x <= cx + 6:
                    c.set(x, col[0] + 1, P["skin_hi"])
        c.set(cx + 2, hip - 1, P["skin_sh"])                       # belly button
        # bib, hanging from the neck
        c.stamp(cx + 7, hip - 4, BIB, {"T": P["bib_trim"], "B": P["bib"], "b": P["bib_sh"]})
        return Anchors(neck=(cx + 7, hip - 5), shoulder=(cx + 5, hip - 4), top=top, bottom=hip)


CURL = [".hh", "h.h", "..h"]


class BabyHead(Head):
    """A big round head with one curl, a rosy cheek and a pacifier. Wails when hit."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        wail = pose.anim in ("hurt", "death")
        x0, y0 = nx - 4, ny - 12
        c.oval(x0, y0, 14, 13, P["skin"])
        for x in range(x0, x0 + 14):                               # jaw and back of the head in shade
            col = [y for y in range(y0, y0 + 13) if c.get(x, y) == P["skin"]]
            if col:
                c.set(x, col[-1], P["skin_sh"])
                if x < x0 + 3:
                    c.set(x, col[0] + 3, P["skin_sh"])
        c.hline(x0 + 5, x0 + 9, y0 + 1, P["skin_hi"])              # shiny forehead
        c.set(x0 + 10, y0 + 2, P["skin_hi"])
        c.stamp(x0 + 5, y0 - 3, CURL, {"h": P["hair"]})            # the curl
        c.set(x0 + 7, y0 - 1, P["hair_sh"])
        c.stamp(x0 + 3, y0 + 5, [".e", "eE", ".e"], {"e": P["skin_sh"], "E": P["skin_dk"]})   # ear
        c.set(x0 + 14, y0 + 7, P["skin"])                          # button nose
        c.hline(x0 + 9, x0 + 10, y0 + 9, P["blush"])               # rosy cheek
        ex, ey = x0 + 9, y0 + 5
        if wail:                                                   # eyes squeezed shut, mouth wide open
            c.stamp(ex - 1, ey, ["k..", ".kk", "k.."], {"k": INK})
            c.rect(x0 + 11, y0 + 9, 3, 3, P["mouth"])
            c.hline(x0 + 11, x0 + 12, y0 + 11, P["tongue"])
            for dx, dy in ((-3, -1), (-4, 0), (3, -2), (4, -1)):   # tears squirting both ways
                c.set(ex + dx, ey + dy, P["tear"])
            c.stamp(x0 + 15, y0 - 2, [".r.", "rPr", ".P."], {"r": P["ring"], "P": P["paci"]})   # pacifier, airborne
            return
        if pose.blink:
            c.hline(ex, ex + 1, ey + 1, INK)
        else:
            c.rect(ex, ey, 2, 3, INK)
            c.set(ex + 1, ey, "#ffffff")                           # sparkle
        suck = pose.anim == "idle" and pose.frame % 2
        c.stamp(x0 + 13 - suck, y0 + 8, ["P.", "Pr", "P.r", "Pr"], {"P": P["paci"], "r": P["ring"]})
        c.set(x0 + 13 - suck, y0 + 8, P["paci_hi"])


def rattle_ball(hx: int, hy: int, dx: float, dy: float) -> tuple[int, int]:
    """Where the rattle's ball ends up, held at (hx, hy) pointing along (dx, dy)."""
    d = math.hypot(dx, dy) or 1
    return min(40, round(hx + 1 + dx / d * 5)), min(GROUND - 4, round(hy + dy / d * 5))


class BabyArm(Arm):
    """Chubby arm that plants a fist on the floor at every step. The front fist holds
    a rattle, and the rattle is a weapon: wind up overhead, then BONK."""
    species = SPECIES
    reach = 8
    fx_colors = (P["handle"], P["rattle_hi"])
    targets = {
        "crouch": ((0.3, 1.0), (0.0, 1.0)),
        "reach": ((1.0, 0.25), (-0.25, -0.95)),              # pounce: arms out under the chin
        "out": ((0.9, 0.45), (-0.8, -0.5)),
        "windup": ((-0.3, -0.95), (0.1, 1.0)),               # rattle up over the head...
        "strike": ((0.85, 0.55), (0.0, 1.0)),                # ...BONK
        "follow": ((0.7, 0.75), (0.1, 1.0)),
        "recover": ((0.4, 0.9), (0.1, 1.0)),
        "flail": ((-0.5, -0.85), (-0.9, -0.4)),              # waving it around, inconsolable
    }

    def rattle(self, c: Canvas, hx: int, hy: int, dx: float, dy: float) -> None:
        """Rattle gripped at (hx, hy), pointing along (dx, dy)."""
        bx, by = rattle_ball(hx, hy, dx, dy)
        c.line(hx + 1, hy, bx, by, P["handle"])
        c.oval(bx - 1, by - 1, 4, 4, P["rattle"])
        c.set(bx, by, P["rattle_hi"])
        c.set(bx + 1, by + 1, P["rattle_sh"])

    def fist(self, c: Canvas, hx: int, hy: int, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        c.rect(hx - 1, hy, 3, 2, skin)
        c.set(hx + 1, hy, P["skin_hi"] if front else skin)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        s = pose.swing if front else -pose.swing
        stride = {"run": 3}.get(pose.anim, 2)
        lifting = pose.lift and (pose.frame % 4 == (3 if front else 1))
        hx = sx + 2 + s * stride - (0 if front else 2)
        hy = min(GROUND - 1, sy + 10) - (pose.lift + 1 if lifting else 0)
        ex, ey = elbow(sx, sy, hx, hy, 1)
        c.stroke(sx, sy, ex, ey, skin, 3)
        c.stroke(ex, ey, hx, hy - 1, skin, 3)
        self.fist(c, hx, hy, front)
        if front:
            self.rattle(c, hx, hy, 0.6, -1.0)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        hy = min(hy, GROUND - 1)
        ex, ey = elbow(sx, sy, hx, hy, 1)
        c.stroke(sx, sy, ex, ey, skin, 3)
        c.stroke(ex, ey, hx, hy, skin, 3)
        self.fist(c, hx, hy, front)
        if front:                                             # swung along the arm, otherwise held upright
            swung = mode in ("windup", "strike", "follow", "flail")
            self.rattle(c, hx, hy, *((hx - sx, hy - sy - 4) if swung else (0.6, -1.0)))

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        bx, by = rattle_ball(hx, hy, hx - sx, hy - sy - 4)
        if pose.fx == "swoosh":                                   # rattle rattle: shake marks either side
            for dx, dy in ((-2, -3), (1, -4), (4, -3), (5, 0)):
                fx.set(bx + dx, by + dy, "#ffffff")
            fx.hline(bx - 6, bx - 4, by - 2, P["rattle_hi"])      # speed lines behind the swing
            fx.hline(bx - 7, bx - 5, by + 3, "#ffffff")
        else:                                                     # BONK
            x = min(bx + 3, 40)
            star(fx, x, min(by + 1, 40), "#ffffff", P["handle"], r=4)
            for ox, oy in ((-1, -6), (5, -4)):                    # little dizzy sparkles
                fx.set(x + ox, by + oy, P["rattle_hi"])


GENES = dict(legs=BabyLegs(), torso=BabyBack(), head=BabyHead(), arm=BabyArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
