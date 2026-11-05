"""Detective: trench coat, collar up, fedora pulled low, pipe going.
It was a dark and stormy lab. The dame had six legs."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, DETECTIVE as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "detective"
PREFIX, SUFFIX = "Sherl", "lock"


class DetectiveLegs(Legs):
    """Pressed grey slacks and scuffed brogues."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1, hip, fx, foot_y - 1, P["pants"] if front else P["pants_sh"], width=3)
            shoe = P["shoe"] if front else INK
            c.rect(fx, foot_y, 4, 1, shoe)
            c.rect(fx - 1, foot_y + 1, 6, 1, shoe)
            if front:
                c.set(fx + 2, foot_y, P["shoe_hi"])            # polished toe cap


class DetectiveTorso(Torso):
    """Belted trench coat. The skirt hangs over the legs and flaps when he hurries."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        # coat skirt: flares toward the hem, trails behind on the run
        trail = {"run": 2, "jump": 1}.get(pose.anim, 0) + (wave(pose.frame, pose.n) if pose.anim == "run" else 0)
        hem = 6 - pose.tuck // 2
        for i in range(hem + 1):
            back = cx - 4 - (i * (1 + trail)) // 3
            front = cx + 4 + i // 4 + (pose.swing > 0 and i > 3)
            c.hline(back, front, hip + i, P["coat"])
            c.set(back, hip + i, P["coat_sh"])
        c.vline(cx + 2, hip + 1, hip + hem, P["coat_sh"])        # where the coat overlaps
        c.hline(cx - 4 - (hem * (1 + trail)) // 3, cx + 4 + hem // 4, hip + hem, P["coat_sh"])
        # the coat proper
        c.rect(cx - 3, top, 7, 1, P["coat"])
        c.rect(cx - 4, top + 1, 9, 11, P["coat"])
        c.vline(cx - 4, top + 1, hip, P["coat_sh"])
        c.vline(cx + 4, top + 2, hip - 4, P["coat_hi"])
        c.stamp(cx + 1, top, ["sWT", ".WT"], {"s": P["coat_sh"], "W": P["shirt"], "T": P["tie"]})
        c.line(cx + 1, top + 2, cx + 3, top + 4, P["coat_sh"])  # lapel
        for y in (top + 5, top + 7):                              # double-breasted
            c.set(cx + 1, y, P["button"])
            c.set(cx + 3, y, P["button"])
        c.hline(cx - 4, cx + 4, hip - 2, P["coat_dk"])            # belt, cinched
        c.set(cx + 2, hip - 2, P["brass"])
        c.stamp(cx - 6, hip - 2, ["dd.", "d..", "d.."], {"d": P["coat_dk"]})  # loose belt end
        # collar turned up against the rain
        c.stamp(cx - 5, top - 5, ["c...", "cC..", "cCC.", "cCCC", ".cCC"], {"c": P["coat_sh"], "C": P["coat"]})
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


# Fedora snapped down over the eyes, brim up at the back; long nose; five o'clock shadow.
HEAD = [
    "......hhFF.F...",
    ".....hFFFFFFF..",
    "....hFFFFFFFFF.",
    ".F..RRRRRRRRRR.",
    "..FFFFFFFFFFFFF",
    "...kkkkkkkkkkFF",
    "...HHsssssssss.",
    "...HHssssssEss.",
    "...HHSSSSSSSSSN",
    "...HSeSSSSSSSSN",
    "....SSSSSSSSS..",
    "....sSSSSSSMS..",
    "....sstttttt...",
    ".....sttttt....",
]


class DetectiveHead(Head):
    """The pipe belongs to the head, so it keeps smoking whatever body it ends up on."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 7, ny - 15
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "h": P["hat_hi"], "F": P["hat"], "k": P["hat_sh"], "R": P["band"],
            "H": P["hair"], "S": P["skin"], "s": P["skin_sh"], "e": P["skin_sh"],
            "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"],
            "t": P["stubble"], "M": P["skin_sh"],
        }
        c.stamp(x0, y0, HEAD, key)
        # bent briar pipe: stem out of the corner of the mouth, bowl up
        bx, by = x0 + 13, y0 + 12
        c.line(x0 + 11, y0 + 11, bx, by, P["pipe"])
        c.rect(bx, by - 1, 2, 3, P["pipe"])
        c.set(bx + 1, by, P["pipe_hi"])
        c.set(bx + 1, by - 1, P["ember"] if pose.frame % 2 == 0 else P["pipe_hi"])
        if pose.flash or pose.melt:
            return
        # a wisp of smoke, drifting up and away from the brim
        d = pose.frame % 2
        for dx, dy in ((2, -3), (3, -4), (3, -5), (4, -6)):
            c.set(bx + dx + d, by + dy - d, P["smoke"])


# Direction the magnifier's handle points out of the hand, per arm pose.
GLASS_DIR = {
    "crouch": (0.6, -0.8), "up": (0.3, -1.0), "reach": (0.7, -0.7), "out": (0.9, -0.5),
    "windup": (0.8, -0.6), "strike": (1.0, -0.3), "follow": (1.0, -0.2),
    "recover": (0.7, -0.7), "flail": (-0.4, -0.9), "use": (0.9, -0.45),
}


def magnifier(c: Canvas, hx: int, hy: int, dx: float, dy: float) -> tuple[int, int]:
    """Magnifying glass gripped at (hx, hy), handle pointing along (dx, dy). Returns the lens center."""
    n = math.hypot(dx, dy) or 1
    dx, dy = dx / n, dy / n
    c.line(hx, hy, round(hx + dx * 3), round(hy + dy * 3), P["handle"])
    lx, ly = round(hx + dx * 6), round(hy + dy * 6)
    c.stamp(lx - 2, ly - 2, [".BBB.", "BLLLB", "BLLLB", "BLLLB", ".BBB."], {"B": P["brass"], "L": P["lens"]})
    c.set(lx - 1, ly - 1, P["lens_hi"])
    c.set(lx + 2, ly + 1, P["brass_sh"])
    return lx, ly


class DetectiveArm(Arm):
    """Trench-coat sleeve. Front hand holds a magnifying glass; the back one stays in his pocket.
    Attack: focuses a sunbeam into a very hot little dot."""
    species = SPECIES
    reach = 8
    fx_colors = (P["beam_hot"], P["beam"])
    targets = {
        "windup":  ((0.8, -0.5), (-0.4, 0.85)),              # hold it up to catch the light...
        "strike":  ((0.5, 0.15), (-0.7, 0.55)),              # ...and focus it on the floor ahead
        "follow":  ((0.5, 0.25), (-0.6, 0.7)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if not front:                                          # hand in the coat pocket
            dx = pose.swing
            c.line(sx, sy, sx + dx, sy + 6, P["coat_sh"], width=2)
            c.hline(sx + dx, sx + dx + 1, sy + 7, P["coat_dk"])
            return
        bob = (0, 0, 1, 1)[pose.frame % 4] if pose.anim == "idle" else 0
        hx, hy = sx + 4 - pose.swing, sy + 5 + bob
        c.stroke(sx, sy, sx, sy + 4, P["coat"], 2)
        c.stroke(sx + 1, sy + 5, hx - 1, hy, P["coat"], 2)
        c.vline(hx - 1, hy, hy + 1, P["coat_sh"])              # cuff
        magnifier(c, hx + 1, hy, 0.6, -0.8)
        c.rect(hx, hy, 2, 2, P["skin"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = P["coat"] if front else P["coat_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        if front:
            lx, ly = magnifier(c, hx + 1, hy, *GLASS_DIR[mode])
            if mode == "windup":                               # catching the sun
                for dx, dy in ((0, -4), (4, 0), (-4, 0), (3, -3), (-3, -3)):
                    c.set(lx + dx, ly + dy, P["beam"])
        c.rect(hx, hy, 2, 2, P["skin"] if front else P["skin_sh"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        dx, dy = self.direction("strike", True)                # aim from where the glass was held
        gx, gy = sx + round(dx * self.reach) + 1, sy + round(dy * self.reach)
        bx, by = GLASS_DIR["strike"]
        n = math.hypot(bx, by)
        lx, ly = round(gx + bx / n * 6), round(gy + by / n * 6)       # lens center
        tx, ty = min(lx + 8, fx.w - 6), min(ly + 10, GROUND - 1)     # focal point, just ahead
        if pose.fx == "swoosh":                                # a cone of sunlight narrowing to a point
            vx, vy = tx - lx, ty - ly
            n = math.hypot(vx, vy)
            px, py = -vy / n, vx / n
            for k in (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5):
                x0, y0 = round(lx + vx / n * 3 + px * k), round(ly + vy / n * 3 + py * k)
                fx.line(x0, y0, tx, ty, P["beam"])
            fx.line(round(lx + vx / n * 3), round(ly + vy / n * 3), tx, ty, P["beam_hot"])
            star(fx, tx, ty, P["beam_hot"], P["beam"], r=2)
        else:                                                  # it smolders, then catches
            fx.stamp(tx - 2, ty - 3, ["..r..", ".rOr.", ".OYO.", "rOYOr", ".rrr."],
                     {"r": P["fire_r"], "O": P["fire"], "Y": P["beam"]})
            for ex, ey in ((-3, -5), (2, -6), (0, -8)):
                fx.set(tx + ex, ty + ey, P["fire"])                  # embers
            fx.stamp(tx - 1, ty - 12, [".ss", "ss.", ".s."], {"s": P["smoke"]})


GENES = dict(legs=DetectiveLegs(), torso=DetectiveTorso(), head=DetectiveHead(), arm=DetectiveArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
