"""OOH: what UNLOCK.EXE does with the answer the lab gives you for testing every theory.

Type OOH into UNLOCK.EXE and the terminal goes dark. To the 2001 fanfare
(assets/sounds/ooh_2001.mp3, the track from 0:20 for a minute), noodles creep
in from off screen, lunge on the first big hit, and the camera pulls back
through the lull until, on the second entrance, the whole picture is there: the
Spaghetti Monster, meatballs and eyestalks, with a noodly appendage round every
member of the cast, hearts everywhere. A few seconds later, one line at a time:

    ALL MEAT,
    ALL BALLS,
    ALL THE TIME!

Everything sits in one 320x180 "world" seen through a camera that zooms from 7x
down to 1x. Noodles are drawn as vectors (stamped circles) through the camera so
they stay crisp at any zoom; the cast are their own pixel-art sprites, scaled up.
The clock follows the music when there is music, so the cues land on the beats.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

from sprites.canvas import Canvas, hex_to_rgba
from sprites.font import BIG_H, big_width, draw_big_text
from sprites.viewer import to_surface

SONG = Path(__file__).resolve().parent.parent / "assets" / "sounds" / "ooh_2001.mp3"
W, H = 320, 180

# cues, in seconds into the clip (see the envelope of ooh_2001.mp3: a rumble, a hit
# at 7.4, loud to 17, a lull, then the second entrance at 26 that stays loud)
HIT = 7.4                   # the first big hit: the noodles lunge and writhe
PULL = 17.0                 # the music drops back: the camera starts pulling out
REVEAL = 26.0               # the second entrance: the whole scene, all at once
WORDS = 31.0                # ALL MEAT ...
WORD_STEP = 1.4             # s between the lines
END = 60.0                  # the clip's length
LINES = ("ALL MEAT", "ALL BALLS", "ALL THE TIME!")

Z0, Z1 = 7.0, 5.5           # zoom at the start, and when the pull-back starts
START_AT = (160.0, 128.0)   # what the camera looks at to begin with: empty space under the monster
WIDE_AT = (160.0, 90.0)

MONSTER = (160.0, 64.0)
NOODLE_R = 1.3              # a noodle's radius, in world px
NOODLE = {"edge": "#8a6424", "main": "#f0c860", "hi": "#fff0b0"}
MEAT = {"edge": "#3e180c", "main": "#8a3a1e", "light": "#b85a30", "hi": "#e89060", "speck": "#5a2412"}
SKY = "#0c0614"
GLOW = "#3a1030"
TEXT = "#ffd86a"
TEXT_SHADOW = "#5a1a10"
HINT = "#5dff7a"
RAVE = ("#ff6a9a", "#5ff3ff", "#ffe14d", "#b46bff", "#9dff5a")   # the womb rave's lights
BEAT = 2.0                  # pulses/s for the strobing background


def rgb(c: str) -> tuple[int, int, int]:
    return hex_to_rgba(c)[:3]


def smooth(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def text_surface(s: str, color: str, scale: int) -> pygame.Surface:
    c = Canvas(max(1, big_width(s)), BIG_H)
    draw_big_text(c, 0, 0, s, color)
    surf = to_surface(c)
    return pygame.transform.scale(surf, (surf.get_width() * scale, surf.get_height() * scale))


def _frames(make, n: int = 4) -> list[pygame.Surface]:
    """A sprite's animation frames, cropped to what's drawn."""
    out = []
    for f in range(n):
        try:
            s = make(f)
        except (IndexError, KeyError, ValueError):
            break
        s = to_surface(s) if not isinstance(s, pygame.Surface) else s
        out.append(s.subsurface(s.get_bounding_rect()).copy())
    return out or [pygame.Surface((8, 8), pygame.SRCALPHA)]


def cast() -> list[tuple[str, list[pygame.Surface], int, tuple[float, float]]]:
    """Who's at the party: (name, frames, world px per sprite px, where they are)."""
    from minigames.it_takes_two.art import egg, enemy, penis, sperm
    from minigames.primordial_soup.art import critter
    from minigames.primordial_soup.people import DINER_LOOKS, chef_frames, diner_frames, staff_frames
    from minigames.stork_bomber import hairy_man
    from minigames.stork_bomber.art import baby, stork

    hairy = hairy_man.frames()["idle"]
    chef = chef_frames()["idle"]
    diner = diner_frames(DINER_LOOKS[1])["idle"]
    sci = staff_frames("scientist")["idle"]
    return [
        ("stork", _frames(lambda f: stork(f, False)), 1, (48, 34)),
        ("hairy", _frames(lambda f: hairy[f % len(hairy)]), 1, (34, 116)),
        ("chef", _frames(lambda f: chef[f % len(chef)]), 1, (88, 142)),
        ("egg", _frames(egg), 2, (140, 156)),
        ("sperm", _frames(sperm), 2, (184, 160)),
        ("baby", _frames(lambda f: baby(f % 2)), 2, (234, 140)),
        ("hotdog", _frames(lambda f: critter("hotdog", f)), 2, (284, 114)),
        ("eyeball", _frames(lambda f: critter("eyeball", f)), 2, (276, 38)),
        # the second ring, in the gaps
        ("scientist", _frames(lambda f: sci[f % len(sci)]), 1, (108, 26)),
        ("diner", _frames(lambda f: diner[f % len(diner)]), 1, (214, 26)),
        ("legfish", _frames(lambda f: critter("legfish", f)), 2, (16, 66)),
        ("condom", _frames(lambda f: enemy("condom", f, (-1, 0))), 2, (304, 70)),
        ("jello", _frames(lambda f: critter("jello", f)), 2, (66, 90)),
        ("pill", _frames(lambda f: enemy("pill", f, (-1, 0))), 2, (256, 90)),
        ("penis", _frames(lambda f: penis(0.3 * (f % 2), squirt=f % 4 == 3)), 1, (26, 164)),
        ("wiener", _frames(lambda f: critter("wiener", f)), 2, (300, 164)),
    ]


class Tentacle:
    """A noodly appendage from the monster to one of the cast, coiled round them at the end."""

    REACH = 0.8             # the part of it that reaches; the rest is the coil

    def __init__(self, who: int, base: tuple[float, float], target: tuple[float, float], size: tuple[int, int],
                 lag: float, rng: random.Random) -> None:
        self.who = who                  # which of the cast it's wrapped round
        self.base, self.target = base, target
        self.coil_r = max(7.0, min(15.0, size[0] * 0.5 + 2))      # just wider than they are
        self.lag = lag
        self.phase = rng.uniform(0, math.tau)
        self.turns = rng.uniform(1.2, 1.5)
        self.side = rng.choice((-1, 1))

    def points(self, t: float, grown: float, writhe: float, speed: float,
               bob: float) -> tuple[list[tuple[float, float]], list[bool]]:
        """Points along it, in world px, out to `grown` (0..1) of its length, and for
        each one whether it's on the near side of the coil (drawn over whoever it's round)."""
        bx, by = self.base
        tx, ty = self.target[0], self.target[1] + bob
        a0 = math.atan2(by - ty, bx - tx)                         # the coil starts on the side facing the monster
        sx, sy = tx + math.cos(a0) * self.coil_r, ty + math.sin(a0) * self.coil_r * 0.4
        dx, dy = sx - bx, sy - by
        n = math.hypot(dx, dy) or 1
        px, py = -dy / n, dx / n
        amp = 5.0 + 5.0 * writhe
        pts, front = [], []
        steps = 70
        for i in range(int(steps * grown) + 1):
            s = i / steps
            if s <= self.REACH:
                u = s / self.REACH
                w = amp * math.sin(math.pi * u) * math.sin(5 * math.pi * u - t * speed + self.phase)
                pts.append((bx + dx * u + px * w, by + dy * u + py * w))
                front.append(False)
            else:
                u = (s - self.REACH) / (1 - self.REACH)
                a = a0 + self.side * u * self.turns * math.tau
                r = self.coil_r * (1 - 0.2 * u) * (1 + 0.06 * math.sin(t * speed * 1.5 + u * 9))
                pts.append((tx + math.cos(a) * r, ty + math.sin(a) * r * 0.4))
                front.append(math.sin(a) > -0.15)
        return pts, front


class Ooh:
    def __init__(self, mute: bool = False, seed: int = 1) -> None:
        self.rng = random.Random(seed)
        self.t = 0.0
        self.done = False
        self.music = False
        self.cast = cast()
        mx, my = MONSTER
        self.tentacles: list[Tentacle] = []
        for i, (_, frames, k, pos) in enumerate(self.cast):
            w, h = frames[0].get_width() * k, frames[0].get_height() * k
            ang = math.atan2(pos[1] - my, pos[0] - mx)
            base = (mx + math.cos(ang) * 22, my + math.sin(ang) * 12)
            # the two straight under the monster come first: they're the ones the camera starts on
            lag = 0.0 if pos[1] > 150 else 0.08 + 0.04 * (i % 3)
            self.tentacles.append(Tentacle(i, base, pos, (w, h), lag, self.rng))
            if i % 2 == 0:                                    # and a second one for good measure
                self.tentacles.append(Tentacle(i, (base[0] + self.rng.uniform(-6, 6), base[1]),
                                               (pos[0], pos[1] + h * 0.2), (w, h), lag + 0.06, self.rng))
        # the tangle that is the monster's body: loops round and round
        self.strands = [(self.rng.uniform(0, math.tau), self.rng.uniform(0, math.tau), self.rng.uniform(0.7, 1.0),
                         self.rng.choice((2, 3)), self.rng.uniform(-1, 1)) for _ in range(14)]
        self.stars = [(self.rng.randrange(W), self.rng.randrange(H), self.rng.choice((30, 50, 80))) for _ in range(50)]
        self.hearts: list[list[float]] = []
        self.heart_imgs = self._hearts()
        # the background going off once the party's on: see _chaos()
        from minigames.it_takes_two.art import sperm
        from minigames.stork_bomber.art import stork
        self.swimmer = _frames(sperm)
        self.flyer = _frames(lambda f: stork(f, True))
        self.sparks: list[list[float]] = []            # fireworks: x, y, vx, vy, age, colour
        self.balls: list[list[float]] = []             # meatball rain: x, y, vy, r
        self.boom = 0.0                                # s to the next firework
        self.beams = pygame.Surface((W, H))
        self.words = [text_surface(s, TEXT, 3) for s in LINES]
        self.shadows = [text_surface(s, TEXT_SHADOW, 3) for s in LINES]
        self.hint = text_surface("BUTTON: BACK", HINT, 1)
        self.scaled: dict[tuple[int, int, int], pygame.Surface] = {}
        if not mute and SONG.exists():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(str(SONG))
                pygame.mixer.music.play()
                self.music = True
            except pygame.error:
                self.music = False

    def _hearts(self) -> list[pygame.Surface]:
        from minigames.it_takes_two.art import heart
        small, big = to_surface(heart()), to_surface(heart(True))
        return [pygame.transform.scale_by(small, 2), pygame.transform.scale_by(big, 2), big]

    # -- the clock and the cues -------------------------------------------------------
    def stop(self) -> None:
        if self.music and pygame.mixer.get_init():
            pygame.mixer.music.fadeout(500)
        self.music = False

    @property
    def words_up(self) -> bool:
        return self.t > WORDS + WORD_STEP * (len(LINES) - 1)

    def update(self, dt: float, sx: int, act: bool) -> None:
        self.t += dt
        if self.music and pygame.mixer.get_init():
            pos = pygame.mixer.music.get_pos()
            if pos > 0 and abs(pos / 1000 - self.t) > 0.08:      # follow the music, so the cues land on the beats
                self.t = pos / 1000
        if sx < 0 or act and self.words_up or self.t > END + 0.5:
            self.done = True
        if self.t > REVEAL:                                      # hearts float up off the cast
            for _ in range(1 if self.rng.random() < dt * 9 else 0):
                _, frames, k, (x, y) = self.rng.choice(self.cast)
                self.hearts.append([x + self.rng.uniform(-10, 10), y - frames[0].get_height() * k / 2,
                                    self.rng.uniform(0, math.tau), self.rng.randrange(len(self.heart_imgs)), 0.0])
            for h in self.hearts:
                h[1] -= 18 * dt
                h[4] += dt
            self.hearts = [h for h in self.hearts if h[4] < 2.2]
            self._update_chaos(dt)

    def _update_chaos(self, dt: float) -> None:
        self.boom -= dt
        if self.boom <= 0:                                       # a firework goes off somewhere
            self.boom = self.rng.uniform(0.25, 0.7)
            x, y = self.rng.uniform(20, W - 20), self.rng.uniform(15, 100)
            col = self.rng.randrange(len(RAVE))
            for i in range(18):
                a = i / 18 * math.tau + self.rng.uniform(-0.1, 0.1)
                v = self.rng.uniform(30, 60)
                self.sparks.append([x, y, math.cos(a) * v, math.sin(a) * v, 0.0, col])
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[3] += 40 * dt                                     # they droop
            sp[4] += dt
        self.sparks = [sp for sp in self.sparks if sp[4] < 1.1]
        if self.rng.random() < dt * 6:                           # it's raining meatballs
            self.balls.append([self.rng.uniform(0, W), -6.0, self.rng.uniform(20, 50), self.rng.uniform(2, 4)])
        for b in self.balls:
            b[2] += 120 * dt
            b[1] += b[2] * dt
            if b[1] > H - b[3] and b[2] > 0:                     # and they bounce
                b[1], b[2] = H - b[3], -b[2] * 0.55
        self.balls = [b for b in self.balls if abs(b[2]) > 12 or b[1] < H - b[3] - 1][-40:]

    def _chaos(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Behind the party: spinning rave lights, fireworks, sperm racing by, a stork
        on a delivery run and meatballs raining down, all pulsing on the beat."""
        t = self.t - REVEAL
        pulse = 0.5 + 0.5 * math.cos(t * BEAT * math.tau)
        mx, my = MONSTER[0] + ox, MONSTER[1] + oy
        self.beams.fill((0, 0, 0))
        for i in range(8):                                       # rave lights round the monster
            a = t * (0.9 if i % 2 else -0.6) + i * math.tau / 8
            r, g, b = rgb(RAVE[i % len(RAVE)])
            k = 0.18 + 0.17 * pulse
            pts = [(mx, my), (mx + math.cos(a - 0.09) * 400, my + math.sin(a - 0.09) * 400),
                   (mx + math.cos(a + 0.09) * 400, my + math.sin(a + 0.09) * 400)]
            pygame.draw.polygon(self.beams, (int(r * k), int(g * k), int(b * k)), pts)
        screen.blit(self.beams, (0, 0), special_flags=pygame.BLEND_ADD)

        for x, y, _, _, age, col in self.sparks:                 # fireworks
            if age < 0.8 or int(age * 20) % 2:
                c = rgb(RAVE[int(col)])
                screen.fill(c, (int(x) + ox, int(y) + oy, 2, 2))

        for lane, (y0, vx) in enumerate(((118, 70), (48, -55))):  # two streams of sperm, racing
            for i in range(9):
                x = (t * vx + i * 22 + lane * 50) % (W + 60) - 30
                if vx < 0:
                    x = W - x
                y = y0 + math.sin(t * 5 + i * 0.8) * 6
                img = self.swimmer[int(t * 10 + i) % len(self.swimmer)]
                if vx < 0:
                    img = pygame.transform.flip(img, True, False)
                screen.blit(img, (int(x) + ox, int(y) + oy))

        x = (t * 45) % (W + 120) - 60                            # a stork on its rounds, high up
        img = self.flyer[int(t * 8) % len(self.flyer)]
        screen.blit(img, (int(x) + ox, 2 + int(math.sin(t * 3) * 3) + oy))

        for x, y, _, r in self.balls:                            # meatball rain
            pygame.draw.circle(screen, rgb(MEAT["edge"]), (x + ox, y + oy), r + 1)
            pygame.draw.circle(screen, rgb(MEAT["main"]), (x + ox, y + oy), r)
            pygame.draw.circle(screen, rgb(MEAT["hi"]), (x + ox - r * 0.35, y + oy - r * 0.35), max(1, r * 0.3))

    def grown(self) -> float:
        """0..1: how far the noodles have reached."""
        if self.t < HIT:
            return 0.55 * (self.t / HIT) ** 1.6
        return 0.55 + 0.45 * smooth((self.t - HIT) / (REVEAL - 2 - HIT))

    def camera(self) -> tuple[float, float, float]:
        """Zoom and where it's looking (world px)."""
        t = self.t
        if t < HIT:
            return Z0, *START_AT
        if t < PULL:
            k = (t - HIT) / (PULL - HIT)
            return Z0 + (Z1 - Z0) * k, START_AT[0], START_AT[1] - 4 * k
        k = smooth((t - PULL) / (REVEAL - PULL))
        z = Z1 * (1 / Z1) ** k                                   # even-feeling zoom: the same ratio each frame
        cy = START_AT[1] - 4 + (WIDE_AT[1] - START_AT[1] + 4) * k
        return z, START_AT[0] + (WIDE_AT[0] - START_AT[0]) * k, cy

    def shake(self) -> tuple[int, int]:
        for cue, size in ((HIT, 3.0), (REVEAL, 4.0)):
            k = 1 - (self.t - cue) / 0.6
            if 0 < k <= 1:
                return round(self.rng.uniform(-1, 1) * size * k), round(self.rng.uniform(-1, 1) * size * k)
        return 0, 0

    # -- drawing --------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        z, cx, cy = self.camera()
        ox, oy = self.shake()

        def to_screen(x: float, y: float) -> tuple[float, float]:
            return (x - cx) * z + W / 2 + ox, (y - cy) * z + H / 2 + oy

        party = self.t > REVEAL
        screen.fill(rgb(SKY))
        for x, y, v in self.stars:
            if (x * 7 + y * 3 + int(self.t * 2)) % 9:
                screen.set_at((x, y), (v, v // 2 + 10, v + 20))
        if party:                                                # a warm glow behind the monster
            gx, gy = to_screen(*MONSTER)
            glow = rgb(GLOW)
            for r in (90, 70, 50):
                pygame.draw.ellipse(screen, glow, (gx - r * 1.4, gy - r * 0.8, r * 2.8, r * 1.6))
                glow = tuple(min(255, c + 12) for c in glow)

        if party:
            self._chaos(screen, ox, oy)

        writhe = 0.0 if self.t < HIT else min(1.0, (self.t - HIT) / 1.5)
        speed = 2.0 + 2.5 * writhe + (2.5 if party else 0)
        grown = self.grown()

        bobs = [-abs(math.sin(self.t * math.tau * 1.1 + i * 1.3)) * 3 if party else 0.0
                for i in range(len(self.cast))]                  # the cast bounce once it's on
        coils = []
        for tent in self.tentacles:                              # noodles first: the far side of each coil
            g = max(0.0, min(1.0, (grown - tent.lag) / max(0.01, 1 - tent.lag)))
            if g > 0:
                pts, front = tent.points(self.t, g, writhe, speed, bobs[tent.who])
                self._noodle(screen, pts, to_screen, z, taper=g < 1)
                coils.append((pts, front, g < 1))
        for i, (_, frames, k, (x, y)) in enumerate(self.cast):  # then the cast, in the coils
            img = frames[int(self.t * 6 + i) % len(frames)]
            self._sprite(screen, img, k * z, to_screen(x, y + bobs[i]))
        for pts, front, taper in coils:                          # then the near side of each coil, over them
            run: list[tuple[float, float]] = []
            for p, near in zip(pts, front):
                if near:
                    run.append(p)
                elif run:
                    self._noodle(screen, run, to_screen, z)
                    run = []
            self._noodle(screen, run, to_screen, z, taper=taper)
        for strand in self.strands:                              # the body
            self._noodle(screen, self._strand(strand), to_screen, z)
        self._meatballs(screen, to_screen, z)
        self._eyes(screen, to_screen, z, party)

        for x, y, ph, kind, age in self.hearts:
            img = self.heart_imgs[kind]
            sx, sy = to_screen(x + math.sin(age * 4 + ph) * 4, y)
            screen.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))

        if party and self.t - REVEAL < 0.35:                     # the flash as it all lands
            v = int(255 * (1 - (self.t - REVEAL) / 0.35))
            screen.fill((v, v, v), special_flags=pygame.BLEND_ADD)
        if self.t < 1.2:                                         # in from black
            v = int(255 * self.t / 1.2)
            screen.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        self._draw_words(screen)

    def _strand(self, strand) -> list[tuple[float, float]]:
        p, q, size, lobes, spin = strand
        mx, my = MONSTER
        pts = []
        for i in range(37):
            a = i / 36 * math.tau
            x = mx + 26 * size * (0.8 * math.cos(a + p) + 0.25 * math.cos(lobes * a + q + self.t * 0.7 * spin))
            y = my + 13 * size * (0.8 * math.sin(a + p) + 0.3 * math.sin((lobes + 1) * a + q - self.t * 0.5))
            pts.append((x, y))
        return pts

    def _noodle(self, screen, pts, to_screen, z: float, taper: bool = False) -> None:
        if len(pts) < 2:
            return
        sp = [to_screen(x, y) for x, y in pts]
        r = NOODLE_R * z
        if r < 2.5:                                              # zoomed out: plain lines are enough
            w = max(2, round(r * 2))
            pygame.draw.lines(screen, rgb(NOODLE["edge"]), False, sp, w + 2)
            pygame.draw.lines(screen, rgb(NOODLE["main"]), False, sp, w)
            if w >= 3:
                pygame.draw.lines(screen, rgb(NOODLE["hi"]), False, [(x - 1, y - 1) for x, y in sp], 1)
            return
        # zoomed in: stamp circles along it, close enough to look solid, skipping what's off screen
        stamps = []
        step = max(1.0, r * 0.5)
        n = len(sp)
        for i in range(n - 1):
            (x0, y0), (x1, y1) = sp[i], sp[i + 1]
            d = math.hypot(x1 - x0, y1 - y0)
            k = max(1, int(d / step))
            for j in range(k):
                u = j / k
                x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
                if -r - 2 < x < W + r + 2 and -r - 2 < y < H + r + 2:
                    f = (i + u) / (n - 1)
                    rr = r * (0.35 + 0.65 * min(1.0, (1 - f) * 12)) if taper else r
                    stamps.append((x, y, rr))
        edge, main, hi = rgb(NOODLE["edge"]), rgb(NOODLE["main"]), rgb(NOODLE["hi"])
        for x, y, rr in stamps:
            pygame.draw.circle(screen, edge, (x, y), rr + max(1, rr * 0.18))
        for x, y, rr in stamps:
            pygame.draw.circle(screen, main, (x, y), rr)
        for x, y, rr in stamps:
            pygame.draw.circle(screen, hi, (x - rr * 0.35, y - rr * 0.35), max(1, rr * 0.3))

    def _meatballs(self, screen, to_screen, z: float) -> None:
        mx, my = MONSTER
        for side in (-1, 1):
            x, y = to_screen(mx + side * 13, my + 3 + math.sin(self.t * 3 + side) * 0.8)
            r = 7.5 * z
            pygame.draw.circle(screen, rgb(MEAT["edge"]), (x, y), r + max(1, z * 0.7))
            pygame.draw.circle(screen, rgb(MEAT["main"]), (x, y), r)
            pygame.draw.circle(screen, rgb(MEAT["light"]), (x - r * 0.2, y - r * 0.2), r * 0.7)
            pygame.draw.circle(screen, rgb(MEAT["hi"]), (x - r * 0.4, y - r * 0.4), max(1, r * 0.22))
            for a, d in ((0.5, 0.5), (2.2, 0.6), (3.8, 0.45), (5.1, 0.65)):
                pygame.draw.circle(screen, rgb(MEAT["speck"]), (x + math.cos(a) * r * d, y + math.sin(a) * r * d),
                                   max(1, r * 0.1))

    def _eyes(self, screen, to_screen, z: float, party: bool) -> None:
        mx, my = MONSTER
        for side in (-1, 1):
            sway = math.sin(self.t * 1.7 + side) * 2
            ex, ey = mx + side * 11 + sway, my - 32
            stalk = [(mx + side * 5 + (ex - mx - side * 5) * u + math.sin(u * 5 + self.t * 2) * 1.5 * (1 - u),
                      my - 10 + (ey - my + 10) * u) for u in (i / 10 for i in range(11))]
            self._noodle(screen, stalk, to_screen, z)
            x, y = to_screen(ex, ey)
            r = 4.5 * z
            pygame.draw.circle(screen, (20, 12, 12), (x, y), r + max(1, z * 0.6))
            pygame.draw.circle(screen, (250, 250, 240), (x, y), r)
            if party:                                            # looking round at everyone
                look = math.sin(self.t * 2.3 + side * 0.6)
                lx, ly = look * r * 0.45, math.cos(self.t * 1.9) * r * 0.25
            else:
                lx, ly = 0, r * 0.4                              # looking down at what it's reaching for
            pygame.draw.circle(screen, (10, 10, 20), (x + lx, y + ly), r * 0.45)
            pygame.draw.circle(screen, (255, 255, 255), (x + lx - r * 0.15, y + ly - r * 0.15), max(1, r * 0.12))

    def _sprite(self, screen, img: pygame.Surface, k: float, at: tuple[float, float]) -> None:
        """A cast member at k screen px per sprite px, centred on `at`, if any of it is on screen."""
        w, h = max(1, round(img.get_width() * k)), max(1, round(img.get_height() * k))
        x, y = at[0] - w / 2, at[1] - h / 2
        if x > W or y > H or x + w < 0 or y + h < 0:
            return
        key = (id(img), w, h)
        if key not in self.scaled:
            if len(self.scaled) > 64:
                self.scaled.clear()
            self.scaled[key] = pygame.transform.scale(img, (w, h))
        screen.blit(self.scaled[key], (round(x), round(y)))

    def _draw_words(self, screen: pygame.Surface) -> None:
        if self.t < WORDS:
            return
        k = min(1.0, (self.t - WORDS) / 0.5)                     # the party dims under the words
        v = int(255 - 150 * k)
        screen.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        top = H // 2 - (len(LINES) * 30 - 9) // 2 - 6
        for i, (img, sh) in enumerate(zip(self.words, self.shadows)):
            since = self.t - WORDS - i * WORD_STEP
            if since < 0:
                break
            x, y = W // 2 - img.get_width() // 2, top + i * 30
            punch = round(max(0.0, 1 - since / 0.15) * 3)        # a little jolt as each line lands
            screen.blit(sh, (x + 2, y + 2 - punch))
            screen.blit(img, (x, y - punch))
        if self.words_up and int(self.t * 2) % 2 == 0:
            screen.blit(self.hint, (W - 4 - self.hint.get_width(), H - 10))
