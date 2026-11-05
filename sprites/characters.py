"""The roster: every character the game knows about, normal and spliced."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .canvas import Canvas
from .rig import ANIMATIONS, Pose, poses
from .species import (alien, banana_dude, centaur, cowboy, crawling_baby, detective, dominatrix,
                      fairy, fly_man, ghost, giant_slug, gimp, headless_horseman, jazz_sax,
                      katana_chick, medusa, mermaid, pageant_queen, puppet, sasquatch, sassquatch,
                      spider, stephen_hawking, stoner, succubus, swamp_monster, tech_bro,
                      technoviking, wyvern, zombie)
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
    ("sassquatch", "Sassquatch", sassquatch),
    ("fly_man", "Fly Man", fly_man),
    ("alien", "Alien", alien),
    ("zombie", "Zombie", zombie),
    ("mermaid", "Mermaid", mermaid),
    ("medusa", "Medusa", medusa),
    ("giant_slug", "Giant Slug", giant_slug),
    ("centaur", "Centaur", centaur),
    ("wyvern", "Wyvern", wyvern),
    ("katana_chick", "Katana Chick", katana_chick),
    ("pageant_queen", "Pageant Queen", pageant_queen),
    ("succubus", "Succubus", succubus),
    ("fairy", "Fairy", fairy),
    ("cowboy", "Cowboy", cowboy),
    ("spider", "Spider", spider),
    ("stoner", "Stoner", stoner),
    ("crawling_baby", "Crawling Baby", crawling_baby),
    ("technoviking", "Technoviking", technoviking),
    ("jazz_sax", "Jazz Saxophonist", jazz_sax),
    ("ghost", "Ghost", ghost),
    ("headless_horseman", "Headless Horseman", headless_horseman),
    ("detective", "Detective", detective),
    ("puppet", "Puppet", puppet),
    ("dominatrix", "Dominatrix", dominatrix),
    ("gimp", "Gimp", gimp),
    ("stephen_hawking", "Stephen Hawking", stephen_hawking),
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
