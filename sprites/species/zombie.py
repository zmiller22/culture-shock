"""Zombie: grey-green, stitched up, shirt in tatters. Arms out, jaw slack,
shuffling toward the nearest brain at a leisurely pace."""

from ..canvas import Canvas
from ..palette import INK, ZOMBIE as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "zombie"
PREFIX, SUFFIX = "Zom", "bie"


def stitches(c: Canvas, x0: int, x1: int, y: int, scar: str = P["wound"]) -> None:
    """A horizontal scar with little cross-stitches every other pixel."""
    c.hline(x0, x1, y, scar)
    for x in range(x0 + 1, x1 + 1, 2):
        c.set(x, y - 1, P["stitch"])
        c.set(x, y + 1, P["stitch"])


class ZombieLegs(Legs):
    species = SPECIES
    length = 13

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift // 2               # the back foot drags
            foot_y = ground - 1 - lift
            skin = P["skin"] if front else P["skin_sh"]
            c.line(cx - 1, hip, fx, foot_y - 1, skin, width=3)
            # pant leg torn off above the ankle, ragged hem
            kx = round(cx - 1 + (fx - cx + 1) * 0.65)
            ky = round(hip + (foot_y - 1 - hip) * 0.65)
            c.line(cx - 1, hip, kx, ky, P["pants"] if front else P["pants_sh"], width=3)
            c.set(kx + (1 if front else 2), ky + 1, P["pants"] if front else P["pants_sh"])
            shoe = P["shoe"] if front else INK
            c.rect(fx, foot_y, 4, 1, shoe)
            c.rect(fx - 1, foot_y + 1, 5, 1, shoe)
            if front:
                c.set(fx + 4, foot_y + 1, P["skin"])          # toe poking out of the shoe
                c.set(fx + 1, foot_y, P["shoe_hi"])
            elif lift == 0 and pose.lift:
                c.set(fx - 2, foot_y + 1, shoe)               # drag scuff


class ZombieTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        for y in range(top, hip):                              # hunched: shoulders lean forward
            off = (hip - y) // 4
            x0 = cx - 4 + off + (1 if y == top else 0)
            c.hline(x0, cx + 4 + off - (1 if y == top else 0), y, P["shirt"])
            c.set(x0, y, P["shirt_sh"])
        c.hline(cx - 4, cx + 4, hip, P["pants"])               # waistband
        for x in range(cx - 3, cx + 5, 2):                     # torn hem, belly showing through
            c.set(x, hip - 1, P["skin_sh"])
        c.oval(cx + 1, top + 5, 3, 3, P["skin"])               # rip in the shirt...
        c.set(cx + 2, top + 6, P["skin_dk"])                   # ...and a nasty bruise
        stitches(c, cx - 2, cx + 1, top + 3)                   # stitched-up shirt tear
        c.set(cx - 3, top + 8, P["shirt_sh"])                  # moth holes
        c.set(cx + 4, top + 9, P["shirt_sh"])
        return Anchors(neck=(cx + 3, top + 1), shoulder=(cx + 1, top + 2), top=top, bottom=hip)


HEAD = [
    "...HhH.H....",
    "..HHHHHHHh..",
    ".HHSSSSSHHS.",
    ".HSSSSSSSSS.",
    ".HSSSSSSSSS.",
    ".sSSSSkkkSS.",
    ".ssSSSkpkSSN",
    ".sSSSSSkSSSS",
    ".sSSSSSSSSs.",
    "..sSSSSmmmm.",
    "...sSSSmTmT.",
    "....sSSmmm..",
    ".....sSSSS..",
]


class ZombieHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        loll = 1 if pose.lift else 0                           # head lolls forward on the shuffle
        c.rect(nx - 1, ny - 2, 3, 3, P["skin_sh"])
        key = {
            "H": P["hair"], "h": P["hair_hi"], "S": P["skin"], "s": P["skin_sh"], "N": P["skin_sh"],
            "k": P["socket"], "p": P["socket"] if pose.blink else P["pupil"],
            "m": P["mouth"], "T": P["teeth"],
        }
        x0, y0 = nx - 5 + loll, ny - 12 + loll
        c.stamp(x0, y0, HEAD, key)
        stitches(c, x0 + 3, x0 + 7, y0 + 3, P["skin_dk"])     # forehead scar
        if pose.anim == "attack" and pose.frame in (1, 2):    # CHOMP: jaw drops wide open
            c.hline(x0 + 7, x0 + 10, y0 + 12, P["mouth"])
            c.set(x0 + 8, y0 + 12, P["teeth"])


class ZombieArm(Arm):
    """Torn sleeve, rotting forearm, limp hand -- held straight out in front, always.
    Attacks with a lunging grab and a bite."""
    species = SPECIES
    reach = 10
    fx_colors = ("#ffffff", P["teeth"])
    targets = {                                                # both arms stay out front
        "crouch":  ((0.85, 0.45), (0.8, 0.35)),
        "up":      ((0.8, -0.6), (0.7, -0.7)),
        "reach":   ((0.95, -0.35), (0.9, -0.45)),
        "out":     ((1.0, -0.15), (0.95, -0.3)),
        "windup":  ((0.8, -0.6), (0.7, -0.7)),               # BRAAAINS...
        "strike":  ((1.0, 0.0), (1.0, -0.15)),               # ...lunge!
        "follow":  ((1.0, 0.15), (0.95, 0.0)),
        "recover": ((0.95, 0.3), (0.9, 0.2)),
    }

    def hand(self, c: Canvas, hx: int, hy: int, front: bool, grab: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        c.rect(hx, hy, 2, 2, skin)
        if grab:                                               # fingers splayed forward
            c.set(hx + 2, hy - 1, skin)
            c.set(hx + 2, hy + 1, skin)
        else:                                                  # limp, dangling fingers
            c.vline(hx + 1, hy + 2, hy + 3, skin)
            c.set(hx + 2, hy + 2, skin)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        dy = pose.swing if front else -pose.swing
        dy += (0, 0, 1, 1)[pose.frame % 4] if pose.anim == "idle" else 0
        lift = 0 if front else -1                              # back arm peeks out above
        ex, ey = sx + 4, sy + lift + dy // 2
        hx, hy = sx + 9, sy + lift + dy
        c.stroke(sx, sy, ex, ey, P["shirt"] if front else P["shirt_sh"], 2)
        c.set(ex, ey + 2, P["shirt_sh"])                       # tattered sleeve
        c.stroke(ex + 1, ey, hx, hy, P["skin"] if front else P["skin_sh"], 2)
        self.hand(c, hx, hy, front, grab=False)
        if front:
            c.set(ex + 3, ey, P["skin_hi"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1)
        c.stroke(sx, sy, ex, ey, P["shirt"] if front else P["shirt_sh"], 2)
        c.stroke(ex, ey, hx, hy, P["skin"] if front else P["skin_sh"], 2)
        self.hand(c, hx, hy, front, grab=mode in ("windup", "strike", "follow"))

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                                # lunge speed lines
            for dy, x0 in ((-3, hx - 7), (0, hx - 9), (3, hx - 6)):
                fx.hline(x0, hx - 4, hy + dy, P["skin_hi"])
            return
        x, y = min(hx + 4, fx.w - 8), hy - 2                   # CHOMP: a set of bite marks
        fx.stamp(x, y, ["TTTTT", "T.T.T", ".....", "T.T.T", "TTTTT"], {"T": "#ffffff"})
        for dx, dy in ((-1, -2), (5, -2), (-1, 6), (5, 6)):
            fx.set(x + dx, y + dy, P["teeth"])


GENES = dict(legs=ZombieLegs(), torso=ZombieTorso(), head=ZombieHead(), arm=ZombieArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
