"""D-LOOP: what UNLOCK.EXE does with DNA.

A love story in strand invasion. A double helix (dsDNA) twists slowly across
the screen. A single strand (ssDNA) drifts in and, in a speech bubble:

    I SAW YOU FROM ACROSS THE ROOM
    AND I LIKED YOUR CURVES...
    CAN I INSERT MYSELF
    INTO YOUR MAJOR GROOVE?

The helix opens up in the middle, the single strand slides into the gap and
base-pairs with the bottom strand, rung by rung, and the top strand it pushed
out bulges up into the D loop. Then all three twist up together, hearts rise
off them, and it says, big:

    OH GOD YOU'RE GONNA
    MAKE MY D LOOP

From SKIP_AT on, HOLD BUTTON: SKIP shows along the bottom and a SKIP_HOLD hold
goes back to the file listing. It goes back by itself after DLOOP_TIME.
"""

from __future__ import annotations

import math
import random

import pygame

from sprites.font import BIG_H, big_width
from minigames.shell import prompt_text

from .trip import HUES, Trip

W, H = 320, 180
CY = 120                    # the helix's middle line
AMP = 11                    # how far each strand swings out from it
TWIST = 0.075               # radians of twist a pixel along the helix
SPIN = 1.4                  # radians a second the helix turns
MID, HALF, EDGE = 160, 74, 26   # the bubble: its middle, its half-width, and how gradually its sides open
TOP_Y, BOT_Y = CY - 36, CY + 10     # where the open strands go: the displaced one up (the D loop), the template down
SS_LEN = 104                # the single strand's length, px

# the story, in seconds
T_SPEAK = 1.8               # the speech bubble starts typing
T_OPEN = 9.0                # the helix starts opening
T_INSERT = 10.8             # the single strand goes in
T_TANGLE = 14.2             # all three twist up together
T_SHOUT = 15.4              # OH GOD ...
OPEN_TIME, INSERT_TIME, TANGLE_TIME = 1.6, 2.6, 1.6
TYPE_RATE = 26.0            # letters a second in the speech bubble
SKIP_AT = 8.0               # s before HOLD BUTTON: SKIP comes up (and a hold works)
SKIP_HOLD = 1.0             # s of holding the button that skips it
DLOOP_TIME = 32.0           # s before it goes back to the listing by itself

LINE_UP = ("I SAW YOU FROM ACROSS THE ROOM", "AND I LIKED YOUR CURVES...",
           "CAN I INSERT MYSELF", "INTO YOUR MAJOR GROOVE?")
SHOUT = (("OH GOD YOU'RE GONNA", 2), ("MAKE MY D LOOP", 3))

BG = (14, 6, 26)
STRAND_A, STRAND_B, STRAND_S = (95, 243, 255), (255, 106, 213), (255, 225, 77)   # top, bottom, the single strand
BASES = {"A": (255, 90, 90), "T": (90, 150, 255), "G": (100, 230, 110), "C": (255, 170, 60)}
PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}


def ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def heart(screen: pygame.Surface, x: int, y: int, col: tuple[int, int, int]) -> None:
    for dy, row in enumerate(("01100110", "11111111", "11111111", "01111110", "00111100", "00011000")):
        for dx, c in enumerate(row):
            if c == "1":
                screen.fill(col, (x + dx - 4, y + dy - 3, 1, 1))


class DLoop:
    _render = staticmethod(Trip._render)
    _glyph = Trip._glyph

    def __init__(self, seed: int | None = None) -> None:
        self.t = 0.0
        self.done = False
        self.hold: float | None = None
        self.glyphs: dict[tuple[str, int, int], pygame.Surface] = {}
        self.rng = random.Random(seed)
        self.top_seq = [self.rng.choice("ATGC") for _ in range(W // 6 + 2)]        # a base every 6 px
        self.ss_seq = [PAIR[self.top_seq[(MID - SS_LEN // 2) // 6 + i]] for i in range(SS_LEN // 6 + 1)]
        self.hearts: list[list[float]] = []            # x, y, age
        self.next_heart = 0.0

    # -- the story's dials, 0..1 ------------------------------------------------------------
    @property
    def open(self) -> float:
        return ease((self.t - T_OPEN) / OPEN_TIME)

    @property
    def insert(self) -> float:
        return ease((self.t - T_INSERT) / INSERT_TIME)

    @property
    def tangle(self) -> float:
        return ease((self.t - T_TANGLE) / TANGLE_TIME)

    def update(self, dt: float, held: bool) -> None:
        self.t += dt
        if self.t >= SKIP_AT and held:
            self.hold = (self.hold or 0.0) + dt
        else:
            self.hold = None
        if self.hold and self.hold >= SKIP_HOLD or self.t > DLOOP_TIME:
            self.done = True
            return
        if self.tangle > 0.3:                          # hearts float up off the three of them
            self.next_heart -= dt
            if self.next_heart <= 0:
                self.next_heart = 0.18
                self.hearts.append([self.rng.uniform(MID - HALF + 10, MID + HALF - 10), TOP_Y + 10, 0.0])
        for h in self.hearts:
            h[1] -= 22 * dt
            h[2] += dt
        self.hearts = [h for h in self.hearts if h[2] < 2.5]

    # -- where things are ---------------------------------------------------------------------
    def bubble(self, x: float) -> float:
        """0..1: how far open the helix is at x (1 in the middle of the bubble once it's open)."""
        return self.open * ease((HALF - abs(x - MID)) / EDGE)

    def phase(self, x: float) -> float:
        return x * TWIST + self.t * SPIN

    def strand_a(self, x: float) -> float:
        """The top strand: on the helix, or pushed up into the D loop, wobbling once they're tangled."""
        o = self.bubble(x)
        loop = TOP_Y + 10 - 18 * math.sin(math.pi * max(0.0, min(1.0, (x - MID + HALF) / (2 * HALF))))   # arched: the D
        loop += self.tangle * 4 * math.sin(x * 0.09 + self.t * 5)
        return (CY + AMP * math.sin(self.phase(x))) * (1 - o) + loop * o

    def strand_b(self, x: float) -> float:
        """The bottom strand: on the helix, or flat along the bottom of the bubble, then twisting
        round the single strand."""
        o = self.bubble(x)
        flat = BOT_Y - self.insert * 6 + self.tangle * 6 * math.sin(self.phase(x) * 1.6)
        return (CY - AMP * math.sin(self.phase(x))) * (1 - o) + flat * o

    def strand_s(self, s: float) -> tuple[float, float]:
        """The single strand, s 0..1 along it: hovering top left, then in the bubble, paired."""
        t = self.t
        enter = ease(t / 1.6)
        hx = -SS_LEN + (24 + SS_LEN) * enter + SS_LEN * s
        hy = 92 + 4 * math.sin(s * 11 + t * 5)
        x = MID - SS_LEN / 2 + SS_LEN * s
        paired = self.strand_b(x) - 12                  # lying along the bottom strand, a rung's length up
        twisted = BOT_Y - 6 - 6 * math.sin(self.phase(x) * 1.6)   # wound round it (the bottom strand does the opposite)
        y = paired + (twisted - paired) * self.tangle
        k = self.insert
        arc = -26 * math.sin(math.pi * k)               # a little hop on the way in
        return hx + (x - hx) * k, hy + (y - hy) * k + arc

    # -- drawing ----------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        t = self.t
        shake = (round(math.sin(t * 37)), round(math.cos(t * 29))) if t > T_SHOUT and t < T_SHOUT + 1.2 else (0, 0)
        frame = pygame.Surface((W, H))
        frame.fill(BG)
        self._draw_helix(frame)
        self._draw_single(frame)
        for x, y, age in self.hearts:
            heart(frame, round(x + 4 * math.sin(age * 4 + x)), round(y), (255, 110, 170))
        if T_SPEAK <= t < T_INSERT + 0.4:
            self._draw_speech(frame)
        if t >= T_SHOUT:
            self._draw_shout(frame)
        screen.fill(BG)
        screen.blit(frame, shake)
        if t >= SKIP_AT:
            s = prompt_text("HOLD BUTTON: SKIP")
            x, y = W // 2 - s.get_width() // 2, H - s.get_height() - 6
            screen.fill((0, 0, 0), (x - 4, y - 3, s.get_width() + 8, s.get_height() + 8))
            screen.blit(s, (x, y))
            if self.hold:
                k = min(1.0, self.hold / SKIP_HOLD)
                screen.fill((60, 60, 60), (x, y + s.get_height() + 1, s.get_width(), 2))
                screen.fill((234, 255, 234), (x, y + s.get_height() + 1, round(s.get_width() * k), 2))

    def _shade(self, col: tuple[int, int, int], depth: float) -> tuple[int, int, int]:
        """Darker round the back of the helix: depth -1 (back) .. 1 (front)."""
        k = 0.55 + 0.45 * (depth + 1) / 2
        return int(col[0] * k), int(col[1] * k), int(col[2] * k)

    def _draw_helix(self, s: pygame.Surface) -> None:
        # the rungs first, so the backbones go over their ends
        for i, base in enumerate(self.top_seq):
            x = i * 6 + 3
            o = self.bubble(x)
            if o > 0.2:
                continue                                    # unzipped here
            ya, yb = self.strand_a(x), self.strand_b(x)
            m = (ya + yb) / 2
            depth = math.cos(self.phase(x))
            pygame.draw.line(s, self._shade(BASES[base], depth), (x, ya), (x, m), 2)
            pygame.draw.line(s, self._shade(BASES[PAIR[base]], depth), (x, m), (x, yb), 2)
        for strand, col, sign in ((self.strand_a, STRAND_A, 1), (self.strand_b, STRAND_B, -1)):
            prev = None
            for x in range(-2, W + 3, 2):
                p = (x, strand(x))
                if prev:
                    depth = sign * math.cos(self.phase(x)) * (1 - self.bubble(x))
                    pygame.draw.line(s, self._shade(col, depth), prev, p, 3)
                prev = p
        for i, base in enumerate(self.top_seq):             # the D loop's bases, sticking out unpaired
            x = i * 6 + 3
            if self.bubble(x) > 0.6:
                ya = self.strand_a(x)
                pygame.draw.line(s, BASES[base], (x, ya + 1), (x, ya + 5), 2)

    def _draw_single(self, s: pygame.Surface) -> None:
        n = len(self.ss_seq)
        paired = max(0.0, min(1.0, (self.insert - 0.55) / 0.45))   # pairs up left to right as it lands
        pts = [self.strand_s(i / 40) for i in range(41)]
        for i, base in enumerate(self.ss_seq):
            k = i / (n - 1)
            x, y = self.strand_s(k)
            if k <= paired and self.insert > 0.55:             # paired: a full rung down to the bottom strand
                yb = self.strand_b(x)
                m = (y + yb) / 2
                pygame.draw.line(s, BASES[base], (x, y), (x, m), 2)
                pygame.draw.line(s, BASES[PAIR[base]], (x, m), (x, yb), 2)
            else:                                              # unpaired: a stub, reaching
                pygame.draw.line(s, BASES[base], (x, y), (x, y + 5), 2)
        pygame.draw.lines(s, STRAND_S, False, pts, 3)
        hx, hy = pts[0]                                        # a little face on its 5' end
        pygame.draw.circle(s, STRAND_S, (round(hx) - 3, round(hy)), 5)
        s.fill(BG, (round(hx) - 6, round(hy) - 2, 2, 2))
        s.fill(BG, (round(hx) - 2, round(hy) - 2, 2, 2))
        if self.t < T_TANGLE:
            s.fill(BG, (round(hx) - 5, round(hy) + 2, 4, 1))
        else:                                                  # :O
            s.fill(BG, (round(hx) - 4, round(hy) + 1, 2, 3))

    def _draw_speech(self, s: pygame.Surface) -> None:
        typed = int((self.t - T_SPEAK) * TYPE_RATE)
        lines, left = [], typed
        for line in LINE_UP:
            lines.append(line[:max(0, left)])
            left -= len(line) + 3                               # (a little pause at each line's end)
        w = max(big_width(line) for line in LINE_UP) + 12
        h = len(LINE_UP) * (BIG_H + 3) + 8
        box = pygame.Rect(W - w - 10, 8, w, h)
        hx, hy = self.strand_s(0)
        s.fill((248, 244, 255), box)
        pygame.draw.polygon(s, (248, 244, 255), [(box.x + 18, box.bottom - 1), (box.x + 34, box.bottom - 1),
                                                 (round(hx) + 4, round(hy) - 8)])
        pygame.draw.rect(s, (40, 20, 60), box, 1)
        for i, line in enumerate(lines):
            if line:
                s.blit(prompt_text(line, "#2a1440"), (box.x + 6, box.y + 5 + i * (BIG_H + 3)))

    def _draw_shout(self, s: pygame.Surface) -> None:
        u = self.t - T_SHOUT
        y = 6
        count = 0
        for n, (line, scale) in enumerate(SHOUT):
            x0 = W // 2 - big_width(line) * scale // 2
            for i, ch in enumerate(line):
                count += 1
                if ch == " ":
                    continue
                pop = max(0.0, 1 - (u - count * 0.04) / 0.25)
                if pop >= 1:
                    continue
                wob = math.sin(self.t * 6 + i * 0.7 + n)
                x = x0 + i * 6 * scale
                yy = y + round(wob * 2) - round(30 * pop * pop)
                hue = int(self.t * 12 + i + n * 5) % HUES
                dark = self._glyph(ch, -1, scale)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (2, 2)):
                    s.blit(dark, (x + dx, yy + dy))
                s.blit(self._glyph(ch, hue, scale), (x, yy))
            y += BIG_H * scale + 6
