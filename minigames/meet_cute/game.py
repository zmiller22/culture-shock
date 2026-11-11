"""Meet Cute: a two-player maze chase. The egg and the sperm start at opposite
ends of the reproductive tract and have to find each other.

    python -m minigames.meet_cute [--fullscreen] [--scale 4] [--demo] [--seed N]

Controls (keyboard, or one arcade stick / gamepad per player):
    P1 EGG      WASD     or the first stick plugged in
    P2 SPERM    ARROWS   or the second stick
    SPACE / ENTER / button 0    start, continue
    ESC / Q                     quit

It's co-op. Both of you eat the nutrients lining the tubes. Once you've eaten
enough between you, the egg is RIPE, and the round is won the moment you two
touch. Bump into each other before that and she isn't ready yet.

The immune system patrols the maze and wants you apart:
    MACROPHAGE   a white blood cell. Chases whoever is closest.
    ANTIBODY     cuts the egg off: aims a few tiles ahead of her.
    SPERMICIDE   cuts the sperm off the same way.
    COPPER IUD   parks itself halfway between you two.
Get caught and you lose a heart and go back to your start. Eat a folic-acid
capsule and for a few seconds they're scared of you, and you can eat them.

You win when you meet. You lose if the hearts run out, or if the clock runs out
first and it all comes out as a period.
"""

from __future__ import annotations

import argparse
import heapq
import math
import random
from dataclasses import dataclass

import pygame

from sprites.canvas import hex_to_rgba
from sprites.palette import LAB_DIM, LAB_TEXT
from sprites.viewer import H, W, text_surface, to_surface

from ..shell import Input, run
from . import art
from .art import F, TILE

# -- tuning ------------------------------------------------------------------------
COLS, ROWS = 39, 21              # tiles; odd so the maze has walls on the edges
OX, OY = (W - COLS * TILE) // 2, H - ROWS * TILE - 1    # where tile (0, 0) sits on screen
TIME_LIMIT = 90.0                # s before it all comes out as a period
RIPE_SHARE = 0.6                 # share of the maze's nutrients the two of you eat before she's ready
LIVES = 3                        # shared hearts
EGG_SPEED, SPERM_SPEED = 5.4, 6.8              # tiles/s. Sperm swim faster, eggs roll.
ENEMY_SPEED, ENEMY_SPEED_MAX = 5.0, 6.4        # they speed up over the round
SCARED_SPEED, EYES_SPEED = 3.0, 12.0
SCARED_TIME, SCARED_FLASH = 6.0, 2.0
RELEASE = (0.0, 3.0, 8.0, 14.0)  # s into the round each enemy leaves the pen
MODES = ((6.0, "scatter"), (18.0, "chase"), (5.0, "scatter"), (999.0, "chase"))
EXTRA_SPAWN = 30.0               # s between extra macrophages once all four are out (0 = never)
EXTRA_MAX = 3
INVULN = 2.0                     # s of blinking after respawning
CAUGHT_FREEZE = 1.0
TOUCH = 0.7                      # tiles: how close counts as touching
POINTS_DOT, POINTS_PILL, POINTS_EAT, POINTS_MEET = 10, 50, 200, 1000
EXTRA_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

PEN = (15, 9, 9, 3)              # x, y, w, h of the pen's inside (tiles); the loop round it lands on odd tiles
PEN_HOME = (19, 10)              # where eaten enemies go to re-form
DOOR = (19, 8)
PEN_EXIT = (19, 7)
EGG_START, SPERM_START = (1, 1), (COLS - 2, ROWS - 2)
TUNNEL_ROWS = (5, 15)

NOT_YET = ["NOT YET!", "SHE'S NOT READY", "TOO SOON!", "EAT MORE!", "SLOW DOWN!"]
CAUGHT = {"macrophage": "ENGULFED!", "antibody": "TAGGED!", "spermicide": "DISSOLVED!", "iud": "BLOCKED!"}
EAT_LINES = ["CHOMP!", "YOINK!", "NOM!", "GET REKT"]


def rgb(c: str) -> tuple[int, int, int]:
    return hex_to_rgba(c)[:3]


def big_text(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


def screen_pos(fx: float, fy: float) -> tuple[float, float]:
    return OX + fx * TILE + TILE / 2, OY + fy * TILE + TILE / 2


# -- the maze ----------------------------------------------------------------------

def make_maze(rng: random.Random) -> list[list[str]]:
    """A left-right mirrored maze with no dead ends, a pen in the middle and two
    wrap-around tunnels. '#' wall, '.' corridor, 'p' pen, '-' pen door."""
    g = [["#"] * COLS for _ in range(ROWS)]
    half = COLS // 2                                  # the middle column, shared by both halves
    cw, ch = half // 2 + 1, ROWS // 2                 # cells in the left half (including the middle column)
    seen = {(0, 0)}
    stack = [(0, 0)]
    g[1][1] = "."
    while stack:                                      # recursive backtracker
        cx, cy = stack[-1]
        opts = [(cx + dx, cy + dy) for dx, dy in EXTRA_DIRS
                if 0 <= cx + dx < cw and 0 <= cy + dy < ch and (cx + dx, cy + dy) not in seen]
        if not opts:
            stack.pop()
            continue
        nx, ny = rng.choice(opts)
        g[2 * ny + 1][2 * nx + 1] = "."
        g[cy + ny + 1][cx + nx + 1] = "."
        seen.add((nx, ny))
        stack.append((nx, ny))
    for y in range(ROWS):                             # mirror the left half onto the right
        for x in range(half):
            g[y][COLS - 1 - x] = g[y][x]

    px, py, pw, ph = PEN                              # the pen, walled, with a loop around it
    for y in range(py - 2, py + ph + 2):
        for x in range(px - 2, px + pw + 2):
            g[y][x] = "."
    for y in range(py - 1, py + ph + 1):
        for x in range(px - 1, px + pw + 1):
            g[y][x] = "#"
    for y in range(py, py + ph):
        for x in range(px, px + pw):
            g[y][x] = "p"
    g[DOOR[1]][DOOR[0]] = "-"

    open_ = lambda x, y: 0 < x < COLS - 1 and 0 < y < ROWS - 1 and g[y][x] == "."
    changed = True
    while changed:                                    # braid: knock through every dead end
        changed = False
        for y in range(1, ROWS - 1):
            for x in range(1, half + 1):
                if g[y][x] != "." or sum(open_(x + dx, y + dy) for dx, dy in EXTRA_DIRS) > 1:
                    continue
                knocks = [(dx, dy) for dx, dy in EXTRA_DIRS
                          if g[y + dy][x + dx] == "#" and open_(x + 2 * dx, y + 2 * dy)
                          and 0 < x + dx < COLS - 1 and 0 < y + dy < ROWS - 1]
                if knocks:
                    dx, dy = rng.choice(knocks)
                    for xx in {x + dx, COLS - 1 - (x + dx)}:
                        g[y + dy][xx] = "."
                    changed = True
    for _ in range(10):                               # and a few extra loops
        x, y = rng.randint(2, half), rng.randint(1, ROWS - 2)
        if g[y][x] == "#" and ((open_(x - 1, y) and open_(x + 1, y)) or (open_(x, y - 1) and open_(x, y + 1))):
            g[y][x] = g[y][COLS - 1 - x] = "."
    for y in TUNNEL_ROWS:
        g[y][0] = g[y][COLS - 1] = "."
        g[y][1] = g[y][COLS - 2] = "."
    return g


# -- things that move around the maze ----------------------------------------------

@dataclass
class Mover:
    fx: float
    fy: float
    speed: float
    dir: tuple[int, int] = (0, 0)
    want: tuple[int, int] = (0, 0)
    anim: float = 0.0

    @property
    def tile(self) -> tuple[int, int]:
        return round(self.fx) % COLS, round(self.fy)

    def at_center(self) -> bool:
        return abs(self.fx - round(self.fx)) < 1e-6 and abs(self.fy - round(self.fy)) < 1e-6

    def place(self, t: tuple[int, int]) -> None:
        self.fx, self.fy = float(t[0]), float(t[1])
        self.dir = self.want = (0, 0)


@dataclass
class Player(Mover):
    kind: str = "egg"
    start: tuple[int, int] = (1, 1)
    invuln: float = 0.0
    face: tuple[int, int] = (1, 0)


@dataclass
class Enemy(Mover):
    kind: str = "macrophage"
    state: str = "pen"           # pen, leave, roam, eyes
    release: float = 0.0
    corner: tuple[int, int] = (0, 0)
    roam_target: tuple[int, int] = (0, 0)
    roam_t: float = 0.0


@dataclass
class Popup:
    surf: pygame.Surface
    x: float
    y: float
    t: float = 0.0
    life: float = 1.0


@dataclass
class Bit:
    x: float
    y: float
    vx: float
    vy: float
    col: tuple
    t: float = 0.0
    life: float = 1.2


class Art:
    """Sprites pre-rendered once and reused across rounds."""

    def __init__(self) -> None:
        self.egg = [to_surface(art.egg(f)) for f in range(4)]
        self.egg_ripe = [to_surface(art.egg_blush(f)) for f in range(4)]
        sperm = [to_surface(art.sperm(f)) for f in range(4)]
        self.sperm = {(1, 0): sperm, (-1, 0): [pygame.transform.flip(s, True, False) for s in sperm],
                      (0, -1): [pygame.transform.rotate(s, 90) for s in sperm],
                      (0, 1): [pygame.transform.rotate(s, -90) for s in sperm]}
        looks = list(EXTRA_DIRS) + [(0, 0)]
        self.enemy = {(k, f, lk): to_surface(art.enemy(k, f, lk)) for k in art.ENEMIES for f in range(2) for lk in looks}
        self.scared = {(f, fl): to_surface(art.scared(f, fl)) for f in range(2) for fl in (False, True)}
        self.eyes = {lk: to_surface(art.eyes_only(lk)) for lk in looks}
        self.nutrient = [to_surface(art.nutrient(f)) for f in range(2)]
        self.folic = [to_surface(art.folic(f)) for f in range(2)]
        self.zygote = {n: [to_surface(art.zygote(n, f)) for f in range(4)] for n in (1, 2, 4, 8)}
        self.heart = to_surface(art.heart())
        self.heart_big = to_surface(art.heart(True))
        self.pop = {c: [to_surface(art.pop(f, c)) for f in range(4)] for c in ("#ff4a6a", "#5ff3ff", "#ffe14d")}
        self.door = to_surface(art.pen_door(TILE))
        self.overlay = pygame.Surface((W, H), pygame.SRCALPHA)


_ART: Art | None = None


class MeetCute:
    title = "MEET CUTE"
    players_needed = 2

    def __init__(self, seed: int | None = None, show_title: bool = True) -> None:
        global _ART
        _ART = _ART or Art()
        self.art = _ART
        self.rng = random.Random(seed)
        self.grid = make_maze(self.rng)
        self.maze = to_surface(art.maze(["".join(r) for r in self.grid], OX, OY, W, H, self.rng.randrange(1 << 30)))
        self.dots = {(x, y) for y in range(ROWS) for x in range(COLS) if self.grid[y][x] == "."}
        self.dots -= {EGG_START, SPERM_START, PEN_EXIT, (0, TUNNEL_ROWS[0]), (COLS - 1, TUNNEL_ROWS[0]),
                      (0, TUNNEL_ROWS[1]), (COLS - 1, TUNNEL_ROWS[1])}
        self.pills = set()
        for corner in ((3, 3), (COLS - 4, 3), (3, ROWS - 4), (COLS - 4, ROWS - 4)):
            t = min(self.dots, key=lambda d: math.dist(d, corner))
            self.pills.add(t)
            self.dots.discard(t)

        self.egg = Player(*map(float, EGG_START), EGG_SPEED, kind="egg", start=EGG_START)
        self.sperm = Player(*map(float, SPERM_START), SPERM_SPEED, kind="sperm", start=SPERM_START, face=(-1, 0))
        self.players = (self.egg, self.sperm)
        px, py, pw, ph = PEN
        spots = [(px + 2, py + 1), (px + 4, py + 1), (px + 6, py + 1), (px + 4, py + 2)]
        corners = [(1, -3), (COLS - 2, -3), (1, ROWS + 2), (COLS - 2, ROWS + 2)]
        self.enemies = [Enemy(*map(float, spots[i]), ENEMY_SPEED, kind=k, release=RELEASE[i], corner=corners[i])
                        for i, k in enumerate(art.ENEMIES)]
        self.extra_t = 0.0

        self.need = round(len(self.dots) * RIPE_SHARE)
        self.eaten = 0
        self.score = 0
        self.lives = LIVES
        self.clock = 0.0             # s into the round (only runs while playing)
        self.scared = 0.0
        self.eat_chain = 0
        self.not_yet_cd = 0.0
        self.popups: list[Popup] = []
        self.bits: list[Bit] = []
        self.pops: list[tuple[float, float, str, float]] = []
        self.phase = "title" if show_title else "ready"
        self.phase_t = 0.0
        self.lose_reason = ""
        self.meet_at = (0.0, 0.0)
        self.result: str | None = None
        self.done = False

    # -- helpers -------------------------------------------------------------------
    @property
    def ripe(self) -> bool:
        return self.eaten >= self.need

    def mode(self) -> str:
        t = self.clock
        for length, mode in MODES:
            if t < length:
                return mode
            t -= length
        return "chase"

    def passable(self, t: tuple[int, int], who: Mover) -> bool:
        x, y = t
        if not 0 <= y < ROWS:
            return False
        x %= COLS
        c = self.grid[y][x]
        if c == ".":
            return True
        if isinstance(who, Enemy) and who.state in ("pen", "leave", "eyes"):
            return c in ".p-"
        return False

    def _enter(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _popup(self, text: str, x: float, y: float, color: str = LAB_TEXT, big: bool = False, life: float = 1.0) -> None:
        surf = big_text(text, color) if big else text_surface(text, color)
        x = max(surf.get_width() / 2 + 2, min(W - surf.get_width() / 2 - 2, x))
        self.popups.append(Popup(surf, x, y, life=life))

    def _burst(self, x: float, y: float, cols: list[str], n: int = 14, speed: float = 60) -> None:
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(0.3, 1) * speed
            self.bits.append(Bit(x, y, math.cos(a) * v, math.sin(a) * v, rgb(self.rng.choice(cols)),
                                 life=self.rng.uniform(0.6, 1.3)))

    # -- movement ------------------------------------------------------------------
    def _move(self, m: Mover, dist: float, choose=None) -> None:
        """Slide along the corridors. At each tile centre turn toward `m.want` if it's
        open (or ask `choose` for a direction), and stop at walls."""
        for _ in range(8):
            if dist <= 1e-9:
                return
            if m.dir != (0, 0) and m.want == (-m.dir[0], -m.dir[1]):
                m.dir = m.want                                 # reverse any time
            if m.at_center():
                m.fx, m.fy = float(round(m.fx)), float(round(m.fy))
                tx, ty = round(m.fx), round(m.fy)
                if choose:
                    m.dir = choose(m)
                elif m.want != (0, 0) and self.passable((tx + m.want[0], ty + m.want[1]), m):
                    m.dir = m.want
                if m.dir == (0, 0) or not self.passable((tx + m.dir[0], ty + m.dir[1]), m):
                    m.dir = (0, 0)
                    return
            pos = m.fx if m.dir[0] else m.fy
            step = m.dir[0] or m.dir[1]
            nxt = math.floor(pos + 1e-6) + 1 if step > 0 else math.ceil(pos - 1e-6) - 1
            gap = abs(nxt - pos)
            go = min(dist, gap)
            if m.dir[0]:
                m.fx += step * go
            else:
                m.fy += step * go
            if go >= gap - 1e-9:
                if m.dir[0]:
                    m.fx = float(nxt)
                else:
                    m.fy = float(nxt)
            dist -= go
            m.anim += go
            if m.fx < -0.5:
                m.fx += COLS
            elif m.fx > COLS - 0.5:
                m.fx -= COLS

    def _steer(self, p: Player, inp: Input) -> None:
        """Held stick -> wanted direction. On a diagonal, prefer the turn."""
        x, y = inp.x, inp.y
        if x and y:
            p.want = (0, y) if p.dir[0] else (x, 0)
            tx, ty = round(p.fx), round(p.fy)
            if not self.passable((tx + p.want[0], ty + p.want[1]), p):
                p.want = (x, 0) if p.want[1] else (0, y)
        elif x or y:
            p.want = (x, y)
        if p.dir != (0, 0):
            p.face = p.dir

    def _enemy_target(self, e: Enemy) -> tuple[float, float]:
        if e.state == "leave":
            return PEN_EXIT
        if e.state == "eyes":
            return PEN_HOME
        if self.mode() == "scatter":
            return e.corner
        live = [p for p in self.players if p.invuln <= 0] or list(self.players)
        if e.kind == "macrophage":
            p = min(live, key=lambda p: math.dist((p.fx, p.fy), (e.fx, e.fy)))
            return p.fx, p.fy
        if e.kind in ("antibody", "spermicide"):
            p = self.egg if e.kind == "antibody" else self.sperm
            return p.fx + p.face[0] * 4, p.fy + p.face[1] * 4
        return (self.egg.fx + self.sperm.fx) / 2, (self.egg.fy + self.sperm.fy) / 2   # the IUD: in the way

    def _choose(self, e: Enemy) -> tuple[int, int]:
        """Called at every tile centre an enemy reaches: pick where to go next."""
        tx, ty = round(e.fx), round(e.fy)
        if e.state == "leave" and self.grid[ty][tx % COLS] == ".":
            e.state = "roam"                               # out of the pen
        elif e.state == "eyes" and (tx, ty) == PEN_HOME:
            e.state = "leave"                              # re-formed; back out
        back = (-e.dir[0], -e.dir[1])
        opts = [d for d in EXTRA_DIRS if self.passable((tx + d[0], ty + d[1]), e)]
        if not opts:
            return (0, 0)
        if len(opts) > 1 and back in opts:
            opts.remove(back)
        if e.state == "roam" and self.scared > 0:
            return self.rng.choice(opts)
        gx, gy = self._enemy_target(e)
        return min(opts, key=lambda d: (math.dist((tx + d[0], ty + d[1]), (gx, gy)), self.rng.random()))

    # -- update --------------------------------------------------------------------
    def update(self, dt: float, inp: Input) -> None:
        self.phase_t += dt
        self._update_fx(dt)
        if self.phase == "title":
            if inp.action or any(p.action for p in inp.players):
                self._enter("ready")
        elif self.phase == "ready":
            if self.phase_t >= 1.6:
                self._enter("play")
        elif self.phase == "play":
            self._update_play(dt, inp)
        elif self.phase == "caught":
            if self.phase_t >= CAUGHT_FREEZE:
                if self.lives <= 0:
                    self.lose_reason = "lives"
                    self.result = "lose"
                    self._enter("lost")
                else:
                    self._enter("play")
        elif self.phase == "won":
            if self.phase_t > 3.2 and int(self.phase_t * 10) % 3 == 0:
                self._burst(*self.meet_at, ["#ff6a9a", "#5ff3ff", "#ffe14d", "#ffffff"], n=3, speed=90)
            if self.phase_t >= 4.5:
                self._enter("end")
        elif self.phase == "lost":
            if self.phase_t >= 3.0:
                self._enter("end")
        elif self.phase == "end":
            if self.phase_t > 0.6 and (inp.action or any(p.action for p in inp.players)):
                self.done = True

    def _update_play(self, dt: float, inp: Input) -> None:
        self.clock += dt
        if self.clock >= TIME_LIMIT:
            self.lose_reason = "time"
            self.result = "lose"
            self._enter("lost")
            return
        pads = inp.players or (inp, Input())
        for p, pin in zip(self.players, pads):
            self._steer(p, pin)
            self._move(p, p.speed * dt)
            p.invuln = max(0.0, p.invuln - dt)
            self._eat(p)

        self.scared = max(0.0, self.scared - dt)
        if self.scared == 0:
            self.eat_chain = 0
        speed = ENEMY_SPEED + (ENEMY_SPEED_MAX - ENEMY_SPEED) * min(1.0, self.clock / TIME_LIMIT)
        if self.ripe:
            speed += 0.4
        if EXTRA_SPAWN and self.clock > RELEASE[-1] and len(self.enemies) < len(art.ENEMIES) + EXTRA_MAX:
            self.extra_t += dt
            if self.extra_t >= EXTRA_SPAWN:
                self.extra_t = 0.0
                self.enemies.append(Enemy(*map(float, PEN_HOME), speed, kind="macrophage",
                                          release=self.clock, corner=(COLS // 2, -3)))
                self._popup("MORE WHITE CELLS!", W / 2, OY + PEN[1] * TILE - 6, "#f0eef8")
        for e in self.enemies:
            if e.state == "pen":
                e.anim += dt * 3
                if self.clock >= e.release:
                    e.state = "leave"
                continue
            e.speed = (EYES_SPEED if e.state == "eyes" else
                       SCARED_SPEED if self.scared > 0 and e.state == "roam" else speed)
            self._move(e, e.speed * dt, self._choose)
        self._collide()
        self.not_yet_cd = max(0.0, self.not_yet_cd - dt)

    def _eat(self, p: Player) -> None:
        t = p.tile
        if t in self.dots:
            self.dots.discard(t)
            was_ripe = self.ripe
            self.eaten += 1
            self.score += POINTS_DOT
            if self.ripe and not was_ripe:
                x, y = screen_pos(self.egg.fx, self.egg.fy)
                self._popup("SHE'S RIPE!", x, y - 10, "#ff9ac8", big=True, life=1.6)
                self._burst(x, y, ["#ff6a9a", "#ffc0cc", "#ffe14d"], n=20)
        if t in self.pills:
            self.pills.discard(t)
            self.score += POINTS_PILL
            self.scared = SCARED_TIME
            self.eat_chain = 0
            for e in self.enemies:
                if e.state == "roam":
                    e.dir = (-e.dir[0], -e.dir[1])
            x, y = screen_pos(p.fx, p.fy)
            self._popup("FOLIC ACID!", x, y - 10, "#ffe14d")

    def _collide(self) -> None:
        e_, s_ = self.egg, self.sperm
        if math.dist((e_.fx, e_.fy), (s_.fx, s_.fy)) < TOUCH and abs(e_.fx - s_.fx) < COLS / 2:
            if self.ripe:
                self.meet_at = screen_pos((e_.fx + s_.fx) / 2, (e_.fy + s_.fy) / 2)
                self.score += POINTS_MEET + int(TIME_LIMIT - self.clock) * 20
                self.result = "win"
                self._enter("won")
                return
            if self.not_yet_cd <= 0:
                x, y = screen_pos(e_.fx, e_.fy)
                self._popup(self.rng.choice(NOT_YET), x, y - 10, "#ff9ac8")
                self.not_yet_cd = 1.5
                for p in self.players:                # bounce off each other
                    if p.dir != (0, 0):
                        p.dir = p.want = (-p.dir[0], -p.dir[1])
        for e in self.enemies:
            if e.state != "roam":
                continue
            for p in self.players:
                if math.dist((e.fx, e.fy), (p.fx, p.fy)) >= TOUCH or abs(e.fx - p.fx) > COLS / 2:
                    continue
                x, y = screen_pos(p.fx, p.fy)
                if self.scared > 0:
                    e.state = "eyes"
                    pts = POINTS_EAT * 2 ** self.eat_chain
                    self.eat_chain += 1
                    self.score += pts
                    self.pops.append((x, y, "#5ff3ff", 0.0))
                    self._popup(f"{self.rng.choice(EAT_LINES)} {pts}", x, y - 10, "#5ff3ff")
                elif p.invuln <= 0:
                    self._caught(p, e)
                    return

    def _caught(self, p: Player, e: Enemy) -> None:
        x, y = screen_pos(p.fx, p.fy)
        self.lives -= 1
        self.pops.append((x, y, "#ff4a6a", 0.0))
        self._burst(x, y, ["#ff4a6a", "#ffffff", "#ffc0cc"])
        self._popup(CAUGHT[e.kind], x, y - 10, "#ff4a6a", big=True)
        p.place(p.start)
        p.invuln = INVULN + CAUGHT_FREEZE
        self._enter("caught")

    def _update_fx(self, dt: float) -> None:
        for pu in self.popups:
            pu.t += dt
        self.popups = [pu for pu in self.popups if pu.t < pu.life]
        for b in self.bits:
            b.t += dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.vy += 40 * dt
        self.bits = [b for b in self.bits if b.t < b.life]
        self.pops = [(x, y, c, t + dt) for x, y, c, t in self.pops if t + dt < 0.4]

    # -- draw ----------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        t = pygame.time.get_ticks() / 1000
        screen.fill(rgb(F["void"]))
        pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        screen.fill((26 + int(10 * pulse), 4, 16 + int(4 * pulse)), (OX, OY, COLS * TILE, ROWS * TILE))
        screen.blit(self.maze, (0, 0))
        screen.blit(self.art.door, (OX + DOOR[0] * TILE, OY + DOOR[1] * TILE + 3))

        blink = int(t * 4) % 2
        for x, y in self.dots:
            sx, sy = screen_pos(x, y)
            screen.blit(self.art.nutrient[(x + y + int(t * 3)) % 2], (sx - 1, sy - 1))
        for x, y in self.pills:
            sx, sy = screen_pos(x, y)
            screen.blit(self.art.folic[blink], (sx - 5, sy - 3 + (blink and -1)))

        if self.phase not in ("won", "end") or self.result != "win":
            self._draw_enemies(screen, t)
            self._draw_players(screen, t)
        else:
            self._draw_meet(screen, t)

        for x, y, c, pt in self.pops:
            f = min(3, int(pt / 0.1))
            screen.blit(self.art.pop[c][f], (x - 8, y - 8))
        for b in self.bits:
            screen.fill(b.col, (int(b.x), int(b.y), 2, 2))
        for pu in self.popups:
            k = pu.t / pu.life
            s = pu.surf
            if k > 0.7:
                s = s.copy()
                s.set_alpha(int(255 * (1 - (k - 0.7) / 0.3)))
            screen.blit(s, (pu.x - s.get_width() / 2, pu.y - 12 * k - s.get_height() / 2))

        if self.phase == "lost" or (self.phase == "end" and self.result == "lose"):
            self._draw_loss(screen)
        self._draw_hud(screen, t)

        if self.phase == "title":
            self._banner(screen, "MEET CUTE", ["P1 EGG: WASD OR STICK 1     P2 SPERM: ARROWS OR STICK 2",
                                               f"EAT {self.need} NUTRIENTS BETWEEN YOU TO RIPEN THE EGG",
                                               "THEN FIND EACH OTHER. DODGE THE IMMUNE SYSTEM!",
                                               "", "PRESS START" if blink else ""])
        elif self.phase == "ready":
            s = big_text("READY..." if self.phase_t < 1.0 else "GO!", "#ffe14d")
            screen.blit(s, (W / 2 - s.get_width() / 2, OY + (PEN[1] + ROWS) // 2 * TILE + 2))
        elif self.phase == "end":
            if self.result == "win":
                self._banner(screen, "IT'S CONCEPTION!", [f"MET WITH {int(TIME_LIMIT - self.clock)}S TO SPARE",
                                                         f"SCORE {self.score}", "", "PRESS START" if blink else ""])
            elif self.lose_reason == "time":
                self._banner(screen, "TIME'S UP. PERIOD.", ["THE EGG WAITED. NOBODY CAME.",
                                                           f"SCORE {self.score}", "", "PRESS START" if blink else ""])
            else:
                self._banner(screen, "MISSED CONNECTION", ["THE IMMUNE SYSTEM WINS THIS ONE.",
                                                          f"SCORE {self.score}", "", "PRESS START" if blink else ""])

    def _draw_players(self, screen: pygame.Surface, t: float) -> None:
        for p in self.players:
            if p.invuln > 0 and int(t * 12) % 2 and self.phase == "play":
                continue
            if self.phase == "caught" and p.invuln > INVULN:
                continue                              # still off screen after getting caught
            x, y = screen_pos(p.fx, p.fy)
            if p.kind == "egg":
                frames = self.art.egg_ripe if self.ripe else self.art.egg
                f = int(p.anim * 2) % 4
                if self.ripe:                         # a glow when she's ready
                    r = 8 + int(1.5 * math.sin(t * 6))
                    glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (255, 120, 170, 70), (r, r), r)
                    screen.blit(glow, (x - r, y - r))
                s = frames[f]
            else:
                f = int(t * 10 if p.dir != (0, 0) else t * 4) % 4
                s = self.art.sperm[p.face][f]
            screen.blit(s, (round(x - s.get_width() / 2), round(y - s.get_height() / 2)))

    def _draw_enemies(self, screen: pygame.Surface, t: float) -> None:
        for e in self.enemies:
            x, y = screen_pos(e.fx, e.fy)
            if e.state == "pen":
                y += math.sin(e.anim * 2) * 2
            f = int(t * 5) % 2
            if e.state == "eyes":
                s = self.art.eyes[e.dir]
            elif self.scared > 0 and e.state == "roam":
                s = self.art.scared[(f, self.scared < SCARED_FLASH and int(t * 6) % 2 == 0)]
            else:
                s = self.art.enemy[(e.kind, f, e.dir)]
            screen.blit(s, (round(x - s.get_width() / 2), round(y - s.get_height() / 2)))

    def _draw_meet(self, screen: pygame.Surface, t: float) -> None:
        x, y = self.meet_at
        k = self.phase_t if self.phase == "won" else 99
        if k < 1.0:                                   # the sperm burrows in
            s = self.art.egg_ripe[int(t * 8) % 4]
            screen.blit(s, (x - s.get_width() / 2, y - s.get_height() / 2))
            sp = self.art.sperm[(0, 1)][int(t * 14) % 4]
            screen.blit(sp, (x - sp.get_width() / 2, y - 14 + k * 9 - sp.get_height() / 2))
            return
        cells = 1 if k < 1.8 else 2 if k < 2.5 else 4 if k < 3.2 else 8
        s = self.art.zygote[cells][int(t * 4) % 4]
        screen.blit(s, (x - s.get_width() / 2, y - s.get_height() / 2))
        for i in range(6):                            # hearts floating up around it
            a = i * math.tau / 6 + t * 1.2
            hy = y - 12 - ((t * 18 + i * 9) % 30)
            screen.blit(self.art.heart_big, (x + math.cos(a) * 18 - 3, hy))

    def _draw_loss(self, screen: pygame.Surface) -> None:
        if self.lose_reason != "time":
            return
        k = min(1.0, self.phase_t / 2.5) if self.phase == "lost" else 1.0     # the tide comes in
        top = H - int((H - OY + 10) * k)
        t = pygame.time.get_ticks() / 1000
        tide = self.art.overlay
        tide.fill((0, 0, 0, 0))
        for x in range(0, W, 2):
            wy = top + int(3 * math.sin(x * 0.12 + t * 4))
            pygame.draw.rect(tide, (150, 10, 30, 215), (x, wy, 2, H - wy))
            tide.fill((210, 40, 60, 230), (x, wy, 2, 1))
        screen.blit(tide, (0, 0))

    def _draw_hud(self, screen: pygame.Surface, t: float) -> None:
        screen.fill(rgb(F["void"]), (0, 0, W, OY))
        egg = self.art.egg_ripe[0] if self.ripe else self.art.egg[0]
        small = pygame.transform.scale(egg, (9, 9))
        screen.blit(small, (3, 1))
        label = "RIPE!" if self.ripe else "RIPENESS"
        screen.blit(text_surface(label, "#ff9ac8" if self.ripe and int(t * 4) % 2 else LAB_DIM), (14, 3))
        bx, bw = 52, 50
        screen.fill(rgb(F["deep"]), (bx, 3, bw, 5))
        fill = int(bw * min(1.0, self.eaten / self.need))
        screen.fill(rgb("#ff6a9a" if self.ripe else "#ffe14d"), (bx, 3, fill, 5))
        pygame.draw.rect(screen, rgb(F["light"]), (bx - 1, 2, bw + 2, 7), 1)

        left = max(0.0, TIME_LIMIT - self.clock)
        col = "#ff4a6a" if left < 15 and int(t * 4) % 2 else LAB_TEXT
        s = big_text(f"{int(left // 60)}:{int(left % 60):02d}", col, 1)
        screen.blit(s, (W // 2 - s.get_width() // 2, 3))

        s = text_surface(f"{self.score}", LAB_TEXT)
        screen.blit(s, (W - 4 - s.get_width(), 3))
        for i in range(self.lives):
            screen.blit(self.art.heart, (W - 34 - s.get_width() + i * 7, 3))

    def _banner(self, screen: pygame.Surface, title: str, lines: list[str]) -> None:
        h = 24 + 9 * len(lines)
        top = H // 2 - h // 2
        if self.result == "win":                      # keep clear of the zygote
            top = OY + 4 if self.meet_at[1] > H / 2 else H - h - 4
        shade = pygame.Surface((W, h), pygame.SRCALPHA)
        shade.fill((*rgb(F["deep"]), 225))
        screen.blit(shade, (0, top))
        tt = big_text(title, F["hi"])
        screen.blit(tt, (W // 2 - tt.get_width() // 2, top + 5))
        for i, line in enumerate(lines):
            if line:
                s = text_surface(line, LAB_TEXT if i == len(lines) - 1 else LAB_DIM)
                screen.blit(s, (W // 2 - s.get_width() // 2, top + 21 + i * 9))


# -- the computer plays both ---------------------------------------------------------

def _route(game: MeetCute, p: Player, goal) -> tuple[int, int]:
    """First step of the cheapest path from `p` to any tile where goal(tile) holds,
    steering well clear of enemies that aren't scared."""
    danger = set()
    for e in game.enemies:
        if e.state == "roam" and game.scared <= 0:
            ex, ey = round(e.fx), round(e.fy)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    danger.add(((ex + dx) % COLS, ey + dy))
    start = p.tile
    if goal(start) and not p.at_center():             # finish the step onto it first
        return (round(p.fx) > p.fx) - (round(p.fx) < p.fx), (round(p.fy) > p.fy) - (round(p.fy) < p.fy)
    best = {start: 0}
    heap = [(0, start, (0, 0))]
    while heap:
        cost, t, first = heapq.heappop(heap)
        if cost > best.get(t, 1e9):
            continue
        if t != start and goal(t):
            return first
        for d in EXTRA_DIRS:
            n = ((t[0] + d[0]) % COLS, t[1] + d[1])
            if not game.passable(n, p):
                continue
            c = cost + 1 + (25 if n in danger else 0)
            if c < best.get(n, 1e9):
                best[n] = c
                heapq.heappush(heap, (c, n, first if t != start else d))
    return p.dir


def autopilot(game: MeetCute) -> Input:
    if game.phase in ("title", "end"):
        act = game.phase_t > 0.8
        return Input(action=act, players=(Input(action=act), Input()))
    pads = []
    for p, other in ((game.egg, game.sperm), (game.sperm, game.egg)):
        if game.ripe:
            goal = lambda t, o=other: t == o.tile
        else:
            goal = lambda t: t in game.dots or t in game.pills
        dx, dy = _route(game, p, goal)
        pads.append(Input(dx, dy))
    return Input(players=tuple(pads))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--demo", action="store_true", help="let the computer play both sides")
    ap.add_argument("--seed", type=int, help="same seed, same maze")
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()
    run(lambda: MeetCute(seed=args.seed), "Meet Cute", scale=args.scale, fullscreen=args.fullscreen,
        autopilot=autopilot if args.demo else None, max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
