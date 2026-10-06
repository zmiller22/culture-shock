"""Body-plan rig: every creature is legs + torso + head + two arms ("genes").

Each gene is a small class with a `draw` method that paints into its own layer.
Layers are outlined and composited in a fixed back-to-front order, so a
creature built from genes of different species still reads cleanly.

Normal characters merge legs/torso/head into one outline group so they look
seamless. Kronenberg mutants keep every gene in its own group, which leaves
visible seams -- then we stitch them up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .canvas import Canvas
from .palette import OUTLINE

SIZE = 48          # every frame is SIZE x SIZE
CX = 24            # body center column
GROUND = 45        # lowest row a foot touches (outline goes one below)


@dataclass
class Pose:
    anim: str          # "idle" or "walk"
    frame: int         # frame index within the animation
    n: int             # frames in the animation
    swing: int = 0     # -1 / 0 / +1: which leg is forward
    bob: int = 0       # vertical body offset (+ = down)
    blink: bool = False


# idle: breathe + blink on the last frame; walk: contact/pass/contact/pass
ANIMATIONS: dict[str, list[dict]] = {
    "idle": [dict(bob=0), dict(bob=0), dict(bob=1), dict(bob=1, blink=True)],
    "walk": [dict(swing=1, bob=0), dict(swing=0, bob=-1), dict(swing=-1, bob=0), dict(swing=0, bob=-1)],
}
FPS = {"idle": 4, "walk": 8}


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


class Arm(Gene):
    kind = "arm"

    def draw(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        raise NotImplementedError


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
        # Back-to-front group order.
        body = "body" if self.seamless else None
        order = ["extra_heads", "back_arm", body or "legs", body or "torso", body or "head", "front_arm"]
        layers: dict[str, Canvas] = {}
        for name in order:
            layers.setdefault(name, Canvas(SIZE, SIZE))

        hip = GROUND - self.legs.length + pose.bob
        self.legs.draw(layers[body or "legs"], CX, hip, GROUND, pose)
        a = self.torso.draw(layers[body or "torso"], CX, hip, pose)
        self.head.draw(layers[body or "head"], a.neck[0], a.neck[1], pose)
        for head, dx, dy in self.extra_heads:      # extra heads grow facing backward
            tmp = Canvas(SIZE, SIZE)
            head.draw(tmp, SIZE - 1 - (a.neck[0] + dx), a.neck[1] + dy, pose)
            layers["extra_heads"].paste(tmp.flipped())
        sx, sy = a.shoulder
        self.back_arm.draw(layers["back_arm"], sx - 1, sy, pose, front=False)
        self.front_arm.draw(layers["front_arm"], sx, sy, pose, front=True)

        out = Canvas(SIZE, SIZE)
        for name, layer in layers.items():
            if name in self.layer_fx:
                self.layer_fx[name](layer, pose)
            layer.outline(OUTLINE)
            out.paste(layer)

        info = {"hip": hip, "anchors": a}
        for deco in self.decorations:
            deco(out, layers, info, pose)
        return out
