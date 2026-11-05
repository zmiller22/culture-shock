"""Fairy: pocket-sized, glittery, buzzing. Leaf dress, hair bun, pointy ears, star wand.
Grants wishes. Yours is to stop getting hit by sparkles."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, FAIRY as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "fairy"
PREFIX, SUFFIX = "Fae", "fairy"


STAR = ["..s..", ".sYs.", "sYWYs", ".sYs.", ".s.s."]
DUST = ("dust_p", "dust_c", "dust_y")


def wand_star(c: Canvas, x: int, y: int, twinkle: bool = False) -> None:
    """Five-point star centered on (x, y), with a glint that comes and goes."""
    c.stamp(x - 2, y - 2, STAR, {"s": P["star_sh"], "Y": P["star"], "W": P["star_hi"]})
    c.set(x, y - 2, P["star"])
    if twinkle:
        c.set(x + 1, y - 1, P["star_hi"])


def twinkle(c: Canvas, x: int, y: int, col: str, big: bool = False) -> None:
    """Four-point sparkle (big ones get longer rays)."""
    c.set(x, y, P["star_hi"] if big else col)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        c.set(x + dx, y + dy, col)
        if big:
            c.set(x + 2 * dx, y + 2 * dy, col)


def blade(c: Canvas, rx: float, ry: float, angle: float, length: float, width: float,
          fill: str, rim: str, vein: str) -> None:
    """Gossamer wing: a long teardrop hinged at (rx, ry), pointing along `angle`.
    Rimmed on the leading (upper) edge, one vein down the middle, see-through-ish speckles."""
    ca, sa = math.cos(angle), math.sin(angle)
    r = int(length) + 2
    for y in range(math.floor(ry - r), math.ceil(ry + r) + 1):
        for x in range(math.floor(rx - r), math.ceil(rx + r) + 1):
            dx, dy = x + 0.5 - rx, y + 0.5 - ry
            u = dx * ca + dy * sa                              # along the wing
            v = -dx * sa + dy * ca                             # across it (+ = clockwise side)
            if u < 0 or u > length:
                continue
            half = width / 2 * math.sin(math.pi * (u / length) ** 0.75)   # fat near the tip
            if abs(v) > half + 0.3:
                continue
            if abs(v) > half - 0.9 and v < 0:
                col = rim
            elif abs(v) < 0.5 and u < length * 0.8:
                col = vein
            elif (x * 3 + y * 5) % 7 == 0:
                col = rim                                      # light catching the membrane
            else:
                col = fill
            c.set(x, y, col)


# Wing flutter per frame: (upper wing angle, lower wing angle, upper length).
# Angles are radians from pointing straight back (pi = behind her); smaller = raised.
UP, DOWN = (-2.2, 2.8, 15), (-2.75, 2.45, 12)
FLUTTER = {
    "idle": (UP, DOWN, UP, DOWN),
    "walk": (UP, DOWN, UP, DOWN),
    "run": ((-2.5, 2.9, 15), (-2.9, 2.7, 13), (-2.5, 2.9, 15), (-2.9, 2.7, 13)),        # swept back
    "jump": (DOWN, UP, UP, DOWN),
    "attack": (UP, UP, DOWN, UP),
    "hurt": ((-2.55, 2.55, 12), (-2.4, 2.4, 11)),                                             # crumpled
}


class FairyLegs(Legs):
    """Bare legs with pointed, pompommed slippers. She never quite lands: toes hover above
    the floor and a little fairy dust drifts down underneath."""
    species = SPECIES
    length = 12
    hover = 2

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        flying = pose.anim == "run"
        for front in (False, True):
            k = pose.swing if front else -pose.swing
            skin = P["skin"] if front else P["skin_sh"]
            toe_y = ground - self.hover - (0 if front else pose.lift // 2 + 1)
            if flying:                                         # legs stream out behind her
                ax, ay = cx - 4 - k - (0 if front else 2), toe_y - 2 - (1 if front else 0)
                kx, ky = cx - 1, hip + 4
                tx, ty = ax - 2, ay + 1
            else:                                              # dangling, knees soft, toes pointed
                ax, ay = cx - 1 + 2 * k + (0 if front else -2), toe_y - 2
                kx, ky = cx + (1 if front else -1) + k, hip + (ay - hip) // 2
                tx, ty = ax + 1, ay + 2
            c.stroke(cx - 1, hip, kx, ky, skin, 2)
            c.stroke(kx, ky, ax, ay, skin, 2)
            slip = P["slipper"] if front else P["leaf_sh"]
            c.rect(ax, ay, 2, 2, slip)                         # pointed slipper...
            c.line(ax + (1 if tx > ax else 0), ay + 1, tx, ty, slip)
            c.set(tx, ty, P["pom"] if front else P["cheek"])   # ...with a pompom on the toe
        if pose.tuck or flying:
            return
        # fairy dust drifting to the floor under her
        for i in range(2):
            x = cx - 2 + 4 * i + (pose.frame + i) % 2
            y = ground - 2 + (pose.frame + 2 * i) % 3
            c.set(x, min(GROUND, y), P[DUST[(pose.frame + i) % 3]])


class FairyTorso(Torso):
    """Leaf bodice and petal skirt. Owns the wings, so they survive splicing."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 9
        flut = FLUTTER.get(pose.anim, FLUTTER["idle"])
        up, low, ln = flut[pose.frame % len(flut)]
        rx, ry = cx - 1, top + 2
        # far wings (dimmer, a touch higher), then near wings
        blade(c, rx, ry - 1, up + 0.35, ln - 1, 6, P["wing_sh"], P["wing"], P["vein"])
        blade(c, rx, ry + 2, low - 0.3, ln * 0.6, 5, P["wing_sh"], P["wing"], P["vein"])
        blade(c, rx, ry, up, ln, 7, P["wing"], P["wing_hi"], P["vein"])
        blade(c, rx, ry + 2, low, ln * 0.65, 5, P["wing"], P["wing_hi"], P["vein"])
        # bodice
        c.rect(cx - 1, top, 4, 1, P["skin"])
        c.rect(cx - 3, top + 1, 7, 8, P["leaf"])
        c.vline(cx - 3, top + 1, hip - 1, P["leaf_sh"])
        c.vline(cx + 3, top + 2, hip - 2, P["leaf_hi"])
        c.stamp(cx, top + 1, ["l.l", ".L."], {"l": P["leaf_hi"], "L": P["leaf_sh"]})   # leafy V-neckline
        c.set(cx + 1, top + 1, P["skin"])
        c.hline(cx - 3, cx + 3, hip - 1, P["leaf_dk"])        # vine belt
        # petal skirt: five pointed leaves, flaring and fluttering
        flare = 1 if pose.anim in ("jump", "run") or pose.bob < 0 else 0
        for i, dx in enumerate((-4, -2, 0, 2, 4)):
            lift = (i + pose.frame) % 2 if pose.anim in ("walk", "run", "idle") else 0
            px = cx + dx + (dx > 0) * flare - (dx < 0) * flare
            col = (P["leaf_sh"], P["leaf"], P["leaf_hi"], P["leaf"], P["leaf_hi"])[i]
            c.rect(px - 1, hip, 3, 2, col)
            c.set(px, hip + 2, col)
            c.set(px + (1 if dx > 0 else -1 if dx < 0 else 0), hip + 3 - lift, col)
        c.hline(cx - 4, cx + 4, hip, P["leaf"])
        c.set(cx - 4, hip, P["leaf_sh"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "...hhhhhh...",
    "..hHHHHHHhh.",
    ".hHHHHHHHHHh",
    ".HHHHHHHHHHH",
    "HHHHHHHHHSHH",
    "HHHHHHHSSSSH",
    "HHHHHSSSSSSS",
    "HHHHSSSSSLLS",
    "dHHHSSSSSEIS",
    ".dHHSSSSSSSN",
    ".dHsSSSScSS.",
    "..dssSSSSmS.",
    "....ssSSSS..",
]


class FairyHead(Head):
    """Big eyes, a bun with a flower in it, and pointy ears that droop when she's hit."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 5, ny - 13
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        # the bun, piled on top at the back
        c.oval(x0 + 1, y0 - 3, 6, 5, P["hair"])
        c.hline(x0 + 2, x0 + 4, y0 - 3, P["hair_hi"])
        c.set(x0 + 2, y0 - 1, P["hair_sh"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "d": P["hair_sh"], "S": P["skin"], "s": P["skin_sh"],
            "L": P["skin_sh"] if pose.blink else INK, "E": P["skin_sh"] if pose.blink else INK,
            "I": P["skin_sh"] if pose.blink else P["eye"], "N": P["skin"],
            "c": P["cheek"], "m": P["mouth"],
        }
        c.stamp(x0, y0, HEAD, key)
        if not pose.blink:
            c.set(x0 + 9, y0 + 8, "#ffffff")                   # sparkle in her eye
        # flower pin in the bun
        c.stamp(x0 + 4, y0 - 4, [".p.", "pFp", ".p."], {"p": P["pom"], "F": P["star"]})
        # pointy elf ear, sticking out the back of her hairline
        droop = pose.anim in ("hurt", "death")
        ear = [".o....", "oeo...", ".oeEo.", "..eEeo", "...eeo"] if not droop else \
              ["......", "oeo...", "oeeEo.", ".oeEeo", "...eeo"]
        c.stamp(x0 - 1, y0 + 3, ear, {"e": P["skin"], "E": P["skin_sh"], "o": P["hair_sh"]})


# Wand direction for every draw_limb pose (from the fist toward the star).
WAND_DIR = {
    "crouch": (0.6, -0.8), "up": (0.3, -1.0), "reach": (0.8, -0.6), "out": (0.9, -0.45),
    "windup": (-0.55, -0.85), "strike": (1.0, -0.15), "follow": (0.9, 0.2),
    "recover": (0.7, -0.7), "flail": (-0.4, -0.9), "use": (0.9, -0.45),
}
WAND = 6            # wand length from the fist to the star's center


class FairyArm(Arm):
    """Skinny arm. The front hand keeps hold of a star-tipped wand.
    Attack: a wand flick that sprays sparkle dust, then a star burst."""
    species = SPECIES
    reach = 7
    fx_colors = (P["star"], P["dust_p"])
    targets = {
        "windup": ((-0.3, -0.95), (-0.4, 0.85)),            # wand up over her shoulder...
        "strike": ((1.0, -0.3), (-0.7, 0.55)),               # ...flick!
        "follow": ((1.0, -0.05), (-0.6, 0.7)),
    }

    def wand(self, c: Canvas, hx: int, hy: int, dx: float, dy: float, frame: int) -> tuple[int, int]:
        n = math.hypot(dx, dy) or 1
        tx, ty = round(hx + dx / n * WAND), round(hy + dy / n * WAND)
        c.line(hx, hy, tx, ty, P["wand"])
        c.set(round(hx + dx / n), round(hy + dy / n), P["wand_sh"])
        wand_star(c, tx, ty, frame % 2 == 0)
        return tx, ty

    def tip(self, mode: str, sx: int, sy: int) -> tuple[int, int]:
        dx, dy = self.direction(mode, True)
        wx, wy = WAND_DIR[mode]
        n = math.hypot(wx, wy)
        return round(sx + dx * self.reach + wx / n * WAND), round(sy + dy * self.reach + wy / n * WAND)

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        if not front:
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 5, skin, width=2)
            c.rect(sx + dx, sy + 6, 2, 2, skin)
            return
        if pose.anim == "run":                                 # wand thrust out ahead, leading the way
            hx, hy, wd = sx + 6, sy + 1, (1.0, -0.4)
        else:                                                  # held up in front, bobbing to the beat
            hx, hy, wd = sx + 4 - pose.swing, sy + 4 + wave(pose.frame, pose.n, 1), (0.45, -0.9)
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        self.wand(c, hx + 1, hy, *wd, pose.frame)
        c.rect(hx, hy, 2, 2, skin)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        if front:
            self.wand(c, hx + 1, hy, *WAND_DIR[mode], pose.frame)
        c.rect(hx, hy, 2, 2, skin)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        x1, y1 = self.tip(pose.arm, sx, sy)
        if pose.fx == "swoosh":                                # flick: glitter trails the star and sprays ahead
            x0, y0 = self.tip("windup", sx, sy)
            t0, t1 = math.atan2(y0 - sy, x0 - sx), math.atan2(y1 - sy, x1 - sx)
            if t1 < t0:
                t1 += math.tau
            r = math.hypot(x1 - sx, y1 - sy)
            for i in range(7, 12):
                a = t0 + (t1 - t0) * i / 12
                x, y = round(sx + math.cos(a) * (r + 1)), round(sy + math.sin(a) * (r + 1))
                if 2 <= x <= 45 and 2 <= y <= 44:
                    fx.set(x, y, P[DUST[i % 3]])
            for k, (dx, dy) in enumerate(((4, -3), (6, -1), (5, 2), (8, 1), (3, 4))):   # spray off the star
                fx.set(min(x1 + dx, 44), y1 + dy, P[DUST[k % 3]])
        else:                                                  # STAR BURST, with a ring of glitter
            x, y = min(x1 + 5, 39), max(8, min(y1, GROUND - 8))
            for a in range(5):
                ang = -math.pi / 2 + a * math.tau / 5
                fx.line(x, y, round(x + math.cos(ang) * 4), round(y + math.sin(ang) * 4), P["star"])
            fx.oval(x - 1, y - 1, 3, 3, P["star"])
            fx.set(x, y, P["star_hi"])
            twinkle(fx, x - 5, y - 5, P["dust_p"])
            twinkle(fx, x + 5, y - 4, P["dust_c"])
            for k, (dx, dy) in enumerate(((6, 3), (-4, 5), (1, 7), (0, -7))):
                fx.set(x + dx, y + dy, P[DUST[k % 3]])


GENES = dict(legs=FairyLegs(), torso=FairyTorso(), head=FairyHead(), arm=FairyArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
