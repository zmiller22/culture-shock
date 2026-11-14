"""Build-A-Bear: sew a toy together out of spare parts and bring it to life.

    python -m minigames.build_a_bear [--fullscreen] [--scale 4] [--demo] [--skip-title]

Controls (keyboard, or an arcade stick / gamepad):
    ARROWS              walk around the lab / move through the menu     stick
    SPACE / Z / ENTER   pick up / drop / use the slab / pull the switch  button 0
    ESC / Q             quit

Toy parts lie all over the castle lab: teddy bears, porcelain dolls, bunnies,
sock monkeys, a plush octopus. Pick one up, carry it to the slab and press the
button: a menu asks where it goes. Anything goes anywhere (a tentacle can be a
head, if you like), and putting a part where one already is knocks the old one
off. Once every slot is filled (a head, two arms, two legs), walk over to the big
knife switch on the wall and throw it. Lightning, smoke, and it's alive.

There's no way to lose yet: this is the building half. What winning and losing
mean is still to be decided.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass

import pygame

from sprites.canvas import Canvas, hex_to_rgba
from sprites.palette import LAB_BG, LAB_DIM, LAB_TEXT
from sprites.rig import ANIMATIONS, GROUND, SIZE, Pose
from sprites.viewer import H, W, text_surface, to_surface

from ..primordial_soup import art as soup_art
from ..shell import Input, run
from . import art, tutorial

SLOTS = art.SLOTS
NEED = len(SLOTS)
FLOOR_PARTS = {"head": 3, "arm": 4, "leg": 4}     # how many of each lie around the lab

# the room (floor coordinates are where feet touch)
X_MIN, X_MAX = art.WALL_L + 8, art.WALL_R - 8
Y_MIN, Y_MAX = art.FLOOR_TOP + 6, art.WALL_B - 2
SLAB_L, SLAB_R = art.SLAB_X - art.SLAB_W // 2, art.SLAB_X + art.SLAB_W // 2
SLAB_BACK = art.SLAB_FRONT - art.SLAB_DEPTH
COIL_FOOT = [(x, y - 4, 13, 5) for x, y in art.COILS]         # floor ellipses: cx, cy, rx, ry
LEVER_SPOT = (art.LEVER_PIVOT[0], Y_MIN)                      # stand here to reach the switch
LEVER_REACH = (18, 14)                                        # how close, across and in depth
SLAB_REACH = 12                                               # how close to the slab's edge to use it

DOC_MAX = 86                    # px/s
CARRY_MAX = 74
GRIP = 30.0                     # how fast he gets up to the stick's speed (1/s)
DEPTH = 0.8                     # up/down moves a bit slower than left/right (3/4 view)
FEET_R = 6
GRAB_R = 16                     # px from the hands a part can be picked up
PULL_T = 0.45                   # s to haul on the switch
FIZZLE_T = 0.9                  # s the switch stays down when the body isn't finished

# it's alive: seconds into the "zap" phase
SLAM, CHARGE, TWITCH, SIT, HOP, ROAR, BANNER = 0.25, 2.6, 3.7, 4.3, 4.9, 5.0, 6.2
HOP_DOWN = 18                   # px in front of the slab it lands

GRAB_LINES = ["GOT IT!", "SO SOFT!", "OOH, FLUFFY.", "STILL SQUEAKS!"]
PLACE_LINES = ["PERFECT!", "STITCH STITCH!", "ADORABLE!", "SNUGGLY!"]
WRONG_LINES = ["BOLD CHOICE.", "WHY NOT!", "SCIENCE!", "THE KIDS WILL LOVE IT."]
SWAP_LINES = ["OUT WITH THE OLD!", "YOINK!", "RIIIP!"]
DROP_LINES = ["OOPS.", "LATER.", "SQUEAK."]
FIZZLE_LINES = ["IT NEEDS MORE PARTS!", "NOT YET!", "IT'S NOT FINISHED!"]
ZAP_LINES = ["ZZZAP!", "BZZZT!", "KRZZZK!"]
ALIVE_LINES = ["IT'S ALIVE!", "IT'S ALIIIVE!"]
ROAR_LINES = ["HUG ME!", "MAMA?", "PLAY WITH ME!", "I LOVE YOU. FOREVER."]
NUDGE_LINES = ["BRING ME PARTS!", "IT NEEDS LIMBS!"]


@dataclass
class Popup:
    text: pygame.Surface
    x: float
    y: float
    t: float = 0.0
    life: float = 1.2


@dataclass
class Part:
    kind: str                   # head | arm | leg
    fam: str                    # zombie, ape, fish, robot, tentacle, chicken
    x: float
    y: float
    z: float = 0.0
    state: str = "floor"        # floor | held | air | placed
    t: float = 0.0
    flip: int = 0               # which way it lies on the floor
    x0: float = 0.0             # flight, when knocked off the slab
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    twitch: float = 3.0         # s to the next twitch, lying on the floor

    @property
    def name(self) -> str:
        return art.PART_NAMES[(self.kind, self.fam)]


@dataclass
class Menu:
    """Where does it go? The slots, then NEVER MIND."""
    i: int = 0
    prev_y: int = 0
    t: float = 0.0

    @property
    def choices(self) -> int:
        return NEED + 1


def big_text(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


def both(c: Canvas) -> dict[int, pygame.Surface]:
    right = to_surface(c)
    return {1: right, -1: pygame.transform.flip(right, True, False)}


def white(img: pygame.Surface) -> pygame.Surface:
    """The silhouette, lit up white (the zap)."""
    out = img.copy()
    out.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return out


class Art:
    """Every sprite pre-rendered to surfaces."""

    def __init__(self) -> None:
        self.lab = to_surface(art.lab(W, H))
        self.slab = to_surface(art.slab())
        self.straps = to_surface(art.straps())
        self.blades = [to_surface(art.blade(k / 6)) for k in range(7)]
        self.coil = [to_surface(soup_art.tesla_coil(q)) for q in (0.0, 0.5, 1.0)]
        self.doc = {name: [both(f) for f in frames] for name, frames in art.doc_frames().items()}
        self.carry_pts = {}
        for name, base in (("carry_idle", "idle"), ("carry_run", "run")):
            self.carry_pts[name] = [art.carry_point(Pose(base, i, len(ANIMATIONS[base]), **kw))
                                    for i, kw in enumerate(ANIMATIONS[base])]
        self.parts = {(k, f): [to_surface(art.lying(k, f, i)) for i in range(2)]
                      for k, fams in art.FAMILIES.items() for f in fams}
        self.spark = to_surface(art.spark())
        self.smoke = [to_surface(art.smoke(f)) for f in range(4)]
        self.star = to_surface(art.star())
        self._creature: dict[tuple, tuple[pygame.Surface, pygame.Surface, int]] = {}

    def creature(self, parts: dict[str, tuple[str, str]]) -> tuple[pygame.Surface, pygame.Surface, int]:
        """(standing, lying on its back, row its feet touch when standing)."""
        key = tuple(sorted(parts.items()))
        if key not in self._creature:
            c = art.creature(parts)
            box = c.bbox() or (0, 0, art.MW - 1, art.MH - 1)
            self._creature[key] = (to_surface(c), to_surface(art.rot90(c)), box[3])
        return self._creature[key]


_ART: Art | None = None


class BuildABear:
    title = "BUILD-A-BEAR"

    def __init__(self, seed: int | None = None, show_title: bool = True) -> None:
        global _ART
        _ART = _ART or Art()
        self.art = _ART
        self.rng = random.Random(seed)
        self.result: str | None = None
        self.done = False
        self.cutscene = False
        self.phase = "title" if show_title else "play"
        self.phase_t = 0.0
        self.time = 0.0
        self.howto = tutorial.make(self.art)

        self.x, self.y = 60.0, 140.0
        self.vx = self.vy = 0.0
        self.facing = 1
        self.anim_t = 0.0
        self.held: Part | None = None
        self.pull = 0.0                               # counts down while hauling on the switch
        self.menu: Menu | None = None
        self.built: dict[str, Part] = {}
        self.lever = 0.0                              # 0 open .. 1 slammed live
        self.lever_to = 0.0
        self.fizzle = 0.0
        self.nagged = False

        self.parts: list[Part] = []
        for kind, n in FLOOR_PARTS.items():
            fams = list(art.FAMILIES[kind])
            self.rng.shuffle(fams)
            for i in range(n):
                x, y = self._free_spot(14)
                self.parts.append(Part(kind, fams[i % len(fams)], x, y, flip=self.rng.randrange(2),
                                       twitch=self.rng.uniform(1, 6)))

        self.popups: list[Popup] = []
        self.bolts: list[list] = []                   # [points, t]
        self.sparks: list[list[float]] = []           # [x, y, t]
        self.puffs: list[list[float]] = []            # [x, y, t]
        self.flash = 0.0
        self.shake = 0.0
        self.storm_in = self.rng.uniform(2, 6)
        self.storm = 0.0                              # window lightning
        self.rise = 0.0                               # where the creature is, once it's up: 0 on the slab .. 1 on the floor

    # -- helpers ----------------------------------------------------------------------
    def _blocked(self, x: float, y: float, r: float = FEET_R) -> bool:
        if not (X_MIN <= x <= X_MAX and Y_MIN <= y <= Y_MAX):
            return True
        for cx, cy, rx, ry in COIL_FOOT:
            if ((x - cx) / (rx + r)) ** 2 + ((y - cy) / (ry + 3)) ** 2 <= 1:
                return True
        return SLAB_L - r <= x <= SLAB_R + r and SLAB_BACK - 2 <= y <= art.SLAB_FRONT + 2

    def _free_spot(self, margin: float = 8) -> tuple[float, float]:
        for _ in range(300):
            x, y = self.rng.uniform(X_MIN + 8, X_MAX - 8), self.rng.uniform(Y_MIN + 6, Y_MAX - 4)
            if self._blocked(x, y, margin) or math.hypot(x - self.x, y - self.y) < 30:
                continue
            if any(math.hypot(x - p.x, y - p.y) < 20 for p in getattr(self, "parts", [])):
                continue
            return x, y
        return X_MIN + 20, Y_MAX - 10

    def _move(self, x: float, y: float, dx: float, dy: float) -> tuple[float, float, bool, bool]:
        bx = self._blocked(x + dx, y)
        if not bx:
            x += dx
        by = self._blocked(x, y + dy)
        if not by:
            y += dy
        return x, y, bx, by

    def _popup(self, text: str, x: float, y: float, color: str = LAB_TEXT, life: float = 1.2) -> None:
        img = text_surface(text, color)
        x = max(img.get_width() / 2 + 2, min(W - img.get_width() / 2 - 2, x))
        self.popups.append(Popup(img, x, max(2, y), life=life))

    @property
    def hands(self) -> tuple[float, float]:
        return self.x + self.facing * 10, self.y

    @property
    def at_slab(self) -> bool:
        dx = max(SLAB_L - self.x, 0, self.x - SLAB_R)
        dy = max(SLAB_BACK - self.y, 0, self.y - art.SLAB_FRONT)
        return dx <= SLAB_REACH and dy <= SLAB_REACH

    @property
    def at_lever(self) -> bool:
        return abs(self.x - LEVER_SPOT[0]) <= LEVER_REACH[0] and self.y - LEVER_SPOT[1] <= LEVER_REACH[1]

    @property
    def complete(self) -> bool:
        return len(self.built) == NEED

    def body(self) -> dict[str, tuple[str, str]]:
        return {slot: (p.kind, p.fam) for slot, p in self.built.items()}

    @property
    def slab_top(self) -> int:
        """Screen row of the slab top's back edge."""
        return art.SLAB_FRONT - self.art.slab.get_height() + 2

    @property
    def body_center(self) -> tuple[float, float]:
        return art.SLAB_X, self.slab_top + art.SLAB_DEPTH / 2

    # -- update ------------------------------------------------------------------------
    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.phase_t += dt
        self.anim_t += dt
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        self._update_storm(dt)
        if self.phase == "title":
            self.howto.update(dt, inp)
            if self.howto.done:
                self.phase, self.phase_t = "play", 0.0
        elif self.phase == "play":
            if self.menu:
                self._update_menu(dt, inp)
            else:
                self._update_doc(dt, inp)
            self._update_lever(dt)
        elif self.phase == "zap":
            self._update_doc(dt, Input())
            self._update_zap(dt)
        elif self.phase == "won":
            self._update_doc(dt, Input())
            if inp.action and self.phase_t > 1.2:
                self.done = True
        self._update_parts(dt)
        self._update_fx(dt)

    def _update_doc(self, dt: float, inp: Input) -> None:
        if self.pull > 0:
            before = self.pull
            self.pull = max(0.0, self.pull - dt)
            if before > PULL_T / 2 >= self.pull:
                self._throw_switch()
            inp = Input()
        ix, iy = inp.x, inp.y * DEPTH
        n = math.hypot(inp.x, inp.y)
        if n > 1:
            ix, iy = ix / n, iy / n
        top = CARRY_MAX if self.held else DOC_MAX
        k = min(1.0, GRIP * dt)
        self.vx += (ix * top - self.vx) * k
        self.vy += (iy * top - self.vy) * k
        self.x, self.y, bx, by = self._move(self.x, self.y, self.vx * dt, self.vy * dt)
        if bx:
            self.vx = 0.0
        if by:
            self.vy = 0.0
        if inp.x:
            self.facing = inp.x
        if inp.action and self.phase == "play":
            self._act()

    def _act(self) -> None:
        """The one button: pick up, drop, use the slab or the switch, depending."""
        if self.held:
            if self.at_slab:
                self.menu = Menu()
                self.vx = self.vy = 0.0
            elif self.at_lever:
                self._popup("HANDS FULL!", self.x, self.y - 54, LAB_DIM, life=0.8)
            else:
                self._drop()
            return
        part = self._nearest_part()
        if self.at_lever:                                          # the switch beats a part lying under it
            if self.lever_to == 0 and self.fizzle <= 0:
                self.pull = PULL_T
                self.facing = 1 if LEVER_SPOT[0] >= self.x else -1
        elif part:
            part.state = "held"
            self.held = part
            self._popup(self.rng.choice(GRAB_LINES), self.x, self.y - 54)
        elif self.at_slab:
            self._popup(self.rng.choice(NUDGE_LINES), self.x, self.y - 54, LAB_DIM, life=1.0)

    def _nearest_part(self) -> Part | None:
        hx, hy = self.hands
        best, best_d = None, GRAB_R
        for p in self.parts:
            if p.state != "floor":
                continue
            d = min(math.hypot(p.x - hx, (p.y - hy) * 1.4), math.hypot(p.x - self.x, (p.y - self.y) * 1.4))
            if d < best_d:
                best, best_d = p, d
        return best

    def _drop(self) -> None:
        p = self.held
        self.held = None
        hx, hy = self.hands
        if self._blocked(hx, hy, 2):
            hx, hy = self.x, self.y
        p.x, p.y, p.z, p.state, p.t = hx, hy + 1, 0.0, "floor", 0.0
        self._popup(self.rng.choice(DROP_LINES), self.x, self.y - 54, LAB_DIM, life=0.7)

    def _update_menu(self, dt: float, inp: Input) -> None:
        m = self.menu
        m.t += dt
        self.vx = self.vy = 0.0
        if inp.y and not m.prev_y:
            m.i = (m.i + inp.y) % m.choices
        m.prev_y = inp.y
        if inp.action and m.t > 0.15:
            self.menu = None
            if m.i < NEED:
                self._place(SLOTS[m.i])

    def _place(self, slot: str) -> None:
        p = self.held
        self.held = None
        old = self.built.get(slot)
        p.state = "placed"
        self.built[slot] = p
        cx, cy = self.body_center
        if old:                                                    # knocked off onto the floor
            old.state, old.t = "air", 0.0
            old.x0, old.y0 = cx, art.SLAB_FRONT + 1
            side = -1 if self.rng.random() < 0.5 else 1
            for _ in range(40):
                tx = cx + side * self.rng.uniform(30, 70)
                ty = art.SLAB_FRONT + self.rng.uniform(10, 40)
                if not self._blocked(tx, ty, 4):
                    break
            else:
                tx, ty = cx, art.SLAB_FRONT + 20
            old.x1, old.y1 = tx, ty
            self._popup(self.rng.choice(SWAP_LINES), cx, cy - 34, "#ff9ab8")
        right = art.SLOT_KIND[slot] == p.kind
        self._popup(self.rng.choice(PLACE_LINES if right else WRONG_LINES), self.x, self.y - 54,
                    LAB_TEXT if right else "#f0d27a")
        for _ in range(4):
            self.sparks.append([cx + self.rng.uniform(-20, 20), cy + self.rng.uniform(-8, 8), 0.0])
        if self.complete and not self.nagged:
            self.nagged = True
            self._popup("NOW... THE SWITCH!", self.x, self.y - 64, "#ffd93a", life=2.0)

    def _throw_switch(self) -> None:
        self.lever_to = 1.0
        px, py = art.LEVER_PIVOT
        self.shake = 0.15
        if self.complete:
            self.phase, self.phase_t = "zap", 0.0
            self.cutscene = True
            self._popup("CLUNK!", px, py - 28, "#ffd93a")
        else:
            self.fizzle = FIZZLE_T
            for _ in range(5):
                self.sparks.append([px + self.rng.uniform(-8, 8), py - 18 + self.rng.uniform(-4, 4), 0.0])
            self._popup("FZZT...", px, py - 28, LAB_DIM, life=0.9)
            self._popup(self.rng.choice(FIZZLE_LINES), self.x, self.y - 54, "#ff9ab8", life=1.4)

    def _update_lever(self, dt: float) -> None:
        if self.fizzle > 0:
            self.fizzle -= dt
            if self.fizzle <= 0:
                self.lever_to = 0.0                              # springs back open
        self.lever += max(-dt * 4, min(dt * 8, self.lever_to - self.lever))

    def _update_zap(self, dt: float) -> None:
        self.lever += max(-dt * 4, min(dt * 8, self.lever_to - self.lever))
        e = self.phase_t
        cx, cy = self.body_center
        if SLAM < e < CHARGE:                                     # both coils arc into the body
            if self.rng.random() < dt * 14:
                coil = self.rng.choice(art.COILS)
                tx, ty = self._coil_top(coil)
                self._bolt((tx, ty), (cx + self.rng.uniform(-24, 24), cy + self.rng.uniform(-6, 6)))
                self.flash = max(self.flash, 0.06)
                self.shake = max(self.shake, 0.1)
            if self.rng.random() < dt * 2.2:
                self._popup(self.rng.choice(ZAP_LINES), cx + self.rng.uniform(-40, 40), cy - 40 - self.rng.uniform(0, 14),
                            "#5ff3ff", life=0.7)
            if self.rng.random() < dt * 3:
                self.storm = 0.15
        if CHARGE <= e < SIT and self.rng.random() < dt * 5:       # smoking
            self.puffs.append([cx + self.rng.uniform(-24, 24), cy - 4, 0.0])
        if e >= SIT and self.phase_t - dt < SIT:
            self.flash = 0.25
            self.shake = 0.3
            for _ in range(8):
                self.puffs.append([cx + self.rng.uniform(-20, 20), cy + self.rng.uniform(-8, 4), 0.0])
        if HOP <= e:
            self.rise = min(1.0, (e - HOP) / 0.45)
            if e - dt < HOP + 0.45 <= e:
                self.shake = 0.25
                self._popup("THUD!", cx, art.SLAB_FRONT + HOP_DOWN - 4, LAB_DIM, life=0.6)
        if e >= ROAR and e - dt < ROAR:
            self._popup(self.rng.choice(ROAR_LINES), cx, art.SLAB_FRONT + HOP_DOWN - 80, "#d4ff7a", life=2.4)
            self._popup(self.rng.choice(ALIVE_LINES), self.x, self.y - 56, "#ffd93a", life=3.0)
        if self.phase == "zap" and e >= BANNER:
            self.phase, self.phase_t = "won", 0.0
            self.result = "win"
            self.cutscene = False

    def _coil_top(self, coil: tuple[int, int]) -> tuple[int, int]:
        x, y = coil
        return x - soup_art.TESLA_W // 2 + soup_art.TESLA_TOP[0], y - soup_art.TESLA_H + 2 + soup_art.TESLA_TOP[1]

    def _bolt(self, a: tuple[float, float], b: tuple[float, float]) -> None:
        pts = [a]
        n = 7
        for k in range(1, n):
            t = k / n
            pts.append((a[0] + (b[0] - a[0]) * t + self.rng.uniform(-6, 6),
                        a[1] + (b[1] - a[1]) * t + self.rng.uniform(-4, 4)))
        pts.append(b)
        self.bolts.append([pts, 0.0])

    def _update_parts(self, dt: float) -> None:
        for p in self.parts:
            p.t += dt
            if p.state == "air":
                k = min(1.0, p.t / 0.6)
                p.x = p.x0 + (p.x1 - p.x0) * k
                p.y = p.y0 + (p.y1 - p.y0) * k
                p.z = 34 * math.sin(k * math.pi) + 10 * (1 - k)
                if k >= 1:
                    p.state, p.z, p.t = "floor", 0.0, 0.0
            elif p.state == "floor":
                p.twitch -= dt
                if p.twitch < -0.4:
                    p.twitch = self.rng.uniform(2, 7)

    def _update_storm(self, dt: float) -> None:
        self.storm = max(0.0, self.storm - dt)
        self.storm_in -= dt
        if self.storm_in <= 0:
            self.storm = 0.18
            self.storm_in = self.rng.uniform(4, 10)

    def _update_fx(self, dt: float) -> None:
        for p in self.popups:
            p.t += dt
            p.y -= 12 * dt
        self.popups = [p for p in self.popups if p.t < p.life]
        for b in self.bolts:
            b[1] += dt
        self.bolts = [b for b in self.bolts if b[1] < 0.12]
        for s in self.sparks:
            s[2] += dt
        self.sparks = [s for s in self.sparks if s[2] < 0.4]
        for s in self.puffs:
            s[2] += dt
        self.puffs = [s for s in self.puffs if s[2] < 1.2]

    # -- draw --------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        a = self.art
        ox = round(self.rng.uniform(-2, 2)) if self.shake > 0 else 0
        oy = round(self.rng.uniform(-1, 1)) if self.shake > 0 else 0
        frame = screen if not (ox or oy) else pygame.Surface((W, H))
        frame.blit(a.lab, (0, 0))
        self._draw_wall(frame)

        items: list[tuple[float, int, str, object]] = [(art.SLAB_FRONT, 0, "slab", None)]
        for coil in art.COILS:
            items.append((coil[1], 1, "coil", coil))
        for p in self.parts:
            if p.state in ("floor", "air"):
                items.append((p.y, 2, "part", p))
        items.append((self.y, 3, "doc", None))
        if self.phase == "won" or (self.phase == "zap" and self.phase_t >= HOP):
            items.append((art.SLAB_FRONT + HOP_DOWN * self.rise + 0.5, 3, "risen", None))
        for y, _, kind, obj in sorted(items, key=lambda it: (it[0], it[1])):
            getattr(self, "_draw_" + kind)(frame, obj)

        for pts, t in self.bolts:
            ipts = [(round(x), round(y)) for x, y in pts]
            pygame.draw.lines(frame, hex_to_rgba("#5ff3ff"), False, [(x + 1, y) for x, y in ipts], 1)
            pygame.draw.lines(frame, hex_to_rgba("#ffffff"), False, ipts, 1)
        for x, y, t in self.sparks:
            img = a.spark
            if int(t * 20) % 2 == 0:
                frame.blit(img, (round(x) - 3, round(y - t * 20) - 3))
        for x, y, t in self.puffs:
            img = a.smoke[min(3, int(t * 3.4))]
            frame.blit(img, (round(x) - 6, round(y - 8 - t * 18)))
        for p in self.popups:
            if p.t < p.life - 0.3 or int(p.t * 20) % 2:
                frame.blit(p.text, (round(p.x) - p.text.get_width() // 2, round(p.y)))
        if self.flash > 0:
            glare = pygame.Surface((W, H), pygame.SRCALPHA)
            glare.fill((220, 248, 255, 110))
            frame.blit(glare, (0, 0))
        if frame is not screen:
            screen.fill(hex_to_rgba(LAB_BG))
            screen.blit(frame, (ox, oy))
        self._draw_hud(screen)

    def _draw_wall(self, screen: pygame.Surface) -> None:
        a = self.art
        for wx, wy, ww, wh in art.WINDOWS:                                 # rain, and the odd fork of lightning
            clip = screen.get_clip()
            screen.set_clip(pygame.Rect(wx, wy - 1, ww, wh + 1))
            if self.storm > 0:
                screen.fill((150, 160, 220), pygame.Rect(wx, wy - 1, ww, wh + 1))
                lx = wx + 6 + (int(self.time * 7) % (ww - 12))
                pygame.draw.lines(screen, (255, 255, 255), False,
                                  [(lx, wy - 1), (lx + 3, wy + 8), (lx - 1, wy + 14), (lx + 2, wy + wh)], 1)
            for k in range(9):
                rx = wx + (k * 7 + int(self.time * 40)) % ww
                ry = wy + (k * 13 + int(self.time * 160)) % wh
                pygame.draw.line(screen, (90, 110, 170), (rx, ry), (rx - 1, ry + 3))
            screen.set_clip(clip)
            pygame.draw.line(screen, (30, 24, 40), (wx + ww // 2, wy), (wx + ww // 2, wy + wh - 1))
            pygame.draw.line(screen, (30, 24, 40), (wx, wy + wh // 2), (wx + ww - 1, wy + wh // 2))
        for i, (tx, ty) in enumerate(art.TORCHES):                         # torches flicker
            f = (int(self.time * 10) + i * 3) % 4
            pygame.draw.ellipse(screen, hex_to_rgba("#ff9a3a"), (tx - 2, ty - 6 + (f == 2), 5, 7 - (f == 2)))
            pygame.draw.ellipse(screen, hex_to_rgba("#ffd93a"), (tx - 1, ty - 4 + (f % 2), 3, 4))
        live = self.phase == "play" and self.complete
        px, py = art.LEVER_PIVOT                                           # the knife switch
        k = min(len(a.blades) - 1, max(0, round(self.lever * (len(a.blades) - 1))))
        screen.blit(a.blades[k], (px - art.BLADE_BOX // 2, py - art.BLADE_BOX // 2))
        if live and int(self.time * 4) % 2:                                # ready: a lamp and an arrow
            pygame.draw.rect(screen, hex_to_rgba("#39ff14"), (art.SWITCH[0] + 4, art.SWITCH[1] + 14, 3, 3))
        if self.phase in ("zap", "won") and self.lever > 0.9 and int(self.time * 15) % 3 == 0:
            screen.blit(a.spark, (px - 3 + self.rng.randint(-3, 3), py - 20 + self.rng.randint(-2, 2)))

    def _draw_slab(self, screen: pygame.Surface, _: object) -> None:
        a = self.art
        sx, sy = SLAB_L - 1, art.SLAB_FRONT - a.slab.get_height() + 1
        screen.blit(a.slab, (sx, sy))
        cx, cy = self.body_center
        e = self.phase_t
        if self.phase in ("title", "play") or (self.phase == "zap" and e < SIT):    # lying there, waiting
            _, lying, _ = a.creature(self.body())
            jx = jy = 0
            if self.phase == "zap" and SLAM < e < CHARGE:
                jx, jy = self.rng.randint(-1, 1), self.rng.randint(-1, 0)
            elif self.phase == "zap" and CHARGE + 0.6 < e < SIT and int(e * 9) % 3 == 0:
                jy = -1                                                    # twitch...
            img = white(lying) if self.phase == "zap" and SLAM < e < CHARGE and int(e * 30) % 2 else lying
            screen.blit(img, (round(cx - img.get_width() / 2) + jx, round(cy - img.get_height() / 2) + jy))
            screen.blit(a.straps, (sx, sy))
            if self.phase == "play" and self.held and self.at_slab and int(self.time * 4) % 2:
                pygame.draw.rect(screen, hex_to_rgba("#ffd93a"), (sx, sy, a.slab.get_width(), art.SLAB_DEPTH + 2), 1)
        elif self.phase == "zap" and e < HOP:                              # sat up: standing on the slab
            self._draw_creature(screen, cx, art.SLAB_FRONT - art.SLAB_FACE - 6, bob=int(e * 6) % 2)

    def _draw_risen(self, screen: pygame.Surface, _: object) -> None:
        cx, _ = self.body_center
        e = self.phase_t if self.phase == "zap" else BANNER + self.phase_t
        k = self.rise
        top = art.SLAB_FRONT - art.SLAB_FACE - 6
        land = art.SLAB_FRONT + HOP_DOWN
        feet = top + (land - top) * k - 22 * math.sin(k * math.pi)
        x = cx
        if e > ROAR + 0.6:                                                 # lurching about, arms out
            x = cx + 10 * math.sin((e - ROAR - 0.6) * 1.6)
        pygame.draw.ellipse(screen, (16, 10, 30), (round(x) - 12, land - 1, 24, 4))
        self._draw_creature(screen, x, feet, bob=int(e * 4) % 2 if k >= 1 else 0)

    def _draw_creature(self, screen: pygame.Surface, x: float, feet: float, bob: int = 0) -> None:
        standing, _, foot_row = self.art.creature(self.body())
        screen.blit(standing, (round(x - art.MW / 2), round(feet - foot_row) + bob))

    def _draw_coil(self, screen: pygame.Surface, coil: tuple[int, int]) -> None:
        q = 0.0
        if self.phase == "zap" and SLAM < self.phase_t < CHARGE:
            q = 1.0 if int(self.phase_t * 12) % 2 else 0.5
        elif self.phase == "play" and self.complete:
            q = 0.5 if int(self.time * 3) % 2 else 0.0
        img = self.art.coil[0 if q <= 0 else 1 if q < 0.6 else 2]
        x, y = coil
        screen.blit(img, (x - soup_art.TESLA_W // 2, y - soup_art.TESLA_H + 2))

    def _shadow(self, screen: pygame.Surface, x: float, y: float, w: int) -> None:
        pygame.draw.ellipse(screen, (16, 10, 30), (round(x) - w // 2, round(y) - 1, w, 3))

    def _draw_part(self, screen: pygame.Surface, p: Part) -> None:
        img = self.art.parts[(p.kind, p.fam)][p.flip]
        self._shadow(screen, p.x, p.y + 1, img.get_width() - 2)
        jig = (1 if int(p.t * 30) % 2 else -1) if p.state == "floor" and p.twitch < 0 else 0
        screen.blit(img, (round(p.x - img.get_width() / 2) + jig, round(p.y - p.z - img.get_height()) + 1))
        if self.phase == "play" and not self.held and not self.menu and not self.at_lever and p is self._nearest_part():
            ax, ay = round(p.x), round(p.y - p.z - img.get_height()) - 6 + round(math.sin(self.time * 8))
            pygame.draw.polygon(screen, hex_to_rgba("#ffd93a"), [(ax - 3, ay), (ax + 3, ay), (ax, ay + 3)])

    def _doc_frame(self) -> tuple[str, int]:
        if self.pull > 0:
            return "interact", min(3, int((PULL_T - self.pull) / PULL_T * 4))
        if self.phase == "won" or (self.phase == "zap" and self.phase_t >= ROAR):
            return "cheer", int(self.time * 6) % 2
        if self.phase == "zap" and SLAM < self.phase_t < CHARGE:
            return "interact", 2
        moving = math.hypot(self.vx, self.vy) > 12
        if self.held:
            return ("carry_run", int(self.anim_t * 12) % 4) if moving else ("carry_idle", int(self.anim_t * 4) % 4)
        return ("run", int(self.anim_t * 12) % 4) if moving else ("idle", int(self.anim_t * 4) % 4)

    def _draw_doc(self, screen: pygame.Surface, _: object) -> None:
        name, f = self._doc_frame()
        self._shadow(screen, self.x, self.y + 1, 16)
        img = self.art.doc[name][f][self.facing]
        screen.blit(img, (round(self.x) - SIZE // 2, round(self.y) - GROUND))
        if self.held:
            px, py = self.art.carry_pts[name][f]
            if self.facing < 0:
                px = SIZE - 1 - px
            pimg = self.art.parts[(self.held.kind, self.held.fam)][self.held.flip]
            screen.blit(pimg, (round(self.x) - SIZE // 2 + px - pimg.get_width() // 2,
                               round(self.y) - GROUND + py - pimg.get_height() + 3))

    # -- hud ---------------------------------------------------------------------------
    def _draw_hud(self, screen: pygame.Surface) -> None:
        if self.phase == "title":
            self.howto.draw(screen)
            return
        panel = pygame.Surface((62, 9), pygame.SRCALPHA)
        panel.fill((20, 15, 38, 220))
        screen.blit(panel, (2, H - 10))
        n = len(self.built)
        screen.blit(text_surface(f"PARTS {n}/{NEED}", "#d4ff7a" if n == NEED else LAB_TEXT), (5, H - 8))
        if self.phase == "play" and self.held and not self.menu:
            label = text_surface(self.held.name, LAB_DIM)
            screen.blit(label, (68, H - 8))
        if self.phase == "play" and self.complete and not self.menu and int(self.time * 3) % 2:
            px = art.LEVER_PIVOT[0]
            hint = text_surface("THROW IT!", "#ffd93a")
            screen.blit(hint, (px - hint.get_width() // 2, art.SWITCH[1] + art.SWITCH[3] + 18))
        if self.menu:
            self._draw_menu(screen)
        if self.phase == "won":
            names = [self.built[s].name for s in SLOTS]
            self._banner(screen, "IT'S ALIVE!", [f"{names[0]}, {names[1]},", f"{names[2]}, {names[3]},",
                                                  f"AND A {names[4]}.", "", "PRESS BUTTON"])

    def _draw_menu(self, screen: pygame.Surface) -> None:
        m = self.menu
        x0, y0, w, h = 40, 6, 240, 92
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((20, 15, 38, 235))
        screen.blit(panel, (x0, y0))
        pygame.draw.rect(screen, (90, 78, 130), (x0, y0, w, h), 1)
        title = text_surface(f"WHERE DOES THE {self.held.name} GO?", "#ffd93a")
        screen.blit(title, (x0 + 6, y0 + 5))
        for i in range(m.choices):
            y = y0 + 17 + i * 11
            sel = i == m.i
            if sel:
                pygame.draw.rect(screen, (60, 50, 100), (x0 + 3, y - 2, 164, 9))
                if int(self.time * 4) % 2:
                    pygame.draw.polygon(screen, hex_to_rgba("#ffd93a"), [(x0 + 5, y), (x0 + 5, y + 4), (x0 + 7, y + 2)])
            if i < NEED:
                slot = SLOTS[i]
                screen.blit(text_surface(slot, LAB_TEXT if sel else LAB_DIM), (x0 + 10, y))
                there = self.built.get(slot)
                screen.blit(text_surface(there.name if there else "---", "#ff9ab8" if there else LAB_DIM),
                            (x0 + 62, y))
            else:
                screen.blit(text_surface("NEVER MIND", LAB_TEXT if sel else LAB_DIM), (x0 + 10, y))
        body = self.body()                                                 # preview, with the part blinking in
        if m.i < NEED and int(self.time * 4) % 4:
            body[SLOTS[m.i]] = (self.held.kind, self.held.fam)
        standing, _, foot = self.art.creature(body)
        bx = x0 + w - art.MW - 6
        by = y0 + h - 4 - foot
        screen.set_clip(pygame.Rect(x0 + 1, y0 + 1, w - 2, h - 2))
        screen.blit(standing, (bx, by))
        screen.set_clip(None)

    def _banner(self, screen: pygame.Surface, title: str, lines: list[str]) -> None:
        shade = pygame.Surface((W, 30 + 9 * len(lines)), pygame.SRCALPHA)
        shade.fill((20, 15, 38, 215))
        top = 8
        screen.blit(shade, (0, top))
        t = big_text(title, "#d4ff7a")
        screen.blit(t, (W // 2 - t.get_width() // 2, top + 7))
        for i, line in enumerate(lines):
            if line:
                s = text_surface(line, LAB_DIM if line != "PRESS BUTTON" else LAB_TEXT)
                screen.blit(s, (W // 2 - s.get_width() // 2, top + 25 + i * 9))


CELL = 4                        # autopilot's path grid


def _route(game: BuildABear, tx: float, ty: float) -> tuple[float, float]:
    """Next waypoint toward (tx, ty) round the slab and coils: a breadth-first
    distance map back from the goal, cached per goal cell."""
    cols, rows = int((X_MAX - X_MIN) // CELL) + 1, int((Y_MAX - Y_MIN) // CELL) + 1
    cell = lambda x, y: (max(0, min(cols - 1, round((x - X_MIN) / CELL))), max(0, min(rows - 1, round((y - Y_MIN) / CELL))))
    centre = lambda c: (X_MIN + c[0] * CELL, Y_MIN + c[1] * CELL)
    pilot = game.__dict__
    if "_open" not in pilot:
        pilot["_open"] = {(i, j) for i in range(cols) for j in range(rows) if not game._blocked(*centre((i, j)), FEET_R + 3)}
        pilot["_maps"] = {}
    goal = cell(tx, ty)
    if goal not in pilot["_open"]:                                          # nearest open cell to the goal
        goal = min(pilot["_open"], key=lambda c: (c[0] - goal[0]) ** 2 + (c[1] - goal[1]) ** 2)
    dist = pilot["_maps"].get(goal)
    if dist is None:
        dist, frontier = {goal: 0}, [goal]
        while frontier:
            nxt = []
            for i, j in frontier:
                for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if n in pilot["_open"] and n not in dist:
                        dist[n] = dist[(i, j)] + 1
                        nxt.append(n)
            frontier = nxt
        pilot["_maps"][goal] = dist
    here = cell(game.x, game.y)
    if dist.get(here, 99) <= 2:
        return tx, ty
    step = here
    for _ in range(3):                                                      # look a few cells down the path
        options = [n for n in ((step[0] + 1, step[1]), (step[0] - 1, step[1]), (step[0], step[1] + 1),
                               (step[0], step[1] - 1)) if n in dist]
        if not options:
            break
        step = min(options, key=lambda n: dist[n])
    return centre(step)


def autopilot(game: BuildABear) -> Input:
    """A computer player that builds a proper body (heads on necks and so on), for demos and smoke tests."""
    inp = Input()
    game.__dict__["_pilot_tick"] = game.__dict__.get("_pilot_tick", 0) + 1
    tick = game.__dict__["_pilot_tick"]
    if game.phase != "play":
        inp.action = game.phase in ("title", "won") and game.phase_t > 1.5 and tick % 30 == 0
        return inp
    if game.menu:
        want = next((i for i, s in enumerate(SLOTS) if s not in game.built and art.SLOT_KIND[s] == game.held.kind),
                    next((i for i, s in enumerate(SLOTS) if s not in game.built), NEED))
        if game.menu.i != want:
            inp.y = (1 if want > game.menu.i else -1) if tick % 2 else 0
        else:
            inp.action = tick % 6 == 0
        return inp
    if game.complete and game.held:                                         # spare part: put it down
        inp.action = tick % 8 == 0
        return inp
    if game.complete:
        tx, ty = LEVER_SPOT[0] - 4, LEVER_SPOT[1] + 2
        if game.at_lever:
            inp.action = game.pull <= 0 and tick % 8 == 0
            return inp
    elif game.held:
        tx, ty = art.SLAB_X, art.SLAB_FRONT + 8
        if game.at_slab:
            inp.action = tick % 8 == 0
            return inp
    else:
        empty = {art.SLOT_KIND[s] for s in SLOTS if s not in game.built}
        wanted = [p for p in game.parts if p.state == "floor" and p.kind in empty]
        if not wanted:
            return inp
        p = min(wanted, key=lambda p: math.hypot(p.x - game.x, p.y - game.y))
        tx, ty = p.x - math.copysign(8, p.x - game.x), p.y
        if p is game._nearest_part():
            inp.action = tick % 8 == 0
            return inp
    tx, ty = _route(game, tx, ty)
    dx, dy = tx - game.x, ty - game.y
    inp.x = (dx > 2) - (dx < -2)
    inp.y = (dy > 2) - (dy < -2)
    return inp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--demo", action="store_true", help="let the computer play")
    ap.add_argument("--skip-title", action="store_true", help="straight into the lab")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()
    run(lambda: BuildABear(seed=args.seed, show_title=not args.skip_title), "Build-A-Bear", scale=args.scale,
        fullscreen=args.fullscreen, autopilot=autopilot if args.demo else None, max_ticks=args.ticks,
        screenshot=args.screenshot)


if __name__ == "__main__":
    main()
