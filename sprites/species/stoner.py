"""Stoner: slouch beanie, tie-dye tee, cargo shorts, flip-flops, joint permanently lit.
Totally knows where he is. Has no idea what day it is."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, STONER as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "stoner"
PREFIX, SUFFIX = "Stone", "ner"


def puff(c: Canvas, x: int, y: int, r: int) -> None:
    """One round smoke puff of radius r: lit from the top-left, shadow crescent bottom-right."""
    if r <= 0:
        c.set(x, y, P["smoke_hi"])
        return
    c.oval(x - r, y - r, 2 * r + 1, 2 * r + 1, P["smoke_sh"])
    c.oval(x - r, y - r, 2 * r, 2 * r, P["smoke"])
    c.set(x - r + 1, y - r + 1, P["smoke_hi"])
    if r > 2:
        c.set(x - r + 2, y - r + 1, P["smoke_hi"])
        c.set(x - r + 1, y - r + 2, P["smoke_hi"])


def joint(c: Canvas, x: int, y: int, dx: int, dy: int, hot: bool = False) -> None:
    """Joint pinched at (x, y), pointing along (dx, dy), lit end out."""
    c.set(x + dx, y + dy, P["paper"])
    c.set(x + 2 * dx, y + 2 * dy, P["paper"])
    c.set(x + 3 * dx, y + 3 * dy, P["ember_hi"] if hot else P["ember"])


class StonerLegs(Legs):
    """Baggy cargo shorts, hairy shins, flip-flops. Never lifts his feet if he can help it."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        shuffle = pose.anim in ("walk", "run")
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + (2 if shuffle else 3) * s                # half-hearted stride
            lift = 0 if front else (min(1, pose.lift) if shuffle else pose.lift)
            foot_y = ground - 1 - lift
            skin = P["skin"] if front else P["skin_sh"]
            c.line(cx - 1, hip, fx + 1, foot_y - 1, skin, width=2)
            # shorts: wide, down to just past the knee
            kx = round(cx - 1 + (fx - cx + 1) * 0.55)
            ky = round(hip + (foot_y - 1 - hip) * 0.55)
            shorts = P["shorts"] if front else P["shorts_sh"]
            c.line(cx - 2, hip, kx - 1, ky, shorts, width=4)
            c.hline(kx - 2, kx + 2, ky + 1, shorts)                # flared hem
            c.set(kx - 2, ky + 1, P["shorts_sh"])
            if front:
                c.rect(kx, ky - 3, 2, 2, P["shorts_sh"])           # cargo pocket
                c.set(kx, ky - 3, P["shorts_hi"])
                c.set(fx + 1, foot_y - 2, P["hair"])               # shin hair
            # flip-flop: flat sole, a toe post, and toes
            c.hline(fx - 1, fx + 4, foot_y + 1, P["sole"] if front else P["sole_sh"])
            c.hline(fx, fx + 3, foot_y, skin)
            c.set(fx + 1, foot_y, P["strap"] if front else P["ash"])


TIE_DYE = ("dye_a", "dye_b", "dye_c", "dye_d")


class StonerTorso(Torso):
    """Oversized tie-dye tee over a slouch. Sways gently to music only he can hear."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        sway = (0, 1, 1, 0)[pose.frame % 4] if pose.anim == "idle" else 0
        ox, oy = cx + 1 + sway, top + 5                            # center of the swirl
        for y in range(top, hip + 1):
            t = (hip - y) / 11
            hunch = round(t * t * 2 + sway * t)                    # shoulders roll forward
            belly = 1 if hip - 5 <= y <= hip - 2 else 0            # ...and so does the belly
            x0 = cx - 4 + hunch + (1 if y == top else 0)
            x1 = cx + 4 + hunch + belly - (1 if y == top else 0)
            for x in range(x0, x1 + 1):
                a = math.atan2(y - oy, x - ox)
                r = math.hypot(x - ox, y - oy)
                k = int((a / math.tau + 0.5) * 4 + r * 0.55) % 4
                c.set(x, y, P[TIE_DYE[k]])
            c.set(x0, y, P["dye_sh"])                              # shadowed back edge
        c.hline(cx - 3, cx + 4, hip + 1, P["dye_sh"])             # hem hangs past the waist
        top_hunch = 2 + sway
        nx = cx + 2 + top_hunch
        c.hline(nx - 2, nx, top, P["dye_sh"])                      # stretched-out collar
        return Anchors(neck=(nx, top + 1), shoulder=(cx + top_hunch - 1, top + 2), top=top, bottom=hip)


# Slouch beanie (rasta stripes, droops off the back), long hair, red half-lidded eye,
# scruffy beard, lazy grin.
HEAD = [
    ".....rrrr...",
    "...rRRRRRRr.",
    "..RRRRRRRRRR",
    ".YYYYYYYYYYY",
    "YYYYGGGGGGGG",
    "YGGGkkkkkkkk",
    "GGGHHHHHSSSS",
    "gGHHHHHSLLLS",
    ".HHHHHSSEPSN",
    "HHHhHHsSssSS",
    "HHHHHHsBSSMS",
    "HHhHH.sBBBbB",
    ".HHH...BBBB.",
    ".H.H....bB..",
]


class StonerHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 6, ny - 13
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        toking = pose.anim == "attack" and pose.frame == 0          # eyes shut, deep breath
        key = {
            "r": P["cap_r"], "R": P["cap_r"], "Y": P["cap_y"], "G": P["cap_g"], "g": P["cap_g_sh"],
            "k": P["rib"], "H": P["hair"], "h": P["hair_hi"], "S": P["skin"], "s": P["skin_sh"],
            "L": P["lid"], "E": P["skin"] if pose.blink or toking else P["eye"],
            "P": P["skin"] if pose.blink or toking else INK, "N": P["skin"],
            "B": P["hair"], "b": P["hair_sh"], "M": P["mouth"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 5, y0 + 1, P["cap_y"])                          # pom-less, but knitted
        if pose.anim == "attack" and pose.frame in (1, 2):         # HOOOO: mouth rounds into an O
            c.stamp(x0 + 9, y0 + 9, ["SM", "MM", "BM"], {"S": P["skin"], "M": P["mouth"], "B": P["hair"]})
        elif toking:                                                # lips pursed on the joint
            c.set(x0 + 10, y0 + 10, P["skin_sh"])


class StonerArm(Arm):
    """Front hand holds the joint, smoke curling off it. Attacks with a lungful of smoke: hotbox."""
    species = SPECIES
    reach = 8
    fx_colors = (P["smoke_hi"], P["smoke"])
    targets = {
        "windup": ((1.0, -0.4), (-0.4, 0.85)),                     # joint to lips...
        "strike": ((1.0, -0.3), (-0.7, 0.55)),                     # ...and exhale
        "follow": ((0.95, -0.1), (-0.6, 0.7)),
    }

    def sleeve(self, c: Canvas, sx: int, sy: int, ex: int, ey: int, front: bool) -> None:
        c.stroke(sx, sy, sx + (ex - sx) // 2, sy + (ey - sy) // 2, P["dye_a"] if front else P["dye_sh"], 2)
        if front:
            c.set(sx, sy, P["dye_d"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        if not front:                                              # back arm just hangs there
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 7, skin, width=2)
            c.line(sx, sy, sx + dx // 2, sy + 2, P["dye_sh"], width=2)
            c.rect(sx + dx, sy + 8, 2, 2, skin)
            return
        lazy = (0, 0, 1, 1)[pose.frame % 4] if pose.anim == "idle" else -pose.swing
        ex, ey = sx + 1, sy + 6                                    # elbow resting on the belly
        hx, hy = sx + 6, sy + 3 + lazy                             # joint held out in front, like a pointer
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        self.sleeve(c, sx, sy, ex, ey, front)
        joint(c, hx + 1, hy, 1, 0)
        c.rect(hx, hy, 2, 2, skin)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        self.sleeve(c, sx, sy, ex, ey, front)
        if front:
            if mode == "windup":                                   # joint at the lips, ember glowing
                joint(c, hx + 1, hy, 1, 0, hot=True)
            elif mode in ("strike", "follow"):                     # palm out; joint tucked in the fist
                c.vline(hx + 2, hy - 1, hy + 1, skin)
                joint(c, hx, hy + 2, -1, 1)
            else:
                joint(c, hx + 1, hy, 1, -1)
        c.rect(hx, hy, 2, 2, skin)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        my = sy - 4                                                # roughly mouth height
        if pose.fx == "swoosh":                                    # a long stream of smoke...
            for i, x in enumerate(range(sx + 9, min(sx + 23, 44), 3)):
                puff(fx, x, my + round(wave(i, 4)), min(2, i // 2 + 1))
            return
        x0 = min(sx + 13, 40)                                      # ...that billows into a hotbox cloud
        for dx, dy, r in ((0, -9, 1), (-1, -4, 2), (3, -6, 2), (2, -1, 3), (-1, 3, 3), (3, 5, 2)):
            puff(fx, x0 + dx, my + dy, r)
        for dx, dy in ((-3, -8), (5, -10), (-4, 7), (5, 1)):        # stray wisps around the edge
            fx.set(x0 + dx, my + dy, P["smoke_hi"])


def smoke_wisp(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """A thin curl of smoke rising off the joint's ember. Painted after outlining, so it
    stays wispy. He's inhaling during the attack, and a hit knocks it out of him."""
    if pose.anim in ("attack", "hurt", "death"):
        return
    arm = layers["front_arm"]
    embers = [(x, y) for y in range(arm.h) for x in range(arm.w) if arm.get(x, y) == P["ember"]]
    if not embers:
        return
    x, y = embers[0]
    height = 5 if pose.anim == "run" else 9
    for i in range(1, height):
        px = x + round(math.sin(i * 0.7 - pose.frame * 1.6) * 1.5 * min(1.0, i / 3))
        if i > 5 and (i + pose.frame) % 2:                       # thins out at the top
            continue
        if out.get(px, y - i) is None or i == 1:                 # behind everything, never over the face
            out.set(px, y - i, P["smoke_hi"] if i < 4 else P["smoke"] if i < 7 else P["smoke_sh"])


GENES = dict(legs=StonerLegs(), torso=StonerTorso(), head=StonerHead(), arm=StonerArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"],
                    decorations=[smoke_wisp])
