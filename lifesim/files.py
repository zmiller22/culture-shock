"""The lab's file drawer: a little file browser on the mainframe's CRT.

Pick C:/> FILES off the theory menu and the CRT turns into a file system full
of what the lab would rather you didn't read: notebooks, incident reports, and
photos of experiments that went wrong. Some files are locked. Their 3-letter
codes are hidden around the room (masking tape, a sticky note, the wall, the
floor), and one notebook gives up another.

It's all stick-and-button, like the visitor name entry:

    on the CODE row   button starts typing; up / down roll the letter, button or
                      right locks it in, left backs up. Three letters and it runs:
                      a hidden code unlocks its file, anything else searches names
    on a file         button opens it; left (or the BACK row) leaves

The two .VID files rick roll you, and they're the one place the game drops the
pixels: the video plays at the window's full resolution with sound, from media
you supply in assets/files/ (it isn't shipped with the game, see the README
there). Missing media gets a TAPE MISSING screen instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pygame

from sprites.font import text_width

from .art import CRT_BG, PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT, SCREEN

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MEDIA_DIR = ASSETS / "files"
MEDIA_NAME = "rickroll"
AUDIO_EXTS = (".ogg", ".mp3", ".wav")
VIDEO_EXTS = (".gif", ".png", ".jpg", ".jpeg", ".webp")
SILENT_ROLL = 20.0          # s a picture-only roll runs, with no audio to say when it's over
ROLL_GRACE = 0.6            # s before we trust mixer.music.get_busy() to mean "finished"
FLASH_TIME = 2.2            # s a status message stays up
REPEAT = (0.4, 0.09)        # s before a held stick repeats, then s per step
BRIGHT = "#eaffea"
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
LIST_Y, ROW_H, LIST_ROWS = 30, 8, 7


@dataclass
class LabFile:
    name: str
    kind: str                       # "txt", "img" or "roll"
    lines: tuple[str, ...] = ()     # txt: the text. img: a caption under the photo
    sprite: str = ""                # img: assets/sprites/<sprite>.png, first frame
    code: str | None = None         # locked until someone types this


FILES = [
    LabFile("WATCH_IF_YOU_ARE_ROLLING.VID", "roll"),
    LabFile("WATCH_IF_YOU_ARE_NOT_ROLLING.VID", "roll"),
    LabFile("NOTEBOOK_001.TXT", "txt", (
        "DAY 1. THE STORK IS LOOSE IN",
        "THE VENTS. THE DIRECTOR SAYS",
        "THIS IS FINE. IT IS NOT FINE.",
        "",
        "DAY 2. FOUND A BABY IN THE",
        "BREAKROOM. NOT OURS. PROBABLY.",
        "",
        "DAY 3. THE STORK HAS A UNION.",
    )),
    LabFile("NOTEBOOK_002.TXT", "txt", (
        "SOUP TRIAL 41. ADDED LIGHTNING.",
        "SOUP TWITCHED.",
        "",
        "SOUP TRIAL 42. MORE LIGHTNING.",
        "SOUP SAT UP.",
        "",
        "SOUP TRIAL 43. SOUP HAS ASKED",
        "FOR A LAWYER. PAUSING TRIALS.",
    )),
    LabFile("INCIDENT_REPORT_88.TXT", "txt", (
        "NATURE OF INCIDENT: RAVE.",
        "LOCATION: INSIDE A WOMB.",
        "",
        "THE NEIGHBOURS REPORT A BASS",
        "LINE AT 3 AM FOR NINE MONTHS.",
        "",
        "ACTION TAKEN: NONE. THE DJ IS",
        "AN UNBORN CHILD. NO JURISDICTION.",
    )),
    LabFile("EXPERIMENT_2.IMG", "img", ("SUBJECT 2. BANANA + LOBSTER.", "WE ARE SO SORRY."),
            sprite="kronenberg_002_banaclaw"),
    LabFile("EXPERIMENT_3.IMG", "img", ("SUBJECT 3. IT KNOWS OUR NAMES.", "DO NOT LET IT READ."),
            sprite="kronenberg_003_brainpus", code="BRN"),
    LabFile("MEMO_FROM_STORK.TXT", "txt", (
        "TO: THE LAB",
        "FROM: THE STORK",
        "",
        "I DO NOT DELIVER BABIES. I HAVE",
        "NEVER DELIVERED BABIES. I WAS",
        "DELIVERING SANDWICHES AND YOU",
        "KEPT HANDING ME BABIES.",
        "",
        "I QUIT.",
    ), code="STK"),
    LabFile("SOUP_RECIPE.TXT", "txt", (
        "PRIMORDIAL SOUP. SERVES 1 PLANET.",
        "",
        "1 OCEAN, WARM",
        "A PINCH OF AMINO ACIDS",
        "LIGHTNING TO TASTE",
        "",
        "SIMMER 500 MILLION YEARS.",
        "DO NOT LET IT SIT UP.",
    ), code="SUP"),
    LabFile("NOTEBOOK_000.TXT", "txt", (
        "FIRST ENTRY. WE FILE THE BAD ONES",
        "UNDER CODES SO THE DIRECTOR",
        "CAN'T FIND THEM.",
        "",
        "THE BIG HAIRY ONE IS FILED UNDER",
        "S-Q-B. IT IS NOT A PERSON. IT",
        "WOULD LIKE YOU TO KNOW IT IS",
        "NOT A PERSON.",
    ), code="RKR"),
    LabFile("EXPERIMENT_6.IMG", "img", ("SUBJECT 6. HE SAYS HE'S FINE.", "HE IS DEFINITELY NOT FINE."),
            sprite="kronenberg_006_squatchbro", code="SQB"),
]

# what the terminal says after a roll, by (which file, were you already rolling)
AFTER_ROLL = {
    ("WATCH_IF_YOU_ARE_NOT_ROLLING.VID", False): ["PLAYBACK COMPLETE.", "", "YOU ARE NOW ROLLING!", "",
                                                  "NOW OPEN", "WATCH_IF_YOU_ARE_ROLLING"],
    ("WATCH_IF_YOU_ARE_NOT_ROLLING.VID", True): ["PLAYBACK COMPLETE.", "", "YOU WERE ALREADY ROLLING.",
                                                 "YOU ARE NOW ROLLING HARDER.", "", "NOW OPEN",
                                                 "WATCH_IF_YOU_ARE_ROLLING"],
    ("WATCH_IF_YOU_ARE_ROLLING.VID", True): ["PLAYBACK COMPLETE.", "", "YOU ARE ROLLING.", "KEEP ROLLING.",
                                             "THE LAB THANKS YOU", "FOR ROLLING."],
    ("WATCH_IF_YOU_ARE_ROLLING.VID", False): ["PLAYBACK COMPLETE.", "", "YOU WERE NOT ROLLING.",
                                              "THAT WAS THE WRONG FILE.", "", "NOW OPEN",
                                              "WATCH_IF_YOU_ARE_NOT_ROLLING"],
}
TAPE_MISSING = ["TAPE MISSING.", "", "THE REEL FOR THIS FILE IS NOT", "ON THE DRIVE. PUT A VIDEO OR",
                "GIF AND A SONG IN ASSETS/FILES", "NAMED RICKROLL. THEN ROLL."]


def rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _find(exts: tuple[str, ...]) -> Path | None:
    for ext in exts:
        p = MEDIA_DIR / f"{MEDIA_NAME}{ext}"
        if p.exists():
            return p
    return None


class Media:
    """The rick roll: frames (with their delays) and a song, all optional, loaded on first use."""

    def __init__(self) -> None:
        self.loaded = False
        self.frames: list[tuple[pygame.Surface, float]] = []
        self.length = 0.0
        self.audio: Path | None = None
        self.scaled: dict[tuple[int, tuple[int, int]], tuple[pygame.Surface, tuple[int, int]]] = {}

    def load(self) -> None:
        if self.loaded:
            return
        self.loaded = True
        self.audio = _find(AUDIO_EXTS)
        pic = _find(VIDEO_EXTS)
        if pic:
            try:
                anim = pygame.image.load_animation(str(pic))
                self.frames = [(s, max(0.02, ms / 1000) if ms else 0.1) for s, ms in anim]
            except (pygame.error, AttributeError):
                self.frames = [(pygame.image.load(str(pic)), 0.1)]
        self.length = sum(d for _, d in self.frames)

    @property
    def missing(self) -> bool:
        return not self.frames and not self.audio

    def frame(self, t: float) -> int:
        if len(self.frames) < 2:
            return 0
        t %= self.length
        for i, (_, d) in enumerate(self.frames):
            if t < d:
                return i
            t -= d
        return 0

    def blit(self, window: pygame.Surface, t: float) -> None:
        """Draw the frame for time t, smooth-scaled to fit the whole window. No pixels here."""
        size = window.get_size()
        window.fill((0, 0, 0))
        if not self.frames:
            return
        i = self.frame(t)
        key = (i, size)
        if key not in self.scaled:
            src = self.frames[i][0]
            k = min(size[0] / src.get_width(), size[1] / src.get_height())
            w, h = max(1, round(src.get_width() * k)), max(1, round(src.get_height() * k))
            img = pygame.transform.smoothscale(src.convert_alpha() if src.get_alpha() else src.convert(), (w, h))
            self.scaled[key] = (img, ((size[0] - w) // 2, (size[1] - h) // 2))
        img, pos = self.scaled[key]
        window.blit(img, pos)


class Stick:
    """Edge-triggered stick presses that repeat when held."""

    def __init__(self) -> None:
        self.held = (0, 0)
        self.t = 0.0

    def step(self, dt: float, x: int, y: int) -> tuple[int, int]:
        d = (x, y)
        if d == (0, 0):
            self.held = d
            return 0, 0
        if d != self.held:
            self.held, self.t = d, 0.0
            return d
        self.t += dt
        if self.t > REPEAT[0]:
            self.t -= REPEAT[1]
            return 0, y               # only up / down repeat: left / right are one-shot
        return 0, 0


class FileTerminal:
    """The file browser. LifeSim hands it ticks while it's open and asks it to
    paint the CRT; it says `closed` when the visitor backs out."""

    def __init__(self, mute: bool = False, log: Callable[..., None] | None = None) -> None:
        self.mute = mute
        self.log = log or (lambda event, **data: None)      # the activity log (see activity.py)
        self.unlocked: set[str] = set()
        self.rolling = False            # have they watched WATCH_IF_YOU_ARE_NOT_ROLLING yet
        self.media = Media()
        self.photos: dict[str, pygame.Surface] = {}
        self.open()

    # -- state ---------------------------------------------------------------------------
    def open(self) -> None:
        self.mode = "list"              # list, code, txt, img, roll, msg
        self.sel = 1 if self.rows()[1:] else 0
        self.scroll = 0
        self.code = ""
        self.letter = 0
        self.flash = ("", 0.0)
        self.viewing: LabFile | None = None
        self.msg: list[str] = []
        self.roll_t = 0.0
        self.closed = False
        self.stick = Stick()

    def visible(self) -> list[LabFile]:
        return [f for f in FILES if f.code is None or f.code in self.unlocked]

    def locked(self) -> int:
        return sum(1 for f in FILES if f.code and f.code not in self.unlocked)

    def rows(self) -> list[LabFile | str]:
        """The rows of the list: the code entry, the files, then BACK."""
        return ["CODE", *self.visible(), "BACK"]

    def shown(self) -> list[LabFile | str]:
        """What the list draws under the code row: the files, the locked count, BACK."""
        return [*self.visible(), *(["LOCKED"] if self.locked() else []), "BACK"]

    def _follow(self) -> None:
        """Scroll so the selected row is on screen."""
        row = self.rows()[self.sel]
        if row == "CODE":
            return
        i = self.shown().index(row)
        self.scroll = max(0, min(self.scroll, i), i - LIST_ROWS + 1)

    @property
    def playing(self) -> bool:
        return self.mode == "roll"

    def _say(self, s: str) -> None:
        self.flash = (s, FLASH_TIME)

    def update(self, dt: float, inp) -> None:
        sx, sy = self.stick.step(dt, inp.x, inp.y)
        self.flash = (self.flash[0], self.flash[1] - dt)
        getattr(self, f"_update_{self.mode}")(dt, sx, sy, inp.action)

    def _update_list(self, dt: float, sx: int, sy: int, act: bool) -> None:
        rows = self.rows()
        if sy:
            self.sel = (self.sel + sy) % len(rows)
        self._follow()
        if sx < 0:
            self.closed = True
        elif act:
            row = rows[self.sel]
            if row == "CODE":
                self.mode, self.code, self.letter = "code", "", 0
            elif row == "BACK":
                self.closed = True
            else:
                self._open_file(row, "list")

    def _update_code(self, dt: float, sx: int, sy: int, act: bool) -> None:
        if sy:
            self.letter = (self.letter - sy) % len(LETTERS)      # up goes A -> B
        if sx < 0:
            if self.code:
                self.letter = LETTERS.index(self.code[-1])
                self.code = self.code[:-1]
            else:
                self.mode = "list"
        elif act or sx > 0:
            self.code += LETTERS[self.letter]
            if len(self.code) == 3:
                self._run_code(self.code)

    def _run_code(self, code: str) -> None:
        self.mode = "list"
        hidden = next((f for f in FILES if f.code == code), None)
        if hidden:
            new = code not in self.unlocked
            self.unlocked.add(code)
            self.sel = self.rows().index(hidden)
            self._follow()
            self._say("ACCESS GRANTED" if new else "ALREADY OPEN")
            self.log("code", code=code, result="unlocked" if new else "already", file=hidden.name)
            self._open_file(hidden, "code")
            return
        hits = [i for i, f in enumerate(self.rows()) if isinstance(f, LabFile) and code in f.name.replace("_", "")]
        self.log("code", code=code, result="found" if hits else "miss")
        if hits:
            self.sel = hits[0]
            self._follow()
            self._say(f"FOUND {len(hits)}: {code}")
        else:
            self._say(f"NO MATCH: {code}")

    def _open_file(self, f: LabFile, via: str) -> None:
        self.viewing = f
        self.log("file_open", file=f.name, via=via)
        if f.kind == "roll":
            self.media.load()
            if self.media.missing:
                self.mode, self.msg = "msg", TAPE_MISSING
                return
            self.mode, self.roll_t = "roll", 0.0
            if self.media.audio and not self.mute:
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(str(self.media.audio))
                    pygame.mixer.music.play()
                except pygame.error:
                    self.media.audio = None
        else:
            self.mode = f.kind

    def _update_txt(self, dt: float, sx: int, sy: int, act: bool) -> None:
        if act or sx < 0:
            self.mode = "list"

    _update_img = _update_txt

    def _update_msg(self, dt: float, sx: int, sy: int, act: bool) -> None:
        nxt = self._next_file()
        if act and nxt:                      # straight into the file it's telling you to open
            self._open_file(nxt, "next")
        elif act or sx < 0:
            self.mode = "list"

    def _next_file(self) -> LabFile | None:
        """The file a message ends by telling you to open ("NOW OPEN" then its name), if any."""
        if len(self.msg) >= 2 and self.msg[-2] == "NOW OPEN":
            return next((f for f in FILES if f.name == self.msg[-1] + ".VID"), None)
        return None

    def _update_roll(self, dt: float, sx: int, sy: int, act: bool) -> None:
        self.roll_t += dt
        music = self.media.audio and not self.mute and pygame.mixer.get_init()
        if music:
            over = self.roll_t > ROLL_GRACE and not pygame.mixer.music.get_busy()
        else:
            over = self.roll_t > SILENT_ROLL
        if act or sx < 0 or over:            # you can bail out of a rick roll. it still counts
            if music:
                pygame.mixer.music.fadeout(400)
            name = self.viewing.name
            self.log("roll_end", file=name, bailed=not over, secs=round(self.roll_t, 1))
            self.msg = AFTER_ROLL[(name, self.rolling)]
            if name.startswith("WATCH_IF_YOU_ARE_NOT"):
                self.rolling = True
            self.mode = "msg"

    # -- drawing ---------------------------------------------------------------------------
    def overlay(self, window: pygame.Surface) -> None:
        if self.mode == "roll":
            self.media.blit(window, self.roll_t)

    def draw(self, crt: pygame.Surface, text, time: float) -> None:
        sw, sh = SCREEN[2], SCREEN[3]
        if self.mode in ("list", "code"):
            self._header(crt, text, "LIFE LAB FILE SYSTEM", "/LAB/FILES")
            self._draw_list(crt, text, time)
        elif self.mode == "txt":
            self._header(crt, text, self.viewing.name)
            for i, line in enumerate(self.viewing.lines):
                if line:
                    crt.blit(text.get(line, PHOSPHOR), (4, 15 + i * 8))
            crt.blit(text.get("BUTTON: BACK", PHOSPHOR_FAINT), (4, 94))
        elif self.mode == "img":
            self._header(crt, text, self.viewing.name)
            photo = self._photo(self.viewing.sprite)
            crt.blit(photo, (sw // 2 - photo.get_width() // 2, 14 + (64 - photo.get_height()) // 2))
            for i, line in enumerate(self.viewing.lines):
                s = text.get(line, PHOSPHOR_DIM)
                crt.blit(s, (sw // 2 - s.get_width() // 2, 81 + i * 7))
            crt.blit(text.get("BUTTON: BACK", PHOSPHOR_FAINT), (4, 97))
        elif self.mode == "msg":
            self._header(crt, text, "SESSION LOG")
            crt.blit(text.get(self.viewing.name.removesuffix(".VID"), PHOSPHOR_DIM), (4, 15))
            nxt = self._next_file()
            for i, line in enumerate(self.msg):
                y = 26 + i * 9
                if nxt and i == len(self.msg) - 1:          # the file to open next, as a blinking button
                    label = "> " + line
                    w = text_width(label) + 4
                    if int(time * 2.5) % 2 == 0:
                        crt.fill(rgb(PHOSPHOR), (4, y - 2, w, 9))
                        crt.blit(text.get(label, CRT_BG), (6, y))
                    else:
                        pygame.draw.rect(crt, rgb(PHOSPHOR), (4, y - 2, w, 9), 1)
                        crt.blit(text.get(label, PHOSPHOR), (6, y))
                    continue
                col = BRIGHT if "ROLLING!" in line or line == "TAPE MISSING." else PHOSPHOR
                if line:
                    crt.blit(text.get(line, col), (4, y))
            hint = "BUTTON: OPEN IT   LEFT: BACK" if nxt else "BUTTON: OK"
            crt.blit(text.get(hint, PHOSPHOR_FAINT), (4, 94))
        elif self.mode == "roll":                       # what the CRT shows behind the full-res video
            s = text.get("NOW ROLLING", PHOSPHOR)
            crt.blit(s, (sw // 2 - s.get_width() // 2, sh // 2 - 3))

    def _header(self, crt, text, left: str, right: str = "") -> None:
        sw = SCREEN[2]
        crt.blit(text.get(left, PHOSPHOR_DIM), (4, 3))
        if right:
            r = text.get(right, PHOSPHOR_DIM)
            crt.blit(r, (sw - 4 - r.get_width(), 3))
        crt.fill(rgb(PHOSPHOR_DIM), (4, 10, sw - 8, 1))

    def _draw_list(self, crt, text, time: float) -> None:
        sw = SCREEN[2]
        rows = self.rows()
        blink = int(time * 2.5) % 2 == 0
        # the code row: three boxes
        on = self.sel == 0
        crt.blit(text.get("CODE:", PHOSPHOR if on else PHOSPHOR_DIM), (4, 16))
        for i in range(3):
            bx = 28 + i * 9
            active = self.mode == "code" and i == len(self.code)
            col = PHOSPHOR if active or (on and self.mode == "list") else PHOSPHOR_DIM
            pygame.draw.rect(crt, rgb(col), (bx, 14, 7, 9), 1)
            if i < len(self.code):
                ch = self.code[i]
            elif active:
                ch = LETTERS[self.letter]
            else:
                ch = "_"
            crt.blit(text.get(ch, BRIGHT if active else PHOSPHOR if on else PHOSPHOR_DIM), (bx + 2, 16))
            if active:                                         # little up / down arrows
                crt.fill(rgb(PHOSPHOR), (bx + 3, 11, 1, 1))
                crt.fill(rgb(PHOSPHOR), (bx + 2, 12, 3, 1))
                crt.fill(rgb(PHOSPHOR), (bx + 2, 24, 3, 1))
                crt.fill(rgb(PHOSPHOR), (bx + 3, 25, 1, 1))
        msg, left = self.flash
        if left > 0:
            crt.blit(text.get(msg, BRIGHT), (60, 16))
        elif self.mode == "code":
            crt.blit(text.get("UP/DN: LETTER", PHOSPHOR_FAINT), (60, 16))
        elif on:
            crt.blit(text.get("BUTTON: TYPE A CODE", PHOSPHOR_FAINT), (60, 16))
        crt.fill(rgb(PHOSPHOR_FAINT), (4, 26, sw - 8, 1))

        # the files
        selected = self.rows()[self.sel] if self.mode == "list" else None
        shown = self.shown()
        for j, row in enumerate(shown[self.scroll:self.scroll + LIST_ROWS]):
            y = LIST_Y + j * ROW_H
            if row == "LOCKED":
                crt.blit(text.get(f"+ {self.locked()} FILES LOCKED", PHOSPHOR_FAINT), (6, y))
                continue
            label = "< BACK TO THEORIES" if row == "BACK" else row.name
            if row is selected:
                crt.fill(rgb(PHOSPHOR), (4, y - 1, sw - 8, 7))
                crt.blit(text.get(label, CRT_BG), (6, y))
            else:
                crt.blit(text.get(label, PHOSPHOR_DIM), (6, y))
        if self.scroll + LIST_ROWS < len(shown):
            crt.blit(text.get("+", PHOSPHOR_DIM), (sw - 8, LIST_Y + (LIST_ROWS - 1) * ROW_H))
        if self.scroll > 0:
            crt.blit(text.get("-", PHOSPHOR_DIM), (sw - 8, LIST_Y))
        crt.fill(rgb(PHOSPHOR_FAINT), (4, 88, sw - 8, 1))
        hint = "STICK: LETTER   LEFT: UNDO" if self.mode == "code" else "STICK: BROWSE   BUTTON: OPEN"
        crt.blit(text.get(hint, PHOSPHOR_FAINT), (4, 93))
        if blink:
            crt.fill(rgb(PHOSPHOR), (4 + text_width(hint) + 2, 93, 3, 5))

    def _photo(self, sprite: str) -> pygame.Surface:
        """An experiment photo: the first frame of a cast sprite, in three shades of phosphor."""
        if sprite not in self.photos:
            sheet = pygame.image.load(str(ASSETS / "sprites" / f"{sprite}.png"))
            frame = sheet.subsurface((0, 0, 48, 48)).copy()
            box = frame.get_bounding_rect()
            frame = frame.subsurface(box).copy()
            k = max(1, min(64 // box.h, 120 // box.w))
            out = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
            shades = [rgb(PHOSPHOR_FAINT), rgb(PHOSPHOR_DIM), rgb(PHOSPHOR), rgb(BRIGHT)]
            for y in range(box.h):
                for x in range(box.w):
                    r, g, b, a = frame.get_at((x, y))
                    if a > 128:
                        lum = (r * 3 + g * 6 + b) / 2550
                        out.set_at((x, y), shades[min(3, int(lum * 4.2))])
            self.photos[sprite] = pygame.transform.scale_by(out, k)
        return self.photos[sprite]
