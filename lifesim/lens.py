"""LENS: what UNLOCK.EXE does with CUM.

The whole screen goes black, like a camera lens, and white paint starts raining
onto it: a drop here and there at first, then more and bigger splotches, until
the lens is nearly all white. Nothing else moves and there's no text. The
button (or the stick left) leaves once it's been up SKIP_GRACE, and it goes
back to the file listing by itself after LENS_TIME.

The splotches are painted onto one surface that's kept between frames, so each
frame only adds the new drops.
"""

from __future__ import annotations

import math
import random

import pygame

from minigames.shell import SKIP_GRACE

W, H = 320, 180
LENS_TIME = 45.0            # s before it goes back to the listing by itself
FILL_TIME = 35.0            # s for the drops to get up to their biggest and quickest
DROPS_START, DROPS_END = 1.5, 30.0     # drops a second, at the start and by FILL_TIME
SIZE_START, SIZE_END = 2.0, 14.0       # the biggest splotch radius, at the start and by FILL_TIME
PAINT = (250, 250, 246)


class Lens:
    def __init__(self, seed: int | None = None) -> None:
        self.t = 0.0
        self.done = False
        self.rng = random.Random(seed)
        self.lens = pygame.Surface((W, H))
        self.lens.fill((0, 0, 0))
        self.owed = 0.0                     # drops due but not painted yet

    def update(self, dt: float, sx: int, act: bool) -> None:
        self.t += dt
        if self.t > SKIP_GRACE and (act or sx < 0) or self.t > LENS_TIME:
            self.done = True
            return
        k = min(1.0, self.t / FILL_TIME)
        k = k * k                                           # slow to start, then it pours
        self.owed += dt * (DROPS_START + (DROPS_END - DROPS_START) * k)
        biggest = SIZE_START + (SIZE_END - SIZE_START) * k
        while self.owed >= 1:
            self.owed -= 1
            self._splat(self.rng.uniform(1.0, biggest))

    def _splat(self, r: float) -> None:
        """One drop: a round blot, a few lumps round its edge, and a spatter of specks."""
        x, y = self.rng.uniform(-4, W + 4), self.rng.uniform(-4, H + 4)
        pygame.draw.circle(self.lens, PAINT, (round(x), round(y)), max(1, round(r)))
        if r < 2.5:
            return
        for _ in range(self.rng.randint(2, 5)):             # lumps, so it isn't a perfect circle
            a = self.rng.uniform(0, math.tau)
            d = r * self.rng.uniform(0.6, 1.0)
            pygame.draw.circle(self.lens, PAINT, (round(x + math.cos(a) * d), round(y + math.sin(a) * d)),
                               max(1, round(r * self.rng.uniform(0.3, 0.6))))
        for _ in range(self.rng.randint(1, 6)):             # specks thrown off it
            a = self.rng.uniform(0, math.tau)
            d = r * self.rng.uniform(1.3, 2.4)
            pygame.draw.circle(self.lens, PAINT, (round(x + math.cos(a) * d), round(y + math.sin(a) * d)),
                               self.rng.choice((1, 1, 2)))

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.lens, (0, 0))
