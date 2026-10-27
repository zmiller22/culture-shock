"""Stork Bomber: fly the stork, drop the baby, land it in the moving target.

    python -m minigames.stork_bomber [--fullscreen] [--scale 4] [--demo]

Controls (keyboard, or an arcade stick / gamepad):
    ARROWS              fly                     stick
    SPACE / Z / ENTER   drop the baby           button 0
    ESC / Q             quit

Deliver NEED babies out of BABIES to win. The target speeds up after every
delivery. The baby keeps the stork's momentum when it's dropped, so lead the shot.
Land STREAK in a row and the target squirts all over the place. Now and then
the Flying Spaghetti Monster shows up and chases the stork to steal the baby:
outfly it.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass

import pygame

from sprites.canvas import hex_to_rgba
from sprites.palette import LAB_DIM, LAB_GRID, LAB_TEXT
from sprites.rig import GROUND, SIZE
from sprites.viewer import H, W, text_surface, to_surface

from ..shell import Input, run
from . import art, hairy_man

BABIES, NEED = 5, 3            # babies per round, deliveries needed to win
FLOOR_Y = 168

STORK_ACCEL = 520              # px/s^2 while the stick is held
STORK_DRAG = 3.0               # velocity lost per second (fraction)
STORK_MAX = 120                # px/s
FLY_X = (24, W - 24)           # where the stork's center may go
FLY_Y = (26, 86)
FLAP_FPS, FLAP_FPS_CLIMB = 8, 14
RELOAD = 0.7                   # s between a baby landing and the next one appearing

GRAVITY = 330                  # px/s^2 on the falling baby
CARRY = 0.9                    # share of the stork's velocity the baby keeps
BABY_DRAG = 0.4
CRY_TIME = 1.4

TARGET_SPEED = 45              # px/s, plus TARGET_SPEEDUP per delivery
TARGET_SPEEDUP = 12
TARGET_X = (28, W - 28)
# A baby that falls within art.GRAB_REACH px of the target's center (at the
# height of its hands) gets grabbed, pulled in and eaten.
BONK_HALF = 12                 # px either side that bounces off while it's busy chewing
GRAB_HOLD = 0.12               # s the hands hold the baby where they caught it
# After a catch: grab and eat, chew (DNA swirls around), then spit out a grown man.
SWALLOW, CHEW, SPIT = 0.55, 2.4, 0.6
GULP_TIME = SWALLOW + CHEW + SPIT
DNA_STRANDS = 6
DNA_SPIN = (1.2, 3.0)          # rad/s the helices circle the target, at the start and end of the chew
DNA_TWIST_FPS = 5              # how fast each helix twists
MAN_GRAVITY = 450
MAN_LAUNCH = (70, -170)        # px/s sideways (toward mid-screen) and up out of the opening
MAN_STAND = 0.8                # s he stands there before running off
MAN_RUN = 110
# Deliver STREAK babies in a row (no misses or steals between) and, after the
# man pops out, the target squirts all over the place.
STREAK = 3
SQUIRT_TIME = 2.6              # s of squirting
SQUIRT_RATE = 150              # drops/s while a pulse is on
SQUIRT_PULSE = 10              # pulses per second, give or take (rad/s of the on/off wave)
SQUIRT_SPEED = (90, 270)       # px/s launch speed
SQUIRT_GRAVITY = 420
SPLAT_LIFE = 4.0               # s a puddle stays on the floor

GRAB_LINES = ["GOTCHA!", "MINE!", "GIMME!"]
CATCH_LINES = ["GULP!", "NOM!", "SLURP!"]
CHEW_LINES = ["CHOMP", "MUNCH", "CHEW"]
MAN_LINES = ["IT'S A BOY!", "IT'S A... MAN?", "HE'S 43!", "HE HAS A MORTGAGE!", "MAZEL TOV!", "HE PAYS TAXES!"]
MISS_LINES = ["WAAH!", "WAAAAH!", "OOPS!"]
STOLEN_LINES = ["STOLEN!", "PASTA NAPPED!", "RAMEN!"]

# The Flying Spaghetti Monster: drifts in now and then and chases the bundle.
# Slower than the stork, so you can outfly it, but it turns well and never gives up
# until its time is up.
FSM_FIRST = (9.0, 14.0)        # s into the round before its first visit
FSM_EVERY = (14.0, 22.0)       # s between visits
FSM_HUNT = 5.0                 # s it chases before giving up
FSM_SPEED = 60                 # px/s, plus FSM_SPEEDUP per delivery
FSM_SPEEDUP = 4
FSM_STEER = 1.4                # how quickly it turns toward the bundle (1/s)
FSM_ESCAPE = 150               # px/s flying off afterwards
FSM_GRAB_R = 7                 # px between its noodles and the bundle to snatch it
BONK_LINES = ["BONK!", "BOING!"]


@dataclass
class Baby:
    x: float
    y: float
    vx: float
    vy: float
    state: str = "fall"        # fall | ground
    t: float = 0.0
    bounced: bool = False
    bonked: bool = False


@dataclass
class Popup:
    text: pygame.Surface
    x: float
    y: float
    t: float = 0.0
    life: float = 1.2


@dataclass
class Man:
    x: float
    y: float                   # feet
    vx: float
    vy: float
    state: str = "fly"         # fly | stand | run
    t: float = 0.0

    @property
    def facing(self) -> int:
        return 1 if self.vx >= 0 else -1


@dataclass
class Monster:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    state: str = "hunt"        # hunt | leave
    t: float = 0.0
    carrying: bool = False

    @property
    def grab(self) -> tuple[float, float]:
        """Where its noodles hold a stolen bundle."""
        return self.x, self.y + art.FSM_GRAB[1] - art.FSM_H // 2


@dataclass
class Heart:
    x: float
    y: float
    vx: float
    t: float = 0.0


def both(c) -> dict[int, pygame.Surface]:
    right = to_surface(c)
    return {1: right, -1: pygame.transform.flip(right, True, False)}


class Art:
    """Every sprite pre-rendered to surfaces, both facings."""

    def __init__(self) -> None:
        self._held: dict[tuple[int, int], tuple[dict, dict]] = {}

        self.stork = {carry: [both(art.stork(f, carry)) for f in range(4)] for carry in (True, False)}
        self.baby = [to_surface(art.baby(f)) for f in range(2)]
        self.crying = [to_surface(art.baby(f, crying=True)) for f in range(2)]
        self.target = {p: both(art.target(p)) for p in art.TARGET_POSES}
        self.drop = [to_surface(art.droplet(big)) for big in (False, True)]
        self.puddle = [to_surface(art.puddle(w)) for w in (5, 8, 11)]
        self.fsm = [both(art.spaghetti_monster(f)) for f in range(art.FSM_FRAMES)]
        self.dna = [to_surface(art.dna(f)) for f in range(art.DNA_FRAMES)]
        self.man = {anim: [both(f) for f in frames] for anim, frames in hairy_man.frames().items()}
        self.heart = to_surface(art.heart())
        self.clouds = [to_surface(art.cloud(w, seed)) for w, seed in ((54, 1), (38, 2), (70, 3), (46, 4))]
        self.backdrop = to_surface(art.backdrop(W, H, FLOOR_Y))

    def held(self, dx: int, y: int) -> tuple[dict, dict]:
        """(target, hands) surfaces for the arms holding a baby at (dx, y), rendered on demand."""
        key = (dx, y)
        if key not in self._held:
            self._held[key] = both(art.target("open", key)), both(art.target_hands(key))
        return self._held[key]


_ART: Art | None = None


def big_text(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


class StorkBomber:
    title = "STORK BOMBER"

    def __init__(self, seed: int | None = None, show_title: bool = True) -> None:
        global _ART
        _ART = _ART or Art()                          # render once, reuse across rounds
        self.art = _ART
        self.rng = random.Random(seed)
        self.result: str | None = None
        self.done = False
        self.phase = "title" if show_title else "play"
        self.phase_t = 0.0

        self.x, self.y = W * 0.3, 50.0
        self.vx = self.vy = 0.0
        self.facing = 1
        self.flap = 0.0
        self.loaded = True
        self.reload = 0.0

        self.babies_left = BABIES - 1                 # one is already in the beak
        self.delivered = 0
        self.baby: Baby | None = None

        self.tx = W * 0.6
        self.tvx = TARGET_SPEED
        self.tfacing = 1                              # the raised hand is held out in front
        self.held_dx = 0.0                            # where the hands grabbed the baby, from center
        self.streak = 0                               # deliveries in a row
        self.squirt = 0.0                             # counts down while it squirts
        self.squirt_pending = False
        self.drops: list[list[float]] = []            # [x, y, vx, vy, big]
        self.splats: list[list[float]] = []           # [x, size, t]
        self.ewed = False
        self.t_anim = 0.0
        self.turn_in = self._next_turn()
        self.gulp = 0.0                               # counts down through swallow / chew / spit
        self.chomp_in = 0.0
        self.men: list[Man] = []
        self.fsm: Monster | None = None
        self.fsm_in = self.rng.uniform(*FSM_FIRST)

        self.popups: list[Popup] = []
        self.hearts: list[Heart] = []
        self.cloud_x = [self.rng.uniform(0, W) for _ in self.art.clouds]
        self.time = 0.0

    # -- helpers ------------------------------------------------------------------
    def _next_turn(self) -> float:
        return self.rng.uniform(1.0, 3.0)

    @property
    def bundle_pos(self) -> tuple[float, float]:
        dx = art.BUNDLE_AT[0] - art.STORK_CENTER[0]
        dy = art.BUNDLE_AT[1] - art.STORK_CENTER[1]
        return self.x + self.facing * dx, self.y + dy

    @property
    def babies_in_play(self) -> int:
        """Babies not yet delivered or lost: in the beak, on the way, or in the air."""
        return self.babies_left + (self.loaded or self.reload > 0 or self.baby is not None)

    @property
    def target_top(self) -> float:
        return FLOOR_Y - art.TARGET_FEET

    @property
    def hole_y(self) -> float:
        return self.target_top + art.TARGET_HOLE

    @property
    def grab_y(self) -> float:
        return self.target_top + art.TARGET_GRAB

    def _popup(self, text: str, x: float, y: float, color: str = LAB_TEXT, life: float = 1.2) -> None:
        self.popups.append(Popup(text_surface(text, color), x, y, life=life))

    # -- update ---------------------------------------------------------------------
    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.phase_t += dt
        self.t_anim += dt
        for i, _ in enumerate(self.cloud_x):
            self.cloud_x[i] = (self.cloud_x[i] - (4 + 3 * i) * dt) % (W + 80)

        if self.phase == "title":
            self.flap += FLAP_FPS * dt
            if inp.action and self.phase_t > 0.3:
                self.phase, self.phase_t = "play", 0.0
            return
        if self.phase in ("won", "lost"):
            self.flap += FLAP_FPS * dt
            self._update_fx(dt)
            if inp.action and self.phase_t > 1.0:
                self.done = True
            return

        self._update_stork(dt, inp)
        self._update_baby(dt)
        self._update_target(dt)
        self._update_fsm(dt)
        self._update_fx(dt)

        if (self.delivered >= NEED and not self.baby and self.gulp <= 0 and all(m.state != "fly" for m in self.men)
                and self.squirt <= 0 and not self.squirt_pending and not self.drops):
            self.phase, self.phase_t, self.result = "won", 0.0, "win"
        elif self.delivered + self.babies_in_play < NEED:
            self.phase, self.phase_t, self.result = "lost", 0.0, "lose"

    def _update_stork(self, dt: float, inp: Input) -> None:
        self.vx += inp.x * STORK_ACCEL * dt
        self.vy += inp.y * STORK_ACCEL * dt
        self.vx -= self.vx * STORK_DRAG * dt
        self.vy -= self.vy * STORK_DRAG * dt
        speed = math.hypot(self.vx, self.vy)
        if speed > STORK_MAX:
            self.vx, self.vy = self.vx * STORK_MAX / speed, self.vy * STORK_MAX / speed
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not FLY_X[0] <= self.x <= FLY_X[1]:
            self.x, self.vx = max(FLY_X[0], min(FLY_X[1], self.x)), 0.0
        if not FLY_Y[0] <= self.y <= FLY_Y[1]:
            self.y, self.vy = max(FLY_Y[0], min(FLY_Y[1], self.y)), 0.0
        if inp.x:
            self.facing = inp.x
        self.flap += (FLAP_FPS_CLIMB if inp.y < 0 else FLAP_FPS) * dt

        if self.reload > 0:
            self.reload -= dt
            if self.reload <= 0:
                self.loaded = True
        if inp.action and self.loaded and self.baby is None:
            bx, by = self.bundle_pos
            self.baby = Baby(bx, by, self.vx * CARRY, self.vy * CARRY * 0.5)
            self.loaded = False

    def _update_baby(self, dt: float) -> None:
        b = self.baby
        if not b:
            return
        b.t += dt
        if b.state == "ground":
            if b.t >= CRY_TIME:
                self._next_baby()
            return

        prev_y = b.y
        b.vy += GRAVITY * dt
        b.vx -= b.vx * BABY_DRAG * dt
        b.x += b.vx * dt
        b.y += b.vy * dt
        if not 8 <= b.x <= W - 8:
            b.x, b.vx = max(8, min(W - 8, b.x)), -b.vx * 0.5

        # crossing the hands' height on the way down
        if prev_y < self.grab_y <= b.y and b.vy > 0 and not b.bonked:
            dx = b.x - self.tx
            busy = self.gulp > 0 or self.squirt > 0
            if abs(dx) <= art.GRAB_REACH and not busy:
                self._catch(dx)
                return
            if abs(dx) <= BONK_HALF and busy:           # still busy chewing: bounces off
                b.bonked = True
                b.vy = -110
                b.vx = math.copysign(70, dx)
                self._popup(self.rng.choice(BONK_LINES), b.x, b.y - 12, LAB_DIM)

        ground = FLOOR_Y - art.BABY_SIZE // 2 + 2
        if b.y >= ground:
            b.y = ground
            if b.vy > 120 and not b.bounced:
                b.vy, b.bounced = -b.vy * 0.3, True
                b.vx *= 0.5
            else:
                b.state, b.t, b.vx, b.vy = "ground", 0.0, 0.0, 0.0
                self.streak = 0
                self._popup(self.rng.choice(MISS_LINES), b.x, b.y - 16, "#5ff3ff")

    def _catch(self, dx: float) -> None:
        self.held_dx = dx
        self.delivered += 1
        self.streak += 1
        if self.streak % STREAK == 0:
            self.squirt_pending = True                  # it lets loose once the man is out
        self.gulp = GULP_TIME
        self.chomp_in = SWALLOW + 0.3
        self._popup(self.rng.choice(GRAB_LINES), self.tx, self.target_top)
        self._next_baby()

    def _next_baby(self) -> None:
        self.baby = None
        if self.babies_left > 0 and self.delivered < NEED:
            self.babies_left -= 1
            self.reload = RELOAD

    def _update_target(self, dt: float) -> None:
        if self.squirt > 0:
            self.squirt -= dt
            self._emit_squirt(dt)
            return
        if self.gulp > 0:
            before = self.gulp_elapsed
            self.gulp -= dt
            after = self.gulp_elapsed
            self.chomp_in -= dt
            if self.chomp_in <= 0 and after < SWALLOW + CHEW - 0.3:
                self.chomp_in = 0.6
                self._popup(self.rng.choice(CHEW_LINES), self.tx + self.rng.uniform(-14, 14),
                            self.target_top - 4, LAB_DIM, life=0.6)
            if before < SWALLOW <= after:
                self._popup(self.rng.choice(CATCH_LINES), self.tx, self.target_top)
            if before < SWALLOW + CHEW <= after:
                self._spit()
            if self.gulp <= 0:                          # back on its feet, a little faster
                self.tvx = math.copysign(TARGET_SPEED + TARGET_SPEEDUP * self.delivered, self.tvx)
                if self.squirt_pending:
                    self.squirt_pending, self.squirt, self.ewed = False, SQUIRT_TIME, False
                    self.popups.append(Popup(big_text(f"{STREAK} IN A ROW!", art.SQUIRT), W / 2, 34, life=2.2))
            return
        self.tx += self.tvx * dt
        self.tfacing = 1 if self.tvx >= 0 else -1
        if not TARGET_X[0] <= self.tx <= TARGET_X[1]:
            self.tx = max(TARGET_X[0], min(TARGET_X[1], self.tx))
            self.tvx = -self.tvx
        self.turn_in -= dt
        if self.turn_in <= 0:
            self.turn_in = self._next_turn()
            if self.rng.random() < 0.5:
                self.tvx = -self.tvx

    def _update_fsm(self, dt: float) -> None:
        m = self.fsm
        if m is None:
            self.fsm_in -= dt
            if self.fsm_in <= 0:
                side = self.rng.choice((-1, 1))
                self.fsm = Monster(W / 2 + side * (W / 2 + 30), self.rng.uniform(20, 60))
                self._popup("INCOMING PASTA!", W / 2, 20, "#f0d27a")
            return
        m.t += dt
        if m.state == "hunt":
            b = self.baby
            grabbable = True
            if self.loaded:
                aim = self.bundle_pos
            elif b and b.state == "fall":
                aim = (b.x, b.y)
            else:
                aim, grabbable = (self.x, self.y + 20), False     # hover under the stork, waiting
            gx, gy = m.grab
            dx, dy = aim[0] - gx, aim[1] - gy
            dist = math.hypot(dx, dy) or 1
            speed = FSM_SPEED + FSM_SPEEDUP * self.delivered
            k = min(1.0, FSM_STEER * dt)                 # lazy steering: it trails behind you
            m.vx += (dx / dist * speed - m.vx) * k
            m.vy += (dy / dist * speed - m.vy) * k
            if dist <= FSM_GRAB_R and grabbable:
                m.carrying, m.state = True, "leave"
                if self.loaded:
                    self.loaded = False
                self._popup(self.rng.choice(STOLEN_LINES), m.x, m.y - 26, "#f0d27a")
                self.streak = 0
                self._next_baby()
            elif m.t >= FSM_HUNT:
                m.state = "leave"
        else:                                            # up and away, toward the nearer side
            side = 1 if m.x > W / 2 else -1
            m.vx += (side * FSM_ESCAPE - m.vx) * min(1.0, 3 * dt)
            m.vy += (-FSM_ESCAPE * 0.4 - m.vy) * min(1.0, 3 * dt)
        m.x += m.vx * dt
        m.y += m.vy * dt
        if m.state == "leave" and not (-40 < m.x < W + 40 and m.y > -40):
            self.fsm = None
            self.fsm_in = self.rng.uniform(*FSM_EVERY)

    @property
    def gulp_elapsed(self) -> float:
        return GULP_TIME - self.gulp if self.gulp > 0 else 0.0

    def _spit(self) -> None:
        side = 1 if self.tx < W / 2 else -1             # out toward the middle of the screen
        self.men.append(Man(self.tx, self.hole_y + 12, side * MAN_LAUNCH[0], MAN_LAUNCH[1]))
        for _ in range(6):
            self.hearts.append(Heart(self.tx + self.rng.uniform(-8, 8), self.hole_y,
                                     self.rng.uniform(-20, 20), self.rng.uniform(-0.3, 0)))

    def _update_men(self, dt: float) -> None:
        for m in self.men:
            m.t += dt
            if m.state == "fly":
                m.vy += MAN_GRAVITY * dt
                m.x += m.vx * dt
                m.y += m.vy * dt
                if m.y >= FLOOR_Y and m.vy > 0:
                    m.y, m.vy, m.state, m.t = FLOOR_Y, 0.0, "stand", 0.0
                    self._popup(self.rng.choice(MAN_LINES), m.x, m.y - 58)
            elif m.state == "stand" and m.t >= MAN_STAND:
                m.state, m.t = "run", 0.0
                m.vx = math.copysign(MAN_RUN, m.vx)
            elif m.state == "run":
                m.x += m.vx * dt
        self.men = [m for m in self.men if -30 < m.x < W + 30]

    def _emit_squirt(self, dt: float) -> None:
        if math.sin(self.squirt * SQUIRT_PULSE) < -0.3:  # gushes come in pulses
            return
        count = SQUIRT_RATE * dt                         # fractional drops carry over by chance
        for _ in range(int(count) + (self.rng.random() < count % 1)):
            ang = self.rng.uniform(math.pi * 1.1, math.pi * 1.9)      # anywhere upward
            speed = self.rng.uniform(*SQUIRT_SPEED)
            self.drops.append([self.tx + self.rng.uniform(-2, 2), self.hole_y - 2,
                               math.cos(ang) * speed, math.sin(ang) * speed, self.rng.random() < 0.4])

    def _update_drops(self, dt: float) -> None:
        live = []
        for d in self.drops:
            d[3] += SQUIRT_GRAVITY * dt
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            if d[1] >= FLOOR_Y:
                self.splats.append([d[0], self.rng.randrange(3) if d[4] else 0, 0.0])
            elif math.hypot(d[0] - self.x, d[1] - self.y) < 14:      # splashed the stork
                if not self.ewed:
                    self.ewed = True
                    self._popup("EW!", self.x, self.y - 24, art.SQUIRT)
            elif -10 < d[0] < W + 10:
                live.append(d)
        self.drops = live
        for sp in self.splats:
            sp[2] += dt
        self.splats = [sp for sp in self.splats if sp[2] < SPLAT_LIFE][-80:]

    def _update_fx(self, dt: float) -> None:
        self._update_men(dt)
        self._update_drops(dt)
        for p in self.popups:
            p.t += dt
            p.y -= 14 * dt
        self.popups = [p for p in self.popups if p.t < p.life]
        for h in self.hearts:
            h.t += dt
            h.x += h.vx * dt
            h.y -= 40 * dt
        self.hearts = [h for h in self.hearts if h.t < 1.2]

    # -- draw -------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        a = self.art
        screen.blit(a.backdrop, (0, 0))
        for i, cloud in enumerate(a.clouds):
            screen.blit(cloud, (round(self.cloud_x[i]) - 80, 22 + i * 17))

        # target
        b = self.baby
        incoming = b and b.state == "fall" and not b.bonked and b.y > self.hole_y - 70 and abs(b.x - self.tx) < 26
        e = self.gulp_elapsed
        shake = 0
        if self.squirt > 0:
            pose = "squirt0" if int(self.squirt * 10) % 2 else "squirt1"
            shake = self.rng.choice((-1, 0, 1))
        elif self.gulp > 0:
            if e < SWALLOW:
                pose = "open"
            elif e < SWALLOW + CHEW:
                pose = "chew0" if int(e * 6) % 2 == 0 else "chew1"
            else:
                pose = "spit" if e < SWALLOW + CHEW + 0.3 else "happy"
        elif incoming:
            pose = "open"
        else:
            pose = "walk0" if int(self.t_anim * 8) % 2 == 0 else "walk1"
        chewing = self.gulp > 0 and SWALLOW <= e < SWALLOW + CHEW
        if chewing:
            self._draw_dna(screen, (e - SWALLOW) / CHEW, front=False)
        for x, size, t in self.splats:                   # puddles under everything
            if t < SPLAT_LIFE - 0.6 or int(t * 10) % 2:
                img = a.puddle[int(size)]
                screen.blit(img, (round(x) - img.get_width() // 2, FLOOR_Y - 2))
        tpos = (round(self.tx) - art.TARGET_W // 2 + shake, round(self.target_top))
        if self.gulp > 0 and e < SWALLOW:               # hands grab the baby and pull it in
            q = max(0.0, (e - GRAB_HOLD) / (SWALLOW - GRAB_HOLD - 0.08))
            q = min(1.0, q * q * (3 - 2 * q))           # ease in and out
            dx = self.held_dx * (1 - q)
            y = art.TARGET_GRAB + (art.TARGET_HOLE - art.TARGET_GRAB) * q
            body, hands = a.held(round(dx * self.tfacing / 2) * 2, round(y / 2) * 2)
            screen.blit(body[self.tfacing], tpos)
            if q < 1:                                   # gone once it's at the opening
                screen.blit(a.baby[0], (round(self.tx + dx) - art.BABY_SIZE // 2,
                                        round(self.target_top + y) - art.BABY_SIZE // 2))
                screen.blit(hands[self.tfacing], tpos)
        else:
            screen.blit(a.target[pose][self.tfacing], tpos)
        if chewing:
            self._draw_dna(screen, (e - SWALLOW) / CHEW, front=True)
        for m in self.men:
            if m.state == "fly":
                img = a.man["jump"][1 if m.vy < -60 else 2 if m.vy < 60 else 3][m.facing]
            elif m.state == "stand":
                img = a.man["idle"][int(m.t * 4) % 4][m.facing]
            else:
                img = a.man["run"][int(m.t * 12) % 4][m.facing]
            screen.blit(img, (round(m.x) - SIZE // 2, round(m.y) - GROUND - 1))

        # baby, with a shadow so you can judge where it'll land
        if b:
            if b.state == "fall":
                w = max(4, 14 - int((FLOOR_Y - b.y) / 10))
                pygame.draw.ellipse(screen, hex_to_rgba(LAB_GRID), (round(b.x) - w // 2, FLOOR_Y + 1, w, 3))
                img = a.baby[int(b.t * 6) % 2]
            else:
                img = a.crying[int(b.t * 6) % 2]
                if b.t > CRY_TIME - 0.4 and int(b.t * 20) % 2:   # blink out
                    img = None
            if img:
                screen.blit(img, (round(b.x) - art.BABY_SIZE // 2, round(b.y) - art.BABY_SIZE // 2))

        # stork
        frame = int(self.flap) % 4
        bob = (0, -1, 0, 1)[frame]
        img = a.stork[self.loaded][frame][self.facing]
        screen.blit(img, (round(self.x) - art.STORK_CENTER[0], round(self.y) - art.STORK_CENTER[1] + bob))

        m = self.fsm
        if m:
            if m.carrying:                                     # the stolen bundle dangles below
                gx, gy = m.grab
                screen.blit(a.baby[int(self.time * 6) % 2], (round(gx) - art.BABY_SIZE // 2, round(gy) - 4))
            img = a.fsm[int(self.time * 8) % art.FSM_FRAMES][1 if m.vx >= 0 else -1]
            screen.blit(img, (round(m.x) - art.FSM_W // 2, round(m.y) - art.FSM_H // 2))

        for x, y, vx, vy, big in self.drops:
            screen.blit(a.drop[int(big)], (round(x) - 3, round(y) - 4))
        for h in self.hearts:
            if h.t >= 0:
                screen.blit(a.heart, (round(h.x + 3 * math.sin(h.t * 9)) - 4, round(h.y) - 4))
        for p in self.popups:
            if p.t < p.life - 0.3 or int(p.t * 20) % 2:
                screen.blit(p.text, (round(p.x) - p.text.get_width() // 2, round(p.y)))

        self._draw_hud(screen)

    def _draw_dna(self, screen: pygame.Surface, progress: float, front: bool) -> None:
        """Helices orbiting the target, spiralling in as the chewing goes on."""
        cx, cy = self.tx, self.target_top + art.TARGET_HOLE - 2
        r = 30 * (1 - 0.65 * progress)
        # orbit speeds up from DNA_SPIN[0] to DNA_SPIN[1] rad/s over the chew
        spin = CHEW * progress * (DNA_SPIN[0] + (DNA_SPIN[1] - DNA_SPIN[0]) * progress / 2)
        for i in range(DNA_STRANDS):
            ang = spin + i * math.tau / DNA_STRANDS
            if (math.sin(ang) > 0) != front:
                continue
            img = self.art.dna[(int(self.time * DNA_TWIST_FPS) + i) % art.DNA_FRAMES]
            x = cx + math.cos(ang) * r
            y = cy + math.sin(ang) * r * 0.35 - 3 * math.sin(self.time * 2 + i)
            screen.blit(img, (round(x) - art.DNA_W // 2, round(y) - art.DNA_H // 2))

    def _draw_hud(self, screen: pygame.Surface) -> None:
        if self.phase == "title":
            self._banner(screen, self.title, [f"DELIVER {NEED} OF {BABIES} BABIES",
                                              "FLY: STICK   DROP: BUTTON",
                                              "PRESS BUTTON TO START" if int(self.time * 2) % 2 == 0 else ""])
            return
        screen.blit(text_surface(f"BABIES LEFT {self.babies_in_play}", LAB_DIM), (6, 6))
        score = text_surface(f"DELIVERED {self.delivered}/{NEED}", LAB_TEXT)
        screen.blit(score, (W - score.get_width() - 6, 6))
        if self.streak:
            streak = text_surface(f"IN A ROW {self.streak}", art.SQUIRT if self.streak >= STREAK else LAB_DIM)
            screen.blit(streak, (6, 14))
        if self.phase == "won":
            self._banner(screen, "SPECIAL DELIVERY!", [f"{self.delivered} BABIES DELIVERED", "PRESS BUTTON"])
        elif self.phase == "lost":
            self._banner(screen, "RETURN TO SENDER", [f"ONLY {self.delivered} OF {NEED} DELIVERED", "PRESS BUTTON"])

    def _banner(self, screen: pygame.Surface, title: str, lines: list[str]) -> None:
        shade = pygame.Surface((W, 64), pygame.SRCALPHA)
        shade.fill((*hex_to_rgba(art.P["city"])[:3], 200))
        screen.blit(shade, (0, 52))
        t = big_text(title, LAB_TEXT)
        screen.blit(t, (W // 2 - t.get_width() // 2, 60))
        for i, line in enumerate(lines):
            if line:
                s = text_surface(line, LAB_DIM)
                screen.blit(s, (W // 2 - s.get_width() // 2, 80 + i * 9))


def autopilot(game: StorkBomber) -> Input:
    """A decent computer player, for demos and smoke tests."""
    inp = Input()
    if game.phase != "play":
        inp.action = game.phase_t > 1.2
        return inp
    bx, by = game.bundle_pos
    fall = max(0.0, game.grab_y - by)
    t = math.sqrt(2 * fall / GRAVITY)
    lead = game.tx + game.tvx * t
    if not TARGET_X[0] <= lead <= TARGET_X[1]:              # it will have bounced off the wall
        lead = 2 * (TARGET_X[0] if lead < TARGET_X[0] else TARGET_X[1]) - lead
    land = bx + game.vx * CARRY * t
    err = lead - land
    inp.x = (err > 6) - (err < -6)
    inp.y = (by < 70) - (by > 80)
    inp.action = game.loaded and game.baby is None and abs(err) < 4 and game.gulp <= 0
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
    run(lambda: StorkBomber(seed=args.seed), "Stork Bomber", scale=args.scale, fullscreen=args.fullscreen,
        autopilot=autopilot if args.demo else None, max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
