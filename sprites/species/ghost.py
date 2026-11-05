"""Ghost: a classic bedsheet ghost. Hollow eyes, stubby sheet-arms, a hem that never
touches the floor. Attacks by saying BOO, which is somehow enough."""

import math

from ..canvas import Canvas, wave
from ..font import draw_text, text_width
from ..palette import INK, GHOST as P
from ..rig import GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "ghost"
PREFIX, SUFFIX = "Spoo", "ghost"


def sheet_col(x: int, y: int, x0: int, x1: int, fade: float) -> str:
    """Sheet shading: shadowed back edge, lit front edge, going see-through toward the hem
    (an ordered dither, since there's no alpha in 8-bit land)."""
    if fade > 0.55 and (x + y) % 2 == 0 or fade > 0.85:
        return P["fade"]
    if fade > 0.3 and (x + y) % 2 == 0 or x <= x0 + 1:
        return P["sheet_dk"] if x <= x0 + 1 and fade > 0.3 else P["sheet_sh"]
    if x >= x1:
        return P["sheet_hi"]
    return P["sheet"]


class GhostHem(Legs):
    """No legs, just the trailing sheet. The scalloped hem ripples as it floats,
    trails behind when moving and streams out into a wisp at a run."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        trail = {"walk": 3, "run": 7, "hurt": -2, "death": -2}.get(pose.anim, 1) + pose.lift // 2
        rise = {"run": 4}.get(pose.anim, 0)                    # at a run, the hem lifts into a tail
        ph = 2 * math.pi * pose.frame / pose.n
        bottom = ground - 1 - rise                             # tips just brush the floor
        rows = max(1, bottom - hip)
        for y in range(hip, bottom + 2):
            t = min(1.0, (y - hip) / rows)
            drift = round(trail * t * t + pose.swing * t)
            x0 = cx - 8 - round(1 * t) - drift
            x1 = cx + 5 + round(1 * t) - drift - round(rise * 1.5 * t * t)
            for x in range(x0, x1 + 1):
                # scallops: three lazy points along the bottom that roll backward each frame
                low = bottom - 1 + round(1.5 * math.sin((x - x0) * 2 * math.pi / 5 + ph))
                if y > low:
                    continue
                fade = max(0.0, 1 - (low - y) / 4)
                c.set(x, y, sheet_col(x, y, x0, x1, fade if t > 0.4 else 0.0))
        # a fold or two hanging down from the hips
        for fold in (cx - 2, cx + 2):
            for y in range(hip + 1, bottom - 3):
                t = (y - hip) / rows
                x = fold - round(trail * t * t + pose.swing * t) + round(wave(pose.frame + y // 3, pose.n, 0.6))
                if c.get(x, y) in (P["sheet"], P["sheet_hi"]):
                    c.set(x, y, P["sheet_sh"])


class GhostTorso(Torso):
    """The draped middle of the sheet. Its own little scalloped edge at the hips means
    it still reads as a sheet over somebody else's legs."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 8
        for y in range(top, hip + 3):
            bulge = min(2, (y - top) // 4)                     # the sheet belling out over whatever's inside
            x0, x1 = cx - 6 - bulge, cx + 5
            for x in range(x0, x1 + 1):
                if y > hip and (x - x0 + pose.frame) % 4 >= 2 + (y - hip):
                    continue                                   # scalloped edge
                c.set(x, y, sheet_col(x, y, x0, x1, 0.0))
        c.line(cx - 2, top + 3, cx - 4, hip - 1, P["sheet_sh"])   # folds falling off the shoulders
        c.line(cx + 1, top + 6, cx, hip, P["sheet_sh"])
        return Anchors(neck=(cx - 1, top), shoulder=(cx + 2, top + 3), top=top, bottom=hip)


HEAD = [
    ".....hhhh....",
    "...hSSSSShh..",
    "..sSSSSSSSSh.",
    ".sSSSSSSSSShh",
    ".sSSSSSSSSSSh",
    "ssSSSSSSSSSSh",
    "ssSSSSSSSSSSS",
    "ssSSSSSSSSSSS",
    "ssSSSSSSSSSSS",
    "ssSSSSSSSSSSS",
    "ssSSSSSSSSSSS",
    "ssSSSSSSSSSSS",
]


class GhostHead(Head):
    """Dome with two hollow eyes (both peeking forward, like they do) and a little 'o' mouth.
    The dome comes with a bit of drape, so on anyone else it's a kid in a costume."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 6, ny - 11
        # drape hanging over the shoulders (invisible on a ghost, a costume on anyone else)
        for y in range(ny, ny + 3):
            for x in range(x0, x0 + 13):
                if y > ny and (x + pose.frame) % 4 < y - ny:
                    continue
                c.set(x, y, sheet_col(x, y, x0, x0 + 12, 0.0))
        key = {"h": P["sheet_hi"], "S": P["sheet"], "s": P["sheet_sh"]}
        c.stamp(x0, y0, HEAD, key)
        # the face
        hurt = pose.anim in ("hurt", "death")
        boo = pose.anim == "attack" and pose.frame in (1, 2)
        for ex in (x0 + 6, x0 + 10):
            if pose.blink or hurt:                             # squeezed shut
                c.hline(ex, ex + 1, y0 + 5, P["hole"])
                c.set(ex + (1 if ex == x0 + 6 else 0), y0 + 4, P["hole"])
            else:
                c.rect(ex, y0 + 3, 2, 4, P["hole"])
                c.hline(ex, ex + 1, y0 + 3, INK)
                c.set(ex, y0 + 6, P["hole_glint"])           # a faint glow at the bottom of the void
                if boo:                                        # angry brows
                    c.set(ex + (0 if ex == x0 + 6 else 1), y0 + 3, P["sheet"])
        mx, my = x0 + 8, y0 + 8
        if boo:                                                # BOO: mouth wide open
            c.stamp(mx, my - 1, [".MM.", "MMMM", "MMMM", ".MM."], {"M": P["mouth"]})
        elif hurt:
            c.stamp(mx, my + 1, ["M.M.", ".M.M"], {"M": P["mouth"]})   # wobbly frown
        else:
            c.stamp(mx + 1, my, ["MM", "MM"], {"M": P["mouth"]})


# The nubs are too short to reach back across the sheet, so every pose stays out front.
WAIL_TARGETS = {
    "windup": ((0.55, 0.7), (-0.3, 0.95)),                     # hunch, gather...
    "strike": ((1.0, -0.35), (0.6, -0.8)),                     # ...then lunge
    "follow": ((1.0, -0.2), (0.5, -0.7)),
    "recover": ((0.85, 0.35), (-0.25, 0.95)),
    "crouch": ((0.75, 0.55), (-0.7, 0.6)),
    "flail": ((0.95, -0.2), (-0.9, -0.4)),                     # flinch, arm flung out
}


class GhostArm(Arm):
    """A stubby sheet-arm with a floppy, drooping end. Attack: lunges with a BOO!"""
    species = SPECIES
    reach = 6
    fx_colors = (P["wail"], P["wail_alt"])
    targets = WAIL_TARGETS

    def nub(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, front: bool, flop: int) -> None:
        col, sh = (P["sheet"], P["sheet_sh"]) if front else (P["sheet_sh"], P["sheet_dk"])
        c.stroke(sx, sy, hx, hy, col, 3)
        c.rect(hx - 1, hy - 1, 3, 3, col)
        c.vline(hx - 1, hy + 1, hy + 2 + flop, sh)             # the sheet hangs off it
        c.vline(hx, hy + 1, hy + 1 + flop, sh)
        if front:
            c.set(hx + 1, hy - 1, P["sheet_hi"])

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        d = pose.swing if front else -pose.swing
        bob = wave(pose.frame, pose.n, 1)
        self.nub(c, sx, sy, sx + 4 + d, sy + 2 + bob, front, 1 + pose.frame % 2)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1)
        c.stroke(sx, sy, ex, ey, P["sheet"] if front else P["sheet_sh"], 3)
        self.nub(c, ex, ey, hx, hy, front, 2 if mode in ("windup", "flail", "up") else 1)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                                # a spooky wail ring rolling out
            cx, cy = hx + 1, hy
            for k, r in enumerate((4, 7)):
                for i in range(-4, 5):
                    a = i * 0.22
                    x, y = round(cx + math.cos(a) * r), round(cy + math.sin(a) * r)
                    if x <= 44 and 2 <= y <= 44:
                        fx.set(x, y, P["wail"] if (i + k) % 3 else P["wail_alt"])
        else:                                                  # BOO
            text = "BOO"
            w = text_width(text)
            x = max(2, min(hx, 44 - w))                        # clear of the face, inside the frame
            y = max(4, min(hy - 7, GROUND - 6))
            draw_text(fx, x, y, text, P["boo"])
            for dx, sl in ((1, -1), (w // 2, 0), (w - 1, 1)):  # shock lines bursting off it
                fx.line(x + dx, y - 2, x + dx + sl, y - 3, P["wail"])
            for i in range(-2, 3):                             # the wail ring, landing
                fx.set(hx + 2 + abs(i) // 2 * -1, hy + 2 + i, P["wail_alt"])


GENES = dict(legs=GhostHem(), torso=GhostTorso(), head=GhostHead(), arm=GhostArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
