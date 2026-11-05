"""Pageant queen: big hair, tiara, sash, sequined gown, roses, parade wave.
Smiles through everything. Including combat."""

from ..canvas import Canvas
from ..palette import INK, PAGEANT_QUEEN as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "pageant_queen"
PREFIX, SUFFIX = "Diva", "queen"


def bouquet(c: Canvas, x: int, y: int, tilt: int = 0) -> None:
    """Bunch of roses, stems at (x, y), blooms up and forward (tilt leans it)."""
    c.line(x, y, x + 2 + tilt, y - 3, P["leaf"])
    c.line(x - 1, y, x + 1 + tilt, y - 3, P["leaf"])
    c.set(x, y - 1, P["wrap"])                                # paper wrap
    c.set(x + 1, y - 1, P["wrap"])
    bx, by = x + tilt, y - 6
    c.oval(bx, by, 5, 4, P["rose"])
    for dx, dy in ((1, 0), (3, 1), (2, 2)):
        c.set(bx + dx, by + dy, P["rose_hi"])
    c.set(bx - 1, by + 2, P["leaf"])


def sparkle(c: Canvas, x: int, y: int, col: str = "#ffffff", big: bool = False) -> None:
    """Four-point twinkle."""
    c.set(x, y, col)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        c.set(x + dx, y + dy, col)
        if big:
            c.set(x + 2 * dx, y + 2 * dy, col)


class PageantQueenLegs(Legs):
    """The legs gene is the gown skirt: an A-line that swishes with every step."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        hem = ground - 1
        rows = max(1, hem - hip)
        s = pose.swing
        # shoe tips peeking out under the hem
        for front in (False, True):
            k = pose.swing if front else -pose.swing
            fx = cx + 1 + 2 * k - (0 if front else 3)
            fy = ground - (0 if front else pose.lift)
            c.hline(fx, fx + 2, fy, P["shoe"] if front else P["gown_sh"])
        for y in range(hip, hem + 1):
            t = (y - hip) / rows
            sh = round(s * 1.5 * t)                               # the whole hem swings...
            x0 = cx - 3 - round(5 * t ** 1.3) + sh - round(max(0, -s) * t)   # ...and the
            x1 = cx + 3 + round(4 * t ** 1.2) + sh + round(max(0, s) * t)    # leading edge flares
            c.hline(x0, x1, y, P["gown"])
            c.set(x0, y, P["gown_dk"])
            c.hline(x0 + 1, x0 + 1 + round(2 * t), y, P["gown_sh"])
            c.set(x1, y, P["gown_hi"])
            if t > 0.2:                                           # folds fanning out
                for fold in (0.35, 0.7):
                    c.set(round(x0 + (x1 - x0) * fold + s * t), y, P["gown_sh"])
        span = c.row_span(hem)
        if span:                                                # wavy hem
            for x in range(span[0], span[1] + 1, 2):
                c.set(x + (pose.frame % 2), hem, P["gown_sh"])
        # sequins: a fixed scatter that twinkles in turn
        for i, (dx, dy) in enumerate(((1, 3), (-3, 6), (3, 8), (-5, 10), (0, 11), (5, 12), (-2, 4))):
            x, y = cx + dx, hip + dy
            if y < hem and c.get(x, y) == P["gown"]:
                c.set(x, y, P["sparkle"] if (i + pose.frame) % 3 == 0 else P["gown_hi"])


class PageantQueenTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 1, top, 3, 2, P["skin"])                     # neck and collarbone
        c.rect(cx - 3, top + 2, 7, 8, P["gown"])
        c.rect(cx - 2, hip - 1, 5, 2, P["gown"])                 # nipped-in waist
        c.vline(cx - 3, top + 2, hip - 2, P["gown_sh"])
        c.vline(cx + 3, top + 2, hip - 2, P["gown_hi"])
        c.hline(cx - 2, cx + 2, hip, P["gown_sh"])
        # the sash: shoulder to hip, with the winner's lettering
        for i in range(9):
            x, y = cx - 2 + i * 5 // 8, top + 1 + i
            c.hline(x, x + 1, y, P["sash"])
            c.set(x, y + 1, P["sash_sh"])
            if i in (2, 4, 6):
                c.set(x, y, P["letter"])
        if pose.frame % 2 == 0:                                  # sequin glint
            c.set(cx + 2, top + 7, P["sparkle"])
        else:
            c.set(cx - 1, top + 4, P["sparkle"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "....hhHHHhh....",
    "..hHHHHHHHHHh..",
    ".hHHHHHHHHHHHh.",
    ".HHHHHHHHHHSHH.",
    "hHHHHHHHHSSSSH.",
    "HHHHHHHHSSSbbS.",
    "HHHHHHHHSSSSES.",
    "HHHHHHHsSSSSSSN",
    "HHHHHHHsSSSSSS.",
    "HHHHHHHHsSSSLL.",
    "dHHHHHHHHsSSS..",
    "dHHHHHHH.sSS...",
    ".dHHHHHd.......",
    "..dHHd.........",
]


class PageantQueenHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 8, ny - 13
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "d": P["hair_sh"], "S": P["skin"], "s": P["skin_sh"],
            "b": INK, "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"], "L": P["lips"],
        }
        c.stamp(x0, y0, HEAD, key)
        for x, y in ((x0 + 3, y0 + 3), (x0 + 1, y0 + 7), (x0 + 4, y0 + 9)):  # curls
            c.stamp(x, y, ["hh.", "..h"], {"h": P["hair_hi"]})
            c.stamp(x, y + 1, ["d..", ".dd"], {"d": P["hair_sh"]})
        gem = P["sparkle"] if pose.frame % 2 else P["gem"]      # the gem catches the light
        c.stamp(x0 + 4, y0 - 2, ["..t..", "t.g.t", "ttttt"], {"t": P["tiara"], "g": gem})


class PageantQueenArm(Arm):
    """Front arm does the parade wave; the back arm cradles the roses.
    Attacks by smacking you with the bouquet (it's thrown into the front hand)."""
    species = SPECIES
    reach = 8
    fx_colors = (P["sparkle"], P["rose_hi"])
    targets = {
        "windup": ((-0.3, -0.95), (-0.4, 0.85)),
        "strike": ((1.0, 0.0), (-0.7, 0.55)),
        "follow": ((0.85, 0.5), (-0.6, 0.7)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if not front:                                            # roses in the crook of the arm
            c.line(sx, sy, sx + 1, sy + 5, P["skin_sh"], width=2)
            c.line(sx + 1, sy + 6, sx + 4, sy + 7, P["skin_sh"], width=2)
            bouquet(c, sx + 5, sy + 10, tilt=1)
            c.rect(sx + 4, sy + 7, 2, 2, P["glove_sh"])
            return
        if pose.anim == "idle":                                  # the parade wave
            ex, ey = sx + 7, sy + 1                              # elbow out front, forearm up
            tw = (0, 1, 0, -1)[pose.frame % 4]                   # wrist twists side to side
            hx, hy = sx + 10 + tw, sy - 7
            c.line(sx, sy, ex, ey, P["skin"], width=2)
            c.line(ex, ey, sx + 10, hy + 3, P["skin"], width=2)
            c.rect(hx, hy, 2, 3, P["glove"])
            c.set(hx + (0 if tw < 0 else 1), hy - 1, P["glove"])        # fingertips
            return
        dx = -2 * pose.swing
        c.line(sx, sy, sx + dx, sy + 6, P["skin"], width=2)
        c.rect(sx + dx, sy + 7, 2, 2, P["glove"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        holding = (pose.anim == "attack") == front               # roses change hands to attack
        if holding:
            tilt = {"windup": -2, "strike": 2, "follow": 3}.get(mode, 0)
            bouquet(c, hx, hy + 1, tilt)
        c.rect(hx, hy, 2, 2, P["glove"] if front else P["glove_sh"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        hx = min(hx, 36 if pose.fx == "swoosh" else 33)           # keep it all inside the frame
        if pose.fx == "swoosh":                                  # sparkly trail behind the swing
            for i, (dx, dy) in enumerate(((7, -6), (3, -10), (6, -13), (9, -2))):
                sparkle(fx, hx + dx, hy + dy, P["sparkle"] if i % 2 == 0 else P["rose_hi"], big=i == 0)
        else:                                                    # petals everywhere
            sparkle(fx, hx + 9, hy - 6, big=True)
            sparkle(fx, hx + 10, hy + 3, big=True)
            sparkle(fx, hx + 6, hy + 6)
            for dx, dy in ((7, -3), (9, -1), (8, 1), (11, -3), (6, 4), (12, 0), (9, 6), (5, -5)):
                fx.set(hx + dx, hy + dy, P["rose"] if (dx + dy) % 2 else P["rose_hi"])


GENES = dict(legs=PageantQueenLegs(), torso=PageantQueenTorso(), head=PageantQueenHead(), arm=PageantQueenArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
