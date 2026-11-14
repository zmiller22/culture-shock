"""How-to-play screen shared by every mini-game: an optional intro (the game's
theory typed out big on its own screen, see `Intro`), then the title over a few pages that each teach one thing, built from the game's own sprites,
with an arcade stick and button in a column on the left.

There are two kinds of page:

- A try-it page has a `trial`: a little live sandbox in the box where the player
  does the thing the caption says (fly the stork, drop a baby...). Doing it
  flashes NICE! and the next page slides in. Until they touch anything, the
  stick and button icons act out what to do; after that they mirror the
  player's own hands. If nobody manages it in TRY_TIME seconds, it moves on
  anyway, so no one gets stuck.
- A show-me page has only a looping `demo` (the rules, the win condition).
  The button turns it, and it turns on its own after `Page.time` seconds,
  except the last page, where the button starts the round.

Every page wears a badge saying which kind it is, WATCH or TRY IT!, and the
captions, control labels and prompts are drawn big in PROMPT (violet), saying
TAP or HOLD, so the instructions are the first thing anyone reads.

A game builds a Tutorial with its pages, calls update/draw while its title
phase runs, and starts the round once `done` goes True.

A page's demo draws into a DEMO_W x DEMO_H surface and returns what the controls
should be doing at that moment: (stick x, stick y, button down), so the stick
icon moves exactly when the sprite does. A trial (see `Trial`) draws the same
way and returns the same hint.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Protocol

import pygame

from sprites.font import BIG_H
from sprites.palette import LAB_DIM, LAB_TEXT
from sprites.viewer import H, W, text_surface

from .shell import PROMPT, Input, prompt_text

DEMO_X, DEMO_Y, DEMO_W, DEMO_H = 74, 32, 238, 104
PAGE_TIME = 4.5                  # s a page shows before turning on its own
MIN_SHOW = 0.35                  # s before a press counts (so the button that started the game doesn't skip)
SLIDE = 0.25                     # s for a page to slide in
TRY_TIME = 15.0                  # s a try-it page waits for the player to manage it before moving on anyway
CHEER_TIME = 1.1                 # s the NICE! shows before the next page
HANDS_OFF = 1.5                  # s after the player last touched anything that the icons go back to hinting
INTRO_TYPE = 0.05                # s per letter as the intro line types out
INTRO_HOLD = 1.8                 # s it stays up once it's all there
INTRO_FADE = 0.4                 # s fading in from, and out to, the dark
EXIT_HINT = False                # the main game turns this on: its exit menu opens on a held button, so the
EXIT_LINE = "DONE PLAYING? HOLD ANY BUTTON TO EXIT"   # last page says so (standalone, holding does nothing)

Controls = tuple[int, int, bool]
Demo = Callable[[pygame.Surface, float], "Controls | list[Controls] | None"]   # a list: one per control icon

INK = (20, 12, 28)
PANEL = (26, 20, 44)
FRAME = (90, 78, 130)
STICK_BALL, STICK_BALL_HI = (232, 59, 59), (255, 150, 140)
BUTTON, BUTTON_HI, BUTTON_DOWN = (255, 225, 77), (255, 248, 190), (190, 150, 30)


class Trial(Protocol):
    """A try-it sandbox: made fresh each time its page opens."""
    done: bool                                     # True once the player has done the thing
    cheer: str                                     # what flashes when they do (e.g. "NICE!")

    def update(self, dt: float, inp: Input) -> None: ...
    def draw(self, s: pygame.Surface, t: float) -> "Controls | list[Controls] | None": ...


@dataclass
class Page:
    caption: tuple[str, ...]                       # one or two lines under the box
    demo: Demo | None = None                       # a show-me page: a looping demo
    controls: tuple[str, ...] = ("stick",)         # icons in the left column: "stick", "button", "stick2", "jar"
    time: float = PAGE_TIME
    trial: Callable[[], Trial] | None = None       # a try-it page: makes the sandbox
    lock: float = 0.0                              # s the demo plays before the button does anything (and
                                                   # before the prompt shows), so nobody skips it by accident


class Intro:
    """The game's theory, typed out big over a heartbeat on a dark screen, then faded out.
    The button can't skip it until the whole line is there."""

    def __init__(self, text: str, accent: str) -> None:
        self.accent, self.t, self.done = accent, 0.0, False
        self.lines = [text]
        words = text.split()
        if outlined(text, accent).get_width() > W - 40 and len(words) > 1:   # two lines: after a full stop
            fits = [i for i in range(1, len(words))                         # if one fits, else most even
                    if max(outlined(" ".join(part), accent).get_width() for part in (words[:i], words[i:])) <= W - 16]
            cut = min(fits or range(1, len(words)), key=lambda i: (not words[i - 1].endswith("."),
                      abs(len(" ".join(words[:i])) - len(" ".join(words[i:])))))
            self.lines = [" ".join(words[:cut]), " ".join(words[cut:])]
            if not fits:                                                     # too long for two: wrap it,
                self.lines = []                                              # a new line for each sentence
                for word in words:
                    trial = f"{self.lines[-1]} {word}" if self.lines and not self.lines[-1].endswith(".") else None
                    if trial and outlined(trial, accent).get_width() <= W - 16:
                        self.lines[-1] = trial
                    else:
                        self.lines.append(word)
        self.chars = sum(len(line) for line in self.lines) + len(self.lines) - 1
        self.typed_at = INTRO_FADE + self.chars * INTRO_TYPE
        self.length = self.typed_at + INTRO_HOLD + INTRO_FADE
        self.ring = pygame.Color(PANEL).lerp(pygame.Color(accent), 0.18)
        self.shade = pygame.Surface((W, H))
        self.shade.fill(INK)
        self._typed: tuple[int, list] | None = None   # letters typed, and each line's (width, height, typed bit)

    def update(self, dt: float, inp: Input) -> None:
        self.t += dt
        pressed = inp.action or any(p.action for p in inp.players)
        if self.t >= self.length or (pressed and self.t > self.typed_at + 0.3):
            self.done = True

    def draw(self, screen: pygame.Surface) -> None:
        t = self.t
        screen.fill(INK)
        pulse = (1 - (t * 2) % 1) ** 3                 # the heartbeat, 120 BPM
        for i in range(6, 0, -1):
            r = i * 22 + pulse * 5 + (t * 12) % 22
            pygame.draw.ellipse(screen, self.ring, (W // 2 - r * 1.6, H // 2 - r * 0.9, r * 3.2, r * 1.8), 2)
        n = max(0, min(self.chars, int((t - INTRO_FADE) / INTRO_TYPE)))
        if n and (self._typed is None or self._typed[0] != n):
            imgs, left = [], n                         # type into each line where it'll end up, so nothing jumps
            for line in self.lines:
                full = outlined(line, self.accent)
                part = outlined(line[:left], self.accent) if left > 0 else None
                imgs.append((full.get_width(), full.get_height(), part))
                left -= len(line) + 1
            self._typed = (n, imgs)
        if n:
            gap = 4
            y = H // 2 - (sum(h for _, h, _ in self._typed[1]) + gap * (len(self.lines) - 1)) // 2
            for w_full, h, part in self._typed[1]:
                if part:
                    screen.blit(part, (W // 2 - w_full // 2, y))
                y += h + gap
        dark = max(1 - t / INTRO_FADE, (t - (self.length - INTRO_FADE)) / INTRO_FADE)
        if dark > 0:
            self.shade.set_alpha(round(255 * min(1.0, dark)))
            screen.blit(self.shade, (0, 0))


@dataclass
class Tutorial:
    title: str
    premise: str                                   # the theory, in one line under the title ("" for none)
    pages: list[Page]
    labels: dict[str, str] = field(default_factory=lambda: {"stick": "STICK", "button": "BUTTON",
                                                            "stick2": "STICK 2", "jar": "SPIT JAR"})
    accent: str = "#ffe14d"
    intro: str = ""                                # the theory, typed out on its own screen before the pages
    page: int = 0
    t: float = 0.0                                 # s on this page
    time: float = 0.0                              # s since the screen opened
    done: bool = False
    trial: Trial | None = None                     # the live sandbox on a try-it page
    cheer_t: float | None = None                   # s since they managed it
    touched: float = -99.0                         # self.time they last touched a control
    hands: tuple[Input, ...] = ()                  # this tick's input, per player, for the icons
    merged: Input = field(default_factory=Input)   # this tick's input from every stick and button

    def __post_init__(self) -> None:
        self.canvas = pygame.Surface((DEMO_W, DEMO_H))
        self.shade = pygame.Surface((W, H), pygame.SRCALPHA)
        self.shade.fill((*INK, 232))
        self._title = big(self.title, self.accent)
        self._premise = text_surface(self.premise, LAB_DIM)
        self._badges = {kind: badge(kind) for kind in ("WATCH", "TRY IT!")}
        self._intro = Intro(self.intro, self.accent) if self.intro else None
        self._open()

    @property
    def last(self) -> bool:
        return self.page == len(self.pages) - 1

    def update(self, dt: float, inp: Input) -> None:
        if self._intro:                            # the intro first; the pages start fresh after it
            self._intro.update(dt, inp)
            if self._intro.done:
                self._intro = None
            return
        self.time += dt
        self.t += dt
        pressed = inp.action or any(p.action for p in inp.players)
        self.hands = inp.players or (inp,)
        self.merged = inp
        if inp.x or inp.y or inp.held or pressed or any(p.x or p.y or p.action for p in inp.players):
            self.touched = self.time
        if self.trial:
            if self.cheer_t is not None:
                self.cheer_t += dt
                if self.cheer_t >= CHEER_TIME:
                    self._turn()
                return
            if self.t > MIN_SHOW:                  # (so the press that turned the page isn't a go)
                self.trial.update(dt, inp)
            if self.trial.done:
                self.cheer_t = 0.0
            elif self.t >= TRY_TIME:
                self._turn()
            return
        if pressed and self.time > MIN_SHOW and self.t > max(MIN_SHOW, self.pages[self.page].lock):
            if self.last:
                self.done = True
            else:
                self._turn()
        elif not self.last and self.t >= self.pages[self.page].time:
            self._turn()

    def _turn(self) -> None:
        if self.last:
            self.done = True
            return
        self.page += 1
        self._open()

    def _open(self) -> None:
        self.t, self.cheer_t = 0.0, None
        make = self.pages[self.page].trial
        self.trial = make() if make else None

    def _icons(self, hint: "Controls | list[Controls] | None", kinds: tuple[str, ...]) -> list[Controls]:
        """What each control icon shows: the hint, or the player's own hands once they've touched them."""
        hint = hint or (0, 0, False)
        hints = hint if isinstance(hint, list) else [hint] * len(kinds)
        if not self.trial or self.time - self.touched > HANDS_OFF:
            return hints
        out = []
        for i, kind in enumerate(kinds):
            if "stick2" in kinds:                    # two players: each icon is one player's hands
                p = self.hands[min(1 if kind == "stick2" else 0, len(self.hands) - 1)] if self.hands else Input()
            else:                                    # one player: either stick, any button
                p = self.merged
            out.append((0, 0, bool(p.held or p.action)) if kind in ("button", "jar") else (p.x, p.y, False))
        return out

    def draw(self, screen: pygame.Surface) -> None:
        """Over whatever the game drew behind it (its playfield, dimmed)."""
        if self._intro:
            self._intro.draw(screen)
            return
        screen.blit(self.shade, (0, 0))
        drop = max(0.0, 1 - self.time / 0.4)                 # the title drops in when the screen opens
        bounce = round(-24 * drop * drop + 2 * math.sin(self.time * 3))
        screen.blit(self._title, (W // 2 - self._title.get_width() // 2, 4 + bounce))
        if self.premise:
            screen.blit(self._premise, (W // 2 - self._premise.get_width() // 2, 22))

        p = self.pages[self.page]
        self.canvas.fill(PANEL)
        out = self.trial.draw(self.canvas, self.t) if self.trial else p.demo(self.canvas, self.t)
        controls = self._icons(out, p.controls)
        if self.cheer_t is not None:                         # they did it
            cheer = big(self.trial.cheer, self.accent)
            k = min(1.0, self.cheer_t / 0.15)
            img = pygame.transform.scale_by(cheer, 0.6 + 0.4 * k)
            blit_c(self.canvas, img, DEMO_W / 2, DEMO_H / 2 - 4 * math.sin(self.cheer_t * 8))
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
            label = prompt_text(self.labels[kind])
            screen.blit(label, (37 - label.get_width() // 2, cy + 15))

        y = DEMO_Y + DEMO_H + 4
        for s in map(prompt_text, p.caption):                # big, so centred on the whole screen to fit
            screen.blit(s, (W // 2 - s.get_width() // 2, y))
            y += BIG_H + 2

        if self.last and EXIT_HINT:                          # the way out, on the last page
            s = prompt_text(EXIT_LINE)
            screen.blit(s, (W // 2 - s.get_width() // 2, H - 2 * BIG_H - 4))

        # WATCH or TRY IT!, top left over the controls column
        b = self._badges["TRY IT!" if self.trial else "WATCH"]
        screen.blit(b, (37 - b.get_width() // 2, DEMO_Y))

        # page dots and the prompt
        for i in range(len(self.pages)):
            col = self.accent if i == self.page else "#5a4e7a"
            pygame.draw.rect(screen, col, (8 + i * 7, H - 9, 4, 4))
        if self.trial:
            prompt = prompt_text("YOUR TURN: TRY IT!") if self.cheer_t is None else None
        else:
            prompt = prompt_text("TAP BUTTON TO START" if self.last else "TAP BUTTON: NEXT") if self.t >= p.lock else None
        if prompt:                                           # (it flashes colour, see prompt_color)
            screen.blit(prompt, (W - prompt.get_width() - 6, H - BIG_H - 2))
        if self.trial and self.cheer_t is None and self.t > TRY_TIME - 5:       # running out: a bar shrinks
            k = (TRY_TIME - self.t) / 5
            pygame.draw.rect(screen, "#5a4e7a", (DEMO_X, DEMO_Y + DEMO_H + 2, round(DEMO_W * k), 1))


def badge(text: str) -> pygame.Surface:
    """WATCH / TRY IT!: dark letters on a violet tag."""
    t = prompt_text(text, "#140c1c")
    out = pygame.Surface((t.get_width() + 8, BIG_H + 6))
    out.fill(PROMPT)
    out.blit(t, (4, 3))
    return out


def big(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


def outlined(text: str, color: str, scale: int = 2) -> pygame.Surface:
    """Big text with a dark outline."""
    fg, bg = big(text, color, scale), big(text, "#140c1c", scale)
    o = max(1, scale // 2)
    out = pygame.Surface((fg.get_width() + 2 * o, fg.get_height() + 2 * o), pygame.SRCALPHA)
    for dx in (-o, 0, o):
        for dy in (-o, 0, o):
            out.blit(bg, (o + dx, o + dy))
    out.blit(fg, (o, o))
    return out


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
