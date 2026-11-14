"""The 'genetics': roll a visitor's DNA profile (a few control-group species with
percentages that add up to 100), then splice a Kronenberg out of it, with the
body parts shared out by percentage, and roll mutations on top.

    profile = roll_profile(rng)               # [Strand("banana_dude", 40), ...]
    profile = survey_profile(answers, rng)    # the same, steered by the behavioral survey
    you = build_you(profile, rng)             # You: base specimen, mutation steps, final specimen

Pure Python, no pygame, so it can run on a worker thread while the screen
plays the analysis.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from sprites.palette import TINTS
from sprites.species.kronenberg import POOL, Specimen, fits, splice

STEP = 5                                   # percentages are multiples of this
DONORS_PER_VISITOR = (3, 4, 4, 4, 5)       # how many species show up in one spit
SLOTS = ("legs", "torso", "head", "front_arm", "back_arm")
PART_NAMES = {"legs": "LEGS", "torso": "TORSO", "head": "HEAD", "front_arm": "ARM", "back_arm": "OTHER ARM"}

# species -> (what the report calls it, a one-line diagnosis)
NICK: dict[str, tuple[str, str]] = {
    "tech_bro": ("TECH BRO", "EXPLAINS YOUR PODCAST."),
    "swamp_monster": ("SWAMP", "EXPLAINS THE SMELL."),
    "sasquatch": ("SASQUATCH", "HARD TO PHOTOGRAPH."),
    "banana_dude": ("BANANA", "A-PEELING. POTASSIUM RICH."),
    "fly_man": ("FLY", "YOU LIKE GARBAGE. IT'S OK."),
    "alien": ("ALIEN", "NOT FROM AROUND HERE."),
    "zombie": ("ZOMBIE", "MORNINGS ARE HARD."),
    "mermaid": ("MERMAID", "BAD AT STAIRS."),
    "medusa": ("MEDUSA", "PEOPLE FREEZE UP AROUND YOU."),
    "giant_slug": ("SLUG", "YOU LEAVE A TRAIL."),
    "centaur": ("CENTAUR", "HALF OF YOU IS A HORSE."),
    "wyvern": ("DRAGON", "CHRONIC HEARTBURN."),
    "katana_chick": ("NINJA", "SILENT. DEADLY. SHARP."),
    "pageant_queen": ("PAGEANT QUEEN", "WANTS WORLD PEACE."),
    "succubus": ("DEMON", "SMALL BUT VERY BAD."),
    "fairy": ("FAIRY", "SPARKLY. STINGS A BIT."),
    "cowboy": ("COWBOY", "YEEHAW DETECTED."),
    "spider": ("SPIDER", "EIGHT LEGS OF ANXIETY."),
    "stoner": ("STONER", "WILL GET TO IT. EVENTUALLY."),
    "crawling_baby": ("BABY", "STILL TEETHING."),
    "technoviking": ("VIKING", "THE BASS IS IN YOUR BLOOD."),
    "jazz_sax": ("JAZZ", "PLAYS THE NOTES YOU DON'T HEAR."),
    "ghost": ("GHOST", "SEE-THROUGH. SAYS BOO."),
    "headless_horseman": ("HORSEMAN", "LOSES THEIR HEAD EASILY."),
    "detective": ("DETECTIVE", "ON THE CASE. ALWAYS."),
    "puppet": ("PUPPET", "SOMEONE IS PULLING STRINGS."),
    "dominatrix": ("DOM", "YOU WILL ADDRESS THEM AS MADAM."),
    "gimp": ("GIMP", "MMPH."),
    "stephen_hawking": ("GENIUS", "BIG BRAIN. HUGE BRAIN."),
}

# The behavioral analysis survey, asked partway through the analysis. The first
# two answers each pull a species into the visitor (with the reason the report
# gives); the colour shades the finished creature.
# (question, [(answer, species, why), ...])
SURVEY_SPECIES: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("FAVORITE ORIFICE?", [
        ("VAGINA", "dominatrix", "FAVORITE ORIFICE: VAGINA. YOU'RE IN CHARGE NOW."),
        ("BUTTHOLE", "gimp", "FAVORITE ORIFICE: BUTTHOLE. MMPH. NO JUDGMENT."),
        ("DICK HOLE", "succubus", "FAVORITE ORIFICE: DICK HOLE. SMALL BUT VERY BAD."),
        ("BUTTON HOLE", "puppet", "FAVORITE ORIFICE: BUTTON HOLE. ALL SEWN UP."),
        ("BELLYBUTTON", "crawling_baby", "FAVORITE ORIFICE: BELLYBUTTON. STILL ATTACHED."),
        ("NOSE (HEHE)", "detective", "FAVORITE ORIFICE: NOSE. A NOSE FOR CLUES."),
        ("I MAKE MY OWN", "cowboy", "MAKES THEIR OWN HOLES. BLAZES A TRAIL."),
    ]),
    ("FAVORITE STRING?", [
        ("YARN", "spider", "FAVORITE STRING: YARN. SPINS A GOOD ONE."),
        ("PASTA", "stoner", "FAVORITE STRING: PASTA. HAS THE MUNCHIES."),
        ("DNA (DUH)", "fly_man", "FAVORITE STRING: DNA. A SCIENTIST. SORT OF."),
        ("THEORY", "stephen_hawking", "FAVORITE STRING: THEORY. BIG BRAIN. HUGE BRAIN."),
    ]),
]
COLORS: list[tuple[str, str]] = [("RED", "#e83b3b"), ("BLUE", "#4a7dff"), ("GREEN", "#39d353"),
                                 ("YELLOW", "#ffe14d"), ("PURPLE", "#a24bff"), ("PINK", "#ff6fb5")]
SURVEY: list[tuple[str, list[str]]] = [(q, [a for a, _, _ in opts]) for q, opts in SURVEY_SPECIES] + \
    [("FAVORITE COLOR?", [name for name, _ in COLORS])]
DONORS = 4                                 # species in a visitor who took the survey

TINT_WORDS = {"radioactive": "RADIOACTIVE", "cryo": "FROZEN", "ultraviolet": "ULTRAVIOLET"}


@dataclass
class Strand:
    species: str
    pct: int
    why: str = ""                          # what in the survey put it there, if anything

    @property
    def nick(self) -> str:
        return NICK[self.species][0]

    @property
    def diagnosis(self) -> str:
        return self.why or NICK[self.species][1]


@dataclass
class Mutation:
    label: str                             # what the screen announces: "NECK BOLTS"
    kwargs: dict                           # what it adds to splice()


@dataclass
class You:
    profile: list[Strand]
    recipe: dict[str, str]                 # slot -> species
    mutations: list[Mutation]
    steps: list[Specimen] = field(default_factory=list)   # base, then one more mutation each

    @property
    def final(self) -> Specimen:
        return self.steps[-1]

    @property
    def name(self) -> str:
        return self.final.name.upper()

    def donor_of(self, slot: str) -> str:
        return NICK[self.recipe[slot]][0]


def sentence(profile: list[Strand]) -> str:
    """'YOU ARE 40% DOM, 30% BANANA AND 30% GENIUS.'"""
    parts = [f"{s.pct}% {s.nick}" for s in profile]
    body = ", ".join(parts[:-1]) + " AND " + parts[-1] if len(parts) > 1 else parts[0]
    return f"YOU ARE {body}."


def roll_profile(rng: random.Random) -> list[Strand]:
    """A handful of species and their share of you, biggest first. Every share is
    a multiple of STEP, at least STEP, and they add up to 100."""
    n = rng.choice(DONORS_PER_VISITOR)
    species = rng.sample(sorted(NICK), n)
    units = 100 // STEP
    shares = [1] * n                                    # everyone gets at least one unit
    weights = [rng.random() ** 2 + 0.05 for _ in range(n)]   # squared: usually one big share
    for _ in range(units - n):
        shares[rng.choices(range(n), weights)[0]] += 1
    profile = [Strand(sp, sh * STEP) for sp, sh in zip(species, shares)]
    profile.sort(key=lambda s: -s.pct)
    return profile


def survey_profile(answers: list[int], rng: random.Random) -> list[Strand]:
    """DONORS species: the ones the orifice and string answers pick, with the
    biggest shares, then randoms to fill. `answers` are option indices into SURVEY."""
    picked: list[Strand] = []
    for (_, opts), a in zip(SURVEY_SPECIES, answers):
        _, species, why = opts[a]
        if all(p.species != species for p in picked):
            picked.append(Strand(species, 0, why))
    others = [sp for sp in sorted(NICK) if all(p.species != sp for p in picked)]
    picked += [Strand(sp, 0) for sp in rng.sample(others, DONORS - len(picked))]
    units = 100 // STEP
    shares = [1] * DONORS
    weights = [3.0 if p.why else rng.random() ** 2 + 0.3 for p in picked]   # the survey ones run deepest
    for _ in range(units - DONORS):
        shares[rng.choices(range(DONORS), weights)[0]] += 1
    for p, sh in zip(picked, shares):
        p.pct = sh * STEP
    picked.sort(key=lambda s: -s.pct)
    return picked


def survey_color(answers: list[int]) -> str:
    """The favourite colour's hex, from the last answer."""
    return COLORS[answers[2]][1]


def _deal_slots(profile: list[Strand], rng: random.Random) -> dict[str, str]:
    """Share the body parts out: everyone gets one if there are enough to go round,
    the rest go to the biggest shares (by weighted draw)."""
    owners = [s.species for s in profile[:len(SLOTS)]]
    while len(owners) < len(SLOTS):
        owners.append(rng.choices([s.species for s in profile], [s.pct for s in profile])[0])
    rng.shuffle(owners)
    return dict(zip(SLOTS, owners))


def _roll_mutations(profile: list[Strand], recipe: dict[str, str], rng: random.Random) -> list[Mutation]:
    """At least one mutation (it's a lab, not a spa), sometimes three."""
    pool: list[Mutation] = []
    eyes = rng.choice((1, 2, 3))
    pool.append(Mutation(f"{eyes} EXTRA EYE{'S' if eyes > 1 else ''}", {"eyes": eyes}))
    pool.append(Mutation("NECK BOLTS", {"bolts": True}))
    second = rng.choice([s.species for s in profile if s.species != recipe["head"]] or ["brain"])
    pool.append(Mutation(f"SECOND HEAD ({NICK.get(second, ('BRAIN',))[0]})", {"extra_head": second}))
    layer = rng.choice(("legs", "torso", "front_arm", "head"))
    tint = rng.choice(sorted(TINTS))
    pool.append(Mutation(f"{TINT_WORDS.get(tint, tint.upper())} {PART_NAMES[layer]}", {"irradiated": {layer: tint}}))
    n = rng.choices((1, 2, 3), (4, 4, 2))[0]
    return rng.sample(pool, n)


def build_you(profile: list[Strand], rng: random.Random, number: int = 0, tries: int = 40) -> You:
    """Splice the visitor. Re-deal the parts until the creature fits the frame
    (tall legs under a tall torso under a tall head can poke out the top)."""
    for attempt in range(tries):
        recipe = _deal_slots(profile, rng)
        muts = _roll_mutations(profile, recipe, rng)
        kwargs: dict = {}
        steps = [splice(**recipe, number=number)]
        for m in muts:
            kwargs.update(m.kwargs)
            steps.append(splice(**recipe, number=number, **kwargs))
        if fits(steps[-1]):
            return You(profile, recipe, muts, steps)
    # couldn't make the full set fit: drop the mutations that make it tall
    muts = [m for m in muts if "extra_head" not in m.kwargs]
    kwargs = {}
    steps = [splice(**recipe, number=number)]
    for m in muts:
        kwargs.update(m.kwargs)
        steps.append(splice(**recipe, number=number, **kwargs))
    return You(profile, recipe, muts, steps)


assert all(sp in POOL["legs"] for sp in NICK), "every NICK species must donate a full body"
