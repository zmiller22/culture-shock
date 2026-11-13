"""Theories of Life: the main game.

    python -m lifesim [--fullscreen] [--scale 4] [--demo] [--skip-boot] [--mute]

You're a spirit with no body yet. The Life Lab Mainframe, a 1970s machine the
scientist insists is state of the art, runs a simulation of each theory of how
life begins. Push the button to boot it: code pours down the screen, the camera
dives into the CRT, and the program opens on a zoom out from the Earth to the
edge of everything (see intro.py), where it finds you: you're the lab's next
visitor, and you sign in with a 1-4 letter name, arcade high-score style. Then
pick a theory off
the terminal, get incarnated into it, and see whether it holds up. Every
mini-game is one simulation.

Controls (keyboard, or an arcade stick / gamepad):
    STICK / ARROWS            pick a theory; on the name entry, up / down change the letter,
                              left goes back a letter, right goes on to the next
    SPACE / Z / ENTER / btn 0 boot, skip the intro, select, next letter, continue
    ESC / Q                   quit

Win a simulation and the theory is CONFIRMED; lose and it's REFUTED. The
terminal keeps score for the session.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import random
from dataclasses import dataclass
from typing import Callable

import pygame

from minigames.shell import Input, MiniGame, run
from sprites.canvas import hex_to_rgba, mix
from sprites.font import text_width
from sprites.viewer import text_surface, to_surface

from . import art
from .art import CRT_BG, PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT, SCREEN
from .intro import Cosmos, Rain

# -- tuning ------------------------------------------------------------------------
TYPE_RATE = 70.0           # characters/s the terminal types at
LINE_PAUSE = 0.12          # s between lines
VISITOR_LOG = Path(os.environ.get("LIFE_LAB_VISITORS", Path.home() / ".life_lab" / "visitors.txt"))
NAME_LEN = 4               # letters in a visitor's name, like an arcade high score
NAME_END = "END"           # the choice after Z (and before A) that signs off a short name
NAME_REPEAT = (0.4, 0.09)  # s before a held stick starts repeating, then s per letter
NAME_TIMEOUT = 40.0        # s of nobody touching anything before it signs them in as is
BUTTON_PRESS = 0.35        # s the boot button stays down before the code rain starts
RAIN_TIME = 1.4            # s of code rain on the CRT before the camera dives in
ENTER_TIME = 1.1           # s to dive into the CRT
RAIN_FADE = 0.8            # s the rain takes to clear off the start of the program
SUMMON_FORM = 1.6          # s for the spirit to come together in the void
EXIT_TIME = 1.0            # s to pull back out of the CRT to the menu
LOAD_TIME = 1.8            # s from picking a theory to the CRT switching off
CRT_OFF_TIME = 0.35
CRT_ON_TIME = 0.35
REEL_IDLE, REEL_FAST = 90.0, 900.0      # degrees/s
DIVE = (SCREEN[0], SCREEN[1] + 7, SCREEN[2], SCREEN[2] * 9 // 16)     # the part of the glass the camera dives into
SUMMON_LINES = ["1 SPIRIT DETECTED.", "YOU ARE VISITOR NO. {num}."]
WELCOME_LINES = ["WELCOME {name}.", "YOU DO NOT HAVE A BODY YET.", "PICK A THEORY OF LIFE. TRY IT ON."]


def next_visitor() -> int:
    """The next number in the lab's visitor log (1 if there's no log yet)."""
    try:
        last = VISITOR_LOG.read_text().split()
        return int(last[-2]) + 1 if len(last) >= 2 else 1
    except (OSError, ValueError):
        return 1


def sign_in(num: int, name: str) -> None:
    try:
        VISITOR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with VISITOR_LOG.open("a") as f:
            f.write(f"{num:04d} {name}\n")
    except OSError:
        pass                                          # a read-only cabinet still plays


class NameEntry:
    """Old-school arcade initials: up / down roll the letter, the button locks it
    in and moves on. After the first letter, END (one step down from A) signs off
    early, so names can be 1-4 letters."""

    LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]

    def __init__(self) -> None:
        self.name = ""
        self.cur = 0                                  # index into choices()
        self.done = False
        self.held = (0, 0)
        self.hold_t = 0.0
        self.idle = 0.0

    def choices(self) -> list[str]:
        return self.LETTERS + ([NAME_END] if self.name else [])

    @property
    def letter(self) -> str:
        return self.choices()[self.cur]

    def _roll(self, step: int) -> None:
        self.cur = (self.cur + step) % len(self.choices())

    def update(self, dt: float, inp: Input) -> None:
        if self.done:
            return
        self.idle += dt
        dirs = (inp.x, inp.y)
        if dirs != (0, 0) or inp.action:
            self.idle = 0.0
        if inp.y:
            if dirs != self.held:
                self._roll(-inp.y)                    # up goes A -> B
                self.hold_t = 0.0
            else:
                self.hold_t += dt
                while self.hold_t > NAME_REPEAT[0]:   # held: keep rolling
                    self._roll(-inp.y)
                    self.hold_t -= NAME_REPEAT[1]
        elif inp.x and dirs != self.held:
            if inp.x > 0:
                self.lock()
            elif self.name:                           # back up a letter
                prev = self.name[-1]
                self.name = self.name[:-1]
                self.cur = self.choices().index(prev)
        self.held = dirs
        if inp.action:
            self.lock()
        if self.idle > NAME_TIMEOUT:
            self.name = self.name or "GHST"
            self.done = True

    def lock(self) -> None:
        if self.letter == NAME_END:
            self.done = True
            return
        self.name += self.letter
        self.done = len(self.name) == NAME_LEN        # otherwise the next slot starts on the same letter


@dataclass
class Theory:
    code: str
    name: str
    blurb: tuple[str, str]
    players: str
    make: Callable[[], MiniGame]
    autopilot: Callable[[MiniGame], Input]
    quips: dict[str, str]


def theories(mute: bool = False) -> list[Theory]:
    """The simulations on the tape library, in the order life supposedly happens.
    Imports are lazy so the mainframe boots before the mini-games load."""
    def stork():
        from minigames.stork_bomber.game import StorkBomber
        return StorkBomber()

    def soup():
        from minigames.primordial_soup.game import PrimordialSoup
        return PrimordialSoup()

    def meet():
        from minigames.meet_cute.game import MeetCute
        return MeetCute()

    def womb():
        from minigames.womb_rave.game import WombRave
        return WombRave(mute=mute)

    def pilot(module: str):
        def go(game):
            import importlib
            return importlib.import_module(module).autopilot(game)
        return go

    return [
        Theory("01", "THE STORK HYPOTHESIS", ("BABIES ARE DELIVERED BY AIR", "BY A LARGE BIRD. TEST DELIVERY."),
               "1P", stork, pilot("minigames.stork_bomber.game"),
               {"win": "BIRD CONFIRMED. NOTIFY THE PRESS.", "lose": "NO BIRD. WHERE DO BABIES COME FROM?"}),
        Theory("02", "PRIMORDIAL SOUP", ("LIFE BEGAN IN A WARM BROTH", "OF CHEMICALS. COOK SOME UP."),
               "1P", soup, pilot("minigames.primordial_soup.game"),
               {"win": "THE SOUP IS ALIVE. IT ATE THE CHEF.", "lose": "SOUP COLD. DINERS ANGRY."}),
        Theory("03", "THE MEET CUTE", ("LIFE STARTS WHEN TWO CELLS", "FALL IN LOVE. 2 SPIRITS NEEDED."),
               "2P", meet, pilot("minigames.meet_cute.game"),
               {"win": "THEY MET. IT WAS ADORABLE.", "lose": "THEY NEVER MET. TRY AGAIN NEXT MONTH."}),
        Theory("04", "THE WOMB RAVE", ("LIFE IS A NINE MONTH PARTY", "IN A VERY SMALL CLUB."),
               "1P", womb, pilot("minigames.womb_rave.game"),
               {"win": "BIRTH ACHIEVED. VIBES IMMACULATE.", "lose": "EVICTED. THE BOUNCER WAS THE CERVIX."}),
    ]


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
    """Cache of rendered text, since the terminal redraws every frame."""

    def __init__(self) -> None:
        self.cache: dict[tuple[str, str, int], pygame.Surface] = {}

    def get(self, s: str, color: str, scale: int = 1) -> pygame.Surface:
        key = (s, color, scale)
        if key not in self.cache:
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
        self.scanlines = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(0, sh, 2):
            self.scanlines.fill((0, 0, 0, 70), (0, y, sw, 1))
        # darken the corners so the glass looks curved
        self.vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(sh):
            for x in range(sw):
                d = math.hypot((x - sw / 2) / (sw / 2), (y - sh / 2) / (sh / 2))
                if d > 0.9:
                    self.vignette.set_at((x, y), (0, 0, 0, min(200, int((d - 0.9) * 260))))
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
                 record: bool = True) -> None:
        global _ART
        _ART = _ART or Art()
        self.art = _ART
        self.text = Glyphs()
        self.rng = random.Random(seed)
        self.theories = theories(mute)
        self.results: dict[str, list[str]] = {t.code: [] for t in self.theories}
        self.sel = 0
        self.held_y = 0
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
        self.entry: NameEntry | None = None
        self.stage = ""
        self._go("hub" if skip_boot else "off")

    # -- phases --------------------------------------------------------------------
    def _go(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0
        if phase == "off":
            self.pushed = None
        elif phase == "rain":
            self.rain = Rain(SCREEN[2], SCREEN[3], seed=self.rng.random())
        elif phase == "cosmos":
            self.cosmos = Cosmos(seed=self.rng.random())
        elif phase == "summon":
            self.stage = "intro"                # intro lines -> name entry -> welcome lines
            self.typer = Typer([s.format(num=f"{self.visitor:04d}") for s in SUMMON_LINES])
            self.motes = [[math.cos(a) * r, math.sin(a) * r * 0.6, self.rng.uniform(0.5, 1.0)]
                          for a, r in ((self.rng.uniform(0, math.tau), self.rng.uniform(50, 180)) for _ in range(70))]
        elif phase == "load":
            t = self.theories[self.sel]
            self.typer = Typer([f"MOUNTING TAPE {t.code}: {t.name}", f"INCARNATING VISITOR {self.name}..."], rate=90)
        elif phase == "return":
            theory, res = self.last
            lines = [f"SIMULATION {theory.code} ENDED.", f"VISITOR {self.name} DISINCARNATED.", "",
                     f"RESULT: THEORY {VERDICT.get(res, VERDICT['?'])}", theory.quips.get(res, "THE DATA ARE A MESS."), ""]
            tested = [t for t in self.theories if self.results[t.code]]
            confirmed = [t for t in self.theories if "win" in self.results[t.code]]
            if len(confirmed) == len(self.theories):
                lines += ["ALL THEORIES CONFIRMED.", "ALL OF THEM. AT ONCE. SOMEHOW."]
            else:
                lines += [f"THEORIES TESTED: {len(tested)} OF {len(self.theories)}"]
            self.typer = Typer(lines)

    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.phase_t += dt
        if self.phase == "off":
            target = 0.0
        elif self.phase in ("load", "rain"):
            target = REEL_FAST
        else:
            target = REEL_IDLE if int(self.time * 0.8) % 3 else 0.0   # tape drives move in fits
        self.reel_speed += (target - self.reel_speed) * min(1.0, dt * 4)
        for i in range(4):
            self.reel_angle[i] = (self.reel_angle[i] + self.reel_speed * dt * (1.0 + 0.15 * i)) % 360

        if self.phase == "sim":
            self.sim.update(dt, inp)
            if self.sim.done:
                res = self.sim.result or "?"
                self.results[self.sim_theory.code].append(res)
                self.last = (self.sim_theory, res)
                self.sim = None
                if pygame.mixer.get_init():
                    pygame.mixer.fadeout(300)     # the womb rave leaves its lobby music on
                self._go("return")
            return

        if self.phase in ("load", "return") or self.phase == "summon" and self.phase_t > SUMMON_FORM:
            self.typer.update(dt)

        if self.phase == "off":
            if inp.action and self.pushed is None and self.phase_t > 0.3:
                self.pushed = self.phase_t
            if self.pushed is not None and self.phase_t - self.pushed > BUTTON_PRESS:
                self._go("rain")
        elif self.phase == "rain":
            self.rain.update(dt)
            if self.phase_t > RAIN_TIME + ENTER_TIME + 0.25:
                self._go("cosmos")
        elif self.phase == "cosmos":
            if self.phase_t < RAIN_FADE:
                self.rain.update(dt)
            self.cosmos.update(dt)
            if inp.action and self.phase_t > 0.5:
                self.cosmos.skip()
            if self.cosmos.done:
                self._go("summon")
        elif self.phase == "summon":
            if self.stage == "name":
                self.entry.update(dt, inp)
                if self.entry.done:
                    self.name = self.entry.name
                    if self.record:
                        sign_in(self.visitor, self.name)
                    self.stage = "welcome"
                    self.typer = Typer([s.format(name=self.name) for s in WELCOME_LINES])
            elif inp.action and self.phase_t > SUMMON_FORM:
                if not self.typer.done:
                    self.typer.finish()
                elif self.stage == "welcome":
                    self._go("exit")
            if self.stage == "intro" and self.typer.done and self.typer.t > self.typer.end + 0.4:
                self.stage = "name"
                self.entry = NameEntry()
        elif self.phase == "exit":
            if self.phase_t > EXIT_TIME:
                self._go("hub")
        elif self.phase == "hub":
            if inp.y and inp.y != self.held_y:
                self.sel = (self.sel + inp.y) % len(self.theories)
            self.held_y = inp.y
            if inp.action and self.phase_t > 0.2:
                self._go("load")
        elif self.phase == "load":
            if self.phase_t > LOAD_TIME + CRT_OFF_TIME + 0.2:
                self.sim_theory = self.theories[self.sel]
                self.sim = self.sim_theory.make()
                self._go("sim")
        elif self.phase == "return":
            if inp.action and self.phase_t > CRT_ON_TIME + 0.5:
                if self.typer.done:
                    self._go("hub")
                else:
                    self.typer.finish()

    # -- drawing -----------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        if self.phase == "sim":
            self.sim.draw(screen)
        elif self.phase == "cosmos":
            self.cosmos.draw(screen)
            if self.phase_t < RAIN_FADE:                  # the code rain clears off the start of the program
                self._draw_rain_fullscreen(screen, 1 - self.phase_t / RAIN_FADE)
        elif self.phase == "summon":
            self._draw_summon(screen)
        elif self.phase in ("rain", "exit"):
            if self.phase == "rain":
                k = max(0.0, min(1.0, (self.phase_t - RAIN_TIME) / ENTER_TIME))
                k = k * k                                   # accelerate into the glass
            else:
                k = 1 - min(1.0, self.phase_t / EXIT_TIME)
                k = k * k * (3 - 2 * k)
            if k <= 0:
                self._draw_room(screen)
            else:
                self._draw_room(self.frame)
                self._camera(screen, k)
        else:
            self._draw_room(screen)

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

    def _draw_summon(self, screen: pygame.Surface) -> None:
        """The edge of everything, where the program finds you."""
        screen.fill((4, 6, 14))
        for x, y, b in self.void_stars:
            screen.fill((b, b, b + 20), (x, y, 1, 1))
        cx, cy = art.W / 2, 68
        k = min(1.0, self.phase_t / SUMMON_FORM)
        self.spirits = []
        for mx, my, speed in self.motes:                    # wisps drifting in from everywhere
            p = min(1.0, k * (0.5 + speed * 0.7))
            if p < 1:
                x, y = cx + mx * (1 - p), cy + my * (1 - p)
                col = art.SPIRIT_BODY if speed > 0.75 else art.SPIRIT_EDGE
                screen.fill(rgb(col), (int(x), int(y), 1 + (speed > 0.9), 1))
        if k > 0.6:
            self._draw_spirit(screen, cx, cy, 2.0 * min(1.0, (k - 0.6) / 0.4))
        lines = self.typer.visible()
        for i, line in enumerate(lines):
            if line:
                full = self.typer.lines[i]
                screen.blit(self.text.get(line, PHOSPHOR), (cx - text_width(full) // 2, 104 + i * 9))
        if self.stage == "name":
            self._draw_name_entry(screen, cx, 126)
        elif self.stage == "welcome" and self.typer.done and int(self.time * 2) % 2 == 0:
            s = self.text.get("PRESS BUTTON", PHOSPHOR_DIM)
            screen.blit(s, (cx - s.get_width() // 2, 160))
        screen.blit(self.text.get("LIFE LAB MAINFRAME", PHOSPHOR_DIM), (4, 3))
        s = self.text.get("PROGRAM: GENESIS", PHOSPHOR_DIM)
        screen.blit(s, (art.W - 4 - s.get_width(), 3))
        screen.blit(self.cosmos.scanlines if self.cosmos else self.art.scanlines, (0, 0))

    def _draw_name_entry(self, screen: pygame.Surface, cx: float, y: int) -> None:
        """ENTER YOUR NAME and four big letter slots, the current one rolling."""
        e = self.entry
        s = self.text.get("ENTER YOUR NAME:", PHOSPHOR_DIM)
        screen.blit(s, (cx - s.get_width() // 2, y))
        slot_w, gap = 14, 6
        x0 = int(cx - (NAME_LEN * slot_w + (NAME_LEN - 1) * gap) / 2)
        blink = int(self.time * 3) % 2 == 0
        for i in range(NAME_LEN):
            x, top = x0 + i * (slot_w + gap), y + 10
            here = i == len(e.name)
            if i < len(e.name):
                img = self.text.get(e.name[i], "#eaffea", 2)
            elif here and e.letter == NAME_END:
                img = self.text.get(NAME_END, "#eaffea" if blink else PHOSPHOR)
            elif here:
                img = self.text.get(e.letter, "#eaffea" if blink else PHOSPHOR, 2)
            else:
                img = None
            if img:
                screen.blit(img, (x + (slot_w - img.get_width()) // 2, top + (10 - img.get_height()) // 2))
            screen.fill(rgb(PHOSPHOR if here else PHOSPHOR_DIM), (x, top + 12, slot_w, 1))
            if here:                                     # little arrows: the stick rolls this one
                screen.fill(rgb(PHOSPHOR_DIM), (x + slot_w // 2 - 1, top - 3, 3, 1))
                screen.fill(rgb(PHOSPHOR_DIM), (x + slot_w // 2, top - 4, 1, 1))
                screen.fill(rgb(PHOSPHOR_DIM), (x + slot_w // 2 - 1, top + 15, 3, 1))
                screen.fill(rgb(PHOSPHOR_DIM), (x + slot_w // 2, top + 16, 1, 1))
        hint = "STICK: LETTER   BUTTON: NEXT" + ("   END: DONE" if e.name else "")
        s = self.text.get(hint, PHOSPHOR_FAINT)
        screen.blit(s, (cx - s.get_width() // 2, 166))

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
        rate = 18 if self.phase in ("load", "rain") else 4
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
        sx, sy, sw, sh = SCREEN
        crt.fill(rgb(CRT_BG))
        self.spirits: list[tuple[float, float, float]] = []
        getattr(self, f"_crt_{self.phase}")(crt)

        # phosphor bloom: a blurred copy added on top
        small = pygame.transform.smoothscale(crt, (sw // 4, sh // 4))
        bloom = pygame.transform.smoothscale(small, (sw, sh))
        bloom.set_alpha(80)
        crt.blit(bloom, (0, 0), special_flags=pygame.BLEND_ADD)
        crt.blit(a.scanlines, (0, 0))
        if int(self.time * 30) % 17 == 0:                      # a little flicker
            crt.fill((6, 10, 6), special_flags=pygame.BLEND_ADD)
        crt.blit(a.vignette, (0, 0))
        for x, y, scale in self.spirits:          # the spirit is real, not phosphor: drawn over the glass effects
            self._draw_spirit(crt, x, y, scale)

        # the CRT switching off (load) or back on (return)
        squash = None
        if self.phase == "load" and self.phase_t > LOAD_TIME:
            squash = min(1.0, (self.phase_t - LOAD_TIME) / CRT_OFF_TIME)
        elif self.phase == "return" and self.phase_t < CRT_ON_TIME:
            squash = 1.0 - self.phase_t / CRT_ON_TIME
        if squash is None:
            screen.blit(crt, (sx, sy))
            return
        screen.fill((0, 0, 0), (sx, sy, sw, sh))
        if squash < 0.6:                                         # collapse to a bright line...
            h = max(1, int(sh * (1 - squash / 0.6)))
            line = pygame.transform.scale(crt, (sw, h))
            line.fill((90, 140, 90), special_flags=pygame.BLEND_ADD)
            screen.blit(line, (sx, sy + (sh - h) // 2))
        elif squash < 1.0:                                       # ...then to a dot
            w = max(2, int(sw * (1 - (squash - 0.6) / 0.4)))
            screen.fill((220, 255, 220), (sx + (sw - w) // 2, sy + sh // 2, w, 1))

    # each phase paints the CRT surface (coordinates are inside the glass)
    def _lines(self, crt: pygame.Surface, lines: list[str], x: int = 4, y: int = 4, cursor: bool = True) -> None:
        for i, line in enumerate(lines):
            if line:
                crt.blit(self.text.get(line, PHOSPHOR), (x, y + i * 7))
        if cursor and int(self.time * 2.5) % 2 == 0:
            last = lines[-1] if lines else ""
            crt.fill(rgb(PHOSPHOR), (x + text_width(last) + (2 if last else 0), y + (len(lines) - 1 if lines else 0) * 7, 3, 5))

    def _spirit(self, crt: pygame.Surface, x: float, y: float, scale: float = 1.0) -> None:
        self.spirits.append((x, y, scale))

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
        sw = SCREEN[2]
        for word, y in (("LIFE LAB", 10), ("MAINFRAME", 29)):
            s = self.text.get(word, PHOSPHOR, 3)
            crt.blit(s, (sw // 2 - s.get_width() // 2, y))
        crt.fill(rgb(PHOSPHOR_DIM), (24, 50, sw - 48, 1))
        # the button: a chunky key with a lip, which sinks when pushed
        down = self.pushed is not None
        bw, bh = 104, 18
        bx, by = sw // 2 - bw // 2, 60 + (2 if down else 0)
        if not down:
            crt.fill(rgb(PHOSPHOR_DIM), (bx, by + 2, bw, bh))           # the lip under it
        pulse = int(self.time * 2) % 2 == 0
        crt.fill(rgb(PHOSPHOR if down or pulse else PHOSPHOR_DIM), (bx, by, bw, bh))
        crt.fill(rgb(PHOSPHOR_DIM if down else PHOSPHOR_FAINT), (bx + 1, by + 1, bw - 2, bh - 2))
        label = self.text.get("PUSH TO BOOT UP", "#eaffea" if down else PHOSPHOR)
        crt.blit(label, (sw // 2 - label.get_width() // 2, by + bh // 2 - 2))
        s = self.text.get("STATE OF THE ART. EST. 1974", PHOSPHOR_FAINT)
        crt.blit(s, (sw // 2 - s.get_width() // 2, 92))

    def _crt_rain(self, crt: pygame.Surface) -> None:
        self.rain.draw(crt)

    def _crt_exit(self, crt: pygame.Surface) -> None:
        self._crt_hub(crt)

    def _crt_hub(self, crt: pygame.Surface) -> None:
        sw = SCREEN[2]
        crt.blit(self.text.get("LIFE LAB MAINFRAME", PHOSPHOR_DIM), (4, 3))
        who = self.text.get(f"VISITOR {self.visitor:04d} {self.name}", PHOSPHOR_DIM)
        crt.blit(who, (sw - 4 - who.get_width(), 3))
        crt.fill(rgb(PHOSPHOR_DIM), (4, 10, sw - 8, 1))
        crt.blit(self.text.get("SELECT A THEORY OF LIFE:", PHOSPHOR), (4, 14))
        for i, t in enumerate(self.theories):
            y = 28 + i * 10
            runs = self.results[t.code]
            verdict = VERDICT["win"] if "win" in runs else VERDICT[runs[-1]] if runs and runs[-1] in VERDICT else \
                VERDICT["?"] if runs else VERDICT[None]
            fg = PHOSPHOR if i == self.sel else PHOSPHOR_DIM
            crt.blit(self.text.get(f"{t.code} {t.name}", fg), (21, y))
            if t.players == "2P":
                crt.blit(self.text.get("2P", fg), (21 + text_width(f"{t.code} {t.name}") + 4, y))
            v = self.text.get(verdict, fg if i == self.sel or runs else PHOSPHOR_FAINT)
            crt.blit(v, (sw - 6 - v.get_width(), y))
        self._spirit(crt, 10, 30 + self.sel * 10)
        crt.fill(rgb(PHOSPHOR_DIM), (4, 70, sw - 8, 1))
        t = self.theories[self.sel]
        for i, line in enumerate(t.blurb):
            crt.blit(self.text.get(line, PHOSPHOR), (4, 75 + i * 7))
        hint = "STICK: CHOOSE   BUTTON: INCARNATE"
        crt.blit(self.text.get(hint, PHOSPHOR_FAINT), (4, 94))
        if int(self.time * 2.5) % 2 == 0:
            crt.fill(rgb(PHOSPHOR), (4 + text_width(hint) + 2, 94, 3, 5))

    def _crt_load(self, crt: pygame.Surface) -> None:
        self._lines(crt, self.typer.visible())
        # the spirit spirals into the tape and shrinks away
        k = min(1.0, max(0.0, (self.phase_t - 0.5) / (LOAD_TIME - 0.6)))
        if k < 1.0:
            ang = k * 5 * math.tau
            r = 22 * (1 - k)
            cx, cy = SCREEN[2] // 2, 60
            self._spirit(crt, cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.6, scale=1.0 - k)
        bar = int((SCREEN[2] - 16) * min(1.0, self.phase_t / LOAD_TIME))
        crt.fill(rgb(PHOSPHOR_FAINT), (8, 90, SCREEN[2] - 16, 5))
        crt.fill(rgb(PHOSPHOR), (8, 90, bar, 5))

    def _crt_return(self, crt: pygame.Surface) -> None:
        self._lines(crt, self.typer.visible())
        if self.typer.done:
            if int(self.time * 2) % 2 == 0:
                s = self.text.get("PRESS BUTTON", PHOSPHOR_DIM)
                crt.blit(s, (SCREEN[2] - 26 - s.get_width(), SCREEN[3] - 12))
            self._spirit(crt, SCREEN[2] - 14, SCREEN[3] - 22)


def autopilot(game: LifeSim) -> Input:
    """Boots up, then runs every simulation in turn with that mini-game's own
    autopilot. For demos and smoke tests."""
    if game.phase == "sim":
        return game.sim_theory.autopilot(game.sim)
    inp = Input()
    if game.phase == "hub":
        untested = [i for i, t in enumerate(game.theories) if not game.results[t.code]]
        want = untested[0] if untested else int(game.time / 20) % len(game.theories)
        if want != game.sel:
            inp.y = 1 if int(game.time * 8) % 2 else 0           # tap down, one step at a time
            return inp
        inp.action = game.phase_t > 1.5
        return inp
    if game.phase == "summon" and game.stage == "name":
        # sign in as DEMO: roll to each letter, then press
        want = "DEMO"[len(game.entry.name)] if len(game.entry.name) < 4 else None
        if want and game.entry.letter != want:
            inp.y = -1 if int(game.time * 30) % 2 else 0          # tap up, one letter at a time
        elif int(game.time * 4) != int((game.time - 1 / 60) * 4):
            inp.action = True
        return inp
    if game.phase in ("rain", "cosmos", "exit") or game.phase == "off" and game.pushed is not None:
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
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()
    record = not args.demo and args.ticks is None
    run(lambda: LifeSim(skip_boot=args.skip_boot, mute=args.mute, seed=args.seed, record=record), "Theories of Life",
        scale=args.scale, fullscreen=args.fullscreen, autopilot=autopilot if args.demo else None,
        max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
