"""It Takes Two's how-to-play pages. They play on a tiny maze, drawn at 1x and blown
up 2x so the egg and the sperm read from across the room. Every page but one is
a try-it page: P1 steers the egg and P2 the sperm round the little maze, with the
game's own speeds and cornering.

    1. Steer, and find each other (done when you touch).
    2. She has to be fertile first: eat 4 nutrients together to fill the bar.
    3. Watch out (a show-me): a condom catches the egg, a heart goes, back to start.
    4. Eat folic acid to fight back: grab the capsule, then eat the condom.
    5. The bar's full: find each other and conceive, and the round starts.
"""

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
EGG_AT, SPERM_AT = (1, 1), (12, 4)  # where they start, in opposite corners like the real maze
FOOD = [(7, 1), (12, 2), (5, 4), (1, 3)]    # the four nutrients on the fertility page
CAPSULE = (6, 4)                    # the folic acid on the fight-back page
CONDOM_AT = (9, 1)                  # and the condom it's for
CONDOM_SPEED, FLEE_SPEED = 2.6, 2.0   # tiles/s: slower than either of you, so it's learnable
SAFE = 1.2                          # s of blinking after getting sent back to start


def px(tx: float, ty: float) -> tuple[float, float]:
    return OX + tx * TILE + TILE / 2, OY + ty * TILE + TILE / 2


def make(a) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""
    from .game import PLAYER_HEX, TOUCH, EGG_SPEED, SPERM_SPEED, Enemy, ItTakesTwo, Player
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

    def shout(s: pygame.Surface, text: str, x: float, y: float, col: str) -> None:
        """A caption with a dark shadow, so it reads over the pink walls."""
        caption(s, text, x + 1, y + 1, "#140c1c")
        caption(s, text, x, y, col)

    def ring(s: pygame.Surface, tx: float, ty: float, t: float, col: str, label: str = "", r: int = 12) -> None:
        """A callout: a pulsing ring round a tile, and a label over it."""
        x, y = px(tx, ty)
        x, y = round(x * 2), round(y * 2)
        rr = r + round(math.sin(t * 8) * 1.5)
        pygame.draw.circle(s, (20, 12, 28), (x + 1, y + 1), rr, 2)
        pygame.draw.circle(s, col, (x, y), rr, 2)
        if label:
            shout(s, label, min(DEMO_W - 30, max(30, x)), y - rr - 8, col)

    def link(s: pygame.Surface, p, q, t: float) -> None:
        """A dotted line marching from one of them to the other: go find them."""
        (x0, y0), (x1, y1) = px(p.fx, p.fy), px(q.fx, q.fy)
        n = max(1, round(math.dist((x0, y0), (x1, y1)) / 4))
        for i in range(n):
            k = (i + (t * 3) % 1) / n
            x, y = (x0 + (x1 - x0) * k) * 2, (y0 + (y1 - y0) * k) * 2
            pygame.draw.rect(s, (255, 154, 200) if i % 2 else (95, 243, 255), (round(x) - 1, round(y) - 1, 2, 2))

    def meter(s: pygame.Surface, share: float, t: float) -> None:
        """The fertility bar, like the one in the game's HUD, flashing a yellow box
        round it and an arrow pointing at it."""
        full = share >= 1
        x0, y0, w_, h_ = DEMO_W // 2 - 52, 4, 104, 11
        pygame.draw.rect(s, (20, 12, 28), (x0, y0, w_, h_))
        s.blit(pygame.transform.scale(a.egg_ripe[0] if full else a.egg[0], (9, 9)), (x0 + 2, y0 + 1))
        label = text_surface("FERTILE!" if full else "FERTILITY",
                             "#ff9ac8" if full and int(t * 4) % 2 else "#f4f4f4")
        s.blit(label, (x0 + 13, y0 + 3))
        bx, bw = x0 + 51, 50
        pygame.draw.rect(s, (60, 30, 50), (bx, y0 + 3, bw, 5))
        pygame.draw.rect(s, (255, 106, 154) if full else (255, 225, 77), (bx, y0 + 3, round(bw * min(1.0, share)), 5))
        if int(t * 3) % 2 == 0:                               # the highlight
            pygame.draw.rect(s, (255, 225, 77), (x0 - 2, y0 - 2, w_ + 4, h_ + 4), 1)
        ay = y0 + h_ + 5 + round(math.sin(t * 6) * 2)
        for ax in (x0 - 8, x0 + w_ + 8):
            pygame.draw.polygon(s, (20, 12, 28), [(ax - 4, ay + 5), (ax + 4, ay + 5), (ax, ay - 1)])
            pygame.draw.polygon(s, (255, 225, 77), [(ax - 3, ay + 4), (ax + 3, ay + 4), (ax, ay)])

    def hearts(s: pygame.Surface, n: int, lost: float | None = None) -> None:
        """Shared hearts, top right. `lost`: s since the last one went (it floats off)."""
        for i in range(3):
            x = DEMO_W - 46 + i * 14
            if i < n:
                s.blit(pygame.transform.scale_by(a.heart_big, 2), (x, 4))
            elif i == n and lost is not None and lost < 0.8:
                h = pygame.transform.scale_by(a.heart_big, 2)
                h.set_alpha(int(255 * (1 - lost / 0.8)))
                s.blit(h, (x, 4 - lost * 20))

    # 3. watch out: a condom catches the egg, a heart goes, back to the start
    SPAN, HIT = 5.0, 1.4                                     # loop length; when they collide

    def caught(s: pygame.Surface, t: float):
        t = loop(t, SPAN) * SPAN
        floor()
        sperm(*SPERM_AT, (-1, 0), t)
        if t < HIT:
            ex, cx = 1 + 3.0 * t, 12 - 4.5 * t
            egg(ex, 1, t)
            blit(a.enemy[("condom", int(t * 5) % 2, (-1, 0))], cx, 1)
        else:
            u = t - HIT
            hx = 1 + 3.0 * HIT
            cx = 12 - 4.5 * HIT + min(u, 2.0) * 2.0           # it wanders off, pleased with itself
            blit(a.enemy[("condom", int(t * 5) % 2, (1, 0) if u > 0.6 else (0, 0))], cx, 1)
            if u < 0.4:
                blit(a.pop["#ff4a6a"][min(3, int(u / 0.1))], hx, 1)
            if u > 0.6 and int(t * 10) % 2:                   # back at the start, blinking
                egg(1, 1, t)
        done(s)
        if t >= HIT:
            u = t - HIT
            hearts(s, 2, u)
            if u < 1.6:
                shout(s, "BAGGED!", px(1 + 3.0 * HIT, 1)[0] * 2, px(0, 1)[1] * 2 + 12 - u * 4, "#ff4a6a")
            if u > 0.3:                                       # the callouts: a heart gone, and back to start
                x0 = DEMO_W - 48
                pygame.draw.rect(s, (255, 74, 106), (x0, 1, 44, 17), 1)
                shout(s, "-1", x0 - 8, 7, "#ff4a6a")
            if u > 0.6:
                ring(s, 1, 1, t, "#ffe14d")
                shout(s, "BACK TO START", px(1, 1)[0] * 2 + 2, px(1, 1)[1] * 2 + 16, "#ffe14d")
        else:
            hearts(s, 3)
            ring(s, 12 - 4.5 * t, 1, t, "#ff4a6a", "CONDOM")
        return [(1, 0, False) if t < HIT else (0, 0, False), (0, 0, False)]

    # -- try it --------------------------------------------------------------------------
    class Box:
        """The tiny maze, driven by the game's own steering and corridor sliding."""
        passable = staticmethod(lambda t, who: 0 <= t[1] < len(GRID) and 0 <= t[0] < len(GRID[0])
                                and GRID[t[1]][t[0]] == ".")
        _move = ItTakesTwo._move
        _steer = ItTakesTwo._steer

    box = Box()

    class Swim:
        """Both of them loose in the tiny maze; done when they find each other."""
        cheer = "FOUND YOU!"
        share = 0.0                                       # how full the fertility bar is

        def __init__(self) -> None:
            self.egg = Player(*map(float, EGG_AT), EGG_SPEED, kind="egg", start=EGG_AT)
            self.sperm = Player(*map(float, SPERM_AT), SPERM_SPEED, kind="sperm", start=SPERM_AT, face=(-1, 0))
            self.done = False
            self.met_t: float | None = None               # page time they touched
            self.met_at = (0.0, 0.0)

        @property
        def ripe(self) -> bool:
            return self.share >= 1

        def swim(self, dt: float, inp) -> None:
            pads = inp.players or (inp, Input())
            for p, pin in zip((self.egg, self.sperm), pads):
                box._steer(p, pin)
                box._move(p, p.speed * dt)
                p.invuln = max(0.0, p.invuln - dt)

        def touching(self) -> bool:
            e, s = self.egg, self.sperm
            if math.dist((e.fx, e.fy), (s.fx, s.fy)) < TOUCH:
                self.met_at = ((e.fx + s.fx) / 2, (e.fy + s.fy) / 2)
                return True
            return False

        def update(self, dt: float, inp) -> None:
            self.swim(dt, inp)
            self.done = self.touching()

        def players(self, t: float) -> None:
            for p in (self.egg, self.sperm):
                if p.invuln > 0 and int(t * 12) % 2:
                    continue
                if p.kind == "egg":
                    blit((a.egg_ripe if self.ripe else a.egg)[int(p.anim * 2) % 4], p.fx, p.fy)
                else:
                    sperm(p.fx, p.fy, p.face, t)

        def tag(self, s: pygame.Surface, p, label: str, t: float) -> None:
            """P1 / P2 over each of them."""
            x, y = px(p.fx, p.fy)
            x, y = x * 2, y * 2 - 22 + round(math.sin(t * 5))
            col = PLAYER_HEX[p.kind]
            caption(s, label, x + 1, y + 1, "#140c1c")        # a shadow, so it reads over the walls
            caption(s, label, x, y, col)

        def tags(self, s: pygame.Surface, t: float) -> None:
            if not self.done:
                self.tag(s, self.egg, "P1", t)
                self.tag(s, self.sperm, "P2", t)

        def found(self, s: pygame.Surface, t: float) -> None:
            """A heart pops up where they touched."""
            if self.met_t is None:
                self.met_t = t
            u = t - self.met_t
            x, y = px(*self.met_at)
            h = pygame.transform.scale_by(a.heart_big, 3)
            s.blit(h, (round(x * 2 - h.get_width() / 2), round(y * 2 - 20 - min(u, 0.4) * 20)))

        def scene(self, t: float) -> None:
            floor()
            self.players(t)

        def callouts(self, s: pygame.Surface, t: float) -> None:
            if not self.done:
                link(s, self.egg, self.sperm, t)
                ring(s, self.egg.fx, self.egg.fy, t, PLAYER_HEX["egg"])
                ring(s, self.sperm.fx, self.sperm.fy, t, PLAYER_HEX["sperm"])

        def draw(self, s: pygame.Surface, t: float):
            self.scene(t)
            done(s)
            self.callouts(s, t)
            self.tags(s, t)
            if self.done:
                hush(s)
                self.found(s, t)
            k = loop(t, 2.4)                                  # the icons: egg right then down, sperm left then up
            return [(1, 0, False) if k < 0.5 else (0, 1, False), (-1, 0, False) if k < 0.5 else (0, -1, False)]

    class Feast(Swim):
        """Four nutrients round the maze; eat them all, between you, and she's fertile."""
        cheer = "SHE'S FERTILE!"

        def __init__(self) -> None:
            super().__init__()
            self.food = set(FOOD)
            self.flash: list[tuple[float, float, float]] = []    # where a nutrient just went, and how long ago

        @property
        def share(self) -> float:
            return 1 - len(self.food) / len(FOOD)

        def update(self, dt: float, inp) -> None:
            self.swim(dt, inp)
            self.flash = [(x, y, u + dt) for x, y, u in self.flash if u + dt < 0.4]
            for p in (self.egg, self.sperm):
                if p.tile in self.food:
                    self.food.discard(p.tile)
                    self.flash.append((*p.tile, 0.0))
            self.done = self.ripe

        def draw(self, s: pygame.Surface, t: float):
            floor()
            for d in self.food:
                blit(a.nutrient[(d[0] + d[1] + int(t * 3)) % 2], *d)
            for x, y, u in self.flash:
                blit(a.pop["#ffe14d"][min(3, int(u / 0.1))], x, y)
            self.players(t)
            done(s)
            for i, d in enumerate(sorted(self.food)):
                ring(s, *d, t + i * 0.3, "#ffe14d", r=8)
            self.tags(s, t)
            meter(s, self.share, t)
            if self.done:
                hush(s)
            k = loop(t, 3.0)                                  # the icons: egg along the top, sperm along the bottom
            return [(1, 0, False) if k < 0.6 else (0, 1, False), (-1, 0, False) if k < 0.6 else (0, -1, False)]

    class Fight(Swim):
        """A condom hunts whoever's closest; touch it and you're sent back. Grab the
        folic acid and it turns blue and runs, and you can eat it."""
        cheer = "GOT 'EM!"

        def __init__(self) -> None:
            super().__init__()
            self.capsule = True
            self.condom = Enemy(*map(float, CONDOM_AT), CONDOM_SPEED, kind="condom", state="roam")
            self.eaten_t: float | None = None
            self.caught: list[tuple[float, float, float]] = []   # BAGGED! popups: x, y, age
            self.time = 0.0

        def choose(self, e) -> tuple[int, int]:
            tx, ty = round(e.fx), round(e.fy)
            opts = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1)) if box.passable((tx + d[0], ty + d[1]), e)]
            back = (-e.dir[0], -e.dir[1])
            if len(opts) > 1 and back in opts:
                opts.remove(back)
            live = [p for p in (self.egg, self.sperm) if p.invuln <= 0] or [self.egg, self.sperm]
            near = min(live, key=lambda p: math.dist((p.fx, p.fy), (e.fx, e.fy)))
            score = lambda d: math.dist((tx + d[0], ty + d[1]), (near.fx, near.fy))
            return (max if not self.capsule else min)(opts, key=score)

        def update(self, dt: float, inp) -> None:
            self.time += dt
            self.swim(dt, inp)
            self.caught = [(x, y, u + dt) for x, y, u in self.caught if u + dt < 1.0]
            if self.eaten_t is not None:
                self.eaten_t += dt
                return
            e = self.condom
            e.speed = CONDOM_SPEED if self.capsule else FLEE_SPEED
            box._move(e, e.speed * dt, self.choose)
            e.anim += dt
            for p in (self.egg, self.sperm):
                if self.capsule and p.tile == CAPSULE:
                    self.capsule = False
                    e.dir = (-e.dir[0], -e.dir[1])
                if math.dist((p.fx, p.fy), (e.fx, e.fy)) >= TOUCH:
                    continue
                if not self.capsule:                      # chomp
                    self.eaten_t = 0.0
                    self.eaten_at = (e.fx, e.fy)
                    self.done = True
                    return
                if p.invuln <= 0:                         # bagged: back to the start
                    self.caught.append((p.fx, p.fy, 0.0))
                    p.place(p.start)
                    p.invuln = SAFE

        def draw(self, s: pygame.Surface, t: float):
            floor()
            f = int(t * 5) % 2
            if self.capsule:
                blit(a.folic[int(t * 4) % 2], *CAPSULE)
            e = self.condom
            if self.eaten_t is None:
                if self.capsule:
                    blit(a.enemy[("condom", f, e.dir)], e.fx, e.fy)
                else:
                    blit(a.scared[(f, int(t * 6) % 3 == 0)], e.fx, e.fy)
            else:
                ex, ey = self.eaten_at
                u = self.eaten_t
                if u < 0.4:
                    blit(a.pop["#5ff3ff"][min(3, int(u / 0.1))], ex, ey)
                blit(a.eyes[(0, -1)], ex, ey - u * 6)          # what's left of it, legging it
            for x, y, u in self.caught:
                if u < 0.4:
                    blit(a.pop["#ff4a6a"][min(3, int(u / 0.1))], x, y)
            self.players(t)
            done(s)
            if self.capsule:
                ring(s, *CAPSULE, t, "#ffe14d", "FOLIC ACID")
                if self.eaten_t is None:
                    ring(s, e.fx, e.fy, t, "#ff4a6a", "AVOID!")
            elif self.eaten_t is None:
                ring(s, e.fx, e.fy, t, "#5ff3ff", "EAT IT!")
            self.tags(s, t)
            for x, y, u in self.caught:
                cx, cy = px(x, y)
                shout(s, "BAGGED!", cx * 2, cy * 2 - 26 - u * 8, "#ff4a6a")
            if self.done:
                hush(s)
                ex, ey = px(*self.eaten_at)
                shout(s, "CHOMP!", ex * 2, ey * 2 + 14, "#ffe14d")
            k = loop(t, 3.0)                                  # the icons: egg along the bottom to the capsule
            return [(0, 1, False) if k < 0.35 else (1, 0, False), (-1, 0, False)]

    class Meet(Swim):
        """The bar's full: swim into each other and it's conception, and the round starts."""
        cheer = "IT'S CONCEPTION!"
        share = 1.0

        def draw(self, s: pygame.Surface, t: float):
            floor()
            if not self.done:
                self.players(t)
                done(s)
                self.callouts(s, t)
                self.tags(s, t)
                meter(s, 1.0, t)
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
        "IT TAKES TWO", "",
        [
            Page(("FIND EACH OTHER!",), controls=both, trial=Swim),
            Page(("EAT 4 NUTRIENTS TO GET FERTILE",), controls=both, trial=Feast),
            Page(("DODGE THE CONTRACEPTIVES",), caught, both, time=SPAN),
            Page(("EAT FOLIC ACID, THEN EAT THEM!",), controls=both, trial=Fight),
            Page(("BAR FULL? TOUCH TO CONCEIVE!",), controls=both, trial=Meet),
        ],
        labels={"stick": "P1 EGG", "stick2": "P2 SPERM"},
        accent="#ff6a8a",                # (no intro screen: the game's own prelude and entrances came first)
    )


def _maze_bytes(size: tuple[int, int]):
    c = art.maze(GRID, OX, OY, *size)
    img = c.to_image()
    return img.tobytes(), img.size, "RGBA"
