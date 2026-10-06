"""The roster: every character the game knows about, normal and spliced."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .canvas import Canvas
from .rig import ANIMATIONS, Pose, poses
from .species import banana_dude, sasquatch, swamp_monster, tech_bro
from .species.kronenberg import CURATED, Specimen, random_specimen


@dataclass
class Character:
    slug: str
    name: str
    kind: str                                  # "control" (normal) or "kronenberg"
    render: Callable[[Pose], Canvas]
    meta: dict = field(default_factory=dict)

    def frames(self, anim: str) -> list[Canvas]:
        return [self.render(p) for p in poses(anim)]

    def all_frames(self) -> dict[str, list[Canvas]]:
        return {anim: self.frames(anim) for anim in ANIMATIONS}


CONTROL_GROUP = [
    ("tech_bro", "Tech Bro", tech_bro),
    ("swamp_monster", "Swamp Monster", swamp_monster),
    ("sasquatch", "Sasquatch", sasquatch),
    ("banana_dude", "Banana Dude", banana_dude),
]


def from_specimen(sp: Specimen) -> Character:
    return Character(
        slug=sp.slug, name=sp.name, kind="kronenberg", render=sp.render,
        meta={"specimen": sp.number, "recipe": sp.recipe, "mutations": sp.mutations},
    )


def roster(mutants: int = 0, seed: int = 100) -> list[Character]:
    """Control group + curated Kronenbergs + `mutants` random ones starting at `seed`."""
    chars = [Character(slug, name, "control", mod.build().render) for slug, name, mod in CONTROL_GROUP]
    chars += [from_specimen(sp) for sp in CURATED]
    chars += [from_specimen(random_specimen(seed + i)) for i in range(mutants)]
    return chars
