"""Level: THE COURT HOUSE. A courthouse, as described to someone who has never seen one.

Everything is a legal term taken completely literally:

    the court ......... a basketball court (hoops and all)
    order! ............ a fast-food counter, ORDER HERE
    all rise .......... legal pads that launch you into the air
    legal briefs ...... underwear on a clothesline
    court of appeals .. banana peels everywhere
    cases ............. suitcases, stacked up to climb
    bailiff ........... a bale of hay in a sheriff's hat
    the dock .......... an actual dock, over actual water
    overruled ......... floating rulers
    the bar ........... a bar. You have to pass it.
    hung jury ......... twelve portraits of the cast, hung up on strings
    jury box .......... a jukebox
    witness stand ..... a lemonade stand. 5 cents.
    exhibit A ......... a rubber duck under glass
    court reporter .... a news camera, ON AIR
    motion to dismiss . a conveyor belt that pushes you back out
    scales of justice . a fish, and a bathroom scale
    the bench ......... a park bench, presided over by the Honorable Judge Spaghetti

    python -m sprites.levels.courthouse     # just this level (the main build also runs it)

Outputs (under assets/levels/courthouse/):
    far.png              wall, columns and windows; loops horizontally, scrolls at half speed
    level.png            the whole level (decor + tiles), 1920x192, scrolls with the camera
    spaghetti_judge.png  boss sheet, one row per state, 80x80 frames
    level.json           tile map, colliders, spawns, zones, and the boss's animation table
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

from ..bosses import spaghetti_judge as judge
from ..canvas import Canvas, mix
from ..font import draw_text, draw_text_centered, text_width
from ..palette import COURT as K, OUTLINE, SPAGHETTI_JUDGE
from ..rig import SIZE

ROOT = Path(__file__).resolve().parent.parent.parent
SLUG = "courthouse"
NAME = "The Court House"
TILE = 16
COLS, ROWS = 120, 12
W, H = COLS * TILE, ROWS * TILE           # 1920 x 192
VIEW = (320, 180)                          # the camera shows rows y=12..192
FLOOR = 10 * TILE                          # top of the floor (y = 160)
FAR_W = 160                                # the far wall repeats every 160px

# tile char -> (name, collider type)
LEGEND = {
    "#": ("court", "solid"),
    "M": ("marble", "solid"),
    "H": ("hay", "solid"),
    "C": ("case", "solid"),
    "-": ("ruler", "oneway"),
    "=": ("dock", "oneway"),
    "P": ("legal_pad", "bounce"),
    "<": ("conveyor", "conveyor"),
    "^": ("banana_peel", "hazard"),
    "~": ("water", "water"),
}
# collider rect inside a tile, (dy, h), for tiles that don't fill their cell
INSET = {"ruler": (0, 5), "dock": (0, 5), "legal_pad": (10, 6), "banana_peel": (11, 5), "water": (5, 11)}

# The level, zone by zone. (zone name, first col, last col)
ZONES = [
    ("LOBBY", 0, 19),
    ("COURT OF APPEALS", 20, 39),
    ("THE DOCK", 40, 59),
    ("THE BAR", 60, 79),
    ("WITNESS STAND", 80, 99),
    ("THE BENCH", 100, 119),
]


def layout() -> list[str]:
    g = [["."] * COLS for _ in range(ROWS)]

    def fill(ch: str, c0: int, c1: int, r0: int, r1: int | None = None) -> None:
        for r in range(r0, (r0 if r1 is None else r1) + 1):
            for c in range(c0, c1 + 1):
                g[r][c] = ch

    fill("#", 0, COLS - 1, 10, 11)                 # the court
    # LOBBY
    fill("M", 0, 0, 0, 9)                          # front wall
    fill("P", 13, 14, 9)                           # ALL RISE
    fill("M", 15, 18, 5)                           # ledge you can only reach by rising
    # COURT OF APPEALS
    for c in (22, 25, 27):
        fill("^", c, c, 9)
    fill("C", 29, 30, 9)
    fill("C", 32, 33, 8, 9)
    fill("^", 33, 33, 7)                           # an a-peel on top of a case
    fill("C", 34, 34, 9)                           # a step, so a missed jump isn't a dead end
    fill("C", 35, 36, 7, 9)
    # THE DOCK / OVERRULED
    fill("H", 40, 41, 9)
    fill("H", 42, 43, 8, 9)
    fill("~", 44, 57, 10, 11)
    fill("=", 44, 45, 9)
    fill("-", 48, 49, 8)
    fill("-", 52, 53, 7)
    fill("=", 56, 57, 9)
    # THE BAR: the bar itself and the jukebox are props with their own colliders
    # WITNESS STAND
    fill("<", 93, 99, 10)                          # MOTION TO DISMISS
    # THE BENCH
    fill("M", COLS - 1, COLS - 1, 0, 9)            # back wall
    return ["".join(row) for row in g]


MAP = layout()


def tile_at(c: int, r: int) -> str:
    return MAP[r][c] if 0 <= r < ROWS and 0 <= c < COLS else "."


def h(*v: int) -> int:
    """Tiny deterministic hash for per-tile variation."""
    x = 0x9E37
    for n in v:
        x = (x * 31 + n * 0x45D9F3B) & 0xFFFFFF
    return x ^ (x >> 7)


# ---------------------------------------------------------------- text helpers

def big_text(c: Canvas, x: int, y: int, text: str, color: str, k: int = 2) -> None:
    t = Canvas(max(1, text_width(text)), 5)
    draw_text(t, 0, 0, text, color)
    for yy in range(5):
        for xx in range(t.w):
            if t.px[yy][xx]:
                c.rect(x + xx * k, y + yy * k, k, k, color)


def sign(c: Canvas, thin: Canvas, cx: int, y: int, lines: list[str], mount: str = "chain",
         big: int = 1, text: str = K["sign_text"], plate: str = K["sign"]) -> tuple[int, int, int, int]:
    """A brass-framed sign centered at cx. mount: 'chain' (from the ceiling), 'post' (to the floor), or 'wall'."""
    tw = max(text_width(s) for s in lines) * big
    w, hh = tw + 8, len(lines) * 6 * big + 5
    x = cx - w // 2
    c.rect(x, y, w, hh, plate)
    for xx, yy in ((x + 1, y + 1), (x + w - 2, y + 1), (x + 1, y + hh - 2), (x + w - 2, y + hh - 2)):
        c.set(xx, yy, K["brass"])                                    # rivets
    for i, s in enumerate(lines):
        if big > 1:
            big_text(c, cx - text_width(s) * big // 2, y + 3 + i * 6 * big, s, text, big)
        else:
            draw_text_centered(c, cx, y + 3 + i * 6, s, text)
    if mount == "chain":
        for xx in (x + 3, x + w - 4):
            for yy in range(0, y):
                thin.set(xx, yy, K["grey"] if yy % 3 else K["grey_sh"])
    elif mount == "post":
        c.rect(cx - 1, y + hh, 3, FLOOR - y - hh, K["dock_sh"])
        c.vline(cx, y + hh, FLOOR - 1, K["dock"])
    return x, y, w, hh


# ---------------------------------------------------------------- far wall (parallax)

def far_wall() -> Canvas:
    c = Canvas(FAR_W, H)
    c.rect(0, 0, FAR_W, H, K["wall"])
    for y in range(28, 120, 12):                                       # marble courses
        c.hline(0, FAR_W - 1, y, K["wall_sh"])
        off = 0 if (y // 12) % 2 else 20
        for x in range(off, FAR_W, 40):
            c.vline(x, y - 11, y - 1, K["wall_sh"])
    # arched window
    wx, wy, ww, wh = 52, 34, 56, 84
    c.rect(wx - 3, wy + 10, ww + 6, wh - 7, K["frame"])
    c.oval(wx - 3, wy - 3, ww + 6, 30, K["frame"])
    for y in range(wy, wy + wh):
        t = (y - wy) / wh
        col = mix(K["sky_top"], K["sky_mid"], t * 1.6) if t < 0.6 else mix(K["sky_mid"], K["sky"], (t - 0.6) * 2.5)
        for x in range(wx, wx + ww):
            inside = y >= wy + 12 or ((x + 0.5 - (wx + ww / 2)) / (ww / 2)) ** 2 + ((y + 0.5 - (wy + 12)) / 12) ** 2 <= 1
            if inside:
                c.set(x, y, col)
    for sx, sy in ((60, 50), (90, 44), (99, 60), (71, 64)):            # a few early stars
        c.set(sx, sy, "#ffffff")
    c.oval(84, 52, 9, 9, "#fff4c8")                                    # moon
    c.oval(87, 51, 8, 8, mix(K["sky_top"], K["sky_mid"], 0.4))
    c.vline(wx + ww // 2, wy, wy + wh - 1, K["frame"])                 # mullions
    for y in (wy + 30, wy + 56):
        c.hline(wx, wx + ww - 1, y, K["frame"])
    c.rect(wx - 5, wy + wh - 2, ww + 10, 4, K["col_sh"])               # sill
    c.hline(wx - 5, wx + ww + 4, wy + wh - 2, K["col"])
    # column
    for x0 in (0,):
        c.rect(x0 + 6, 22, 20, 100, K["col"])
        for fx in range(x0 + 8, x0 + 25, 4):
            c.vline(fx, 26, 118, K["col_sh"])
            c.vline(fx + 1, 26, 118, K["col_hi"])
        c.rect(x0 + 2, 16, 28, 6, K["col_hi"])                         # capital
        c.rect(x0 + 4, 22, 24, 3, K["col"])
        c.rect(x0 + 3, 118, 26, 4, K["col_hi"])                        # base
    # cornice with dentils
    c.rect(0, 0, FAR_W, 14, K["wall_sh"])
    c.hline(0, FAR_W - 1, 14, K["col_sh"])
    for x in range(0, FAR_W, 6):
        c.rect(x, 10, 3, 4, K["col_sh"])
    # dark wood wainscot
    c.rect(0, 122, FAR_W, FLOOR - 122, K["wain"])
    c.hline(0, FAR_W - 1, 122, K["wain_hi"])
    for x in range(4, FAR_W, 40):
        c.rect(x, 128, 32, 26, K["wain_sh"])
        c.rect(x + 1, 129, 30, 24, K["wain"])
        c.hline(x + 1, x + 30, 129, K["wain_hi"])
    c.rect(0, FLOOR, FAR_W, H - FLOOR, K["wood_dk"])
    return c


# ---------------------------------------------------------------- tiles

def draw_tile(c: Canvas, ch: str, col: int, row: int) -> None:
    x, y = col * TILE, row * TILE
    v = h(col, row)
    above = tile_at(col, row - 1)
    if ch == "#":
        top = above not in "#<"
        c.rect(x, y, TILE, TILE, K["wood"])
        for k in range(0, TILE, 4):                                    # boards
            c.hline(x, x + 15, y + k + 3, K["wood_sh"])
        for k in range(4):
            sx = x + (h(col, row, k) % 16)
            c.vline(sx, y + k * 4, y + k * 4 + 2, K["wood_sh"])
            c.set(sx + 1, y + k * 4, K["wood_hi"])
        if top:
            c.rect(x, y, TILE, 3, K["wood_hi"])                        # polished top
            c.hline(x, x + 15, y + 3, K["wood_dk"])
            paint = court_paint(col)
            for px, pc in paint:
                c.rect(x + px, y, 2, 3, pc)
        if row == ROWS - 1:
            c.rect(x, y + 10, TILE, 6, K["wood_dk"])
    elif ch == "M":
        c.rect(x, y, TILE, TILE, K["marble"])
        c.hline(x, x + 15, y, K["marble_hi"])
        c.vline(x, y, y + 15, K["marble_hi"])
        c.hline(x, x + 15, y + 15, K["marble_sh"])
        c.vline(x + 15, y, y + 15, K["marble_sh"])
        vx = x + 3 + v % 9                                             # a vein
        for k in range(10):
            c.set(vx + round(2 * math.sin(k * 0.7 + v)), y + 3 + k, K["vein"])
    elif ch == "H":
        c.rect(x, y, TILE, TILE, K["hay"])
        for k in range(14):                                            # straw
            sx, sy = x + h(col, row, k) % 15, y + h(k, col, row) % 14
            c.line(sx, sy, sx + 2, sy + 1, K["hay_sh"] if k % 3 else K["hay_hi"])
        c.hline(x, x + 15, y, K["hay_hi"])
        c.hline(x, x + 15, y + 15, K["hay_sh"])
        for tx in (x + 4, x + 11):                                     # twine
            c.vline(tx, y, y + 15, K["twine"])
        for k in range(0, 16, 3):                                      # ragged edge
            c.set(x + k, y - 1, K["hay_sh"])
    elif ch == "C":
        pal = ("case", "case_hi", "case_sh") if (col // 2 + row) % 2 else ("case2", "case2_hi", "case2_sh")
        base, hi, sh = (K[p] for p in pal)
        c.rect(x, y + 2, TILE, 14, base)
        c.hline(x, x + 15, y + 2, hi)
        c.hline(x, x + 15, y + 15, sh)
        c.vline(x + 15, y + 2, y + 15, sh)
        for sx in (x + 3, x + 12):                                     # straps
            c.vline(sx, y + 2, y + 15, K["strap"])
        c.rect(x + 6, y + 7, 4, 3, K["brass"])                         # latch
        c.set(x + 7, y + 8, K["brass_sh"])
        if above != "C":                                               # handle on the top case
            c.hline(x + 5, x + 10, y, K["black"])
            c.vline(x + 5, y, y + 1, K["black"])
            c.vline(x + 10, y, y + 1, K["black"])
        if v % 3 == 0:                                                 # travel sticker
            c.rect(x + 1, y + 10, 4, 3, K["red"] if v % 2 else K["white"])
    elif ch == "-":
        c.rect(x, y, TILE, 5, K["ruler"])
        c.hline(x, x + 15, y + 4, K["ruler_sh"])
        for k in range(0, 16, 2):
            c.vline(x + k, y, y + (2 if (col * 16 + k) % 8 else 3), K["tick"])
    elif ch == "=":
        c.rect(x, y, TILE, 5, K["dock"])
        c.hline(x, x + 15, y, K["dock_hi"])
        c.hline(x, x + 15, y + 4, K["dock_sh"])
        for k in range(0, 16, 6):
            c.vline(x + k + (col % 2), y, y + 4, K["dock_sh"])
        if col % 2 == 0:                                               # pilings down into the water
            c.rect(x + 2, y + 5, 3, H - y - 5, K["dock_sh"])
            c.vline(x + 2, y + 5, H - 1, K["dock"])
    elif ch == "P":
        yy = y + 10
        c.rect(x + 1, yy, 14, 6, K["pad"])
        c.rect(x + 1, yy, 14, 2, K["pad_top"])
        for k in (yy + 3, yy + 5):
            c.hline(x + 2, x + 14, k, K["pad_line"])
        c.vline(x + 4, yy + 2, yy + 5, K["red"])                       # margin
        c.hline(x + 1, x + 14, yy + 6, K["pad_sh"])                    # stack of pages
    elif ch == "<":
        c.rect(x, y, TILE, TILE, K["black"])
        c.rect(x, y, TILE, 4, K["grey_sh"])
        for k in range(0, 16, 4):
            c.vline(x + k, y, y + 3, K["black"])
        c.stamp(x + 5, y + 6, ["..Y", ".YY", "YYY", ".YY", "..Y"], {"Y": K["sign_text"]})
        c.oval(x + 1, y + 12, 4, 4, K["grey"])
        c.oval(x + 10, y + 12, 4, 4, K["grey"])
    elif ch == "^":
        banana_peel(c, x + 2, y + 10)


def banana_peel(c: Canvas, x: int, y: int) -> None:
    c.stamp(x, y, [
        "....SS......",
        "..YYSSYY....",
        ".YiiYYiiY...",
        "YiY.YY.YiY..",
        "Y...YY...YY.",
        "....YY......",
    ], {"Y": K["peel"], "S": K["dock_sh"], "i": K["peel_in"]})


def court_paint(col: int) -> list[tuple[int, str]]:
    """Court markings that land on this column's top edge: (x within tile, color)."""
    marks = []
    for line_col, color in ((10, K["paint"]), (59, K["paint"]), (110, K["paint"]),
                            (103, K["key"]), (104, K["key"]), (116, K["key"])):
        if col == line_col:
            marks.append((7, color))
    if 106 <= col <= 114 and col in (106, 114):                         # center circle
        marks.append((0, K["paint"]))
    return marks


def water(c: Canvas) -> None:
    for col in range(COLS):
        for row in range(ROWS):
            if MAP[row][col] != "~":
                continue
            x, y = col * TILE, row * TILE
            c.rect(x, y + (5 if row == 10 else 0), TILE, TILE - (5 if row == 10 else 0), K["water"])
            if row == 10:
                for k in range(TILE):
                    yy = y + 5 + round(math.sin((x + k) * 0.5))
                    c.set(x + k, yy, K["foam"])
                    c.set(x + k, yy + 1, K["water_hi"])
                for k in range(3):
                    c.hline(x + h(col, k) % 12, x + h(col, k) % 12 + 3, y + 9 + 3 * k, K["water_hi"] if k == 0 else K["water_sh"])
            else:
                c.rect(x, y + 8, TILE, 8, K["water_sh"])


# ---------------------------------------------------------------- props

def order_counter(c: Canvas, thin: Canvas, x: int) -> list[dict]:
    """ORDER HERE (order in the court!). A fast-food counter with a menu of verdicts."""
    y = FLOOR - 24
    c.rect(x, y, 72, 24, K["red"])
    c.rect(x, y, 72, 4, K["white"])
    c.hline(x, x + 71, y + 4, K["grey"])
    for k in range(x + 4, x + 70, 10):
        c.rect(k, y + 8, 6, 12, K["red_sh"])
    c.rect(x + 50, y - 8, 12, 8, K["grey_sh"])                         # register
    c.rect(x + 51, y - 7, 10, 3, K["neon2"])
    c.rect(x + 8, y - 4, 8, 4, K["white"])                             # a tray of fries
    c.stamp(x + 9, y - 8, ["Y.Y.Y", "YYYYY", ".YYY."], {"Y": K["peel"]})
    mx, my = x + 4, 66                                                 # menu board
    sign(c, thin, x + 36, my - 12, ["ORDER HERE"], mount="wall", text=K["white"], plate=K["red_sh"])
    c.rect(mx, my, 64, 40, K["black"])
    c.rect(mx + 1, my + 1, 62, 38, K["sign"])
    draw_text_centered(c, mx + 32, my + 3, "TODAYS RULINGS", K["neon"])
    for i, (item, price) in enumerate((("GUILTY", "2.99"), ("NOT GUILTY", "4.99"),
                                       ("MISTRIAL", "FREE"), ("FRIES", "1.49"))):
        draw_text(c, mx + 4, my + 12 + i * 7, item, K["white"])
        draw_text(c, mx + 60 - text_width(price), my + 12 + i * 7, price, K["sign_text"])
    return [dict(type="oneway", x=x, y=y, w=72, h=4)]


def welcome(c: Canvas, thin: Canvas, x: int) -> None:
    """The big sign over the door, and a basketball hoop, because it is a COURT house."""
    sx, sy = x, 20
    c.rect(sx, sy, 92, 38, K["marble_sh"])
    c.rect(sx + 2, sy + 2, 88, 34, K["marble"])
    draw_text_centered(c, sx + 46, sy + 5, "WELCOME TO THE", K["black"])
    big_text(c, sx + 6, sy + 13, "COURT", K["red"], 2)
    house_icon(c, sx + 58, sy + 12)
    big_text(c, sx + 6, sy + 25, "HOUSE", K["red"], 2)
    for y in range(0, sy):
        thin.set(sx + 8, y, K["grey"] if y % 3 else K["grey_sh"])
        thin.set(sx + 83, y, K["grey"] if y % 3 else K["grey_sh"])


def house_icon(c: Canvas, x: int, y: int) -> None:
    c.stamp(x, y, [
        "......R......",
        ".....RRR.....",
        "....RRRRR....",
        "...RRRRRRR...",
        "..RRRRRRRRR..",
        ".RRRRRRRRRRR.",
        "..WWWWWWWWW..",
        "..WBBWWWdWW..",
        "..WBBWWWdWW..",
        "..WWWWWWdWW..",
        "..WWWWWWdWW..",
    ], {"R": K["red"], "W": K["white"], "B": K["neon2"], "d": K["case"]})
    c.oval(x + 16, y + 4, 9, 9, K["key"])                              # ...and a basketball
    c.vline(x + 20, y + 4, y + 12, K["black"])
    c.hline(x + 16, x + 24, y + 8, K["black"])


def hoop(c: Canvas, thin: Canvas, x: int, facing: int) -> None:
    """Basketball hoop on a pole. facing=+1 rim points right."""
    pole = x
    c.rect(pole - 1, 48, 3, FLOOR - 48, K["grey_sh"])
    c.vline(pole, 48, FLOOR - 1, K["grey"])
    bx = pole + (2 if facing > 0 else -4)
    c.rect(bx, 38, 3, 26, K["white"])                                  # backboard (edge-on)
    rim_x = bx + 3 if facing > 0 else bx - 12
    c.hline(rim_x, rim_x + 11, 56, K["red"])
    for k in range(0, 12, 3):                                          # net
        for yy in range(57, 66):
            thin.set(rim_x + k + (yy - 57) // 4 * (1 if k < 6 else -1), yy, K["white"])


def clothesline(c: Canvas, thin: Canvas, x0: int, x1: int, y: int) -> None:
    """LEGAL BRIEFS: underwear on a line, pegged out to dry."""
    sag = lambda x: y + round(8 * math.sin(math.pi * (x - x0) / (x1 - x0)))
    for x in range(x0, x1 + 1):
        thin.set(x, sag(x), K["white"])
    for x in (x0, x1):
        c.rect(x - 1, sag(x) - 2, 3, FLOOR - sag(x) + 2, K["dock_sh"])
    styles = [("white", "grey"), ("neon2", "case2"), ("red", "red_sh"), ("white", "red"),
              ("pad", "pad_sh"), ("neon", "red_sh"), ("white", "neon2")]
    for i, bx in enumerate(range(x0 + 14, x1 - 10, 26)):
        top = sag(bx + 6) + 1
        base, trim = (K[p] for p in styles[i % len(styles)])
        c.stamp(bx, top, [
            "tttttttttttt",
            "bbbbbbbbbbbb",
            "bbbbbbbbbbbb",
            "bbbbbbbbbbbb",
            ".bbbbbbbbbb.",
            "..bbbttbbb..",
            "...bb..bb...",
        ], {"b": base, "t": trim})
        if i % 2:                                                      # polka dots / stripes
            for dx in (2, 6, 9):
                c.set(bx + dx, top + 2 + dx % 2, trim)
        thin.set(bx + 2, top - 1, K["dock"])                           # pegs
        thin.set(bx + 9, top - 1, K["dock"])
    sign(c, thin, (x0 + x1) // 2, 14, ["LEGAL BRIEFS"], mount="wall")


def bailiff(c: Canvas, face: Canvas, x: int, y: int) -> None:
    """A sheriff's hat and badge, worn by a bale of hay. The face goes on a layer in front of the tiles."""
    c.stamp(x, y - 7, [
        ".....hh.hh.....",
        "....hHHHHHh....",
        "....hHHHHHh....",
        "hh..HHHHHHH..hh",
        ".hhHHHHHHHHHhh.",
        "..hhhhhhhhhhh..",
    ], {"h": K["hat"], "H": K["hat_hi"]})
    c.hline(x + 4, x + 10, y - 3, K["twine"])                          # hatband
    face.stamp(x + 12, y + 8, [".b.", "bBb", ".b."], {"b": K["badge_sh"], "B": K["badge"]})
    face.rect(x + 4, y + 4, 2, 2, K["black"])                          # eyes. it is watching.
    face.rect(x + 9, y + 4, 2, 2, K["black"])
    face.hline(x + 5, x + 9, y + 8, K["twine"])


def rubber_duck(c: Canvas, x: int, y: int) -> None:
    c.stamp(x, y, [
        "...DDD..",
        "..DDDbD.",
        "..DDDDBB",
        "D.DDDD..",
        "DDDDDDD.",
        ".DDDDD..",
    ], {"D": K["duck"], "B": K["beak"], "b": K["black"]})


def bar(c: Canvas, thin: Canvas, x: int) -> list[dict]:
    """THE BAR. You must pass it."""
    y = FLOOR - 26
    c.rect(x + 6, 46, 84, 6, K["wain_hi"])                              # back shelf
    c.rect(x + 6, 72, 84, 4, K["wain_hi"])
    for i, bx in enumerate(range(x + 10, x + 88, 7)):                   # bottles
        col = (K["green"], K["case"], K["neon2"], K["red_sh"])[i % 4]
        for sy in (46, 72):
            c.rect(bx, sy - 8, 4, 8, col)
            c.rect(bx + 1, sy - 11, 2, 3, col)
            c.set(bx + 1, sy - 6, K["white"])
    c.rect(x, y, 96, 26, K["wain"])                                    # counter
    c.rect(x - 2, y, 100, 4, K["wain_hi"])
    c.hline(x - 2, x + 97, y + 4, K["wain_sh"])
    for k in range(x + 4, x + 92, 16):
        c.rect(k, y + 8, 12, 14, K["wain_sh"])
        c.rect(k + 1, y + 9, 10, 12, K["wain"])
    c.hline(x, x + 95, FLOOR - 3, K["brass"])                           # foot rail
    for mx in (x + 14, x + 52, x + 78):                                 # mugs
        c.rect(mx, y - 7, 5, 7, K["pad"])
        c.rect(mx, y - 8, 5, 2, K["white"])
        c.vline(mx + 5, y - 6, y - 3, K["grey"])
    for sx in (x + 10, x + 40, x + 70):                                 # stools
        c.rect(sx, FLOOR - 16, 10, 3, K["red"])
        c.vline(sx + 2, FLOOR - 13, FLOOR - 1, K["grey"])
        c.vline(sx + 7, FLOOR - 13, FLOOR - 1, K["grey"])
    neon_x, neon_y = x + 48, 24
    big_text(c, neon_x - text_width("THE BAR"), neon_y, "THE BAR", K["neon"], 2)
    sign(c, thin, x + 48, 88, ["YOU MUST", "PASS THE BAR"], mount="wall")
    return [dict(type="oneway", x=x - 2, y=y, w=100, h=4),
            dict(type="oneway", x=x + 10, y=FLOOR - 16, w=10, h=3),
            dict(type="oneway", x=x + 40, y=FLOOR - 16, w=10, h=3),
            dict(type="oneway", x=x + 70, y=FLOOR - 16, w=10, h=3)]


def hung_jury(c: Canvas, thin: Canvas, x: int, cast: list) -> None:
    """Twelve portraits of the cast, literally hung."""
    big_text(c, x + 72 - text_width("HUNG JURY"), 18, "HUNG JURY", K["sign_text"], 2)
    for i, ch in enumerate(cast[:12]):
        col, row = i % 6, i // 6
        px, py = x + col * 24 + (2 if row else 0), 40 + row * 32 + (h(i) % 4)
        nail = (px + 10, py - 7 + (h(i, 1) % 3))
        for ex in (px + 2, px + 17):                                    # string
            for xx, yy in _pts(nail, (ex, py)):
                thin.set(xx, yy, K["grey"])
        c.rect(px, py, 20, 20, K["brass"])
        c.rect(px + 1, py + 1, 18, 18, K["brass_sh"])
        c.rect(px + 2, py + 2, 16, 16, mix(K["wall"], K["sky"], 0.25 + 0.1 * (i % 3)))
        c.paste(portrait(ch), px + 2, py + 2)
        c.set(*nail, K["black"])


def _pts(a, b):
    from ..canvas import line_points
    return line_points(a[0], a[1], b[0], b[1])


def portrait(ch) -> Canvas:
    """16x16 head-and-shoulders crop of a character's idle frame."""
    f = ch.frames("idle")[0]
    top = f.bbox()[1]
    xs = [x for y in range(top, top + 10) for x in range(SIZE) if f.opaque(x, y)]
    cx = (min(xs) + max(xs)) // 2
    out = Canvas(16, 16)
    for y in range(16):
        for x in range(16):
            out.set(x, y, f.get(cx - 8 + x, top - 1 + y))
    return out


def jukebox(c: Canvas, thin: Canvas, x: int) -> list[dict]:
    """The JURY BOX (a jukebox). Twelve tiny jurors on the selector."""
    y = FLOOR - 34
    c.rect(x, y + 8, 32, 26, K["red_sh"])
    c.oval(x, y, 32, 18, K["red_sh"])
    c.oval(x + 3, y + 3, 26, 14, K["pad"])
    c.oval(x + 6, y + 6, 20, 10, K["neon"])
    c.rect(x + 3, y + 10, 26, 7, K["pad"])
    c.rect(x + 6, y + 10, 20, 7, K["neon"])
    draw_text_centered(c, x + 16, y + 11, "JURY", K["white"])
    c.rect(x + 4, y + 19, 24, 8, K["black"])
    for i in range(12):                                                 # twelve tiny jurors
        c.set(x + 5 + (i % 6) * 4, y + 21 + (i // 6) * 3, K["sign_text"])
    c.rect(x + 3, y + 29, 26, 3, K["grey"])
    draw_text_centered(c, x + 16, y + 28, "BOX", K["black"])
    for k, (nx, ny) in enumerate(((x + 34, y - 4), (x + 40, y - 12), (x - 6, y - 8))):   # music
        c.stamp(nx, ny, [".NN", ".N.", ".N.", "NN."] if k % 2 else ["N..", "NNN", "N.N", "N.N", "..."][:4],
                {"N": K["neon2"]})
    return [dict(type="oneway", x=x + 2, y=y + 1, w=28, h=4)]


def lemonade_stand(c: Canvas, thin: Canvas, x: int) -> list[dict]:
    """The WITNESS STAND: 5 cents, cash only."""
    y = FLOOR - 26
    c.rect(x + 2, y, 60, 26, K["dock"])
    for k in range(x + 2, x + 62, 6):
        c.vline(k, y + 4, FLOOR - 1, K["dock_sh"])
    c.rect(x, y, 64, 4, K["dock_hi"])
    c.rect(x + 8, y + 7, 48, 13, K["white"])
    draw_text_centered(c, x + 32, y + 8, "WITNESS", K["red"])
    draw_text_centered(c, x + 32, y + 14, "STAND", K["red"])
    c.rect(x + 46, y - 12, 8, 12, K["glass"])                          # pitcher of lemonade
    c.rect(x + 47, y - 8, 6, 8, K["pad"])
    c.vline(x + 54, y - 10, y - 4, K["glass"])
    c.rect(x + 12, y - 5, 4, 5, K["pad"])                              # cups
    c.rect(x + 20, y - 5, 4, 5, K["pad"])
    for px in (x + 3, x + 59):                                          # posts and striped awning
        c.rect(px, FLOOR - 50, 2, 24, K["dock_sh"])
    ay = FLOOR - 56
    for k in range(66):
        c.vline(x - 1 + k, ay, ay + 5, K["red"] if (k // 6) % 2 else K["white"])
    for k in range(0, 66, 6):
        c.oval(x - 1 + k, ay + 4, 6, 4, K["red"] if (k // 6) % 2 else K["white"])
    sign(c, thin, x + 32, ay - 18, ["5 CENTS"], mount="wall", text=K["red"], plate=K["white"])
    return [dict(type="oneway", x=x, y=y, w=64, h=4), dict(type="oneway", x=x - 1, y=ay, w=66, h=4)]


def exhibit_a(c: Canvas, thin: Canvas, x: int) -> list[dict]:
    """EXHIBIT A: a rubber duck, under glass, on a pedestal. Nobody knows why."""
    c.rect(x + 2, FLOOR - 30, 20, 30, K["marble"])
    c.rect(x, FLOOR - 32, 24, 3, K["marble_hi"])
    c.rect(x, FLOOR - 3, 24, 3, K["marble_sh"])
    c.vline(x + 4, FLOOR - 29, FLOOR - 4, K["marble_sh"])
    c.rect(x + 2, FLOOR - 52, 20, 20, K["glass"])
    c.rect(x + 4, FLOOR - 50, 16, 18, mix(K["glass"], K["wall"], 0.5))
    c.vline(x + 5, FLOOR - 49, FLOOR - 42, "#ffffff")
    rubber_duck(c, x + 8, FLOOR - 39)
    c.rect(x + 1, FLOOR - 54, 22, 2, K["brass"])
    sign(c, thin, x + 12, FLOOR - 20, ["A"], mount="wall", text=K["black"], plate=K["brass"])
    sign(c, thin, x + 12, 40, ["EXHIBIT"], mount="chain")
    return [dict(type="oneway", x=x, y=FLOOR - 54, w=24, h=4)]


def news_camera(c: Canvas, thin: Canvas, x: int) -> None:
    """The COURT REPORTER."""
    top = FLOOR - 38
    for dx in (-8, 0, 8):                                              # tripod
        for px, py in _pts((x + 10, top + 12), (x + 10 + dx, FLOOR - 1)):
            c.set(px, py, K["grey_sh"])
    c.rect(x, top, 22, 12, K["black"])
    c.rect(x + 22, top + 2, 6, 8, K["grey_sh"])
    c.oval(x + 24, top + 3, 5, 6, K["neon2"])
    c.oval(x + 2, top - 8, 9, 9, K["grey_sh"])                         # film reels
    c.oval(x + 11, top - 8, 9, 9, K["grey_sh"])
    c.set(x + 6, top - 4, K["black"])
    c.set(x + 15, top - 4, K["black"])
    c.rect(x + 3, top + 3, 3, 3, K["red"])                             # tally light
    sign(c, thin, x + 12, top - 26, ["ON AIR"], mount="wall", text=K["white"], plate=K["red_sh"])
    sign(c, thin, x + 12, 22, ["COURT", "REPORTER"], mount="chain")


def scales_of_justice(c: Canvas, thin: Canvas, x: int) -> None:
    """A balance with a fish on one pan (scales!) and a bathroom scale on the other."""
    beam_y = 46
    for y in range(0, beam_y):
        thin.set(x, y, K["grey"] if y % 3 else K["grey_sh"])
    c.rect(x - 2, beam_y - 3, 5, 5, K["brass"])
    for px, py in _pts((x - 24, beam_y + 3), (x + 24, beam_y - 3)):     # tilted: the fish is heavier
        c.set(px, py, K["brass"])
        c.set(px, py + 1, K["brass_sh"])
    for end_x, end_y, drop in ((x - 24, beam_y + 3, 26), (x + 24, beam_y - 3, 20)):
        for d in (-6, 6):
            for px, py in _pts((end_x, end_y), (end_x + d, end_y + drop)):
                thin.set(px, py, K["brass_sh"])
        c.rect(end_x - 8, end_y + drop, 17, 3, K["brass"])
        c.hline(end_x - 6, end_x + 6, end_y + drop + 3, K["brass_sh"])
    fx, fy = x - 33, beam_y + 21                                        # the fish
    c.stamp(fx, fy, [
        "......ff.......",
        "...FFFFFFF...t.",
        "..FFsFsFsFF.tt.",
        ".FeFFsFsFsFFtt.",
        "..FFFFFFFFF.tt.",
        "...FFFFFFF...t.",
    ], {"F": K["fish"], "f": K["fish_sh"], "s": K["fish_hi"], "e": K["black"], "t": K["fish_sh"]})
    sx, sy = x + 18, beam_y + 9                                         # the bathroom scale
    c.rect(sx, sy, 13, 8, K["white"])
    c.rect(sx + 3, sy + 1, 7, 3, K["black"])
    c.set(sx + 6, sy + 2, K["red"])
    sign(c, thin, x, 74, ["SCALES OF JUSTICE"], mount="wall")


def park_bench(c: Canvas, x: int) -> list[dict]:
    """THE BENCH."""
    seat = FLOOR - 12
    for lx in (x + 4, x + 40):
        c.rect(lx, seat, 3, 12, K["black"])
        c.rect(lx - 1, FLOOR - 2, 5, 2, K["black"])
        c.vline(lx + 1, seat - 14, seat, K["black"])
    c.rect(x, seat, 48, 3, K["green"])
    c.hline(x, x + 47, seat + 3, K["green_sh"])
    for k in (seat - 13, seat - 8):                                     # backrest slats
        c.rect(x + 1, k, 46, 3, K["green"])
        c.hline(x + 1, x + 46, k + 2, K["green_sh"])
    c.stamp(x + 20, seat - 5, ["bbbbbbbb"], {"b": K["brass"]})         # memorial plaque
    return [dict(type="oneway", x=x, y=seat, w=48, h=3)]


def bone(c: Canvas, x: int, y: int) -> None:
    c.stamp(x, y, ["WW......WW", "WWWWWWWWWW", "WW......WW"], {"W": K["white"]})


# ---------------------------------------------------------------- assembly

def tile_colliders() -> list[dict]:
    """One rect per horizontal run of same-kind tiles."""
    out = []
    for r, row in enumerate(MAP):
        c = 0
        while c < COLS:
            ch = row[c]
            if ch not in LEGEND:
                c += 1
                continue
            c1 = c
            while c1 + 1 < COLS and row[c1 + 1] == ch:
                c1 += 1
            name, kind = LEGEND[ch]
            dy, hh = INSET.get(name, (0, TILE))
            if name == "water" and tile_at(c, r - 1) == "~":                      # only the surface is inset
                dy, hh = 0, TILE
            rect = dict(type=kind, x=c * TILE, y=r * TILE + dy, w=(c1 - c + 1) * TILE, h=hh, tile=name)
            if kind == "conveyor":
                rect["push"] = -60
            if kind == "bounce":
                rect["launch"] = 420
            out.append(rect)
            c = c1 + 1
    # stacked solid (or water) runs of the same width merge vertically, so a wall is one rect
    merged: list[dict] = []
    for rect in out:
        prev = next((m for m in merged if m["type"] == rect["type"] in ("solid", "water") and m["x"] == rect["x"]
                     and m["w"] == rect["w"] and m["y"] + m["h"] == rect["y"]), None)
        if prev:
            prev["h"] += rect["h"]
        else:
            merged.append(rect)
    return merged


def render(cast: list | None = None) -> tuple[Canvas, Canvas, list[dict]]:
    """Returns (far wall, level, prop colliders)."""
    from ..characters import roster
    cast = cast or [c for c in roster() if c.kind == "control"]

    thin, deco, wet, tiles, front = (Canvas(W, H) for _ in range(5))
    props: list[dict] = []
    T = TILE
    # LOBBY
    welcome(deco, thin, T + 8)
    props += order_counter(deco, thin, 6 * T)
    sign(deco, thin, 14 * T, 120, ["ALL", "RISE"], mount="wall")
    for k in range(3):                                                  # arrows pointing up at the ceiling
        deco.stamp(13 * T + 4 + 10 * k, 102, ["..Y..", ".YYY.", "YYYYY", "..Y..", "..Y.."], {"Y": K["sign_text"]})
    bone(deco, 16 * T + 6, 5 * T - 3)
    sign(deco, thin, 17 * T, 22, ["PRO BONO"])
    hoop(deco, thin, 11 * T + 4, 1)
    # COURT OF APPEALS
    clothesline(deco, thin, 21 * T, 38 * T, 36)
    sign(deco, thin, 23 * T, 98, ["COURT OF", "APPEALS"], mount="post")
    sign(deco, thin, 34 * T, 58, ["CASE", "CLOSED"], mount="wall", text=K["red"], plate=K["white"])
    # THE DOCK / OVERRULED
    bailiff(deco, front, 42 * T + 8, 8 * T)
    sign(deco, thin, 41 * T, 88, ["BAILIFF"], mount="wall")
    sign(deco, thin, 50 * T + 8, 40, ["OVERRULED"])
    sign(deco, thin, 45 * T, 104, ["THE", "DOCK"], mount="wall")
    rubber_duck(wet, 50 * T, FLOOR + 1)
    # THE BAR
    props += bar(deco, thin, 62 * T + 8)
    hung_jury(deco, thin, 70 * T, cast)
    props += jukebox(deco, thin, 76 * T + 8)
    # WITNESS STAND
    props += lemonade_stand(deco, thin, 81 * T + 8)
    props += exhibit_a(deco, thin, 87 * T + 8)
    news_camera(deco, thin, 90 * T)
    sign(deco, thin, 96 * T, 96, ["MOTION TO", "DISMISS"], mount="wall")
    for k in range(3):
        deco.stamp(94 * T + 10 + 12 * k, 118, ["..Y", ".YY", "YYY", ".YY", "..Y"], {"Y": K["sign_text"]})
    # THE BENCH
    hoop(deco, thin, 101 * T + 4, 1)
    hoop(deco, thin, 118 * T + 4, -1)
    scales_of_justice(deco, thin, 105 * T)
    props += park_bench(deco, 109 * T)
    sign(deco, thin, 107 * T - 8, 98, ["APPROACH", "THE BENCH"], mount="post")
    big_text(deco, 108 * T - 4, 18, "ALL HAIL", SPAGHETTI_JUDGE["noodle"], 2)

    for col in range(COLS):
        for row in range(ROWS):
            ch = MAP[row][col]
            if ch not in ".~":
                draw_tile(tiles, ch, col, row)
    water(wet)

    deco.outline(OUTLINE)
    tiles.outline(OUTLINE)
    level = Canvas(W, H)
    for layer in (thin, deco, wet, tiles, front):
        level.paste(layer)
    return far_wall(), level, props


def judge_sheet(frames: dict[str, list[Canvas]]) -> Image.Image:
    cols = max(len(f) for f in frames.values())
    img = Image.new("RGBA", (cols * judge.W, len(frames) * judge.H), (0, 0, 0, 0))
    for row, anim in enumerate(frames):
        for col, f in enumerate(frames[anim]):
            img.alpha_composite(f.to_image(), (col * judge.W, row * judge.H))
    return img


BOSS_HOME = (112 * TILE, FLOOR - 76)       # top-left of the judge's frame while hovering in the arena
CHECKPOINTS = [(2 * TILE, FLOOR), (38 * TILE, FLOOR), (58 * TILE, FLOOR), (80 * TILE, FLOOR), (100 * TILE, FLOOR)]


def data(props: list[dict]) -> dict:
    return {
        "name": NAME,
        "tile": TILE,
        "size": [W, H],
        "view": list(VIEW),
        "camera_y": H - VIEW[1],
        "floor_y": FLOOR,
        "layers": [
            {"image": "far.png", "parallax": 0.5, "repeat_x": True},
            {"image": "level.png", "parallax": 1.0},
        ],
        "map": MAP,
        "legend": {ch: {"tile": name, "collider": kind} for ch, (name, kind) in LEGEND.items()},
        "colliders": tile_colliders() + props,
        "collider_types": {
            "solid": "blocks from every side",
            "oneway": "stand on the top edge; jump up through it",
            "bounce": "oneway, and landing launches you upward at `launch` px/s",
            "conveyor": "solid, and pushes anything standing on it `push` px/s",
            "hazard": "banana peel: touching it while grounded makes you slip (hurt)",
            "water": "fall in and you're done (death, respawn at the last checkpoint)",
        },
        "spawn": [TILE * 2, FLOOR],
        "checkpoints": [list(p) for p in CHECKPOINTS],
        "zones": [{"name": n, "x0": a * TILE, "x1": (b + 1) * TILE} for n, a, b in ZONES],
        "boss": {
            "slug": judge.SLUG,
            "name": judge.NAME,
            "sheet": f"{judge.SLUG}.png",
            "frame_size": [judge.W, judge.H],
            "facing": "right",
            "home": list(BOSS_HOME),
            "arena": [100 * TILE, (COLS - 1) * TILE],
            "hits": 6,
            "attack_point": list(judge.IMPACT),
            "animations": {a: {"row": r, "frames": n, "fps": judge.FPS[a], "loop": judge.LOOP[a],
                               "notes": judge.NOTES[a]} for r, (a, n) in enumerate(judge.ANIMATIONS.items())},
        },
    }


def build(out: Path) -> dict:
    d = out / "levels" / SLUG
    d.mkdir(parents=True, exist_ok=True)
    far, level, props = render()
    far.to_image().save(d / "far.png")
    level.to_image().save(d / "level.png")
    frames = judge.all_frames()
    judge_sheet(frames).save(d / f"{judge.SLUG}.png")
    info = data(props)
    (d / "level.json").write_text(json.dumps(info, indent=1) + "\n")
    (out / "previews").mkdir(parents=True, exist_ok=True)
    preview(far, level, frames).save(out / "previews" / f"level_{SLUG}.png")
    judge_gif(far, frames, out / "previews" / f"{judge.SLUG}.gif")
    print(f"  level      {SLUG}")
    return info


def composite(far: Canvas, level: Canvas, x0: int = 0, w: int = W) -> Canvas:
    """The level as the camera would see it with its left edge at x0 (far wall at half speed)."""
    c = Canvas(w, H)
    for x in range(w):
        fx = (x + x0 // 2) % FAR_W
        for y in range(H):
            c.px[y][x] = far.px[y][fx]
    for y in range(H):
        for x in range(w):
            p = level.px[y][x0 + x] if 0 <= x0 + x < W else None
            if p is not None:
                c.px[y][x] = p
    return c


def preview(far: Canvas, level: Canvas, frames: dict, scale: int = 2) -> Image.Image:
    """The whole level in two strips, with the judge in place and zone labels."""
    from ..characters import roster
    half = W // 2
    out = Canvas(half, 2 * (H + 10))
    out.rect(0, 0, out.w, out.h, K["frame"])
    full = composite(far, level, 0, W)
    hero = next(c for c in roster() if c.slug == "tech_bro").frames("idle")[0]
    full.paste(hero, 2 * TILE - SIZE // 2, FLOOR - 46)
    full.paste(frames["idle"][0].flipped(), *BOSS_HOME)
    for i in range(2):
        y0 = i * (H + 10) + 10
        for y in range(H):
            out.px[y0 + y][:] = full.px[y][i * half:(i + 1) * half]
        for name, a, b in ZONES:
            x = a * TILE - i * half
            if 0 <= x < half:
                draw_text(out, x + 2, y0 - 7, name, K["sign_text"])
    return out.to_image(scale)


JUDGE_GIF = [("idle", 3), ("fly", 3), ("attack", 2), ("hurt", 2), ("death", 1)]


def judge_gif(far: Canvas, frames: dict, path: Path, scale: int = 5) -> None:
    """The judge doing everything, in front of the courthouse wall."""
    bg = Canvas(96, 96)
    for y in range(96):
        for x in range(96):
            bg.px[y][x] = far.px[y + H - 96][(x + 40) % FAR_W]
    images, durations = [], []
    for anim, repeats in JUDGE_GIF:
        for _ in range(repeats):
            for f in frames[anim]:
                c = Canvas(96, 96)
                c.paste(bg)
                c.paste(f, 8, 96 - judge.H - 16)
                draw_text(c, 3, 3, anim, K["sign_text"])
                images.append(c.to_image(scale).convert("RGB"))
                durations.append(1000 // judge.FPS[anim])
    durations[-1] = 1500
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0, disposal=2)


def main() -> None:
    build(ROOT / "assets")


if __name__ == "__main__":
    main()
