"""TRIP: what UNLOCK.EXE does with SEX (the code is hidden somewhere in the room).

The terminal melts into a psychedelic light show, with this wobbling over it in
rainbow letters:

    THANK YOU FOR
    TRIPPING WITH
    THE LIFE LAB!
    YOU ARE
    AMAZING!

The background is a plasma worked out once at startup into an 8-bit picture.
Each frame only rotates its palette, which is cheap enough for the Pi and is
what makes the colours flow. A second, swirling tunnel pattern fades in and out
over the plasma.
"""

from __future__ import annotations

import colorsys
import math

import pygame

from sprites.canvas import Canvas
from sprites.font import BIG_H, big_width, draw_big_text
from sprites.viewer import to_surface
from minigames.shell import SKIP_GRACE, prompt_text

W, H = 320, 180
LW, LH = 160, 90            # the light show's own resolution, doubled up to the screen
LINES = (("THANK YOU FOR", 2), ("TRIPPING WITH", 2), ("THE LIFE LAB!", 2), ("YOU ARE", 3), ("AMAZING!", 3))
HUES = 24                   # rainbow steps the letters cycle through
MIN_TIME = SKIP_GRACE              # s before the button takes you back, so the press that opened it doesn't


def _palette(shift: float, sat: float = 1.0) -> list[tuple[int, int, int]]:
    out = []
    for i in range(256):
        h = (i / 256 + shift) % 1.0
        v = 0.65 + 0.35 * math.sin(i / 256 * math.tau * 3 + shift * 9)
        r, g, b = colorsys.hsv_to_rgb(h, sat, v)
        out.append((int(r * 255), int(g * 255), int(b * 255)))
    return out


def _indexed(value) -> pygame.Surface:
    """An 8-bit LW x LH picture whose pixel (x, y) is palette entry value(x, y)."""
    surf = pygame.Surface((LW, LH), depth=8)
    surf.set_palette(_palette(0))
    for y in range(LH):
        for x in range(LW):
            surf.set_at((x, y), int(value(x, y)) % 256)
    return surf


def _plasma(x: int, y: int) -> float:
    cx, cy = x - LW / 2, y - LH / 2
    v = (math.sin(x / 9) + math.sin(y / 7) + math.sin((x + y) / 13)
         + math.sin(math.hypot(cx, cy) / 6) + math.sin(math.hypot(x - 20, y - 70) / 11))
    return (v + 5) / 10 * 255 * 2


def _tunnel(x: int, y: int) -> float:
    cx, cy = x - LW / 2, (y - LH / 2) * 1.6
    d = math.hypot(cx, cy) + 0.001
    return (math.atan2(cy, cx) / math.tau * 256 * 3 + 900 / d) % 256


class Trip:
    def __init__(self) -> None:
        self.t = 0.0
        self.done = False
        self.plasma = _indexed(_plasma)
        self.tunnel = _indexed(_tunnel)
        self.glyphs: dict[tuple[str, int, int], pygame.Surface] = {}

    def update(self, dt: float, sx: int, act: bool) -> None:
        self.t += dt
        if self.t > MIN_TIME and (act or sx < 0):
            self.done = True

    @staticmethod
    def _render(s: str, color: str, scale: int) -> pygame.Surface:
        c = Canvas(max(1, big_width(s)), BIG_H)
        draw_big_text(c, 0, 0, s, color)
        surf = to_surface(c)
        return pygame.transform.scale(surf, (surf.get_width() * scale, surf.get_height() * scale))

    def _glyph(self, ch: str, hue: int, scale: int) -> pygame.Surface:
        key = (ch, hue, scale)
        if key not in self.glyphs:
            if hue < 0:
                color = "#1a0420"                                # the dark outline
            else:
                r, g, b = colorsys.hsv_to_rgb(hue / HUES, 0.55, 1.0)
                color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
            self.glyphs[key] = self._render(ch, color, scale)
        return self.glyphs[key]

    def draw(self, screen: pygame.Surface) -> None:
        t = self.t
        self.plasma.set_palette(_palette(t * 0.12))
        self.tunnel.set_palette(_palette(-t * 0.3 + 0.5))
        screen.blit(pygame.transform.scale(self.plasma, (W, H)), (0, 0))   # scaled copies keep the palette
        k = 0.5 + 0.5 * math.sin(t * 0.7)                        # the tunnel breathes in and out
        tun = pygame.transform.scale(self.tunnel, (W, H))
        tun.set_alpha(int(60 + 120 * k))
        screen.blit(tun, (0, 0))

        y = (H - sum(BIG_H * sc + 7 for _, sc in LINES) - 4) // 2   # the block of text, centred
        for n, (line, scale) in enumerate(LINES):
            x0 = W // 2 - big_width(line) * scale // 2
            step = 6 * scale
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                wob = math.sin(t * 4 + i * 0.6 + n * 1.1)
                x = x0 + i * step + round(math.cos(t * 3 + i) * scale * 0.7)
                yy = y + round(wob * (2 + scale))
                hue = int(t * 10 + i + n * 4) % HUES
                dark = self._glyph(ch, -1, scale)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (2, 2)):
                    screen.blit(dark, (x + dx, yy + dy))
                screen.blit(self._glyph(ch, hue, scale), (x, yy))
            y += BIG_H * scale + (10 if n == 2 else 7)
        if self.t > MIN_TIME:
            hint = prompt_text("TAP BUTTON: BACK")
            screen.fill((10, 0, 20), (W - 8 - hint.get_width(), H - 12, hint.get_width() + 6, BIG_H + 4))
            screen.blit(hint, (W - 5 - hint.get_width(), H - 10))
