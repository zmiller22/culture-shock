"""Womb Rave: walk into the womb sculpture and dance to the beat inside.

    python -m minigames.womb_rave [--fullscreen] [--scale 4] [--demo] [--character tech_bro] [--mute]

Controls (keyboard, or an arcade stick / gamepad):
    LEFT / RIGHT        choose your dancer (on the select screen)                  stick
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
from .music import BEAT, SONG_LEN

APPROACH = 1.6                 # s from a note appearing to it reaching the membrane, at 120 BPM
                               # (it shrinks as the song speeds up, so notes really do come faster)
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
SELECT_GAP = 58                # px between dancers in the select carousel
SELECT_SLIDE = 14              # how fast the carousel slides to the pick (1/s)
PICK_TIME = 0.9                # s the chosen dancer shows off before walking in
REJECTED = {"tech_bro"}        # the womb won't let these in
SLAM_AT = 52                   # px before the door that it slams on them
BONK_AT = 24                   # px before the door where they walk into it
BONK_LAUNCH = (-95, -150)      # px/s bounced back off the closed door
REJECT_LINES = (("SORRY.", "CLOSED FOR BUSINESS."), ("NOT TODAY", "TECH BRO."), ("HAVE YOU TRIED", "AN INCUBATOR?"))
REJECT_LINE_TIME = 1.3         # s each speech bubble shows
LOAD_RANGE = 3                 # dancers either side of the pick kept loaded
ROUTINES = (                   # select-screen dance routines, one move per beat
    ("bob", "stepL", "bob", "stepR", "hop", "squat", "punch", "spin"),
    ("stepR", "stepL", "stepR", "stepL", "squat", "hop", "squat", "hop"),
    ("punch", "punch", "spin", "bob", "wave", "wave", "hop", "spin"),
    ("squat", "bob", "squat", "bob", "stepL", "stepR", "hop", "hop"),
    ("wave", "bob", "punch", "bob", "spin", "spin", "squat", "hop"),
)
HOP = 9                        # px the dancer hops on UP
NUDGE = 5                      # px the dancer steps on LEFT / RIGHT
TUNNEL_FLOW = 0.35             # rings per second flowing past at 120 BPM (faster as the song speeds up)
STREAK = 8                     # every this many hits in a row: a moan and a line on screen
CLIMAX_EVERY = 32              # ...and every this many, the big one
MOANS_SOFT = ("mmm", "ooh", "oh", "uhh")
MOANS_HOT = ("mmm-ahh", "oh-yeah", "ah-ah")
HOT_AT = 24                    # combo where the moans get more worked up
STREAK_LINES = (
    "ALL ABOUT THE MOTION OF THE OCEAN", "FIND YOUR RHYTHM", "DON'T STOP NOW", "RIGHT THERE!",
    "OH YES. RIGHT ON THE BEAT", "IT'S NOT THE SIZE. IT'S THE TIMING", "BABY MAKING MUSIC",
    "IN AND OUT. IN AND OUT.", "SO IN SYNC", "GET IN THE GROOVE", "BUMP AND GRIND", "THAT'S THE SPOT",
    "KEEP THAT PACE", "SLOW HANDS. QUICK FEET.", "TIMING IS EVERYTHING", "WHO'S YOUR DADDY?",
    "THE BEAT GOES ON AND ON", "STROKE OF GENIUS", "OH THAT'S GOOD", "THE RHYTHM METHOD!",
    "YOU'VE DONE THIS BEFORE", "MAKE SOME NOISE", "GIVE IT TO ME BABY", "HIT IT AGAIN",
)
CLIMAX_LINES = ("OH OH OH YES!", "EARTH. MOVED.", "THE BIG O-VULATION!", "CLIMAX!", "WAS IT GOOD FOR YOU?")
BREAK_LINES = ("IT HAPPENS TO EVERYONE", "TOO SOON?", "AWKWARD...", "WE CAN CUDDLE", "IS IT IN?")
BREAK_AT = 16                  # a combo at least this long breaking gets a line too
SHOUT_TIME = 1.4               # s a FASTER! / HARDER! shout stays up
CALLOUT_TIME = 1.7             # s a streak line stays up
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


def outlined(text: str, color: str, scale: int) -> pygame.Surface:
    """Big text with a dark outline, so it reads over the busy flesh."""
    fg, bg = big_text(text, color, scale), big_text(text, art.F["void"], scale)
    o = max(1, scale // 2)
    out = pygame.Surface((fg.get_width() + 2 * o, fg.get_height() + 2 * o), pygame.SRCALPHA)
    for dx in (-o, 0, o):
        for dy in (-o, 0, o):
            out.blit(bg, (o + dx, o + dy))
    out.blit(fg, (o, o))
    return out


def outlined_lines(text: str, color: str, scale: int, width: int) -> pygame.Surface:
    """outlined(), split onto two lines at the middle space if it's too wide."""
    one = outlined(text, color, scale)
    if one.get_width() <= width or " " not in text:
        return one
    words = text.split()
    cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    a, b = outlined(" ".join(words[:cut]), color, scale), outlined(" ".join(words[cut:]), color, scale)
    out = pygame.Surface((max(a.get_width(), b.get_width()), a.get_height() + b.get_height() - 2), pygame.SRCALPHA)
    out.blit(a, ((out.get_width() - a.get_width()) // 2, 0))
    out.blit(b, ((out.get_width() - b.get_width()) // 2, a.get_height() - 2))
    return out


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
        self.lobby_chan: pygame.mixer.Channel | None = None
        if mute:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.song = pygame.mixer.Sound(file=music.song_wav())
            self.lobby = pygame.mixer.Sound(file=music.lobby_wav())
            self.fx = {name: pygame.mixer.Sound(file=f) for name, f in music.sfx_wavs().items()}
            self.fx["miss"].set_volume(0.5)
            self.ok = True
        except pygame.error:
            pass

    def play_lobby(self) -> None:
        if self.ok and not (self.lobby_chan and self.lobby_chan.get_busy()):
            self.lobby_chan = self.lobby.play(loops=-1)

    def stop_lobby(self, fade_ms: int = 300) -> None:
        if self.lobby_chan:
            self.lobby_chan.fadeout(fade_ms)
            self.lobby_chan = None

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


def cast() -> list[Character]:
    """Who can dance: the control group. The Kronenberg mixes belong to another game."""
    return [c for c in roster() if c.kind == "control"]


def _load(character: Character) -> Loaded:
    if character.slug not in _DANCERS:
        _DANCERS[character.slug] = Loaded(character)
    return _DANCERS[character.slug]


class WombRave:
    title = "WOMB RAVE"

    def __init__(self, character: Character | None = None, seed: int | None = None,
                 show_title: bool = True, mute: bool = False) -> None:
        global _ART, _AUDIO
        _ART = _ART or Art()                          # render once, reuse across rounds
        _AUDIO = _AUDIO or Audio(mute)
        self.art, self.audio = _ART, _AUDIO
        self.rng = random.Random(seed)
        self.cast = cast()
        if character is None:
            character = self.rng.choice([c for c in self.cast if c.slug not in REJECTED])
        self.pick = next(i for i, c in enumerate(self.cast) if c.slug == character.slug)
        self.slide = float(self.pick)                  # where the carousel is drawn, easing to the pick
        self.sel_held = 0
        self.picked = False
        self._choose(character)

        self.result: str | None = None
        self.done = False
        self.phase = "select" if show_title else "walk"
        self.phase_t = 0.0
        self.time = 0.0
        if show_title:
            self.audio.play_lobby()

        # outside
        self.x, self.y = float(START_X), float(art.FLOOR_Y)
        self.vx = self.vy = 0.0
        self.landed = False
        self.door_open = 0.0

        # inside
        self.notes = music.chart()
        for n in self.notes:
            n.approach = APPROACH * music.BPM / music.bpm_at(n.t)
        self.flow = 0.0                                # tunnel position, in rings
        self.callouts: list[tuple[pygame.Surface, float, float]] = []   # surface, time shown, life
        self.shout: tuple[pygame.Surface, float] | None = None          # FASTER! etc., and when
        self.lines = list(STREAK_LINES)
        self.rng.shuffle(self.lines)
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

    def _callout(self, text: str, color: str) -> None:
        """A line in big letters across the top, behind the notes."""
        self.callouts = [(outlined_lines(text, color, 2, W - 16), self.time, CALLOUT_TIME)]

    def _cell(self, scatter: bool = False) -> Bit:
        """A blood cell drifting outward through the tunnel, toward the viewer."""
        a = self.rng.uniform(0, math.tau)
        r = self.rng.uniform(20, 160) if scatter else self.rng.uniform(8, 30)
        speed = self.rng.uniform(10, 26)
        col = rgb(self.rng.choice((art.F["artery"], art.F["warm"], art.F["light"], "#f4e8f0")))
        return Bit(CX + math.cos(a) * r * 1.7, CY + math.sin(a) * r, math.cos(a) * speed * 1.7,
                   math.sin(a) * speed, col, size=self.rng.choice((2, 2, 3)))

    def _choose(self, character: Character) -> None:
        self.dancer = _load(character)
        self.name = character.name.upper()
        self.rejected = character.slug in REJECTED
        self.slammed = False

    def _back_to_select(self) -> None:
        self._enter_phase("select")
        self.picked = False
        self.sel_held = 0
        self.popups.clear()
        self.x, self.y = float(START_X), float(art.FLOOR_Y)
        self.vx = self.vy = 0.0
        self.landed = False
        self.door_open = 0.0
        self.audio.play_lobby()

    def _enter_phase(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    @property
    def section(self) -> str:
        return music.SONG[music.bar_at(self.song_t)]

    @property
    def trimester(self) -> int:
        bar = music.bar_at(self.song_t)
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

        if self.phase == "select":
            self._update_select(dt, inp)
        elif self.phase == "walk":
            self.x += WALK_SPEED * dt
            self.door_open = max(0.0, min(1.0, (self.x - (art.DOOR_X - 70)) / 50))
            if self.rejected:
                if self.x >= art.DOOR_X - SLAM_AT:              # it saw who's coming
                    if not self.slammed:
                        self.slammed = True
                        self.audio.play("miss")
                        self._popup("SLAM!", art.DOOR_X, art.DOOR_TOP - 10, art.F["pale"], life=0.7)
                    self.door_open = 0.0
                if self.x >= art.DOOR_X - BONK_AT:              # and he walks right into it
                    self._enter_phase("rejected")
                    self.vx, self.vy = BONK_LAUNCH
                    self.landed = False
                    self.audio.play("scratch")
                    self._popup("BONK!", self.x, self.y - 52, "#ffe14d", big=True, life=0.8)
            elif self.x >= art.DOOR_X - 2:
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
        elif self.phase == "rejected":
            if not self.landed:
                self.vy += OUT_GRAVITY * dt
                self.x += self.vx * dt
                self.y += self.vy * dt
                if self.y >= art.FLOOR_Y and self.vy > 0:
                    self.y, self.landed = art.FLOOR_Y, True
                    self._popup("THUD", self.x, self.y - 40, LAB_DIM, life=0.8)
            if inp.action and self.phase_t > REJECT_LINE_TIME * len(REJECT_LINES):
                self._back_to_select()
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

    def _update_select(self, dt: float, inp: Input) -> None:
        n = len(self.cast)
        if not self.picked:
            if inp.x and inp.x != self.sel_held:
                self.pick = (self.pick + inp.x) % n
                self.audio.play("tick")
            self.sel_held = inp.x
            if inp.action and self.phase_t > 0.3:
                self.picked, self.phase_t = True, 0.0
                self._choose(self.cast[self.pick])
                self.audio.play("pop")
                self.audio.stop_lobby(int(PICK_TIME * 1000))
                self._popup("LET'S GO!", W // 2, 22, "#ffe14d", big=True, life=PICK_TIME, rise=2)
        elif self.phase_t >= PICK_TIME:
            self._enter_phase("walk")
            self.popups.clear()
            return
        # ease the carousel round the shortest way, wrapping at the ends
        d = (self.pick - self.slide + n / 2) % n - n / 2
        self.slide = (self.slide + d * min(1.0, SELECT_SLIDE * dt)) % n
        # load one nearby dancer per frame so scrolling never stalls
        for off in sorted(range(-LOAD_RANGE, LOAD_RANGE + 1), key=abs):
            c = self.cast[(self.pick + off) % n]
            if c.slug not in _DANCERS:
                _load(c)
                break

    def _update_dance(self, dt: float, inp: Input) -> None:
        if self.audio.playing():                       # the song is the clock
            self.song_t = time.perf_counter() - self.song_t0 - AUDIO_LAG
        else:
            self.song_t += dt
        now = self.song_t

        bar, beat = music.bar_at(now) if now >= 0 else -1, math.floor(music.beats(now))
        self.flow += dt * TUNNEL_FLOW * music.bpm_at(max(0.0, now)) / music.BPM
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
            if bar in music.SPEEDUPS:                  # the tempo kicks up: say so, big
                self.shout = (outlined(music.SPEEDUPS[bar], "#ffe14d", 4), self.time)
                self.audio.play("speedup")

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
            if self.combo >= BREAK_AT:                 # a long streak fizzles out
                self._callout(self.rng.choice(BREAK_LINES), "#9cc4f0")
                self.audio.play("moan_aww")
            self.combo = 0
            self.life = max(0.0, self.life - LIFE_MISS)
            self.move = (DANCE_MOVES["miss"][0], self.time)
            self.audio.play("miss")
            return
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        if self.combo % CLIMAX_EVERY == 0:
            self._callout(self.rng.choice(CLIMAX_LINES), "#ffe14d")
            self.audio.play("moan_climax")
        elif self.combo % STREAK == 0:
            if not self.lines:
                self.lines = list(STREAK_LINES)
                self.rng.shuffle(self.lines)
            self._callout(self.lines.pop(), "#ff9ac8")
            self.audio.play("moan_" + self.rng.choice(MOANS_HOT if self.combo >= HOT_AT else MOANS_SOFT))
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
        if self.phase == "select":
            self._draw_select(screen)
        elif self.phase in ("dance", "flush"):
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

    # dancer select
    def _routine_frame(self, ld: Loaded, routine: tuple[str, ...], t: float) -> tuple[pygame.Surface, float, float]:
        """One of the select-screen routines at time t: (frame, x offset, lift)."""
        beat = int(t / BEAT)
        k = (t % BEAT) / BEAT
        move = routine[beat % len(routine)]
        f = ld.frames

        def fr(anim: str, i: int, facing: int = 1) -> pygame.Surface:
            seq = f[anim][facing]
            return seq[min(i, len(seq) - 1)]
        if move == "stepL" or move == "stepR":
            s = -1 if move == "stepL" else 1
            return fr("walk", int(k * 4), s), s * 4 * math.sin(k * math.pi), 0.0
        if move == "hop":
            return fr("jump", 1 if k < 0.3 else 2 if k < 0.7 else 3), 0.0, math.sin(k * math.pi) * 7
        if move == "squat":
            return fr("crouch", 0 if k < 0.15 or k > 0.85 else 1), 0.0, 0.0
        if move == "punch":
            return fr("attack", int(k * 4), 1 if beat % 2 else -1), 0.0, 0.0
        if move == "spin":
            return fr("idle", 0, 1 if int(k * 4) % 2 == 0 else -1), 0.0, abs(math.sin(k * math.tau)) * 2
        if move == "wave":
            return fr("interact", int(k * 4)), 0.0, 0.0
        return fr("idle", int(k * 4)), 0.0, 2 * (1 - k) if k < 0.3 else 0.0     # bob on the beat

    def _draw_select(self, screen: pygame.Surface) -> None:
        n = len(self.cast)
        beat = (self.time % BEAT) / BEAT
        pulse = (1 - beat) ** 3
        screen.fill(rgb(art.F["deep"]))
        # the womb's rings pulsing in the background
        for i in range(7, 0, -1):
            r = i * 26 + pulse * 6 + (self.time * 10) % 26
            col = mix(art.F["deep"], art.F["pink"], 0.12 + 0.05 * (i % 2) + 0.12 * pulse * (i < 3))
            pygame.draw.ellipse(screen, rgb(col), (W // 2 - r * 1.5, 96 - r * 0.8, r * 3, r * 1.6), 2)
        # stage and spotlight
        pygame.draw.rect(screen, rgb(mix(art.F["deep"], "#000000", 0.35)), (0, 140, W, H - 140))
        pygame.draw.line(screen, rgb(art.F["pink"]), (0, 140), (W, 140))
        spot = pygame.Surface((120, 150), pygame.SRCALPHA)
        pygame.draw.polygon(spot, (255, 230, 240, 26 + round(20 * pulse)), [(48, 0), (72, 0), (118, 150), (2, 150)])
        screen.blit(spot, (W // 2 - 60, -6))
        pygame.draw.ellipse(screen, rgb(mix(art.F["deep"], art.F["hi"], 0.35 + 0.2 * pulse)), (W // 2 - 34, 136, 68, 9))

        t = big_text(self.title, art.F["hi"])
        screen.blit(t, (W // 2 - t.get_width() // 2, 5))
        if not self.picked:
            s = text_surface("PICK YOUR DANCER", LAB_TEXT)
            screen.blit(s, (W // 2 - s.get_width() // 2, 21))

        # the carousel: everyone dancing, the pick big and in the spotlight
        slots = []
        for off in range(-3, 4):
            i = (round(self.slide) + off) % n
            dx = ((i - self.slide + n / 2) % n - n / 2) * SELECT_GAP
            if abs(dx) < W / 2 + SELECT_GAP:
                slots.append((abs(dx), dx, i))
        for _, dx, i in sorted(slots, reverse=True):          # far ones first, the pick on top
            c = self.cast[i]
            near = max(0.0, 1 - abs(dx) / SELECT_GAP)
            x = W // 2 + dx
            ld = _DANCERS.get(c.slug)
            if ld is None:                                     # still loading: a shadow
                pygame.draw.ellipse(screen, rgb(mix(art.F["deep"], "#000000", 0.4)), (x - 10, 125, 20, 5))
                continue
            routine = ROUTINES[i % len(ROUTINES)]
            if self.picked and i == self.pick:                 # chosen: show off
                routine = ("spin", "hop", "punch", "hop")
            img, ox, lift = self._routine_frame(ld, routine, self.time * (2 if self.picked and i == self.pick else 1))
            scale = 1 + near
            if scale > 1.02:
                size = round(SIZE * scale)
                img = pygame.transform.scale(img, (size, size))
            else:
                img = img.copy()
                img.set_alpha(150)
            feet = 128 + 12 * near
            screen.blit(img, (round(x + ox * scale - img.get_width() / 2), round(feet - GROUND * scale - lift * scale)))

        # who's up, and the arrows
        c = self.cast[self.pick]
        name = big_text(c.name.upper(), "#ffe14d" if self.picked else LAB_TEXT)
        screen.blit(name, (W // 2 - name.get_width() // 2, 146))
        tag = f"{self.pick + 1}/{n}"
        s = text_surface(tag, LAB_DIM)
        screen.blit(s, (W // 2 - s.get_width() // 2, 161))
        if not self.picked:
            nudge = round(2 * pulse)
            col = rgb(art.F["hi"])
            for side in (-1, 1):
                ax = W // 2 + side * (W // 2 - 10 + nudge)
                pygame.draw.polygon(screen, col, [(ax, 92), (ax - side * 6, 86), (ax - side * 6, 98)])
            if int(self.time * 2) % 2 == 0:
                s = text_surface("STICK: CHOOSE   BUTTON: GO IN", LAB_DIM)
                screen.blit(s, (W // 2 - s.get_width() // 2, 170))

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
        if self.phase == "walk":
            img = self._frame("walk", int(self.time * 8) % 4, 1)
        elif self.phase == "rejected":
            if not self.landed:
                img = self._frame("hurt", int(self.phase_t * 10) % 2, 1)
            elif self.phase_t < REJECT_LINE_TIME * 2:                  # sit there, stunned
                img = self._frame("crouch", 1, 1)
            else:                                                   # then sulk
                img = self._frame("idle", int(self.time * 2) % 4, -1)
            self._draw_bubble(screen)
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

    def _draw_bubble(self, screen: pygame.Surface) -> None:
        """The womb talking back, in a speech bubble pointing at its door."""
        i = int(self.phase_t / REJECT_LINE_TIME)
        if self.phase_t < 0.25 or self.phase_t > REJECT_LINE_TIME * len(REJECT_LINES):
            return
        lines = REJECT_LINES[min(i, len(REJECT_LINES) - 1)]
        surfs = [big_text(t, art.F["deep"]) for t in lines]
        bw = max(s.get_width() for s in surfs) + 12
        bh = sum(s.get_height() + 2 for s in surfs) + 8
        bx, by = max(4, min(W - 4 - bw, art.DOOR_X - bw // 2)), 44     # over the sculpture, clear of the sign
        pygame.draw.polygon(screen, rgb("#fff4f7"), [(art.DOOR_X - 8, by + bh - 2), (art.DOOR_X + 4, by + bh - 2),
                                                     (art.DOOR_X - 1, art.DOOR_TOP - 2)])
        pygame.draw.rect(screen, rgb("#fff4f7"), (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(screen, rgb(art.F["pink"]), (bx, by, bw, bh), 1, border_radius=4)
        y = by + 5
        for t in surfs:
            screen.blit(t, (bx + bw // 2 - t.get_width() // 2, y))
            y += t.get_height() + 2

    # inside
    def _heartbeat(self) -> float:
        """0..1 thump on every beat: a lub, then a smaller dub."""
        f = music.beats(self.song_t) % 1
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
        phase = self.flow
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
        self._draw_callouts(screen)

        # the membrane every lane ends on, and contractions closing in on it
        mem_col = mix(art.F["pale"], "#ffffff", 0.6 if self.time - self.flash.get("B", -9) < 0.12 else 0.0)
        for i in range(48):
            ang = i * math.tau / 48 + self.time * 0.3
            screen.set_at((round(CX + math.cos(ang) * MEM_RX), round(CY + math.sin(ang) * MEM_RY)), rgb(mem_col))
        for n in self.notes:
            if n.lane == "B" and n.judged is None and 0 <= n.t - now <= n.approach:
                k = 1 + 3.4 * (n.t - now) / n.approach
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
            if ahead > n.approach or (n.judged == "miss" and now - n.hit_t > 0.25):
                continue
            u = 1 - ahead / n.approach
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


        self._draw_shout(screen)
        if losing:                                     # the lights go red
            shade = a.beams
            shade.fill((120, 0, 20, min(140, round(self.phase_t * 160))))
            screen.blit(shade, (0, 0))

    def _draw_callouts(self, screen: pygame.Surface) -> None:
        if self.shout:                                 # the shout has the stage
            return
        for surf, t0, life in self.callouts:          # streak lines: pop in, hang, flicker out
            age = self.time - t0
            if age > life or age > life - 0.3 and int(age * 20) % 2:
                continue
            k = min(1.0, age / 0.12)
            img = surf if k >= 1 else pygame.transform.scale(surf, (max(1, round(surf.get_width() * (0.6 + 0.4 * k))),
                                                                      max(1, round(surf.get_height() * (0.6 + 0.4 * k)))))
            screen.blit(img, (CX - img.get_width() // 2, 34 - img.get_height() // 2))

    def _draw_shout(self, screen: pygame.Surface) -> None:
        if self.shout:                                 # FASTER! slams in huge, shakes, then goes
            surf, t0 = self.shout
            age = self.time - t0
            if age > SHOUT_TIME:
                self.shout = None
                return
            if age > SHOUT_TIME - 0.35 and int(age * 20) % 2:
                return
            z = 1 + 1.5 * max(0.0, 1 - age / 0.15) ** 2
            img = surf if z == 1 else pygame.transform.scale(surf, (round(surf.get_width() * z), round(surf.get_height() * z)))
            shake = 3 * max(0.0, 1 - age / 0.6)
            dx, dy = self.rng.uniform(-shake, shake), self.rng.uniform(-shake, shake)
            screen.blit(img, (round(CX - img.get_width() / 2 + dx), round(36 - img.get_height() / 2 + dy)))

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
                self._frame("idle", int(music.beats(self.song_t) * 2) % 4)
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
        if self.phase == "select":
            return
        if self.phase == "rejected" and self.phase_t > REJECT_LINE_TIME * len(REJECT_LINES):
            self._banner(screen, "REJECTED", ["THE WOMB IS CLOSED FOR BUSINESS", "PRESS BUTTON TO PICK SOMEONE ELSE"])
            return
        if self.phase == "dance" or self.phase == "flush":
            screen.blit(self.art.heart, (4, 4))
            pygame.draw.rect(screen, rgb(LAB_GRID), (15, 5, 62, 6))
            low = self.life < 25
            col = "#ff4a6a" if not low or int(self.time * 6) % 2 else "#ffffff"
            pygame.draw.rect(screen, rgb(col), (16, 6, round(60 * self.life / LIFE_MAX), 4))
            screen.blit(text_surface("VITALS", LAB_DIM), (16, 13))
            tri = ("FIRST", "SECOND", "THIRD")[max(0, self.trimester - 1)] if self.song_t >= music.BAR_START[1] else "COUNT-IN"
            s = text_surface(f"{tri} TRIMESTER" if self.song_t >= music.BAR_START[1] else tri, LAB_TEXT)
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
    if game.phase == "select" and game.cast[game.pick].slug in REJECTED:
        inp.x = 1 if int(game.time * 10) % 2 else 0
        return inp
    if game.phase != "dance":
        inp.action = game.phase in ("select", "won", "lost") and game.phase_t > 1.2 or \
            game.phase == "rejected" and game.phase_t > REJECT_LINE_TIME * len(REJECT_LINES) + 0.5
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
    ap.add_argument("--character", help="who's picked first on the dancer select, by slug (e.g. tech_bro)")
    ap.add_argument("--mute", action="store_true", help="no sound (the game keeps its own clock)")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()

    ch = None
    if args.character:
        everyone = cast()
        matches = [c for c in everyone if c.slug == args.character]
        if not matches:
            raise SystemExit(f"no character {args.character!r}; try one of: " + ", ".join(c.slug for c in everyone))
        ch = matches[0]

    run(lambda: WombRave(ch, seed=args.seed, mute=args.mute), "Womb Rave", scale=args.scale, fullscreen=args.fullscreen,
        autopilot=autopilot if args.demo else None, max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
