"""Spider: a red-kneed lab tarantula the size of a beagle. Eight hairy legs, eight
shiny eyes, two fangs. Shoots web. Nobody remembers ordering it.

One spider split across the genes: the legs are all eight walking legs plus the
big hairy abdomen (like the centaur's horse, it travels with the legs), the torso
is the carapace, the head is the eye mound with the jaws and fangs, and the arms
are the pedipalps, which double as web shooters.
"""

import math

from ..canvas import Canvas, wave
from ..palette import INK, SPIDER as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "spider"
PREFIX, SUFFIX = "Spi", "pider"


# Per leg, front to back: root under the carapace, resting foot, and knee (relative to
# the root and the hip). The legs arch up well above the body before coming down.
ROOTS = (3, 1, -1, -3)
NEAR_TIPS = (17, 9, -9, -17)
FAR_TIPS = (14, 5, -5, -13)
KNEES = ((10, -12), (3, -15), (-5, -16), (-11, -14))

# Alternating tetrapod gait: legs 1 & 3 on one side step with legs 2 & 4 on the other.
NEAR_GROUP = (0, 1, 0, 1)
FAR_GROUP = (1, 0, 1, 0)

# Jump: how far the legs splay from the root (1 = resting), plus a shove backward.
JUMP = {0: (1.15, 0), 1: (0.8, -2), 2: (0.5, 0), 3: (1.15, 1)}


def step(pose: Pose, group: int) -> tuple[int, int]:
    """(dx, lift) for one gait group. Feet travel back while planted and swing forward lifted."""
    amp, h = {"walk": (2, 2), "run": (3, 3)}.get(pose.anim, (0, 0))
    ph = 2 * math.pi * pose.frame / pose.n + group * math.pi
    return round(amp * math.cos(ph)), round(h * max(0.0, -math.sin(ph)))


class SpiderLegs(Legs):
    """Eight jointed legs scuttling in an alternating tetrapod, and the big hairy
    abdomen riding along behind them."""
    species = SPECIES
    length = 8

    def leg(self, c: Canvas, rx: int, ry: int, kx: int, ky: int, tx: int, ty: int, near: bool) -> None:
        ax, ay = round(kx + (tx - kx) * 0.7), ty - 4              # ankle
        fwd = 1 if tx > rx else -1
        if near:                                                  # dark rim so the leg reads over the body
            for (x0, y0), (x1, y1) in (((rx, ry), (kx, ky)), ((kx, ky), (ax, ay))):
                c.stroke(x0, y0, x1, y1, INK, 4)
        col = P["fur"] if near else P["fur_dk"]
        c.stroke(rx, ry, kx, ky, col, 2)
        c.stroke(kx, ky, ax, ay, col, 2)
        c.line(ax, ay, tx, ty, col)
        c.set(tx + fwd, ty, col)                                  # little hooked foot
        c.rect(kx, ky, 2, 2, P["knee"] if near else P["knee_sh"])  # red knees
        if near:
            c.line(rx, ry - 1, kx, ky - 1, P["fur_hi"])           # top of the thigh catches the light
            c.line(kx + 1, ky + 1, ax, ay, P["fur_sh"])           # shin in shadow
            c.set(kx + (fwd > 0), ky, P["knee_hi"])
            c.set(ax - fwd, ay - 1, P["knee_sh"])                 # second, thinner band
            c.set(round((kx + ax) / 2) + fwd, round((ky + ay) / 2) - 1, P["hair"])   # stray bristle

    def abdomen(self, c: Canvas, cx: int, hip: int, pose: Pose) -> None:
        sway = wave(pose.frame, pose.n, 1) if pose.anim in ("walk", "run") else 0
        x0, y0 = cx - 19, hip - 12 + sway + (pose.anim == "idle" and pose.bob > 0)
        c.oval(x0, y0, 16, 13, P["rust"])
        for x in range(x0, x0 + 16):                             # top sheen, belly shadow
            col = [y for y in range(y0, y0 + 13) if c.get(x, y) == P["rust"]]
            if not col:
                continue
            c.vline(x, col[-3], col[-1], P["rust_sh"])
            if x0 + 4 <= x <= x0 + 11:
                c.set(x, col[1], P["rust_hi"])
            if x % 3 == 1 and x0 + 1 < x < x0 + 14:              # hair tufts poke out of the outline
                c.set(x, col[0] - 1, P["rust"])
        for dx, dy in ((5, 4), (8, 4), (11, 5), (3, 6), (6, 7), (9, 7), (13, 7), (4, 9), (8, 9)):
            c.set(x0 + dx, y0 + dy, P["rust_hi"] if dy < 6 else P["rust_sh"])   # bristly stipple
        c.stamp(x0 - 1, y0 + 7, ["s.", "Ss"], {"s": P["rust_sh"], "S": P["fur_dk"]})   # spinnerets

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        spread, shove = JUMP[pose.frame] if pose.anim == "jump" else (1.0, 0)
        if pose.anim in ("hurt", "death"):
            spread = 0.75                                        # legs flinch in
        # far legs, the near hind legs (knees poking up over the abdomen), the abdomen, the near front legs
        order = [(False, i) for i in (3, 2, 0, 1)] + [(True, 3), (True, 2), (None, 0), (True, 0), (True, 1)]
        for near, i in order:
            if near is None:
                self.abdomen(c, cx, hip, pose)
                continue
            tips, groups = (NEAR_TIPS, NEAR_GROUP) if near else (FAR_TIPS, FAR_GROUP)
            rx = cx + ROOTS[i] - (0 if near else 1)
            dx, lift = step(pose, groups[i])
            if pose.anim == "idle" and near and i == 0 and pose.frame == 2:
                lift = 1                                         # impatient tap
            tx = rx + round((tips[i] - ROOTS[i]) * spread) + dx + shove
            kx = rx + round(KNEES[i][0] * spread * (1 if near else 0.8)) + dx // 2
            ky = hip + KNEES[i][1] + (0 if near else 3) - lift + (3 if pose.anim == "jump" and pose.frame == 2 else 0)
            self.leg(c, rx, hip - 2, kx, max(2, ky), tx, ground - lift, near)


class SpiderCarapace(Torso):
    """The hairy shell over the front half, with the dark groove pattern radiating
    from its centre, and the narrow waist (pedicel) back to the abdomen."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 6
        c.rect(cx - 7 - pose.lean, hip - 4, 4 + pose.lean, 3, P["fur_sh"])   # pedicel
        c.oval(cx - 5, top, 12, 7, P["fur"])
        c.hline(cx - 3, cx + 3, top, P["fur_hi"])
        c.hline(cx - 4, cx + 5, hip, P["fur_sh"])
        for dx, dy in ((0, 2), (-1, 3), (1, 3), (-3, 2), (3, 2), (0, 4)):   # fovea and grooves
            c.set(cx + dx, top + dy, P["fur_dk"] if dy == 3 else P["fur_sh"])
        c.set(cx - 3, top + 1, P["hair"])
        c.set(cx + 4, top + 1, P["hair"])
        return Anchors(neck=(cx + 4, hip - 3), shoulder=(cx + 6, hip - 1), top=top, bottom=hip)


HEAD = [
    "...hhhh....",
    "..hHHHHh...",
    ".hHeHHeHH..",
    ".HHHHEgHEg.",
    "HHHHHEEHEE.",
    "HHHHHHHHHH.",
    ".sJJJJJJJ..",
    ".sJJJJjJJJ.",
    "..sJJJJJJJ.",
    "...sjjjjj..",
]
FANGS = {False: ["...FF", "..Ff."], True: ["....F", "....FF", ".....f"]}


class SpiderHead(Head):
    """Eye mound with a cluster of beady red eyes over a pair of big hairy jaws and two curved fangs."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 3, ny - 9
        flinch = pose.anim in ("hurt", "death")
        gape = flinch or pose.fx is not None or pose.arm == "windup"
        shut = pose.blink and not flinch
        key = {
            "h": P["fur_hi"], "H": P["fur"], "J": P["fur"], "j": P["fur_sh"], "s": P["fur_sh"],
            "E": P["fur_sh"] if shut else P["eye"], "g": P["fur_sh"] if shut else P["glint"],
            "e": P["fur_sh"] if shut else P["eye"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 8, y0 + 7, P["hair"])                        # bristles on the jaw
        c.set(x0 + 4, y0 + 8, P["fur_hi"])
        # fangs fold back under the jaw, or flick open to bite
        c.stamp(x0 + 3, y0 + 10, FANGS[gape], {"F": P["fang"], "f": P["fang_sh"]})
        if pose.anim == "idle" and pose.frame in (1, 2):         # a bead of venom
            c.set(x0 + 5, y0 + 12 + (pose.frame == 2), P["venom"])


class Pedipalp(Arm):
    """A short, hairy feeler with a clubbed tip. Takes aim from under the fangs,
    then fires a strand of web that splats into a sticky net."""
    species = SPECIES
    reach = 7
    fx_colors = (P["web"], P["web_sh"])
    targets = {
        "windup": ((0.3, 0.95), (0.0, 1.0)),                 # palps tucked under the fangs: aim...
        "strike": ((1.0, -0.15), (-0.6, 0.6)),               # THWIP
        "follow": ((1.0, 0.05), (-0.6, 0.7)),
        "recover": ((0.7, 0.6), (-0.25, 0.95)),
    }

    def palp(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, front: bool, bend: float) -> None:
        fur, knee = (P["fur_hi"], P["knee"]) if front else (P["fur_sh"], P["knee_sh"])
        hy = min(hy, GROUND - 1)                                 # the tip never digs into the floor
        ex, ey = elbow(sx, sy, hx, hy, bend)
        c.stroke(sx, sy, ex, ey, fur, 2)
        c.stroke(ex, ey, hx, hy, fur, 2)
        c.set(ex, ey, knee)
        c.rect(hx, hy, 2, 2, P["fur_dk"])                        # clubbed tip
        if front:
            c.set(hx + 1, hy, P["hair"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        d = pose.swing if front else -pose.swing
        twitch = pose.anim == "idle" and front and pose.frame % 2
        hy = min(GROUND - 2, sy + 6) - twitch - (pose.lift if not front else 0)
        self.palp(c, sx, sy, sx + 4 + 2 * d - (0 if front else 2), hy, front, -2)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        self.palp(c, sx, sy, hx, hy, front, 1.5)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        main, shade = self.fx_colors
        if pose.fx == "swoosh":                                  # THWIP: a strand shoots out, glob first
            end = min(hx + 14, 43)
            fx.line(hx + 2, hy, end, hy - 1, main)
            fx.rect(end, hy - 2, 3, 3, main)
            fx.set(end + 2, hy, shade)
            for dy, x0 in ((-3, hx), (3, hx + 2)):              # speed lines
                fx.hline(x0, min(x0 + 3, end - 2), hy + dy, shade)
        else:                                                    # SPLAT: a sticky web net
            gx, gy = min(hx + 6, 39), min(max(7, hy - 1), 38)
            fx.line(hx + 2, hy, gx, gy, shade)                   # the strand still attached
            for r, col in ((3, shade), (6, main)):               # rings
                pts = [(gx + round(r * math.cos(k * math.pi / 4)), gy + round(r * math.sin(k * math.pi / 4)))
                       for k in range(8)]
                for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
                    fx.line(x0, y0, x1, y1, col)
            for k in range(8):                                   # spokes
                a = k * math.pi / 4
                fx.line(gx, gy, gx + round(6 * math.cos(a)), gy + round(6 * math.sin(a)), main)


GENES = dict(legs=SpiderLegs(), torso=SpiderCarapace(), head=SpiderHead(), arm=Pedipalp())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
