"""How-to-play screen shared by every mini-game: the title, a one-line premise,
then a few pages that each show one rule with a tiny looping demo built from the
game's own sprites, plus an arcade stick and button that wiggle and press in
time with it.

A game builds a Tutorial with its pages, calls update/draw while its title
phase runs, and starts the round once `done` goes True.

    BUTTON        next page; on the last page, start
    STICK LEFT    back a page
Pages also turn on their own after `Page.time` seconds, and stop on the last one.

A page's demo draws into a DEMO_W x DEMO_H surface and returns what the controls
should be doing at that moment: (stick x, stick y, button down), so the stick
icon moves exactly when the sprite does.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import pygame

from sprites.palette import LAB_DIM, LAB_TEXT
from sprites.viewer import H, W, text_surface

from .shell import Input

DEMO_X, DEMO_Y, DEMO_W, DEMO_H = 74, 32, 238, 104
PAGE_TIME = 4.5                  # s a page shows before turning on its own
MIN_SHOW = 0.35                  # s before a press counts (so the button that started the game doesn't skip)
SLIDE = 0.25                     # s for a page to slide in

Controls = tuple[int, int, bool]
Demo = Callable[[pygame.Surface, float], "Controls | list[Controls] | None"]   # a list: one per control icon

INK = (20, 12, 28)
PANEL = (26, 20, 44)
FRAME = (90, 78, 130)
STICK_BALL, STICK_BALL_HI = (232, 59, 59), (255, 150, 140)
BUTTON, BUTTON_HI, BUTTON_DOWN = (255, 225, 77), (255, 248, 190), (190, 150, 30)


@dataclass
class Page:
    caption: tuple[str, ...]                       # one or two lines under the demo
    demo: Demo
    controls: tuple[str, ...] = ("stick",)         # icons in the left column: "stick", "button", "stick2", "jar"
    time: float = PAGE_TIME


@dataclass
class Tutorial:
    title: str
    premise: str                                   # the theory, in one line
    pages: list[Page]
    labels: dict[str, str] = field(default_factory=lambda: {"stick": "STICK", "button": "BUTTON",
                                                            "stick2": "STICK 2", "jar": "SPIT JAR"})
    accent: str = "#ffe14d"
    page: int = 0
    t: float = 0.0                                 # s on this page
    time: float = 0.0                              # s since the screen opened
    done: bool = False
    held_x: int = 0

    def __post_init__(self) -> None:
        self.canvas = pygame.Surface((DEMO_W, DEMO_H))
        self.shade = pygame.Surface((W, H), pygame.SRCALPHA)
        self.shade.fill((*INK, 232))
        self._title = big(self.title, self.accent)
        self._premise = text_surface(self.premise, LAB_DIM)
        self._captions = [[text_surface(line, LAB_TEXT) for line in p.caption] for p in self.pages]
        self._labels = {k: text_surface(v, LAB_DIM) for k, v in self.labels.items()}
        self._next = text_surface("BUTTON: NEXT", LAB_DIM)
        self._start = text_surface("PRESS BUTTON TO START", self.accent)

    @property
    def last(self) -> bool:
        return self.page == len(self.pages) - 1

    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.t += dt
        pressed = inp.action or any(p.action for p in inp.players)
        x = inp.x or next((p.x for p in inp.players if p.x), 0)
        if pressed and self.time > MIN_SHOW and self.t > MIN_SHOW:
            if self.last:
                self.done = True
            else:
                self._turn(1)
        elif x < 0 and self.held_x >= 0 and self.page > 0:
            self._turn(-1)
        elif x > 0 and self.held_x <= 0 and not self.last:
            self._turn(1)
        elif not self.last and self.t >= self.pages[self.page].time:
            self._turn(1)
        self.held_x = x

    def _turn(self, step: int) -> None:
        self.page += step
        self.t = 0.0

    def draw(self, screen: pygame.Surface) -> None:
        """Over whatever the game drew behind it (its playfield, dimmed)."""
        screen.blit(self.shade, (0, 0))
        drop = max(0.0, 1 - self.time / 0.4)                 # the title drops in when the screen opens
        bounce = round(-24 * drop * drop + 2 * math.sin(self.time * 3))
        screen.blit(self._title, (W // 2 - self._title.get_width() // 2, 4 + bounce))
        screen.blit(self._premise, (W // 2 - self._premise.get_width() // 2, 22))

        p = self.pages[self.page]
        self.canvas.fill(PANEL)
        out = p.demo(self.canvas, self.t) or (0, 0, False)
        controls = out if isinstance(out, list) else [out] * len(p.controls)
        slide = max(0.0, 1 - self.t / SLIDE)
        dx = round(slide * slide * 30)                       # each page slides in from the left
        frame = pygame.Rect(DEMO_X - 2, DEMO_Y - 2, DEMO_W + 4, DEMO_H + 4)
        pygame.draw.rect(screen, INK, frame.inflate(2, 2))
        pygame.draw.rect(screen, FRAME, frame, 1)
        screen.fill(PANEL, (DEMO_X, DEMO_Y, DEMO_W, DEMO_H))
        screen.blit(self.canvas, (DEMO_X + dx, DEMO_Y), (0, 0, DEMO_W - dx, DEMO_H))

        # the controls, acting it out
        n = len(p.controls)
        for i, kind in enumerate(p.controls):
            cy = DEMO_Y + DEMO_H // 2 + round((i - (n - 1) / 2) * 44) - 4
            sx, sy, down = controls[i]
            if kind == "button":
                draw_button(screen, 37, cy, down)
            elif kind == "jar":
                draw_jar(screen, 37, cy, down, self.time)
            else:
                draw_stick(screen, 37, cy, sx, sy)
            label = self._labels[kind]
            screen.blit(label, (37 - label.get_width() // 2, cy + 16))

        y = DEMO_Y + DEMO_H + 6
        for s in self._captions[self.page]:
            screen.blit(s, (DEMO_X + DEMO_W // 2 - s.get_width() // 2, y))
            y += 8

        # page dots and the prompt
        for i in range(len(self.pages)):
            col = self.accent if i == self.page else "#5a4e7a"
            pygame.draw.rect(screen, col, (8 + i * 7, H - 9, 4, 4))
        prompt = self._start if self.last else self._next
        if not self.last or int(self.time * 2.5) % 2 == 0:
            screen.blit(prompt, (W - prompt.get_width() - 6, H - 9))


def big(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


def draw_stick(screen: pygame.Surface, cx: int, cy: int, sx: int, sy: int) -> None:
    """A ball-top arcade stick seen from the front, leaning toward (sx, sy)."""
    pygame.draw.ellipse(screen, INK, (cx - 15, cy + 5, 30, 10))
    pygame.draw.ellipse(screen, (60, 52, 84), (cx - 14, cy + 5, 28, 8))
    pygame.draw.ellipse(screen, (110, 100, 140), (cx - 14, cy + 4, 28, 7), 1)
    if sx or sy:                                          # little arrows showing where it's pushed
        ax, ay = cx + sx * 15, cy - 4 + sy * 11
        pts = [(ax + sx * 4, ay + sy * 4), (ax - sy * 3, ay + sx * 3), (ax + sy * 3, ay - sx * 3)]
        pygame.draw.polygon(screen, STICK_BALL_HI, pts)
    tx, ty = cx + sx * 7, cy - 9 + sy * 4 + (2 if sy > 0 else 0)
    pygame.draw.line(screen, INK, (cx, cy + 8), (tx, ty + 2), 4)
    pygame.draw.line(screen, (150, 150, 165), (cx, cy + 8), (tx, ty + 2), 2)
    pygame.draw.circle(screen, INK, (tx, ty), 7)
    pygame.draw.circle(screen, STICK_BALL, (tx, ty), 6)
    pygame.draw.circle(screen, STICK_BALL_HI, (tx - 2, ty - 2), 2)


def draw_button(screen: pygame.Surface, cx: int, cy: int, down: bool) -> None:
    """A round arcade button, pushed in while `down`."""
    pygame.draw.ellipse(screen, INK, (cx - 13, cy - 2, 26, 16))
    pygame.draw.ellipse(screen, (60, 52, 84), (cx - 12, cy - 1, 24, 13))
    top = cy + (3 if down else 0)
    if not down:
        pygame.draw.rect(screen, BUTTON_DOWN, (cx - 9, top + 1, 18, 4))
    pygame.draw.ellipse(screen, INK, (cx - 10, top - 4, 20, 12))
    pygame.draw.ellipse(screen, BUTTON_DOWN if down else BUTTON, (cx - 9, top - 3, 18, 10))
    if not down:
        pygame.draw.ellipse(screen, BUTTON_HI, (cx - 5, top - 2, 7, 3))
    else:
        for a in range(0, 360, 45):                       # a little click flash
            r = math.radians(a)
            p0 = (cx + math.cos(r) * 14, cy + 2 + math.sin(r) * 10)
            p1 = (cx + math.cos(r) * 18, cy + 2 + math.sin(r) * 13)
            pygame.draw.line(screen, BUTTON_HI, p0, p1)


def draw_jar(screen: pygame.Surface, cx: int, cy: int, down: bool, t: float) -> None:
    """The spit jar on its scale. `down`: a gob is landing in it right now."""
    pygame.draw.rect(screen, INK, (cx - 13, cy + 7, 26, 6))                 # the scale
    pygame.draw.rect(screen, (110, 100, 140), (cx - 12, cy + 8, 24, 4))
    pygame.draw.rect(screen, (60, 52, 84), (cx - 12, cy + 11, 24, 1))
    jar = pygame.Rect(cx - 9, cy - 12, 18, 20)
    pygame.draw.rect(screen, INK, jar.inflate(2, 2), border_radius=3)
    pygame.draw.rect(screen, (70, 96, 104), jar, border_radius=3)            # glass
    fill = 7 + (1 if down else 0)
    pygame.draw.rect(screen, (196, 220, 150), (jar.x + 1, jar.bottom - fill, jar.w - 2, fill - 1))   # spit
    pygame.draw.rect(screen, (240, 250, 210), (jar.x + 1, jar.bottom - fill, jar.w - 2, 1))
    pygame.draw.line(screen, (180, 220, 230), (jar.x + 2, jar.y + 3), (jar.x + 2, jar.y + 9))       # shine
    pygame.draw.rect(screen, INK, (cx - 10, cy - 15, 20, 4))                # rim
    pygame.draw.rect(screen, (150, 160, 170), (cx - 9, cy - 14, 18, 2))
    if down:                                                                 # splash
        for dx, dy in ((-6, -18), (0, -21), (6, -18)):
            pygame.draw.rect(screen, (220, 240, 190), (cx + dx, cy + dy, 2, 2))
    else:                                                                    # a gob on its way down
        y = cy - 30 + round((t * 40) % 14)
        pygame.draw.circle(screen, (220, 240, 190), (cx, y), 2)


# helpers for writing demos -------------------------------------------------------------
def loop(t: float, period: float) -> float:
    """0..1 through a repeating cycle."""
    return (t % period) / period


def ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def sign(v: float, dead: float = 0.0) -> int:
    return (v > dead) - (v < -dead)


def along(t: float, pts: list[tuple[float, float]], speed: float, closed: bool = True
          ) -> tuple[float, float, int, int]:
    """Position after t seconds at `speed` px/s along the polyline `pts` (looping round if
    closed, else holding at the end), plus the direction of travel (-1/0/+1 each), for the stick."""
    segs = list(zip(pts, pts[1:] + pts[:1] if closed else pts[1:]))
    lens = [math.dist(a, b) for a, b in segs]
    d = t * speed
    total = sum(lens)
    if closed:
        d %= total
    elif d >= total:
        (x0, y0), (x1, y1) = segs[-1]
        return x1, y1, 0, 0
    for (a, b), n in zip(segs, lens):
        if d <= n and n:
            k = d / n
            return a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, sign(b[0] - a[0]), sign(b[1] - a[1])
        d -= n
    return pts[0][0], pts[0][1], 0, 0


def blit_c(surf: pygame.Surface, img: pygame.Surface, x: float, y: float) -> None:
    """Blit centered on (x, y)."""
    surf.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() / 2)))


def caption(surf: pygame.Surface, text: str, x: float, y: float, color: str = LAB_TEXT) -> None:
    s = text_surface(text, color)
    surf.blit(s, (round(x - s.get_width() / 2), round(y)))
