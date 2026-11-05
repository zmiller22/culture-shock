"""Dominatrix: patent-black catsuit, red corset, peaked cap, thigh-high stilettos
and a bullwhip. You will address her as Madam."""

from ..canvas import Canvas
from ..palette import INK, DOMINATRIX as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "dominatrix"
PREFIX, SUFFIX = "Domi", "trix"


# Stiletto boot foot, top-left at the ankle. The heel spike is red (of course).
STILETTO = ["BBB..", "RBBB.", "R..BB"]


class DominatrixLegs(Legs):
    """Thigh-high patent boots on red stiletto heels."""
    species = SPECIES
    length = 13

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            fy = ground - lift
            latex = P["latex"] if front else P["latex_sh"]
            c.line(cx - 1, hip, fx, fy - 3, latex, width=3)
            c.stamp(fx, fy - 2, STILETTO, {"B": latex, "R": P["red"] if front else P["red_sh"]})
            # boot top: a red rim a third of the way down the thigh
            ky = hip + (fy - 3 - hip) // 3
            kx = round(cx - 1 + (fx - cx + 1) * (ky - hip) / max(1, fy - 3 - hip))
            c.hline(kx, kx + 2, ky, P["red"] if front else P["red_sh"])
            if front:                                          # shine down the shin
                c.line(kx + 2, ky + 2, fx + 2, fy - 3, P["latex_hi"])
                c.set(kx + 2, ky + 3, P["gloss"])
                c.set(fx + 3, fy - 1, P["latex_hi"])


class DominatrixTorso(Torso):
    """Catsuit with a cinched red corset."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 2, top, 5, 1, P["latex"])
        c.rect(cx - 3, top + 1, 7, 4, P["latex"])
        c.rect(cx - 2, top + 5, 5, 4, P["red"])                # cinched waist...
        c.rect(cx - 3, top + 9, 7, 2, P["red"])                # ...flaring to the hips
        c.hline(cx - 3, cx + 3, top + 4, P["red"])             # corset top edge
        c.vline(cx - 2, top + 5, top + 8, P["red_sh"])
        c.set(cx - 3, top + 9, P["red_sh"])
        c.vline(cx + 2, top + 5, top + 8, P["red_hi"])
        c.set(cx + 3, top + 9, P["red_hi"])
        for y in range(top + 5, top + 10, 2):                  # lacing
            c.set(cx, y, P["latex_sh"])
        c.hline(cx - 3, cx + 3, hip, P["latex"])               # catsuit below the corset
        c.vline(cx + 3, top + 1, top + 3, P["latex_hi"])
        c.set(cx + 3, top + 2, P["gloss"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "...cccccccc...",
    "..cCCCCCCCCgc.",
    "..CCCCCCCCCCCC",
    "...CCCCCCCCCC.",
    "...RRRRRRRRRB.",
    "..HHHHHHvVVVVV",
    ".HHHHHHsssss..",
    ".HHHHHSSSlEE..",
    ".HHHHHSSSSSS..",
    ".HhHHHsSSSSSN.",
    ".HHHHHHsSSSS..",
    ".HHHHHHHsSLL..",
    "..HHHHHHsSS...",
    "....HHH..s....",
]


class DominatrixHead(Head):
    """Sharp black bob under a patent peaked cap, cat-eye liner, red lips, studded collar."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 7, ny - 14
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        lid = P["skin_sh"] if pose.blink else INK
        key = {
            "c": P["latex_hi"], "C": P["latex"], "g": P["gloss"], "R": P["red"], "B": P["silver"],
            "v": P["latex"], "V": P["latex_hi"], "H": P["hair"], "h": P["hair_hi"],
            "S": P["skin"], "s": P["skin_sh"], "N": P["skin"],
            "l": lid, "E": P["skin_sh"] if pose.blink else INK, "L": P["lips"],
        }
        c.stamp(x0, y0, HEAD, key)
        if not pose.blink:
            c.set(x0 + 9, y0 + 6, INK)                         # winged liner
        # studded collar
        c.hline(nx - 1, nx + 1, ny - 1, P["latex"])
        c.set(nx, ny - 1, P["silver"])
        c.set(nx + 1, ny - 1, P["latex_hi"])


def bezier(p0, p1, p2, n: int = 16) -> list[tuple[int, int]]:
    """Quadratic curve from p0 to p2 pulled toward p1, as n + 1 pixel points."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((round(x), round(y)))
    return pts


def lash(c: Canvas, pts: list[tuple[int, int]]) -> None:
    """Braided whip along a polyline, clipped to the frame, ending in a pale popper."""
    pts = [(min(45, max(2, x)), min(GROUND, max(2, y))) for x, y in pts]
    for k, ((x0, y0), (x1, y1)) in enumerate(zip(pts, pts[1:])):
        c.line(x0, y0, x1, y1, P["whip_hi"] if k % 3 == 0 else P["whip"])
    c.set(*pts[-1], P["popper"])


def crack_tip(hx: int, hy: int) -> tuple[int, int]:
    """Where the whip snaps: up and ahead of the hand, but never off the frame."""
    return min(42, hx + 13), max(5, hy - 8)


class DominatrixArm(Arm):
    """Long patent gloves. The front hand never puts the whip down.
    Attacks with a bullwhip crack you can hear from the next level."""
    species = SPECIES
    reach = 9
    fx_colors = (P["spark"], "#ffffff")
    targets = {
        "windup": ((-0.45, -0.9), (-0.4, 0.85)),             # whip hand up behind her head...
        "strike": ((1.0, -0.25), (-0.7, 0.55)),              # ...throws it overhand...
        "follow": ((0.75, 0.0), (-0.6, 0.7)),                # ...and snaps it out straight
    }

    def whip_path(self, mode: str, hx: int, hy: int) -> list[tuple[int, int]]:
        """Points from the end of the handle to the tip, per arm pose."""
        if mode == "windup":                                  # trails down her back
            return bezier((hx - 1, hy - 1), (hx - 9, hy - 4), (hx - 11, hy + 12))
        if mode == "strike":                                  # rolls out over the top in an S
            a = bezier((hx + 2, hy - 1), (hx + 4, hy - 9), (hx + 8, hy - 7), 8)
            b = bezier((hx + 8, hy - 7), (hx + 12, hy - 5), (hx + 10, hy + 5), 8)
            return a + b[1:]
        if mode == "follow":                                  # dead straight: CRACK
            tx, ty = crack_tip(hx, hy)
            return bezier((hx + 2, hy), ((hx + tx) // 2 + 1, hy - 1), (tx, ty))
        # anything else: hangs from the hand and pools on the floor
        return bezier((hx + 1, hy + 1), (hx + 3, GROUND + 4), (hx + 9, GROUND))

    def handle(self, c: Canvas, hx: int, hy: int, dx: int, dy: int) -> None:
        """Red grip from (hx, hy) toward (dx, dy), silver pommel behind the fist."""
        c.line(hx, hy, hx + dx, hy + dy, P["red_sh"])
        c.set(hx + dx, hy + dy, P["red"])
        c.set(hx - (dx > 0), hy - (dy > 0), P["silver"])

    def glove(self, c: Canvas, sx: int, sy: int, ex: int, ey: int, hx: int, hy: int, front: bool) -> None:
        latex = P["latex"] if front else P["latex_sh"]
        c.stroke(sx, sy, ex, ey, latex, 2)
        c.stroke(ex, ey, hx, hy, latex, 2)
        if front:                                             # patent shine along the forearm
            c.line(ex, ey, (ex + hx) // 2, (ey + hy) // 2, P["latex_hi"])
            c.set(ex, ey, P["gloss"])
        c.rect(hx, hy, 2, 2, latex)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if not front:
            if pose.anim == "idle":                           # hand on hip, elbow out
                self.glove(c, sx, sy, sx - 3, sy + 4, sx, sy + 8, False)
                return
            dx = 2 * pose.swing
            self.glove(c, sx, sy, sx + dx // 2, sy + 4, sx + dx, sy + 7, False)
            return
        # whip in hand, tail dragging on the floor ahead of her
        if pose.anim == "idle":                               # tap, tap, tap...
            hx, hy = sx + 4, sy + 6 - pose.frame % 2
            ex, ey = sx + 1, sy + 4
            flick = (0, 2, 1, -1)[pose.frame % 4]
        else:
            dx = -2 * pose.swing
            hx, hy = sx + dx + 2, sy + 7
            ex, ey = sx + dx // 2, sy + 4
            flick = (1, 3, 0, 3)[pose.frame % 4] if pose.anim == "run" else (0, 1, 0, 1)[pose.frame % 4]
        self.glove(c, sx, sy, ex, ey, hx, hy, True)
        lash(c, bezier((hx + 3, hy + 2), (hx + 6, GROUND + 2), (hx + 12, GROUND - 1 - flick)))
        self.handle(c, hx + 1, hy + 1, 2, 1)
        c.rect(hx, hy, 2, 2, P["latex"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        self.glove(c, sx, sy, ex, ey, hx, hy, front)
        if front:
            lash(c, self.whip_path(mode, hx, hy))
            c.rect(hx, hy, 2, 2, P["latex"])
            c.set(hx + 1, hy, P["latex_hi"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                               # whoosh lines riding over the loop
            loop = self.whip_path("strike", hx, hy)
            for (i0, i1), (ox, oy), col in (((3, 10), (-1, -2), "#ffffff"), ((4, 8), (-2, -4), P["whip_hi"])):
                pts = [(min(45, x + ox), max(2, y + oy)) for x, y in loop[i0:i1]]
                for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                    fx.line(x0, y0, x1, y1, col)
            return
        x, y = crack_tip(hx, hy)                              # CRACK
        star(fx, x, y, P["spark"], "#ffffff", r=3)
        for dx, dy in ((-3, -3), (3, 3), (-3, 3), (3, -3)):
            fx.set(x + dx, y + dy, "#ffffff")


GENES = dict(legs=DominatrixLegs(), torso=DominatrixTorso(), head=DominatrixHead(), arm=DominatrixArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
