"""The lab's file drawer: a little file system on the mainframe.

Pick SYSTEM FILES off the theory map and the whole screen becomes a terminal.
It holds the two rick roll videos, a few unlocked text files (stick up / down
scrolls a long one) and UNLOCK.EXE.

Opening it types a DIR command, like a real terminal, and the directory listing
it prints is the menu. It's all stick-and-button, like the visitor name entry:

    on ..             (the top row) button goes back to the theories; so does left
    on a file         button opens it
    on UNLOCK.EXE     a full-screen ENTER PASSWORD: three letters, typed like the
                      name entry (down rolls A -> B, up rolls back, button or right
                      locks a letter in, left backs up, and out from the first).
                      One of PASSWORDS gets ACCESS GRANTED; ANSWER (what the lab
                      tells you once you've tested every theory) plays the OOH
                      sequence (see ooh.py); TRIP_CODE (hidden in the room) is a
                      psychedelic thank-you (see trip.py); anything else is
                      ACCESS DENIED and another go

The terminal uses the bigger 5x7 font, in one colour, so it reads easily on the
cabinet.

The two .VID files rick roll you, and they're the one place the game drops the
pixels: the video plays over the whole window with its sound. It streams from
the video in assets/files/ through ffmpeg (the soundtrack is pulled out once and
cached). Without ffmpeg it falls back to the GIF there, silent; with no media at
all you get a TAPE MISSING screen. See the README there.
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pygame

from sprites.font import BIG_ADV, BIG_H, big_width

from .art import CRT_BG, PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT
from .ooh import Ooh
from .trip import Trip

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MEDIA_DIR = ASSETS / "files"
MEDIA_NAME = "rickroll"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "culture-shock"
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
AUDIO_EXTS = (".ogg", ".mp3", ".wav")
MOVIE_EXTS = (".mp4", ".m4v", ".mov", ".webm", ".mkv")     # need ffmpeg
PICTURE_EXTS = (".gif", ".png", ".jpg", ".jpeg", ".webp")
VIDEO_FPS = 30
SILENT_ROLL = 20.0          # s a picture-only roll runs, with no audio to say when it's over
ROLL_GRACE = 0.6            # s before we trust mixer.music.get_busy() to mean "finished"
FLASH_TIME = 2.2            # s a status message stays up
REPEAT = (0.4, 0.09)        # s before a held stick repeats, then s per step
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
PASSWORDS = ("XXX",)       # what UNLOCK.EXE says ACCESS GRANTED to, for now
ANSWER = "OOH"              # the answer you get for testing every theory: it plays ooh.py
TRIP_CODE = "SEX"           # hidden somewhere in the room: it plays trip.py
DENIED_TIME = 1.6           # s ACCESS DENIED stays up before another go

# the terminal fills the 320x180 screen, in the 5x7 font: 6 px a character, 10 px a line
SW, SH = 320, 180
X0 = 4                                       # left margin
COLS = (SW - 2 * X0 + 1) // BIG_ADV          # characters that fit across (52)
LINE = 10
CMD_Y = 4                                    # the command line
LIST_Y, ROW_H, LIST_ROWS = 22, LINE, 13      # the directory listing: first row's y, px per row, rows that fit
FOOT_Y = 157                                 # the divider over the hint / code line
HINT_Y = 165
DIR_CMD = "DIR ADMIN\\LIFELAB\\PRIVATE\\SECRET\\BOOBS\\BACKUP"
PROMPT = "C:\\>"
CMD_WAIT = 0.45                              # s the bare prompt blinks before the command types
CMD_RATE = 30.0                              # characters/s the DIR command types at
LIST_WAIT = 0.3                              # s after the command before the listing prints
LIST_RATE = 0.07                             # s per line of the listing


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
    LabFile("MATH_IS_EASY.TXT", "txt", (
        "Sex = fun",
        "More sex = more fun",
        "=> Polycule",
        "Q.E.D",
    )),
    LabFile("LAB_NOTEBOOK_11-13-26.TXT", "txt", (
        "No sleep for 72 hours",
        "Hung out with Calvin and Klein",
        "Met the machine elves",
        "Shit my pants",
    )),
    LabFile("DREAM_JOURNAL.TXT", "txt", (
        "Was a sperm again",
        "Came in second",
        "Still not over it",
    )),
    LabFile("MS_SUSIE.TXT", "txt", (
        "Miss Susie had a steamboat,",
        "The steamboat had a bell, (ding, ding!)",
        "Miss Susie went to heaven,",
        "The steamboat went to... (hell)",
        "Hello operator,",
        "Please give me number nine,",
        "And if you disconnect me,",
        "I'll chop off your... (behind)",
        "Behind the refrigerator,",
        "There lay a piece of glass,",
        "Miss Susie sat upon it,",
        "And cut her little... (ask)",
        "Ask me no more questions,",
        "Tell me no more lies,",
        "The boys are in the bathroom,",
        "Zipping up their... (flies)",
        "Flies are in the meadow,",
        "The bees are in the park,",
        "Miss Susie and her boyfriend",
        "Are kissing in the... (dark)",
        "D-A-R-K,",
        "Dark, dark, dark.",
    )),
    LabFile("DATA.TXT", "txt", (
        "Andy and Zack",
        "Sitting in a tree",
        "K-I-S-S-I-N-G",
        "First comes love",
        "Then comes marriage",
        "Then comes a baby in a baby carriage.",
    )),
]
TXT_Y = 24                                   # the first line of an open text file
TXT_ROWS = (FOOT_Y - 2 - TXT_Y) // LINE      # lines of it that fit (13); longer ones scroll

# what the terminal says after a roll. Always the same for a file: watching one never changes the other.
# A message whose last line names a file ends on a button that opens it.
AFTER_ROLL = {
    "WATCH_IF_YOU_ARE_NOT_ROLLING.VID": ["PLAYBACK COMPLETE.", "", "YOU ARE NOW ROLLING! READY TO WATCH:",
                                         "WATCH_IF_YOU_ARE_ROLLING"],
    "WATCH_IF_YOU_ARE_ROLLING.VID": ["PLAYBACK COMPLETE.", "", "YOU ARE ROLLING.", "KEEP ROLLING.", "",
                                     "THE LIFE LAB THANKS YOU", "FOR ROLLING."],
}
TAPE_MISSING = ["TAPE MISSING.", "", "THE REEL FOR THIS FILE IS NOT", "ON THE DRIVE. PUT A VIDEO OR",
                "GIF AND A SONG IN ASSETS/FILES", "NAMED RICKROLL. THEN ROLL."]


def rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def wrap_path(s: str, width: int = COLS) -> list[str]:
    """Break a long command into lines, after a backslash where it can."""
    out = []
    while len(s) > width:
        cut = s.rfind("\\", 0, width) + 1 or width
        out.append(s[:cut])
        s = s[cut:]
    return out + [s]


def human_size(n: int) -> str:
    return f"{n}" if n < 1000 else f"{n / 1000:.1f}K" if n < 1_000_000 else f"{n / 1_000_000:.1f}M"


def _find(exts: tuple[str, ...]) -> Path | None:
    """assets/files/rickroll.<ext>, or else any file there with one of these extensions."""
    for ext in exts:
        p = MEDIA_DIR / f"{MEDIA_NAME}{ext}"
        if p.exists():
            return p
    hits = sorted(p for p in MEDIA_DIR.glob("*") if p.suffix.lower() in exts)
    return hits[0] if hits else None


def _load_frames(pic: Path) -> list[tuple[pygame.Surface, float]]:
    """Every frame of an animated picture, with how long each one shows (s).
    pygame-ce has load_animation; plain pygame (the Pi's system pygame) doesn't,
    so fall back to Pillow, and only then to a single still."""
    def delay(ms) -> float:
        return max(0.02, ms / 1000) if ms else 0.1

    load_animation = getattr(pygame.image, "load_animation", None)
    if load_animation:
        try:
            return [(s, delay(ms)) for s, ms in load_animation(str(pic))]
        except pygame.error:
            pass
    try:
        from PIL import Image, ImageSequence
        with Image.open(pic) as im:
            frames = []
            for f in ImageSequence.Iterator(im):
                rgba = f.convert("RGBA")
                frames.append((pygame.image.frombytes(rgba.tobytes(), rgba.size, "RGBA"), delay(f.info.get("duration"))))
            if frames:
                return frames
    except (ImportError, OSError, ValueError):
        pass
    try:
        return [(pygame.image.load(str(pic)), 0.1)]
    except pygame.error:
        return []


def _soundtrack(movie: Path) -> Path | None:
    """The movie's audio as a WAV pygame can play, pulled out by ffmpeg once and cached."""
    st = movie.stat()
    out = CACHE_DIR / f"{movie.stem.replace(' ', '_')}-{st.st_size}-{int(st.st_mtime)}.wav"
    if out.exists():
        return out
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".part.wav")
        subprocess.run([FFMPEG, "-v", "error", "-nostdin", "-y", "-i", str(movie), "-vn", "-ac", "2",
                        "-ar", "44100", "-c:a", "pcm_s16le", str(tmp)], check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tmp.replace(out)
        return out
    except (OSError, subprocess.SubprocessError):
        return None


def _duration(movie: Path) -> float | None:
    if not FFPROBE:
        return None
    try:
        out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(movie)], capture_output=True, text=True, timeout=10).stdout
        return float(out.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


class Stream:
    """A movie decoded by ffmpeg on the fly, scaled to fit `size` and letterboxed.
    A thread reads raw frames off the pipe; frame(t) skips ahead to the one for
    time t, so the picture keeps up with the sound even if it starts late."""

    def __init__(self, movie: Path, size: tuple[int, int], fps: int = VIDEO_FPS) -> None:
        w, h = size
        self.size, self.fps = size, fps
        vf = (f"fps={fps},scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
        self.proc = subprocess.Popen(
            [FFMPEG, "-v", "error", "-nostdin", "-i", str(movie), "-map", "0:v:0", "-an", "-vf", vf,
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w * h * 3)
        self.q: queue.Queue[bytes | None] = queue.Queue(maxsize=8)
        self.n = -1                     # the frame on screen
        self.surf: pygame.Surface | None = None
        self.ended = False
        self.closed = False
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        nbytes = self.size[0] * self.size[1] * 3
        while not self.closed:
            buf = self.proc.stdout.read(nbytes)
            item = buf if len(buf) == nbytes else None
            while not self.closed:
                try:
                    self.q.put(item, timeout=0.2)
                    break
                except queue.Full:
                    pass
            if item is None:
                return

    def frame(self, t: float) -> pygame.Surface | None:
        want = int(t * self.fps)
        while self.n < want and not self.ended:
            try:
                buf = self.q.get_nowait()
            except queue.Empty:
                break
            if buf is None:
                self.ended = True
                break
            self.n += 1
            self.surf = pygame.image.frombuffer(buf, self.size, "RGB")
        return self.surf

    def close(self) -> None:
        self.closed = True
        try:
            self.proc.kill()
            self.proc.stdout.close()
        except OSError:
            pass


class Media:
    """The rick roll, loaded on first use: a movie streamed through ffmpeg with
    its own soundtrack, or else an (animated) picture and maybe a song."""

    def __init__(self) -> None:
        self.loaded = False
        self.movie: Path | None = None
        self.stream: Stream | None = None
        self.frames: list[tuple[pygame.Surface, float]] = []
        self.length = 0.0
        self.audio: Path | None = None
        self.scaled: dict[tuple[int, tuple[int, int]], tuple[pygame.Surface, tuple[int, int]]] = {}

    def load(self) -> None:
        if self.loaded:
            return
        self.loaded = True
        self.audio = _find(AUDIO_EXTS)
        self.movie = _find(MOVIE_EXTS) if FFMPEG else None
        if self.movie:
            self.audio = self.audio or _soundtrack(self.movie)
            self.length = _duration(self.movie) or 60.0
            return
        pic = _find(PICTURE_EXTS)
        if pic:
            self.frames = _load_frames(pic)
        self.length = sum(d for _, d in self.frames)

    @property
    def path(self) -> Path | None:
        return self.movie or _find(PICTURE_EXTS)

    @property
    def missing(self) -> bool:
        return not self.movie and not self.frames and not self.audio

    @property
    def ended(self) -> bool:
        return bool(self.stream and self.stream.ended)

    def start(self, size: tuple[int, int] | None) -> None:
        """Get the movie decoding (from the top) at this window size, ahead of the first frame."""
        self.stop()
        if self.movie and size:
            self.stream = Stream(self.movie, size)

    def stop(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

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
        """Draw the picture for time t over the whole window. No pixels here."""
        size = window.get_size()
        window.fill((0, 0, 0))
        if self.movie:
            if not self.stream or self.stream.size != size:
                self.start(size)
            img = self.stream.frame(t)
            if img:
                window.blit(img, (0, 0))
            return
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
        self.media = Media()
        self.photos: dict[str, pygame.Surface] = {}
        self.hold_k = 0.0               # 0..1: how far a held button is to the exit countdown (set by LifeSim)
        self.open()

    # -- state ---------------------------------------------------------------------------
    def open(self) -> None:
        self.mode = "boot"              # boot (the DIR typing out), list, code, granted, ooh, trip, txt, img, roll, msg
        self.ooh: Ooh | None = None
        self.trip: Trip | None = None
        self.boot_t = 0.0
        self.sel = 1                    # the first file, with .. (the way out) just above it
        self.scroll = 0
        self.code = ""
        self.letter = 0
        self.denied = 0.0               # s left on ACCESS DENIED
        self.flash = ("", 0.0)
        self.viewing: LabFile | None = None
        self.txt_scroll = 0             # first line of an open text file on screen
        self.msg: list[str] = []
        self.roll_t = 0.0
        self.closed = False
        self.stick = Stick()

    def visible(self) -> list[LabFile]:
        return [f for f in FILES if f.code is None or f.code in self.unlocked]

    def locked(self) -> int:
        return sum(1 for f in FILES if f.code and f.code not in self.unlocked)

    def rows(self) -> list[LabFile | str]:
        """The directory listing, which is also the menu: .. (back to the
        theories), the files, then UNLOCK.EXE (type a code)."""
        return ["UP", *self.visible(), "CODE"]

    def _follow(self) -> None:
        """Scroll so the selected row is on screen."""
        self.scroll = max(0, min(self.scroll, self.sel), self.sel - LIST_ROWS + 1)

    def command(self) -> list[str]:
        """The DIR command as typed so far, wrapped onto the screen."""
        typed = DIR_CMD[:max(0, int((self.boot_t - CMD_WAIT) * CMD_RATE))]
        return wrap_path(PROMPT + typed)

    def _printed(self) -> int:
        """How many rows of the listing have printed (all of them once it's a menu)."""
        if self.mode != "boot":
            return len(self.rows())
        t = self.boot_t - CMD_WAIT - len(DIR_CMD) / CMD_RATE - LIST_WAIT
        return max(0, min(len(self.rows()), int(t / LIST_RATE) + 1 if t >= 0 else 0))

    def size(self, f: LabFile) -> str:
        if f.kind == "txt":
            return human_size(sum(len(line) + 2 for line in f.lines))
        path = ASSETS / "sprites" / f"{f.sprite}.png" if f.kind == "img" else self.media.path
        try:
            return human_size(path.stat().st_size)
        except (AttributeError, OSError):
            return "0"

    @property
    def playing(self) -> bool:
        return self.mode in ("roll", "ooh")

    def _say(self, s: str) -> None:
        self.flash = (s, FLASH_TIME)

    def update(self, dt: float, inp) -> None:
        sx, sy = self.stick.step(dt, inp.x, inp.y)
        self.flash = (self.flash[0], self.flash[1] - dt)
        getattr(self, f"_update_{self.mode}")(dt, sx, sy, inp.action)

    def _update_boot(self, dt: float, sx: int, sy: int, act: bool) -> None:
        self.boot_t += dt
        if act or self._printed() >= len(self.rows()) and self.boot_t > CMD_WAIT + len(DIR_CMD) / CMD_RATE + 1.2:
            self.mode = "list"
            self.boot_t = 1e9                       # everything typed out

    def _update_list(self, dt: float, sx: int, sy: int, act: bool) -> None:
        rows = self.rows()
        if sy:
            self.sel = max(0, min(len(rows) - 1, self.sel + sy))   # no wrap: .. is the top
        self._follow()
        if sx < 0:
            self.closed = True
        elif act:
            row = rows[self.sel]
            if row == "CODE":
                self.mode, self.code, self.letter, self.denied = "code", "", 0, 0.0
            elif row == "UP":
                self.closed = True
            else:
                self._open_file(row, "list")

    def _update_code(self, dt: float, sx: int, sy: int, act: bool) -> None:
        if self.denied > 0:                                      # ACCESS DENIED, then another go
            self.denied -= dt
            return
        if sy:
            self.letter = (self.letter + sy) % len(LETTERS)      # down goes A -> B, like the name entry
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
        if code == ANSWER:
            self.log("code", code=code, result="ooh")
            self.mode, self.ooh = "ooh", Ooh(self.mute)
            return
        if code == TRIP_CODE:
            self.log("code", code=code, result="trip")
            self.mode, self.trip = "trip", Trip()
            return
        ok = code in PASSWORDS
        self.log("code", code=code, result="granted" if ok else "denied")
        if ok:
            self.mode = "granted"
        else:
            self.code, self.letter, self.denied = "", 0, DENIED_TIME

    def _update_granted(self, dt: float, sx: int, sy: int, act: bool) -> None:
        if act or sx < 0:
            self.mode = "list"

    def _update_ooh(self, dt: float, sx: int, sy: int, act: bool) -> None:
        self.ooh.update(dt, sx, act)
        if self.ooh.done:
            self.log("ooh_end", secs=round(self.ooh.t, 1))
            self.ooh.stop()
            self.ooh = None
            self.mode = "list"

    def _update_trip(self, dt: float, sx: int, sy: int, act: bool) -> None:
        self.trip.update(dt, sx, act)
        if self.trip.done:
            self.trip = None
            self.mode = "list"

    def _open_file(self, f: LabFile, via: str) -> None:
        self.viewing = f
        self.log("file_open", file=f.name, via=via)
        if f.kind == "roll":
            self.media.load()
            if self.media.missing:
                self.mode, self.msg = "msg", TAPE_MISSING
                return
            self.mode, self.roll_t = "roll", 0.0
            window = pygame.display.get_surface()
            self.media.start(window.get_size() if window else None)     # decoding before the sound starts
            if self.media.audio and not self.mute:
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(str(self.media.audio))
                    pygame.mixer.music.play()
                except pygame.error:
                    self.media.audio = None
        else:
            self.mode, self.txt_scroll = f.kind, 0

    def _update_txt(self, dt: float, sx: int, sy: int, act: bool) -> None:
        if sy and self.viewing.kind == "txt":
            top = max(0, len(self.viewing.lines) - TXT_ROWS)
            self.txt_scroll = max(0, min(top, self.txt_scroll + sy))
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
        """The file a message ends by naming, to open next, if any."""
        if not self.msg:
            return None
        return next((f for f in FILES if f.name == self.msg[-1] + ".VID"), None)

    def _update_roll(self, dt: float, sx: int, sy: int, act: bool) -> None:
        self.roll_t += dt
        music = self.media.audio and not self.mute and pygame.mixer.get_init()
        if music:
            over = self.roll_t > ROLL_GRACE and not pygame.mixer.music.get_busy()
        elif self.media.movie:
            over = self.media.ended or self.roll_t > self.media.length + 0.5
        else:
            over = self.roll_t > SILENT_ROLL
        if act or sx < 0 or over:            # you can bail out of a rick roll. it still counts
            if music:
                pygame.mixer.music.fadeout(400)
            self.media.stop()
            name = self.viewing.name
            self.log("roll_end", file=name, bailed=not over, secs=round(self.roll_t, 1))
            self.msg = AFTER_ROLL[name]
            self.mode = "msg"

    # -- drawing ---------------------------------------------------------------------------
    def overlay(self, window: pygame.Surface) -> None:
        if self.mode == "roll":
            self.media.blit(window, self.roll_t)

    def draw(self, screen: pygame.Surface, text, time: float) -> None:
        """Paint the terminal over the whole screen, in the 5x7 font."""
        self.text = text
        screen.fill(rgb(CRT_BG))
        if self.mode in ("boot", "list"):
            self._draw_list(screen, time)
        elif self.mode == "code":
            self._draw_code(screen, time)
        elif self.mode == "granted":
            self._header(screen, "UNLOCK.EXE")
            for i, line in enumerate(("ACCESS", "GRANTED")):
                img = self.text.get(line, PHOSPHOR, 3, big=True)
                screen.blit(img, (SW // 2 - img.get_width() // 2, 50 + i * 30))
            self._footer(screen, "BUTTON: OK")
        elif self.mode == "ooh":
            self.ooh.draw(screen)
        elif self.mode == "trip":
            self.trip.draw(screen)
        elif self.mode == "txt":
            self._header(screen, self.viewing.name)
            lines, s = self.viewing.lines, self.txt_scroll
            for i, line in enumerate(lines[s:s + TXT_ROWS]):
                self._put(screen, line, X0, TXT_Y + i * LINE)
            long = len(lines) > TXT_ROWS
            if s > 0:                                   # more above
                self._put(screen, "^", SW - X0 - 5, TXT_Y)
            if s + TXT_ROWS < len(lines):               # more below
                self._put(screen, "+", SW - X0 - 5, TXT_Y + (TXT_ROWS - 1) * LINE)
            self._footer(screen, "STICK: SCROLL   BUTTON: BACK" if long else "BUTTON: BACK")
        elif self.mode == "img":
            self._header(screen, self.viewing.name)
            photo = self._photo(self.viewing.sprite)
            screen.blit(photo, (SW // 2 - photo.get_width() // 2, 22 + (96 - photo.get_height()) // 2))
            for i, line in enumerate(self.viewing.lines):
                self._put(screen, line, SW // 2 - big_width(line) // 2, 126 + i * LINE)
            self._footer(screen, "BUTTON: BACK")
        elif self.mode == "msg":
            self._header(screen, "SESSION LOG", self.viewing.name.removesuffix(".VID"))
            nxt = self._next_file()
            for i, line in enumerate(self.msg):
                y = 26 + i * LINE
                if nxt and i == len(self.msg) - 1:          # the file to open next, as a blinking button
                    label = "> " + line
                    w = big_width(label) + 6
                    lit = int(time * 2.5) % 2 == 0
                    if lit:
                        screen.fill(rgb(PHOSPHOR), (X0, y - 2, w, BIG_H + 4))
                    else:
                        pygame.draw.rect(screen, rgb(PHOSPHOR), (X0, y - 2, w, BIG_H + 4), 1)
                    self._put(screen, label, X0 + 3, y, CRT_BG if lit else PHOSPHOR)
                else:
                    self._put(screen, line, X0, y)
            self._footer(screen, "BUTTON: OPEN IT   LEFT: BACK" if nxt else "BUTTON: OK")
        elif self.mode == "roll":                       # what's under the full-window video
            label = "NOW ROLLING"
            self._put(screen, label, SW // 2 - big_width(label) // 2, SH // 2 - BIG_H // 2)

    def _put(self, screen, s: str, x: int, y: int, color: str = PHOSPHOR) -> int:
        """One line of 5x7 text; returns its width."""
        if not s:
            return 0
        img = self.text.get(s, color, big=True)
        screen.blit(img, (x, y))
        return img.get_width()

    def _put_right(self, screen, s: str, y: int, color: str = PHOSPHOR, right: int = SW - X0) -> None:
        self._put(screen, s, right - big_width(s), y, color)

    def _header(self, screen, left: str, right: str = "") -> None:
        self._put(screen, left, X0, CMD_Y)
        if right:
            self._put_right(screen, right, CMD_Y)
        screen.fill(rgb(PHOSPHOR_DIM), (X0, CMD_Y + BIG_H + 4, SW - 2 * X0, 1))

    def _footer(self, screen, hint: str, hold: bool = False) -> None:
        screen.fill(rgb(PHOSPHOR_DIM), (X0, FOOT_Y, SW - 2 * X0, 1))
        self._put(screen, hint, X0, HINT_Y)
        if hold:
            self._draw_hold_hint(screen)

    def _cursor(self, screen, x: int, y: int, color: str = PHOSPHOR) -> None:
        screen.fill(rgb(color), (x, y, 5, BIG_H))

    def _draw_list(self, screen, time: float) -> None:
        """The terminal: the DIR command, the listing under it (the menu), and a
        footer with the hint, a status message, or the code being typed."""
        blink = int(time * 2.5) % 2 == 0
        cmd = self.command()
        for i, line in enumerate(cmd):
            self._put(screen, line, X0, CMD_Y + i * LINE)
        printed = self._printed()
        if self.mode == "boot" and printed == 0:                # the cursor, typing
            if blink or len(cmd[-1]) > len(PROMPT) and self.boot_t - CMD_WAIT < len(DIR_CMD) / CMD_RATE:
                self._cursor(screen, X0 + len(cmd[-1]) * BIG_ADV, CMD_Y + (len(cmd) - 1) * LINE)
            return

        rows = self.rows()
        top = LIST_Y + (len(cmd) - 1) * LINE
        selected = self.sel if self.mode == "list" else None
        for j in range(self.scroll, min(len(rows), self.scroll + LIST_ROWS, printed)):
            row = rows[j]
            y = top + (j - self.scroll) * ROW_H
            if row == "UP":
                label, right = ".. EXIT TO THEORIES", "<DIR>"
            elif row == "CODE":
                label, right = "UNLOCK.EXE", f"{self.locked()} LOCKED" if self.locked() else ""
            else:
                label, right = row.name, self.size(row)
            fg = PHOSPHOR
            if j == selected:                                   # dark text on a lit bar
                screen.fill(rgb(PHOSPHOR), (X0 - 2, y - 2, SW - 2 * X0 + 4, BIG_H + 4))
                fg = CRT_BG
            self._put(screen, label, X0 + 6, y, fg)
            if right and big_width(label) + big_width(right) < SW - 2 * X0 - 30:
                self._put_right(screen, right, y, fg, SW - X0 - 8)
        if self.scroll > 0:                                     # more above: the way out is up there
            self._put(screen, "^", SW - X0 - 5, top - LINE + 1)
        if self.scroll + LIST_ROWS < min(printed, len(rows)):
            self._put(screen, "+", SW - X0 - 5, top + LIST_ROWS * ROW_H - 2)
        if self.mode == "boot":
            if printed < len(rows) and blink:
                y = top + min(printed, LIST_ROWS) * ROW_H
                self._cursor(screen, X0 + 6, min(y, FOOT_Y - BIG_H - 2))
            return

        screen.fill(rgb(PHOSPHOR_DIM), (X0, FOOT_Y, SW - 2 * X0, 1))
        y = HINT_Y
        msg, left = self.flash
        row = rows[self.sel]
        if left > 0:
            self._put(screen, msg, X0, y)
        else:
            self._put(screen, "BUTTON: BACK TO THEORIES" if row == "UP" else
                      "BUTTON: TYPE A CODE" if row == "CODE" else "BUTTON: OPEN", X0, y)
        self._draw_hold_hint(screen)

    def _draw_code(self, screen, time: float) -> None:
        """UNLOCK.EXE: ENTER PASSWORD and three big letter slots, the current one rolling."""
        self._header(screen, "UNLOCK.EXE")
        title = self.text.get("ENTER PASSWORD", PHOSPHOR, 2, big=True)
        screen.blit(title, (SW // 2 - title.get_width() // 2, 30))
        if self.denied > 0:
            if int(time * 4) % 2 == 0:
                img = self.text.get("ACCESS DENIED", PHOSPHOR, 2, big=True)
                screen.blit(img, (SW // 2 - img.get_width() // 2, 80))
            self._footer(screen, "TRY AGAIN")
            return
        slot_w, gap, top = 22, 10, 74
        x0 = SW // 2 - (3 * slot_w + 2 * gap) // 2
        bob = int(time * 4) % 2                                   # the arrows nudge in and out
        hi = rgb(PHOSPHOR)
        for i in range(3):
            x = x0 + i * (slot_w + gap)
            here = i == len(self.code)
            ch = self.code[i] if i < len(self.code) else LETTERS[self.letter] if here else ""
            if ch:
                img = self.text.get(ch, PHOSPHOR, 2, big=True)
                screen.blit(img, (x + (slot_w - img.get_width()) // 2, top))
            screen.fill(rgb(PHOSPHOR if here else PHOSPHOR_DIM), (x, top + 18, slot_w, 1 + here))
            if here:                                              # arrows above and below: up and down roll it
                mx = x + slot_w // 2
                for k in range(4):
                    screen.fill(hi, (mx - k, top - 8 - bob + k, 2 * k + 1, 1))
                    screen.fill(hi, (mx - k, top + 26 + bob - k, 2 * k + 1, 1))
        for i, line in enumerate(("STICK UP / DOWN: CHANGE THE LETTER", "BUTTON: SELECT LETTER")):
            self._put(screen, line, SW // 2 - big_width(line) // 2, 116 + i * LINE)
        self._footer(screen, "LEFT: BACK")

    def _draw_hold_hint(self, screen) -> None:
        """HOLD: EXIT at the right of the footer, with a bar filling up while the button's held."""
        label = "HOLD: EXIT"
        x = SW - X0 - big_width(label)
        self._put(screen, label, x, HINT_Y)
        if self.hold_k > 0:
            screen.fill(rgb(PHOSPHOR), (x, HINT_Y + BIG_H + 2, int(big_width(label) * self.hold_k), 2))

    def _photo(self, sprite: str) -> pygame.Surface:
        """An experiment photo: the first frame of a cast sprite, in shades of phosphor."""
        if sprite not in self.photos:
            sheet = pygame.image.load(str(ASSETS / "sprites" / f"{sprite}.png"))
            frame = sheet.subsurface((0, 0, 48, 48)).copy()
            box = frame.get_bounding_rect()
            frame = frame.subsurface(box).copy()
            k = max(1, min(96 // box.h, 200 // box.w))
            out = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
            shades = [rgb(PHOSPHOR_FAINT), rgb(PHOSPHOR_DIM), rgb(PHOSPHOR), rgb("#eaffea")]
            for y in range(box.h):
                for x in range(box.w):
                    r, g, b, a = frame.get_at((x, y))
                    if a > 128:
                        lum = (r * 3 + g * 6 + b) / 2550
                        out.set_at((x, y), shades[min(3, int(lum * 4.2))])
            self.photos[sprite] = pygame.transform.scale_by(out, k)
        return self.photos[sprite]
