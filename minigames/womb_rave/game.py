"""Womb Rave: walk into the womb sculpture and dance to the mother's heartbeat.

    python -m minigames.womb_rave [--fullscreen] [--scale 4] [--demo] [--character tech_bro] [--mute]

Controls (keyboard, or an arcade stick / gamepad):
    ARROWS              dance: hit the direction as a thing reaches your bubble    stick
    SPACE / Z / ENTER   SQUEEZE: hit it as the contraction ring closes in          button 0
    ESC / Q             quit

Your character floats in the amniotic sac in the middle of the womb. Things
come at the membrane around the sac along four lanes, each a part of the womb:
    LEFT / RIGHT   eggs rolling down the fallopian tubes
    UP             mom's cravings sliding down the umbilical cord
    DOWN           sperm swimming up from the cervix
    BUTTON         a contraction: the walls squeeze in to the membrane
Stick diagonals hit two lanes at once. Every hit makes the dancer move.

Make it to the end of the song (three trimesters and the PUSH) and you're born.
Miss too many and your vitals run out: the womb evicts you.
"""

from __future__ import annotations

import argparse
import math
import random
import time
from dataclasses import dataclass

import pygame

from sprites.canvas import hex_to_rgba, mix
from sprites.characters import Character, roster
from sprites.palette import LAB_DIM, LAB_GRID, LAB_TEXT
from sprites.rig import GROUND, SIZE
from sprites.viewer import H, W, Loaded, text_surface, to_surface

from ..shell import Input, run
from . import art, music
from .art import CX, CY, MEM_RX, MEM_RY, RECEPTOR, SAC_RX, SAC_RY
from .music import BAR, BEAT, SONG_LEN

APPROACH = 1.6                 # s from a note appearing to it reaching the membrane
WINDOWS = (("perfect", 0.045), ("great", 0.09), ("ok", 0.14))   # s either side of the beat
OK_WINDOW = WINDOWS[-1][1]
AUDIO_LAG = 0.03               # s the speakers trail the clock. Raise it if every hit reads early.
LIFE_START, LIFE_MAX = 60.0, 100.0
LIFE_GAIN = {"perfect": 3.0, "great": 2.0, "ok": 0.5}
LIFE_MISS = 6.0
POINTS = {"perfect": 100, "great": 60, "ok": 25}
COMBO_BONUS, COMBO_CAP = 5, 40  # extra points per combo step, up to the cap
GRADES = ((0.95, "S"), (0.85, "A"), (0.7, "B"), (0.5, "C"), (0.0, "D"))
ACCURACY = {"perfect": 1.0, "great": 0.7, "ok": 0.4, "miss": 0.0}

START_X = 40                   # outside: where the character waits
WALK_SPEED = 80
ENTER_TIME = 0.7               # s getting slurped in
FADE_IN = 0.6
FLUSH_TIME = 1.7               # s sliding out the bottom at the end
OUT_LAUNCH = (-110, -190)      # px/s out of the door
OUT_GRAVITY = 520
OUT_LINGER = 1.4               # s after landing before the end banner

DANCE_MOVES = {                # stick / button -> (animation, seconds it plays)
    "L": ("walk", 0.25), "R": ("walk", 0.25), "U": ("jump", 0.36), "D": ("crouch", 0.26),
    "B": ("attack", 0.34), "miss": ("hurt", 0.2),
}
HOP = 9                        # px the dancer hops on UP
NUDGE = 5                      # px the dancer steps on LEFT / RIGHT
TUNNEL_FLOW = 0.35             # rings per second flowing past
CELLS = 26

JUDGE = {"perfect": ("PERFECT!", "#ffe14d"), "great": ("GREAT", "#9dff5a"), "ok": ("OK", "#5ff3ff"),
         "miss": ("MISS", "#ff4a6a")}
HIT_LINES = {"U": ["NOM!", "YUM!", "CRAVING!", "PICKLES!"], "D": ["SWIM!", "ZOOM!", "GO GO GO!"],
             "L": ["PLOP!", "OVULATE!", "EGG-CELLENT!"], "R": ["PLOP!", "OVULATE!", "EGG-CELLENT!"],
             "B": ["SQUEEZE!", "CLENCH!", "OOF!"]}
COUNT_IN = ("READY", "3", "2", "1")


@dataclass
class Popup:
    text: pygame.Surface
    x: float
    y: float
    t: float = 0.0
    life: float = 1.0
    rise: float = 14.0


@dataclass
class Bit:
    """Confetti, splashes and blood cells."""
    x: float
    y: float
    vx: float
    vy: float
    col: tuple
    t: float = 0.0
    life: float = 1.5
    size: int = 2
    gravity: float = 0.0


def big_text(text: str, color: str, scale: int = 2) -> pygame.Surface:
    s = text_surface(text, color)
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))


def rgb(c: str) -> tuple[int, int, int]:
    return hex_to_rgba(c)[:3]


class Art:
    """Every sprite pre-rendered to surfaces."""

    def __init__(self) -> None:
        self.overlay = to_surface(art.interior_overlay())
        self.guide = to_surface(art.lane_guide())
        self.gallery = to_surface(art.gallery())
        self.doors = [to_surface(art.door(i / (art.DOOR_FRAMES - 1))) for i in range(art.DOOR_FRAMES)]
        self.neon = [pygame.transform.scale2x(to_surface(art.neon(on))) for on in (False, True)]
        self.egg = [to_surface(art.egg(f)) for f in range(4)]
        self.sperm = [to_surface(art.sperm(f)) for f in range(3)]
        self.snack = [to_surface(art.snack(k)) for k in range(len(art.SNACKS))]
        self.receptor = {(ln, st): to_surface(art.receptor(ln, st)) for ln in "LRUD" for st in ("idle", "held", "flash")}
        self.burst = {ln: [to_surface(art.burst(f, art.LANE_COLOR[ln])) for f in range(4)] for ln in "LRUDB"}
        self.heart = to_surface(art.heart_icon())
        self.judge = {g: big_text(t, c) for g, (t, c) in JUDGE.items()}

        self.sac = pygame.Surface((SAC_RX * 2 + 2, SAC_RY * 2 + 2), pygame.SRCALPHA)
        box = (1, 1, SAC_RX * 2, SAC_RY * 2)
        pygame.draw.ellipse(self.sac, (255, 200, 215, 52), box)
        self.rim = pygame.Surface(self.sac.get_size(), pygame.SRCALPHA)
        pygame.draw.ellipse(self.rim, (*rgb(art.F["hi"]), 210), box, 1)
        pygame.draw.arc(self.rim, (255, 255, 255, 230), (5, 5, SAC_RX * 2 - 8, SAC_RY * 2 - 8), 1.9, 2.9, 1)
        self.beams = pygame.Surface((W, H), pygame.SRCALPHA)
        self.fade = pygame.Surface((W, H))


class Audio:
    """The song and effects. Everything is optional: without a sound card the
    game keeps its own clock and plays silently."""

    def __init__(self, mute: bool) -> None:
        self.ok = False
        self.song_chan: pygame.mixer.Channel | None = None
        if mute:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.song = pygame.mixer.Sound(file=music.song_wav())
            self.fx = {name: pygame.mixer.Sound(file=f) for name, f in music.sfx_wavs().items()}
            self.fx["miss"].set_volume(0.5)
            self.ok = True
        except pygame.error:
            pass

    def play_song(self) -> None:
        if self.ok:
            self.song_chan = self.song.play()

    def playing(self) -> bool:
        return bool(self.song_chan and self.song_chan.get_busy())

    def stop_song(self, fade_ms: int = 0) -> None:
        if self.song_chan:
            if fade_ms:
                self.song_chan.fadeout(fade_ms)
            else:
                self.song_chan.stop()

    def play(self, name: str) -> None:
        if self.ok:
            self.fx[name].play()


_ART: Art | None = None
_AUDIO: Audio | None = None
_DANCERS: dict[str, Loaded] = {}


class WombRave:
    title = "WOMB RAVE"

    def __init__(self, character: Character | None = None, seed: int | None = None,
                 show_title: bool = True, mute: bool = False) -> None:
        global _ART, _AUDIO
        _ART = _ART or Art()                          # render once, reuse across rounds
        _AUDIO = _AUDIO or Audio(mute)
        self.art, self.audio = _ART, _AUDIO
        self.rng = random.Random(seed)
        if character is None:
            character = self.rng.choice([c for c in roster() if c.kind == "control"])
        if character.slug not in _DANCERS:
            _DANCERS[character.slug] = Loaded(character)
        self.dancer = _DANCERS[character.slug]
        self.name = character.name.upper()

        self.result: str | None = None
        self.done = False
        self.phase = "title" if show_title else "walk"
        self.phase_t = 0.0
        self.time = 0.0

        # outside
        self.x, self.y = float(START_X), float(art.FLOOR_Y)
        self.vx = self.vy = 0.0
        self.landed = False
        self.door_open = 0.0

        # inside
        self.notes = music.chart()
        self.song_t = 0.0
        self.song_t0 = 0.0
        self.bar = -1
        self.beat = -1
        self.life = LIFE_START
        self.score = 0
        self.combo = self.max_combo = 0
        self.tally = {g: 0 for g in ACCURACY}
        self.judged: tuple[str, float] | None = None   # last judgment and when
        self.flash: dict[str, float] = {}              # lane -> time it was last hit
        self.squeezed = -9.0                           # song time of the last contraction
        self.held_x = self.held_y = 0
        self.facing = 1
        self.move: tuple[str, float] | None = None     # dance animation and when it started
        self.nudge = 0.0
        self.popups: list[Popup] = []
        self.bits: list[Bit] = []
        self.cells = [self._cell(scatter=True) for _ in range(CELLS)]
        self.bursts: list[tuple[str, float, float, float]] = []   # lane, x, y, time

    # -- helpers ----------------------------------------------------------------
    def _popup(self, text: str, x: float, y: float, color: str = LAB_TEXT, life: float = 1.0,
               big: bool = False, rise: float = 14.0) -> None:
        surf = big_text(text, color) if big else text_surface(text, color)
        self.popups.append(Popup(surf, x, y, life=life, rise=rise))

    def _cell(self, scatter: bool = False) -> Bit:
        """A blood cell drifting outward through the tunnel, toward the viewer."""
        a = self.rng.uniform(0, math.tau)
        r = self.rng.uniform(20, 160) if scatter else self.rng.uniform(8, 30)
        speed = self.rng.uniform(10, 26)
        col = rgb(self.rng.choice((art.F["artery"], art.F["warm"], art.F["light"], "#f4e8f0")))
        return Bit(CX + math.cos(a) * r * 1.7, CY + math.sin(a) * r, math.cos(a) * speed * 1.7,
                   math.sin(a) * speed, col, size=self.rng.choice((2, 2, 3)))

    def _enter_phase(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    @property
    def section(self) -> str:
        bar = max(0, min(len(music.SONG) - 1, int(self.song_t // BAR)))
        return music.SONG[bar]

    @property
    def trimester(self) -> int:
        bar = int(self.song_t // BAR)
        return sum(bar >= b for b in music.TRIMESTERS)

    @property
    def accuracy(self) -> float:
        n = sum(self.tally.values())
        return sum(ACCURACY[g] * k for g, k in self.tally.items()) / n if n else 0.0

    @property
    def grade(self) -> str:
        return next(g for cut, g in GRADES if self.accuracy >= cut)

    # -- update -----------------------------------------------------------------
    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.phase_t += dt
        self._update_fx(dt)

        if self.phase == "title":
            if inp.action and self.phase_t > 0.3:
                self._enter_phase("walk")
        elif self.phase == "walk":
            self.x += WALK_SPEED * dt
            self.door_open = max(0.0, min(1.0, (self.x - (art.DOOR_X - 70)) / 50))
            if self.x >= art.DOOR_X - 2:
                self.x = art.DOOR_X
                self._enter_phase("enter")
                self.audio.play("slurp")
                self._popup("SHLOOP!", art.DOOR_X, art.DOOR_TOP - 12, art.F["pale"], big=True)
        elif self.phase == "enter":
            if self.phase_t >= ENTER_TIME + 0.25:
                self._enter_phase("dance")
                self.popups.clear()
                self.audio.play_song()
                self.song_t0 = time.perf_counter()
                self.song_t = -AUDIO_LAG
        elif self.phase == "dance":
            self._update_dance(dt, inp)
        elif self.phase == "flush":
            if self.phase_t >= FLUSH_TIME:
                self._enter_phase("out")
                self.popups.clear()
                self.x, self.y = art.DOOR_X, art.FLOOR_Y - 8
                self.vx, self.vy = OUT_LAUNCH
                self.door_open, self.landed, self.facing = 1.0, False, -1
                self.audio.play("pop" if self.result == "win" else "miss")
        elif self.phase in ("out", "won", "lost"):
            self._update_out(dt)
            if self.phase == "out" and self.landed and self.phase_t >= OUT_LINGER:
                self.phase = "won" if self.result == "win" else "lost"
                self.phase_t = 0.0
            if self.phase in ("won", "lost") and inp.action and self.phase_t > 1.0:
                self.done = True

    def _update_dance(self, dt: float, inp: Input) -> None:
        if self.audio.playing():                       # the song is the clock
            self.song_t = time.perf_counter() - self.song_t0 - AUDIO_LAG
        else:
            self.song_t += dt
        now = self.song_t

        bar, beat = int(now // BAR), int(now // BEAT)
        if beat != self.beat:
            self.beat = beat
            if bar == 0 and 0 <= beat < len(COUNT_IN):
                self._popup(COUNT_IN[beat], CX, CY - 8, LAB_TEXT, life=BEAT * 0.9, big=True, rise=0)
            elif bar == 1 and beat == 4:
                self._popup("DANCE!", CX, CY - 8, art.LANE_COLOR["B"], life=BEAT * 1.5, big=True, rise=0)
        if bar != self.bar:
            self.bar = bar
            if bar in music.CUES:
                self._popup(music.CUES[bar], W - 8, H - 18, art.F["hi"], life=2.2, rise=0)

        # presses: the stick acts on the edge, like a key press
        presses = []
        if inp.x == -1 and self.held_x != -1:
            presses.append("L")
        if inp.x == 1 and self.held_x != 1:
            presses.append("R")
        if inp.y == -1 and self.held_y != -1:
            presses.append("U")
        if inp.y == 1 and self.held_y != 1:
            presses.append("D")
        if inp.action:
            presses.append("B")
        self.held_x, self.held_y = inp.x, inp.y
        for lane in presses:
            self._press(lane, now)

        for n in self.notes:
            if n.judged is None and now - n.t > OK_WINDOW:
                self._judge(n, "miss", now)
            if n.lane == "B" and n.t <= now and n.t > self.squeezed:
                self.squeezed = n.t                    # the walls squeeze whether you hit it or not
        self.nudge -= self.nudge * min(1.0, 10 * dt)

        if self.life <= 0:
            self.result = "lose"
            self._enter_phase("flush")
            self.audio.stop_song()
            self.audio.play("scratch")
            self._popup("EVICTED!", CX, CY - 52, "#ff4a6a", life=FLUSH_TIME, big=True, rise=0)
        elif now > SONG_LEN + 0.4 and all(n.judged for n in self.notes):
            self.result = "win"
            self._enter_phase("flush")
            self.audio.stop_song(600)
            self.audio.play("pop")
            self._popup("WATER BROKE!", CX, CY - 52, art.LANE_COLOR["D"], life=FLUSH_TIME, big=True, rise=0)
            for _ in range(70):                        # the sac bursts
                a = self.rng.uniform(0, math.tau)
                sp = self.rng.uniform(60, 190)
                self.bits.append(Bit(CX + math.cos(a) * SAC_RX, CY + math.sin(a) * SAC_RY, math.cos(a) * sp,
                                     math.sin(a) * sp - 40, rgb(self.rng.choice(("#ffd0dc", "#5ff3ff", "#ffffff"))),
                                     life=1.2, gravity=260))

    def _press(self, lane: str, now: float) -> None:
        for n in self.notes:                           # sorted by time, so the first match is the oldest
            if n.lane == lane and n.judged is None and abs(n.t - now) <= OK_WINDOW:
                err = abs(n.t - now)
                grade = next(g for g, w in WINDOWS if err <= w)
                self._judge(n, grade, now)
                break
        self._dance(lane)

    def _judge(self, n: music.Note, grade: str, now: float) -> None:
        n.judged, n.hit_t = grade, now
        self.tally[grade] += 1
        self.judged = (grade, self.time)
        if grade == "miss":
            self.combo = 0
            self.life = max(0.0, self.life - LIFE_MISS)
            self.move = (DANCE_MOVES["miss"][0], self.time)
            self.audio.play("miss")
            return
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.score += POINTS[grade] + COMBO_BONUS * min(self.combo, COMBO_CAP)
        self.life = min(LIFE_MAX, self.life + LIFE_GAIN[grade])
        self.flash[n.lane] = self.time
        if n.lane == "B":                              # sparkles all round the membrane
            for k in range(6):
                a = k * math.tau / 6 + 0.5
                self.bursts.append(("B", CX + math.cos(a) * MEM_RX, CY + math.sin(a) * MEM_RY, self.time))
        else:
            self.bursts.append((n.lane, *RECEPTOR[n.lane], self.time))
        if grade == "perfect" and self.rng.random() < 0.3:
            rx, ry = RECEPTOR[n.lane] if n.lane != "B" else (CX, CY + MEM_RY)
            self._popup(self.rng.choice(HIT_LINES[n.lane]), rx, ry + 8, LAB_DIM, life=0.6)

    def _dance(self, lane: str) -> None:
        anim, _ = DANCE_MOVES[lane]
        self.move = (anim, self.time)
        if lane in "LR":
            self.facing = -1 if lane == "L" else 1
            self.nudge = NUDGE * self.facing

    def _update_out(self, dt: float) -> None:
        if not self.landed:
            self.vy += OUT_GRAVITY * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.y >= art.FLOOR_Y and self.vy > 0:
                self.y, self.landed = art.FLOOR_Y, True
                self.phase_t = 0.0
                if self.result == "win":
                    self.audio.play("fanfare")
                    self._popup(f"IT'S A {self.name}!", W / 2, 30, "#ffe14d", life=OUT_LINGER + 0.2, big=True, rise=0)
                    for _ in range(90):
                        self.bits.append(Bit(self.rng.uniform(0, W), self.rng.uniform(-60, 0), self.rng.uniform(-20, 20),
                                             self.rng.uniform(20, 60), rgb(self.rng.choice(("#ff9ac8", "#9cc4f0", "#ffe14d", "#ffffff"))),
                                             life=4.0, gravity=30))
                else:
                    self._popup("THUD", self.x, self.y - 40, LAB_DIM, life=0.8)
        self.door_open = max(0.0, self.door_open - dt * 1.5) if self.landed or self.x < art.DOOR_X - 20 else 1.0

    def _update_fx(self, dt: float) -> None:
        for p in self.popups:
            p.t += dt
            p.y -= p.rise * dt
        self.popups = [p for p in self.popups if p.t < p.life]
        for b in self.bits:
            b.t += dt
            b.vy += b.gravity * dt
            b.x += b.vx * dt
            b.y += b.vy * dt
        self.bits = [b for b in self.bits if b.t < b.life and b.y < H + 10]
        for i, c in enumerate(self.cells):
            c.x += c.vx * dt
            c.y += c.vy * dt
            c.vx *= 1 + 0.6 * dt                     # speeding up as they come toward you
            c.vy *= 1 + 0.6 * dt
            if not (-10 < c.x < W + 10 and -10 < c.y < H + 10):
                self.cells[i] = self._cell()
        self.bursts = [b for b in self.bursts if self.time - b[3] < 0.3]

    # -- draw -------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        if self.phase in ("dance", "flush"):
            self._draw_inside(screen)
        else:
            self._draw_outside(screen)
        for b in self.bits:
            if b.life - b.t > 0.3 or int(b.t * 20) % 2:
                pygame.draw.rect(screen, b.col, (round(b.x), round(b.y), b.size, b.size))
        for p in self.popups:
            if p.t < p.life - 0.25 or int(p.t * 20) % 2:
                x = p.x - p.text.get_width() // 2 if p.x < W - 10 else p.x - p.text.get_width()
                screen.blit(p.text, (round(x), round(p.y)))
        self._draw_hud(screen)
        self._draw_fade(screen)

    def _frame(self, anim: str, i: int, facing: int | None = None) -> pygame.Surface:
        frames = self.dancer.frames[anim][facing or self.facing]
        return frames[min(i, len(frames) - 1)]

    # outside
    def _draw_outside(self, screen: pygame.Surface) -> None:
        a = self.art
        screen.blit(a.gallery, (0, 0))
        flicker = (self.time * 7) % 11 > 0.6 and not (3.0 < self.time % 9 < 3.25)
        sign = a.neon[flicker]
        screen.blit(sign, (14, 22))
        door = a.doors[round(self.door_open * (art.DOOR_FRAMES - 1))]
        screen.blit(door, (art.DOOR_X - door.get_width() // 2, art.DOOR_TOP))

        img, x, y = None, self.x, self.y
        if self.phase == "title":
            img = self._frame("idle", int(self.time * 4) % 4, 1)
        elif self.phase == "walk":
            img = self._frame("walk", int(self.time * 8) % 4, 1)
        elif self.phase == "enter":
            k = min(1.0, self.phase_t / ENTER_TIME)
            if k < 1:                                  # stretched thin and sucked in
                src = self._frame("jump", 2, 1)
                w, h = max(1, round(SIZE * (1 - k) ** 1.5)), max(1, round(SIZE * (1 - 0.6 * k)))
                img = pygame.transform.scale(src, (w, h))
                screen.blit(img, (round(x) - w // 2, round(y - GROUND * (1 - 0.6 * k) - 10 * k)))
            return
        else:                                          # out, won, lost
            if not self.landed:
                img = pygame.transform.rotate(self._frame("jump", 2), 90 * (int(self.time * 14) % 4))
            elif self.result == "win":
                cycle = self.time % 0.8
                hop = max(0.0, math.sin(cycle / 0.4 * math.pi)) * 8 if cycle < 0.4 else 0
                img = self._frame("jump", 2 if cycle < 0.4 else 0) if cycle < 0.4 else self._frame("attack", int((cycle - 0.4) * 12))
                y -= hop
            else:
                img = self._frame("hurt", 0) if self.phase_t < 0.4 and self.phase == "out" else self._frame("crouch", 1)
        if img is not None:
            if img.get_width() != SIZE or not self.landed and self.phase == "out":
                screen.blit(img, (round(x) - img.get_width() // 2, round(y) - img.get_height() // 2 - 14))
            else:
                screen.blit(img, (round(x) - SIZE // 2, round(y) - GROUND - 1))

    # inside
    def _heartbeat(self) -> float:
        """0..1 thump on every beat: a lub, then a smaller dub."""
        f = (self.song_t / BEAT) % 1
        return max(math.exp(-f * 7), 0.6 * math.exp(-((f - 0.25) % 1) * 9))

    def _squeeze(self) -> float:
        return math.exp(-(self.song_t - self.squeezed) * 5) if self.song_t >= self.squeezed else 0.0

    def _draw_inside(self, screen: pygame.Surface) -> None:
        a = self.art
        now = self.song_t
        beat = self._heartbeat()
        squeeze = self._squeeze()
        losing = self.phase == "flush" and self.result == "lose"
        rave = self.section in ("chorus", "push") or (self.phase == "flush" and self.result == "win")

        # the tunnel: rings of flesh flowing out past you, throbbing with the heartbeat
        screen.fill(rgb(art.F["void"]))
        scale = 1 + 0.035 * beat - 0.14 * squeeze
        phase = self.time * TUNNEL_FLOW
        base = math.floor(phase)
        f = phase - base
        lo, hi = (art.F["deep"], art.F["warm"]) if not losing else ("#2a0408", "#7a1018")
        for k in range(13, -1, -1):
            ry = 7 * 1.3 ** (k + f) * scale
            depth = min(1.0, (k + f) / 12)
            col = mix(lo, hi, depth)
            if (k - base) % 2:
                col = mix(col, art.F["void"], 0.25)
            col = mix(col, art.F["hi"], 0.12 * beat * depth)
            pygame.draw.ellipse(screen, rgb(col), (CX - ry * 1.75, CY - ry, ry * 3.5, ry * 2))

        if rave:                                       # club lights sweeping the walls
            beams = a.beams
            beams.fill((0, 0, 0, 0))
            for i, (ox, oy) in enumerate(((0, 0), (W, 0), (0, H), (W, H))):
                ang = math.atan2(CY - oy, CX - ox) + 0.55 * math.sin(self.time * 1.3 + i * 1.7)
                col = rgb(art.RAVE[(self.beat + i) % len(art.RAVE)])
                pts = [(ox, oy)] + [(ox + math.cos(ang + s) * 400, oy + math.sin(ang + s) * 400) for s in (-0.07, 0.07)]
                pygame.draw.polygon(beams, (*col, 44), pts)
            screen.blit(beams, (0, 0))

        for c in self.cells:
            pygame.draw.ellipse(screen, c.col, (round(c.x), round(c.y), c.size + 1, c.size))
        screen.blit(a.overlay, (0, 0))
        screen.blit(a.guide, (0, 0))

        # the membrane every lane ends on, and contractions closing in on it
        mem_col = mix(art.F["pale"], "#ffffff", 0.6 if self.time - self.flash.get("B", -9) < 0.12 else 0.0)
        for i in range(48):
            ang = i * math.tau / 48 + self.time * 0.3
            screen.set_at((round(CX + math.cos(ang) * MEM_RX), round(CY + math.sin(ang) * MEM_RY)), rgb(mem_col))
        for n in self.notes:
            if n.lane == "B" and n.judged is None and 0 <= n.t - now <= APPROACH:
                k = 1 + 3.4 * (n.t - now) / APPROACH
                box = (CX - MEM_RX * k, CY - MEM_RY * k, MEM_RX * 2 * k, MEM_RY * 2 * k)
                pygame.draw.ellipse(screen, rgb(art.F["deep"]), box, 5)
                pygame.draw.ellipse(screen, rgb(art.LANE_COLOR["B"]), (box[0] + 1, box[1] + 1, box[2] - 2, box[3] - 2), 3)

        self._draw_sac(screen, beat)

        # receptors, then everything coming at them
        for lane, (rx, ry) in RECEPTOR.items():
            held = (lane == "L" and self.held_x == -1 or lane == "R" and self.held_x == 1
                    or lane == "U" and self.held_y == -1 or lane == "D" and self.held_y == 1)
            st = "flash" if self.time - self.flash.get(lane, -9) < 0.1 else "held" if held else "idle"
            screen.blit(a.receptor[(lane, st)], (rx - 5, ry - 5))
        for n in self.notes:
            if n.lane == "B" or n.judged not in (None, "miss"):
                continue
            ahead = n.t - now
            if ahead > APPROACH or (n.judged == "miss" and now - n.hit_t > 0.25):
                continue
            u = 1 - ahead / APPROACH
            x, y = art.lane_pos(n.lane, u)
            if n.lane in "LR":
                img = a.egg[int(self.time * 8) % 4]
            elif n.lane == "U":
                img = a.snack[n.snack]
            else:
                img = a.sperm[int(self.time * 10) % 3]
            if n.judged == "miss" and int(self.time * 20) % 2:
                continue
            screen.blit(img, (round(x) - img.get_width() // 2, round(y) - (2 if n.lane == "D" else img.get_height() // 2)))
        for lane, x, y, t in self.bursts:
            img = a.burst[lane][min(3, int((self.time - t) / 0.3 * 4))]
            screen.blit(img, (round(x) - 10, round(y) - 10))


        if losing:                                     # the lights go red
            shade = a.beams
            shade.fill((120, 0, 20, min(140, round(self.phase_t * 160))))
            screen.blit(shade, (0, 0))

    def _draw_sac(self, screen: pygame.Surface, beat: float) -> None:
        a = self.art
        sx, sy = CX - SAC_RX - 1, CY - SAC_RY - 1
        burst = self.phase == "flush" and self.result == "win"
        if not burst:
            screen.blit(a.sac, (sx, sy))

        # the dancer
        height, img = 0.0, None
        flushing = self.phase == "flush"
        if self.move and not flushing:
            anim, t0 = self.move
            dt = self.time - t0
            dur = dict(DANCE_MOVES.values())[anim]
            if dt < dur:
                k = dt / dur
                if anim == "walk":
                    img = self._frame("walk", int(dt * 16) % 4)
                elif anim == "jump":
                    height = math.sin(k * math.pi) * HOP
                    img = self._frame("jump", 1 if k < 0.4 else 2 if k < 0.6 else 3)
                elif anim == "crouch":
                    img = self._frame("crouch", 0 if dt < 0.06 else 1)
                elif anim == "attack":
                    img = self._frame("attack", int(dt * 12))
                else:
                    img = self._frame("hurt", int(dt * 10))
        if img is None:
            img = self._frame("hurt", 0) if flushing and self.result == "lose" else \
                self._frame("idle", int(self.song_t / BEAT * 2) % 4)
        x = CX + self.nudge
        y = CY + 15 - height + round(beat)                 # feet, bobbing on the beat
        if flushing:                                       # sliding out the bottom
            k = min(1.0, self.phase_t / (FLUSH_TIME - 0.3))
            y += (H + 60 - y) * k * k
            img = pygame.transform.rotate(img, -90 * (int(self.phase_t * 10) % 4)) if k > 0.15 else img

        # the cord, from the top of the sac to the belly
        top = (CX, CY - SAC_RY)
        belly = (x, y - 14)
        pts = [(top[0] + (belly[0] - top[0]) * s + 3 * math.sin(s * 6 + self.time * 3), top[1] + (belly[1] - top[1]) * s)
               for s in (i / 8 for i in range(9))]
        if not flushing:
            pygame.draw.lines(screen, rgb(art.F["cord_sh"]), False, pts, 3)
            pygame.draw.lines(screen, rgb(art.F["cord"]), False, pts, 1)
        if img.get_width() == SIZE and img.get_height() == SIZE and not (flushing and self.phase_t > 0.2):
            screen.blit(img, (round(x) - SIZE // 2, round(y) - GROUND - 1))
        else:
            screen.blit(img, (round(x) - img.get_width() // 2, round(y) - img.get_height() // 2 - 15))
        if not burst:
            screen.blit(a.rim, (sx, sy))

    # HUD and overlays
    def _draw_hud(self, screen: pygame.Surface) -> None:
        if self.phase == "title":
            self._banner(screen, self.title, ["THE WOMB IS OPEN. YOU'RE ON THE LIST.",
                                              "STICK: DANCE   BUTTON: SQUEEZE",
                                              "HIT THEM AS THEY TOUCH YOUR BUBBLE",
                                              "PRESS BUTTON TO START" if int(self.time * 2) % 2 == 0 else ""])
            return
        if self.phase == "dance" or self.phase == "flush":
            screen.blit(self.art.heart, (4, 4))
            pygame.draw.rect(screen, rgb(LAB_GRID), (15, 5, 62, 6))
            low = self.life < 25
            col = "#ff4a6a" if not low or int(self.time * 6) % 2 else "#ffffff"
            pygame.draw.rect(screen, rgb(col), (16, 6, round(60 * self.life / LIFE_MAX), 4))
            screen.blit(text_surface("VITALS", LAB_DIM), (16, 13))
            tri = ("FIRST", "SECOND", "THIRD")[max(0, self.trimester - 1)] if self.song_t >= BAR else "COUNT-IN"
            s = text_surface(f"{tri} TRIMESTER" if self.song_t >= BAR else tri, LAB_TEXT)
            screen.blit(s, (W - s.get_width() - 5, 5))
            s = text_surface(f"SCORE {self.score}", LAB_DIM)
            screen.blit(s, (W - s.get_width() - 5, 13))
            prog = max(0.0, min(1.0, self.song_t / SONG_LEN))
            pygame.draw.rect(screen, rgb(LAB_GRID), (W - 66, 21, 61, 3))
            pygame.draw.rect(screen, rgb(art.F["pale"]), (W - 66, 21, round(61 * prog), 3))
            if self.judged and self.time - self.judged[1] < 0.45 and self.phase == "dance":
                img = self.art.judge[self.judged[0]]          # down in the corner, clear of the lanes
                pop = 1 if self.time - self.judged[1] < 0.06 else 0
                screen.blit(img, (8, H - 38 - pop))
            if self.combo >= 4:
                c = big_text(f"{self.combo}", "#ffe14d" if self.combo >= 20 else LAB_TEXT)
                screen.blit(c, (8, H - 24))
                screen.blit(text_surface("COMBO", LAB_DIM), (8, H - 12))
        if self.phase == "won":
            self._banner(screen, "BORN TO DANCE", [f"GRADE {self.grade}   {round(self.accuracy * 100)}% IN SYNC",
                                                   f"SCORE {self.score}   MAX COMBO {self.max_combo}", "PRESS BUTTON"])
        elif self.phase == "lost":
            tri = ("FIRST", "SECOND", "THIRD")[max(0, self.trimester - 1)]
            self._banner(screen, "EVICTED", ["THE WOMB DIDN'T FEEL YOUR GROOVE",
                                             f"YOU MADE IT TO THE {tri} TRIMESTER", "PRESS BUTTON"])

    def _draw_fade(self, screen: pygame.Surface) -> None:
        alpha = 0
        if self.phase == "enter":
            alpha = max(0.0, (self.phase_t - ENTER_TIME * 0.5) / (ENTER_TIME * 0.5 + 0.25))
        elif self.phase == "dance" and self.phase_t < FADE_IN:
            alpha = 1 - self.phase_t / FADE_IN
        elif self.phase == "flush":
            alpha = max(0.0, (self.phase_t - (FLUSH_TIME - 0.4)) / 0.4)
        elif self.phase == "out" and self.phase_t < 0.3 and not self.landed:
            alpha = 1 - self.phase_t / 0.3
        if alpha > 0:
            fade = self.art.fade
            fade.fill(rgb(art.F["pink"]))
            fade.set_alpha(round(255 * min(1.0, alpha)))
            screen.blit(fade, (0, 0))

    def _banner(self, screen: pygame.Surface, title: str, lines: list[str]) -> None:
        shade = pygame.Surface((W, 22 + 9 * len(lines)), pygame.SRCALPHA)
        shade.fill((*rgb(art.F["deep"]), 215))
        screen.blit(shade, (0, 56))
        t = big_text(title, art.F["hi"])
        screen.blit(t, (W // 2 - t.get_width() // 2, 61))
        for i, line in enumerate(lines):
            if line:
                s = text_surface(line, LAB_DIM if i else LAB_TEXT)
                screen.blit(s, (W // 2 - s.get_width() // 2, 76 + i * 9))


def autopilot(game: WombRave) -> Input:
    """A computer dancer with perfect rhythm, for demos and smoke tests."""
    inp = Input()
    if game.phase != "dance":
        inp.action = game.phase in ("title", "won", "lost") and game.phase_t > 1.2
        return inp
    now = game.song_t
    for n in game.notes:
        if n.judged is None and -0.012 <= now - n.t <= 0.06:
            if n.lane == "L":
                inp.x = -1
            elif n.lane == "R":
                inp.x = 1
            elif n.lane == "U":
                inp.y = -1
            elif n.lane == "D":
                inp.y = 1
            else:
                inp.action = True
    return inp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--demo", action="store_true", help="let the computer play")
    ap.add_argument("--character", help="who goes in, by slug (e.g. tech_bro). Default: someone random")
    ap.add_argument("--mute", action="store_true", help="no sound (the game keeps its own clock)")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()

    ch = None
    if args.character:
        cast = roster()
        matches = [c for c in cast if c.slug == args.character]
        if not matches:
            raise SystemExit(f"no character {args.character!r}; try one of: " + ", ".join(c.slug for c in cast))
        ch = matches[0]

    run(lambda: WombRave(ch, seed=args.seed, mute=args.mute), "Womb Rave", scale=args.scale, fullscreen=args.fullscreen,
        autopilot=autopilot if args.demo else None, max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
