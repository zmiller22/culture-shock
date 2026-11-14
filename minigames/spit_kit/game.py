"""Spit Kit: spit in the jar, the mainframe reads your DNA, and splices you
together out of the lab's specimens.

    python -m minigames.spit_kit [--fullscreen] [--scale 4] [--demo] [--seed N]

The jar next to the cabinet sits on an HX711 load cell (see jar.py). A spit is
a step up in weight that settles. Without the sensor (on a laptop), the button
is the spit.

The round:
    title     how-to pages
    spit      SPIT IN THE JAR. After MALFUNCTION_AFTER s with no spit, holding the
              button goes ahead on DNA from a shed hair instead (the fallback for
              a sensor that isn't working). Waits up to SPIT_TIMEOUT s, then
              gives up (lose)
    got       SAMPLE RECEIVED
    analyze   centrifuge, sequence, cross-reference (button hurries it along)
    survey    partway through: the behavioral analysis survey (orifice, string,
              colour). The first two pick species that go into you; the colour
              is the room you walk out into
    report    YOU ARE 40% DOM, 30% BANANA AND 30% GENIUS
    splice    the donors spin together, you get scanned in, mutations zap on
    reveal    THIS IS YOU. Walk it around; walk out the door, ENTER SIMULATION, to
              finish (win)

Controls (keyboard, or an arcade stick / gamepad):
    SPACE / Z / ENTER / button 0    next / hurry / attack (and the spit, with no sensor); on the
                                    survey, a tap is the next question and a hold hands it in
    STICK / ARROWS                  survey: sideways changes the answer, up / down the question;
                                    walk your new body, up jumps
    ESC / Q                         quit
"""

from __future__ import annotations

import argparse
import math
import random
import threading

import pygame

from sprites.canvas import Canvas, hex_to_rgba
from sprites.characters import CONTROL_GROUP, from_specimen
from sprites.font import text_width
from sprites.palette import LAB_BG, LAB_DIM, LAB_FLOOR, LAB_GRID, LAB_TEXT
from sprites.rig import SIZE, poses
from sprites.viewer import H, W, Actor, text_surface, to_surface

from ..shell import Input, run
from . import dna, tutorial
from .jar import get_jar

# -- tuning ------------------------------------------------------------------------
SPIT_TIMEOUT = 90.0          # s of waiting at the jar before the lab gives up
FALLBACK_AFTER = 6.0         # s a live sensor can be not-ready before the button counts as a spit
MALFUNCTION_AFTER = 15.0     # s with no spit before SENSOR MALFUNCTION DETECTED offers the hair instead
HAIR_HOLD = 1.5              # s of holding the button that takes the hair (under the main game's HOLD_ANYWHERE)
MALFUNCTION_LINES = ("SENSOR MALFUNCTION DETECTED...",
                     "USING DNA FROM HAIR YOU SHED WHEN YOU WALKED IN INSTEAD.",
                     "HOLD DOWN ANY BUTTON TO CONTINUE.")
GOT_TIME = 2.8               # s of SAMPLE RECEIVED
REPORT_STEP = 2.8            # s per species in the report
REPORT_HOLD = 6.0            # s on the finished report before it moves on by itself
SWIRL_TIME, FLASH_TIME, SCAN_TIME = 2.2, 0.3, 3.4
ZAP_TIME = 2.6               # s per mutation
DRIVE_TIMEOUT = 40.0         # s of nobody touching anything before the reveal ends itself
JAR_SIDE = 1                 # which side of the cabinet the real jar is on: +1 right, -1 left
VOLUME = ((600, "A DRIBBLE"), (2500, "ADEQUATE"), (8000, "GENEROUS"), (1e12, "FRANKLY ALARMING"))
FLOOR_Y = 164
SCALE = 2                    # the new you is drawn at 2x

ACCENT = "#ffe14d"
SPIT_COL = "#c4dc96"
PHOS, PHOS_DIM, PHOS_BG = "#5dff7a", "#2a9a46", "#06160b"
BASE_COLS = {"A": "#e83b3b", "T": "#4aa3ff", "C": "#ffe14d", "G": "#39d353"}

TAUNTS = ("DON'T BE SHY.", "HOCK ONE UP.", "IT'S FOR SCIENCE.", "WE'VE SEEN WORSE.",
          "ONE GOOD GOB IS ALL WE NEED.", "THE JAR IS WAITING.", "NO SPIT, NO SCIENCE.")

# (label, seconds of work after it types, suffix once the work is done)
ANALYSIS = (
    ("SAMPLE VOLUME: {vol}", 0.9, ""),
    ("SPINNING CENTRIFUGE", 1.6, " OK"),
    ("FILTERING OUT FOREIGN DNA", 1.6, "... HOW MANY PEOPLE HAVE YOU KISSED?!?"),
    ("DRUG TEST", 1.3, "... POSITIVE"),
    ("EXTRACTING DNA", 1.4, " OK"),
    (SURVEY_LINE := "BEHAVIORAL ANALYSIS SURVEY", 0.4, " DONE"),
    ("SEQUENCING 3,200,000,000 BASES", 2.6, " OK"),
    ("MATCHING LAB SPECIMENS", 1.9, " OK"),
    ("{n} MATCHES FOUND.", 1.2, ""),
)
TYPE_RATE = 40.0
SURVEY_REPEAT = (0.4, 0.12)  # s before a held stick starts rolling the answers, then s per answer
SUBMIT_HOLD = 0.8            # s of holding the button that hands the survey in
ROOM_WASH = 110              # alpha of the favourite colour washed over the room you walk out into


def rgb(c: str) -> tuple[int, int, int]:
    return hex_to_rgba(c)[:3]


_TEXT: dict[tuple[str, str, int], pygame.Surface] = {}


def txt(s: str, color: str = LAB_TEXT, scale: int = 1) -> pygame.Surface:
    key = (s, color, scale)
    if key not in _TEXT:
        surf = text_surface(s, color)
        _TEXT[key] = pygame.transform.scale_by(surf, scale) if scale > 1 else surf
    return _TEXT[key]


def blit_c(screen: pygame.Surface, img: pygame.Surface, x: float, y: float) -> None:
    screen.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() / 2)))


def wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and text_width(trial) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


class Survey:
    """Three questions, every one with an answer already picked. Up and down move
    between the questions, left and right slide through the answers, a tap of the
    button goes on to the next question, and holding it hands the survey in."""

    def __init__(self) -> None:
        self.q = 0
        self.picks = [0] * len(dna.SURVEY)
        self.held = (0, 0)
        self.hold_t = 0.0
        self.press: float | None = None               # s the button's been down, while it is
        self.slide = 0                                # which way the answer just slid, for the animation
        self.slide_t = 9.0
        self.done = False

    @property
    def hold_k(self) -> float:
        """0..1, how far a held button is to handing it in (0 for a tap)."""
        if self.press is None or self.press < 0.15:
            return 0.0
        return min(1.0, (self.press - 0.15) / (SUBMIT_HOLD - 0.15))

    def _roll(self, step: int) -> None:
        n = len(dna.SURVEY[self.q][1])
        self.picks[self.q] = (self.picks[self.q] + step) % n
        self.slide, self.slide_t = step, 0.0

    def update(self, dt: float, inp: Input, pressed: bool) -> None:
        self.slide_t += dt
        dirs = (inp.x, inp.y)
        if inp.y and dirs != self.held:               # up and down: another question
            self.q = max(0, min(len(dna.SURVEY) - 1, self.q + inp.y))
        elif inp.x:                                   # sideways: another answer, held keeps sliding
            if dirs != self.held:
                self._roll(inp.x)
                self.hold_t = 0.0
            else:
                self.hold_t += dt
                while self.hold_t > SURVEY_REPEAT[0]:
                    self._roll(inp.x)
                    self.hold_t -= SURVEY_REPEAT[1]
        self.held = dirs
        if pressed:
            self.press = 0.0
        elif self.press is not None:
            if inp.held:
                self.press += dt
                self.done = self.press >= SUBMIT_HOLD
            else:                                     # a tap: on to the next question
                if self.press < SUBMIT_HOLD:
                    self.q = min(len(dna.SURVEY) - 1, self.q + 1)
                self.press = None


def volume_word(delta: float, hair: bool = False) -> str:
    if hair:
        return "ONE HAIR"
    return next(word for limit, word in VOLUME if abs(delta) < limit)


# -- art ---------------------------------------------------------------------------
def donor_idle(species: str) -> list[Canvas]:
    mod = next(m for slug, _, m in CONTROL_GROUP if slug == species)
    body = mod.build()
    return [body.render(p) for p in poses("idle")]


def draw_jar(screen: pygame.Surface, x: int, y: int, level: float, t: float, scale: int = 3) -> None:
    """A big glass jar on a scale, bottom-centre at (x, y). `level` 0..1 of spit in it."""
    s = scale
    jw, jh = 22 * s, 28 * s
    jar = pygame.Rect(x - jw // 2, y - 6 * s - jh, jw, jh)
    pygame.draw.rect(screen, (20, 12, 28), (x - 15 * s, y - 6 * s, 30 * s, 6 * s))            # scale
    pygame.draw.rect(screen, (110, 100, 140), (x - 14 * s, y - 5 * s, 28 * s, 4 * s))
    pygame.draw.rect(screen, (60, 52, 84), (x - 14 * s, y - 2 * s, 28 * s, s))
    pygame.draw.rect(screen, (30, 22, 40), (x - 4 * s, y - 4 * s, 8 * s, 2 * s))              # readout
    pygame.draw.rect(screen, (20, 12, 28), jar.inflate(2 * s, 2 * s), border_radius=4 * s)
    pygame.draw.rect(screen, (50, 72, 84), jar, border_radius=4 * s)
    fill = round((0.15 + 0.6 * level) * (jh - 2 * s))
    if fill > 0:
        top = jar.bottom - s - fill
        pygame.draw.rect(screen, rgb(SPIT_COL), (jar.x + s, top, jw - 2 * s, fill), border_radius=2 * s)
        for i in range(0, jw - 2 * s, s):                                                       # wobbly surface
            dy = round(math.sin(t * 5 + i * 0.3) * s * 0.6)
            pygame.draw.rect(screen, (240, 250, 210), (jar.x + s + i, top + dy, s, s))
        for i in range(3):                                                                      # bubbles
            by = jar.bottom - s - ((t * 9 + i * 13) % fill)
            pygame.draw.rect(screen, (230, 245, 200), (jar.x + 5 * s + i * 5 * s, by, s, s))
    pygame.draw.rect(screen, (150, 200, 210), (jar.x + 2 * s, jar.y + 3 * s, s, 12 * s))        # shine
    pygame.draw.rect(screen, (20, 12, 28), (x - 13 * s, jar.y - 4 * s, 26 * s, 5 * s))          # rim
    pygame.draw.rect(screen, (150, 160, 170), (x - 12 * s, jar.y - 3 * s, 24 * s, 3 * s))
    label = txt("DNA", "#1b1430")
    pygame.draw.rect(screen, (230, 220, 190), (x - 9, jar.y + 9 * s, 18, 9))
    screen.blit(label, (x - label.get_width() // 2, jar.y + 9 * s + 2))


def draw_arrow(screen: pygame.Surface, x: int, y: int, way: int = 1, color: str = ACCENT) -> None:
    """A chunky pixel arrow, tip at (x, y), pointing right (way=+1) or left (-1)."""
    shaft = [(-20, -3), (-9, -3), (-9, -8), (0, 0), (-9, 8), (-9, 3), (-20, 3)]
    pts = [(x + way * dx, y + dy) for dx, dy in shaft]
    pygame.draw.polygon(screen, (20, 12, 28), [(px + way, py + 1) for px, py in pts])     # drop shadow
    pygame.draw.polygon(screen, rgb(color), pts)


def draw_lab(screen: pygame.Surface, t: float) -> None:
    screen.fill(rgb(LAB_BG))
    for i in range(7):                                           # specimen tubes on the back wall
        x = 8 + i * 46
        pygame.draw.rect(screen, rgb(LAB_GRID), (x, 40, 16, 84), 1)
        lvl = 50 + round(4 * math.sin(t * 0.7 + i))
        pygame.draw.rect(screen, (34, 58, 52), (x + 2, 124 - lvl, 12, lvl - 1))
        pygame.draw.rect(screen, rgb(LAB_FLOOR), (x - 2, 36, 20, 5))
    pygame.draw.rect(screen, rgb(LAB_FLOOR), (0, FLOOR_Y, W, H - FLOOR_Y))
    for gx in range(-16, W + 16, 16):
        pygame.draw.line(screen, rgb(LAB_GRID), (gx, FLOOR_Y), (gx - 12, H), 1)
    pygame.draw.line(screen, rgb(LAB_GRID), (0, FLOOR_Y), (W, FLOOR_Y), 1)


def draw_helix(screen: pygame.Surface, cx: int, top: int, bottom: int, t: float, speed: float = 2.5,
               radius: int = 16, seq: str = "") -> None:
    n = (bottom - top) // 6
    for i in range(n):
        y = top + i * 6
        ph = t * speed + i * 0.45
        s, c = math.sin(ph), math.cos(ph)
        x1, x2 = cx + s * radius, cx - s * radius
        base = seq[i % len(seq)] if seq else "ATCG"[i % 4]
        pair = {"A": "T", "T": "A", "C": "G", "G": "C"}[base]
        mid = (x1 + x2) / 2
        pygame.draw.line(screen, rgb(BASE_COLS[base]), (x1, y + 1), (mid, y + 1), 1)
        pygame.draw.line(screen, rgb(BASE_COLS[pair]), (mid, y + 1), (x2, y + 1), 1)
        front = (220, 230, 255) if c > 0 else (110, 100, 150)
        back = (110, 100, 150) if c > 0 else (220, 230, 255)
        pygame.draw.rect(screen, front, (round(x1) - 1, y, 3, 3))
        pygame.draw.rect(screen, back, (round(x2) - 1, y, 3, 3))


class Art:
    def __init__(self) -> None:
        self.shade = pygame.Surface((W, H), pygame.SRCALPHA)
        self.shade.fill((0, 0, 0, 150))


_ART: Art | None = None


# -- the game -----------------------------------------------------------------------
class SpitKit:
    title = "SPIT KIT"

    def __init__(self, seed: int | None = None, show_title: bool = True) -> None:
        global _ART
        _ART = _ART or Art()
        self.art = _ART
        self.rng = random.Random(seed)
        self.result: str | None = None
        self.done = False
        self.time = 0.0
        self.phase, self.phase_t = ("title" if show_title else "spit"), 0.0
        self.howto = tutorial.make()
        self.jar = get_jar()
        self.jar.poll()                                  # drop anything from before this round
        self.sample_no = self.rng.randrange(1000, 9999)
        self.delta = 0.0
        self.not_ready_t = 0.0
        self.hair = False                                # went ahead on a shed hair, not a spit
        self.hair_hold: float | None = None              # s the button's been held on the malfunction notice
        self.taunt = self.rng.randrange(len(TAUNTS))
        self.splash: list[list[float]] = []              # spit droplets on the SAMPLE RECEIVED screen
        self.idle_t = 0.0
        self.actor: Actor | None = None
        self.ax = W / 2
        self.held_y = 0

        # the genes get rolled once the survey's answered (or the lab gives up on a spit),
        # then rendered on a worker thread while the analysis plays out
        self.survey = Survey()
        self.color: str | None = None                  # the favourite colour, once they've said
        self.profile: list[dna.Strand] = []
        self.you: dna.You | None = None
        self._canvases: dict | None = None
        self.sprites: dict | None = None

    def _roll(self, answers: list[int] | None) -> None:
        """Pick the donors (from the survey answers, or at random) and start rendering."""
        if answers is None:
            self.profile = dna.roll_profile(self.rng)
        else:
            self.profile = dna.survey_profile(answers, self.rng)
            self.color = dna.survey_color(answers)
        build_rng = random.Random(self.rng.random())
        threading.Thread(target=self._build, args=(build_rng,), daemon=True).start()

    def _build(self, rng: random.Random) -> None:
        you = dna.build_you(self.profile, rng, number=self.sample_no)
        donors = {s.species: donor_idle(s.species) for s in you.profile}
        steps = [[sp.render(p) for p in poses("idle")] for sp in you.steps]
        final = from_specimen(you.final).all_frames()
        self._canvases = {"donors": donors, "steps": steps, "final": final}
        self.you = you

    @property
    def ready(self) -> bool:
        return self.you is not None

    def _surfaces(self) -> dict:
        """The worker's canvases, turned into surfaces (pygame wants that on the main thread)."""
        if self.sprites is None and self.ready:
            c = self._canvases

            def big(cv: Canvas) -> pygame.Surface:
                return pygame.transform.scale_by(to_surface(cv), SCALE)

            final = {}
            for anim, frames in c["final"].items():
                right = [big(f) for f in frames]
                final[anim] = {1: right, -1: [pygame.transform.flip(s, True, False) for s in right]}
            self.sprites = {
                "donors": {k: [to_surface(f) for f in v] for k, v in c["donors"].items()},
                "steps": [[big(f) for f in frames] for frames in c["steps"]],
                "final": final,
            }
        return self.sprites

    @property
    def cutscene(self) -> bool:
        """Nobody's expected to touch the stick: spitting in the jar, then the lab
        reading it. Tells the main game not to ask if anyone's still there."""
        return self.phase in ("spit", "got", "analyze", "report", "splice")     # (not the survey)

    def _go(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    # -- timings ---------------------------------------------------------------------
    def _analysis(self) -> list[tuple[str, float, str, float]]:
        """(text, start, suffix, work) per line, with the placeholders filled in."""
        out, t = [], 0.0
        for label, work, suffix in ANALYSIS:
            text = label.format(vol=volume_word(self.delta, self.hair), n=len(self.profile) or dna.DONORS)
            out.append((text, t, suffix, work))
            t += len(text) / TYPE_RATE + work + 0.1
        return out

    @property
    def survey_at(self) -> float:
        """s into the analysis that the survey comes up."""
        return next(start for text, start, _, _ in self._analysis() if text == SURVEY_LINE)

    @property
    def analysis_time(self) -> float:
        text, start, suffix, work = self._analysis()[-1]
        return start + len(text) / TYPE_RATE + work

    @property
    def report_time(self) -> float:
        return len(self.profile) * REPORT_STEP

    @property
    def splice_time(self) -> float:
        n = len(self.you.mutations) if self.you else 0
        return SWIRL_TIME + FLASH_TIME + SCAN_TIME + n * ZAP_TIME + 0.6

    # -- update ------------------------------------------------------------------------
    def update(self, dt: float, inp: Input) -> None:
        self.time += dt
        self.phase_t += dt
        events = self.jar.poll()
        pressed = inp.action or any(p.action for p in inp.players)

        if self.phase == "title":
            self.howto.update(dt, inp)
            if self.howto.done:
                self.jar.poll()
                self._go("spit")
        elif self.phase == "spit":
            self._update_spit(dt, inp, pressed, events)
        elif self.phase == "got":
            for d in self.splash:
                d[0] += d[2] * dt
                d[1] += d[3] * dt
                d[3] += 300 * dt
            if self.phase_t > GOT_TIME:
                self._go("analyze")
        elif self.phase == "analyze":
            if pressed and self.phase_t > 0.5:
                self.phase_t += 1.2                          # hurry the lab along
            if not self.survey.done and self.phase_t >= self.survey_at:
                self._go("survey")
            elif self.phase_t > self.analysis_time + 0.6 and self.ready:
                self._surfaces()
                self._go("report")
        elif self.phase == "survey":
            self.survey.update(dt, inp, pressed and self.phase_t > 0.4)
            if self.survey.done:
                self._roll(self.survey.picks)
                self.phase, self.phase_t = "analyze", self.survey_at
        elif self.phase == "report":
            done_at = self.report_time + 1.5
            if pressed and self.phase_t > 0.4:
                # first press finishes the report, the next one moves on
                self.phase_t = done_at if self.phase_t < done_at else done_at + REPORT_HOLD
            if self.phase_t > done_at + REPORT_HOLD:
                self._go("splice")
        elif self.phase == "splice":
            if self.phase_t > self.splice_time:
                self._start_drive()
        elif self.phase == "reveal":
            self._update_drive(dt, inp, pressed)
        elif self.phase == "nospit":
            if pressed and self.phase_t > 1.0:
                self.done = True

    @property
    def malfunction(self) -> bool:
        """No spit for a while: the lab offers to go ahead on a shed hair."""
        return self.phase == "spit" and self.phase_t > MALFUNCTION_AFTER

    def _update_spit(self, dt: float, inp: Input, pressed: bool, events: list[tuple[str, float]]) -> None:
        jar = self.jar
        self.not_ready_t = 0.0 if jar.ready else self.not_ready_t + dt
        spit = next((d for e, d in events if e == "SPIT"), None)
        fallback = not jar.live or (jar.state in ("OFFLINE", "ERROR") and self.not_ready_t > FALLBACK_AFTER)
        held = inp.held or any(p.held for p in inp.players)
        if self.malfunction:                                 # the hair: a hold, so a stray tap can't take it
            if pressed:
                self.hair_hold = 0.0
            elif self.hair_hold is not None:
                self.hair_hold = self.hair_hold + dt if held else None
        elif spit is None and pressed and fallback and self.phase_t > 0.3:
            spit = self.rng.uniform(800, 9000)               # a pretend gob
        if spit is not None:
            self.delta = spit
            self.splash = [[100.0, 70.0, self.rng.uniform(-90, 90), self.rng.uniform(-160, -40)] for _ in range(14)]
            self._go("got")
        elif self.hair_hold is not None and self.hair_hold >= HAIR_HOLD:
            self.hair, self.delta, self.splash = True, 0.0, []
            self._go("got")
        elif self.phase_t > SPIT_TIMEOUT:
            self.result = "lose"
            self._roll(None)                                 # no spit, no survey: the lab makes something up
            self._go("nospit")
        if int(self.phase_t / 3.2) != int((self.phase_t - dt) / 3.2):
            self.taunt = (self.taunt + 1) % len(TAUNTS)

    def _start_drive(self) -> None:
        self.result = "win"
        self.actor = Actor()
        self.ax = W / 2
        self.idle_t = 0.0
        self._go("reveal")

    def _update_drive(self, dt: float, inp: Input, pressed: bool) -> None:
        a = self.actor
        jump = inp.y < 0 and self.held_y >= 0
        self.held_y = inp.y
        busy = inp.x or inp.y or pressed
        self.idle_t = 0.0 if busy else self.idle_t + dt
        a.update(dt, move=inp.x, jump=jump, attack=pressed and self.phase_t > 0.5, crouch=inp.y > 0)
        self.ax += a.dx * dt
        half = SIZE * SCALE / 2
        self.ax = max(half - 20, self.ax)
        if self.ax > W + half - 30 or self.idle_t > DRIVE_TIMEOUT:    # out the exit
            self.done = True

    # -- draw ----------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        draw_lab(screen, self.time)
        if self.phase in ("report", "splice"):
            screen.blit(self.art.shade, (0, 0))              # the lab fades back so the specimens stand out
        getattr(self, f"_draw_{self.phase}")(screen)

    def _draw_title(self, screen: pygame.Surface) -> None:
        self.howto.draw(screen)

    def _draw_spit(self, screen: pygame.Surface) -> None:
        jar, t = self.jar, self.time
        level = max(0.0, min(1.0, jar.diff / max(1.0, jar.threshold * 20))) if jar.live else 0.0
        draw_jar(screen, 70, FLOOR_Y, level, t)

        title = txt("SPIT IN THE JAR", ACCENT, 2)
        blit_c(screen, title, 214, 22 + round(2 * math.sin(t * 3)))
        blit_c(screen, txt(TAUNTS[self.taunt], LAB_TEXT), 214, 40)

        # point at the real jar, next to the cabinet
        k = round(4 * math.sin(t * 8))
        side = "THE REAL ONE IS RIGHT THERE"
        if JAR_SIDE > 0:
            blit_c(screen, txt(side, LAB_DIM), 214, 62)
            blit_c(screen, txt(">>>", ACCENT, 3), 290 + k, 80)
        else:
            blit_c(screen, txt(side, LAB_DIM), 214, 62)
            blit_c(screen, txt("<<<", ACCENT, 3), 132 - k, 80)

        # the sensor readout
        x0, y0, w = 140, 112, 150
        screen.blit(txt("SALIVA SENSOR", LAB_DIM), (x0, y0 - 8))
        pygame.draw.rect(screen, (20, 12, 28), (x0 - 1, y0 - 1, w + 2, 9))
        pygame.draw.rect(screen, rgb(LAB_FLOOR), (x0, y0, w, 7))
        if jar.live:
            k = max(0.0, min(1.0, jar.diff / (jar.threshold * 3)))
            pygame.draw.rect(screen, rgb(SPIT_COL), (x0, y0, round(w * k), 7))
            tick = x0 + w // 3
            pygame.draw.line(screen, rgb(ACCENT), (tick, y0 - 2), (tick, y0 + 8))
        status, col = self._sensor_status()
        if status:
            screen.blit(txt(status, col), (x0, y0 + 12))
        left = max(0, int(SPIT_TIMEOUT - self.phase_t))
        if self.malfunction:
            self._draw_malfunction(screen)
        elif left < 30:
            screen.blit(txt(f"SAMPLE WINDOW CLOSES IN {left}", "#ff6a6a"), (x0, y0 + 22))

    def _draw_malfunction(self, screen: pygame.Surface) -> None:
        """SENSOR MALFUNCTION DETECTED, over the sensor readout, with the hold bar."""
        panel = pygame.Rect(124, 96, W - 130, 72)
        pygame.draw.rect(screen, (20, 12, 28), panel.inflate(4, 4))
        pygame.draw.rect(screen, rgb(PHOS_BG), panel)
        pygame.draw.rect(screen, rgb(PHOS_DIM), panel, 1)
        blink = int(self.time * 3) % 2 == 0
        first, *rest = MALFUNCTION_LINES
        y = panel.y + 5
        screen.blit(txt(first, "#ff6a6a" if blink else PHOS), (panel.x + 5, y))
        y += 12
        for line in rest:
            for part in wrap(line, panel.w - 10):
                screen.blit(txt(part, PHOS if part is not rest[-1] else ACCENT), (panel.x + 5, y))
                y += 9
            y += 3
        k = 0.0 if self.hair_hold is None else min(1.0, self.hair_hold / HAIR_HOLD)
        bar = pygame.Rect(panel.x + 5, panel.bottom - 9, panel.w - 10, 4)
        pygame.draw.rect(screen, rgb(PHOS_DIM), bar, 1)
        if k:
            pygame.draw.rect(screen, rgb(ACCENT), (bar.x, bar.y, round(bar.w * k), bar.h))

    def _sensor_status(self) -> tuple[str, str]:
        jar = self.jar
        blink = int(self.time * 3) % 2 == 0
        if not jar.live:
            return ("NO SENSOR: PRESS BUTTON TO SPIT", ACCENT if blink else LAB_DIM)
        if jar.state == "CHANGING":
            return ("SOMETHING IS HAPPENING...", ACCENT if blink else LAB_TEXT)
        if jar.state == "IDLE":
            return ("READY. AIM FOR THE JAR.", LAB_TEXT)
        if jar.state == "RESET":
            return ("PUT THE JAR BACK ON THE SCALE.", "#ff6a6a" if blink else LAB_DIM)
        if jar.state == "START":
            return ("CALIBRATING. DON'T TOUCH THE JAR.", LAB_DIM)
        if self.not_ready_t > FALLBACK_AFTER:
            return ("SENSOR TROUBLE: PRESS BUTTON TO SPIT", ACCENT if blink else LAB_DIM)
        return ("SENSOR TROUBLE. HOLD ON...", "#ff6a6a")

    def _draw_got(self, screen: pygame.Surface) -> None:
        draw_jar(screen, 70, FLOOR_Y, 0.5 + 0.1 * math.sin(self.phase_t * 20) * max(0, 1 - self.phase_t), self.time)
        for x, y, *_ in self.splash:
            pygame.draw.rect(screen, rgb(SPIT_COL), (round(x) - 1, round(y) - 1, 3, 3))
        k = min(1.0, self.phase_t / 0.25)
        img = txt("SAMPLE RECEIVED!", ACCENT, 2)
        img = pygame.transform.scale_by(img, 0.5 + 0.5 * k) if k < 1 else img
        blit_c(screen, img, 214, 60)
        if self.phase_t > 0.6:
            blit_c(screen, txt(f"VOLUME: {volume_word(self.delta, self.hair)}", LAB_TEXT), 214, 80)
        if self.phase_t > 1.6:
            blit_c(screen, txt("THANK YOU FOR YOUR SERVICE.", LAB_DIM), 214, 92)

    def _draw_analyze(self, screen: pygame.Surface) -> None:
        t = self.phase_t
        panel = pygame.Rect(6, 6, 196, 150)
        pygame.draw.rect(screen, (20, 12, 28), panel.inflate(4, 4))
        pygame.draw.rect(screen, rgb(PHOS_BG), panel)
        screen.blit(txt(f"DNA ANALYSIS - SAMPLE NO. {self.sample_no}", PHOS_DIM), (panel.x + 4, panel.y + 4))
        pygame.draw.line(screen, rgb(PHOS_DIM), (panel.x + 4, panel.y + 12), (panel.right - 5, panel.y + 12))
        y = panel.y + 17
        seq_live = False
        for text, start, suffix, work in self._analysis():
            if t < start:
                break
            typed = int((t - start) * TYPE_RATE)
            line = text[:typed]
            if typed >= len(text):
                into = t - start - len(text) / TYPE_RATE
                if into < work:
                    line += "." * (int(into * 6) % 4)
                    seq_live = text.startswith("SEQUENCING")
                else:
                    line += suffix
            for part in wrap(line, panel.w - 8) or [""]:     # a long one carries on underneath
                screen.blit(txt(part, PHOS), (panel.x + 4, y))
                y += 9
            if seq_live and text.startswith("SEQUENCING"):
                rnd = random.Random(int(t * 20))
                bases = "".join(rnd.choice("ACGT") for _ in range(40))
                x = panel.x + 8
                for b in bases:
                    screen.blit(txt(b, BASE_COLS[b]), (x, y))
                    x += 4
                y += 9
        if int(self.time * 2.5) % 2 == 0:
            pygame.draw.rect(screen, rgb(PHOS), (panel.x + 4, min(y, panel.bottom - 8), 3, 5))

        # the helix spins faster as it works
        k = min(1.0, t / max(0.1, self.analysis_time))
        draw_helix(screen, 260, 14, 150, self.time, speed=2 + 8 * k * (1 - k) * 4, radius=18)
        # progress
        x0, y0, w = 6, 164, 308
        pygame.draw.rect(screen, (20, 12, 28), (x0 - 1, y0 - 1, w + 2, 9))
        pygame.draw.rect(screen, rgb(PHOS_BG), (x0, y0, w, 7))
        shown = min(0.99 if not self.ready else 1.0, k)
        pygame.draw.rect(screen, rgb(PHOS_DIM), (x0, y0, round(w * shown), 7))
        label = txt(f"SEQUENCING {int(shown * 100)}%", PHOS)
        blit_c(screen, label, W / 2, y0 + 4)

    def _draw_survey(self, screen: pygame.Surface) -> None:
        sv = self.survey
        panel = pygame.Rect(6, 6, W - 12, H - 12)
        pygame.draw.rect(screen, (20, 12, 28), panel.inflate(4, 4))
        pygame.draw.rect(screen, rgb(PHOS_BG), panel)
        screen.blit(txt(f"DNA ANALYSIS - SAMPLE NO. {self.sample_no}", PHOS_DIM), (panel.x + 4, panel.y + 4))
        pygame.draw.line(screen, rgb(PHOS_DIM), (panel.x + 4, panel.y + 12), (panel.right - 5, panel.y + 12))
        blit_c(screen, txt("TO IMPROVE OUR ANALYSIS, PLEASE COMPLETE", PHOS), W / 2, 25)
        blit_c(screen, txt("THIS BEHAVIORAL ANALYSIS SURVEY.", PHOS), W / 2, 33)
        bob = int(self.time * 4) % 2
        for i, (question, options) in enumerate(dna.SURVEY):
            y = 50 + i * 28
            here = i == sv.q
            screen.blit(txt(f"{i + 1}. {question}", PHOS if here else PHOS_DIM), (20, y + 3))
            box = pygame.Rect(150, y - 4, 140, 20)
            col = dna.COLORS[sv.picks[i]][1] if i == 2 else PHOS     # the colour question shows the colour
            img = txt(options[sv.picks[i]], col if here else PHOS_DIM if i != 2 else col, 2)
            dx = 0
            if here:
                pygame.draw.rect(screen, rgb(PHOS), box, 1)
                for k in range(4):                        # arrows either side: sideways slides the answer
                    pygame.draw.rect(screen, rgb(PHOS), (box.x - 6 - bob + k, box.centery - k, 1, 2 * k + 1))
                    pygame.draw.rect(screen, rgb(PHOS), (box.right + 5 + bob - k, box.centery - k, 1, 2 * k + 1))
                k = min(1.0, sv.slide_t / 0.15)
                dx = round(sv.slide * 24 * (1 - k))       # the new answer slides in from the side it came
            clip = screen.get_clip()
            screen.set_clip(box.inflate(-2, -2))
            blit_c(screen, img, box.centerx + dx, box.centery)
            screen.set_clip(clip)
        blit_c(screen, txt("STICK LEFT / RIGHT: CHANGE ANSWER    UP / DOWN: QUESTION", PHOS_DIM), W / 2, H - 30)
        submit = txt("HOLD ANY BUTTON TO SUBMIT YOUR ANSWERS", PHOS)
        if int(self.time * 2.5) % 2 == 0 or sv.hold_k > 0:
            blit_c(screen, submit, W / 2, H - 18)
        if sv.hold_k > 0:                                 # holding: a bar fills up to handing it in
            x0, w = W // 2 - submit.get_width() // 2, submit.get_width()
            pygame.draw.rect(screen, rgb(PHOS_DIM), (x0, H - 12, w, 2))
            pygame.draw.rect(screen, (234, 255, 234), (x0, H - 12, round(w * sv.hold_k), 2))

    def _draw_report(self, screen: pygame.Surface) -> None:
        sp, t = self._surfaces(), self.phase_t
        blit_c(screen, txt("GENETIC REPORT", ACCENT, 2), W / 2, 12)
        blit_c(screen, txt(f"SAMPLE NO. {self.sample_no}  -  {len(self.profile)} MATCHES", LAB_DIM), W / 2, 26)
        n = len(self.profile)
        col = W / n
        for i, s in enumerate(self.profile):
            u = t - i * REPORT_STEP
            if u < 0:
                break
            cx = col * i + col / 2
            pop = min(1.0, u / 0.3)
            frames = sp["donors"][s.species]
            img = frames[int(self.time * 4) % len(frames)]
            if pop < 1:
                img = pygame.transform.scale_by(img, 0.4 + 0.6 * pop)
            blit_c(screen, img, cx, 62)
            pct = round(s.pct * min(1.0, u / 0.8))
            blit_c(screen, txt(f"{pct}%", ACCENT, 2), cx, 96)
            name = txt(s.nick, LAB_TEXT)
            if name.get_width() > col - 4:
                name = txt(s.nick.split()[-1], LAB_TEXT)
            blit_c(screen, name, cx, 108)
            bw = col - 14
            pygame.draw.rect(screen, rgb(LAB_FLOOR), (cx - bw / 2, 114, bw, 4))
            pygame.draw.rect(screen, rgb(SPIT_COL), (cx - bw / 2, 114, round(bw * pct / 100), 4))

        # the caption: each species' diagnosis as it lands, then the verdict
        if t < self.report_time + 0.3:
            i = min(n - 1, int(t / REPORT_STEP))
            s = self.profile[i]
            if t - i * REPORT_STEP > 0.5:
                for j, line in enumerate(wrap(f"{s.nick}: {s.diagnosis}", 300)):
                    blit_c(screen, txt(line, LAB_TEXT), W / 2, 136 + j * 8)
        else:
            u = t - self.report_time - 0.3
            full = dna.sentence(self.profile)
            shown = full[:int(u * TYPE_RATE)]
            lines = wrap(full, 300)
            done = 0
            for j, line in enumerate(lines):
                part = shown[done:done + len(line)]
                done += len(line) + 1
                if part:                                     # typed left to right, where the whole line will sit
                    screen.blit(txt(part, ACCENT), (round(W / 2 - text_width(line) / 2), 130 + j * 9))
            if u > len(full) / TYPE_RATE + 0.5 and int(self.time * 2.5) % 2 == 0:
                blit_c(screen, txt("BUTTON: SPLICE ME", LAB_DIM), W / 2, 170)

    def _draw_splice(self, screen: pygame.Surface) -> None:
        sp, t, you = self._surfaces(), self.phase_t, self.you
        cx, cy = W / 2, 92
        n = len(self.profile)
        if t < SWIRL_TIME:
            # the donors leave their columns and spin together
            k = t / SWIRL_TIME
            col = W / n
            for i, s in enumerate(self.profile):
                a = i / n * math.tau + k * k * 14
                r = 70 * (1 - k) ** 1.5
                hx, hy = col * i + col / 2, 62
                x = hx + (cx + math.cos(a) * r - hx) * min(1.0, k * 3)
                y = hy + (cy + math.sin(a) * r * 0.6 - hy) * min(1.0, k * 3)
                frames = sp["donors"][s.species]
                img = pygame.transform.scale_by(frames[0], 1 - 0.6 * k)
                blit_c(screen, img, x, y)
            draw_helix(screen, round(cx), 20, 160, self.time, speed=4 + 20 * k, radius=round(10 + 30 * k))
            blit_c(screen, txt("SPLICING...", ACCENT, 2), W / 2, 12)
            return
        t -= SWIRL_TIME
        if t < FLASH_TIME:
            screen.fill((255, 255, 255))
            return
        t -= FLASH_TIME
        steps = sp["steps"]
        bottom = FLOOR_Y + 2
        if t < SCAN_TIME:
            # print the new body from the feet up
            img = steps[0][int(self.time * 4) % 4]
            h = img.get_height()
            k = min(1.0, t / (SCAN_TIME * 0.75))
            shown = round(h * k)
            x, y = cx - img.get_width() / 2, bottom - h
            screen.blit(img, (x, y + h - shown), (0, h - shown, img.get_width(), shown))
            sy = y + h - shown
            if k < 1:
                pygame.draw.line(screen, rgb(PHOS), (x - 6, sy), (x + img.get_width() + 6, sy), 2)
            blit_c(screen, txt("ASSEMBLING YOU", ACCENT, 2), W / 2, 12)
            return
        t -= SCAN_TIME
        i = min(len(you.mutations), int(t / ZAP_TIME) + 1) if you.mutations else 0
        u = t - (i - 1) * ZAP_TIME if i else 99
        step = i if u > 0.35 else i - 1
        img = steps[max(0, step)][int(self.time * 4) % 4]
        x, y = cx - img.get_width() / 2, bottom - img.get_height()
        if i and u < 0.35:                                   # lightning
            rnd = random.Random(int(self.time * 30))
            px, py = cx + rnd.uniform(-40, 40), 0
            while py < y + 40:
                nx, ny = cx + rnd.uniform(-20, 20), py + rnd.uniform(10, 22)
                pygame.draw.line(screen, (255, 255, 200), (px, py), (nx, ny), 2)
                px, py = nx, ny
            if int(self.time * 30) % 2:
                img = img.copy()
                img.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
        screen.blit(img, (x, y))
        if i:
            pop = min(1.0, u / 0.2)
            head = txt("MUTATION!", "#ff6a6a", 2)
            blit_c(screen, pygame.transform.scale_by(head, 0.5 + 0.5 * pop) if pop < 1 else head, W / 2, 12)
            blit_c(screen, txt(you.mutations[i - 1].label, ACCENT), W / 2, 28)
        else:
            blit_c(screen, txt("ASSEMBLING YOU", ACCENT, 2), W / 2, 12)

    def _draw_reveal(self, screen: pygame.Surface) -> None:
        sp, a, you = self._surfaces(), self.actor, self.you
        if self.color:                                       # the room comes up in their favourite colour
            wash = pygame.Surface((W, H))
            wash.fill(rgb(self.color))
            wash.set_alpha(ROOM_WASH)
            screen.blit(wash, (0, 0))
        # the way out, into the simulation
        door = pygame.Rect(W - 34, FLOOR_Y - 62, 30, 62)
        pygame.draw.rect(screen, (20, 12, 28), door.inflate(4, 4))
        pygame.draw.rect(screen, (40, 30, 70), door)
        pygame.draw.rect(screen, (90, 78, 130), door, 1)
        for j, word in enumerate(("ENTER", "SIMULATION")):         # right-aligned: too wide to centre on the door
            sign = txt(word, PHOS)
            pad = pygame.Rect(W - 4 - sign.get_width() - 2, door.y - 21 + j * 9, sign.get_width() + 4, 9)
            pygame.draw.rect(screen, (20, 12, 28), pad)
            screen.blit(sign, (pad.x + 2, pad.y + 1))
        if self.phase_t > 1.5:                                   # walk this way
            draw_arrow(screen, door.x - 8 + round(4 * math.sin(self.time * 8)), door.centery + 6)

        frames = sp["final"][a.state][a.facing]
        img = frames[min(a.frame, len(frames) - 1)]
        top = FLOOR_Y + 2 - img.get_height() - round(a.height)
        screen.blit(img, (round(self.ax - img.get_width() / 2), top))
        if self.color and self.phase_t > 0.6:
            self._bubble(screen, "NICE COLOR CHOICE!", self.ax, top + 14)

        blit_c(screen, txt("THIS IS YOU.", ACCENT, 2), W / 2, 12)
        blit_c(screen, txt(f"SPECIMEN: {you.name}", LAB_TEXT), W / 2, 27)
        for j, line in enumerate(wrap(dna.sentence(self.profile), 300)):
            blit_c(screen, txt(line, LAB_TEXT), W / 2, 37 + j * 8)       # (bright: the room may be any colour)
        if self.phase_t > 1.5:
            hint = txt("STICK: WALK  UP: JUMP  BUTTON: ATTACK", LAB_DIM)
            blit_c(screen, hint, W / 2, H - 7)

    def _bubble(self, screen: pygame.Surface, text: str, x: float, y: float) -> None:
        """A speech bubble whose tail points down at (x, y)."""
        label = txt(text, "#1b1430")
        w, h = label.get_width() + 10, 13
        bx = round(max(4, min(W - 4 - w, x - w / 2)))
        by = round(y - 6 - h + 2 * math.sin(self.time * 3))
        tip = (round(x), by + h + 5)
        pygame.draw.polygon(screen, (20, 12, 28), [(tip[0] - 4, by + h - 1), (tip[0] + 4, by + h - 1), tip])
        pygame.draw.rect(screen, (20, 12, 28), (bx - 1, by - 1, w + 2, h + 2), border_radius=4)
        pygame.draw.rect(screen, (250, 246, 230), (bx, by, w, h), border_radius=3)
        pygame.draw.polygon(screen, (250, 246, 230), [(tip[0] - 3, by + h - 1), (tip[0] + 3, by + h - 1),
                                                      (tip[0], tip[1] - 1)])
        screen.blit(label, (bx + 5, by + 4))

    def _draw_nospit(self, screen: pygame.Surface) -> None:
        draw_jar(screen, 70, FLOOR_Y, 0.0, self.time)
        blit_c(screen, txt("NO SAMPLE.", "#ff6a6a", 2), 214, 50)
        blit_c(screen, txt("THE JAR IS DISAPPOINTED IN YOU.", LAB_TEXT), 214, 70)
        if self.phase_t > 1 and int(self.time * 2.5) % 2 == 0:
            blit_c(screen, txt("BUTTON: CONTINUE", LAB_DIM), 214, 90)


# -- demo / test driver -----------------------------------------------------------------
def autopilot(game: SpitKit) -> Input:
    if game.phase == "reveal":
        return Input(x=1 if game.phase_t > 2 else 0, action=0.8 < game.phase_t < 0.85)
    tick = int(game.time * 60)
    press = tick % 40 == 0
    if game.phase == "spit":
        press = game.phase_t > 1.5 and tick % 20 == 0
    if game.phase == "analyze":
        press = False
    if game.phase == "survey":                    # slide an answer or two along, then hold the button
        roll = tick % 20 == 10 and game.phase_t < 1.5
        hold = game.phase_t > 2.0
        return Input(x=1 if roll else 0, action=hold and game.survey.press is None, held=hold)
    return Input(action=press, players=(Input(action=press),))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--demo", action="store_true", help="let the computer play (keyboard spit)")
    ap.add_argument("--seed", type=int, help="same seed, same DNA")
    ap.add_argument("--skip-title", action="store_true")
    ap.add_argument("--ticks", type=int, help="quit after this many frames (testing)")
    ap.add_argument("--screenshot", help="save the last frame here (with --ticks)")
    args = ap.parse_args()
    run(lambda: SpitKit(seed=args.seed, show_title=not args.skip_title), "Spit Kit", scale=args.scale,
        fullscreen=args.fullscreen, autopilot=autopilot if args.demo else None,
        max_ticks=args.ticks, screenshot=args.screenshot)


if __name__ == "__main__":
    main()
