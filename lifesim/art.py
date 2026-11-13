"""Art for the main game: the Life Lab Mainframe, a 1970s computer the lab
swears is state of the art, and the spirit you play.

The room is one 320x180 picture: two tape drives either side of a console with
a green-phosphor CRT and a lamp-and-switch panel. The moving parts (reels,
vacuum-column tape loops, blinking lamps, the CRT itself) are drawn by the game
on top, at the spots this module exports.

Drawn with the same canvas, palette and 1px outline as the main cast.
"""

from __future__ import annotations

import math

from sprites.canvas import Canvas, mix
from sprites.font import draw_text_centered
from sprites.palette import INK, OUTLINE

W, H = 320, 180

# -- colours -----------------------------------------------------------------------
WALL, WALL_DARK = "#3b2a22", "#2e2019"
STRIPES = ("#c8642a", "#e0a030", "#8a3e1c")         # a 70s supergraphic across the wall
FLOOR, FLOOR_LINE, FLOOR_DARK = "#6d6a66", "#57544f", "#44413d"
BEIGE, BEIGE_SHADE, BEIGE_DARK, BEIGE_LIGHT = "#d8c8a4", "#b3a27f", "#7f7258", "#eee2c4"
BLUE, BLUE_DARK, BLUE_LIGHT = "#3a5f8a", "#263f5e", "#6286b0"
METAL, METAL_DARK, METAL_LIGHT = "#a8acb4", "#6c707a", "#dfe2e8"
GLASS = "#1c2228"
BEZEL, BEZEL_DARK = "#2e2e34", "#1c1c20"
TAPE, TAPE_DARK = "#5a3a22", "#3a2414"

PHOSPHOR = "#5dff7a"          # P1 green
PHOSPHOR_DIM = "#2a9a46"
PHOSPHOR_FAINT = "#14502a"
CRT_BG = "#06160b"

LAMP_ON = ("#ff6a3a", "#ffd23a", "#ffffff", "#ff3a3a")
LAMP_OFF = "#4a2a20"

SPIRIT_EDGE, SPIRIT_BODY, SPIRIT_CORE = "#5ec8e8", "#bdf4ff", "#ffffff"

# -- where things sit ----------------------------------------------------------------
FLOOR_Y = 156
SCREEN = (80, 14, 160, 104)                     # the CRT's glass: x, y, w, h
DRIVES = ((6, 22), (254, 22))                   # top-left of each tape cabinet (60 wide)
REEL_R = 12
REEL_SIZE = REEL_R * 2 + 1
REEL_FRAMES = 12                                 # the reel has 3-fold symmetry; 12 frames cover 120 degrees


def reel_centers() -> list[tuple[int, int]]:
    return [(dx + ox, dy + 24) for dx, dy in DRIVES for ox in (16, 44)]


def column_slots() -> list[tuple[int, int, int, int]]:
    """The vacuum columns under the reels, where the tape hangs in a loop: x, y, w, h."""
    return [(dx + ox, dy + 44, 10, 22) for dx, dy in DRIVES for ox in (11, 39)]


def drive_lamps() -> list[tuple[int, int]]:
    return [(dx + 8 + i * 6, dy + 72) for dx, dy in DRIVES for i in range(8)]


def console_lamps() -> list[tuple[int, int]]:
    """Two rows of front-panel lamps under the CRT."""
    return [(86 + i * 6, 128 + r * 6) for r in range(2) for i in range(16)]


# -- the room ------------------------------------------------------------------------

def _cabinet(c: Canvas, x: int, y: int, w: int, h: int) -> None:
    c.rect(x, y, w, h, BEIGE)
    c.rect(x, y, w, 3, BEIGE_LIGHT)
    c.rect(x + w - 2, y, 2, h, BEIGE_SHADE)
    c.rect(x, y + h - 4, w, 4, BEZEL)                 # kick plate
    c.hline(x, x + w - 1, y, OUTLINE)
    c.hline(x, x + w - 1, y + h - 1, OUTLINE)
    c.vline(x, y, y + h - 1, OUTLINE)
    c.vline(x + w - 1, y, y + h - 1, OUTLINE)


def _tape_drive(c: Canvas, x: int, y: int, n: int) -> None:
    _cabinet(c, x, y, 60, FLOOR_Y - y + 2)
    # the window over the reels
    c.rect(x + 3, y + 8, 54, 34, METAL_DARK)
    c.rect(x + 4, y + 9, 52, 32, GLASS)
    c.hline(x + 5, x + 20, y + 10, mix(GLASS, "#ffffff", 0.25))   # glare
    c.hline(x + 5, x + 12, y + 11, mix(GLASS, "#ffffff", 0.15))
    # the head block between the reels and the columns
    c.rect(x + 25, y + 38, 10, 6, METAL)
    c.rect(x + 27, y + 39, 6, 3, METAL_DARK)
    # vacuum columns
    for sx, sy, sw, sh in column_slots():
        if x <= sx < x + 60:
            c.rect(sx - 1, sy - 1, sw + 2, sh + 2, METAL_DARK)
            c.rect(sx, sy, sw, sh, GLASS)
    # lamp strip and a blue name plate
    c.rect(x + 5, y + 69, 50, 7, BEIGE_DARK)
    c.rect(x + 6, y + 84, 48, 9, BLUE)
    c.hline(x + 6, x + 53, y + 84, BLUE_LIGHT)
    draw_text_centered(c, x + 30, y + 86, f"TAPE {n}", BEIGE_LIGHT)
    # two door panels and their handles
    for py in (y + 98, y + 116):
        c.rect(x + 5, py, 50, 16, BEIGE_SHADE)
        c.rect(x + 6, py + 1, 48, 14, BEIGE)
        c.rect(x + 26, py + 6, 8, 2, METAL_DARK)


def _console(c: Canvas) -> None:
    x, y, w = 70, 8, 180
    _cabinet(c, x, y, w, FLOOR_Y - y + 2)
    sx, sy, sw, sh = SCREEN
    # CRT bezel, chunky, with rounded corners
    c.rect(sx - 6, sy - 5, sw + 12, sh + 10, BEZEL)
    c.rect(sx - 6, sy + sh + 3, sw + 12, 2, BEZEL_DARK)
    c.rect(sx - 2, sy - 2, sw + 4, sh + 4, BEZEL_DARK)
    for cx, cy in ((sx - 6, sy - 5), (sx + sw + 5, sy - 5), (sx - 6, sy + sh + 4), (sx + sw + 5, sy + sh + 4)):
        c.set(cx, cy, BEIGE)
    # the front panel under the CRT
    c.rect(x + 6, 124, w - 12, 30, BEIGE_SHADE)
    c.rect(x + 7, 125, w - 14, 28, BEIGE)
    c.rect(83, 126, 99, 13, BEIGE_DARK)                     # lamp field
    # toggle switches, alternating colours like the real ones
    for i in range(16):
        tx = 86 + i * 6
        col = BLUE if (i // 4) % 2 == 0 else "#c8642a"
        c.rect(tx - 1, 142, 4, 8, col)
        c.rect(tx, 143 if i % 3 else 146, 2, 3, METAL_LIGHT)
    # name plate
    c.rect(188, 127, 54, 23, BLUE)
    c.hline(188, 241, 127, BLUE_LIGHT)
    c.rect(188, 149, 54, 1, BLUE_DARK)
    draw_text_centered(c, 215, 130, "LIFE LAB", BEIGE_LIGHT)
    draw_text_centered(c, 215, 137, "MAINFRAME", mix(BEIGE_LIGHT, BLUE, 0.35))
    draw_text_centered(c, 215, 143, "MOD 1974", mix(BEIGE_LIGHT, BLUE, 0.35))
    # a big red power button nobody is allowed to touch
    c.oval(237, 145, 3, 3, "#d03030")


def room() -> Canvas:
    c = Canvas(W, H)
    c.rect(0, 0, W, FLOOR_Y, WALL)
    for x in range(0, W, 20):                         # wood panelling
        c.vline(x, 0, FLOOR_Y - 1, WALL_DARK)
    for i, col in enumerate(STRIPES):
        c.rect(0, 6 + i * 4, W, 3, col)
    # fluorescent tubes
    for lx in (14, 266):
        c.rect(lx, 0, 40, 2, "#f4f0d8")
    # raised computer-room floor
    c.rect(0, FLOOR_Y, W, H - FLOOR_Y, FLOOR)
    c.hline(0, W - 1, FLOOR_Y, FLOOR_DARK)
    for x in range(0, W, 24):
        c.line(x, FLOOR_Y + 1, x + (x - W // 2) // 6, H - 1, FLOOR_LINE)
    for fy in (164, 174):
        c.hline(0, W - 1, fy, FLOOR_LINE)
    # cables snaking from the drives to the console
    c.rect(66, FLOOR_Y + 1, 4, 2, "#222222")
    c.rect(250, FLOOR_Y + 1, 4, 2, "#222222")
    for n, (dx, dy) in enumerate(DRIVES, 1):
        _tape_drive(c, dx, dy, n)
    _console(c)
    return c


# -- the moving bits -------------------------------------------------------------------

def reel(frame: int, pack: float = 0.7) -> Canvas:
    """A tape reel: a silver flange with three cut-out windows that show the tape
    wound on the hub. `frame` (0..REEL_FRAMES) turns it a third of the way round;
    `pack` is how full it is (0..1)."""
    c = Canvas(REEL_SIZE, REEL_SIZE)
    turn = frame / REEL_FRAMES * 120
    tape_r = 4.5 + pack * 6
    for y in range(REEL_SIZE):
        for x in range(REEL_SIZE):
            dx, dy = x - REEL_R, y - REEL_R
            r = math.hypot(dx, dy)
            if r > REEL_R + 0.3:
                continue
            ang = (math.degrees(math.atan2(dy, dx)) - turn) % 120
            if r < 2:
                col = METAL_DARK
            elif r < 4:
                col = METAL_LIGHT if ang < 30 else METAL
            elif 4.5 < r < 10.5 and 15 < ang < 75:
                col = (TAPE if r < tape_r - 1 else TAPE_DARK) if r < tape_r else "#101418"
            elif r > REEL_R - 1:
                col = METAL_DARK
            else:
                col = METAL_LIGHT if 90 < ang < 105 else METAL
            c.set(x, y, col)
    return c


SPIRIT_W, SPIRIT_H = 14, 18
SPIRIT_FRAMES = 6


def spirit(frame: int) -> Canvas:
    """The player before they have a body: a little wisp with a round head and a
    tail that curls. Six frames of flicker."""
    c = Canvas(SPIRIT_W, SPIRIT_H)
    ph = frame / SPIRIT_FRAMES * math.tau
    cx = SPIRIT_W / 2 - 0.5
    # the tail, thinning toward the tip and swaying more the further down it goes
    for y in range(8, SPIRIT_H):
        k = (y - 8) / (SPIRIT_H - 8)
        half = 5.2 * (1 - k) ** 1.4 + 0.5
        mid = cx + math.sin(ph - k * 4.0) * 3.4 * k ** 0.8
        for x in range(SPIRIT_W):
            d = abs(x - mid)
            if d <= half:
                c.set(x, y, SPIRIT_CORE if d < half - 2.4 else SPIRIT_BODY if d < half - 1 else SPIRIT_EDGE)
    # the head
    c.oval(1, 1, 12, 11, SPIRIT_EDGE)
    c.oval(2, 2, 10, 9, SPIRIT_BODY)
    c.oval(4, 3, 6, 5, SPIRIT_CORE)
    # a lick of flame on top
    tip = round(math.sin(ph) * 1.2)
    c.set(int(cx) + tip, 0, SPIRIT_EDGE)
    c.set(int(cx) + tip, 1, SPIRIT_BODY)
    # face: blinks on the last frame
    if frame == SPIRIT_FRAMES - 1:
        c.hline(4, 5, 6, INK)
        c.hline(8, 9, 6, INK)
    else:
        c.rect(4, 5, 2, 2, INK)
        c.rect(8, 5, 2, 2, INK)
    c.hline(6, 7, 9, mix(INK, SPIRIT_BODY, 0.4))
    return c
