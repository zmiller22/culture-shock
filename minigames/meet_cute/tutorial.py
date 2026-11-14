"""Meet Cute's how-to-play pages. They play on a tiny maze, drawn at 1x and blown
up 2x so the egg and the sperm read from across the room. Most are try-it pages:
P1 steers the egg and P2 the sperm round the little maze, with the game's own
speeds and cornering."""

from __future__ import annotations

import math

import pygame

from sprites.viewer import text_surface

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, caption, loop
from . import art
from .art import TILE

GRID = ["##############",
        "#............#",
        "#.##.####.##.#",
        "#.##.####.##.#",
        "#............#",
        "##############"]
OX, OY = 3, 2                       # tile (0, 0), on the half-size surface
RING = [(1, 1), (12, 1), (12, 4), (1, 4)]    # the corridor loop, in tiles (clockwise)
PERIM = 2 * (11 + 3)
EGG_AT, SPERM_AT = (1, 1), (12, 4)  # where they start, in opposite corners like the real maze
MOVED = 1.5                         # tiles each has to swim on the first page
FOOD = [(4, 1), (8, 1), (12, 2), (9, 2), (4, 3), (1, 3), (5, 4), (9, 4)]   # the nutrients on the eating page


def at(s: float) -> tuple[float, float, int, int]:
    """Tile position s tiles clockwise round the loop from the top-left, and the heading."""
    s %= PERIM
    for (ax, ay), (bx, by) in zip(RING, RING[1:] + RING[:1]):
        n = abs(bx - ax) + abs(by - ay)
        if s <= n:
            dx, dy = (bx > ax) - (bx < ax), (by > ay) - (by < ay)
            return ax + dx * s, ay + dy * s, dx, dy
        s -= n
    return RING[0][0], RING[0][1], 1, 0


def px(tx: float, ty: float) -> tuple[float, float]:
    return OX + tx * TILE + TILE / 2, OY + ty * TILE + TILE / 2


def make(a) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""
    from .game import PLAYER_HEX, TOUCH, EGG_SPEED, SPERM_SPEED, MeetCute, Player
    from ..shell import Input

    half = pygame.Surface((DEMO_W // 2, DEMO_H // 2))
    walls = pygame.image.frombytes(*_maze_bytes(half.get_size()))

    def floor() -> None:
        half.fill((16, 2, 10))
        half.fill((31, 4, 18), (OX, OY, len(GRID[0]) * TILE, len(GRID) * TILE))
        half.blit(walls, (0, 0))

    def blit(img: pygame.Surface, tx: float, ty: float, dy: float = 0) -> None:
        x, y = px(tx, ty)
        half.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() / 2 + dy)))

    def egg(tx: float, ty: float, t: float, ripe: bool = False) -> None:
        blit((a.egg_ripe if ripe else a.egg)[int(t * 8) % 4], tx, ty)

    def sperm(tx: float, ty: float, d: tuple[int, int], t: float) -> None:
        blit(a.sperm[d if d != (0, 0) else (-1, 0)][int(t * 12) % 4], tx, ty)

    def done(s: pygame.Surface) -> None:
        pygame.transform.scale(half, s.get_size(), s)

    band = pygame.Surface((DEMO_W, 26), pygame.SRCALPHA)
    band.fill((16, 2, 10, 190))

    def hush(s: pygame.Surface) -> None:
        """Darken a strip behind the cheer, so it reads over the pink walls."""
        s.blit(band, (0, DEMO_H // 2 - 15))

    # 3. dodge the contraception; a folic acid capsule turns the tables
    CAP, TURN = 8.0, 2.0                                     # capsule at s=8; the egg gets there at t=2

    def dodge(s: pygame.Surface, t: float):
        t = loop(t, 5.5) * 5.5
        floor()
        for d in [(x, y) for y, row in enumerate(GRID) for x, ch in enumerate(row) if ch == "."]:
            if not _arc(d) <= min(t, TURN) * 4:
                blit(a.nutrient[(d[0] + d[1] + int(t * 3)) % 2], *d)
        if t < TURN:
            se, sc, scared = t * 4, t * 4 - 3.5, False
        else:
            u = t - TURN
            se, sc, scared = CAP - 4 * u, CAP - 3.5 - 1.6 * u, True
        caught = scared and se - sc <= 0.5
        if not t >= TURN:
            blit(a.folic[int(t * 4) % 2], *at(CAP)[:2])
        ex, ey, edx, edy = at(se)
        cx, cy, cdx, cdy = at(sc)
        if not caught:
            if scared:
                blit(a.scared[(int(t * 5) % 2, t - TURN > 1.0 and int(t * 8) % 2 == 0)], cx, cy)
            else:
                blit(a.enemy[("condom", int(t * 5) % 2, (cdx, cdy))], cx, cy)
        elif t - TURN < 2.8:
            blit(a.eyes[(-1, 0)], cx - (t - TURN - 1.0) * 8, cy)
        egg(ex, ey, t)
        done(s)
        if TURN <= t < TURN + 1.0:
            caption(s, "SCARED!", px(cx, cy)[0] * 2, 6, "#5ff3ff")
        if caught and t - TURN < 2.6:
            caption(s, "CHOMP!", px(ex, ey)[0] * 2 + 20, 6, "#ffe14d")
        heading = (edx, edy) if t < TURN else (-edx, -edy)
        return [(*heading, False), (0, 0, False)]

    # -- try it --------------------------------------------------------------------------
    class Box:
        """The tiny maze, driven by the game's own steering and corridor sliding."""
        passable = staticmethod(lambda t, who: 0 <= t[1] < len(GRID) and 0 <= t[0] < len(GRID[0])
                                and GRID[t[1]][t[0]] == ".")
        _move = MeetCute._move
        _steer = MeetCute._steer

    box = Box()

    class Swim:
        """Both of them loose in the tiny maze; done once each has swum a bit."""
        cheer = "BOTH READY!"
        ripe = False

        def __init__(self) -> None:
            self.egg = Player(*map(float, EGG_AT), EGG_SPEED, kind="egg", start=EGG_AT)
            self.sperm = Player(*map(float, SPERM_AT), SPERM_SPEED, kind="sperm", start=SPERM_AT, face=(-1, 0))
            self.swum = [0.0, 0.0]
            self.done = False

        def swim(self, dt: float, inp) -> None:
            pads = inp.players or (inp, Input())
            for i, (p, pin) in enumerate(zip((self.egg, self.sperm), pads)):
                box._steer(p, pin)
                before = p.anim
                box._move(p, p.speed * dt)
                if pin.x or pin.y:
                    self.swum[i] += p.anim - before

        def update(self, dt: float, inp) -> None:
            self.swim(dt, inp)
            self.done = min(self.swum) >= MOVED

        def players(self, t: float) -> None:
            e, s = self.egg, self.sperm
            sperm(s.fx, s.fy, s.face, t)
            blit((a.egg_ripe if self.ripe else a.egg)[int(e.anim * 2) % 4], e.fx, e.fy)

        def tag(self, s: pygame.Surface, p, label: str, ready: bool, t: float) -> None:
            """P1 / P2 over each of them, or READY! with a tick once they've swum."""
            x, y = px(p.fx, p.fy)
            x, y = x * 2, y * 2 - 22 + (0 if ready else round(math.sin(t * 5)))
            text = "READY!" if ready else label
            col = PLAYER_HEX[p.kind]
            caption(s, text, x + 1, y + 1, "#140c1c")         # a shadow, so it reads over the walls
            caption(s, text, x, y, col)
            if ready:
                x0 = x - text_surface(text, col).get_width() / 2 - 3
                tick = [(x0 - 6, y + 2), (x0 - 4, y + 4), (x0, y)]
                pygame.draw.lines(s, (20, 12, 28), False, [(i + 1, j + 1) for i, j in tick], 2)
                pygame.draw.lines(s, col, False, tick, 2)

        def draw(self, s: pygame.Surface, t: float):
            floor()
            self.players(t)
            done(s)
            self.tag(s, self.egg, "P1", self.swum[0] >= MOVED, t)
            self.tag(s, self.sperm, "P2", self.swum[1] >= MOVED, t)
            if self.done:
                hush(s)
            k = loop(t, 2.4)                                  # the icons: egg right then down, sperm left then up
            return [(1, 0, False) if k < 0.5 else (0, 1, False), (-1, 0, False) if k < 0.5 else (0, -1, False)]

    class Feast(Swim):
        """A few nutrients round the maze; eat them all, between you, and she's ripe."""
        cheer = "SHE'S RIPE!"

        def __init__(self) -> None:
            super().__init__()
            self.food = set(FOOD)

        @property
        def ripe(self) -> bool:
            return not self.food

        def update(self, dt: float, inp) -> None:
            self.swim(dt, inp)
            self.food -= {self.egg.tile, self.sperm.tile}
            self.done = self.ripe

        def draw(self, s: pygame.Surface, t: float):
            floor()
            for d in self.food:
                blit(a.nutrient[(d[0] + d[1] + int(t * 3)) % 2], *d)
            self.players(t)
            done(s)
            share = 1 - len(self.food) / len(FOOD)
            pygame.draw.rect(s, (20, 12, 28), (DEMO_W // 2 - 40, 4, 80, 7))     # the ripeness meter
            pygame.draw.rect(s, (255, 106, 138), (DEMO_W // 2 - 39, 5, round(78 * share), 5))
            caption(s, "RIPE!" if self.ripe else "RIPENESS", DEMO_W // 2, 13,
                    "#ff6a8a" if self.ripe and int(t * 4) % 2 else "#f4f4f4")
            if self.done:
                hush(s)
            k = loop(t, 3.0)                                  # the icons: egg along the top, sperm along the bottom
            return [(1, 0, False) if k < 0.6 else (0, 1, False), (-1, 0, False) if k < 0.6 else (0, -1, False)]

    class Meet(Swim):
        """She's ripe from the start: swim into each other and it's conception."""
        cheer = "IT'S CONCEPTION!"
        ripe = True

        def __init__(self) -> None:
            super().__init__()
            self.met_t: float | None = None                   # page time they touched, for the zygote
            self.met_at = (0.0, 0.0)

        def update(self, dt: float, inp) -> None:
            self.swim(dt, inp)
            e, s = self.egg, self.sperm
            if math.dist((e.fx, e.fy), (s.fx, s.fy)) < TOUCH:
                self.met_at = ((e.fx + s.fx) / 2, (e.fy + s.fy) / 2)
                self.done = True

        def draw(self, s: pygame.Surface, t: float):
            floor()
            if not self.done:
                self.players(t)
                done(s)
                k = loop(t, 3.0)                              # the icons: egg down then right, sperm left
                return [(0, 1, False) if k < 0.35 else (1, 0, False), (-1, 0, False)]
            if self.met_t is None:
                self.met_t = t
            u = t - self.met_t
            blit(a.zygote[min(8, 2 ** int(u * 3))][int(t * 6) % 4], *self.met_at, -min(6, u * 8))
            done(s)
            hush(s)
            cx, cy = px(*self.met_at)
            for i in range(8):                                # hearts bursting out
                ang = i * math.tau / 8 + t
                r = u * 70
                s.blit(a.heart, (round(cx * 2 + math.cos(ang) * r), round(cy * 2 + math.sin(ang) * r * 0.6)))
            return [(0, 0, False), (0, 0, False)]

    both = ("stick", "stick2")
    return Tutorial(
        "MEET CUTE", "LIFE STARTS WHEN TWO CELLS FALL IN LOVE.",
        [
            Page(("P1: MOVE STICK 1 TO STEER THE EGG", "P2: MOVE STICK 2 TO STEER THE SPERM"),
                 controls=both, trial=Swim),
            Page(("IT'S CO-OP. EAT THE NUTRIENTS", "TOGETHER TO RIPEN THE EGG"), controls=both, trial=Feast),
            Page(("DODGE THE CONTRACEPTION. EAT A FOLIC", "ACID CAPSULE AND YOU CAN EAT THEM"), dodge,
                 both, time=5.5),
            Page(("ONCE SHE'S RIPE, TOUCH TO WIN.", "BEAT THE CLOCK OR IT'S A PERIOD!"), controls=both, trial=Meet),
        ],
        labels={"stick": "P1 EGG", "stick2": "P2 SPERM"},
        accent="#ff6a8a",
    )


def _arc(d: tuple[int, int]) -> float:
    """How far clockwise round the loop a tile is (dots off the loop get a huge number)."""
    x, y = d
    if y == 1:
        return x - 1
    if x == 12:
        return 11 + (y - 1)
    if y == 4:
        return 14 + (12 - x)
    if x == 1:
        return 25 + (4 - y)
    return 1e9


def _maze_bytes(size: tuple[int, int]):
    c = art.maze(GRID, OX, OY, *size)
    img = c.to_image()
    return img.tobytes(), img.size, "RGBA"
