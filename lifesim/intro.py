"""The opening of the program: green code rain, then the cosmic zoom-out.

`Rain` is falling columns of phosphor characters. It draws onto any surface,
so it runs on the CRT and then fills the screen as the camera dives in.

`Cosmos` is the Powers-of-Ten zoom from the Earth out to the big bang, four
stops: the Earth, the solar system, the Milky Way and the big bang. The camera
holds on each one long enough to get the joke, then glides smoothly out to
the next. It has the same update/draw/done
shape as a mini-game, so the main game just runs it until `done`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from minigames.it_takes_two.art import heart
from minigames.stork_bomber.art import stork
from sprites.canvas import hex_to_rgba
from sprites.font import GLYPHS
from sprites.viewer import H, W, text_surface, to_surface

from . import space_art as sa
from .art import PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT
from minigames.shell import SKIP_GRACE, prompt_color
from sprites.font import BIG_H, big_width, draw_big_text
from sprites.canvas import Canvas

# -- tuning ------------------------------------------------------------------------
RAIN_COL, RAIN_ROW = 4, 6                  # px per character cell
RAIN_SPEED = (40.0, 110.0)                 # px/s a column falls
RAIN_TRAIL = (5, 14)                       # characters per column
RAIN_RAMP = 0.8                            # s for the rain to go from a few columns to all of them
ZOOM_TEMPO = 1.3                           # the whole zoom-out runs this much faster than the times below
ZOOM_MOVE = 1.6 / ZOOM_TEMPO               # s to glide out from one stop to the next
# how long the camera holds on each stop (the levels' `hold`) is set in build_levels()
BIRTH_RATE = 4.3                           # babies born on Earth per second, roughly. One heart each.
HEART_LIFE = 2.0                           # s each heart floats up before it fades
FADE_IN = 0.7                              # levels of zoom over which an outer level fades in
FADE_OUT = 1.4 / ZOOM_TEMPO                # s zooming on into the dark at the end
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
    phase: float = 0.0                         # degrees round the orbit it starts at
    squash: float = 0.45                       # how flat the orbit is
    spin: float = 0.0                          # degrees/s
    hop: float = 0.0                           # canvas px it bounces up and down
    label: tuple[str, str] | None = None
    start: float = 0.0                         # s into the zoom its first frame shows (frames[0] before then)
    loop: bool = True                          # False: play the frames once and stay on the last


@dataclass
class Level:
    back: pygame.Surface
    labels: list[tuple[float, float, float, str, str]] = field(default_factory=list)  # u, v, radius, line 1, line 2
    props: list[Prop] = field(default_factory=list)
    front: pygame.Surface | None = None
    scale: str = ""
    hold: float = 3.0                          # s the camera stays on it
    fade_out: bool = False                     # fades away as the camera leaves it (the lab, into the flash)


def _surf(c) -> pygame.Surface:
    return to_surface(c)


def _text_frames(word: str, color: str, shadow: str, on: list[int], n: int) -> list[pygame.Surface]:
    """A word that pops up on some frames of an n-frame loop (and is blank on the rest)."""
    img = pygame.transform.scale_by(text_surface(word, color), 2)
    sh = pygame.transform.scale_by(text_surface(word, shadow), 2)
    pop = pygame.Surface((img.get_width() + 2, img.get_height() + 2), pygame.SRCALPHA)
    pop.blit(sh, (2, 2))
    pop.blit(img, (0, 0))
    blank = pygame.Surface(pop.get_size(), pygame.SRCALPHA)
    return [pop if f in on else blank for f in range(n)]


BUBBLE_INK, BUBBLE_EDGE = "#2a1640", "#1a1030"
BUBBLE_LINES = (("JUST LIKE THAT",), ("YOU ARE DOING", "SO GOOD TIGER"), ("DON'T STOP",))
BUBBLE_SAY = 1.5 / ZOOM_TEMPO                           # s each line stays up
BUBBLE_GAP = 0.25 / ZOOM_TEMPO                          # s of nothing between lines


def _bubble_frames(lines: tuple[tuple[str, ...], ...], tail_x: int) -> list[pygame.Surface]:
    """Speech bubbles, all the same size, one per thing said, with a tail at the
    bottom (tail_x from the left). Drawn for one screen px per px."""
    pad, row = 4, 7
    texts = [[text_surface(s, BUBBLE_INK) for s in said] for said in lines]
    bw = max(t.get_width() for said in texts for t in said) + pad * 2
    bh = max(len(said) for said in texts) * row - 2 + pad * 2
    frames = []
    for said in texts:
        surf = pygame.Surface((bw, bh + 8), pygame.SRCALPHA)
        body = pygame.Rect(0, 0, bw, bh)
        pygame.draw.rect(surf, (255, 255, 255), body, border_radius=4)
        pygame.draw.rect(surf, rgb(BUBBLE_EDGE), body, 1, border_radius=4)
        tail = [(tail_x - 3, bh - 1), (tail_x + 4, bh - 1), (tail_x + 6, bh + 7)]
        pygame.draw.polygon(surf, (255, 255, 255), tail)
        pygame.draw.lines(surf, rgb(BUBBLE_EDGE), False, [tail[0], tail[2], tail[1]])
        y = pad + (bh - pad * 2 - len(said) * row + 2) // 2
        for t in said:
            surf.blit(t, ((bw - t.get_width()) // 2, y))
            y += row
        frames.append(surf)
    return frames


def build_levels() -> list[Level]:
    cx, cy = sa.CX, sa.CY
    stork_frames = [_surf(stork(f, True)) for f in range(4)]
    bed = [_surf(sa.giants(f)) for f in range(sa.GIANTS_FRAMES)]
    bed_fps = 6.0                               # one thrust every 4 frames; the BANGs land on the knock (frame 2)
    gx, gy, gs = cx, cy + 4, 1.5                # where the bed sits, and canvas px per sprite px

    def on_bed(sx: float, sy: float) -> tuple[float, float]:
        return gx + (sx - sa.GIANTS_W / 2) * gs, gy + (sy - sa.GIANTS_H / 2) * gs

    # her lines, in a speech bubble over the pillow: one frame per line, a short blank between
    said = _bubble_frames(BUBBLE_LINES, tail_x=30)
    blank = pygame.Surface(said[0].get_size(), pygame.SRCALPHA)
    step = 0.05
    bubble_frames = [blank]
    for s in said:
        bubble_frames += [s] * round(BUBBLE_SAY / step) + [blank] * round(BUBBLE_GAP / step)
    bubble = Prop(bubble_frames, *on_bed(35, 11), size=1 / K0, fps=1 / step, loop=False)

    levels = [
        Level(_surf(sa.earth_level()), scale="1E+07 M", hold=4.0 / ZOOM_TEMPO,
              labels=[(cx, cy, 52, "EARTH", ""),
                      (cx, cy, -52, "BABIES MADE SINCE YOU GOT HERE:", "{births}")],
              props=[Prop(stork_frames, cx, cy, size=0.32, orbit=(62, 40))]),
        Level(_surf(sa.solar_level()), scale="1E+13 M", hold=4.5 / ZOOM_TEMPO,
              labels=[(*sa.URANUS, -(sa.CHEEK_R + 1), "URANUS", ""),
                      (*sa.SUN, 13, "THE SUN", "")] +
                     # every other planet is just balls (radius: + label below it, - above)
                     [(*sa.AT[name], r, "BALLS", "") for name, r in
                      (("mercury", -3), ("venus", 4), ("mars", -4), ("jupiter", 8), ("saturn", -5),
                       ("neptune", -5))] + [(cx, cy, -4, "BALLS", "")]),
        Level(_surf(sa.milky_way_level()), scale="1E+21 M", hold=4.5 / ZOOM_TEMPO, fade_out=True,
              labels=[(sa.CX + 2, sa.BOOBS[0][1], 36, "THE MILKY WAY", ""),
                      (*sa.YOU_ARE_HERE, -3, "YOU ARE HERE", "V")]),
        Level(_surf(sa.big_bang_level()), scale="1E+27 M", hold=5.5 / ZOOM_TEMPO,
              labels=[(cx, cy, -50, "THE BIG BANG", "")],
              props=[Prop(bed, gx, gy, size=gs, fps=bed_fps),
                     Prop(_text_frames("BANG!", "#ffe14d", "#c83a2a", [2, 3], 8), *on_bed(6, -6), fps=bed_fps),
                     Prop(_text_frames("BANG!", "#ffe14d", "#c83a2a", [6, 7], 8), *on_bed(2, 30), fps=bed_fps),
                     bubble]),
    ]
    bubble.start = sum(lv.hold for lv in levels[:-1]) + ZOOM_MOVE * (len(levels) - 1) + 0.3   # once the camera's there
    return levels


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
        self.length = sum(lv.hold for lv in self.levels) + ZOOM_MOVE * (len(self.levels) - 1) + FADE_OUT
        self.hearts: list[list[float]] = []      # u, v, age: babies being made on the Earth
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

    def _big(self, s: str, col: str) -> pygame.Surface:
        """The 5x7 font, for the instruction."""
        if (s, col, "big") not in self.text:
            c = Canvas(max(1, big_width(s)), BIG_H)
            draw_big_text(c, 0, 0, s, col)
            self.text[(s, col, "big")] = to_surface(c)
        return self.text[(s, col, "big")]

    def z_at(self, t: float) -> float:
        """How far out the camera is: 0 is the Earth, 1 the solar system, and so on.
        Hold on a level, glide out to the next (easing in and out), hold, ..."""
        for i, lv in enumerate(self.levels):
            if t < lv.hold:
                return float(i)
            t -= lv.hold
            if i == len(self.levels) - 1:
                break
            if t < ZOOM_MOVE:
                k = t / ZOOM_MOVE
                return i + k * k * k * (k * (k * 6 - 15) + 10)    # smootherstep: no jolt at either end
            t -= ZOOM_MOVE
        k = min(1.0, t / FADE_OUT)                   # then on out into the dark
        return len(self.levels) - 1 + k * k * 1.2

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
        # a heart pops up somewhere on the Earth for every baby made
        if self.z < 0.6 and self.rng.random() < BIRTH_RATE * dt:
            a, r = self.rng.uniform(0, math.tau), 44 * math.sqrt(self.rng.random())
            self.hearts.append([sa.CX + r * math.cos(a), sa.CY + r * math.sin(a), 0.0])
        for h in self.hearts:
            h[2] += dt
        self.hearts = [h for h in self.hearts if h[2] < HEART_LIFE]
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
        k = max(0.0, min(1.0, (self.z - (i - 1)) / FADE_IN))
        if self.levels[i].fade_out:
            k *= 1 - max(0.0, min(1.0, (self.z - i - 0.15) / 0.6))
        return int(255 * k)

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
            a = math.radians(self.t * speed + p.phase)
            u, v = u + r * math.cos(a), v + r * p.squash * math.sin(a)
        if p.hop:
            v -= abs(math.sin(self.t * 3.0)) * p.hop
        return u, v

    def _draw_prop(self, screen: pygame.Surface, i: int, p: Prop, alpha: int = 255) -> None:
        f = self._factor(i) * p.size
        n = int(max(0.0, self.t - p.start) * p.fps)
        img = p.frames[n % len(p.frames) if p.loop else min(n, len(p.frames) - 1)]
        w, h = img.get_width() * f, img.get_height() * f
        if w < 1 or w > W * 3:
            return
        if p.orbit and not p.spin and math.sin(math.radians(self.t * p.orbit[1] + p.phase)) * p.orbit[1] > 0:
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
        self._draw_hearts(screen)
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

    def _draw_hearts(self, screen: pygame.Surface) -> None:
        if not self.hearts:
            return
        if not hasattr(self, "_heart"):
            self._heart = _surf(heart(False))
        f = self._factor(0) * 2.2
        img = pygame.transform.scale(self._heart, (max(1, round(5 * f)), max(1, round(4 * f))))
        for u, v, age in self.hearts:
            x, y = self._to_screen(0, u, v - age * 6)        # float up off the surface...
            img.set_alpha(int(255 * min(1.0, (HEART_LIFE - age) / 0.5)))   # ...and fade
            screen.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))

    def _draw_labels(self, screen: pygame.Surface) -> None:
        i = round(self.z)
        if i >= len(self.levels):
            return
        d = self.z - i
        if not -0.2 < d < 0.32:
            return
        alpha = int(255 * max(0.0, min(1.0, 1.6 * (1 - abs(d) / (0.2 if d < 0 else 0.32)))))
        lv = self.levels[i]
        tags = list(lv.labels)
        for p in lv.props:
            if p.label:
                u, v = self._prop_pos(p)
                tags.append((u, v, p.frames[0].get_height() * p.size / 2, *p.label))
        f = self._factor(i)
        births = f"{int(self.t * BIRTH_RATE):,}".replace(",", " ")
        for u, v, r, a, b in tags:
            b = b.format(births=births)
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
        if self.t > SKIP_GRACE:                                 # (the button can't skip it before then)
            s = self._big("TAP BUTTON: SKIP", prompt_color())
            screen.blit(s, (W - 4 - s.get_width(), H - 10))
