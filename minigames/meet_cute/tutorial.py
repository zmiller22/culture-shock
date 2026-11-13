"""Meet Cute's how-to-play pages. The demos play on a tiny maze, drawn at 1x and
blown up 2x so the egg and the sperm read from across the room."""

from __future__ import annotations

import math

import pygame

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
    half = pygame.Surface((DEMO_W // 2, DEMO_H // 2))
    walls = pygame.image.frombytes(*_maze_bytes(half.get_size()))
    dots = [(x, y) for y, row in enumerate(GRID) for x, ch in enumerate(row) if ch == "."]

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

    def nutrients(t: float, eaten=lambda d: False) -> None:
        for d in dots:
            if not eaten(d):
                blit(a.nutrient[(d[0] + d[1] + int(t * 3)) % 2], *d)

    def done(s: pygame.Surface) -> None:
        pygame.transform.scale(half, s.get_size(), s)

    # 1. two players, one each
    def move(s: pygame.Surface, t: float):
        floor()
        nutrients(t)
        ex, ey, edx, edy = at(t * 4.5)
        sx, sy, sdx, sdy = at(PERIM / 2 - t * 5.5)            # the other way round
        sperm(sx, sy, (-sdx, -sdy), t)
        egg(ex, ey, t)
        done(s)
        caption(s, "P1", px(ex, ey)[0] * 2, px(ex, ey)[1] * 2 - 22, "#ffc4b0")
        caption(s, "P2", px(sx, sy)[0] * 2, px(sx, sy)[1] * 2 - 22, "#5ff3ff")
        return [(edx, edy, False), (-sdx, -sdy, False)]

    # 2. eat to ripen the egg
    def eat(s: pygame.Surface, t: float):
        t = loop(t, 6.0) * 6.0
        floor()
        se, ss = t * 4.5, PERIM / 2 - t * 4.5
        gone = lambda d: _ahead(_arc(d), 0, se) or _behind(_arc(d), PERIM / 2, ss)
        nutrients(t, gone)
        share = min(1.0, sum(map(gone, dots)) / (len(dots) * 0.8))
        ex, ey, edx, edy = at(se)
        sx, sy, sdx, sdy = at(ss)
        sperm(sx, sy, (-sdx, -sdy), t)
        egg(ex, ey, t, ripe=share >= 1)
        done(s)
        # the ripeness meter
        pygame.draw.rect(s, (20, 12, 28), (DEMO_W // 2 - 40, 4, 80, 7))
        pygame.draw.rect(s, (255, 106, 138), (DEMO_W // 2 - 39, 5, round(78 * share), 5))
        caption(s, "RIPE!" if share >= 1 else "RIPENESS", DEMO_W // 2, 13,
                "#ff6a8a" if share >= 1 and int(t * 4) % 2 else "#f4f4f4")
        return [(edx, edy, False), (-sdx, -sdy, False)]

    # 3. dodge the contraception; a folic acid capsule turns the tables
    CAP, TURN = 8.0, 2.0                                     # capsule at s=8; the egg gets there at t=2

    def dodge(s: pygame.Surface, t: float):
        t = loop(t, 5.5) * 5.5
        floor()
        nutrients(t, lambda d: _arc(d) <= min(t, TURN) * 4)
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

    # 4. meet up
    def meet(s: pygame.Surface, t: float):
        t = loop(t, 4.5) * 4.5
        floor()
        k = min(1.0, t / 1.6)
        ex, sx = 1 + 5 * k, 12 - 5.5 * k                     # along the bottom corridor, toward each other
        met = k >= 1
        if not met:
            sperm(sx, 4, (-1, 0), t)
            egg(ex, 4, t, ripe=True)
        else:
            blit(a.zygote[min(8, 2 ** int((t - 1.6) * 2))][int(t * 6) % 4], 6.25, 4, -min(8, (t - 1.6) * 10))
        done(s)
        if met:
            r = (t - 1.6) * 60
            for i in range(8):
                ang = i * math.tau / 8 + t
                img = a.heart
                s.blit(img, (round(px(6.25, 4)[0] * 2 + math.cos(ang) * r), round(px(6.25, 4)[1] * 2 + math.sin(ang) * r * 0.6)))
            caption(s, "IT'S CONCEPTION!", DEMO_W // 2, 10, "#ffe14d")
        go = 0 if met else 1
        return [(go, 0, False), (-go, 0, False)]

    return Tutorial(
        "MEET CUTE", "LIFE STARTS WHEN TWO CELLS FALL IN LOVE.",
        [
            Page(("P1 IS THE EGG: WASD OR STICK 1", "P2 IS THE SPERM: ARROWS OR STICK 2"), move, ("stick", "stick2")),
            Page(("IT'S CO-OP. EAT THE NUTRIENTS", "BETWEEN YOU TO RIPEN THE EGG"), eat, ("stick", "stick2"), time=6.0),
            Page(("DODGE THE CONTRACEPTION. EAT A FOLIC", "ACID CAPSULE AND YOU CAN EAT THEM"), dodge,
                 ("stick", "stick2"), time=5.5),
            Page(("ONCE SHE'S RIPE TOUCH TO WIN.", "BEAT THE CLOCK OR IT'S A PERIOD!"), meet, ("stick", "stick2")),
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


def _ahead(s: float, start: float, now: float) -> bool:
    return start <= s <= now


def _behind(s: float, start: float, now: float) -> bool:
    """Passed going anticlockwise from start to now (wrapping)."""
    span = start - now
    return 0 <= (start - s) % PERIM <= span


def _maze_bytes(size: tuple[int, int]):
    c = art.maze(GRID, OX, OY, *size)
    img = c.to_image()
    return img.tobytes(), img.size, "RGBA"
