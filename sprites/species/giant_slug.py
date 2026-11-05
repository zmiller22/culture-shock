"""Giant slug: a lab experiment that got out of hand. Long, glossy, slow, spits acid.

One slug body split across the genes: the legs are the muscular foot and its
slime trail, the torso is the humped mantle and back, the head is the front end
with the eye stalks.
"""

import math

from ..canvas import Canvas, wave
from ..palette import INK, GIANT_SLUG as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "giant_slug"
PREFIX, SUFFIX = "Slug", "slug"


TAIL, NOSE = -19, 10        # foot extent relative to the body center


def spotted(x: int, y: int) -> bool:
    """Leopard mottling: a fixed scatter of 2x2-ish spots that rides along with the body."""
    return (x // 2 * 7 + y // 2 * 5) % 9 == 0 and (x + y) % 4 != 0


class SlugFoot(Legs):
    """The muscular sole: a long skirt along the floor, pedal waves rippling forward,
    a pointed tail, and a glistening slime trail left behind."""
    species = SPECIES
    length = 5

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        bottom = max(ground, min(hip + 3, GROUND))
        tail = cx + TAIL + pose.tuck                            # airborne: the foot bunches up
        nose = cx + NOSE - pose.tuck // 2
        ripple = pose.frame * {"walk": 2, "run": 3}.get(pose.anim, 0)
        for x in range(tail, nose + 1):
            taper = max(0, (cx - 14) - x)                       # pointed tail end, tip curls off the floor
            low = bottom - (taper + 1) // 2
            top = min(low - 1, hip + 1 + taper // 3)
            if x == nose:                                       # rounded front
                top = min(bottom, top + 2)
            c.vline(x, top, low, P["body_sh"])
            c.set(x, top, P["body"] if not taper else P["body_sh"])
            skirt = P["sole_sh"] if (x - ripple) % 5 == 0 else P["sole"]     # pedal waves
            c.vline(x, max(top, low - 1), low, skirt)
        if pose.tuck:                                           # slime drips off the sole mid-air
            for k, x in enumerate(range(tail + 4, nose - 2, 7)):
                c.vline(x, bottom + 1, min(GROUND, bottom + 1 + (k + pose.frame) % 3), P["slime"])
        else:                                                   # glistening trail behind
            for x in range(2, cx - 12):
                if c.opaque(x, bottom) or c.opaque(x, bottom - 1) or x < 5 and x % 2:
                    continue                                    # (and it dries up toward the edge)
                c.set(x, bottom, P["slime_hi"] if (x + pose.frame * 2) % 5 == 0 else P["slime"])


def back_height(u: float) -> float:
    """Height of the hindquarters above the hip at column offset u."""
    d = (u + 8) / 9.5
    return 10 * math.sqrt(1 - d * d) if abs(d) < 1 else 0.0


def mantle_height(u: float) -> float:
    """Height of the mantle (the humped shield over the front half)."""
    d = (u + 1) / 9.5
    return 15.5 * math.sqrt(1 - d * d) if abs(d) < 1 else 0.0


class SlugMantle(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        moving = {"walk": 1.3, "run": 1.9}.get(pose.anim, 0)
        breath = 1 if pose.anim == "idle" and pose.bob else 0     # mantle swells on the in-breath
        ph = 2 * math.pi * pose.frame / pose.n
        tops = {}
        for u in range(-20, 9):
            m, b = mantle_height(u), back_height(u)
            h = max(b, m + breath * (u > -7))
            h += moving * math.sin(u * 0.4 - ph)                  # muscle ripple rolling forward
            if h < 0.5:
                continue
            x, top = cx + u, hip + 1 - round(h)
            tops[u] = top
            for y in range(top, hip + 2):
                d = y - top
                if y >= hip:
                    col = P["body_dk"]                            # belly crease above the foot
                elif d == 0 and u > -11:
                    col = P["body_hi"]
                elif m < b or y > hip - 3:
                    col = P["body_sh"]                            # hindquarters sit in shade
                elif d <= 2 and u > -4:
                    col = P["body_hi"] if d == 1 and u > 0 else P["body"]
                else:
                    col = P["body"]
                if d > 0 and y < hip and spotted(u, y - hip):
                    col = P["spot"]
                c.set(x, y, col)
        # mantle rim: a groove where the shield meets the body
        for u in range(-10, 8):
            y = hip - 3 - (2 if u < -7 else 0) - (2 if u < -9 else 0)
            if u in tops and tops[u] < y:
                c.set(cx + u, y, P["body_dk"] if u < -7 else P["body_sh"])
        # tubercle grooves along the hindquarters
        for u in range(-18, -10, 3):
            if u in tops:
                c.line(cx + u, tops[u] + 1, cx + u - 1, hip - 1, P["body_dk"])
        # breathing hole on the mantle rim: opens and closes
        open_ = pose.anim == "idle" and pose.frame < 2 or pose.anim in ("walk", "run") and pose.frame % 2 == 0
        c.rect(cx - 5, hip - 5, 2, 2 if open_ else 1, P["hole"])
        c.set(cx - 3, hip - 5, P["body_hi"])
        # wet glints
        for u in (-4, -1, 2):
            if u in tops:
                c.set(cx + u, tops[u] + 1, P["gloss"])
        c.set(cx - 12, tops.get(-12, hip) + 1, P["gloss"])
        return Anchors(neck=(cx + 8, hip + 1), shoulder=(cx + 1, hip - 5), top=min(tops.values()), bottom=hip)


class SlugHead(Head):
    """Snout with two tall eye stalks (they retract when hit) and two short feelers."""
    species = SPECIES

    def stalk(self, c: Canvas, bx: int, by: int, tx: int, ty: int, front: bool, pose: Pose) -> None:
        col = P["body"] if front else P["body_sh"]
        c.line(bx, by, tx, ty, col, width=2)
        c.oval(tx - 1, ty - 2, 4, 4, col)
        if front:
            c.set(tx + 1, ty - 2, P["body_hi"])
        if pose.blink and front:
            c.hline(tx, tx + 1, ty, P["body_dk"])
        else:
            c.rect(tx, ty - 1, 2, 2, P["eye_w"] if front else P["sole"])
            c.set(tx + 1, ty, INK)                                 # pupil looks ahead

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        sway = wave(pose.frame, pose.n, 1)
        flinch = pose.anim in ("hurt", "death")
        reach = 3 if flinch else 12 + (pose.bob < 0)              # stalks shoot up, or retract when hit
        lean = {"jump": -2, "attack": 2}.get(pose.anim, 0)
        # far stalk first, a little behind the near one
        self.stalk(c, nx + 1, ny - 6, nx + lean + sway, ny - 5 - reach, False, pose)
        # snout
        c.oval(nx - 3, ny - 8, 10, 9, P["body"])
        c.hline(nx - 1, nx + 3, ny - 8, P["body_hi"])
        c.set(nx + 5, ny - 6, P["body_hi"])
        c.hline(nx - 3, nx + 6, ny, P["body_sh"])
        c.set(nx + 1, ny - 5, P["spot"])
        c.set(nx - 1, ny - 3, P["spot"])
        self.stalk(c, nx + 4, ny - 6, nx + 6 + lean - sway, ny - 6 - reach, True, pose)
        # short lower feelers and a little smile
        wig = (pose.frame % 2) if not flinch else 0
        c.line(nx + 6, ny - 3, nx + 8, ny - 2 + wig, P["body"])
        c.line(nx + 5, ny - 1, nx + 8, ny + wig, P["body_sh"])
        c.set(nx + 4, ny - 2, P["mouth"])
        c.set(nx + 3, ny - 3, P["mouth"])


class Pseudopod(Arm):
    """A stubby, slimy feeler. It flicks globs of acid."""
    species = SPECIES
    reach = 6
    fx_colors = (P["acid"], P["acid_hi"])
    targets = {"strike": ((1.0, -0.3), (-0.7, 0.55)), "follow": ((1.0, -0.1), (-0.6, 0.7))}

    def blob(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, front: bool, drip: int) -> None:
        col, hi = (P["body"], P["body_hi"]) if front else (P["body_sh"], P["body"])
        c.stroke(sx, sy, hx, hy, col, 3)
        c.oval(hx - 1, hy - 1, 4, 4, col)
        c.set(hx + 1, hy - 1, hi)
        if front and drip and hy + 3 <= GROUND:
            c.vline(hx + 1, hy + 3, min(GROUND, hy + 2 + drip), P["slime"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        d = pose.swing if front else -pose.swing
        wig = wave(pose.frame, pose.n, 1)
        self.blob(c, sx, sy, sx + 2 + d, sy + 3 + wig, front, 1 + pose.frame % 2)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1)
        c.stroke(sx, sy, ex, ey, P["body"] if front else P["body_sh"], 3)
        self.blob(c, ex, ey, hx, hy, front, 0 if mode in ("strike", "follow") else 1)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                                  # PTOO: a glob of acid in flight
            gx, gy = hx + 6, hy - 3
            fx.oval(gx, gy, 4, 4, P["acid"])
            fx.set(gx + 2, gy + 1, P["acid_hi"])
            fx.set(gx + 1, gy + 3, P["acid_sh"])
            for dx, dy in ((-2, 2), (-4, 3), (-3, 0)):          # droplets trailing behind
                fx.set(gx + dx, gy + dy, P["acid"])
        else:                                                    # SPLAT, with sizzle bubbles
            gx, gy = hx + 9, hy - 2
            fx.oval(gx - 1, gy - 1, 3, 3, P["acid"])
            fx.set(gx, gy, P["acid_hi"])
            for dx, dy in ((-3, -2), (2, -3), (2, 2), (-3, 2), (0, -4), (0, 4), (3, 0)):
                fx.set(gx + dx, gy + dy, P["acid"])
            for dx, dy in ((-1, -6), (2, -6), (-4, -4)):          # sizzle bubbles
                fx.set(gx + dx, gy + dy, P["acid_hi"])


GENES = dict(legs=SlugFoot(), torso=SlugMantle(), head=SlugHead(), arm=Pseudopod())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
