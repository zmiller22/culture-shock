"""LANGTON LABS: what UNLOCK.EXE does with LAB.

Eight of Langton's ants, the lab's namesake, crawl over a dark screen. Each
ant turns left or right depending on the colour of the cell it's on, steps
the cell on to the next colour, and moves one cell. With a many-colour rule
they paint swirling, growing patterns, and the colours flow round the rainbow
the whole time. The ants start slowly, so you can see them, then speed up.
Over the top, in wobbling rainbow letters:

    BROUGHT TO YOU BY
    LANGTON LABS

From SKIP_AT on, HOLD BUTTON: SKIP shows along the bottom and a SKIP_HOLD hold
goes back to the file listing. It goes back by itself after LAB_TIME.

The grid is one byte a cell, turned into an 8-bit picture each frame, so the
rainbow is only a palette change, which is cheap enough for the Pi.
"""

from __future__ import annotations

import colorsys
import math

import pygame

from sprites.font import BIG_H, big_width
from minigames.shell import prompt_text

from .trip import HUES, Trip

W, H = 320, 180
GW, GH = 160, 90            # the grid, a cell is 2x2 pixels
RULE = "LLRR"               # the turn on each colour: this one grows symmetric blooms
ANTS = tuple((round(GW / 2 + 52 * math.cos(a * math.tau / 8)), round(GH / 2 + 30 * math.sin(a * math.tau / 8)), a % 4)
             for a in range(8))           # eight ants in a ring: eight flowers that grow into each other
STEPS_START, STEPS_MAX = 60.0, 4000.0   # steps a second for each ant, at first and once it's sped up
HUE_SPAN = 0.45             # how much of the rainbow the colours span at once (it all drifts round)
SPEED_UP = 12.0             # s to get up to full speed
TEXT_AT = 1.5               # s before the words come in
LINES = (("BROUGHT TO YOU BY", 2), ("LANGTON LABS", 3))
SKIP_AT = 8.0               # s before HOLD BUTTON: SKIP comes up (and a hold works)
SKIP_HOLD = 1.0             # s of holding the button that skips it
LAB_TIME = 45.0             # s before it goes back to the listing by itself
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))   # up, right, down, left: an ant's heading is an index into this


class Langton:
    _render = staticmethod(Trip._render)
    _glyph = Trip._glyph

    def __init__(self) -> None:
        self.t = 0.0
        self.done = False
        self.grid = bytearray(GW * GH)
        self.ants = [list(a) for a in ANTS]
        self.owed = 0.0                     # steps due but not taken yet
        self.hold: float | None = None
        self.glyphs: dict[tuple[str, int, int], pygame.Surface] = {}
        self.turns = [1 if c == "R" else -1 for c in RULE]

    def update(self, dt: float, held: bool) -> None:
        self.t += dt
        if self.t >= SKIP_AT and held:
            self.hold = (self.hold or 0.0) + dt
        else:
            self.hold = None
        if self.hold and self.hold >= SKIP_HOLD or self.t > LAB_TIME:
            self.done = True
            return
        k = min(1.0, self.t / SPEED_UP)
        self.owed += dt * (STEPS_START + (STEPS_MAX - STEPS_START) * k * k)
        steps, self.owed = int(self.owed), self.owed % 1
        grid, turns, n = self.grid, self.turns, len(RULE)
        for ant in self.ants:
            x, y, d = ant
            for _ in range(steps):
                i = y * GW + x
                c = grid[i]
                d = (d + turns[c]) % 4
                grid[i] = (c + 1) % n
                dx, dy = MOVES[d]
                x, y = (x + dx) % GW, (y + dy) % GH
            ant[0], ant[1], ant[2] = x, y, d

    def _palette(self) -> list[tuple[int, int, int]]:
        """Colour 0 is the dark; the rest go round the rainbow, flowing as time goes on."""
        t, n = self.t, len(RULE)
        pulse = 0.5 + 0.5 * math.sin(t * 1.3)
        out = [(int(10 + 14 * pulse), 0, int(24 + 20 * pulse))]
        for i in range(1, n):
            hue = (i / n * HUE_SPAN + t * 0.18) % 1.0          # neighbouring colours close: it flows, not confetti
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.55 + 0.45 * i / n)
            out.append((int(r * 255), int(g * 255), int(b * 255)))
        return out + [(0, 0, 0)] * (256 - n)

    def draw(self, screen: pygame.Surface) -> None:
        t = self.t
        pic = pygame.image.frombuffer(bytes(self.grid), (GW, GH), "P")
        pic.set_palette(self._palette())
        screen.blit(pygame.transform.scale(pic, (W, H)), (0, 0))
        for x, y, _ in self.ants:                       # the ants themselves, white
            screen.fill((255, 255, 255), (x * 2, y * 2, 2, 2))

        if t >= TEXT_AT:                                # the words, each letter dropping in, then wobbling
            u = t - TEXT_AT
            y = (H - sum(BIG_H * sc + 8 for _, sc in LINES)) // 2
            band = pygame.Surface((W, sum(BIG_H * sc + 8 for _, sc in LINES) + 12), pygame.SRCALPHA)
            band.fill((8, 0, 16, round(150 * min(1.0, u / 0.5))))   # a dark band so the words read
            screen.blit(band, (0, y - 8))
            count = 0
            for n, (line, scale) in enumerate(LINES):
                x0 = W // 2 - big_width(line) * scale // 2
                for i, ch in enumerate(line):
                    count += 1
                    if ch == " ":
                        continue
                    drop = max(0.0, 1 - (u - count * 0.05) / 0.3)
                    if drop >= 1:
                        continue
                    wob = math.sin(t * 4 + i * 0.6 + n * 1.7)
                    x = x0 + i * 6 * scale + round(math.cos(t * 3 + i) * scale * 0.7)
                    yy = y + round(wob * (2 + scale)) - round(40 * drop * drop)
                    hue = int(t * 12 + i + n * 6) % HUES
                    dark = self._glyph(ch, -1, scale)
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (2, 2)):
                        screen.blit(dark, (x + dx, yy + dy))
                    screen.blit(self._glyph(ch, hue, scale), (x, yy))
                y += BIG_H * scale + 8

        if t >= SKIP_AT:
            s = prompt_text("HOLD BUTTON: SKIP")
            x, y = W // 2 - s.get_width() // 2, H - s.get_height() - 6
            screen.fill((0, 0, 0), (x - 4, y - 3, s.get_width() + 8, s.get_height() + 8))
            screen.blit(s, (x, y))
            if self.hold:
                k = min(1.0, self.hold / SKIP_HOLD)
                screen.fill((60, 60, 60), (x, y + s.get_height() + 1, s.get_width(), 2))
                screen.fill((234, 255, 234), (x, y + s.get_height() + 1, round(s.get_width() * k), 2))
