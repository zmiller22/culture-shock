"""LENS: what UNLOCK.EXE does with CUM.

The whole screen goes black, like a camera lens, and white paint starts raining
onto it: a drop here and there at first, then more and bigger splotches, until
the lens is mostly white by SKIP_AT. Nothing else moves, and the only text is
HOLD BUTTON: SKIP along the bottom from SKIP_AT on: holding the button for
SKIP_HOLD (a bar fills) goes back to the file listing. It goes back by itself
after LENS_TIME.

The splotches are painted onto one surface that's kept between frames, so each
frame only adds the new drops.
"""

from __future__ import annotations

import math
import random

import pygame

from minigames.shell import prompt_text

W, H = 320, 180
LENS_TIME = 40.0            # s before it goes back to the listing by itself
FILL_TIME = 11.0            # s for the drops to get up to their biggest and quickest (about 80% white by 15 s)
DROPS_START, DROPS_END = 2.0, 45.0     # drops a second, at the start and by FILL_TIME
SIZE_START, SIZE_END = 2.0, 16.0       # the biggest splotch radius, at the start and by FILL_TIME
SKIP_AT = 15.0              # s before HOLD BUTTON: SKIP comes up (and a hold works)
SKIP_HOLD = 1.0             # s of holding the button that skips it
PAINT = (250, 250, 246)


class Lens:
    def __init__(self, seed: int | None = None) -> None:
        self.t = 0.0
        self.done = False
        self.rng = random.Random(seed)
        self.lens = pygame.Surface((W, H))
        self.lens.fill((0, 0, 0))
        self.owed = 0.0                     # drops due but not painted yet
        self.hold: float | None = None      # s the button's been held toward skipping

    def update(self, dt: float, held: bool) -> None:
        self.t += dt
        if self.t >= SKIP_AT and held:      # (a hold started before the prompt counts from when it's up)
            self.hold = (self.hold or 0.0) + dt
        else:
            self.hold = None
        if self.hold and self.hold >= SKIP_HOLD or self.t > LENS_TIME:
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
        if self.t < SKIP_AT:
            return
        s = prompt_text("HOLD BUTTON: SKIP")              # on a dark strip, so it reads over the paint
        x, y = W // 2 - s.get_width() // 2, H - s.get_height() - 6
        screen.fill((0, 0, 0), (x - 4, y - 3, s.get_width() + 8, s.get_height() + 8))
        screen.blit(s, (x, y))
        if self.hold:                                       # holding: a bar fills up to skipping
            k = min(1.0, self.hold / SKIP_HOLD)
            screen.fill((60, 60, 60), (x, y + s.get_height() + 1, s.get_width(), 2))
            screen.fill((234, 255, 234), (x, y + s.get_height() + 1, round(s.get_width() * k), 2))
