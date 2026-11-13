"""The opening of the program: green code rain, then the cosmic zoom-out.

`Rain` is falling columns of phosphor characters. It draws onto any surface,
so it runs on the CRT and then fills the screen as the camera dives in.

`Cosmos` is the Powers-of-Ten zoom from the Earth out to a universe in a jar,
with labels and the props along the way. It has the same update/draw/done
shape as a mini-game, so the main game just runs it until `done`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from minigames.primordial_soup.art import utensil
from minigames.stork_bomber.art import FSM_FRAMES, spaghetti_monster, stork
from sprites.canvas import hex_to_rgba
from sprites.font import GLYPHS
from sprites.viewer import H, W, text_surface, to_surface

from . import space_art as sa
from .art import PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT

# -- tuning ------------------------------------------------------------------------
RAIN_COL, RAIN_ROW = 4, 6                  # px per character cell
RAIN_SPEED = (40.0, 110.0)                 # px/s a column falls
RAIN_TRAIL = (5, 14)                       # characters per column
RAIN_RAMP = 0.8                            # s for the rain to go from a few columns to all of them
ZOOM_HOLD = 1.1                            # s the camera rests on each level (labels show here)
ZOOM_MOVE = 1.25                           # s to zoom out to the next level
FINAL_HOLD = 1.8
FADE_IN = 0.7                              # levels of zoom over which an outer level fades in                           # s on the last level: the jar
FADE_OUT = 1.4                             # s zooming on into the dark at the end
K0 = 1.25                                  # screen px per canvas px when a level is "current"
STARS = 160

RAIN_GLYPHS = [ch for ch in GLYPHS if ch not in " .'"]


def rgb(c: str) -> tuple[int, int, int]:
    return hex_to_rgba(c)[:3]


class Rain:
    """Falling columns of characters, matrix style."""

    COLORS = ("#eaffea", PHOSPHOR, PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_DIM, PHOSPHOR_FAINT)

    def __init__(self, w: int, h: int, seed: int | None = None) -> None:
        self.w, self.h = w, h
        self.rng = random.Random(seed)
        self.t = 0.0
        self.cols = []
        for i in range(w // RAIN_COL):
            self.cols.append(self._column(i, start=self.rng.uniform(-h * 1.5, 0)))
        self.order = list(range(len(self.cols)))
        self.rng.shuffle(self.order)               # which columns switch on first
        self.glyphs = {(ch, col): text_surface(ch, col) for ch in RAIN_GLYPHS for col in self.COLORS}

    def _column(self, i: int, start: float) -> dict:
        n = self.rng.randint(*RAIN_TRAIL)
        return {"x": i * RAIN_COL, "y": start, "speed": self.rng.uniform(*RAIN_SPEED),
                "chars": [self.rng.choice(RAIN_GLYPHS) for _ in range(n)]}

    def update(self, dt: float) -> None:
        self.t += dt
        live = int(len(self.cols) * min(1.0, 0.15 + self.t / RAIN_RAMP))
        for k in self.order[:live]:
            col = self.cols[k]
            col["y"] += col["speed"] * dt
            if self.rng.random() < dt * 8:          # the characters keep changing
                col["chars"][self.rng.randrange(len(col["chars"]))] = self.rng.choice(RAIN_GLYPHS)
            if col["y"] - len(col["chars"]) * RAIN_ROW > self.h:
                self.cols[k] = self._column(k, start=self.rng.uniform(-30, 0))
        self.live = set(self.order[:live])

    def draw(self, surf: pygame.Surface) -> None:
        for k in getattr(self, "live", ()):
            col = self.cols[k]
            head = int(col["y"] // RAIN_ROW) * RAIN_ROW
            n = len(col["chars"])
            for j, ch in enumerate(col["chars"]):
                y = head - j * RAIN_ROW
                if -RAIN_ROW < y < self.h:
                    shade = self.COLORS[min(len(self.COLORS) - 1, j * len(self.COLORS) // n)]
                    surf.blit(self.glyphs[(ch, shade)], (col["x"], y))


# -- the cosmic zoom ---------------------------------------------------------------------

@dataclass
class Prop:
    frames: list[pygame.Surface]
    u: float                                   # where it sits in its level's canvas
    v: float
    size: float = 1.0                          # canvas px per sprite px
    fps: float = 8.0
    orbit: tuple[float, float] | None = None   # radius (canvas px), degrees/s around (u, v)
    spin: float = 0.0                          # degrees/s
    hop: float = 0.0                           # canvas px it bounces up and down
    label: tuple[str, str] | None = None


@dataclass
class Level:
    back: pygame.Surface
    labels: list[tuple[float, float, float, str, str]] = field(default_factory=list)  # u, v, radius, line 1, line 2
    props: list[Prop] = field(default_factory=list)
    front: pygame.Surface | None = None
    scale: str = ""


def _surf(c) -> pygame.Surface:
    return to_surface(c)


def build_levels() -> list[Level]:
    stork_frames = [_surf(stork(f, True)) for f in range(4)]
    fsm_frames = [_surf(spaghetti_monster(f)) for f in range(FSM_FRAMES)]
    cow_frames = [_surf(sa.cow(f)) for f in range(2)]
    cx, cy = sa.CX, sa.CY
    return [
        Level(_surf(sa.earth_level()), scale="1E+07 M",
              labels=[(cx, cy, 52, "EARTH", "POP. 8 BILLION AND RISING")],
              props=[Prop(stork_frames, cx, cy, size=0.32, orbit=(62, 40), label=("A STORK", "MAKING A DELIVERY"))]),
        Level(_surf(sa.moon_level()), scale="1E+09 M",
              labels=[(*sa.MOON, -6, "THE MOON", "")],
              props=[Prop(cow_frames, sa.MOON[0] + 16, sa.MOON[1] - 4, size=0.55, fps=4, hop=3,
                          label=("A COW", "JUMPING OVER IT"))]),
        Level(_surf(sa.inner_level()), scale="1E+11 M",
              labels=[(*sa.SUN, 13, "THE SUN", "LOOKING COOL")],
              props=[Prop([_surf(sa.teapot())], *sa.TEAPOT_AT, size=0.6, hop=1,
                          label=("RUSSELL'S TEAPOT", "YOU CAN'T PROVE IT ISN'T")),
                     Prop([_surf(utensil("dildo"))], *sa.DILDO_AT, size=0.6, spin=90,
                          label=("A DILDO", "DON'T ASK"))]),
        Level(_surf(sa.outer_level()), scale="1E+13 M",
              labels=[(*sa.URANUS, 6, "URANUS", "HEH"), (*sa.SATURN, 6, "SATURN", "")],
              props=[Prop(fsm_frames, *sa.FSM_AT, size=0.55, fps=8, hop=2,
                          label=("FLYING SPAGHETTI MONSTER", "R'AMEN"))]),
        Level(_surf(sa.milky_way_level()), scale="1E+21 M",
              labels=[(sa.CX + 2, sa.BOOBS[0][1], 36, "THE MILKY WAY", "BOTH OF THEM"),
                      (*sa.YOU_ARE_HERE, -3, "YOU ARE HERE", "V")]),
        Level(_surf(sa.brain_level()), scale="1E+25 M",
              labels=[(sa.BRAIN[0], sa.BRAIN[1], -(sa.BRAIN[3] + 2), "THE COSMIC WEB", "WAIT. IS THAT A BRAIN?")]),
        Level(_surf(sa.jar_level()), front=_surf(sa.jar_front()), scale="ONE SHELF",
              labels=[(sa.CX, sa.CY - 44, -6, "SPECIMEN: THE UNIVERSE", "PROPERTY OF LIFE LAB")]),
    ]


_LEVELS: list[Level] | None = None


class Cosmos:
    def __init__(self, seed: int | None = None) -> None:
        global _LEVELS
        _LEVELS = _LEVELS or build_levels()
        self.levels = _LEVELS
        self.rng = random.Random(seed)
        self.t = 0.0
        self.z = 0.0
        self.done = False
        n = len(self.levels) - 1
        self.length = n * (ZOOM_HOLD + ZOOM_MOVE) + FINAL_HOLD + FADE_OUT
        self.stars = [self._star(anywhere=True) for _ in range(STARS)]
        self.text: dict[tuple[str, str], pygame.Surface] = {}
        self.scanlines = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 2):
            self.scanlines.fill((0, 0, 0, 45), (0, y, W, 1))

    def _star(self, anywhere: bool = False) -> list[float]:
        if anywhere:
            x, y = self.rng.uniform(-W, W), self.rng.uniform(-H, H)
        else:                                            # zooming out: new stars come in from the edges
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(190, 260)
            x, y = r * math.cos(a), r * math.sin(a)
        # the last item is how close to the middle it gets before it's too far away to see,
        # so stars don't pile up in the middle as the camera pulls back
        return [x, y, self.rng.choice((0.35, 0.5, 0.7, 1.0)), self.rng.random() < 0.08, self.rng.uniform(2, 110)]

    def _label(self, s: str, col: str) -> pygame.Surface:
        if (s, col) not in self.text:
            self.text[(s, col)] = text_surface(s, col)
        return self.text[(s, col)]

    def z_at(self, t: float) -> float:
        n = len(self.levels) - 1
        seg = ZOOM_HOLD + ZOOM_MOVE
        if t < n * seg:
            i, local = int(t // seg), t % seg
            if local < ZOOM_HOLD:
                return float(i)
            k = (local - ZOOM_HOLD) / ZOOM_MOVE
            return i + k * k * (3 - 2 * k)               # ease in and out of each level
        t -= n * seg
        if t < FINAL_HOLD:
            return float(n)
        k = min(1.0, (t - FINAL_HOLD) / FADE_OUT)
        return n + k * k * 1.2

    def skip(self) -> None:
        self.done = True

    def update(self, dt: float) -> None:
        self.t += dt
        z = self.z_at(self.t)
        shrink = sa.SCALE ** -(z - self.z)
        self.z = z
        for i, s in enumerate(self.stars):
            s[0] *= shrink
            s[1] *= shrink
            if math.hypot(s[0], s[1]) < s[4]:
                self.stars[i] = self._star()
        if self.t >= self.length:
            self.done = True

    # -- drawing -----------------------------------------------------------------------
    def _factor(self, i: int) -> float:
        return K0 * sa.SCALE ** (i - self.z)

    def _to_screen(self, i: int, u: float, v: float) -> tuple[float, float]:
        f = self._factor(i)
        return W / 2 + (u - sa.CX) * f, H / 2 + (v - sa.CY) * f

    def _alpha(self, i: int) -> int:
        """Outer levels fade in as the camera pulls back to them, so their middles
        never show blown up over the level you're looking at."""
        return int(255 * max(0.0, min(1.0, (self.z - (i - 1)) / FADE_IN)))

    def _blit_level(self, screen: pygame.Surface, surf: pygame.Surface, f: float, alpha: int = 255) -> None:
        ox, oy = W / 2 - sa.CX * f, H / 2 - sa.CY * f
        u0, u1 = max(0, math.floor(-ox / f)), min(sa.CW, math.ceil((W - ox) / f))
        v0, v1 = max(0, math.floor(-oy / f)), min(sa.CH, math.ceil((H - oy) / f))
        if u1 <= u0 or v1 <= v0:
            return
        x0, x1 = round(ox + u0 * f), round(ox + u1 * f)
        y0, y1 = round(oy + v0 * f), round(oy + v1 * f)
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        sub = surf.subsurface((u0, v0, u1 - u0, v1 - v0))
        scale = pygame.transform.smoothscale if f < 1 else pygame.transform.scale
        img = scale(sub, (x1 - x0, y1 - y0))
        if alpha < 255:
            img.set_alpha(alpha)
        screen.blit(img, (x0, y0))

    def _prop_pos(self, p: Prop) -> tuple[float, float]:
        u, v = p.u, p.v
        if p.orbit:
            r, speed = p.orbit
            a = math.radians(self.t * speed)
            u, v = u + r * math.cos(a), v + r * 0.45 * math.sin(a)
        if p.hop:
            v -= abs(math.sin(self.t * 3.0)) * p.hop
        return u, v

    def _draw_prop(self, screen: pygame.Surface, i: int, p: Prop, alpha: int = 255) -> None:
        f = self._factor(i) * p.size
        img = p.frames[int(self.t * p.fps) % len(p.frames)]
        w, h = img.get_width() * f, img.get_height() * f
        if w < 1 or w > W * 3:
            return
        if p.orbit and math.sin(math.radians(self.t * p.orbit[1])) < 0:
            img = pygame.transform.flip(img, True, False)      # fly the way it's going
        img = pygame.transform.scale(img, (max(1, round(w)), max(1, round(h))))
        if p.spin:
            img = pygame.transform.rotate(img, self.t * p.spin)
        x, y = self._to_screen(i, *self._prop_pos(p))
        if alpha < 255:
            img.set_alpha(alpha)
        screen.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))

    def _visible(self, i: int) -> bool:
        f = self._factor(i)
        return f * sa.CW >= 2 and self._alpha(i) > 0

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(rgb(sa.NIGHT))
        for x, y, b, big, _ in self.stars:
            c = (int(230 * b), int(235 * b), int(255 * b))
            px, py = int(W / 2 + x), int(H / 2 + y)
            screen.fill(c, (px, py, 1, 1))
            if big:
                screen.fill((c[0] // 2, c[1] // 2, c[2] // 2), (px - 1, py, 3, 1))
                screen.fill((c[0] // 2, c[1] // 2, c[2] // 2), (px, py - 1, 1, 3))

        n = len(self.levels)
        for i in reversed(range(n)):
            if not self._visible(i):
                continue
            lv = self.levels[i]
            a = self._alpha(i)
            self._blit_level(screen, lv.back, self._factor(i), a)
            for p in lv.props:
                self._draw_prop(screen, i, p, a)
        for i in reversed(range(n)):
            if self._visible(i) and self.levels[i].front:
                self._blit_level(screen, self.levels[i].front, self._factor(i), self._alpha(i))

        self._draw_labels(screen)
        self._draw_hud(screen)
        screen.blit(self.scanlines, (0, 0))
        # fade to black at the very end
        end = self.length - FADE_OUT * 0.6
        if self.t > end:
            k = min(1.0, (self.t - end) / (FADE_OUT * 0.6))
            dark = pygame.Surface((W, H))
            dark.set_alpha(int(255 * k))
            screen.blit(dark, (0, 0))

    def _draw_labels(self, screen: pygame.Surface) -> None:
        i = round(self.z)
        if i >= len(self.levels):
            return
        d = self.z - i
        if not -0.12 < d < 0.4:
            return
        alpha = int(255 * max(0.0, min(1.0, 1 - abs(d) / (0.12 if d < 0 else 0.4))))
        lv = self.levels[i]
        tags = list(lv.labels)
        for p in lv.props:
            if p.label:
                u, v = self._prop_pos(p)
                tags.append((u, v, p.frames[0].get_height() * p.size / 2, *p.label))
        f = self._factor(i)
        for u, v, r, a, b in tags:
            x, y = self._to_screen(i, u, v)
            rows = 2 if b else 1
            y = y + r * f + 3 if r >= 0 else y + r * f - 2 - 7 * rows      # negative radius: label above
            y = max(12, min(H - 12 - 7 * rows, y))
            for k, (s, col) in enumerate(((a, "#eaffea"), (b, PHOSPHOR_DIM))):
                if not s:
                    continue
                img = self._label(s, col)
                lx = max(2, min(W - img.get_width() - 2, x - img.get_width() / 2))
                ly = y + k * 7
                shadow = self._label(s, "#000000")
                shadow.set_alpha(alpha)
                img.set_alpha(alpha)
                screen.blit(shadow, (lx + 1, ly + 1))
                screen.blit(img, (lx, ly))

    def _draw_hud(self, screen: pygame.Surface) -> None:
        screen.blit(self._label("LIFE LAB MAINFRAME", PHOSPHOR_DIM), (4, 3))
        s = self._label("PROGRAM: GENESIS", PHOSPHOR_DIM)
        screen.blit(s, (W - 4 - s.get_width(), 3))
        i = min(len(self.levels) - 1, int(self.z + 0.5))
        screen.blit(self._label(f"SCALE: {self.levels[i].scale}", PHOSPHOR), (4, H - 9))
        s = self._label("BUTTON: SKIP", PHOSPHOR_FAINT)
        screen.blit(s, (W - 4 - s.get_width(), H - 9))
