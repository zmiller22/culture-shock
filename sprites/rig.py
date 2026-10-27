"""Body-plan rig: every creature is legs + torso + head + two arms ("genes").

Each gene is a small class with a `draw` method that paints into its own layer.
Layers are outlined and composited in a fixed back-to-front order, so a
creature built from genes of different species still reads cleanly.

Normal characters merge legs/torso/head into one outline group so they look
seamless. Kronenberg mutants keep every gene in its own group, which leaves
visible seams -- then we stitch them up.

Animation states are described entirely by `Pose` values (see ANIMATIONS), so
every gene -- and therefore every spliced creature -- gets every state for free.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from .canvas import Canvas
from .palette import OUTLINE

SIZE = 48          # every frame is SIZE x SIZE
CX = 24            # body center column
GROUND = 45        # lowest row a foot touches (outline goes one below)


@dataclass
class Pose:
    anim: str                 # animation name
    frame: int                # frame index within the animation
    n: int                    # frames in the animation
    swing: int = 0            # leg stride: + = front leg forward (walk 1, run 2)
    bob: int = 0              # vertical body offset (+ = down)
    blink: bool = False
    lift: int = 0             # raise the back foot (passing frames)
    tuck: int = 0             # raise both feet toward the hip (airborne)
    lean: int = 0             # shift torso/head/arms forward (+) or back (-)
    arm: str = "swing"        # front arm pose; see ARM_TARGETS
    back_arm: str | None = None   # back arm pose (defaults to `arm`)
    fx: str | None = None     # attack effect: "swoosh" | "impact"
    flash: bool = False       # white hit-flash
    melt: float = 0.0         # 0..1, dissolve into goo (death)


_HURT = dict(lean=-2, bob=1, blink=True, arm="flail")

ANIMATIONS: dict[str, list[dict]] = {
    # breathe, blink on the last frame
    "idle": [dict(bob=0), dict(bob=0), dict(bob=1), dict(bob=1, blink=True)],
    # contact / pass / contact / pass
    "walk": [dict(swing=1), dict(bob=-1, lift=1), dict(swing=-1), dict(bob=-1, lift=1)],
    # longer stride, airborne pass frames, leaning in
    "run": [dict(swing=2, lean=1), dict(bob=-1, lift=3, lean=1),
            dict(swing=-2, lean=1), dict(bob=-1, lift=3, lean=1)],
    # crouch / take-off / apex / falling  (no baked height: the game moves the sprite)
    "jump": [dict(swing=1, bob=3, lean=1, arm="crouch"),
             dict(swing=1, tuck=1, bob=-1, arm="reach", back_arm="up"),
             dict(swing=1, tuck=5, bob=-1, arm="out"),
             dict(tuck=1, arm="out", back_arm="up")],
    # wind-up / strike / follow-through / recover
    "attack": [dict(bob=1, lean=-1, arm="windup"),
               dict(swing=1, lean=2, arm="strike", fx="swoosh"),
               dict(swing=1, lean=2, arm="follow", fx="impact"),
               dict(lean=1, arm="recover")],
    # recoil / recoil + white flash
    "hurt": [dict(_HURT), dict(_HURT, lean=-3, flash=True)],
    # recoil, then melt into a puddle of lab goo
    "death": [dict(_HURT, flash=True)] + [dict(_HURT, melt=t) for t in (0.25, 0.5, 0.75, 0.9, 1.0)],
    # dropping down / held low (hold the last frame while DOWN is held)
    "crouch": [dict(swing=1, bob=3, lean=1, arm="crouch"), dict(swing=1, bob=5, lean=1, arm="crouch")],
    # reach / press / hold / recover: doors, switches, levers
    "interact": [dict(lean=1, arm="reach", back_arm="recover"),
                 dict(swing=1, lean=2, arm="use", back_arm="recover"),
                 dict(swing=1, lean=2, arm="use", back_arm="recover"),
                 dict(lean=1, arm="recover")],
}
FPS = {"idle": 4, "walk": 8, "run": 12, "jump": 8, "attack": 12, "hurt": 10, "death": 8, "crouch": 12, "interact": 10}
LOOP = {"idle": True, "walk": True, "run": True, "jump": False, "attack": False, "hurt": False, "death": False,
        "crouch": False, "interact": False}


def poses(anim: str) -> list[Pose]:
    spec = ANIMATIONS[anim]
    return [Pose(anim, i, len(spec), **kw) for i, kw in enumerate(spec)]


@dataclass
class Anchors:
    """Attachment points a torso exposes for the rest of the body."""
    neck: tuple[int, int]
    shoulder: tuple[int, int]
    top: int
    bottom: int


class Gene:
    species: str = "?"
    kind: str = "?"


class Legs(Gene):
    kind = "legs"
    length = 10

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        raise NotImplementedError


class Torso(Gene):
    kind = "torso"

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        raise NotImplementedError


class Head(Gene):
    kind = "head"

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        raise NotImplementedError


# Where the hand goes for each arm pose, as a direction from the shoulder that
# gets scaled by the arm's reach. {pose: (front arm, back arm)}
ARM_TARGETS: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "crouch":  ((-0.3, 0.9), (-0.7, 0.6)),
    "up":      ((0.7, -0.7), (-0.25, -0.95)),
    "reach":   ((0.9, -0.4), (-0.8, -0.5)),
    "out":     ((0.9, -0.35), (-0.9, -0.3)),
    "windup":  ((-0.75, 0.25), (-0.4, 0.85)),
    "strike":  ((1.0, 0.05), (-0.7, 0.55)),
    "follow":  ((0.95, 0.3), (-0.6, 0.7)),
    "recover": ((0.55, 0.75), (-0.25, 0.95)),
    "flail":   ((-0.7, 0.5), (-0.9, -0.4)),      # flung back by the hit
    "use":     ((1.0, -0.2), (-0.4, 0.85)),      # flat-out press at chest height
}


def elbow(sx: int, sy: int, hx: int, hy: int, bend: float) -> tuple[int, int]:
    """Elbow point: the shoulder-hand midpoint pushed out sideways, bending down/back."""
    dx, dy = hx - sx, hy - sy
    length = math.hypot(dx, dy) or 1
    px, py = -dy / length, dx / length
    if py < 0 or (py == 0 and px > 0):
        px, py = -px, -py
    return round((sx + hx) / 2 + px * bend), round((sy + hy) / 2 + py * bend)


class Arm(Gene):
    """Arms have two drawing paths:

    * `draw_swing` -- the hand-tuned resting/walking arm (idle, walk, run)
    * `draw_limb`  -- reach the hand to an arbitrary point (every other pose)
    """
    kind = "arm"
    reach = 9                                   # shoulder-to-hand length in px
    targets: dict = {}                          # per-gene overrides of ARM_TARGETS
    fx_colors = ("#ffffff", "#fff27a")          # (main, accent) for attack effects

    def direction(self, mode: str, front: bool) -> tuple[float, float]:
        f, b = {**ARM_TARGETS, **self.targets}[mode]
        return f if front else b

    def draw(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> tuple[int, int] | None:
        mode = pose.arm if front else (pose.back_arm or pose.arm)
        if mode == "swing":
            self.draw_swing(c, sx, sy, pose, front)
            return None
        dx, dy = self.direction(mode, front)
        hx, hy = sx + round(dx * self.reach), sy + round(dy * self.reach)
        self.draw_limb(c, sx, sy, hx, hy, pose, front, mode)
        return hx, hy

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        raise NotImplementedError

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        raise NotImplementedError

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        """Default effect: a swoosh (speed lines, or an arc for long arms), then an impact star."""
        main, accent = self.fx_colors
        if pose.fx == "swoosh" and self.reach < 10:             # short arms: speed lines behind the fist
            for dy, x0, col in ((-2, hx - 6, main), (1, hx - 8, accent), (4, hx - 5, main)):
                fx.hline(x0, hx - 3, hy + dy, col)
        elif pose.fx == "swoosh":                               # long arms: trail from wind-up to strike
            a0 = math.atan2(*reversed(self.direction("windup", True)))
            a1 = math.atan2(*reversed(self.direction("strike", True)))
            if a1 < a0:
                a1 += math.tau
            r = self.reach + 2
            steps = 14
            for i in range(steps // 3, steps):                  # skip the start: trail fades in
                a = a0 + (a1 - a0) * i / steps
                x, y = sx + round(math.cos(a) * r), sy + round(math.sin(a) * r)
                fx.set(x, y, accent if i > steps * 2 // 3 else main)
                fx.set(x + 1, y, main)
        elif pose.fx == "impact":
            star(fx, hx + 4, hy, main, accent)


def star(c: Canvas, x: int, y: int, main: str, accent: str, r: int = 3) -> None:
    """Little 8-direction impact burst."""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        c.line(x + dx, y + dy, x + dx * r, y + dy * r, main)
    for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
        c.set(x + dx * (r - 1), y + dy * (r - 1), accent)
    c.set(x, y, accent)


# A decoration painted after compositing: fn(final_canvas, layers, info, pose)
Decoration = Callable[[Canvas, dict, dict, Pose], None]


@dataclass
class BodyPlan:
    legs: Legs
    torso: Torso
    head: Head
    front_arm: Arm
    back_arm: Arm
    seamless: bool = True                 # one outline around legs+torso+head
    extra_heads: list[tuple[Head, int, int]] = field(default_factory=list)  # (head, dx, dy), drawn mirrored behind the main head
    layer_fx: dict[str, Callable[[Canvas, Pose], None]] = field(default_factory=dict)  # per-layer post-process
    decorations: list[Decoration] = field(default_factory=list)

    def render(self, pose: Pose) -> Canvas:
        from .effects import hit_flash, melt   # effects imports rig constants

        # Back-to-front group order.
        body = "body" if self.seamless else None
        order = ["extra_heads", "back_arm", body or "legs", body or "torso", body or "head", "front_arm", "fx"]
        layers: dict[str, Canvas] = {}
        for name in order:
            layers.setdefault(name, Canvas(SIZE, SIZE))

        hip = GROUND - self.legs.length + pose.bob
        ux = CX + pose.lean                      # upper body x
        self.legs.draw(layers[body or "legs"], CX, hip, GROUND - pose.tuck, pose)
        a = self.torso.draw(layers[body or "torso"], ux, hip, pose)
        self.head.draw(layers[body or "head"], a.neck[0], a.neck[1], pose)
        for head, dx, dy in self.extra_heads:      # extra heads grow facing backward
            tmp = Canvas(SIZE, SIZE)
            head.draw(tmp, SIZE - 1 - (a.neck[0] + dx), a.neck[1] + dy, pose)
            layers["extra_heads"].paste(tmp.flipped())
        sx, sy = a.shoulder
        self.back_arm.draw(layers["back_arm"], sx - 1, sy, pose, front=False)
        hand = self.front_arm.draw(layers["front_arm"], sx, sy, pose, front=True)
        if pose.fx and hand:
            self.front_arm.attack_fx(layers["fx"], sx, sy, hand[0], hand[1], pose)

        out = Canvas(SIZE, SIZE)
        for name, layer in layers.items():
            if name in self.layer_fx:
                self.layer_fx[name](layer, pose)
            layer.outline(OUTLINE)
            if name != "fx":
                out.paste(layer)

        info = {"hip": hip, "anchors": a}
        for deco in self.decorations:
            deco(out, layers, info, pose)
        if pose.flash:
            hit_flash(out)
        if pose.melt:
            melt(out, pose.melt)
        out.paste(layers["fx"])                  # effects sit on top, never flash or melt
        return out
