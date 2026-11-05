"""Technoviking: a viking who took a wrong turn at the fjord and ended up at a rave.
Horned helmet, braided beard, no shirt, ever. Points at you. The bass drops."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, TECHNOVIKING as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "technoviking"
PREFIX, SUFFIX = "Techno", "viking"

NEON = (P["neon_c"], P["neon_m"], P["neon_g"], P["neon_y"])


def neon(frame: int, k: int = 0) -> str:
    """Rave lighting: cycles through the neon colors, one step per frame."""
    return NEON[(frame + k) % len(NEON)]


class TechnovikingLegs(Legs):
    """Baggy pants, fur-cuffed boots. Walks like every step is on the downbeat."""
    species = SPECIES
    length = 13

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 2 + 3 * s
            lift = 0 if front else pose.lift
            if pose.anim == "walk" and lift:                   # the stomp: knee high, foot slams down next frame
                lift += 2
            foot_y = ground - 1 - lift
            pants = P["pants"] if front else P["pants_sh"]
            kx = (cx - 2 + fx) // 2 + (2 if lift > 1 else 0)    # knee comes forward when the foot is up
            ky = (hip + foot_y) // 2
            c.stroke(cx - 1, hip + 1, kx, ky, pants, 4)
            c.stroke(kx, ky, fx + 1, foot_y - 3, pants, 3)
            boot = P["boot"] if front else P["pants_sh"]
            c.rect(fx - 1, foot_y - 2, 4, 2, P["fur"] if front else P["fur_sh"])   # fur cuff
            c.rect(fx - 1, foot_y, 6, 2, boot)
            if front:
                c.set(fx, foot_y - 2, P["fur_sh"])
                c.set(fx + 2, foot_y - 1, P["fur_sh"])
                c.hline(fx + 1, fx + 4, foot_y, P["boot_hi"])


TORSO = [
    "....sSSSs.....",
    "..sSSSSSSSh...",
    ".sSSSSSSSSSh..",
    "sSSSSSSSSSSHh.",
    "sSSSSSSSSSHHHh",
    "sSSSSSSSSSdddd",
    ".sSSSSSSSShHd.",
    ".sSSSSSSSdShdH",
    "..sSSSSSSShHd.",
    "..sSSSSSSdShdH",
    "..sSSSSSSShHd.",
    "..sSSSSSSSSSH.",
    "..bbbbbbbbbBB.",
]


MANTLE = [                      # wolf fur over the shoulders, shaggy at the back
    "...FFFFF...",
    ".FFFfFFFFF.",
    "FFfFFFfFFfF",
    "fFFfF.f..f.",
    "F.f.f......",
]


class TechnovikingTorso(Torso):
    """Shirtless and absurdly ripped. A wolf-fur mantle, for the cold Nordic dance floors."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 12
        key = {
            "s": P["skin_sh"], "S": P["skin"], "H": P["skin_hi"], "h": P["skin_hi"], "d": P["skin_dk"],
            "b": P["belt"], "B": P["buckle"],
        }
        c.stamp(cx - 6, top, TORSO, key)
        c.stamp(cx - 7, top - 1, MANTLE, {"F": P["fur"], "f": P["fur_sh"]})
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 3), top=top, bottom=hip)


# Horned helmet with a nose guard, a stern brow, and a beard that has seen things.
HEAD = [
    "....hhhhh....",
    "..hHHHHHHHh..",
    ".hHHHHHHHHHH.",
    ".GGGGGGGGGgGG",
    ".YYYYYsbbbgS.",
    ".YYYYSSSSEgS.",
    ".YYYYSSSSSgSN",
    "..YYYSSSSSSS.",
    "..YYyYYBBMBB.",
    "...YyBBBBBBBB",
    "....BBbBBBbB.",
    "....BbBBBbBB.",
    ".....BBBBBB..",
    "......BBBB...",
]
HORNS = [                       # (stamp, dx, dy) relative to the head origin: back horn, front horn
    (["h....", "Hh...", "Hh...", ".Hh..", "..Hhh", "...HH"], -4, -3),
    (["....h", "...hH", "...hH", "..hH.", "hhH..", "HH..."], 12, -3),
]


class TechnovikingHead(Head):
    """Horned helmet, a long braided blond beard, and a stare that doesn't blink much."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        nod = 1 if pose.anim == "idle" and pose.frame % 2 else 0   # nodding along to the beat
        x0, y0 = nx - 6, ny - 11 + nod
        key = {
            "h": P["helm_hi"], "H": P["helm"], "G": P["helm_sh"], "g": P["helm_sh"],
            "Y": P["beard"], "y": P["beard_sh"], "S": P["skin"], "s": P["skin_sh"],
            "b": P["beard_sh"], "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"],
            "B": P["beard"], "M": P["skin_dk"],
        }
        for rows, dx, dy in HORNS:
            c.stamp(x0 + dx, y0 + dy, rows, {"h": P["horn"], "H": P["horn_sh"]})
        c.stamp(x0, y0, HEAD, key)
        for x in (x0 + 3, x0 + 7):                               # rivets on the brow band
            c.set(x, y0 + 3, P["helm_hi"])
        for x, y in ((x0 + 6, y0 + 10), (x0 + 9, y0 + 11), (x0 + 7, y0 + 12)):
            c.set(x, y, P["beard_hi"])
        # braids: two plaits hanging off the beard, with neon beads
        for k, bx in enumerate((x0 + 7, x0 + 9)):
            for j in range(3):
                c.set(bx, y0 + 14 + j, P["beard"] if j % 2 else P["beard_sh"])
            c.set(bx, y0 + 17, neon(pose.frame, k))


def glow_stick(c: Canvas, x: int, y: int, frame: int) -> None:
    """A glow stick held upright in a fist at (x, y)."""
    col = neon(frame, 2)
    c.vline(x, y - 4, y - 1, col)
    c.set(x, y - 5, "#ffffff")


class TechnovikingArm(Arm):
    """Huge arms, neon wristbands, a glow stick in the off hand. Attack: a commanding
    point that drops the bass."""
    species = SPECIES
    reach = 9
    fx_colors = (P["neon_c"], P["neon_m"])
    targets = {
        "windup": ((-0.55, 0.65), (-0.4, 0.85)),             # fist pulled back to the hip...
        "strike": ((1.0, -0.15), (-0.7, 0.55)),               # ...then the point. You. Dance.
        "follow": ((1.0, -0.1), (-0.6, 0.7)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        if not front and pose.anim == "idle":                 # glow stick in the air, pumping to the beat
            hx, hy = sx - 7, sy - 7 + (pose.frame % 2)
            self.limb(c, sx, sy, sx - 6, sy - 1, hx, hy, skin, front)
            c.hline(hx - 1, hx + 1, hy + 1, neon(pose.frame, 1))
            c.rect(hx - 1, hy - 1, 3, 2, skin)
            glow_stick(c, hx, hy - 1, pose.frame)
            return
        dx = (-2 if front else 2) * pose.swing
        ex, ey = sx - 1 + dx // 2, sy + 5
        hx, hy = sx + dx, sy + 10
        self.limb(c, sx, sy, ex, ey, hx, hy, skin, front)
        c.hline(hx - 1, hx + 1, hy - 1, neon(pose.frame, 0 if front else 1))
        c.rect(hx - 1, hy, 3, 2, skin)
        if not front:
            glow_stick(c, hx, hy, pose.frame)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        self.limb(c, sx, sy, ex, ey, hx, hy, skin, front)
        c.rect(hx - 1, hy - 1, 2, 3, neon(pose.frame, 0 if front else 1))
        c.rect(hx + 1, hy - 1, 2, 3, skin)
        if front and mode in ("strike", "follow"):              # the point
            c.hline(hx + 3, hx + 4, hy - 1, skin)
        if not front:
            glow_stick(c, hx + 1, hy - 1, pose.frame)

    def limb(self, c: Canvas, sx: int, sy: int, ex: int, ey: int, hx: int, hy: int, skin: str, front: bool) -> None:
        c.oval(sx - 2, sy - 2, 5, 5, skin)                    # boulder of a shoulder
        c.stroke(sx, sy, ex, ey, skin, 3)
        c.stroke(ex, ey, hx, hy, skin, 3)
        if front:
            c.set(sx, sy - 1, P["skin_hi"])                    # deltoid shine
            c.set(sx + 1, sy, P["skin_hi"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        x, y = hx + 3, hy - 1
        if pose.fx == "swoosh":                               # the drop builds: two small rings
            rings = ((2, P["neon_y"]), (4, P["neon_c"]))
        else:                                                 # BWOOM: big rings and the floor lights up
            rings = ((3, P["neon_y"]), (6, P["neon_m"]), (9, P["neon_c"]))
        for r, col in rings:                                   # sound waves: ))) out of the fingertip
            for i in range(-16, 17):
                a = i / 16 * 1.1
                px, py = round(x + math.cos(a) * r * 0.7), round(y + math.sin(a) * r * 1.1)
                if px <= 44 and 2 <= py <= GROUND - 1:
                    fx.set(px, py, col)
        if pose.fx == "impact":                               # equalizer bars bouncing on the floor
            for i, h in enumerate((2, 5, 3, 7, 4, 6, 2)):
                bx = hx - 6 + 2 * i
                if bx <= 44:
                    fx.vline(bx, GROUND - h, GROUND, NEON[i % len(NEON)])


def beat(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """Music notes floating off him while he grooves."""
    if pose.anim not in ("idle", "walk") or pose.flash or pose.melt:
        return
    nx, ny = info["anchors"].neck
    x, y = nx + 8, ny - 14 - pose.frame % 2
    note = ["..XX", "..X.", "..X.", "XXX.", "XX.."]
    out.stamp(x, y, note, {"X": neon(pose.frame)})


GENES = dict(legs=TechnovikingLegs(), torso=TechnovikingTorso(), head=TechnovikingHead(), arm=TechnovikingArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"],
                    decorations=[beat])
