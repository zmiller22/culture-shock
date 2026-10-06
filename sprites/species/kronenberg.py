"""Kronenberg monsters: the splicer.

Takes genes (legs / torso / head / arms) from any species -- including the
lab-only mutant genes -- and sews them into one creature. Seams are left
visible and stitched shut, and a few extra mutations get rolled on top.

    splice(legs="sasquatch", torso="tech_bro", head="brain", front_arm="claw")
    random_specimen(seed=1234)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..canvas import Canvas
from ..palette import INK, MUTANT as M, OUTLINE, TINTS
from ..rig import CX, GROUND, SIZE, BodyPlan, Pose
from . import banana_dude, sasquatch, swamp_monster, tech_bro
from .mutant_parts import (BlobTorso, BrainJarHead, ClawArm, EyestalkHead, TentacleArm,
                           TentacleLegs, eyeball)

# gene pool: kind -> species -> gene
POOL: dict[str, dict[str, object]] = {"legs": {}, "torso": {}, "head": {}, "arm": {}}
for mod in (tech_bro, swamp_monster, sasquatch, banana_dude):
    for kind, gene in mod.GENES.items():
        POOL[kind][mod.SPECIES] = gene
POOL["legs"]["tentacle"] = TentacleLegs()
POOL["torso"]["blob"] = BlobTorso()
POOL["head"]["brain"] = BrainJarHead()
POOL["head"]["eyestalk"] = EyestalkHead()
POOL["arm"]["claw"] = ClawArm()
POOL["arm"]["tentacle"] = TentacleArm()

# syllables used to name a hybrid: prefix from the first donor, suffix from the last
SYLLABLES = {
    tech_bro.SPECIES: (tech_bro.PREFIX, tech_bro.SUFFIX),
    swamp_monster.SPECIES: (swamp_monster.PREFIX, swamp_monster.SUFFIX),
    sasquatch.SPECIES: (sasquatch.PREFIX, sasquatch.SUFFIX),
    banana_dude.SPECIES: (banana_dude.PREFIX, banana_dude.SUFFIX),
    "tentacle": ("Tenta", "pus"),
    "blob": ("Blob", "blob"),
    "brain": ("Brain", "brain"),
    "eyestalk": ("Eye", "eyes"),
    "claw": ("Pinch", "claw"),
}


@dataclass
class Specimen:
    name: str
    number: int
    plan: BodyPlan
    recipe: dict[str, str]
    mutations: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return f"kronenberg_{self.number:03d}_{self.name.lower()}"

    def render(self, pose: Pose) -> Canvas:
        return self.plan.render(pose)


def hybrid_name(recipe: dict[str, str]) -> str:
    donors = []
    for kind in ("head", "torso", "legs", "front_arm", "back_arm"):
        if recipe[kind] not in donors:
            donors.append(recipe[kind])
    if len(donors) == 1:
        return SYLLABLES[donors[0]][0]
    return SYLLABLES[donors[0]][0] + SYLLABLES[donors[-1]][1]


# -- decorations (painted after the layers are composited) ------------------

def stitch_seam(upper: str, lower: str):
    """Sew stitches across the visible seam where layer `upper` sits on layer `lower`."""
    def deco(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
        up, lo = layers[upper], layers[lower]
        n = 0
        for x in range(out.w):
            ys = [y for y in range(out.h) if up.opaque(x, y)]
            if not ys:
                continue
            y = ys[-1]                                       # upper layer's bottom outline
            visible = (
                out.get(x, y) == OUTLINE
                and out.get(x, y - 1) not in (None, OUTLINE) and out.get(x, y - 1) == up.get(x, y - 1)
                and out.get(x, y + 1) not in (None, OUTLINE) and out.get(x, y + 1) == lo.get(x, y + 1)
            )
            if not visible:
                continue
            if n % 2 == 0:
                out.set(x, y - 1, M["stitch"])
                out.set(x, y + 1, M["stitch"])
            n += 1
    return deco


def extra_eyes(count: int, seed: int, torso):
    """Grow `count` eyeballs on the torso. Spots are picked once on a neutral pose
    (relative to the hip) so the eyes ride along with the body between frames."""
    ref = Canvas(SIZE, SIZE)
    hip0 = GROUND - 10
    torso.draw(ref, CX, hip0, Pose("idle", 0, 4))
    ref.outline(OUTLINE)
    spots = [
        (x, y - hip0) for y in range(SIZE - 3) for x in range(SIZE - 3)
        if all(ref.get(x + i, y + j) not in (None, OUTLINE) for i in range(-1, 4) for j in range(-1, 4))
    ]
    rng = random.Random(seed)
    chosen: list[tuple[int, int]] = []
    for x, y in rng.sample(spots, len(spots)):
        if all(abs(x - ox) > 3 or abs(y - oy) > 3 for ox, oy in chosen):
            chosen.append((x, y))
        if len(chosen) == count:
            break

    def deco(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
        torso_layer = layers["torso"]
        for x, dy in chosen:
            y = info["hip"] + dy
            if all(out.get(x + i, y + j) == torso_layer.get(x + i, y + j) for i in range(3) for j in range(3)):
                eyeball(out, x, y, pose)
    return deco


def neck_bolts(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """Frankenstein bolt sticking out the back of the neck."""
    nx, ny = info["anchors"].neck
    y = ny - 2
    span = layers["head"].row_span(y) or (nx - 3, nx)
    out.stamp(span[0] - 2, y - 1, ["KKKK", "hMMK", "KKKK"], {"K": INK, "M": M["metal"], "h": M["metal_hi"]})


def irradiate(color: str, amount: float = 0.4):
    return lambda layer, pose: layer.tint(color, amount)


# -- the splicer -------------------------------------------------------------

def splice(
    legs: str,
    torso: str,
    head: str,
    front_arm: str,
    back_arm: str | None = None,
    *,
    number: int = 0,
    name: str | None = None,
    extra_head: str | None = None,
    eyes: int = 0,
    bolts: bool = False,
    irradiated: dict[str, str] | None = None,   # layer -> tint name
    stitches: bool = True,
) -> Specimen:
    back_arm = back_arm or front_arm
    recipe = dict(legs=legs, torso=torso, head=head, front_arm=front_arm, back_arm=back_arm)
    plan = BodyPlan(
        legs=POOL["legs"][legs],
        torso=POOL["torso"][torso],
        head=POOL["head"][head],
        front_arm=POOL["arm"][front_arm],
        back_arm=POOL["arm"][back_arm],
        seamless=False,
    )
    mutations = []
    if extra_head:
        plan.extra_heads.append((POOL["head"][extra_head], -8, 1))
        recipe["extra_head"] = extra_head
        mutations.append(f"second head ({extra_head})")
    if stitches:
        plan.decorations += [stitch_seam("torso", "legs"), stitch_seam("head", "torso")]
    if eyes:
        plan.decorations.append(extra_eyes(eyes, seed=number, torso=plan.torso))
        mutations.append(f"{eyes} extra eye{'s' if eyes > 1 else ''}")
    if bolts:
        plan.decorations.append(neck_bolts)
        mutations.append("neck bolts")
    for layer, tint in (irradiated or {}).items():
        plan.layer_fx[layer] = irradiate(TINTS[tint])
        mutations.append(f"{tint} {layer.replace('_', ' ')}")
    return Specimen(name or hybrid_name(recipe), number, plan, recipe, mutations)


def random_specimen(seed: int) -> Specimen:
    """Roll a random hybrid. Guaranteed to draw from at least three donors."""
    rng = random.Random(seed)
    while True:
        r = {k: rng.choice(sorted(POOL[k])) for k in ("legs", "torso", "head")}
        r["front_arm"] = rng.choice(sorted(POOL["arm"]))
        r["back_arm"] = r["front_arm"] if rng.random() < 0.5 else rng.choice(sorted(POOL["arm"]))
        if len(set(r.values())) >= 3:
            break
    tint_layer = rng.choice(["legs", "torso", "front_arm", "head"])
    return splice(
        **r,
        number=seed,
        extra_head=rng.choice(sorted(POOL["head"])) if rng.random() < 0.2 else None,
        eyes=rng.choice([0, 0, 1, 2, 3]),
        bolts=rng.random() < 0.4,
        irradiated={tint_layer: rng.choice(sorted(TINTS))} if rng.random() < 0.35 else None,
    )


# Hand-picked specimens from the lab notebook.
CURATED = [
    splice(number=1, legs="sasquatch", torso="sasquatch", head="tech_bro",
           front_arm="tech_bro", back_arm="sasquatch", bolts=True),
    splice(number=2, legs="tentacle", torso="swamp_monster", head="banana_dude",
           front_arm="claw", back_arm="swamp_monster"),
    splice(number=3, legs="swamp_monster", torso="tech_bro", head="brain",
           front_arm="tentacle", back_arm="tech_bro", irradiated={"legs": "radioactive"}),
    splice(number=4, legs="banana_dude", torso="blob", head="eyestalk",
           front_arm="banana_dude", eyes=2),
    splice(number=5, legs="sasquatch", torso="blob", head="swamp_monster",
           front_arm="claw", back_arm="swamp_monster", extra_head="sasquatch",
           irradiated={"extra_heads": "ultraviolet"}),
    splice(number=6, legs="tech_bro", torso="banana_dude", head="sasquatch",
           front_arm="banana_dude", back_arm="sasquatch", bolts=True),
    splice(number=7, name="Twofacebro", legs="tentacle", torso="blob", head="tech_bro",
           front_arm="tech_bro", back_arm="tentacle", extra_head="banana_dude"),
]
