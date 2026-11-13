"""Primordial Soup: catch the lab's escaped critters and throw them in the pot.

    python -m minigames.primordial_soup [--fullscreen] [--scale 4] [--demo]

Controls (keyboard, or an arcade stick / gamepad):
    ARROWS              run around the kitchen          stick
    SPACE / Z / ENTER   pounce on a critter / throw it   button 0
    ESC / Q             quit

Get NEED critters into the soup before the clock runs out. Throw one toward the
pot from close enough and it'll land in; the chef has a good arm. Tools fly off
the wall rack at you now and then (the kitchen is haunted, obviously): a hit
knocks you silly and the critter you're carrying gets away. Grease is slippery.

Make it in time and the soup comes alive, eats the chef, puts on his hat and
trashes the kitchen. Run out of time and the diners come in for their soup and
stab the chef to death with their cutlery.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass, field

import pygame

from sprites.canvas import Canvas, hex_to_rgba
from sprites.palette import LAB_BG, LAB_DIM, LAB_TEXT
from sprites.rig import ANIMATIONS, GROUND, SIZE, Pose
from sprites.viewer import H, W, text_surface, to_surface

from ..shell import Input, run
from ..stork_bomber import art as stork_art
from . import art, people, tutorial

NEED = 4                        # critters in the soup to bring it to life
TIME_LIMIT = 45.0               # seconds before the diners lose patience

# the room (floor coordinates are where feet touch)
X_MIN, X_MAX = art.WALL_L + 8, art.WALL_R - 8
Y_MIN, Y_MAX = art.FLOOR_TOP + 6, art.WALL_B - 2
POT_X, POT_Y = 160, 122         # pot's feet
POT_FOOT = (POT_X, POT_Y - 5, 29, 9)            # floor ellipse it blocks: cx, cy, rx, ry
POT_RIM_Z = art.POT_FEET - art.POT_RIM[1] - 2   # height of the rim above the floor
BENCHES = [(30, 100, 56, 18, 1), (234, 100, 56, 18, 2)]
# (x, bottom row, width, depth, seed): each blocks the floor rect x..x+w, bottom-depth..bottom
TESLA_FOOT = (art.TESLA[0], art.TESLA[1] - 4, 13, 5)
TANK_FOOT = (art.TANK[0], art.TANK[1] - 4, 16, 5)
ROUND = [POT_FOOT, TESLA_FOOT, TANK_FOOT]       # floor ellipses nothing walks through

CHEF_MAX = 84                   # px/s, a bit less while carrying
CARRY_MAX = 72
CHEF_GRIP = 30.0                # how fast he gets to the stick's speed (1/s): high = tight, arcade-y
GREASE_GRIP = 1.6               # ...and on grease, not very
DEPTH = 0.8                     # up/down moves a bit slower than left/right (it's a 3/4 view)
FEET_R = 6                      # half-width of feet for collisions

LUNGE_T = 0.34                  # pounce duration
LUNGE_SPEED = 150
GRAB_REACH = 17                 # px in front of the chef the hands reach
GRAB_DEPTH = 9
THROW_T = 0.25
THROW_SPEED = 115
THROW_UP = 150                  # px/s up at release
GRAVITY = 420
HAND_Z = 18                     # height of the hands
AIM_RANGE = 70                  # throw toward the pot from this close and it goes in
STUN_T = 0.9

CRIT_SPEED = (44, 60)
CRIT_PANIC = 62                 # flee once the chef is this close
CRIT_STUN = 0.8
CRITTERS_PER_ROUND = 7
# each kind's personality: speed multiplier, hops along, taunts you from a distance
PERSONALITY = {
    "eyeball": (1.0, False), "legfish": (1.3, False), "amoeba": (0.75, False), "brainbug": (1.05, False),
    "jello": (0.9, True), "egg": (0.85, True), "hotdog": (1.1, False), "trilobite": (0.95, False),
    "wiener": (1.15, True), "vulva": (1.0, False),
}
TAUNT_RANGE = 95                # taunts only when the chef is at least this far away
TAUNT_EVERY = (3.0, 7.0)
TAUNT_T = 0.9

TESLA_EVERY = (3.0, 5.0)        # s between zaps
TESLA_WARN = 0.7                # it crackles this long before firing
TESLA_REACH = 62                # px from the coil it'll arc to
ZAP_T = 0.22                    # how long a bolt stays on screen
ZAP_STUN = 0.75

STAFF = ("sous", "scientist", "intern")
STAFF_SPEED = {"sous": 34, "scientist": 26, "intern": 92}
STAFF_R = 8                     # half-width they take up on the floor
BUMP_SPEED = 120                # px/s the chef gets shoved
BUMP_T = 0.3

TOOL_FIRST = (6.0, 9.0)         # s before the first tool flies off the rack
TOOL_EVERY = (6.0, 10.0)
TOOL_SHAKE = 0.8
TOOL_FLIGHT = 0.95
TOOL_HIT_R = 12
TOOL_REHANG = 5.0

# the soup comes alive
RUMBLE, RISE, ROAR, LEAP, DIGEST = 1.4, 1.0, 1.0, 0.6, 2.4
RAMPAGE_BANNER = 4.0            # s into the rampage before the win banner
HOP_T = 0.7
# the diners come in
DINERS = 6
DINER_SPEED = 120
DINER_EVERY = 0.22
STAB_FOR = 3.2                  # s of stabbing before the chef goes down

SOUP_LINES = ["SPLOOSH!", "PLOP!", "IN THE SOUP!", "SIMMER DOWN!"]
GRAB_LINES = ["GOTCHA!", "COME HERE!", "AHA!"]
MISS_LINES = ["WHIFF!", "MISSED!", "SLIPPERY!"]
BONK_LINES = ["BONK!", "CLANG!", "OOF!"]
ESCAPE_LINES = ["IT GOT AWAY!", "NOOO!"]
STAB_LINES = ["STAB!", "SHANK!", "FORKED!", "STAB!", "SLICE!", "POKE!"]
ANGRY_LINES = ["WHERE'S OUR SOUP?!", "45 MINUTES?!", "I WANT THE MANAGER!", "ORDER UP?!"]
AFTER_LINES = ["TOO SALTY.", "ONE STAR.", "STILL HUNGRY.", "NEEDS MORE CHEF."]
EAT_LINES = ["NOM!", "GLORP!", "SLURP!"]
SQUEAL_LINES = {
    "eyeball": ["EYE OBJECT!", "I SEE WHAT YOU'RE DOING!"], "legfish": ["MY LEGS!", "I JUST GOT THESE!"],
    "amoeba": ["SACRE BLEU!", "I'LL SPLIT!"], "brainbug": ["I'M TOO SMART FOR SOUP!", "EUREKA... NO!"],
    "jello": ["THERE'S ALWAYS ROOM FOR... NO!", "WOBBLE!"], "egg": ["AAAAAA!", "I'M NOT EVEN BORN!"],
    "hotdog": ["I'M A SANDWICH!", "UNHAND ME!"], "trilobite": ["I'VE SEEN EXTINCTIONS!", "NOT COOL!"],
    "wiener": ["NOT THE BALLS!", "IT'S COLD IN HERE!", "I'M A GROWER!"],
    "vulva": ["BUY ME DINNER FIRST!", "HANDS OFF!", "WHERE'S MY STORK?!"],
}
TAUNT_LINES = ["NYAH!", "CAN'T CATCH ME!", "BLEH!", "TOO SLOW!", "OVER HERE!", "EAT A SALAD!"]
SOUP_CRIES = ["BLUB BLUB", "IT'S WARM!", "HOT HOT HOT!"]
ZAP_LINES = ["ZZZAP!", "BZZZT!", "KRZZZK!"]
BUMP_LINES = {"sous": ["WATCH IT!", "COMING THROUGH!", "BEHIND!"],
              "scientist": ["MIND THE SAMPLE!", "FASCINATING...", "CAREFUL!"],
              "intern": ["AAAAAH!", "I'M ON FIRE!", "HOT HOT HOT!", "SORRY!"]}
STAFF_LINES = {"sous": ["YES CHEF!", "HEARD!", "TABLE NINE!"],
               "scientist": ["IT NEEDS MORE VOLTAGE!", "HYPOTHESIS: SOUP!", "MWAHAHA!"],
               "intern": ["AAAAAH!", "IS THIS NORMAL?!", "WHERE'S THE EXTINGUISHER?!"]}


@dataclass
class Popup:
    text: pygame.Surface
    x: float
    y: float
    t: float = 0.0
    life: float = 1.2


@dataclass
class Critter:
    kind: str
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    z: float = 0.0
    vz: float = 0.0
    state: str = "roam"         # roam | held | air | stun | soup | eaten
    t: float = 0.0
    goal: tuple[float, float] = (0.0, 0.0)
    speed: float = 50.0
    facing: int = 1
    aim: bool = False           # thrown at the pot
    hop: bool = False           # bounces along instead of scuttling
    taunt: float = 0.0          # counts down while it's taunting you
    taunt_in: float = 5.0


@dataclass
class Staff:
    """Another cook or scientist going about their business. They're in the way."""
    who: str
    x: float
    y: float
    goal: tuple[float, float] = (0.0, 0.0)
    state: str = "walk"         # walk | pause | hurt | flee | eaten
    t: float = 0.0
    pause: float = 0.0
    facing: int = 1
    vx: float = 0.0
    vy: float = 0.0
    talk_in: float = 4.0


@dataclass
class Tool:
    kind: str
    spot: int                   # index into art.HANG_SPOTS
    state: str = "shake"        # shake | fly | floor
    t: float = 0.0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    spin: int = 0


@dataclass
class Bit:
    """Flying debris: soup, sauce, plates, a hat. Floor position + height."""
    img: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    t: float = 0.0
    life: float = 2.0


@dataclass
class Diner:
    look: int
    x: float
    y: float
    slot: tuple[float, float]
    t: float = 0.0
    state: str = "run"          # run | stab | wait | idle
    wait: float = 0.0
    facing: int = -1


@dataclass
class Slime:
    x: float
    y: float
    z: float = 0.0
    w: int = 50
    h: int = 56
    state: str = "pot"          # pot | leap | engulf | hop | land
    t: float = 0.0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    hat: bool = False
    eaten: list[str] = field(default_factory=list)
    facing: int = 1
    snacks: list[str] = field(default_factory=list)   # staff it swallowed


def both(c: Canvas) -> dict[int, pygame.Surface]:
    right = to_surface(c)
    return {1: right, -1: pygame.transform.flip(right, True, False)}


def big_text(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


class Art:
    """Every sprite pre-rendered to surfaces (both facings where it matters)."""

    def __init__(self) -> None:
        self.kitchen = to_surface(art.kitchen(W, H))
        self.doors = [to_surface(art.door(o)) for o in (0.0, 0.5, 1.0)]
        self.benches = [to_surface(art.bench(w, d, seed)) for _, _, w, d, seed in BENCHES]
        self.pot_back = [[to_surface(art.pot_back(f, lv)) for f in range(4)] for lv in range(4)]
        self.pot_front = [to_surface(art.pot_front(f)) for f in range(3)]
        self.pot_shake = [to_surface(art.pot_front(f, s)) for f, s in ((0, -1), (1, 1))]
        self.crit = {k: [both(art.critter(k, f)) for f in range(4)] for k in art.CRITTERS}
        self.tools = {k: to_surface(art.utensil(k)) for k in art.UTENSILS}
        self.stars = to_surface(art.stars())
        self.grease = [to_surface(art.grease(w, h)) for w, h in ((22, 7), (16, 6))]
        self.splat = [to_surface(art.goo_splat(w)) for w in (6, 10, 14)]
        self.bits = {
            "soup": to_surface(art.drop(art.GOO, art.GOO_HI)),
            "broth": to_surface(art.drop("#8a7a54", "#c8b07a")),
            "sauce": to_surface(art.drop("#d8302a", "#ff6a4a")),
            "plate": to_surface(art.plate()),
            "shard0": to_surface(art.shard(0)),
            "shard1": to_surface(art.shard(1)),
            "hat": to_surface(self._hat()),
        }
        self.steam = [to_surface(art.steam(f)) for f in range(3)]
        self.dna = [to_surface(stork_art.dna(f)) for f in range(stork_art.DNA_FRAMES)]
        self.chef = {name: [both(f) for f in frames] for name, frames in people.chef_frames().items()}
        self.chef_raw = people.chef_frames()["hurt"]
        self.carry_pts = {}
        for name, base in (("carry_idle", "idle"), ("carry_run", "run")):
            self.carry_pts[name] = [people.carry_point(Pose(base, i, len(ANIMATIONS[base]), **kw))
                                    for i, kw in enumerate(ANIMATIONS[base])]
        self.diners = [{a: [both(f) for f in fr] for a, fr in people.diner_frames(look).items()}
                       for look in people.DINER_LOOKS]
        staff = {who: people.staff_frames(who) for who in STAFF}
        self.staff_raw = {who: f["hurt"][0] for who, f in staff.items()}
        self.staff = {who: {a: [both(x) for x in fr] for a, fr in f.items()} for who, f in staff.items()}
        self.tesla = [to_surface(art.tesla_coil(q)) for q in (0.0, 0.5, 1.0)]
        self.tank = [to_surface(art.specimen_tank(f)) for f in range(4)]
        self._slime: dict[tuple, dict[int, pygame.Surface]] = {}

    @staticmethod
    def _hat() -> Canvas:
        c = Canvas(14, 10)
        c.stamp(0, 1, people.HEAD[:8], {"W": people.CHEF["white"], "w": people.CHEF["white_sh"],
                                        "b": people.CHEF["white_dk"]})
        c.outline(art.OUTLINE)
        return c

    def slime(self, w: int, h: int, frame: int, mouth: str, hat: bool, inside: tuple = ()) -> dict:
        """inside: (kind, amount) pairs; 'chef' or a critter kind, amount quantized."""
        key = (w, h, frame, mouth, hat, inside)
        if key not in self._slime:
            things = []
            for i, (kind, amount) in enumerate(inside):
                if kind == "chef":
                    things.append((self.chef_raw[frame % 2], 0, -6 - frame % 2, amount))
                elif kind.startswith("staff:"):
                    things.append((self.staff_raw[kind[6:]], (i * 17) % 24 - 12, -8, amount))
                else:
                    things.append((art.critter(kind, 2 + frame % 2), (i * 13) % 30 - 15, -h // 2 + (i * 7) % 12, 0.2))
            self._slime[key] = both(art.slime(w, h, frame, mouth, hat, things))
        return self._slime[key]


_ART: Art | None = None


class PrimordialSoup:
    title = "PRIMORDIAL SOUP"

    def __init__(self, seed: int | None = None, show_title: bool = True) -> None:
        global _ART
        _ART = _ART or Art()
        self.art = _ART
        self.rng = random.Random(seed)
        self.result: str | None = None
        self.done = False
        self.phase = "title" if show_title else "play"
        self.phase_t = 0.0
        self.howto = tutorial.make(self.art, NEED, TIME_LIMIT)
        self.time = 0.0
        self.clock = TIME_LIMIT

        self.x, self.y = 110.0, 150.0
        self.vx = self.vy = 0.0
        self.facing = 1
        self.anim_t = 0.0
        self.lunge = 0.0
        self.throw = 0.0
        self.stun = 0.0
        self.held: Critter | None = None
        self.dead_t = -1.0                             # counts up once the diners finish him
        self.whoa = False

        self.critters: list[Critter] = []
        for kind in self.rng.sample(art.CRITTERS, CRITTERS_PER_ROUND):
            x, y = self._free_spot()
            speed, hop = PERSONALITY.get(kind, (1.0, False))
            c = Critter(kind, x, y, speed=self.rng.uniform(*CRIT_SPEED) * speed, facing=self.rng.choice((-1, 1)),
                        hop=hop, taunt_in=self.rng.uniform(*TAUNT_EVERY))
            c.goal = self._free_spot()
            self.critters.append(c)
        self.staff: list[Staff] = []
        for who in STAFF:
            x, y = self._free_spot(12)
            st = Staff(who, x, y, talk_in=self.rng.uniform(3, 9))
            st.goal = self._free_spot(12)
            self.staff.append(st)
        self.bump = 0.0
        self.tesla_in = self.rng.uniform(*TESLA_EVERY)
        self.bolts: list[list] = []                   # [points, t]
        self.flash = 0.0
        self.ding_in = self.rng.uniform(8, 14)
        self.vents: list[list[float]] = []           # [x, y, t]
        self.in_soup = 0
        self.slicks = []
        for i in range(2):
            gx, gy = self._free_spot(margin=16)
            self.slicks.append((gx, gy, i))

        self.tools: list[Tool] = []
        self.hanging = [True] * len(art.HANG_SPOTS)
        self.rehang = [0.0] * len(art.HANG_SPOTS)
        self.tool_in = self.rng.uniform(*TOOL_FIRST)

        self.bits: list[Bit] = []
        self.splats: list[list[float]] = []          # [x, y, size, t]
        self.popups: list[Popup] = []
        self.dna: list[list[float]] = []             # [x, y, t]
        self.shake = 0.0
        self.slime: Slime | None = None
        self.diners: list[Diner] = []
        self.diner_in = 0.0
        self.diners_left = DINERS
        self.door = 0.0
        self.stab_t = -1.0

    # -- helpers ----------------------------------------------------------------------
    def _blocked(self, x: float, y: float, r: float = FEET_R) -> bool:
        if not (X_MIN <= x <= X_MAX and Y_MIN <= y <= Y_MAX):
            return True
        for cx, cy, rx, ry in ROUND:
            if ((x - cx) / (rx + r)) ** 2 + ((y - cy) / (ry + 3)) ** 2 <= 1:
                return True
        for bx, bottom, bw, depth, _ in BENCHES:
            if bx - r <= x <= bx + bw + r and bottom - depth - 2 <= y <= bottom + 2:
                return True
        return False

    def _free_spot(self, margin: float = 8) -> tuple[float, float]:
        for _ in range(200):
            x, y = self.rng.uniform(X_MIN + 8, X_MAX - 8), self.rng.uniform(Y_MIN + 4, Y_MAX - 4)
            if not self._blocked(x, y, margin) and math.hypot(x - self.x, y - self.y) > 40:
                return x, y
        return X_MIN + 20, Y_MAX - 10

    def _move(self, x: float, y: float, dx: float, dy: float, r: float = FEET_R) -> tuple[float, float, bool, bool]:
        """Slide along whatever's in the way. Returns new x, y and whether each axis was blocked."""
        bx = self._blocked(x + dx, y, r)
        if not bx:
            x += dx
        by = self._blocked(x, y + dy, r)
        if not by:
            y += dy
        return x, y, bx, by

    def _popup(self, text: str, x: float, y: float, color: str = LAB_TEXT, life: float = 1.2) -> None:
        img = text_surface(text, color)
        x = max(img.get_width() / 2 + 2, min(W - img.get_width() / 2 - 2, x))
        self.popups.append(Popup(img, x, y, life=life))

    def _on_grease(self, x: float, y: float) -> bool:
        for gx, gy, i in self.slicks:
            iw, ih = self.art.grease[i].get_size()
            if abs(x - gx) < iw / 2 and abs(y - gy) < ih / 2 + 1:
                return True
        return False

    @property
    def hands(self) -> tuple[float, float]:
        """Floor position just in front of the chef, where the hands reach."""
        return self.x + self.facing * 10, self.y

    def _splash(self, x: float, y: float, z: float, n: int, img: str, speed: float = 70) -> None:
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            s = self.rng.uniform(0.3, 1.0) * speed
            self.bits.append(Bit(img, x, y, z, math.cos(a) * s, math.sin(a) * s * 0.5,
                                 self.rng.uniform(60, 160), life=3.0))

    # -- update ------------------------------------------------------------------------
    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.phase_t += dt
        self.anim_t += dt
        self.shake = max(0.0, self.shake - dt)

        self.flash = max(0.0, self.flash - dt)
        self._update_staff(dt)
        self._update_lab(dt)
        if self.phase == "title":
            self._update_critters(dt)
            self.howto.update(dt, inp)
            if self.howto.done:
                self.phase, self.phase_t = "play", 0.0
            self._update_fx(dt)
            return
        if self.phase == "play":
            self.clock = max(0.0, self.clock - dt)
            self._update_chef(dt, inp)
            self._update_tools(dt)
            self._update_tesla(dt)
            if self.in_soup >= NEED and not any(c.state == "air" for c in self.critters):
                self._start_alive()
            elif self.clock <= 0:
                self._start_mob()
        elif self.phase == "alive":
            self._update_alive(dt)
        elif self.phase == "mob":
            self._update_mob(dt)
        elif self.phase in ("won", "lost"):
            if self.slime:
                self._update_slime(dt)
            if self.diners:
                self._update_diners(dt)
            if inp.action and self.phase_t > 1.2:
                self.done = True
        self._update_critters(dt)
        self._update_fx(dt)

    def _update_chef(self, dt: float, inp: Input) -> None:
        self.lunge = max(0.0, self.lunge - dt)
        self.throw = max(0.0, self.throw - dt)
        if self.stun > 0:
            self.stun -= dt
            inp = Input()
        slick = self._on_grease(self.x, self.y)
        if slick and not self.whoa and math.hypot(self.vx, self.vy) > 40:
            self.whoa = True
            self._popup("WHOA!", self.x, self.y - 50, "#f0d27a", life=0.8)
        elif not slick:
            self.whoa = False
        self.bump = max(0.0, self.bump - dt)
        if self.lunge <= 0 and self.bump <= 0:
            ix, iy = inp.x, inp.y * DEPTH
            n = math.hypot(inp.x, inp.y)
            if n > 1:                                                  # diagonals aren't faster
                ix, iy = ix / n, iy / n
            top = CARRY_MAX if self.held else CHEF_MAX
            k = min(1.0, (GREASE_GRIP if slick else CHEF_GRIP) * dt)
            self.vx += (ix * top - self.vx) * k
            self.vy += (iy * top - self.vy) * k
        elif self.lunge > 0:
            self.vx -= self.vx * 4 * dt
            self.vy -= self.vy * 4 * dt
        else:                                                          # shoved: skid to a stop
            self.vx -= self.vx * 6 * dt
            self.vy -= self.vy * 6 * dt
        self.x, self.y, bx, by = self._move(self.x, self.y, self.vx * dt, self.vy * dt)
        if bx:
            self.vx = 0.0
        if by:
            self.vy = 0.0
        if inp.x and self.lunge <= 0:
            self.facing = inp.x

        if inp.action and self.lunge <= 0 and self.throw <= 0:
            if self.held:
                self._throw(inp)
            else:
                self.lunge = LUNGE_T
                self.vx = self.facing * LUNGE_SPEED
                self.vy = inp.y * LUNGE_SPEED * 0.4
        if self.lunge > 0 and not self.held and LUNGE_T - self.lunge > 0.05:
            hx, hy = self.hands
            for c in self.critters:
                if c.state in ("roam", "stun") and abs(c.x - hx) < GRAB_REACH * 0.7 and abs(c.y - hy) < GRAB_DEPTH:
                    c.state, c.t = "held", 0.0
                    self.held = c
                    self.lunge = min(self.lunge, 0.08)
                    self._popup(self.rng.choice(GRAB_LINES), self.x, self.y - 52)
                    self._popup(self.rng.choice(SQUEAL_LINES.get(c.kind, ["EEK!"])), self.x, self.y - 62, "#5ff3ff")
                    break
            else:
                if self.lunge <= dt:
                    self._popup(self.rng.choice(MISS_LINES), self.x, self.y - 52, LAB_DIM, life=0.7)

    def _throw(self, inp: Input) -> None:
        c = self.held
        self.held = None
        self.throw = THROW_T
        hx, hy = self.hands
        c.x, c.y, c.z, c.state, c.t = hx, hy, HAND_Z, "air", 0.0
        dx, dy = POT_X - hx, (POT_Y - 3) - hy
        facing_pot = dx * self.facing > -6
        if facing_pot and math.hypot(dx, dy * 1.5) <= AIM_RANGE:        # the chef's got a good arm
            t = max(0.35, min(0.8, math.hypot(dx, dy) / THROW_SPEED))
            c.vx, c.vy = dx / t, dy / t
            c.vz = (POT_RIM_Z + 4 - HAND_Z + 0.5 * GRAVITY * t * t) / t
            c.aim = True
        else:
            c.vx = self.facing * THROW_SPEED + self.vx * 0.4
            c.vy = inp.y * 60 + self.vy * 0.4
            c.vz = THROW_UP
            c.aim = False
        c.facing = self.facing

    def _drop_held(self) -> None:
        c = self.held
        if not c:
            return
        self.held = None
        c.x, c.y = self.hands
        c.z, c.vz, c.state, c.t = HAND_Z, 90, "air", 0.0
        c.vx, c.vy, c.aim = -self.facing * 40, self.rng.uniform(-20, 20), False
        self._popup(self.rng.choice(ESCAPE_LINES), self.x, self.y - 60, "#5ff3ff")

    def _update_critters(self, dt: float) -> None:
        for c in self.critters:
            c.t += dt
            if c.state == "held":
                continue
            if c.state == "air":
                c.vz -= GRAVITY * dt
                c.z += c.vz * dt
                nx, ny = c.x + c.vx * dt, c.y + c.vy * dt
                cx, cy, rx, ry = POT_FOOT
                over_pot = ((nx - cx) / rx) ** 2 + ((ny - cy) / ry) ** 2 <= 1.15
                if over_pot and c.vz < 0 and c.z <= POT_RIM_Z + 4:
                    self._into_soup(c)
                    continue
                if over_pot and c.z < POT_RIM_Z and not c.aim:   # a wild throw hit the side of the pot
                    c.vx, c.vy = -c.vx * 0.4, -c.vy * 0.4
                    nx, ny = c.x, c.y
                    self._popup("CLANG!", c.x, c.y - 30, LAB_DIM, life=0.6)
                if not c.aim and c.z < 12 and not over_pot and self._blocked(nx, ny, 3):   # only low throws hit things
                    c.vx, c.vy = -c.vx * 0.3, -c.vy * 0.3
                else:
                    c.x, c.y = nx, ny
                if c.z <= 0:
                    c.z, c.state, c.t = 0.0, "stun", 0.0
                    c.vx = c.vy = 0.0
                    if self._blocked(c.x, c.y, 3):
                        c.x, c.y = self._free_spot()
                continue
            if c.state == "stun":
                if c.t >= CRIT_STUN:
                    c.state, c.t = "roam", 0.0
                continue
            if c.state != "roam":
                continue
            # roam: wander, but bolt from the chef when he gets close
            dx, dy = c.x - self.x, c.y - self.y
            d = math.hypot(dx, dy) or 1
            if c.hop:                                                  # boing, boing
                c.z = abs(math.sin(c.t * 7)) * 5 if math.hypot(c.vx, c.vy) > 10 else 0.0
            if self.phase == "play":
                c.taunt_in -= dt
                if c.taunt > 0:                                        # standing there, wiggling at you
                    c.taunt -= dt
                    c.facing = -1 if dx > 0 else 1
                    c.vx = c.vy = 0.0
                    if d >= CRIT_PANIC:
                        continue
                    c.taunt = 0.0
                elif c.taunt_in <= 0 and d > TAUNT_RANGE:
                    c.taunt, c.taunt_in = TAUNT_T, self.rng.uniform(*TAUNT_EVERY)
                    self._popup(self.rng.choice(TAUNT_LINES), c.x, c.y - 26, "#ff9ab8", life=0.9)
                    continue
            panic = self.phase in ("play", "alive", "mob") and d < CRIT_PANIC and self.held is not c
            if self.slime and self.slime.state in ("hop", "land", "leap"):
                sdx, sdy = c.x - self.slime.x, c.y - self.slime.y
                sd = math.hypot(sdx, sdy) or 1
                if sd < 80:
                    dx, dy, d, panic = sdx, sdy, sd, True
            if panic:
                tx, ty = dx / d, dy / d
                if c.x < X_MIN + 20 or c.x > X_MAX - 20:              # cornered: juke along the wall
                    tx, ty = tx * 0.3, (1 if c.y < (Y_MIN + Y_MAX) / 2 else -1)
                if c.y < Y_MIN + 12 or c.y > Y_MAX - 12:
                    tx, ty = (1 if c.x < W / 2 else -1), ty * 0.3
                speed = c.speed * 1.4
            else:
                gx, gy = c.goal
                tx, ty = gx - c.x, gy - c.y
                gd = math.hypot(tx, ty)
                if gd < 6 or c.t > 4:
                    c.goal, c.t = self._free_spot(), 0.0
                    continue
                tx, ty = tx / gd, ty / gd
                speed = c.speed * 0.55
            k = min(1.0, 6 * dt)
            c.vx += (tx * speed - c.vx) * k
            c.vy += (ty * speed * DEPTH - c.vy) * k
            c.x, c.y, bx, by = self._move(c.x, c.y, c.vx * dt, c.vy * dt, 4)
            if bx and by:                                             # stuck: pick a new way
                c.goal = self._free_spot()
                c.vx, c.vy = -c.vx, -c.vy
            if abs(c.vx) > 5:
                c.facing = 1 if c.vx > 0 else -1

    def _into_soup(self, c: Critter) -> None:
        c.state, c.t = "soup", 0.0
        self.in_soup += 1
        line = "NOTHING BUT SOUP!" if not c.aim else self.rng.choice(SOUP_LINES)
        self._popup(line, POT_X, POT_Y - 70, art.GOO_HI)
        self._popup(self.rng.choice(SOUP_CRIES), POT_X + self.rng.uniform(-20, 20), POT_Y - 60, "#5ff3ff", life=1.0)
        self._splash(POT_X, POT_Y - 4, POT_RIM_Z, 10, "broth" if self.in_soup < NEED else "soup")
        self.dna.append([POT_X + self.rng.uniform(-10, 10), POT_Y - POT_RIM_Z, 0.0])

    def _update_staff(self, dt: float) -> None:
        s = self.slime
        for st in self.staff:
            st.t += dt
            if st.state == "eaten":
                continue
            if st.state == "hurt":
                if st.t > 0.7:
                    st.state, st.t = "walk", 0.0
                continue
            speed = STAFF_SPEED[st.who]
            if s and s.state not in ("pot",) and self.phase in ("alive", "won"):   # RUN
                dx, dy = st.x - s.x, st.y - s.y
                d = math.hypot(dx, dy) or 1
                if d < 90:
                    st.state = "flee"
                    st.goal = (st.x + dx / d * 40, st.y + dy / d * 40)
                    speed = max(speed, 80)
            elif self.phase in ("mob", "lost"):
                st.state = "pause"                                     # stop and stare
                st.facing = 1 if self.x > st.x else -1
                continue
            if st.state == "pause":
                st.pause -= dt
                if st.pause <= 0:
                    st.state, st.goal = "walk", self._free_spot(12)
                continue
            gx, gy = st.goal
            dx, dy = gx - st.x, gy - st.y
            d = math.hypot(dx, dy)
            if d < 4:
                if st.who == "intern":                                 # never stops screaming
                    st.goal = self._free_spot(12)
                else:
                    st.state, st.pause, st.t = "pause", self.rng.uniform(0.8, 2.2), 0.0
                continue
            nvx, nvy = dx / d * speed, dy / d * speed * DEPTH
            st.x, st.y, bx, by = self._move(st.x, st.y, nvx * dt, nvy * dt, STAFF_R - 2)
            st.vx, st.vy = nvx, nvy
            if bx and by:
                st.goal = self._free_spot(12)
            if abs(dx) > 1:
                st.facing = 1 if dx > 0 else -1
            st.talk_in -= dt
            if st.talk_in <= 0 and self.phase in ("play", "title"):
                st.talk_in = self.rng.uniform(5, 11)
                self._popup(self.rng.choice(STAFF_LINES[st.who]), st.x, st.y - 50, LAB_DIM, life=1.1)
            # they don't walk through the chef: whoever's in the way gets shoved
            if self.phase == "play" and self.stun <= 0:
                ddx, ddy = self.x - st.x, (self.y - st.y) * 1.6
                dd = math.hypot(ddx, ddy)
                if dd < STAFF_R + FEET_R and self.bump <= 0:
                    nx, ny = (ddx / dd, ddy / dd) if dd > 0.1 else (st.facing, 0.0)
                    self.vx, self.vy = nx * BUMP_SPEED, ny * BUMP_SPEED * 0.6
                    self.bump = BUMP_T
                    self._popup(self.rng.choice(BUMP_LINES[st.who]), st.x, st.y - 50, "#f0d27a", life=0.8)
                    if st.who == "intern" and self.held:               # he's on fire, it's chaos
                        self._drop_held()
                    st.goal = self._free_spot(12)
        # and the chef can't walk through them either
        for st in self.staff:
            if st.state == "eaten":
                continue
            ddx, ddy = self.x - st.x, (self.y - st.y) * 1.6
            dd = math.hypot(ddx, ddy)
            if 0.1 < dd < STAFF_R + FEET_R - 1:
                push = (STAFF_R + FEET_R - 1 - dd)
                nx, ny = self._move(self.x, self.y, ddx / dd * push, ddy / dd * push / 1.6)[:2]
                self.x, self.y = nx, ny

    def _update_tesla(self, dt: float) -> None:
        self.tesla_in -= dt
        if self.tesla_in > 0:
            return
        self.tesla_in = self.rng.uniform(*TESLA_EVERY)
        tx, ty = art.TESLA
        top = (tx - art.TESLA_W // 2 + art.TESLA_TOP[0], ty - art.TESLA_H + 2 + art.TESLA_TOP[1])
        # who's closest gets it: the chef, a critter, a coworker, or just the floor
        targets = [(math.hypot(self.x - tx, (self.y - ty) * 1.4), "chef", None)]
        targets += [(math.hypot(c.x - tx, (c.y - ty) * 1.4), "crit", c) for c in self.critters if c.state in ("roam", "stun")]
        targets += [(math.hypot(st.x - tx, (st.y - ty) * 1.4), "staff", st) for st in self.staff if st.state != "eaten"]
        d, kind, obj = min(targets, key=lambda t: t[0])
        if d > TESLA_REACH:
            a = self.rng.uniform(-math.pi, 0)
            end = (tx + math.cos(a) * 40, ty + 6 + math.sin(a) * -12)
            kind = "floor"
        elif kind == "chef":
            end = (self.x, self.y - 22)
            self.stun = ZAP_STUN
            self.vx = self.vy = 0.0
            self._drop_held()
            self._popup(self.rng.choice(ZAP_LINES), self.x, self.y - 60, "#dff8ff")
        elif kind == "crit":
            end = (obj.x, obj.y - 6)
            obj.state, obj.t = "stun", -0.8                            # extra crispy: stunned longer
            self._popup("FRIED!", obj.x, obj.y - 24, "#dff8ff", life=0.8)
        else:
            end = (obj.x, obj.y - 22)
            obj.state, obj.t = "hurt", 0.0
            self._popup("YOWCH!", obj.x, obj.y - 52, "#dff8ff", life=0.8)
        self._bolt(top, end)
        self.flash = 0.08
        self.shake = max(self.shake, 0.1)

    def _bolt(self, a: tuple[float, float], b: tuple[float, float]) -> None:
        pts = [a]
        n = 7
        for k in range(1, n):
            t = k / n
            pts.append((a[0] + (b[0] - a[0]) * t + self.rng.uniform(-6, 6),
                        a[1] + (b[1] - a[1]) * t + self.rng.uniform(-4, 4)))
        pts.append(b)
        self.bolts.append([pts, 0.0])

    @property
    def tesla_charge(self) -> float:
        if self.phase != "play":
            return 0.0
        return max(0.0, 1 - self.tesla_in / TESLA_WARN)

    def _update_lab(self, dt: float) -> None:
        for b in self.bolts:
            b[1] += dt
        self.bolts = [b for b in self.bolts if b[1] < ZAP_T]
        if self.tesla_charge > 0 and self.rng.random() < 12 * dt:      # crackling before it fires
            tx, ty = art.TESLA
            top = (tx - art.TESLA_W // 2 + art.TESLA_TOP[0], ty - art.TESLA_H + 2 + art.TESLA_TOP[1])
            a = self.rng.uniform(0, math.tau)
            self._bolt(top, (top[0] + math.cos(a) * 12, top[1] + math.sin(a) * 6))
        self.ding_in -= dt
        if self.ding_in <= 0:
            self.ding_in = self.rng.uniform(9, 16)
            wx, wy, ww, _ = art.MICRO_WIN
            self._popup("DING!", wx + ww / 2, wy - 8, "#ffd93a", life=0.9)
        if self.rng.random() < 0.7 * dt:
            vx, vy = self.rng.choice(art.VENTS)
            self.vents.append([vx, vy, 0.0])
        for v in self.vents:
            v[2] += dt
        self.vents = [v for v in self.vents if v[2] < 0.9]

    def _update_tools(self, dt: float) -> None:
        for i, t in enumerate(self.rehang):
            if not self.hanging[i] and t > 0:
                self.rehang[i] -= dt
                if self.rehang[i] <= 0:
                    self.hanging[i] = True
        self.tool_in -= dt
        if self.tool_in <= 0 and any(self.hanging):
            self.tool_in = self.rng.uniform(*TOOL_EVERY)
            spot = self.rng.choice([i for i, h in enumerate(self.hanging) if h])
            self.hanging[spot] = False
            self.tools.append(Tool(art.UTENSILS[spot], spot))
        live = []
        for tool in self.tools:
            tool.t += dt
            if tool.state == "shake" and tool.t >= TOOL_SHAKE:
                sx, sy = art.HANG_SPOTS[tool.spot]
                tool.state, tool.t = "fly", 0.0
                tool.x0, tool.y0 = sx + art.UT_SIZE / 2, art.FLOOR_TOP + 2
                lead = 0.4                                            # aims a little ahead of you
                tool.x1 = max(X_MIN, min(X_MAX, self.x + self.vx * lead))
                tool.y1 = max(Y_MIN, min(Y_MAX, self.y + self.vy * lead))
                tool.spin = self.rng.choice((-1, 1))
                self._popup("LOOK OUT!", sx + 8, 30, "#ff5f5f", life=0.8)
            elif tool.state == "fly" and tool.t >= TOOL_FLIGHT:
                tool.state, tool.t = "floor", 0.0
                if math.hypot(self.x - tool.x1, (self.y - tool.y1) * 1.5) < TOOL_HIT_R and self.stun <= 0:
                    self.stun = STUN_T
                    self.vx = self.vy = 0.0
                    self._popup(self.rng.choice(BONK_LINES), self.x, self.y - 56, "#fff27a")
                    self._drop_held()
                    self.shake = 0.15
                self.rehang[tool.spot] = TOOL_REHANG
            if not (tool.state == "floor" and tool.t > 1.6):
                live.append(tool)
        self.tools = live

    # -- the soup comes alive -------------------------------------------------------------
    def _ground_tools(self) -> None:
        """An ending is starting: tools in the air drop where they are, rattling ones settle back."""
        for tool in self.tools:
            if tool.state == "shake":
                self.hanging[tool.spot] = True
        self.tools = [t for t in self.tools if t.state == "floor"]

    def _start_alive(self) -> None:
        self.phase, self.phase_t, self.result = "alive", 0.0, "win"
        self.slime = Slime(POT_X, POT_Y - 2, state="pot")
        self._ground_tools()
        self._popup("IT'S... ALIVE?", POT_X, POT_Y - 74, art.GOO_HI, life=1.6)
        if self.held:
            self._drop_held()

    def _update_alive(self, dt: float) -> None:
        s = self.slime
        e = self.phase_t
        self.vx = self.vy = 0.0
        self.facing = 1 if POT_X > self.x else -1
        if e < RUMBLE:
            if self.rng.random() < 6 * dt:
                self._splash(POT_X, POT_Y - 4, POT_RIM_Z, 2, "soup", 40)
        elif e - dt < RUMBLE + RISE + ROAR <= e:
            self.popups.append(Popup(big_text("IT'S ALIVE!!", art.GOO_HI), W / 2, 66, life=2.2))
            self._popup("MAMMA MIA!", self.x, self.y - 56, "#f4f4f4")
            self.shake = 0.4
        if s.state == "pot" and e >= RUMBLE + RISE + ROAR:
            s.state, s.t = "leap", 0.0
            s.x0, s.y0, s.x1, s.y1 = s.x, s.y, self.x, self.y + 1
        self._update_slime(dt)
        if s.state == "engulf" and s.t >= DIGEST and not s.hat:
            s.hat = True
            s.w, s.h = 62, 62
            self._popup("BURP!", s.x, s.y - 74, art.GOO_HI)
            s.state, s.t = "hop", 0.0
            self._next_hop()
        if s.hat and self.phase == "alive" and e >= RUMBLE + RISE + ROAR + LEAP + DIGEST + RAMPAGE_BANNER:
            self.phase, self.phase_t = "won", 0.0

    def _next_hop(self) -> None:
        s = self.slime
        prey = [(c.x, c.y) for c in self.critters if c.state in ("roam", "stun")]
        prey += [(st.x, st.y) for st in self.staff if st.state != "eaten"]
        if prey and self.rng.random() < 0.7:
            tx, ty = min(prey, key=lambda p: math.hypot(p[0] - s.x, p[1] - s.y))
        else:
            tx, ty = self._free_spot(20)
        d = math.hypot(tx - s.x, ty - s.y)
        if d > 90:                                                     # one hop at a time
            tx, ty = s.x + (tx - s.x) * 90 / d, s.y + (ty - s.y) * 90 / d
        s.x0, s.y0, s.x1, s.y1 = s.x, s.y, tx, ty
        s.facing = 1 if tx >= s.x else -1

    def _update_slime(self, dt: float) -> None:
        s = self.slime
        s.t += dt
        if s.state == "pot":
            e = self.phase_t
            rise = min(1.0, max(0.0, (e - RUMBLE) / RISE))
            s.z = -(1 - rise) * 66                                     # sinks below the rim
        elif s.state in ("leap", "hop"):
            dur = LEAP if s.state == "leap" else HOP_T
            q = min(1.0, s.t / dur)
            s.x = s.x0 + (s.x1 - s.x0) * q
            s.y = s.y0 + (s.y1 - s.y0) * q
            s.z = (34 if s.state == "hop" else 56) * 4 * q * (1 - q)
            if s.state == "leap":
                s.z += (1 - q) * 4
            if q >= 1:
                s.z = 0.0
                self.shake = 0.25
                self._splash(s.x, s.y, 4, 8, "soup", 90)
                for _ in range(3):
                    self.splats.append([s.x + self.rng.uniform(-30, 30), s.y + self.rng.uniform(-8, 8),
                                        self.rng.randrange(3), 0.0])
                if s.state == "leap":
                    s.state, s.t = "engulf", 0.0
                    self._popup("GLORP!", s.x, s.y - 70, art.GOO_HI)
                else:
                    s.state, s.t = "land", 0.0
                    self._rampage_hit()
        elif s.state == "land" and s.t >= 0.35:
            s.state, s.t = "hop", 0.0
            self._next_hop()

    def _rampage_hit(self) -> None:
        s = self.slime
        for c in self.critters:
            if c.state in ("roam", "stun") and math.hypot(c.x - s.x, (c.y - s.y) * 1.4) < 30:
                c.state = "eaten"
                s.eaten.append(c.kind)
                self._popup(self.rng.choice(EAT_LINES), s.x, s.y - 76, art.GOO_HI, life=0.8)
        for st in self.staff:
            if st.state != "eaten" and math.hypot(st.x - s.x, (st.y - s.y) * 1.4) < 32:
                st.state = "eaten"
                s.snacks.append(st.who)
                self._popup("CRUNCH!", s.x, s.y - 84, art.GOO_HI, life=0.9)
        roll = self.rng.random()
        if roll < 0.4 and any(self.hanging):                           # the rack comes down
            spot = self.rng.choice([i for i, h in enumerate(self.hanging) if h])
            self.hanging[spot] = False
            sx, sy = art.HANG_SPOTS[spot]
            self.bits.append(Bit("tool:" + art.UTENSILS[spot], sx + 8, art.FLOOR_TOP + 2, 30,
                                 self.rng.uniform(-60, 60), self.rng.uniform(20, 60), 80, life=2.4))
        elif roll < 0.8:                                              # plates off the counter
            for _ in range(2):
                self.bits.append(Bit("plate", 222 + self.rng.uniform(-6, 6), art.FLOOR_TOP + 1, 14,
                                     self.rng.uniform(-90, 90), self.rng.uniform(30, 80), 120, life=1.5))

    # -- the diners come in -------------------------------------------------------------
    def _start_mob(self) -> None:
        self.phase, self.phase_t, self.result = "mob", 0.0, "lose"
        self.popups.append(Popup(big_text("TIME'S UP!", "#ff5f5f"), W / 2, 66, life=1.8))
        self._drop_held()
        self._ground_tools()
        self.vx = self.vy = 0.0
        self.stun = 0.0
        self.diner_in = 0.6

    def _update_mob(self, dt: float) -> None:
        self.door = min(1.0, self.door + 4 * dt) if self.phase_t > 0.4 else 0.0
        self.diner_in -= dt
        if self.diner_in <= 0 and self.diners_left > 0:
            self.diner_in = DINER_EVERY
            i = DINERS - self.diners_left
            self.diners_left -= 1
            ang = math.pi * (0.15 + 0.7 * (i / max(1, DINERS - 1)))   # fan around the chef
            side = 1 if i % 2 else -1
            slot = (self.x + side * (14 + 6 * (i // 2)), self.y + math.cos(ang) * 8 * side)
            slot = (max(X_MIN, min(X_MAX, slot[0])), max(Y_MIN, min(Y_MAX, slot[1])))
            self.diners.append(Diner(i % len(people.DINER_LOOKS), art.DOOR_X + art.DOOR_W / 2,
                                     art.FLOOR_TOP + 2, slot))
            if i == 0:
                self._popup(self.rng.choice(ANGRY_LINES), art.DOOR_X, 30, "#ff5f5f", life=1.6)
        self._update_diners(dt)
        if self.stab_t >= 0:
            self.stab_t += dt
            if self.stab_t >= STAB_FOR and self.dead_t < 0:
                self.dead_t = 0.0
                for d in self.diners:
                    d.state = "idle"
        if self.dead_t >= 0:
            before = self.dead_t
            self.dead_t += dt
            if before < 1.0 <= self.dead_t:
                d = self.rng.choice(self.diners)
                self._popup(self.rng.choice(AFTER_LINES), d.x, d.y - 50)
            if self.dead_t >= 1.8:
                self.phase, self.phase_t = "lost", 0.0

    def _update_diners(self, dt: float) -> None:
        for d in self.diners:
            d.t += dt
            if d.state == "run":
                dx, dy = d.slot[0] - d.x, d.slot[1] - d.y
                dist = math.hypot(dx, dy)
                if dist < 3:
                    d.state, d.t, d.wait = "stab", 0.0, self.rng.uniform(0, 0.3)
                    if self.stab_t < 0:
                        self.stab_t = 0.0
                else:
                    step = min(dist, DINER_SPEED * dt)
                    d.x, d.y, bx, by = self._move(d.x, d.y, dx / dist * step, dy / dist * step, 3)
                    if bx and by:                                       # benches in the way: just squeeze past
                        d.x += dx / dist * step
                        d.y += dy / dist * step
                    d.facing = 1 if dx > 0 else -1
            elif d.state == "stab":
                d.facing = 1 if self.x > d.x else -1
                if d.wait > 0:
                    d.wait -= dt
                    d.t = 0.0
                    continue
                before, after = (d.t - dt) * 12, d.t * 12
                if before < 2 <= after:                                 # the fork lands
                    hx = d.x + d.facing * 12
                    self._splash(hx, d.y, 22, 2, "sauce", 50)
                    self._popup(self.rng.choice(STAB_LINES), hx + self.rng.uniform(-6, 6),
                                d.y - 40 - self.rng.uniform(0, 14), "#ff6a4a", life=0.6)
                    self.shake = max(self.shake, 0.06)
                if after >= 4:
                    d.t, d.wait = 0.0, self.rng.uniform(0.05, 0.35)

    def _update_fx(self, dt: float) -> None:
        live = []
        for b in self.bits:
            b.t += dt
            b.vz -= GRAVITY * dt
            b.z += b.vz * dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            if b.z <= 0:
                if b.img in ("soup", "broth") and self.rng.random() < 0.5:
                    self.splats.append([b.x, b.y, 0, 0.0])
                if b.img == "plate":
                    for k in range(3):
                        self.bits.append(Bit(f"shard{k % 2}", b.x, b.y, 1, self.rng.uniform(-50, 50),
                                             self.rng.uniform(-20, 20), 70, life=0.8))
                    self._popup("CRASH!", b.x, b.y - 20, "#f4f4f4", life=0.5)
                    continue
                if b.img.startswith("tool:"):
                    b.z, b.vz, b.vx, b.vy = 0.0, 0.0, 0.0, 0.0
                else:
                    continue
            if b.t < b.life and -20 < b.x < W + 20:
                live.append(b)
        self.bits = live[-200:]
        for sp in self.splats:
            sp[3] += dt
        self.splats = [sp for sp in self.splats if sp[3] < 6.0][-60:]
        for p in self.popups:
            p.t += dt
            p.y -= 14 * dt
        self.popups = [p for p in self.popups if p.t < p.life]
        for d in self.dna:
            d[2] += dt
        self.dna = [d for d in self.dna if d[2] < 1.6]

    # -- draw -----------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        a = self.art
        ox = round(self.rng.uniform(-2, 2)) if self.shake > 0 else 0
        oy = round(self.rng.uniform(-1, 1)) if self.shake > 0 else 0
        frame = screen if not (ox or oy) else pygame.Surface((W, H))
        frame.blit(a.kitchen, (0, 0))
        self._draw_wall(frame)

        for gx, gy, i in self.slicks:
            img = a.grease[i]
            frame.blit(img, (round(gx) - img.get_width() // 2, round(gy) - img.get_height() // 2))
        for x, y, size, t in self.splats:
            if t < 5.4 or int(t * 10) % 2:
                img = a.splat[int(size)]
                frame.blit(img, (round(x) - img.get_width() // 2, round(y) - 3))

        # everything standing on the floor, back to front
        items: list[tuple[float, int, object]] = []
        for i, (bx, bottom, bw, depth, _) in enumerate(BENCHES):
            items.append((bottom, 0, ("bench", i)))
        items.append((POT_Y, 1, ("pot", None)))
        items.append((art.TESLA[1], 1, ("tesla", None)))
        items.append((art.TANK[1], 1, ("tank", None)))
        for st in self.staff:
            if st.state != "eaten":
                items.append((st.y, 3, ("staff", st)))
        for c in self.critters:
            if c.state not in ("held", "soup", "eaten"):
                items.append((c.y, 2, ("crit", c)))
        items.append((self.y, 3, ("chef", None)))
        for d in self.diners:
            items.append((d.y, 3, ("diner", d)))
        for tool in self.tools:
            if tool.state != "shake":
                items.append((self._tool_pos(tool)[1], 4, ("tool", tool)))
        for b in self.bits:
            items.append((b.y, 4, ("bit", b)))
        s = self.slime
        if s and s.state != "pot":
            items.append((s.y + 0.5, 3, ("slime", s)))
        for y, _, (kind, obj) in sorted(items, key=lambda it: (it[0], it[1])):
            getattr(self, "_draw_" + kind)(frame, obj)

        for d in self.dna:                                                 # helices rising out of the pot
            x, y, t = d
            img = a.dna[int(self.time * 6) % stork_art.DNA_FRAMES]
            if t < 1.3 or int(t * 20) % 2:
                frame.blit(img, (round(x + 4 * math.sin(t * 5)) - stork_art.DNA_W // 2, round(y - t * 40) - 24))
        for pts, t in self.bolts:                                          # lightning
            ipts = [(round(x), round(y)) for x, y in pts]
            pygame.draw.lines(frame, hex_to_rgba("#5ff3ff"), False, [(x + 1, y) for x, y in ipts], 1)
            pygame.draw.lines(frame, hex_to_rgba("#ffffff"), False, ipts, 1)
        for p in self.popups:
            if p.t < p.life - 0.3 or int(p.t * 20) % 2:
                frame.blit(p.text, (round(p.x) - p.text.get_width() // 2, round(p.y)))
        if self.flash > 0:
            glare = pygame.Surface((W, H), pygame.SRCALPHA)
            glare.fill((220, 248, 255, 90))
            frame.blit(glare, (0, 0))
        if frame is not screen:
            screen.fill(hex_to_rgba(LAB_BG))
            screen.blit(frame, (ox, oy))
        self._draw_hud(screen)

    def _draw_wall(self, screen: pygame.Surface) -> None:
        a = self.art
        for fx, fy in art.STOVE_FLAMES:                                    # back burners
            for k in range(-4, 5, 2):
                h = 2 + (int(self.time * 12) + k) % 3
                pygame.draw.line(screen, hex_to_rgba(art.FLAME[1]), (fx + k, fy - 1), (fx + k, fy - 1 - h))
                pygame.draw.line(screen, hex_to_rgba(art.FLAME[0]), (fx + k, fy - 1), (fx + k, fy - h + 1))
        for i, (lx, ly) in enumerate(art.LEDS):                            # the control panel blinks away
            h = (i * 7919 + int(self.time * (2 + i % 3))) % 5
            if h < 3:
                pygame.draw.rect(screen, hex_to_rgba(("#39ff14", "#e83b3b", "#ffd93a")[h]), (lx, ly, 2, 1))
        wx, wy, ww, wh = art.MICRO_WIN                                     # something rotating in the microwave
        pygame.draw.rect(screen, (60, 50, 20), (wx, wy, ww, wh))
        pygame.draw.rect(screen, (110, 90, 30), (wx + 2, wy + wh - 3, ww - 4, 2))
        n = int(self.time / 6) % (len(art.CRITTERS) + 1)
        item = self.art.tools["dildo"] if n == len(art.CRITTERS) else self.art.crit[art.CRITTERS[n]][2][1]
        spin = pygame.transform.rotate(item, (self.time * 90) % 360)
        clip = screen.get_clip()
        screen.set_clip(pygame.Rect(wx, wy, ww, wh))
        screen.blit(spin, (wx + ww // 2 - spin.get_width() // 2, wy + wh // 2 - spin.get_height() // 2))
        screen.set_clip(clip)
        for vx, vy, t in self.vents:                                       # steam puffs from the pipes
            st = self.art.steam[min(2, int(t * 3.4))]
            screen.blit(st, (vx - 5, round(vy - 10 - t * 10)))
        for i, (sx, sy) in enumerate(art.HANG_SPOTS):
            if self.hanging[i]:
                screen.blit(a.tools[art.UTENSILS[i]], (sx, sy))
        for tool in self.tools:
            if tool.state == "shake":
                sx, sy = art.HANG_SPOTS[tool.spot]
                jig = (-1, 1)[int(tool.t * 24) % 2]
                screen.blit(a.tools[tool.kind], (sx + jig, sy))
        cx, cy, r = art.CLOCK                                              # the clock counts down
        frac = self.clock / TIME_LIMIT
        ang = -math.pi / 2 + (1 - frac) * math.tau
        col = "#e83b3b" if self.clock < 10 and int(self.time * 4) % 2 else "#1e1828"
        pygame.draw.line(screen, hex_to_rgba(col), (cx, cy), (cx + round(math.cos(ang) * (r - 2)),
                                                              cy + round(math.sin(ang) * (r - 2))))
        door = 0 if self.door < 0.25 else 1 if self.door < 0.75 else 2
        if self.phase in ("play", "title") and self.clock < 8 and int(self.time * 3) % 2:
            door = 1                                                    # the diners are getting restless
        screen.blit(a.doors[door], (art.DOOR_X, art.DOOR_Y))

    def _draw_tesla(self, screen: pygame.Surface, _: object) -> None:
        q = self.tesla_charge
        img = self.art.tesla[0 if q <= 0 else 1 if q < 0.6 else 2]
        tx, ty = art.TESLA
        screen.blit(img, (tx - art.TESLA_W // 2, ty - art.TESLA_H + 2))

    def _draw_tank(self, screen: pygame.Surface, _: object) -> None:
        img = self.art.tank[int(self.time * 3) % 4]
        tx, ty = art.TANK
        screen.blit(img, (tx - art.TANK_W // 2, ty - art.TANK_H + 2))

    def _draw_staff(self, screen: pygame.Surface, st: Staff) -> None:
        fr = self.art.staff[st.who]
        if st.state == "hurt":
            img = fr["hurt"][int(st.t * 10) % 2][st.facing]
        elif st.state == "pause":
            anim = "pour" if st.who == "scientist" else "idle"
            img = fr[anim][int(st.t * 4) % 4][st.facing]
        else:
            fps = 14 if st.who == "intern" or st.state == "flee" else 8
            img = fr["walk"][int(st.t * fps) % 4][st.facing]
        self._shadow(screen, st.x, st.y + 1, 14)
        screen.blit(img, (round(st.x) - SIZE // 2, round(st.y) - GROUND))

    def _draw_bench(self, screen: pygame.Surface, i: int) -> None:
        bx, bottom = BENCHES[i][0], BENCHES[i][1]
        img = self.art.benches[i]
        screen.blit(img, (bx, bottom - img.get_height() + 1))

    def _draw_pot(self, screen: pygame.Surface, _: object) -> None:
        a = self.art
        px, py = POT_X - art.POT_RIM[0], POT_Y - art.POT_FEET
        level = min(3, math.ceil(self.in_soup * 3 / NEED)) if not (self.slime and self.slime.state != "pot") else 0
        f = int(self.time * (6 + 4 * level)) % 4
        screen.blit(a.pot_back[level][f], (px, py))
        s = self.slime
        if s and s.state == "pot":                                         # rising out of the pot
            img = a.slime(s.w, s.h, int(self.time * 6) % 4, "open" if self.phase_t > RUMBLE + RISE else "closed",
                          False)[1]
            clip = screen.get_clip()
            screen.set_clip(pygame.Rect(0, 0, W, py + 40))
            screen.blit(img, (POT_X - art.SLIME_CX, round(py + art.POT_RIM[1] + 4 - art.SLIME_BASE - s.z)))
            screen.set_clip(clip)
        rumbling = self.phase == "alive" and self.phase_t < RUMBLE + RISE
        body = a.pot_shake[int(self.time * 20) % 2] if rumbling else a.pot_front[int(self.time * 8) % 3]
        screen.blit(body, (px, py))
        if level and int(self.time * 2) % 2 == 0:
            st = a.steam[int(self.time * 3) % 3]
            screen.blit(st, (POT_X - 12 + 8 * math.sin(self.time), py - 4))

    def _shadow(self, screen: pygame.Surface, x: float, y: float, w: int) -> None:
        pygame.draw.ellipse(screen, (16, 10, 30), (round(x) - w // 2, round(y) - 1, w, 3))

    def _draw_crit(self, screen: pygame.Surface, c: Critter) -> None:
        self._shadow(screen, c.x, c.y + 1, 10)
        if c.state == "air":
            f = 2 + int(c.t * 12) % 2
        elif c.state == "stun":
            f = 0
        elif c.taunt > 0:                                                  # wiggling, mouth open
            f = 2 + int(c.t * 12) % 2
        else:
            moving = math.hypot(c.vx, c.vy) > 8
            f = int(c.t * 10) % 2 if moving else 0
        img = self.art.crit[c.kind][f][c.facing]
        screen.blit(img, (round(c.x) - art.CRIT_W // 2, round(c.y - c.z) - art.CRIT_FEET))
        if c.state == "stun":
            a = self.time * 8
            for k in (0, math.pi):
                screen.blit(self.art.stars, (round(c.x + 7 * math.cos(a + k)) - 3, round(c.y - 18 + 2 * math.sin(a + k))))

    def _chef_frame(self) -> tuple[str, int]:
        if self.dead_t >= 0:
            return "death", min(5, int(self.dead_t * 8))
        if self.phase == "mob" or (self.phase == "lost"):
            return ("hurt", int(self.time * 10) % 2) if self.stab_t >= 0 else ("cower", int(self.time * 6) % 2)
        if self.phase == "alive" and self.phase_t > RUMBLE + RISE:
            return "cower", int(self.time * 6) % 2
        if self.stun > 0:
            return "hurt", int(self.time * 10) % 2
        moving = math.hypot(self.vx, self.vy) > 12
        if self.held:
            return ("carry_run", int(self.anim_t * 12) % 4) if moving else ("carry_idle", int(self.anim_t * 4) % 4)
        if self.lunge > 0:
            return "attack", min(3, int((LUNGE_T - self.lunge) / LUNGE_T * 4))
        if self.throw > 0:
            return "attack", 1 + min(2, int((THROW_T - self.throw) / THROW_T * 3))
        return ("run", int(self.anim_t * 12) % 4) if moving else ("idle", int(self.anim_t * 4) % 4)

    def _draw_chef(self, screen: pygame.Surface, _: object) -> None:
        s = self.slime
        if s and (s.state == "engulf" or s.hat):                         # inside the slime now
            return
        if s and s.state == "leap" and s.t > LEAP * 0.85:
            return
        name, f = self._chef_frame()
        if name != "death":
            self._shadow(screen, self.x, self.y + 1, 16)
        img = self.art.chef[name][f][self.facing]
        screen.blit(img, (round(self.x) - SIZE // 2, round(self.y) - GROUND))
        if self.held:
            px, py = self.art.carry_pts[name][f]
            if self.facing < 0:
                px = SIZE - 1 - px
            c = self.held
            cimg = self.art.crit[c.kind][2 + int(self.time * 10) % 2][self.facing]
            screen.blit(cimg, (round(self.x) - SIZE // 2 + px - art.CRIT_W // 2,
                               round(self.y) - GROUND + py - art.CRIT_H // 2 - 1))
        if self.stun > 0:
            a = self.time * 7
            for k in (0, 2.1, 4.2):
                screen.blit(self.art.stars, (round(self.x + 9 * math.cos(a + k)) - 3,
                                             round(self.y - 46 + 2 * math.sin(a + k))))

    def _draw_diner(self, screen: pygame.Surface, d: Diner) -> None:
        frames = self.art.diners[d.look]
        if d.state == "run":
            img = frames["run"][int(d.t * 12) % 4][d.facing]
        elif d.state == "stab":
            img = frames["attack"][min(3, int(d.t * 12))][d.facing]
        else:
            img = frames["idle"][int(d.t * 4) % 4][d.facing]
        self._shadow(screen, d.x, d.y + 1, 14)
        screen.blit(img, (round(d.x) - SIZE // 2, round(d.y) - GROUND))

    def _tool_pos(self, tool: Tool) -> tuple[float, float, float]:
        if tool.state == "floor":
            return tool.x1, tool.y1, 0.0
        q = min(1.0, tool.t / TOOL_FLIGHT)
        x = tool.x0 + (tool.x1 - tool.x0) * q
        y = tool.y0 + (tool.y1 - tool.y0) * q
        z = 60 * 4 * q * (1 - q) + (1 - q) * 30
        return x, y, z

    def _draw_tool(self, screen: pygame.Surface, tool: Tool) -> None:
        x, y, z = self._tool_pos(tool)
        if tool.state == "floor" and tool.t > 1.2 and int(tool.t * 20) % 2:
            return
        if tool.state == "fly":                                            # where it'll land
            q = tool.t / TOOL_FLIGHT
            w = 6 + round(10 * q)
            pygame.draw.ellipse(screen, (232, 59, 59) if int(self.time * 10) % 2 else (16, 10, 30),
                                (round(tool.x1) - w // 2, round(tool.y1) - 2, w, 4), 1)
            self._shadow(screen, x, y, 8)
        img = self.art.tools[tool.kind]
        turns = int(tool.t * 10) * tool.spin if tool.state == "fly" else 1
        img = pygame.transform.rotate(img, 90 * (turns % 4))
        screen.blit(img, (round(x) - img.get_width() // 2, round(y - z) - img.get_height()))

    def _draw_bit(self, screen: pygame.Surface, b: Bit) -> None:
        if b.img.startswith("tool:"):
            img = pygame.transform.rotate(self.art.tools[b.img[5:]], 90 * (int(b.t * 10) % 4) if b.z > 0 else 90)
        else:
            img = self.art.bits[b.img]
        if b.life - b.t < 0.4 and int(b.t * 20) % 2:
            return
        screen.blit(img, (round(b.x) - img.get_width() // 2, round(b.y - b.z) - img.get_height()))

    def _draw_slime(self, screen: pygame.Surface, s: Slime) -> None:
        f = int(self.time * 6) % 4
        w, h = s.w, s.h
        if s.state in ("leap", "hop"):
            w, h = round(w * 0.86), round(h * 1.12)                         # stretched in the air
            mouth = "open"
        elif s.state == "land" and s.t < 0.15:
            w, h = round(w * 1.22), round(h * 0.8)                          # squashed on landing
            mouth = "grin"
        elif s.state == "engulf":
            mouth = "chew"
        else:
            mouth = "grin"
        w, h = w // 2 * 2, h // 2 * 2
        inside = []
        if s.state == "engulf":
            inside.append(("chef", round(min(1.0, s.t / DIGEST) * 4) / 4))
        inside += [(k, 0.2) for k in s.eaten[-4:]]
        inside += [(f"staff:{who}", 0.25) for who in s.snacks[-2:]]
        img = self.art.slime(w, h, f, mouth, s.hat, tuple(inside))[s.facing]
        shadow_w = w + 8
        pygame.draw.ellipse(screen, (16, 10, 30), (round(s.x) - shadow_w // 2, round(s.y) - 3, shadow_w, 7))
        screen.blit(img, (round(s.x) - art.SLIME_CX, round(s.y - s.z) - art.SLIME_BASE))

    # -- HUD ------------------------------------------------------------------------------
    def _draw_hud(self, screen: pygame.Surface) -> None:
        if self.phase == "title":
            self.howto.draw(screen)
            return
        panel = pygame.Surface((76, 9), pygame.SRCALPHA)                    # bottom-left, over the near wall
        panel.fill((20, 15, 38, 220))
        screen.blit(panel, (2, H - 10))
        screen.blit(text_surface(f"SOUP {min(self.in_soup, NEED)}/{NEED}", art.GOO_HI if self.in_soup else LAB_TEXT),
                    (5, H - 8))
        secs = math.ceil(self.clock)
        col = "#ff5f5f" if secs <= 10 and int(self.time * 4) % 2 else LAB_DIM
        screen.blit(text_surface(f"TIME {secs:02d}", col), (44, H - 8))
        if self.phase == "won":
            self._banner(screen, "IT'S ALIVE!", ["LIFE FROM SOUP. SCIENCE!", "THE CHEF WAS AN INGREDIENT",
                                                 "PRESS BUTTON"])
        elif self.phase == "lost":
            self._banner(screen, "KITCHEN NIGHTMARE", ["THE CUSTOMER IS ALWAYS RIGHT", "PRESS BUTTON"])

    def _banner(self, screen: pygame.Surface, title: str, lines: list[str]) -> None:
        shade = pygame.Surface((W, 30 + 9 * len(lines)), pygame.SRCALPHA)
        shade.fill((20, 15, 38, 215))
        top = 58
        screen.blit(shade, (0, top))
        t = big_text(title, LAB_TEXT)
        screen.blit(t, (W // 2 - t.get_width() // 2, top + 7))
        for i, line in enumerate(lines):
            if line:
                s = text_surface(line, LAB_DIM)
                screen.blit(s, (W // 2 - s.get_width() // 2, top + 25 + i * 9))


def autopilot(game: PrimordialSoup) -> Input:
    """A decent computer player, for demos and smoke tests."""
    inp = Input()
    if game.phase != "play":
        inp.action = game.phase in ("title", "won", "lost") and game.phase_t > 1.5
        return inp
    if game.held:
        side = -1 if game.x < POT_X else 1
        tx, ty = POT_X + side * 46, POT_Y - 4
        if math.hypot(game.x - tx, game.y - ty) < 12:
            inp.x = -side                                                   # face the pot and let go
            inp.action = game.throw <= 0 and game.facing == -side
            return inp
    else:
        prey = [c for c in game.critters if c.state in ("roam", "stun")]
        if not prey:
            return inp
        c = min(prey, key=lambda c: math.hypot(c.x - game.x, c.y - game.y))
        tx, ty = c.x - math.copysign(12, c.x - game.x), c.y
        if abs(c.x - game.hands[0]) < GRAB_REACH and abs(c.y - game.y) < GRAB_DEPTH - 2 \
                and (c.x - game.x) * game.facing > 0:
            inp.action = game.lunge <= 0
    dx, dy = tx - game.x, ty - game.y
    inp.x = (dx > 3) - (dx < -3)
    inp.y = (dy > 3) - (dy < -3)
    if not game.held and not inp.x and prey:                               # close enough: turn to face it
        inp.x = 1 if c.x > game.x else -1
    if abs(game.vx) + abs(game.vy) < 5 and game.time % 1.0 < 0.3:            # wriggle free of corners
        inp.y = 1 if game.y < (Y_MIN + Y_MAX) / 2 else -1
    return inp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--demo", action="store_true", help="let the computer play")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()
    run(lambda: PrimordialSoup(seed=args.seed), "Primordial Soup", scale=args.scale, fullscreen=args.fullscreen,
        autopilot=autopilot if args.demo else None, max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
