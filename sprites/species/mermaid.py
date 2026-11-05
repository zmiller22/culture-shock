"""Mermaid: a fish out of water. Hops around on her tail and pokes things with a trident."""

import math

from ..canvas import Canvas, wave
from ..palette import INK, MERMAID as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "mermaid"
PREFIX, SUFFIX = "Mer", "maid"


# -- scaly tubes (shared with the medusa's snake tail) -------------------------

def spline(pts: list[tuple[float, float]], steps: int = 6) -> list[tuple[float, float]]:
    """Catmull-Rom curve through `pts`, sampled densely."""
    ext = [pts[0], *pts, pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = ext[i - 1:i + 3]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * (2 * x1 + (x2 - x0) * t + (2 * x0 - 5 * x1 + 4 * x2 - x3) * t2 + (3 * x1 - x0 - 3 * x2 + x3) * t3),
                0.5 * (2 * y1 + (y2 - y0) * t + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t2 + (3 * y1 - y0 - 3 * y2 + y3) * t3),
            ))
    out.append(pts[-1])
    return out


def tube(c: Canvas, pts: list[tuple[float, float]], width, shade) -> None:
    """Paint a round tube along dense points `pts`, back to front.

    width(t) gives the diameter at t (0 = first point, 1 = last). Each pixel is
    colored by shade(x, y, ox, oy, s, t): (ox, oy) is how far the pixel sits off
    the center line (-1..1 per axis) for lighting, and s is the same distance
    signed by side (+ = right-hand side of the direction of travel).
    """
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / max(1, n - 1)
        x1, y1 = pts[min(n - 1, i + 1)]
        x0, y0 = pts[max(0, i - 1)]
        tl = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / tl, (x1 - x0) / tl              # normal to the curve
        r = width(t) / 2
        for yy in range(math.floor(y - r), math.ceil(y + r) + 1):
            for xx in range(math.floor(x - r), math.ceil(x + r) + 1):
                dx, dy = xx + 0.5 - x, yy + 0.5 - y
                if dx * dx + dy * dy > r * r + 0.3:
                    continue
                s = (dx * nx + dy * ny) / max(r, 0.5)            # signed distance across the tube
                c.set(xx, yy, shade(xx, yy, s * nx, s * ny, s, t))


def fan(c: Canvas, x: float, y: float, angle: float, spread: float, length, col, rib: str) -> None:
    """A fin: rays fanned out from (x, y) around `angle`. length(u) for u in -1..1."""
    rays = 13
    for k in range(rays):
        u = -1 + 2 * k / (rays - 1)
        a = angle + u * spread
        ln = length(u)
        x1, y1 = x + math.cos(a) * ln, y + math.sin(a) * ln
        c.line(round(x), round(y), round(x1), round(y1), rib if k % 3 == 1 else col)


# -- genes ---------------------------------------------------------------------

def scales(x: int, y: int) -> bool:
    """Scallop pattern: staggered dots every other row."""
    return y % 2 == 0 and (x + (y // 2) % 2 * 2) % 4 == 0


class MermaidTail(Legs):
    """Fish tail standing in for legs: down from the hips, along the floor, fin up behind."""
    species = SPECIES
    length = 13

    def path(self, cx: int, hip: int, ground: int, pose: Pose) -> list[tuple[float, float]]:
        h = ground - hip
        moving = pose.anim in ("walk", "run")
        flap = wave(pose.frame, pose.n, 2.5 if moving else 1.5) if pose.anim in ("idle", "walk", "run") else 0
        arch = 2 * pose.lift                                   # hop: the tail bunches up off the floor
        s = 2 * pose.swing                                     # ...then shoves the body forward
        flat = [
            (cx - 1, hip), (cx + 1.5 + s * 0.5, hip + h * 0.45), (cx + 0.5, ground - 2),
            (cx - 5 - s, ground - 2 - arch), (cx - 10 - s, ground - 3 - arch * 0.5),
            (cx - 13 - s * 0.5, ground - 7 - arch + flap),
        ]
        coil = [                                               # jump: tail curls up under her
            (cx - 1, hip), (cx + 2, hip + h * 0.5), (cx, ground - 1),
            (cx - 5, ground - 2), (cx - 9, ground - 5), (cx - 11, ground - 10),
        ]
        k = min(1.0, pose.tuck / 5)
        return [(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k) for a, b in zip(flat, coil)]

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        ctrl = self.path(cx, hip, ground, pose)
        pts = spline(ctrl)

        def shade(x, y, ox, oy, s, t):
            lit = 0.55 * ox - 0.85 * oy                        # light from the upper right
            if lit > 0.5:
                return P["tail_hi"]
            if lit < -0.45:
                return P["tail_dk"] if t > 0.15 else P["tail_sh"]
            if lit < -0.1 or scales(x, y):
                return P["tail_sh"]
            return P["tail"]

        tube(c, pts, lambda t: 8 - 5 * t, shade)
        # fluke: two lobes fanned out from the tail tip, notched in the middle
        (x0, y0), (x1, y1) = pts[-3], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        flop = 0.15 * wave(pose.frame, pose.n, 1, 1.5)
        fan(c, x1, y1, ang + flop, 1.05, lambda u: 6 - 3.5 * math.exp(-u * u * 12), P["fin"], P["fin_sh"])


class MermaidTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 10
        rows = [
            "..sSSSS.",
            ".sSSSSSS",
            ".sSSSSSS",
            ".sSSSKkh",
            ".sSSSKKk",
            "..sSSSS.",
            "..sSSSS.",
            "..sSSSS.",
            ".tTTTTTt",
            "tTFTFTFTt",
            "tTTTTTTTt",
        ]
        key = {"s": P["skin_sh"], "S": P["skin"], "K": P["shell"], "k": P["shell_sh"], "h": P["shell_hi"],
               "t": P["tail_sh"], "T": P["tail"], "F": P["tail_hi"]}
        c.stamp(cx - 4, top, rows, key)
        c.set(cx + 3, top + 2, P["shell_sh"])                  # shell strap
        c.set(cx + 4, top + 4, P["shell_hi"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "....rrrr.....",
    "..rrRRRRrr...",
    ".rRRRRRRRRR..",
    "rRRRRRRRRRRR.",
    "RRRRRRRSSSSR.",
    "RRRRRRSSSBBS.",
    "RRRRRSSSSLES.",
    "RRRRRSSSSSES.",
    "RRRRRsSSSSSSN",
    "dRRRRRsSSSSS.",
    "dRRRRR.sSSmS.",
    "dRRRRR..sSS..",
    ".dRRRR.......",
    ".dRRR........",
    "..dRR........",
    "..dR.........",
]


class MermaidHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "r": P["hair_hi"], "R": P["hair"], "d": P["hair_sh"],
            "S": P["skin"], "s": P["skin_sh"], "N": P["skin"], "m": P["lips"],
            "B": P["hair_sh"], "L": P["skin_sh"] if pose.blink else INK,
            "E": P["skin_sh"] if pose.blink else P["eye"],
        }
        x0, y0 = nx - 6, ny - 13
        c.stamp(x0, y0, HEAD, key)
        sway = wave(pose.frame, pose.n, 1)                    # hair tips drift
        c.vline(x0 + 1 + sway, y0 + 16, y0 + 17, P["hair_sh"])
        c.set(x0 + 4, y0 + 1, P["shell_hi"])                   # starfish clip
        c.set(x0 + 3, y0 + 2, P["shell"])
        c.set(x0 + 5, y0 + 2, P["shell"])


class MermaidArm(Arm):
    """Slim arm. The front hand never lets go of her golden trident. Attack: thrust + splash."""
    species = SPECIES
    reach = 9
    fx_colors = (P["water"], P["foam"])
    targets = {"windup": ((-0.6, 0.4), (-0.4, 0.85)), "strike": ((0.9, 0.0), (-0.7, 0.55)),
               "follow": ((0.85, 0.15), (-0.6, 0.7))}

    def trident(self, c: Canvas, x: int, y: int, dx: int, dy: int, back: int = 6, front: int = 10) -> None:
        """Trident through the fist at (x, y), pointing along unit axis (dx, dy)."""
        px, py = -dy, dx                                       # sideways
        c.line(x - dx * back, y - dy * back, x + dx * front, y + dy * front, P["gold_sh"])
        tx, ty = x + dx * front, y + dy * front                # crossbar + three prongs
        c.line(tx - 2 * px, ty - 2 * py, tx + 2 * px, ty + 2 * py, P["gold"])
        for k in (-2, 0, 2):
            ln = 3 if k == 0 else 2
            c.line(tx + k * px, ty + k * py, tx + k * px + dx * ln, ty + k * py + dy * ln, P["gold"])
        c.set(tx + dx * 3, ty + dy * 3, "#fff6c0")              # glint on the center tip

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        if front:                                              # trident held upright, out in front of her face
            sway = -pose.swing
            c.line(sx, sy, sx + 1, sy + 4, skin, width=2)
            c.line(sx + 1, sy + 5, sx + 7 + sway, sy + 4, skin)
            c.line(sx + 1, sy + 4, sx + 7 + sway, sy + 3, skin)
            self.trident(c, sx + 9 + sway, sy + 4, 0, -1, back=9, front=9)
            c.rect(sx + 8 + sway, sy + 3, 2, 2, skin)
            c.set(sx + 5, sy + 4, P["gold"])                    # bracelet
        else:
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 7, skin, width=2)
            c.rect(sx + dx, sy + 8, 2, 2, skin)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        if front:
            if mode in ("windup", "strike", "follow"):        # level for the thrust
                self.trident(c, hx + 1, hy, 1, 0, back=9, front=6)
            else:
                self.trident(c, hx + 1, hy, 0, -1, back=7, front=9)
        c.rect(hx, hy, 2, 2, skin)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        tip = hx + 10                                          # center prong tip
        if pose.fx == "swoosh":                                # water streaming off the prongs
            for dy, x0, col in ((-4, tip - 10, P["water"]), (4, tip - 9, P["water"]), (-6, tip - 6, P["foam"])):
                fx.hline(x0, tip - 4, hy + dy, col)
            fx.set(tip - 3, hy + 6, P["water"])
        else:                                                  # SPLASH: a crown of water around the prongs
            for dx, dy in ((-1, -4), (0, -6), (1, -5), (2, -3), (-1, 4), (0, 6), (1, 5), (2, 3)):
                fx.set(tip + dx, hy + dy, P["water"])
            for dx, dy in ((-3, -7), (2, -8), (-3, 7), (2, 8), (2, -1), (2, 1)):
                fx.set(tip + dx, hy + dy, P["foam"])


GENES = dict(legs=MermaidTail(), torso=MermaidTorso(), head=MermaidHead(), arm=MermaidArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
