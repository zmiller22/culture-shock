"""Theories of Life: the main game.

    python -m lifesim [--fullscreen] [--scale 4] [--demo] [--skip-boot] [--mute]

You're a spirit with no body yet. The Life Lab Mainframe, a 1970s machine the
scientist insists is state of the art, runs a simulation of each theory of how
life begins. Push the button to boot it: the camera dives into the CRT, the
lab welcomes you as its next visitor, and you sign in with a 1-4 letter name,
arcade high-score style. Then the genesis program runs: code pours down the
screen and it zooms out from the Earth to the edge of everything (see
intro.py), where you form as a spirit. WE KNOW LIFE STARTS WITH DNA, so to get a body you spit in the jar
(Spit Kit, theory SPLICER): it reads your DNA, asks a behavioral survey, and
splices you a creature. That creature walks the theory map (see worldmap.py): every theory is a tile playing a
clip of its simulation, joined by paths you float along. Pick one, get
incarnated into it, and see whether it holds up. Every mini-game is one
simulation.

Controls (keyboard, or an arcade stick / gamepad):
    STICK / ARROWS            move along the map's paths; on the name entry, down goes A -> B, up goes back,
                              left and right move the cursor
    SPACE / Z / ENTER / any button  boot, select, continue (hold: sign in, the exit menu)
    ESC / Q                   quit

Leave it alone for IDLE_PROMPT s (outside the boot sequence and cut-scenes), or
hold the button on a menu (the map or the file listing) for MENU_HOLD s, or
anywhere else, mini-games included, for HOLD_ANYWHERE s, and the game freezes
under the exit menu (STILL THERE? when it came up by itself): CONTINUE,
RETURN TO THEORY MENU (once they've reached the map) and TERMINATE PROGRAM (back to the start screen).
The stick picks one and holding the button for SELECT_HOLD s takes it. A
countdown runs underneath, and letting it run out goes back to the start
screen for the next visitor. Because of the hold, menus act when the button
is let go.

Win a simulation and the theory is CONFIRMED; lose and it's REFUTED. The
terminal keeps score for the session. Test every theory and the lab says
CONGRATULATIONS! and lets slip that XXX IS THE ANSWER: typed into UNLOCK.EXE in
the file system, it plays the OOH sequence (see ooh.py). OOH, the old answer, still works too.

EXIT, down the right of the map, opens the same exit menu.

SYSTEM FILES, in the grid after the last theory, opens the lab's
file drawer (see files.py): notebooks, photos of experiments gone wrong, and
locked files whose 3-letter codes are hidden around the room.
"""

from __future__ import annotations

import argparse
import atexit
import math
import os
from pathlib import Path
import random
from dataclasses import dataclass, replace
from typing import Callable

import pygame

from minigames.shell import PROMPT, PROMPT_FLASH, READ_GRACE, Input, MiniGame, prompt_color, run
from sprites.canvas import Canvas, hex_to_rgba
from sprites.font import BIG_H, big_width, draw_big_text
from sprites.viewer import text_surface, to_surface

from . import art
from .art import CRT_BG, PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT, SCREEN
from . import saves, scores
from .activity import ActivityLog, disabled_by_env
from .files import FileTerminal
from .intro import Cosmos, Rain
from . import worldmap
from .worldmap import COLS, EXIT, EXIT_RECT, FILES, TILE_H, TILE_W, VOID, WorldMap, tile_at, tile_rect

# -- tuning ------------------------------------------------------------------------
# (each theory's par, the mini-game score that's worth PAR_POINTS lab points, is in theories():
#  roughly what its autopilot scores, so a great human run lands near 1000)
TYPE_RATE = 70.0           # characters/s the terminal types at
LINE_PAUSE = 0.12          # s between lines
VISITOR_LOG = Path(os.environ.get("LIFE_LAB_VISITORS", Path.home() / ".life_lab" / "visitors.txt"))
NAME_LEN = 4               # letters in a visitor's name, like an arcade high score
NAME_HOLD = 0.8            # s of holding the button that signs off a name shorter than NAME_LEN
NAME_REPEAT = (0.4, 0.09)  # s before a held stick starts repeating, then s per letter
NAME_TIMEOUT = 40.0        # s of nobody touching anything before it signs them in as is
NAME_TAKEN_TIME = 2.5      # s NAME TAKEN stays up when they say a taken name isn't theirs
SCORES_TIME = 8.0          # s of HIGH SCORES when a visit ends, before the next visitor's start screen
ATTRACT = (8.0, 6.0)       # s of PUSH ANY BUTTON TO BOOT UP, then s of HIGH SCORES, round and round on the start screen
SCORE_ROWS = 10            # rows on the high score table
BUTTON_PRESS = 0.35        # s the boot button stays down before the code rain starts
ENTER_TIME = 1.1           # s to dive into the CRT after the boot button
RAIN_TIME = 1.6            # s of code rain as the genesis program starts, before the zoom out
RAIN_FADE = 0.8            # s the rain takes to clear off the start of the program
SUMMON_FORM = 1.6          # s for the spirit to come together in the void
MAP_FADE = 0.5             # s for the theory map to fade in
LOAD_TIME = 1.8            # s from picking a theory to the screen switching off
LOAD_DIVE = 0.7            # s for the spirit to dive into the tile, which then grows to fill the screen
CRT_OFF_TIME = 0.35
CRT_ON_TIME = 0.35
IDLE_PROMPT = 60.0         # s of nobody touching anything before the "still there?" countdown
IDLE_COUNTDOWN = 60        # s it counts down from before it goes back to the start screen
SELECT_HOLD = 1.0          # s of holding the button on the exit menu to take the option
MENU_HOLD = 0.8            # s of holding the button on a menu to bring the countdown up (menus act on release)
HOLD_ANYWHERE = 2.5        # s of holding the button anywhere else, mini-games too, to bring the countdown up
REEL_IDLE, REEL_FAST = 90.0, 900.0      # degrees/s
DIVE = (SCREEN[0], SCREEN[1] + 7, SCREEN[2], SCREEN[2] * 9 // 16)     # the part of the glass the camera dives into
SIGN_IN_LINES = ["WELCOME TO THE LIFE LAB, VISITOR {num}!", "",
                 "HERE YOU CAN EXPLORE STATE-OF-THE-ART SIMULATIONS",
                 "ON LEADING THEORIES OF HOW LIFE IS CREATED.", "", "WHAT SHOULD WE CALL YOU?"]
JOURNEY_LINES = ["OUR JOURNEY STARTS", "AT THE VERY BEGINNING..."]
JOURNEY_TIME = 4.0         # s on the journey screen before the genesis program runs (the button skips it)
SPIRIT_LINES = ["YOU ARE A SPIRIT!", "BUT HOW DO YOU", "BECOME A LIFE?"]
DNA_LINES = ["WE KNOW LIFE", "STARTS WITH DNA."]
DNA_HOLD = 1.5             # s the DNA line stays up once it's typed, before the Spit Kit
# once every theory's been tested: the lab's thanks, and the answer to type into UNLOCK.EXE (see ooh.py)
FRONTIER_LINES = ["CONGRATULATIONS!", "", "YOU HAVE EXPANDED THE FRONTIER", "OF OUR KNOWLEDGE.", "",
                  "WHAT YOU LEARNED...", "XXX IS THE ANSWER.", "",
                  "MAYBE THERE IS SOMEWHERE IN THE", "FILE SYSTEM YOU COULD USE THAT..."]
# the tour of the map, the first time on it: what to light up, and what to say
RETURN_OPTIONS = ["PLAY AGAIN", "EXPLORE OTHER THEORIES"]   # after a simulation's verdict
# the first time on the map: one INSTRUCTIONS screen, arrows pointing down at the controls line
TOUR_SHOW = 2.0             # s before HOLD BUTTON TO CONTINUE comes up (and a hold works)
TOUR_HOLD = 1.0             # s of holding the button that goes on to the map


def next_visitor() -> int:
    """The next number in the lab's visitor log (1 if there's no log yet)."""
    try:
        last = VISITOR_LOG.read_text().split()
        return int(last[-2]) + 1 if len(last) >= 2 else 1
    except (OSError, ValueError):
        return 1


def taken_names() -> set[str]:
    """Every name already in the visitor log or with a saved game: signing in as one
    asks whether it's theirs."""
    try:
        words = VISITOR_LOG.read_text().split()
        logged = set(words[1::2])
    except OSError:
        logged = set()
    return logged | saves.names()


def sign_in(num: int, name: str) -> None:
    try:
        VISITOR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with VISITOR_LOG.open("a") as f:
            f.write(f"{num:04d} {name}\n")
    except OSError:
        pass                                          # a read-only cabinet still plays


class NameEntry:
    """Old-school arcade initials, all on the stick: up and down roll the letter
    under the cursor (down goes A -> B; one step up from A is a blank, for names
    shorter than NAME_LEN), left and right move the cursor, and holding the
    button down signs off. Nothing else does anything: a tap of the button is
    ignored, so nobody types a letter by accident.

    A name someone already has asks HAVE YOU PLAYED HERE BEFORE? The stick picks
    YES or NO and holding the button answers. YES signs them in as that name
    (`returning`, so the game can pick up their saved game); NO says the name's
    taken, and they change it."""

    LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    ROLL = LETTERS + [" "]                            # the blank sits one step up from A

    def __init__(self, taken: set[str] | None = None) -> None:
        self.taken = taken or set()                   # names already signed in: these ask PLAYED HERE BEFORE?
        self.taken_t = 0.0                            # s left on NAME TAKEN
        self.slots = ["A"] + [" "] * (NAME_LEN - 1)
        self.pos = 0                                  # the slot the cursor's on
        self.done = False
        self.held = (0, 0)
        self.hold_t = 0.0
        self.press: float | None = None               # s the button's been held down, while it is
        self.armed = False                            # a button already down when this opened doesn't count
        self.idle = 0.0
        self.ask: str | None = None                   # the taken name, while PLAYED HERE BEFORE? is up
        self.ask_sel = 0                              # 0 = YES, 1 = NO
        self.returning = False                        # they said YES: it's their name from before

    @property
    def name(self) -> str:
        return "".join(self.slots).replace(" ", "")

    @name.setter
    def name(self, value: str) -> None:
        self.slots = list(value[:NAME_LEN].ljust(NAME_LEN))

    @property
    def letter(self) -> str:
        return self.slots[self.pos]

    @property
    def hold_k(self) -> float:
        """0..1, how far a held button is to signing off (or to answering PLAYED HERE BEFORE?)."""
        if self.press is None or (not self.name and self.ask is None):
            return 0.0
        return min(1.0, self.press / NAME_HOLD)

    def _roll(self, step: int) -> None:
        k = self.ROLL.index(self.slots[self.pos])
        self.slots[self.pos] = self.ROLL[(k + step) % len(self.ROLL)]

    def _move(self, step: int) -> None:
        pos = max(0, min(NAME_LEN - 1, self.pos + step))
        if pos > self.pos and self.slots[pos] == " ":   # a new slot starts on the letter before it
            self.slots[pos] = self.slots[self.pos] if self.slots[self.pos] != " " else "A"
        self.pos = pos

    def _held_long(self, dt: float, inp: Input) -> bool:
        """True the tick a hold reaches NAME_HOLD. A tap does nothing at all."""
        if not self.armed:
            self.armed = not inp.held
            return False
        if not inp.held:
            self.press = None
            return False
        self.press = (self.press or 0.0) + dt
        if self.press >= NAME_HOLD:
            self.press, self.armed = None, False      # (let go before the next hold counts)
            return True
        return False

    def update(self, dt: float, inp: Input) -> None:
        if self.done:
            return
        self.taken_t = max(0.0, self.taken_t - dt)
        self.idle += dt
        dirs = (inp.x, inp.y)
        if dirs != (0, 0) or inp.action or inp.held:
            self.idle = 0.0
        if self.ask is not None:
            self._update_ask(dt, inp, dirs)
            return
        if inp.y:
            if dirs != self.held:
                self._roll(inp.y)                     # down goes A -> B
                self.hold_t = 0.0
            else:
                self.hold_t += dt
                while self.hold_t > NAME_REPEAT[0]:   # held: keep rolling
                    self._roll(inp.y)
                    self.hold_t -= NAME_REPEAT[1]
        elif inp.x and dirs != self.held:
            self._move(inp.x)
        self.held = dirs
        if self._held_long(dt, inp) and self.name:
            if self.name in self.taken:               # someone has it: is it them?
                self._ask(self.name)
                return
            self.done = True                          # held down: that's the name
        if self.idle > NAME_TIMEOUT:
            self.name = self.name or "GHST"
            rng = random.Random()
            while self.name in self.taken:            # nobody's here to pick another, so make one up
                self.name = "".join(rng.choice(self.LETTERS) for _ in range(NAME_LEN))
            self.done = True

    def _ask(self, name: str) -> None:
        self.ask, self.ask_sel = name, 0
        self.name = name
        self.press, self.armed = None, False          # the hold that finished the name isn't an answer
        self.held = (1, 1)                            # a stick already pushed doesn't move it straight away

    def _update_ask(self, dt: float, inp: Input, dirs: tuple[int, int]) -> None:
        """PLAYED HERE BEFORE? The stick picks YES or NO, holding the button answers."""
        move = inp.x or inp.y
        if move and dirs != self.held:
            self.ask_sel = 0 if move < 0 else 1
        self.held = dirs
        if self._held_long(dt, inp):
            self.answer(self.ask_sel == 0)
        elif self.idle > NAME_TIMEOUT:                # nobody's answering: not them, then
            self.answer(False)
            self.idle = NAME_TIMEOUT + 1              # and the timeout makes a name up

    def answer(self, yes: bool) -> None:
        name, self.ask = self.ask, None
        if yes:
            self.name, self.returning, self.done = name, True, True
            return
        self.taken_t = NAME_TAKEN_TIME                # NAME TAKEN: they change it with the stick
        self.press, self.armed = None, False


@dataclass
class Theory:
    code: str
    name: str
    game: str                   # the mini-game's own name, on its map tile
    blurb: tuple[str, str]
    players: str
    make: Callable[..., MiniGame]   # make(prev): prev is the round just played, for PLAY AGAIN (no how-to)
    autopilot: Callable[[MiniGame], Input]
    quips: dict[str, str]
    par: int = 0                # the mini-game's own score for a strong run, which the lab counts as PAR_POINTS

    def lab_points(self, score: int) -> int:
        """The mini-game's own score on the lab's common scale, so every theory is worth about the same."""
        return round(max(0, score) * PAR_POINTS / self.par) if self.par else 0


PAR_POINTS = 1000           # lab points for a strong run on any theory


def theories(mute: bool = False) -> list[Theory]:
    """The simulations on the tape library, in the order life supposedly happens.
    Imports are lazy so the mainframe boots before the mini-games load."""
    # each takes the round just played when they PLAY AGAIN: then there's no title or how-to
    def stork(prev=None):
        from minigames.stork_bomber.game import StorkBomber
        return StorkBomber(show_title=prev is None)

    def soup(prev=None):
        from minigames.primordial_soup.game import PrimordialSoup
        return PrimordialSoup(show_title=prev is None)

    def meet(prev=None):
        from minigames.it_takes_two.game import ItTakesTwo
        return ItTakesTwo(show_title=prev is None)

    def womb(prev=None):
        from minigames.womb_rave.game import WombRave
        dancer = prev.cast[prev.pick] if prev is not None and not prev.rejected else None   # the same dancer again
        return WombRave(character=dancer, show_title=prev is None, mute=mute)

    def spit(prev=None):
        from minigames.spit_kit.game import SpitKit
        return SpitKit(walk_out=False)          # no how-to, and straight to the map once you're spliced

    def bear(prev=None):
        from minigames.build_a_bear.game import BuildABear
        return BuildABear(show_title=prev is None)

    def pilot(module: str):
        def go(game):
            import importlib
            return importlib.import_module(module).autopilot(game)
        return go

    return [
        Theory("01", "THE STORK HYPOTHESIS", "STORK BOMBER", ("BABIES ARE DELIVERED BY AIR", "BY A LARGE BIRD. TEST DELIVERY."),
               "1P", stork, pilot("minigames.stork_bomber.game"),
               {"win": "BIRD CONFIRMED. NOTIFY THE PRESS.", "lose": "NO BIRD. WHERE DO BABIES COME FROM?"}, par=1800),
        Theory("02", "PRIMORDIAL SOUP", "PRIMORDIAL SOUP", ("LIFE BEGAN IN A WARM BROTH", "OF CHEMICALS. COOK SOME UP."),
               "1P", soup, pilot("minigames.primordial_soup.game"),
               {"win": "THE SOUP IS ALIVE. IT ATE THE CHEF.", "lose": "SOUP COLD. DINERS ANGRY."}, par=1550),
        Theory("03", "IT TAKES TWO", "IT TAKES TWO", ("LIFE STARTS WHEN TWO CELLS", "FALL IN LOVE. 2 SPIRITS NEEDED."),
               "2P", meet, pilot("minigames.it_takes_two.game"),
               {"win": "THEY MET. IT WAS ADORABLE.", "lose": "THEY NEVER MET. TRY AGAIN NEXT MONTH."}, par=4700),
        Theory("04", "THE WOMB RAVE", "WOMB RAVE", ("LIFE IS A NINE MONTH PARTY", "IN A VERY SMALL CLUB."),
               "1P", womb, pilot("minigames.womb_rave.game"),
               {"win": "BIRTH ACHIEVED. VIBES IMMACULATE.", "lose": "EVICTED. THE BOUNCER WAS THE CERVIX."}, par=20100),
        Theory("05", "THE GENETIC CODE", "SPIT KIT", ("LIFE IS A RECIPE IN YOUR SPIT.", "THE JAR WILL READ YOURS."),
               "1P", spit, pilot("minigames.spit_kit.game"),
               {"win": "YOU ARE MOSTLY SOMEONE ELSE.", "lose": "NO SPIT. NO SCIENCE."}),
        Theory("06", "SPARK OF LIFE", "BUILD-A-BEAR", ("A BOLT OF LIGHTNING BRINGS DEAD", "MATTER TO LIFE. SEW, THEN ZAP."),
               "1P", bear, pilot("minigames.build_a_bear.game"),
               {"win": "IT'S ALIVE! IT WANTS A HUG.", "lose": "NO LIGHTNING. JUST A SAD TOY."}, par=1950),
    ]


FILES_BLURB = ("WAIT... WHAT IS THIS?",)
EXIT_BLURB = ("LEAVE THE LIFE LAB.", "THE NEXT VISITOR IS WAITING.")
SPLICER = "05"             # the theory that gives the spirit its body (Spit Kit), played before the map
AVATAR_FEET = 20           # px below a tile's middle that the new body stands on the map
VERDICT = {"win": "CONFIRMED", "lose": "REFUTED", None: "UNTESTED", "?": "INCONCLUSIVE"}


def rgb(c: str) -> tuple[int, int, int]:
    return hex_to_rgba(c)[:3]


class Typer:
    """Lines of terminal text that type themselves out, one after another."""

    def __init__(self, lines: list[str], rate: float = TYPE_RATE, pause: float = LINE_PAUSE) -> None:
        self.lines, self.rate, self.pause = lines, rate, pause
        self.t = 0.0
        # when each line starts typing
        self.starts, t = [], 0.0
        for line in lines:
            self.starts.append(t)
            t += len(line) / rate + pause
        self.end = t

    def update(self, dt: float) -> None:
        self.t += dt

    def finish(self) -> None:
        self.t = self.end

    @property
    def done(self) -> bool:
        return self.t >= self.end

    def visible(self) -> list[str]:
        out = []
        for line, start in zip(self.lines, self.starts):
            if self.t < start:
                break
            out.append(line[:int((self.t - start) * self.rate)])
        return out


class Glyphs:
    """Cache of rendered text, since the terminal redraws every frame.

    The terminal is one colour: every shade of phosphor (dim, faint, the white-hot
    highlight) comes out as plain PHOSPHOR, so text is always the brightest, easiest
    thing to read. The exceptions are CRT_BG, for dark text on a lit bar, and
    PROMPT, the violet every stick and button instruction is drawn in. PROMPT
    comes out flashing (see prompt_color).
    `big` uses the 5x7 font instead of the 3x5 one."""

    def __init__(self, mono: bool = True) -> None:
        self.mono = mono
        self.cache: dict[tuple[str, str, int, bool], pygame.Surface] = {}

    def get(self, s: str, color: str, scale: int = 1, big: bool = False) -> pygame.Surface:
        if color == PROMPT:
            color = prompt_color()
        if self.mono and color not in (CRT_BG, PROMPT, PROMPT_FLASH):
            color = PHOSPHOR
        key = (s, color, scale, big)
        if key not in self.cache:
            if big:
                c = Canvas(max(1, big_width(s)), BIG_H)
                draw_big_text(c, 0, 0, s, color)
                surf = to_surface(c)
            else:
                surf = text_surface(s, color)
            if scale > 1:
                surf = pygame.transform.scale_by(surf, scale)
            self.cache[key] = surf
        return self.cache[key]


class Art:
    def __init__(self) -> None:
        self.room = to_surface(art.room())
        self.reels = [to_surface(art.reel(f)) for f in range(art.REEL_FRAMES)]
        self.spirit = [to_surface(art.spirit(f)) for f in range(art.SPIRIT_FRAMES)]
        sw, sh = SCREEN[2], SCREEN[3]
        # no scanlines on the CRT: with text this small they make it hard to read
        # darken the corners so the glass looks curved
        self.vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(sh):
            for x in range(sw):
                d = math.hypot((x - sw / 2) / (sw / 2), (y - sh / 2) / (sh / 2))
                if d > 1.1:                       # just the very corners, clear of the text
                    self.vignette.set_at((x, y), (0, 0, 0, min(200, int((d - 1.1) * 300))))
        self.scanlines = pygame.Surface((art.W, art.H), pygame.SRCALPHA)
        for y in range(0, art.H, 2):
            self.scanlines.fill((0, 0, 0, 45), (0, y, art.W, 1))
        # a soft halo, added on top (so it's plain colour scaled by brightness, no alpha)
        self.glow = pygame.Surface((24, 24))
        er, eg, eb = rgb(art.SPIRIT_EDGE)
        for y in range(24):
            for x in range(24):
                k = max(0.0, 1 - math.hypot(x - 11.5, y - 11.5) / 12) ** 2 * 0.35
                self.glow.set_at((x, y), (int(er * k), int(eg * k), int(eb * k)))


_ART: Art | None = None


class LifeSim:
    """The main game. It's a MiniGame itself, so it runs in the same shell, and
    while a simulation is on it hands every tick to that mini-game."""

    title = "THEORIES OF LIFE"

    def __init__(self, skip_boot: bool = False, mute: bool = False, seed: int | None = None,
                 record: bool = True, log_activity: bool = True, idle_exit: bool = True,
                 played_all: bool = False) -> None:
        global _ART
        import minigames.tutorial
        minigames.tutorial.EXIT_HINT = idle_exit    # each how-to's last page: DONE PLAYING? HOLD ANY BUTTON TO EXIT
        _ART = _ART or Art()
        self.art = _ART
        self.text = Glyphs()
        self.rng = random.Random(seed)
        every = theories(mute)
        # the genetic code isn't a tile: it's how the spirit gets a body, straight after it forms
        self.splicer = next(t for t in every if t.code == SPLICER)
        self.theories = [t for t in every if t is not self.splicer]
        self.avatar: dict[str, dict[int, list[pygame.Surface]]] | None = None   # the body they got, for the map
        self.facing = 1
        self.results: dict[str, list[str]] = {t.code: [] for t in self.theories}
        self.frontier_shown = False             # the CONGRATULATIONS! screen comes up once a session
        if played_all:                          # testing: as if every theory's been played already
            self.results = {code: ["?"] for code in self.results}
        self.map = WorldMap([t.code for t in self.theories])
        self.result: str | None = None
        self.done = False
        self.time = 0.0
        self.reel_angle = [0.0] * 4
        self.reel_speed = REEL_IDLE
        self.sim: MiniGame | None = None
        self.sim_theory: Theory | None = None
        self.last: tuple[Theory, str] | None = None
        self.crt = pygame.Surface(SCREEN[2:])
        self.frame = pygame.Surface((art.W, art.H))
        self.motes: list[list[float]] = []
        self.void_stars = [(self.rng.randrange(art.W), self.rng.randrange(art.H), self.rng.choice((40, 70, 110)))
                           for _ in range(70)]
        self.rain: Rain | None = None
        self.cosmos: Cosmos | None = None
        self.pushed: float | None = None
        self.record = record                    # write visitors to the log (not in demos and tests)
        self.visitor = next_visitor()
        self.name = "ANON"                      # until they sign in (--skip-boot never asks)
        self.signed_in = False
        self.best: dict[str, int] = {}          # theory code -> their best points on it (the total is the high score)
        self.last_points = 0                    # points from the simulation that just ended
        self.prev_sim: MiniGame | None = None   # the round that just ended, while its verdict is up
        self.replay = False                     # PLAY AGAIN: the next load skips the how-to
        self.time_base = 0.0                    # s of play on earlier visits, for a visitor who's come back
        self.has_save = False                   # they've got a body, so there's a game to save (see saves.py)
        self.saved_frames: dict[str, int] = {}  # what's in the saved body's strips
        self.return_sel = 1                     # the picked option on a simulation's verdict screen
        self.return_y = 0
        self.return_press: float | None = None  # s the button's been held on the verdict's choice
        self.return_armed = False               # the button has to come up before a hold counts
        self.score_saved = False
        self.scores = scores.ranked(scores.load())
        self.entry: NameEntry | None = None
        self.tutorial: int | None = None        # the page of the map tour showing, if it's on
        self.tour_t = 0.0                       # s the tour page has been up
        self.tour_press: float | None = None    # s the button's been held on it
        self.tour_armed = False                 # the button has to come up before a hold turns a page
        # what each visitor does (games played, files opened, codes): play_log/<machine>.csv.
        # On unless turned off, never in demos/tests
        self.activity = ActivityLog(enabled=record and log_activity and not disabled_by_env(),
                                    visitor=self.visitor, name=self.name,
                                    games={t.code: t.game for t in every})
        self.sim_started = 0.0                  # self.time when the current simulation started, for theory_end
        self.activity("session_start", skip_boot=skip_boot)
        atexit.register(self.activity.close)
        atexit.register(self._save_score)       # quit with ESC: the visit still counts
        self.term = FileTerminal(mute, log=self.activity)
        # the "still there?" countdown: see _idle()
        self.idle_exit = idle_exit
        self.idle = 0.0                         # s since anyone touched anything
        self.countdown: float | None = None     # s left on the countdown while it's up
        self.hold: float | None = None          # s the button has been held on the exit menu
        self.menu_sel = 0                       # which exit menu option is picked
        self.menu_y = 0                         # the stick last tick, so a held stick moves one option
        self.prompt_via = "idle"                # what brought the exit menu up: idle, hold or exit_tile
        self.swallow = False                    # eat input after the countdown until hands are off
        self.armed = True                       # False: opened by a held button, waiting for it to let go
        self.press: float | None = None         # s the button's been down on a menu
        self.long_press: float | None = None    # s the button's been down anywhere else (since it went down)
        self.hold_exit = skip_boot              # holding anywhere only exits once they've reached the map
        if skip_boot:
            self._random_avatar()
        if skip_boot and played_all:            # straight to the CONGRATULATIONS! screen
            self.frontier_shown = True
            self._go("frontier")
        else:
            self._go("hub" if skip_boot else "off")

    @property
    def sel(self) -> int:
        """The map node the body's on: a theory's index, FILES or EXIT."""
        return self.map.sel

    # -- phases --------------------------------------------------------------------
    def _go(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0
        if phase == "off":
            self.pushed = None
        elif phase == "rain":
            self.rain = Rain(SCREEN[2], SCREEN[3], seed=self.rng.random())
        elif phase == "cosmos":
            self.cosmos = Cosmos(seed=self.rng.random())
        elif phase == "summon":                 # sign in: the welcome, then the name entry
            self.entry = None
            self.typer = Typer([s.format(num=f"{self.visitor:04d}") for s in SIGN_IN_LINES])
        elif phase == "journey":
            self.typer = Typer(JOURNEY_LINES, rate=24, pause=0.5)
        elif phase == "dnafact":
            self.typer = Typer(DNA_LINES, rate=24, pause=0.4)
        elif phase == "spirit":                 # after the big bang the spirit comes together
            self.typer = Typer(SPIRIT_LINES, rate=30, pause=0.6)
            self.motes = [[math.cos(a) * r, math.sin(a) * r * 0.6, self.rng.uniform(0.5, 1.0)]
                          for a, r in ((self.rng.uniform(0, math.tau), self.rng.uniform(50, 180)) for _ in range(70))]
        elif phase == "load":
            t = self.theories[self.sel]
            self.typer = Typer([f"MOUNTING TAPE {t.code}: {t.name}", f"INCARNATING VISITOR {self.name}..."], rate=90)
        elif phase == "return":
            theory, res = self.last
            lines = [f"SIMULATION {theory.code} ENDED.", f"VISITOR {self.name} DISINCARNATED.", "",
                     f"RESULT: THEORY {VERDICT.get(res, VERDICT['?'])}", theory.quips.get(res, "THE DATA ARE A MESS."),
                     f"POINTS: {self.last_points}   BEST: {self.best.get(theory.code, 0)}   TOTAL: {self.points}", ""]
            tested = [t for t in self.theories if self.results[t.code]]
            confirmed = [t for t in self.theories if "win" in self.results[t.code]]
            if len(confirmed) == len(self.theories):
                lines += ["ALL THEORIES CONFIRMED.", "ALL OF THEM. AT ONCE. SOMEHOW."]
            else:
                lines += [f"THEORIES TESTED: {len(tested)} OF {len(self.theories)}"]
            self.typer = Typer(lines)
            self.return_sel = RETURN_OPTIONS.index("PLAY AGAIN" if res != "win" else "EXPLORE OTHER THEORIES")
            self.return_y = 1                   # a stick already held doesn't move it straight away
            self.return_press, self.return_armed = None, False
        elif phase == "frontier":
            self.typer = Typer(FRONTIER_LINES, rate=30, pause=0.6)

    # -- the "still there?" countdown -----------------------------------------------------
    def _idle_paused(self) -> bool:
        """Times nobody is expected to touch anything: the start screen, the boot
        sequence, loading a tape, a rick roll, or a mini-game's own cut-scene."""
        if self.phase in ("off", "dive", "journey", "dnafact", "rain", "cosmos", "load"):
            return True
        if self.phase == "files":
            return self.term.playing
        if self.phase == "sim":
            return bool(getattr(self.sim, "cutscene", False))
        return False

    def _idle(self, dt: float, inp: Input) -> bool:
        """Track inactivity and run the countdown. True means it has the screen
        and the game underneath stays paused this tick."""
        touched = bool(inp.x or inp.y or inp.action or inp.held) or \
            any(p.x or p.y or p.action for p in inp.players)
        if self.swallow:                     # the press that dismissed it isn't for the game
            self.swallow = touched
            return touched
        if self.countdown is None:
            self.idle = 0.0 if touched or self._idle_paused() else self.idle + dt
            if self.idle < IDLE_PROMPT:
                return False
            self._open_prompt("idle")
            return True
        self.countdown -= dt
        opts = self.menu_options()
        y = inp.y or inp.x or next((p.y or p.x for p in inp.players if p.y or p.x), 0)
        if not self.armed:                   # brought up by holding the button: let go first
            self.armed = not inp.held
        elif self.hold is not None:          # holding: a bar fills up to taking the option
            if inp.held:
                self.hold += dt
                if self.hold >= SELECT_HOLD:
                    self._choose(opts[self.menu_sel])
                    return True
            else:                            # let go too soon: nothing happens
                self.hold = None
        elif inp.action:
            self.hold = 0.0
        elif y and not self.menu_y:          # the stick: up and down the options, one per push
            self.menu_sel = max(0, min(len(opts) - 1, self.menu_sel + y))
        if touched:                          # someone's here: the countdown starts over
            self.countdown = float(IDLE_COUNTDOWN)
        self.menu_y = y
        if self.countdown is not None and self.countdown <= 0:
            self._back_to_start("timeout")
        return True

    def menu_options(self) -> list[str]:
        """The exit menu. No theory menu to go back to until they've reached the map."""
        if self.hold_exit:
            return ["CONTINUE", "RETURN TO THEORY MENU", "TERMINATE PROGRAM"]
        return ["CONTINUE", "TERMINATE PROGRAM"]

    def _choose(self, option: str) -> None:
        self.activity("menu_choice", option=option, phase=self.phase, via=self.prompt_via)
        if option == "CONTINUE":
            self._dismiss()
        elif option == "RETURN TO THEORY MENU":
            self._to_theory_menu()
        else:
            self._back_to_start(self.prompt_via)

    def _to_theory_menu(self) -> None:
        """Back to the map from wherever they are. A simulation they walk out of isn't scored."""
        if self.phase == "sim" and self.sim is not None:
            self.activity("theory_end", theory=self.sim_theory.code, result="quit", secs=self._sim_secs())
            if self.sim_theory is not self.splicer:
                self.map.place(self.theories.index(self.sim_theory))
            self.sim = None
        elif self.phase == "files":
            self.term.media.stop()
            self.activity("files_close")
        if pygame.mixer.get_init():              # whatever was playing stays behind
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()
            pygame.mixer.stop()
            pygame.mixer.music.stop()
        self.countdown = self.hold = None
        self.idle = 0.0
        self.swallow = True                      # the hold that picked it isn't for the map
        self._go("hub")

    def _open_prompt(self, via: str) -> None:
        self.countdown, self.hold = float(IDLE_COUNTDOWN), None
        self.armed = via != "hold"
        self.prompt_via, self.menu_sel = via, 0
        self.menu_y = 1                          # a stick already held doesn't move it straight away
        self.press = None
        self.term.hold_k = 0.0
        self.activity("idle_prompt", phase=self.phase, via=via)
        if pygame.mixer.get_init():              # the game underneath is frozen, so its sound is too
            pygame.mixer.pause()
            pygame.mixer.music.pause()

    def _menu_button(self, dt: float, inp: Input) -> Input | None:
        """On the menus (the theories and the file listing) the button acts when
        it's let go, so holding it can bring up the exit countdown instead.
        None means the countdown just came up."""
        menu = self.phase == "hub" and self.tutorial is None or self.phase == "files" and self.term.mode == "list"
        if not menu:
            self.press = None
            return inp
        if inp.action:
            self.press = 0.0
        elif self.press is None:
            return inp
        elif inp.held:
            self.press += dt
            if self.press >= MENU_HOLD:
                self._open_prompt("hold")
                return None
        else:                                    # let go in time: that's a press
            self.press = None
            return replace(inp, action=True)
        return replace(inp, action=False)

    @property
    def hold_k(self) -> float:
        """0..1, how far a held button on a menu is to the countdown (0 for a quick tap)."""
        if self.press is None or self.press < 0.15:
            return 0.0
        return min(1.0, (self.press - 0.15) / (MENU_HOLD - 0.15))

    def _long_hold(self, dt: float, inp: Input) -> bool:
        """Off the menus, once they've reached the map, holding the button down for
        HOLD_ANYWHERE brings the countdown up, whatever's going on: a cut-scene, a mini-game.
        True means it just came up. The game still sees the button as usual."""
        if not self.hold_exit or self.press is not None or self.countdown is not None or \
                self.phase == "hub" and self.tutorial is not None or \
                self.phase == "sim" and getattr(self.sim, "hold_in_use", False) or \
                self.phase == "return":                # (its choice is made by holding)
            # (the tour's holds turn its pages, and a mini-game asking for a hold gets it)
            self.long_press = None
            return False
        if inp.action:
            self.long_press = 0.0
        elif self.long_press is not None:
            self.long_press = self.long_press + dt if inp.held else None
        if self.long_press is not None and self.long_press >= HOLD_ANYWHERE:
            self._open_prompt("hold")
            self.long_press = None
            return True
        return False

    def _draw_long_hold(self, screen: pygame.Surface) -> None:
        """Once a hold looks deliberate, a bar along the bottom fills up to the exit menu."""
        t = self.long_press
        if t is None or t < 0.6:
            return
        k = min(1.0, (t - 0.6) / (HOLD_ANYWHERE - 0.6))
        s = self.text.get("KEEP HOLDING THE BUTTON: EXIT MENU", PROMPT, big=True)
        w = max(s.get_width(), 120) + 12
        box = pygame.Rect(art.W // 2 - w // 2, art.H - 24, w, 20)
        screen.fill(rgb(CRT_BG), box)
        pygame.draw.rect(screen, rgb(PHOSPHOR), box, 1)
        screen.blit(s, (box.centerx - s.get_width() // 2, box.y + 3))
        screen.fill(rgb(PHOSPHOR_FAINT), (box.x + 6, box.y + 13, w - 12, 3))
        screen.fill(rgb("#eaffea"), (box.x + 6, box.y + 13, int((w - 12) * k), 3))

    def _dismiss(self) -> None:
        self.countdown = self.hold = None
        self.idle = 0.0
        self.swallow = True
        self.activity("idle_continue")
        if pygame.mixer.get_init():
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()

    def _sim_secs(self) -> int:
        return round(self.time - self.sim_started)

    @property
    def confirmed(self) -> int:
        return sum("win" in r for r in self.results.values())

    @property
    def explored(self) -> int:
        return sum(bool(r) for r in self.results.values())

    @property
    def points(self) -> int:
        return sum(self.best.values())

    def my_score(self) -> scores.Score:
        return scores.Score(self.visitor, self.name, self.explored, self.points, self.confirmed)

    def _save_game(self, avatar=None) -> None:
        """Their saved game, so they can come back to it under the same name. Only once they've got a body."""
        if not (self.record and self.signed_in and self.has_save):
            return
        state = saves.Save(self.name, self.visitor, results={k: list(v) for k, v in self.results.items()},
                           frontier_shown=self.frontier_shown, best=dict(self.best),
                           played=self.time_base + self.time, frames=dict(self.saved_frames))
        saves.save(state, avatar)                     # with a body, this fills in state.frames
        self.saved_frames = state.frames

    def _resume(self, save: saves.Save) -> None:
        """A visitor who's been before: their body and results back, and straight to the theory map."""
        self.visitor = self.activity.visitor = save.visitor
        for code in self.results:
            self.results[code] = list(save.results.get(code, []))
        self.frontier_shown = save.frontier_shown
        self.best = {code: pts for code, pts in save.best.items() if code in self.results}
        self.time_base = save.played - self.time      # so time_base + self.time carries on from where they were
        self.saved_frames = dict(save.frames)
        frames = saves.load_avatar(save)
        if frames:
            self.avatar = {anim: {1: right, -1: [pygame.transform.flip(img, True, False) for img in right]}
                           for anim, right in frames.items()}
        else:
            self._random_avatar()
        self.has_save = self.hold_exit = True
        self.tutorial = None
        self.activity("resume", confirmed=self.confirmed)
        self._go("hub")

    def _save_score(self) -> None:
        """Once per visit, and only for a visitor who signed in."""
        self._save_game()
        if self.signed_in and not self.score_saved:
            self.score_saved = True
            if self.record:
                scores.save(self.my_score())
            self.scores = scores.ranked([s for s in self.scores if s.visitor != self.visitor] + [self.my_score()])

    def _back_to_start(self, why: str) -> None:
        """Back to the PUSH ANY BUTTON TO BOOT UP screen for the next visitor, by way of the
        high scores if they signed in: the shell starts a fresh LifeSim when this
        one says it's done."""
        self.activity("idle_exit", why=why, phase=self.phase)
        self._save_score()
        if self.signed_in and self.phase != "scores":
            if self.phase == "files":
                self.term.media.stop()
            self._silence()
            self.countdown = None
            self.sim = None
            self._go("scores")
            return
        self._finish()

    def _silence(self) -> None:
        if pygame.mixer.get_init():              # unpause first so the next visitor's sound isn't stuck paused
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()
            pygame.mixer.stop()
            pygame.mixer.music.stop()

    def _finish(self) -> None:
        self.activity.close()
        atexit.unregister(self.activity.close)
        atexit.unregister(self._save_score)
        self._silence()
        self.countdown = None
        self.done = True

    def update(self, dt: float, inp: Input) -> None:
        if self.phase == "scores":              # the visit's over: HIGH SCORES, then the next visitor
            self.time += dt
            self.phase_t += dt
            if self.phase_t > SCORES_TIME or (inp.action and self.phase_t > 1.0):
                self._finish()
            return
        if self.idle_exit:
            if self._idle(dt, inp):
                return
            inp = self._menu_button(dt, inp)
            if inp is None or self._long_hold(dt, inp):
                return
        self.term.hold_k = self.hold_k
        self.time += dt
        self.phase_t += dt
        if self.phase == "off":
            target = 0.0
        elif self.phase in ("load", "dive") or self.phase == "files" and self.term.playing:
            target = REEL_FAST
        else:
            target = REEL_IDLE if int(self.time * 0.8) % 3 else 0.0   # tape drives move in fits
        self.reel_speed += (target - self.reel_speed) * min(1.0, dt * 4)
        for i in range(4):
            self.reel_angle[i] = (self.reel_angle[i] + self.reel_speed * dt * (1.0 + 0.15 * i)) % 360

        if self.phase == "sim":
            self.sim.update(dt, inp)
            if self.sim.done and self.sim_theory is self.splicer:
                self._take_body(self.sim)
            elif self.sim.done:
                res = self.sim.result or "?"
                code = self.sim_theory.code
                self.results[code].append(res)
                self.last_points = self.sim_theory.lab_points(int(getattr(self.sim, "score", 0) or 0))
                self.best[code] = max(self.best.get(code, 0), self.last_points)
                self.activity("theory_end", theory=code, result=res, secs=self._sim_secs(), points=self.last_points)
                self.last = (self.sim_theory, res)
                self.prev_sim, self.sim = self.sim, None
                self._save_game()
                if pygame.mixer.get_init():
                    pygame.mixer.fadeout(300)     # the womb rave leaves its lobby music on
                self._go("return")
            return

        if self.phase in ("load", "return", "frontier", "summon", "journey", "dnafact") or \
                self.phase == "spirit" and self.phase_t > SUMMON_FORM:
            self.typer.update(dt)

        if self.phase == "off":
            if inp.action and self.pushed is None and self.phase_t > 0.3:
                self.pushed = self.phase_t
            if self.pushed is not None and self.phase_t - self.pushed > BUTTON_PRESS:
                self._go("dive")
        elif self.phase == "dive":
            if self.phase_t > ENTER_TIME + 0.1:
                self._go("summon")
        elif self.phase == "rain":
            self.rain.update(dt)
            if self.phase_t > RAIN_TIME:
                self._go("cosmos")
        elif self.phase == "cosmos":
            if self.phase_t < RAIN_FADE:
                self.rain.update(dt)
            self.cosmos.update(dt)                      # (it plays through: no skipping the genesis program)
            if self.cosmos.done:
                self._go("spirit")
        elif self.phase == "summon":
            if self.entry:
                self.entry.update(dt, inp)
                if self.entry.done:
                    self.name = self.activity.name = self.entry.name
                    self.signed_in = True
                    save = saves.load(self.name) if self.entry.returning else None
                    if save:                            # they've been before: pick up where they left off
                        self._resume(save)
                    else:
                        if self.record:
                            sign_in(self.visitor, self.name)
                        self.activity("sign_in", returning=self.entry.returning)
                        self._go("journey")
            elif inp.action and not self.typer.done and self.phase_t > READ_GRACE:
                self.typer.finish()
            if not self.entry and self.typer.done and self.typer.t > self.typer.end + 0.3:
                self.entry = NameEntry(taken_names())
        elif self.phase == "journey":
            if self.phase_t > JOURNEY_TIME or inp.action and self.phase_t > READ_GRACE:
                self._go("rain")                    # the genesis program runs
        elif self.phase == "spirit":
            if inp.action and self.phase_t > max(SUMMON_FORM, READ_GRACE):
                if not self.typer.done:
                    self.typer.finish()
                else:
                    self._go("dnafact")
        elif self.phase == "dnafact":                   # WE KNOW LIFE STARTS WITH DNA.
            act = inp.action and self.phase_t > READ_GRACE
            if act and not self.typer.done:
                self.typer.finish()
            elif self.typer.done and (act or self.typer.t > self.typer.end + DNA_HOLD):
                self._start_splicer()
        elif self.phase == "hub" and self.tutorial is not None:
            self._tutorial(dt, inp)
        elif self.phase == "hub":
            self._walk(dt, inp)
            if inp.action and self.phase_t > 0.2 and not self.map.moving:
                if self.sel == FILES:
                    self.term.open()
                    self.activity("files_open")
                    self._go("files")
                elif self.sel == EXIT:
                    self._open_prompt("exit_tile")
                else:
                    self._go("load")
        elif self.phase == "files":
            self.term.update(dt, inp)
            if self.term.closed:
                self.activity("files_close")
                self._go("hub")
        elif self.phase == "load":
            if self.phase_t > LOAD_TIME + CRT_OFF_TIME + 0.2:
                self.sim_theory = self.theories[self.sel]
                self.activity("theory_start", theory=self.sim_theory.code)
                self.sim_started = self.time
                prev = self.prev_sim if self.replay and self.prev_sim is not None else None
                self.sim = self.sim_theory.make(prev) if prev is not None else self.sim_theory.make()
                self.prev_sim, self.replay = None, False
                self._go("sim")
        elif self.phase == "return":
            y = inp.y or inp.x or next((p.y or p.x for p in inp.players if p.y or p.x), 0)
            if self.typer.done and y and not self.return_y:   # the stick: PLAY AGAIN or EXPLORE OTHER THEORIES
                self.return_sel = max(0, min(len(RETURN_OPTIONS) - 1, self.return_sel + y))
            self.return_y = y
            if not self.typer.done:                     # a tap finishes the typing
                if inp.action and self.phase_t > READ_GRACE:
                    self.typer.finish()
            elif not self.return_armed:                 # then the choice is a hold, started fresh
                self.return_armed = not inp.held
            elif inp.held and self.phase_t > READ_GRACE:
                self.return_press = (self.return_press or 0.0) + dt
                if self.return_press >= SELECT_HOLD:
                    self.return_press = None
                    self.swallow = True                 # (that hold isn't for what comes next)
                    self._after_return(RETURN_OPTIONS[self.return_sel])
            else:
                self.return_press = None
        elif self.phase == "frontier":                  # CONGRATULATIONS! ... XXX IS THE ANSWER.
            if inp.action and self.phase_t > READ_GRACE:
                if not self.typer.done:
                    self.typer.finish()
                else:
                    if self.last:
                        self.map.place(self.theories.index(self.last[0]))
                    self._go("hub")

    def _after_return(self, option: str) -> None:
        """Off the verdict screen: the same simulation again, or back to the map (by way of
        CONGRATULATIONS! the first time every theory's been tested)."""
        self.activity("return_choice", option=option, theory=self.last[0].code)
        self.map.place(self.theories.index(self.last[0]))
        if option == "PLAY AGAIN":
            self.replay = True                  # same simulation, no how-to this time
            self._go("load")
        elif all(self.results.values()) and not self.frontier_shown:   # every theory tested
            self.prev_sim = None
            self.frontier_shown = True
            self._save_game()
            self.activity("frontier")
            self._go("frontier")
        else:
            self.prev_sim = None
            self._go("hub")

    # -- drawing -----------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        if self.phase == "scores":
            self._draw_scores(screen)
            return
        if self.phase == "sim":
            self.sim.draw(screen)
        elif self.phase == "cosmos":
            self.cosmos.draw(screen)
            if self.phase_t < RAIN_FADE:                  # the code rain clears off the start of the program
                self._draw_rain_fullscreen(screen, 1 - self.phase_t / RAIN_FADE)
        elif self.phase == "summon":
            self._draw_sign_in(screen)
        elif self.phase == "journey":
            self._draw_journey(screen)
        elif self.phase == "spirit":
            self._draw_spirit_formed(screen)
        elif self.phase == "dnafact":
            screen.fill(VOID)
            self._centre_lines(screen, self.typer, 66, 22, scale=2)
            screen.blit(self.art.scanlines, (0, 0))
        elif self.phase == "files":                       # the file system takes the whole screen
            self.term.draw(screen, self.text, self.time)
        elif self.phase == "hub":
            self._draw_map(screen)
        elif self.phase == "load":
            self._draw_load(screen)
        elif self.phase == "return":
            self._draw_return(screen)
        elif self.phase == "frontier":
            self._draw_frontier(screen)
        elif self.phase == "rain":
            self._draw_genesis(screen)
        elif self.phase == "dive":
            k = min(1.0, self.phase_t / ENTER_TIME)
            k = k * k                                       # accelerate into the glass
            if k <= 0:
                self._draw_room(screen)
            else:
                self._draw_room(self.frame)
                self._camera(screen, k)
        else:
            self._draw_room(screen)
        if self.countdown is not None:
            self._draw_countdown(screen)
        elif self.idle_exit:
            self._draw_long_hold(screen)

    def _draw_countdown(self, screen: pygame.Surface) -> None:
        """The exit menu over whatever was on screen, frozen and dimmed."""
        screen.fill((90, 90, 90), special_flags=pygame.BLEND_MULT)
        opts = self.menu_options()
        cx = art.W // 2
        pw, ph = 252, 68 + 14 * len(opts)
        px, py = cx - pw // 2, art.H // 2 - ph // 2
        screen.fill(rgb(CRT_BG), (px, py, pw, ph))
        pygame.draw.rect(screen, rgb(PHOSPHOR), (px, py, pw, ph), 1)
        pygame.draw.rect(screen, rgb(PHOSPHOR_FAINT), (px + 2, py + 2, pw - 4, ph - 4), 1)

        def centre(s: pygame.Surface, y: int) -> None:
            screen.blit(s, (cx - s.get_width() // 2, y))

        centre(self.text.get("STILL THERE?" if self.prompt_via == "idle" else "EXIT MENU", PHOSPHOR, 2, big=True), py + 6)
        # the options: the picked one on a lit bar, filling brighter while the button's held
        bw = pw - 24
        y = py + 28
        for i, opt in enumerate(opts):
            row = pygame.Rect(px + 12, y, bw, 12)
            if i == self.menu_sel:
                screen.fill(rgb(PHOSPHOR_DIM), row)
                if self.hold is not None:
                    screen.fill(rgb(PHOSPHOR), (row.x, row.y, int(bw * min(1.0, self.hold / SELECT_HOLD)), row.h))
                s = self.text.get(opt, CRT_BG, big=True)
            else:
                s = self.text.get(opt, PHOSPHOR, big=True)
            centre(s, y + 3)
            y += 14
        # the seconds drain away along a bar
        left = max(0, math.ceil(self.countdown))
        y += 4
        screen.fill(rgb(PHOSPHOR_FAINT), (px + 12, y, bw, 2))
        screen.fill(rgb(PHOSPHOR), (px + 12, y, int(bw * self.countdown / IDLE_COUNTDOWN), 2))
        centre(self.text.get(f"BACK TO THE START SCREEN IN {left}", PHOSPHOR), y + 5)
        centre(self.text.get("STICK: CHOOSE   HOLD BUTTON DOWN: SELECT", PROMPT, big=True), y + 14)

    def overlay(self, window: pygame.Surface) -> None:
        """Called by the shell after scaling, on the real window: the rick roll plays here, at full res."""
        if self.phase == "files" and self.countdown is None:
            self.term.overlay(window)

    def _camera(self, screen: pygame.Surface, k: float) -> None:
        """Zoom the room picture toward the CRT glass: k=0 is the whole room, k=1 fills the screen with DIVE."""
        dx, dy, dw, dh = DIVE
        w = art.W * (dw / art.W) ** k
        h = w * art.H / art.W
        t = (art.W - w) / (art.W - dw)                      # 0..1 in step with the size
        cx = art.W / 2 + (dx + dw / 2 - art.W / 2) * t
        cy = art.H / 2 + (dy + dh / 2 - art.H / 2) * t
        rect = pygame.Rect(round(cx - w / 2), round(cy - h / 2), max(1, round(w)), max(1, round(h)))
        rect = rect.clip(self.frame.get_rect())
        pygame.transform.scale(self.frame.subsurface(rect), screen.get_size(), screen)

    def _draw_rain_fullscreen(self, screen: pygame.Surface, k: float) -> None:
        layer = pygame.Surface(SCREEN[2:])
        self.rain.draw(layer)
        dx, dy, dw, dh = DIVE
        big = pygame.transform.scale(layer.subsurface((0, dy - SCREEN[1], dw, dh)), screen.get_size())
        v = int(255 * k)
        big.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        screen.blit(big, (0, 0), special_flags=pygame.BLEND_ADD)

    def _draw_genesis(self, screen: pygame.Surface) -> None:
        """The genesis program starting up: code rain over the whole screen."""
        screen.fill((0, 0, 0))
        self._draw_rain_fullscreen(screen, 1.0)
        if self.phase_t > 0.3:
            s = self.text.get("RUNNING PROGRAM: GENESIS", PHOSPHOR, big=True)
            box = s.get_rect(center=(art.W // 2, art.H // 2)).inflate(16, 10)
            screen.fill(rgb(CRT_BG), box)
            pygame.draw.rect(screen, rgb(PHOSPHOR), box, 1)
            screen.blit(s, (box.x + 8, box.y + 5))
        screen.blit(self.art.scanlines, (0, 0))

    def _header(self, screen: pygame.Surface, right: str) -> None:
        screen.blit(self.text.get("LIFE LAB MAINFRAME", PHOSPHOR, big=True), (4, 3))
        s = self.text.get(right, PHOSPHOR, big=True)
        screen.blit(s, (art.W - 4 - s.get_width(), 3))
        screen.fill(rgb(PHOSPHOR_DIM), (4, 13, art.W - 8, 1))

    def _centre_lines(self, screen: pygame.Surface, typer: Typer, y: int, step: int, scale: int = 1) -> None:
        """Typed lines, each centred on where its whole line will end up."""
        for i, line in enumerate(typer.visible()):
            if line:
                full = typer.lines[i]
                x = art.W // 2 - big_width(full) * scale // 2
                screen.blit(self.text.get(line, PHOSPHOR, scale, big=True), (x, y + i * step))

    def _draw_sign_in(self, screen: pygame.Surface) -> None:
        """The welcome, then WHAT SHOULD WE CALL YOU? and the name entry."""
        self._draw_void(screen)
        self._header(screen, "PROGRAM: RESEARCH EXPLORATION")
        self._centre_lines(screen, self.typer, 26, 11)
        if self.entry:
            self._draw_name_entry(screen, art.W / 2, 101)
        screen.blit(self.art.scanlines, (0, 0))

    def _draw_name_entry(self, screen: pygame.Surface, cx: float, top: int) -> None:
        """Four big letter slots with the cursor on one (arrows above and below: up and
        down roll it; either side: left and right move it), the controls underneath."""
        e = self.entry
        slot_w, gap = 18, 8
        x0 = int(cx - (NAME_LEN * slot_w + (NAME_LEN - 1) * gap) / 2)
        bob = int(self.time * 4) % 2                     # the arrows nudge in and out
        hi = rgb(PHOSPHOR)
        for i in range(NAME_LEN):
            x = x0 + i * (slot_w + gap)
            here = i == e.pos and e.ask is None
            ch = e.slots[i]
            if ch != " ":
                img = self.text.get(ch, PHOSPHOR, 2, big=True)
                screen.blit(img, (x + (slot_w - img.get_width()) // 2, top + (14 - img.get_height()) // 2))
            screen.fill(rgb(PHOSPHOR if here else PHOSPHOR_DIM), (x, top + 17, slot_w, 1 + here))
            if here:
                mx, my = x + slot_w // 2, top + 7
                for k in range(4):
                    screen.fill(hi, (mx - k, top - 7 - bob + k, 2 * k + 1, 1))      # up / down: the letter
                    screen.fill(hi, (mx - k, top + 25 + bob - k, 2 * k + 1, 1))
                    if i > 0:                                                    # left / right: the cursor
                        screen.fill(hi, (x - 7 - bob + k, my - k, 1, 2 * k + 1))
                    if i < NAME_LEN - 1:
                        screen.fill(hi, (x + slot_w + 6 + bob - k, my - k, 1, 2 * k + 1))

        def hold_bar(s: pygame.Surface, x: float, y: int) -> None:
            if e.hold_k > 0:                               # holding: a bar fills up to done
                screen.fill(rgb(PHOSPHOR_FAINT), (x, y + 9, s.get_width(), 2))
                screen.fill(rgb("#eaffea"), (x, y + 9, int(s.get_width() * e.hold_k), 2))

        if e.ask is not None:                              # a taken name: is it theirs?
            q = self.text.get(f"{e.ask} IS TAKEN. HAVE YOU PLAYED HERE BEFORE?", PHOSPHOR, big=True)
            screen.blit(q, (cx - q.get_width() // 2, top + 34))
            for i, opt in enumerate(("YES", "NO")):
                row = pygame.Rect(int(cx) - 54 + i * 60, top + 47, 48, 12)
                if i == e.ask_sel:
                    screen.fill(rgb(PHOSPHOR), row)
                    s = self.text.get(opt, CRT_BG, big=True)
                else:
                    pygame.draw.rect(screen, rgb(PHOSPHOR_DIM), row, 1)
                    s = self.text.get(opt, PHOSPHOR, big=True)
                screen.blit(s, (row.centerx - s.get_width() // 2, row.y + 3))
            h = self.text.get("STICK: CHOOSE    HOLD BUTTON DOWN: SELECT", PROMPT, big=True)
            hx = cx - h.get_width() // 2
            screen.blit(h, (hx, top + 64))
            hold_bar(h, hx, top + 64)
            return
        lines = ["STICK UP / DOWN: CHANGE THE LETTER", "STICK LEFT / RIGHT: MOVE",
                 "HOLD BUTTON DOWN: DONE"]
        if e.taken_t > 0:                                  # that name's someone else's
            lines[0] = "NAME TAKEN! CHOOSE A UNIQUE NAME"
        for i, line in enumerate(lines):
            s = self.text.get(line, PHOSPHOR if i == 0 and e.taken_t > 0 else PROMPT, big=True)
            x, y = cx - s.get_width() // 2, top + 38 + i * 10
            screen.blit(s, (x, y))
            if i == 2:
                hold_bar(s, x, y)

    def _draw_journey(self, screen: pygame.Surface) -> None:
        """OUR JOURNEY STARTS AT THE VERY BEGINNING..., big, then a fade to the genesis program."""
        screen.fill(VOID)
        self._centre_lines(screen, self.typer, 62, 22, scale=2)
        k = (self.phase_t - (JOURNEY_TIME - 0.6)) / 0.6
        if k > 0:
            v = int(255 * max(0.0, 1 - k))
            screen.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        screen.blit(self.art.scanlines, (0, 0))

    def _draw_spirit_formed(self, screen: pygame.Surface) -> None:
        """Wisps from everywhere come together into the spirit, which dances. YOU ARE A SPIRIT!"""
        self._draw_void(screen)
        cx, cy = art.W / 2, 50
        k = min(1.0, self.phase_t / SUMMON_FORM)
        for mx, my, speed in self.motes:
            p = min(1.0, k * (0.5 + speed * 0.7))
            if p < 1:
                x, y = cx + mx * (1 - p), cy + my * (1 - p)
                col = art.SPIRIT_BODY if speed > 0.75 else art.SPIRIT_EDGE
                screen.fill(rgb(col), (int(x), int(y), 1 + (speed > 0.9), 1))
        if k > 0.6:
            grow = min(1.0, (k - 0.6) / 0.4)
            self._draw_dance(screen, cx, cy, 3.0 * grow, self.phase_t - SUMMON_FORM)
        self._centre_lines(screen, self.typer, 94, 19, scale=2)
        if self.typer.done:                                  # (it flashes colour, never off)
            s = self.text.get("TAP BUTTON", PROMPT, big=True)
            screen.blit(s, (art.W // 2 - s.get_width() // 2, 162))
        screen.blit(self.art.scanlines, (0, 0))

    def _draw_dance(self, screen: pygame.Surface, x: float, y: float, scale: float, t: float) -> None:
        """A little dance, four moves round and round on a beat: sway, hop, spin, sway back."""
        if scale <= 0.05:
            return
        beat = 0.5                                         # s per beat, 4 beats a move
        t = max(0.0, t)
        move, k = int(t / (beat * 4)) % 4, (t / (beat * 4)) % 1.0
        dx = dy = ang = 0.0
        sx = sy = 1.0
        if move in (0, 3):                                 # sway side to side, leaning in
            side = math.sin(k * math.tau * 2) * (1 if move == 0 else -1)
            dx, ang = side * 10, -side * 14
        elif move == 1:                                    # hop, hop: squash down, stretch up
            b = (k * 4) % 1.0
            dy = -abs(math.sin(b * math.pi)) * 14
            sy = 1.0 + 0.2 * math.sin(b * math.pi)
            sx = 2.0 - sy
        else:                                              # a twirl: turn round twice
            sx = math.cos(k * math.tau * 2)
        f = int(self.time * 8) % (art.SPIRIT_FRAMES - 1)
        img = self.art.spirit[f]
        w, h = img.get_size()
        img = pygame.transform.scale(img, (max(1, round(w * scale * abs(sx))), max(1, round(h * scale * sy))))
        if sx < 0:
            img = pygame.transform.flip(img, True, False)
        if ang:
            img = pygame.transform.rotate(img, ang)
        glow = pygame.transform.scale_by(self.art.glow, scale)
        px, py = x + dx, y + dy + math.sin(self.time * 3) * 1.5
        screen.blit(glow, (px - glow.get_width() / 2, py - glow.get_height() / 2), special_flags=pygame.BLEND_ADD)
        screen.blit(img, (px - img.get_width() / 2, py - img.get_height() / 2))

    # -- the theory map, and going in and out of a simulation ---------------------------
    def _verdict(self, t: Theory) -> str:
        runs = self.results[t.code]
        if "win" in runs:
            return VERDICT["win"]
        return VERDICT.get(runs[-1], VERDICT["?"]) if runs else VERDICT[None]

    def _draw_void(self, screen: pygame.Surface) -> None:
        screen.fill(VOID)
        for x, y, b in self.void_stars:
            screen.fill((b, b, b + 20), (x, y, 1, 1))

    def _draw_map(self, screen: pygame.Surface, info: bool = True) -> None:
        m, sw = self.map, art.W
        self._draw_void(screen)
        for i, t in enumerate(self.theories):
            m.draw_tile(screen, i, self.time, lit=i == self.sel and not m.moving)
            x, y = tile_at(i)
            v = self._verdict(t)
            col = PHOSPHOR if v == VERDICT["win"] else PHOSPHOR_DIM if self.results[t.code] else PHOSPHOR_FAINT
            s = self.text.get(t.game, col)
            screen.blit(s, (x + TILE_W // 2 - s.get_width() // 2, y + TILE_H + 3))
        slots = worldmap.FILES_SLOT + 1                  # the theories, then SYSTEM FILES
        for i in range(slots, -(-slots // COLS) * COLS):
            m.draw_empty(screen, i)
        m.draw_files(screen, self.time, lit=self.sel == FILES and not m.moving)
        fr = tile_rect(FILES)
        s = self.text.get("SYSTEM FILES", PHOSPHOR if self.sel == FILES else PHOSPHOR_FAINT)
        screen.blit(s, (fr.centerx - s.get_width() // 2, fr.bottom + 3))
        m.draw_exit(screen, self.time, lit=self.sel == EXIT and not m.moving)
        s = self.text.get("EXIT", PHOSPHOR if self.sel == EXIT else PHOSPHOR_DIM, big=True)
        screen.blit(s, (EXIT_RECT.centerx - s.get_width() // 2, EXIT_RECT.top + 61))
        self._header(screen, f"VISITOR {self.visitor:04d} {self.name}")
        if info and not m.moving and self.tutorial is None:
            if self.sel == FILES:
                title, blurb, tag = "SYSTEM FILES", FILES_BLURB, "C:\\> FILES"
            elif self.sel == EXIT:
                title, blurb, tag = "EXIT", EXIT_BLURB, ""
            else:
                t = self.theories[self.sel]
                tag = ("2 PLAYERS   " if t.players == "2P" else "") + f"{self._verdict(t)}   TAPE {t.code}"
                title, blurb = t.name, t.blurb
            screen.blit(self.text.get(title, PHOSPHOR, big=True), (6, 139))
            s = self.text.get(tag, PHOSPHOR_DIM)
            screen.blit(s, (sw - 6 - s.get_width(), 140))
            for i, line in enumerate(blurb):
                screen.blit(self.text.get(line, PHOSPHOR), (6, 149 + i * 7))
        # the controls
        screen.fill(rgb(PHOSPHOR_FAINT), (4, 164, sw - 8, 1))
        screen.blit(self.text.get("STICK: MOVE    TAP BUTTON: ENTER", PROMPT, big=True), (6, 168))
        if self.idle_exit:
            hold = self.text.get("HOLD BUTTON: EXIT", PROMPT, big=True)
            hx = sw - 6 - hold.get_width()
            screen.blit(hold, (hx, 168))
            if self.hold_k > 0:
                screen.fill(rgb("#eaffea"), (hx, 176, int(hold.get_width() * self.hold_k), 2))
        if self.phase == "hub" and self.tutorial is not None:
            self._draw_tutorial(screen)
        if self.phase == "hub":
            x, y = m.pos
            self._draw_body(screen, x, y + AVATAR_FEET, "walk" if m.moving else "idle")
        for i, t in enumerate(self.theories):            # played: CONFIRMED or REFUTED stamped over the preview
            if self.results[t.code]:                     # (on top of the body, so it's never hidden)
                v = self._verdict(t)
                self._stamp(screen, tile_at(i)[0] + TILE_W // 2, tile_at(i)[1] + 4, v, lit=v == VERDICT["win"])
        k = min(1.0, self.phase_t / MAP_FADE) if self.phase == "hub" and self.tutorial == 0 else 1.0
        if k < 1:                                        # fading in from the void
            v = int(255 * k)
            screen.fill((v, v, v), special_flags=pygame.BLEND_MULT)

    def _stamp(self, screen: pygame.Surface, cx: int, top: int, word: str, lit: bool) -> None:
        """A verdict across the top of a tile: lit for CONFIRMED, dark with a frame for the rest."""
        s = self.text.get(word, CRT_BG if lit else PHOSPHOR, big=True)
        box = pygame.Rect(0, top, s.get_width() + 6, 11)
        box.centerx = cx
        screen.fill(rgb(PHOSPHOR if lit else CRT_BG), box)
        pygame.draw.rect(screen, rgb(CRT_BG if lit else PHOSPHOR), box, 1)
        screen.blit(s, (box.x + 3, box.y + 2))

    # -- the tour of the map ------------------------------------------------------------
    def _walk(self, dt: float, inp: Input) -> None:
        """Move on the map, turning the body to face where it's going."""
        self.map.update(dt, inp)
        if self.map.target is not None:
            dx = tile_rect(self.map.target).centerx - self.map.pos[0]
            self.facing = 1 if dx > 0 else -1 if dx < 0 else self.facing

    def _start_splicer(self) -> None:
        """Off to get a body: spit in the jar."""
        self.sim_theory = self.splicer
        self.activity("theory_start", theory=self.splicer.code)
        self.sim_started = self.time
        self.sim = self.splicer.make()
        self._go("sim")

    def _take_body(self, kit) -> None:
        """Spit Kit's done: keep the creature it spliced to walk the
        map, and on to the map, with the tour."""
        self.activity("theory_end", theory=self.splicer.code, result=kit.result or "?", secs=self._sim_secs())
        canvases = getattr(kit, "_canvases", None)
        if canvases:
            self._set_avatar(canvases["final"])
        self.sim = None
        self.has_save = True                    # from here on there's a game to come back to
        self._save_game(canvases["final"] if canvases else None)
        self.tutorial = 0                       # first time on the map: show them round it
        self.tour_t, self.tour_press, self.tour_armed = 0.0, None, False
        self.hold_exit = True                   # from here on, holding the button anywhere exits
        self._go("hub")

    def _set_avatar(self, frames: dict) -> None:
        """The body that walks the map, from its canvases (anim -> frames, facing right)."""
        self.avatar = {}
        for anim, canvases in frames.items():
            right = [to_surface(f) for f in canvases]
            self.avatar[anim] = {1: right, -1: [pygame.transform.flip(img, True, False) for img in right]}

    def _random_avatar(self) -> None:
        """--skip-boot misses Spit Kit, so splice them a body at random instead."""
        from minigames.spit_kit import dna
        from sprites.characters import from_specimen
        rng = random.Random(self.rng.random())
        you = dna.build_you(dna.roll_profile(rng), rng, number=rng.randrange(1000, 9999))
        self._set_avatar(from_specimen(you.final).all_frames())

    def _draw_body(self, screen: pygame.Surface, x: float, feet: float, anim: str, scale: float = 1.0) -> None:
        """Their spliced body standing on (x, feet), or the spirit if there isn't one yet."""
        if not self.avatar:
            self._draw_spirit(screen, x, feet - AVATAR_FEET, scale)
            return
        frames = self.avatar.get(anim, self.avatar["idle"])[self.facing]
        img = frames[int(self.time * 8) % len(frames)]
        if scale != 1.0:
            img = pygame.transform.scale_by(img, scale)
        px, py = round(x - img.get_width() / 2), round(feet - img.get_height())
        ink = pygame.mask.from_surface(img).to_surface(setcolor=(8, 6, 16, 255), unsetcolor=(0, 0, 0, 0))
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):     # a dark outline, so it reads over the busy tiles
            screen.blit(ink, (px + ox, py + oy))
        screen.blit(img, (px, py))

    def _tutorial(self, dt: float, inp: Input) -> None:
        """The INSTRUCTIONS screen: once it's been up TOUR_SHOW, holding the button for
        TOUR_HOLD goes on to the map. A tap does nothing; a button already down when it
        came up has to be let go first."""
        self.tour_t += dt
        if not self.tour_armed:
            self.tour_armed = not inp.held
            return
        if not inp.held or self.tour_t < TOUR_SHOW:
            self.tour_press = None
            return
        self.tour_press = (self.tour_press or 0.0) + dt
        if self.tour_press >= TOUR_HOLD:
            self.tutorial = None
            self.tour_press = None
            self.swallow = True                            # (that hold isn't for the map)
            self.activity("tutorial_done")

    def _draw_tutorial(self, screen: pygame.Surface) -> None:
        """INSTRUCTIONS across the top, the map dimmed, the controls line along the bottom
        left lit with an arrow pointing down at each control, and once a hold would work,
        HOLD BUTTON TO CONTINUE in the middle."""
        foot = pygame.Rect(0, 164, art.W, art.H - 164)
        lit = screen.subsurface(foot).copy()
        screen.fill((60, 60, 60), special_flags=pygame.BLEND_MULT)
        screen.blit(lit, foot)
        screen.fill(VOID, (0, 0, art.W, 17))
        title = self.text.get("INSTRUCTIONS", PROMPT, 2, big=True)
        screen.blit(title, (art.W // 2 - title.get_width() // 2, 2))
        # an arrow over each control on the line below
        col = rgb(PROMPT)
        targets = [6 + big_width("STICK: MOVE") // 2,
                   6 + big_width("STICK: MOVE    ") + big_width("TAP BUTTON: ENTER") // 2]
        if self.idle_exit:
            targets.append(art.W - 6 - big_width("HOLD BUTTON: EXIT") // 2)
        bob = round(2 * math.sin(self.time * 6))
        for x in targets:
            tip = 163 + bob
            screen.fill(col, (x - 1, tip - 30, 3, 24))                     # the shaft
            for k in range(7):                                             # the head
                screen.fill(col, (x - k, tip - k, 2 * k + 1, 1))
        if self.tour_t >= TOUR_SHOW:                       # once a hold would work: big, flashing colour
            s = self.text.get("HOLD BUTTON TO CONTINUE", PROMPT, 2, big=True)
            box = s.get_rect(center=(art.W // 2, 80)).inflate(16, 18)
            screen.fill(rgb(CRT_BG), box)
            pygame.draw.rect(screen, col, box, 1)
            screen.blit(s, (box.x + 8, box.y + 6))
            if self.tour_press:                            # holding: a bar fills up to the map
                k = min(1.0, self.tour_press / TOUR_HOLD)
                screen.fill(rgb(PHOSPHOR_FAINT), (box.x + 8, box.bottom - 6, s.get_width(), 2))
                screen.fill(rgb("#eaffea"), (box.x + 8, box.bottom - 6, int(s.get_width() * k), 2))

    def _draw_load(self, screen: pygame.Surface) -> None:
        """The body dives into the tile, the tile grows to fill the screen, then it switches off."""
        self._draw_map(screen, info=False)
        tx, ty = tile_at(self.sel)
        cx, cy = tx + TILE_W / 2, ty + TILE_H / 2
        k = min(1.0, self.phase_t / LOAD_DIVE)
        if k < 1:                                        # spiral in, shrinking away
            ang, r = k * 3 * math.tau, 14 * (1 - k)
            self._draw_body(screen, cx + math.cos(ang) * r, cy + AVATAR_FEET * (1 - k) + math.sin(ang) * r * 0.6,
                            "jump", 1.0 - k)
        g = max(0.0, min(1.0, (self.phase_t - LOAD_DIVE) / (LOAD_TIME - LOAD_DIVE - 0.4)))
        g = g * g * (3 - 2 * g)
        if g > 0:
            frames = self.map.previews[self.sel]
            img = frames[int(self.time * 6) % len(frames)]
            w, h = TILE_W + (art.W - TILE_W) * g, TILE_H + (art.H - TILE_H) * g
            x, y = tx + (0 - tx) * g, ty + (0 - ty) * g
            screen.blit(pygame.transform.scale(img, (round(w), round(h))), (round(x), round(y)))
        # what's happening, in a band across the middle
        band = pygame.Rect(0, art.H // 2 - 14, art.W, 28)
        screen.fill(rgb(CRT_BG), band)
        screen.fill(rgb(PHOSPHOR_DIM), (0, band.top, art.W, 1))
        screen.fill(rgb(PHOSPHOR_DIM), (0, band.bottom - 1, art.W, 1))
        for i, line in enumerate(self.typer.visible()):
            if line:
                screen.blit(self.text.get(line, PHOSPHOR, big=True), (8, band.top + 4 + i * 10))
        bar = int((art.W - 16) * min(1.0, self.phase_t / LOAD_TIME))
        screen.fill(rgb(PHOSPHOR_FAINT), (8, band.bottom + 4, art.W - 16, 3))
        screen.fill(rgb(PHOSPHOR), (8, band.bottom + 4, bar, 3))
        if self.phase_t > LOAD_TIME:
            self._squash(screen, min(1.0, (self.phase_t - LOAD_TIME) / CRT_OFF_TIME))

    def _draw_return(self, screen: pygame.Surface) -> None:
        """Back in the program after a simulation: the verdict."""
        self._draw_void(screen)
        screen.blit(self.text.get("LIFE LAB MAINFRAME", PHOSPHOR, big=True), (4, 3))
        s = self.text.get("PROGRAM: RESEARCH EXPLORATION", PHOSPHOR, big=True)
        screen.blit(s, (art.W - 4 - s.get_width(), 3))
        screen.fill(rgb(PHOSPHOR_DIM), (4, 13, art.W - 8, 1))
        for i, line in enumerate(self.typer.visible()):
            if line:
                screen.blit(self.text.get(line, PHOSPHOR, big=True), (12, 24 + i * 11))
        if self.typer.done:
            bw, x = 150, 12
            for i, opt in enumerate(RETURN_OPTIONS):       # PLAY AGAIN / EXPLORE OTHER THEORIES
                row = pygame.Rect(x, 120 + i * 14, bw, 12)
                if i == self.return_sel:
                    screen.fill(rgb(PHOSPHOR_DIM), row)
                    if self.return_press:                  # holding: the bar fills up to taking it
                        screen.fill(rgb(PHOSPHOR), (row.x, row.y, int(bw * min(1.0, self.return_press / SELECT_HOLD)), row.h))
                    s = self.text.get(opt, CRT_BG, big=True)
                else:
                    pygame.draw.rect(screen, rgb(PHOSPHOR_DIM), row, 1)
                    s = self.text.get(opt, PHOSPHOR, big=True)
                screen.blit(s, (row.centerx - s.get_width() // 2, row.y + 3))
            s = self.text.get("STICK: CHOOSE   HOLD BUTTON: SELECT", PROMPT, big=True)   # (clear of the body)
            screen.blit(s, (x, 151))
            self._draw_body(screen, art.W - 40, 172, "idle", 2.0)
        if self.phase_t < CRT_ON_TIME:
            self._squash(screen, 1.0 - self.phase_t / CRT_ON_TIME)

    def _draw_frontier(self, screen: pygame.Surface) -> None:
        """Every theory tested: CONGRATULATIONS!, big, then the hint about XXX."""
        self._draw_void(screen)
        self._header(screen, "PROGRAM: RESEARCH EXPLORATION")
        for i, line in enumerate(self.typer.visible()):
            if line:
                scale = 2 if i == 0 else 1
                x = art.W // 2 - big_width(self.typer.lines[i]) * scale // 2
                screen.blit(self.text.get(line, PHOSPHOR, scale, big=True), (x, 22 if i == 0 else 30 + i * 11))
        if self.typer.done:                                  # (it flashes colour, never off)
            s = self.text.get("TAP BUTTON", PROMPT, big=True)
            screen.blit(s, (art.W // 2 - s.get_width() // 2, 162))
        screen.blit(self.art.scanlines, (0, 0))

    def _squash(self, screen: pygame.Surface, k: float) -> None:
        """An old tube switching off: k=0 is the picture, then a bright line, then a dot, then dark at 1."""
        w, h = screen.get_size()
        if k <= 0:
            return
        pic = screen.copy()
        screen.fill((0, 0, 0))
        if k < 0.6:
            lh = max(1, int(h * (1 - k / 0.6)))
            line = pygame.transform.scale(pic, (w, lh))
            line.fill((90, 140, 90), special_flags=pygame.BLEND_ADD)
            screen.blit(line, (0, (h - lh) // 2))
        elif k < 1.0:
            lw = max(2, int(w * (1 - (k - 0.6) / 0.4)))
            screen.fill((220, 255, 220), ((w - lw) // 2, h // 2, lw, 1))

    def _draw_room(self, screen: pygame.Surface) -> None:
        a = self.art
        screen.blit(a.room, (0, 0))
        for (cx, cy), ang in zip(art.reel_centers(), self.reel_angle):
            f = int(ang / 120 * art.REEL_FRAMES) % art.REEL_FRAMES
            screen.blit(a.reels[f], (cx - art.REEL_R, cy - art.REEL_R))
        for i, (sx, sy, sw, sh) in enumerate(art.column_slots()):
            loop = sy + sh // 2 + int(math.sin(self.time * 3 + i * 1.7 + self.reel_angle[i] / 40) * (sh // 2 - 3))
            pygame.draw.line(screen, rgb(art.TAPE), (sx + 1, sy), (sx + 1, loop))
            pygame.draw.line(screen, rgb(art.TAPE), (sx + sw - 2, sy), (sx + sw - 2, loop))
            pygame.draw.arc(screen, rgb(art.TAPE), (sx + 1, loop - 3, sw - 2, 7), math.pi, math.tau)
        rate = 18 if self.phase == "dive" else 4
        tick = int(self.time * rate)
        for i, (lx, ly) in enumerate(art.drive_lamps() + art.console_lamps()):
            h = (i * 2654435761 + tick * 40503 + (i % 5) * tick) & 0xFFFF
            if self.phase == "off" and self.pushed is None:
                on = i == 16 and int(self.time * 1.5) % 2 == 0      # just the power lamp, waiting
            else:
                on = h % 7 < 3
            col = art.LAMP_ON[(i // 4) % len(art.LAMP_ON)] if on else art.LAMP_OFF
            screen.fill(rgb(col), (lx, ly, 3, 3))
        self._draw_crt(screen)

    def _draw_crt(self, screen: pygame.Surface) -> None:
        a, crt = self.art, self.crt
        sx, sy = SCREEN[:2]
        crt.fill(rgb(CRT_BG))
        getattr(self, f"_crt_{self.phase}")(crt)
        # no bloom, flicker or scanlines: crisp text reads best at this size
        crt.blit(a.vignette, (0, 0))
        screen.blit(crt, (sx, sy))

    # each phase paints the CRT surface (coordinates are inside the glass)
    def _draw_spirit(self, crt: pygame.Surface, x: float, y: float, scale: float) -> None:
        if scale <= 0.05:
            return
        f = int(self.time * 8) % art.SPIRIT_FRAMES
        if int(self.time * 0.5 + 0.3) % 4 == 0 and f == art.SPIRIT_FRAMES - 1:
            pass                                                   # blink now and then
        elif f == art.SPIRIT_FRAMES - 1:
            f = 0
        bob = math.sin(self.time * 3) * 1.5
        img = self.art.spirit[f]
        if scale != 1.0:
            img = pygame.transform.scale_by(img, scale)
        glow = pygame.transform.scale_by(self.art.glow, scale)
        crt.blit(glow, (x - glow.get_width() / 2, y + bob - glow.get_height() / 2), special_flags=pygame.BLEND_ADD)
        crt.blit(img, (x - img.get_width() / 2, y + bob - img.get_height() / 2))

    def _crt_off(self, crt: pygame.Surface) -> None:
        if self.pushed is None and self.scores and self.phase_t % sum(ATTRACT) > ATTRACT[0]:
            self._crt_scores(crt)                   # nobody's pushed it yet: the high scores, now and then
            return
        sw = SCREEN[2]
        for word, y in (("LIFE LAB", 10), ("MAINFRAME", 29)):
            s = self.text.get(word, PHOSPHOR, 3)
            crt.blit(s, (sw // 2 - s.get_width() // 2, y))
        crt.fill(rgb(PHOSPHOR_DIM), (24, 50, sw - 48, 1))
        # the button: a chunky key with a lip, which sinks when pushed
        down = self.pushed is not None
        bw, bh = 124, 18
        bx, by = sw // 2 - bw // 2, 60 + (2 if down else 0)
        if not down:
            crt.fill(rgb(PHOSPHOR_DIM), (bx, by + 2, bw, bh))           # the lip under it
        pulse = int(self.time * 2) % 2 == 0
        crt.fill(rgb(PHOSPHOR if down or pulse else PHOSPHOR_DIM), (bx, by, bw, bh))
        crt.fill(rgb(PHOSPHOR_DIM if down else PHOSPHOR_FAINT), (bx + 1, by + 1, bw - 2, bh - 2))
        label = self.text.get("PUSH ANY BUTTON TO BOOT UP", "#eaffea" if down else PHOSPHOR)
        crt.blit(label, (sw // 2 - label.get_width() // 2, by + bh // 2 - 2))
        s = self.text.get("WELCOME TO THE LIFE LAB!", PHOSPHOR_DIM)
        crt.blit(s, (sw // 2 - s.get_width() // 2, 92))

    def _crt_scores(self, crt: pygame.Surface) -> None:
        """HIGH SCORES on the mainframe's own screen, small, for the start screen."""
        sw = SCREEN[2]
        s = self.text.get("HIGH SCORES", PHOSPHOR, big=True)
        crt.blit(s, (sw // 2 - s.get_width() // 2, 6))
        crt.fill(rgb(PHOSPHOR_DIM), (16, 16, sw - 32, 1))
        for i, sc in enumerate(self.scores[:8]):
            y = 21 + i * 9
            crt.blit(self.text.get(f"{i + 1}.", PHOSPHOR_DIM), (18, y))
            crt.blit(self.text.get(sc.name, PHOSPHOR), (32, y))
            r = self.text.get(f"{sc.explored}/{len(self.theories)}", PHOSPHOR)      # theories explored
            crt.blit(r, (sw - 62 - r.get_width(), y))
            t = self.text.get(f"{sc.points} PTS", PHOSPHOR_DIM)
            crt.blit(t, (sw - 18 - t.get_width(), y))
        if int(self.time * 2) % 2 == 0:
            s = self.text.get("PUSH ANY BUTTON TO BOOT UP", PHOSPHOR)
            crt.blit(s, (sw // 2 - s.get_width() // 2, 95))

    def _draw_scores(self, screen: pygame.Surface) -> None:
        """When a visit ends: HIGH SCORES, full screen, their own row lit up."""
        screen.fill(rgb(CRT_BG))
        self._header(screen, f"VISITOR {self.visitor:04d} {self.name}")
        mine = self.my_score()
        rank = next((i for i, sc in enumerate(self.scores) if sc.visitor == self.visitor), None)
        title = self.text.get("HIGH SCORES", PHOSPHOR, 2, big=True)
        screen.blit(title, (art.W // 2 - title.get_width() // 2, 19))
        cols = (70, 92, 160, 230)                            # rank, name, explored, points
        y = 40
        for label, x in zip(("", "NAME", "EXPLORED", "POINTS"), cols):
            screen.blit(self.text.get(label, PHOSPHOR_DIM), (x, y))
        shown = list(enumerate(self.scores[:SCORE_ROWS]))
        if rank is not None and rank >= SCORE_ROWS:          # not in the top: their row at the bottom
            shown[-1] = (rank, self.scores[rank])
        for row, (i, sc) in enumerate(shown):
            y = 50 + row * 10
            me = sc.visitor == self.visitor
            if me:
                screen.fill(rgb(PHOSPHOR_DIM if int(self.time * 3) % 3 else PHOSPHOR_FAINT), (64, y - 2, 214, 10))
            for text, x in ((f"{i + 1}.", cols[0]), (sc.name, cols[1]),
                            (f"{sc.explored} OF {len(self.theories)}", cols[2]),
                            (str(sc.points), cols[3])):
                screen.blit(self.text.get(text, PHOSPHOR, big=True), (x, y))
        msg = (f"YOU EXPLORED {mine.explored} OF {len(self.theories)} THEORIES: {mine.points} POINTS." if mine.explored
               else "NO THEORIES EXPLORED. THE LAB IS DISAPPOINTED.")
        s = self.text.get(msg, PHOSPHOR, big=True)
        screen.blit(s, (art.W // 2 - s.get_width() // 2, 158))
        if self.phase_t > 1.0 and int(self.time * 2) % 2 == 0:
            p = self.text.get("THANKS FOR VISITING THE LIFE LAB", PHOSPHOR_DIM)
            screen.blit(p, (art.W // 2 - p.get_width() // 2, 170))
        screen.blit(self.art.scanlines, (0, 0))

    def _crt_dive(self, crt: pygame.Surface) -> None:
        crt.fill(VOID)                              # the sign-in screen, before anything's on it


def autopilot(game: LifeSim) -> Input:
    """Boots up, then runs every simulation in turn with that mini-game's own
    autopilot. For demos and smoke tests."""
    if game.phase == "sim":
        return game.sim_theory.autopilot(game.sim)
    inp = Input()
    if game.phase == "hub" and game.tutorial is not None:
        inp.held = game.tour_t > TOUR_SHOW                   # hold, once it says to
        return inp
    if game.phase == "hub":
        untested = [i for i, t in enumerate(game.theories) if not game.results[t.code]]
        want = untested[0] if untested else int(game.time / 20) % len(game.theories)
        if want != game.sel or game.map.moving:
            return game.map.steer(want)
        inp.action = game.phase_t > 1.5
        return inp
    if game.phase == "summon" and game.entry and game.entry.ask is not None:
        game.entry.answer(False)                            # a demo never played before
        return inp
    if game.phase == "summon" and game.entry:
        # sign in as DEMO: roll each slot to its letter, move right, then hold the button
        e, want = game.entry, "DEMO"
        tick = int(game.time * 30) % 2                          # (the stick acts on each push)
        if e.slots[e.pos] != want[e.pos]:
            inp.y = tick
        elif e.pos < len(want) - 1:
            inp.x = tick
        else:
            inp.held = True
        return inp
    if game.phase == "return" and game.typer.done:
        if RETURN_OPTIONS[game.return_sel] != "EXPLORE OTHER THEORIES":
            inp.y = 1 if int(game.time * 30) % 2 else 0       # tap down to EXPLORE OTHER THEORIES
        else:
            inp.held = game.return_armed and game.phase_t > 2.5   # then a fresh hold of the button
        return inp
    if game.phase in ("dive", "journey", "rain", "cosmos") or game.phase == "off" and game.pushed is not None:
        return inp                                          # let the intro play
    inp.action = game.phase_t > (1.5 if game.phase == "off" else 2.5)
    return inp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--demo", action="store_true", help="let the computer play every simulation")
    ap.add_argument("--skip-boot", action="store_true", help="skip the boot and the intro: straight to the theory menu")
    ap.add_argument("--mute", action="store_true", help="no sound in the simulations that have it")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--played-all", action="store_true",
                    help="testing: as if every theory's been played. With --skip-boot it opens on the "
                         "CONGRATULATIONS! screen; otherwise it comes up after the next result")
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    ap.add_argument("--no-log", action="store_true",
                    help="don't write to the play log, play_log/<machine>.csv (or set LIFE_LAB_ACTIVITY=0)")
    args = ap.parse_args()
    record = not args.demo and args.ticks is None
    rounds = 0

    def make() -> LifeSim:
        # --skip-boot and --played-all are for the first round only: after TERMINATE PROGRAM
        # (or a timeout) the next visitor gets the start screen and the whole boot sequence
        nonlocal rounds
        first, rounds = rounds == 0, rounds + 1
        return LifeSim(skip_boot=args.skip_boot and first, mute=args.mute, seed=args.seed, record=record,
                       log_activity=not args.no_log, idle_exit=not args.demo,
                       played_all=args.played_all and first)

    run(make, "Theories of Life",
        scale=args.scale, fullscreen=args.fullscreen, autopilot=autopilot if args.demo else None,
        max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
