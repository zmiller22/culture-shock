"""Primordial Soup art: the critters, the stockpot, the living soup, and the
mad-science kitchen they all run around in.

Same canvas, palette and 1px outline as the main cast and Stork Bomber. The
helpers (polygons, layered outlining, DNA helices) come from Stork Bomber.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.effects import GOO, GOO_HI
from sprites.font import draw_text, text_width
from sprites.palette import INK, LAB_BG, LAB_DIM, LAB_FLOOR, MUTANT, OUTLINE

from ..stork_bomber.art import layered, poly
from .people import CHEF

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

STEEL = {"base": "#9aa0b0", "hi": "#d0d4e0", "sh": "#5a6070", "dk": "#3a3f4e", "shine": "#f4f4f4"}
FLAME = ("#5ff3ff", "#2a6ac8", "#ffffff")
GOO_SH, GOO_DK, GOO_IN = "#4a9a2a", "#2a5a1a", "#5aa83a"
SOUP_STAGES = ["#6a5a3a", "#6a7a34", "#5a9234", "#7fd13b"]      # murky broth -> living green
SOUP_HI = ["#8a7a54", "#8aa04a", "#8acc4a", "#d4ff7a"]
EYE_W, IRIS, MOUTH, TOOTH = "#f4f4f4", "#e83b3b", MUTANT["mouth"], "#f0eccc"


def dither(c: Canvas, x0: int, y0: int, x1: int, y1: int, src: str, dst: str, level: float) -> None:
    """Ordered-dither src pixels toward dst in the box, at level 0..1."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if c.get(x, y) == src and BAYER[y % 4][x % 4] < level * 16:
                c.set(x, y, dst)


# -- critters -----------------------------------------------------------------------

CRIT_W, CRIT_H = 16, 14
CRIT_FEET = 12                   # row the feet touch
CRITTERS = ("eyeball", "tadpole", "amoeba", "trilobite", "brainbug")
CRIT_NAMES = {"eyeball": "EYEBALL", "tadpole": "WALKING FISH", "amoeba": "AMOEBA",
              "trilobite": "TRILOBITE", "brainbug": "BRAIN BUG"}


def critter(kind: str, frame: int) -> Canvas:
    """A tiny lab escapee, right-facing. frame 0/1 scuttles; 2/3 squirm (held)."""
    held = frame >= 2
    f = frame % 2
    s = 1 if f else -1                                   # leg phase

    def eyeball(c: Canvas) -> None:
        for i, lx in enumerate((5, 7, 9, 11)):
            out = -2 if i < 2 else 2
            end = (lx + out + s * (1 if i % 2 else -1), 6 if held else 12)
            c.line(lx, 8, end[0], end[1], "#3a2f44")
        c.oval(3, 1, 10, 10, EYE_W)
        for x, y in ((4, 6), (5, 8), (6, 9), (4, 4)):
            c.set(x, y, "#ff8a9a")                       # bloodshot
        c.oval(8, 3, 5, 5, IRIS)
        c.rect(10, 4 + (2 if held else 0), 2, 2, INK)
        c.set(9, 4, "#ffffff")

    def tadpole(c: Canvas) -> None:
        body, belly = "#4a9a6a", "#9ad08a"
        c.oval(4, 4, 10, 7, body)
        c.hline(6, 11, 9, belly)
        c.hline(7, 10, 10, belly)
        wig = (s * 2) if not held else (3 if frame == 2 else -3)
        c.line(4, 7, 1, 7 + wig // 2, body, width=1)
        c.line(1, 7 + wig // 2, 0, 7 + wig, body)
        c.set(2, 6 + wig // 2, "#6ab88a")
        c.oval(10, 4, 3, 3, EYE_W)
        c.set(11, 5, INK)
        for lx in (6, 10):                               # it's evolving: little legs
            c.line(lx, 10, lx + s, 12, "#3a7a4a")
        c.set(13, 8, "#2a5a3a")                          # mouth

    def amoeba(c: Canvas) -> None:
        blob, spot = "#b07ad0", "#e0b8f0"
        c.oval(2, 4, 12, 8, blob)
        for bx, by, bw in (((0, 6, 5), (11, 3, 5), (6, 9, 5)) if f else ((1, 3, 5), (12, 6, 4), (3, 9, 5))):
            c.oval(bx, by, bw, 4, blob)                  # pseudopods
        if held:
            c.oval(5, 1, 6, 5, blob)
        c.oval(6, 6, 4, 3, MUTANT["tent_sh"])            # nucleus
        c.set(7, 7, spot)
        c.set(4, 6, spot)
        c.set(11, 9, spot)
        c.set(11, 5, EYE_W)
        c.set(13, 5, EYE_W)
        c.set(12, 5, INK)

    def trilobite(c: Canvas) -> None:
        shell, seg, head = "#8a7a6a", "#6a5a4a", "#b0a088"
        for lx in range(4, 13, 2):
            c.set(lx + (s if (lx // 2) % 2 else -s), 12 if not held else 3, "#5a4a3a")
        c.oval(2, 5, 12, 7, shell)
        for x in range(4, 11, 2):
            c.vline(x, 6, 10, seg)
        c.oval(10, 5, 5, 6, head)
        c.set(12, 6, INK)
        c.line(13, 6, 15, 2 + f, "#5a4a3a")
        c.line(12, 5, 13, 1, "#5a4a3a")

    def brainbug(c: Canvas) -> None:
        brain, gyri = MUTANT["brain"], MUTANT["brain_dk"]
        for i, tx in enumerate((5, 8, 11)):
            wob = s if i % 2 else -s
            if held:
                c.line(tx, 8, tx + wob * 2, 12, MUTANT["tent"])
            else:
                c.line(tx, 8, tx + wob, 10, MUTANT["tent"])
                c.line(tx + wob, 10, tx - wob, 12, MUTANT["tent"])
        c.oval(3, 1, 11, 8, brain)
        for x, y in ((5, 3), (6, 4), (8, 2), (9, 3), (6, 6), (7, 6), (10, 5), (11, 4)):
            c.set(x, y, gyri)
        c.vline(8, 2, 7, gyri)
        c.oval(11, 4, 3, 3, EYE_W)
        c.set(12, 5, INK)

    draw = {"eyeball": eyeball, "tadpole": tadpole, "amoeba": amoeba,
            "trilobite": trilobite, "brainbug": brainbug}[kind]
    return layered(CRIT_W, CRIT_H, [draw])


def stars() -> Canvas:
    """Dizzy stars that circle a stunned critter (or chef)."""
    c = Canvas(7, 7)
    c.stamp(1, 1, ["..#..", ".###.", "#####", ".###.", "..#.."], {"#": "#fff27a"})
    c.set(3, 3, "#ffffff")
    c.outline(OUTLINE)
    return c


# -- the stockpot -----------------------------------------------------------------------

POT_W, POT_H = 64, 58
POT_FEET = 55                    # floor row
POT_RIM = (32, 16)               # center of the rim ellipse (seen from above, so it's round-ish)
POT_RX, POT_RY = 27, 10
SOUP_TOP = 17                    # row of the soup surface's center


def pot_back(frame: int, level: int) -> Canvas:
    """The open top of the pot: the far rim and the soup surface, bubbling.
    level 0..3: how alive the soup is."""
    soup, hi = SOUP_STAGES[min(level, 3)], SOUP_HI[min(level, 3)]
    rng = random.Random(frame * 7 + level)

    def top(c: Canvas) -> None:
        cx, cy = POT_RIM
        c.oval(cx - POT_RX, cy - POT_RY, POT_RX * 2, POT_RY * 2 + 1, STEEL["hi"])
        c.oval(cx - POT_RX + 3, cy - POT_RY + 2, POT_RX * 2 - 6, POT_RY * 2 - 3, STEEL["dk"])
        c.oval(cx - POT_RX + 3, cy - POT_RY + 4, POT_RX * 2 - 6, POT_RY * 2 - 4, soup)
        for _ in range(3 + level * 2):                      # bubbles
            bx, by = cx + rng.randint(-18, 18), cy + rng.randint(-1, 3)
            r = rng.choice((1, 1, 2))
            if c.get(bx, by) == soup:
                c.oval(bx - r, by - r, 2 * r + 1, 2 * r, hi)
                c.set(bx, by - r + 1 if r > 1 else by, "#ffffff" if level >= 3 else hi)
        if level:
            for i in range(level):                          # bits of things floating in it
                bx = cx - 14 + i * 11 + (frame % 2)
                c.set(bx, cy + 2, EYE_W)
                c.set(bx + 1, cy + 2, IRIS)

    return layered(POT_W, POT_H, [top])


def pot_front(frame: int, shake: int = 0) -> Canvas:
    """Pot body, near rim, handles and the gas ring under it, flames flickering."""
    cx, cy = POT_RIM

    def stand(c: Canvas) -> None:
        for lx in (12, 50):
            c.line(lx, 46, lx - (2 if lx < cx else -2), POT_FEET, STEEL["dk"], width=2)
        c.hline(14, 50, 49, STEEL["dk"])
        for i, fx in enumerate(range(18, 48, 4)):          # flames licking the bottom
            h = 3 + (frame + i) % 3
            c.vline(fx, 48 - h, 48, FLAME[1])
            c.vline(fx, 49 - h + 1, 47, FLAME[0])
            if (frame + i) % 3 == 2:
                c.set(fx, 48 - h, FLAME[2])

    def body(c: Canvas) -> None:
        for y in range(cy, 45):
            taper = (y - cy) // 12
            c.hline(cx - POT_RX + 1 + taper, cx + POT_RX - 1 - taper, y, STEEL["base"])
        c.oval(cx - POT_RX + 3, 41, POT_RX * 2 - 6, 6, STEEL["base"])
        for y in range(cy, 47):                             # shading bands
            for x in range(c.w):
                if c.get(x, y) == STEEL["base"]:
                    if x < cx - 18:
                        c.set(x, y, STEEL["sh"] if x < cx - 22 or BAYER[y % 4][x % 4] < 8 else STEEL["base"])
                    elif cx + 10 <= x <= cx + 14:
                        c.set(x, y, STEEL["hi"])
                    elif x == cx + 12:
                        c.set(x, y, STEEL["shine"])
        c.hline(cx - POT_RX + 2, cx + POT_RX - 2, 44, STEEL["sh"])
        for side in (-1, 1):                                # handles
            hx = cx + side * (POT_RX + 2)
            c.rect(hx - 2, cy + 3, 4, 2, STEEL["dk"])
            c.rect(hx - 2 + side * 2, cy + 3, 2, 7, STEEL["dk"])
            c.rect(hx - 2, cy + 8, 4, 2, STEEL["dk"])
        for rx in (cx - 20, cx - 8, cx + 4, cx + 16):       # rivets
            c.set(rx, cy + 6, STEEL["hi"])
        # near half of the rim, so whatever is in the pot sits behind it
        for y in range(cy, cy + POT_RY + 1):
            dy = (y + 0.5 - cy) / POT_RY
            if dy >= 1:
                continue
            w = POT_RX * math.sqrt(1 - dy * dy)
            c.hline(round(cx - w), round(cx + w) - 1, y, STEEL["hi"] if y > cy + POT_RY - 3 else STEEL["base"])
        c.hline(cx - POT_RX + 4, cx + POT_RX - 5, cy + POT_RY - 1, STEEL["shine"])
        # a label, because it's that kind of lab
        draw_text(c, cx - text_width("SOUP") // 2, cy + 18, "SOUP", STEEL["sh"])

    out = layered(POT_W, POT_H, [stand, body])
    if shake:
        moved = Canvas(POT_W, POT_H)
        moved.paste(out, shake, 0)
        return moved
    return out


# -- the soup, alive -------------------------------------------------------------------

SLIME_W, SLIME_H = 104, 100
SLIME_BASE = 96                  # bottom row of the body: sits on the floor (or in the pot)
SLIME_CX = SLIME_W // 2


def slime(w: int, h: int, frame: int, mouth: str = "closed", hat: bool = False,
          inside: list[tuple[Canvas, int, int, float]] | None = None, facing_eye: int = 1) -> Canvas:
    """The living soup: a w x h blob of goo with too many eyes, right-facing.

    mouth: "closed" | "open" (roaring, lunging) | "chew" | "grin"
    hat: wearing the chef's toque
    inside: (canvas, dx, dy, amount) things floating inside the body, offset from
      the body's bottom-center, dissolved by `amount` (0 = intact, 1 = gone).
    """
    ph = 2 * math.pi * frame / 4
    cx, base = SLIME_CX, SLIME_BASE
    top = base - h

    def body_shape(c: Canvas, col: str) -> None:
        c.oval(cx - w // 2, top + h // 4, w, h - h // 4 + 1, col)
        c.oval(cx - w // 2 + 4, top + 2, w - 8, h * 2 // 3, col)
        for i, (fx, fr) in enumerate(((-0.28, 0.32), (0.05, 0.36), (0.3, 0.28))):   # lumps on top
            r = round(w * fr / 2)
            x = round(cx + fx * w + 1.5 * math.sin(ph + i * 2))
            y = round(top + 3 + 1.5 * math.cos(ph + i * 1.7))
            c.oval(x - r, y - r // 2, 2 * r, r + 4, col)
        for i in range(-3, 4):                                       # it puddles out at the base
            x = cx + i * w // 7
            c.oval(x - 4, base - 4, 9, 5, col)

    def arms(c: Canvas) -> None:
        raise_ = {"open": -0.55, "grin": -0.85}.get(mouth, 0.15)
        for side in (-1, 1):
            sx, sy = cx + side * (w // 2 - 4), base - h // 2
            ex = sx + side * (w // 4 + 2)
            ey = round(sy + raise_ * h * 0.5 + 2 * math.sin(ph + side))
            c.stroke(sx, sy, ex, ey, GOO, 5)
            c.oval(ex - 4, ey - 4, 9, 8, GOO)
            c.set(ex + side * 3, ey + 4, GOO_SH)                      # drip off the fist
            c.vline(ex + side * 3, ey + 5, ey + 6 + frame % 2, GOO)

    def body(c: Canvas) -> None:
        body_shape(c, GOO)
        mask = [[c.get(x, y) is not None for x in range(c.w)] for y in range(c.h)]
        for y in range(c.h):                                         # shade: left and underside
            for x in range(c.w):
                if not mask[y][x]:
                    continue
                d = (x - (cx - w * 0.15)) / (w / 2) - (y - (top + h * 0.2)) / (h * 1.4)
                if d < -0.75:
                    c.set(x, y, GOO_DK if d < -1.15 else GOO_SH if BAYER[y % 4][x % 4] < 10 else GOO)
                elif d > 0.55 and BAYER[y % 4][x % 4] < (d - 0.55) * 30:
                    c.set(x, y, GOO_HI)
        for thing, dx, dy, amount in inside or []:                   # swallowed, floating, dissolving
            ox, oy = cx + dx - thing.w // 2, base + dy - thing.h
            for y in range(thing.h):
                for x in range(thing.w):
                    p = thing.px[y][x]
                    X, Y = ox + x, oy + y
                    if p and 0 <= X < c.w and 0 <= Y < c.h and mask[Y][X]:
                        if amount > 0 and BAYER[Y % 4][X % 4] < amount * 16:
                            continue
                        c.set(X, Y, mix(p, GOO_IN, 0.35 + 0.4 * amount))
        rng = random.Random(3)
        for i in range(7):                                           # bubbles rising inside
            bx = cx + rng.randint(-w // 3, w // 3)
            by = base - 6 - (rng.randint(0, h) + frame * 5 + i * 3) % max(1, h - 12)
            if 0 <= by < c.h and mask[by][bx]:
                c.set(bx, by, GOO_HI)
                c.set(bx + 1, by, "#ffffff")
        # eyes: one of them used to be the eyeball critter
        look = facing_eye
        for fx, fy, size, iris in ((0.12, 0.28, 9, IRIS), (-0.2, 0.22, 7, "#ffd93a"),
                                   (0.32, 0.12, 5, "#5ff3ff"), (-0.04, 0.06, 5, "#ff9ab8"),
                                   (-0.36, 0.42, 4, "#ffd93a")):
            ex, ey = round(cx + fx * w), round(top + fy * h + 2)
            blink = (frame + round(fx * 10)) % 4 == 3 and size < 9
            if blink:
                c.hline(ex - size // 2, ex + size // 2, ey + size // 2, GOO_DK)
                continue
            c.oval(ex - size // 2, ey, size, size, EYE_W)
            r = max(2, size // 2)
            ix = ex - r // 2 + look * (size // 4)
            c.oval(ix, ey + (size - r) // 2, r, r, iris)
            c.set(ix + r // 2 + (look > 0), ey + size // 2, INK)
            c.set(ex - size // 2 + 1, ey + 1, "#ffffff")
        # mouth
        mx, my = round(cx + 0.06 * w), round(top + h * 0.58)
        mw = round(w * 0.5)
        if mouth in ("open", "grin"):
            mh = round(h * (0.3 if mouth == "open" else 0.14))
            c.oval(mx - mw // 2, my - mh // 3, mw, mh, MOUTH)
            for tx in range(mx - mw // 2 + 3, mx + mw // 2 - 2, 4):  # teeth, top and bottom
                c.vline(tx, my - mh // 3 + 1, my - mh // 3 + 2, TOOTH)
                c.set(tx + 1, my - mh // 3 + 1, TOOTH)
                if mouth == "open":
                    c.vline(tx + 2, my + mh * 2 // 3 - 3, my + mh * 2 // 3 - 2, TOOTH)
            if mouth == "open":
                c.oval(mx - 4, my + mh // 3, 9, 4, "#e0607a")         # tongue
        elif mouth == "chew":
            for i, x in enumerate(range(mx - mw // 2, mx + mw // 2)):
                c.set(x, my + (1 if (i // 3 + frame) % 2 else -1), MOUTH)
        else:
            for i, x in enumerate(range(mx - mw // 2, mx + mw // 2)):
                c.set(x, my + round(math.sin(i * 0.7 + ph)), MOUTH)
        # drips off the bottom edge
        for i in range(-2, 3):
            x = cx + i * w // 5 + 2
            if mask[base - 2][x] if 0 <= base - 2 < c.h and 0 <= x < c.w else False:
                c.vline(x, base, base + 1 + (frame + i) % 3, GOO)

    def toque(c: Canvas) -> None:
        tx, ty = cx - 9 + round(w * 0.05), top - 9         # the chef's hat, a bit askew
        c.stamp(tx, ty, ["...WWW..WWWW....", "..WWWWWWWWWWWW..", ".WWWWWWWWWWWWWW.", "WWWWWWWWWWWWWWWW",
                         "WWWWWWWWWWWWWWWw", ".wWWWWWWWWWWWWw.", "..wWWWWWWWWWWw..", "..WWWWWWWWWWWW..",
                         "..wWWWWWWWWWWw..", "..bbbbbbbbbbbb..", "..bbbbbbbbbbbb.."],
                {"W": CHEF["white"], "w": CHEF["white_sh"], "b": CHEF["white_dk"]})
        c.set(tx + 5, ty + 2, "#ffffff")

    layers = [arms, body] + ([toque] if hat else [])
    return layered(SLIME_W, SLIME_H, layers)


# -- props, hazards and bits of mess --------------------------------------------------------

UTENSILS = ("pan", "cleaver", "ladle", "whisk", "rolling_pin")
UT_SIZE = 16


def utensil(kind: str) -> Canvas:
    """A kitchen tool, about UT_SIZE square, hanging handle-up."""
    def draw(c: Canvas) -> None:
        if kind == "pan":
            c.rect(7, 0, 2, 6, "#3a2a1e")
            c.oval(1, 5, 14, 11, "#2a2a3a")
            c.oval(3, 7, 10, 7, "#3a3f4e")
            c.set(4, 8, STEEL["hi"])
        elif kind == "cleaver":
            c.rect(7, 0, 2, 5, "#5a3a22")
            c.rect(3, 5, 10, 9, STEEL["base"])
            c.vline(3, 5, 13, STEEL["sh"])
            c.vline(12, 6, 13, STEEL["shine"])
            c.set(5, 7, STEEL["dk"])
        elif kind == "ladle":
            c.vline(8, 0, 9, STEEL["hi"])
            c.vline(7, 0, 9, STEEL["base"])
            c.oval(3, 9, 10, 6, STEEL["base"])
            c.hline(5, 10, 10, STEEL["dk"])
        elif kind == "whisk":
            c.rect(7, 0, 2, 5, "#e83b3b")
            for dx in (-3, -1, 1, 3):
                c.line(8, 5, 8 + dx, 10, STEEL["hi"])
                c.line(8 + dx, 10, 8, 15, STEEL["base"])
        else:                                                        # rolling pin, hung by a string
            c.vline(8, 0, 4, "#c8c8d8")
            c.rect(2, 5, 12, 5, "#d89a5a")
            c.hline(2, 13, 6, "#ecb878")
            c.rect(0, 6, 2, 3, "#8a5a2e")
            c.rect(14, 6, 2, 3, "#8a5a2e")
    return layered(UT_SIZE, UT_SIZE, [draw])


def grease(w: int, h: int) -> Canvas:
    """A slick of spilled fry oil on the floor."""
    c = Canvas(w + 2, h + 2)
    c.oval(1, 1, w, h, "#8a6a1a")
    c.oval(3, 2, w - 6, h - 3, "#a8842a")
    c.hline(w // 3, w // 2, 2, "#f0d27a")
    c.set(w * 2 // 3, h - 1, "#f0d27a")
    return c


def goo_splat(w: int) -> Canvas:
    c = Canvas(w + 2, 6)
    c.oval(1, 1, w, 4, GOO)
    c.hline(2, w - 1, 4, GOO_SH)
    c.set(3, 1, GOO_HI)
    c.outline(OUTLINE)
    return c


def drop(color: str, hi: str) -> Canvas:
    c = Canvas(5, 5)
    c.stamp(1, 1, [".#.", "###", ".#."], {"#": color})
    c.set(2, 2, hi)
    c.outline(OUTLINE)
    return c


def plate() -> Canvas:
    c = Canvas(12, 6)
    c.oval(1, 1, 10, 4, "#f4f4f4")
    c.oval(3, 2, 6, 2, "#c8c8d8")
    c.hline(2, 9, 4, "#5f9fd8")
    c.outline(OUTLINE)
    return c


def shard(frame: int) -> Canvas:
    c = Canvas(6, 6)
    c.stamp(1, 1, (["##..", ".##.", "..#."], ["#...", "###.", ".#.."])[frame % 2], {"#": "#f4f4f4"})
    c.outline(OUTLINE)
    return c


def steam(frame: int) -> Canvas:
    c = Canvas(10, 12)
    r = 2 + frame
    c.oval(5 - r, 11 - 2 * r - frame * 2, 2 * r, 2 * r, "#dce4f0" if frame < 2 else "#8a86a8")
    return c


def door(open_: float) -> Canvas:
    """The double swing door to the dining room. open_: 0 closed .. 1 flung open."""
    w, h = DOOR_W, DOOR_H
    c = Canvas(w, h)
    c.rect(0, 0, w, h, "#140f26")                                     # the doorway (dark dining room)
    for y in range(4, h, 6):
        c.hline(2, w - 3, y, "#2a2038")
    if open_ < 0.05:
        panels = ((1, 14), (15, 14))
    else:
        pw = max(3, round(14 * (1 - open_)))
        panels = ((1, pw), (w - 1 - pw, pw))
    for px, pw in panels:
        c.rect(px, 4, pw, h - 4, "#6a4228")
        c.vline(px, 4, h - 1, "#4a2c17")
        c.vline(px + pw - 1, 4, h - 1, "#8e5c38")
        c.hline(px, px + pw - 1, h - 10, STEEL["base"])                 # kick plate
        if pw >= 9:
            c.oval(px + pw // 2 - 4, 14, 8, 8, STEEL["base"])           # porthole
            c.oval(px + pw // 2 - 3, 15, 6, 6, "#ffd06a")
            c.set(px + pw // 2 - 2, 16, "#fff2c0")
    c.rect(0, 0, w, 4, "#2c2350")
    draw_text(c, w // 2 - text_width("EXIT") // 2 + 1, 0, "EXIT", "#ff5f5f")
    return c


# -- the kitchen-lab, seen from above (3/4 view) ---------------------------------------------
#
# Arcade overhead view: the back wall shows its face across the top, the side walls
# are thick caps, and the floor is square tiles. Things on the floor (benches, the
# pot) show their top and their front face, and sort by their front edge.

WALL_FACE = 44                   # rows of back-wall face
FLOOR_TOP = 58                   # first floor row (below the back counter)
WALL_L, WALL_R, WALL_B = 8, 312, 176
DOOR_X, DOOR_W = 258, 30         # doorway in the back wall, to the dining room
DOOR_Y, DOOR_H = 6, 52
CLOCK = (302, 14, 7)             # center x, y, radius (the game draws the hand)
RACK_Y = 3
HANG_SPOTS = [(104 + i * 19, RACK_Y + 2) for i in range(5)]     # top-left of each tool on the wall rack
STOVE_FLAMES = [(20, 51), (42, 51), (64, 51)]                  # burners on the back counter (the game animates them)
TILE = 16


def kitchen(w: int, h: int, seed: int = 11) -> Canvas:
    """The mad-science kitchen from above: tiled back wall with a hood, a rack of
    tools, shelves of specimens and a chalk menu; a counter with burners along
    it; a doorway to the dining room; and a big checkerboard lab floor."""
    rng = random.Random(seed)
    c = Canvas(w, h)
    wall, wall_hi = "#2a2a4e", "#33335c"
    for y in range(WALL_FACE):                                        # subway tile
        row = y // 5
        for x in range(w):
            gx = (x + (4 if row % 2 else 0)) % 8
            c.set(x, y, LAB_BG if y % 5 == 0 or gx == 0 else wall_hi if y % 5 == 1 else wall)

    # floor: lab checkerboard, with a drain and a few old stains
    dark, light = LAB_FLOOR, mix(LAB_FLOOR, LAB_DIM, 0.25)
    for y in range(FLOOR_TOP, h):
        for x in range(w):
            c.set(x, y, light if ((x // TILE) + ((y - FLOOR_TOP) // TILE)) % 2 else dark)
    for y in range(FLOOR_TOP, h):                                     # grout
        if (y - FLOOR_TOP) % TILE == 0:
            c.hline(0, w - 1, y, mix(dark, LAB_BG, 0.5))
    for x in range(0, w, TILE):
        c.vline(x, FLOOR_TOP, h - 1, mix(dark, LAB_BG, 0.5))
    c.rect(118, 152, 10, 10, STEEL["dk"])                             # floor drain
    for k in range(3):
        c.hline(119, 126, 154 + k * 3, "#140f26")
    for sx, sy, col in ((60, 150, GOO_SH), (230, 70, "#8a3a5a"), (284, 140, GOO_SH), (40, 72, "#5a4a2a")):
        for _ in range(14):                                           # stains
            c.set(sx + rng.randint(-4, 4), sy + rng.randint(-2, 2), mix(col, dark, 0.55))
    # hazard stripes in front of the doorway
    for x in range(DOOR_X, DOOR_X + DOOR_W):
        for y in range(FLOOR_TOP, FLOOR_TOP + 4):
            c.set(x, y, "#e8c040" if ((x + y) // 3) % 2 else "#1e1828")

    # stove hood and burners on the left
    poly(c, [(10, 4), (92, 4), (84, 26), (18, 26)], STEEL["base"])
    c.hline(12, 90, 5, STEEL["hi"])
    c.hline(18, 84, 25, STEEL["sh"])
    for x in range(26, 78, 8):
        c.rect(x, 17, 5, 2, STEEL["dk"])

    # tool rack (the tools are drawn by the game, so they can fly off it)
    c.hline(100, 198, RACK_Y, STEEL["hi"])
    c.hline(100, 198, RACK_Y + 1, STEEL["sh"])

    # one shelf of specimen jars
    c.rect(100, 36, 100, 3, "#6a4228")
    c.hline(100, 199, 36, "#8e5c38")
    x = 102
    while x < 192:
        jw, jh = rng.randint(7, 10), rng.randint(9, 13)
        fluid = rng.choice(["#39ff14", "#5ff3ff", "#ff9ab8", "#f0d27a", "#b07ad0"])
        c.rect(x, 36 - jh, jw, jh, mix(fluid, LAB_BG, 0.45))
        c.rect(x, 36 - jh, jw, 2, "#c8c8d8")
        c.vline(x + 1, 36 - jh + 3, 34, "#dfffff")
        mx, my = x + jw // 2, 36 - jh // 2
        what = rng.choice(["eye", "brain", "fish", "none"])
        if what == "eye":
            c.oval(mx - 2, my - 1, 4, 4, EYE_W)
            c.set(mx, my, IRIS)
        elif what == "brain":
            c.oval(mx - 3, my - 1, 6, 4, MUTANT["brain"])
        elif what == "fish":
            c.hline(mx - 2, mx + 2, my, "#4a9a6a")
            c.set(mx + 2, my - 1, EYE_W)
        x += jw + rng.randint(2, 4)

    # chalkboard menu
    c.rect(204, 4, 50, 32, "#6a4228")
    c.rect(206, 6, 46, 28, "#1e3a2a")
    for t, (line, col) in enumerate((("SOUP DU", "#f4f4f4"), ("JOUR:", "#f4f4f4"),
                                      ("PRIMORDIAL", "#d4ff7a"), ("ALIVE?", "#8a86a8"))):
        draw_text(c, 229 - text_width(line) // 2, 8 + t * 6, line, col)

    # order tickets and the clock, right of the door
    c.hline(292, 311, 26, STEEL["hi"])
    for i in range(3):
        c.rect(293 + i * 6, 27, 5, 9 + (i % 2) * 3, "#f4f0e0")
        c.hline(294 + i * 6, 296 + i * 6, 29, "#8a86a8")
    cx, cy, r = CLOCK
    c.oval(cx - r - 1, cy - r - 1, 2 * r + 3, 2 * r + 3, "#2a2a3a")
    c.oval(cx - r, cy - r, 2 * r + 1, 2 * r + 1, "#f4f0e0")
    for k in range(12):
        a = k * math.tau / 12
        c.set(round(cx + math.cos(a) * (r - 1)), round(cy + math.sin(a) * (r - 1)), "#5a6070")

    # the back counter, seen from above: steel top, then its front face
    c.rect(0, WALL_FACE, w, 8, STEEL["base"])
    c.hline(0, w - 1, WALL_FACE, STEEL["hi"])
    c.rect(0, WALL_FACE + 8, w, FLOOR_TOP - WALL_FACE - 8, STEEL["sh"])
    c.hline(0, w - 1, FLOOR_TOP - 1, STEEL["dk"])
    for fx, fy in STOVE_FLAMES:                                       # burner rings
        c.oval(fx - 7, fy - 5, 14, 6, "#140f26")
        c.oval(fx - 5, fy - 4, 10, 4, "#2a2a3a")
    c.rect(118, WALL_FACE + 1, 22, 6, "#c08a4a")                      # cutting board, tomato, onion
    c.oval(121, WALL_FACE + 1, 5, 4, "#e83b3b")
    c.oval(130, WALL_FACE + 1, 6, 5, "#e8e0b0")
    c.oval(150, WALL_FACE, 12, 8, "#bfefff")                          # a petri dish of something
    c.oval(153, WALL_FACE + 2, 4, 3, "#39ff14")
    c.rect(176, WALL_FACE + 1, 3, 6, "#6a4228")                       # knife block
    c.rect(180, WALL_FACE - 3, 2, 9, STEEL["hi"])
    c.oval(214, WALL_FACE, 14, 8, "#f4f4f4")                          # stack of plates
    c.oval(216, WALL_FACE + 1, 10, 5, "#c8c8d8")

    # the doorway cuts through the counter and the wall
    c.rect(DOOR_X - 3, DOOR_Y - 3, DOOR_W + 6, FLOOR_TOP - DOOR_Y + 3, "#4a2c17")

    # side walls and the near wall: thick caps, like an arcade dungeon room
    cap, cap_hi = "#140f26", "#2c2350"
    c.rect(0, WALL_FACE, WALL_L, h - WALL_FACE, cap)
    c.vline(WALL_L - 1, WALL_FACE, h - 1, cap_hi)
    c.rect(WALL_R, WALL_FACE, w - WALL_R, h - WALL_FACE, cap)
    c.vline(WALL_R, WALL_FACE, h - 1, cap_hi)
    c.rect(0, WALL_B, w, h - WALL_B, cap)
    c.hline(0, w - 1, WALL_B, cap_hi)
    return c


def bench(w: int, depth: int, seed: int) -> Canvas:
    """A lab bench / prep island from above: a w x depth top surface and a front
    face, cluttered with glassware. Its floor footprint is the bottom `depth` rows."""
    face = 10
    rng = random.Random(seed)
    c = Canvas(w, depth + face + 14)
    top0 = 14

    def draw(c: Canvas) -> None:
        c.rect(0, top0, w, depth, "#d8d4e4")                          # lab-white top
        c.hline(0, w - 1, top0, "#f4f2fa")
        c.rect(0, top0 + depth, w, face, "#5a6070")                   # cabinet front
        c.hline(0, w - 1, top0 + depth, "#3a3f4e")
        for x in range(4, w - 6, 14):
            c.rect(x, top0 + depth + 2, 11, face - 4, "#3a3f4e")
            c.hline(x + 3, x + 7, top0 + depth + 4, STEEL["hi"])
        x = 4
        while x < w - 10:                                             # glassware on top
            kind = rng.choice(["flask", "beaker", "burner", "tubes", "scope"])
            col = rng.choice(["#39ff14", "#5ff3ff", "#ff5fd7", "#ffd93a"])
            by = top0 + rng.randint(4, max(4, depth - 4))
            if kind == "flask":
                poly(c, [(x + 3, by - 12), (x + 5, by - 12), (x + 8, by), (x, by)], "#bfefff")
                c.rect(x + 1, by - 4, 7, 4, col)
            elif kind == "beaker":
                c.rect(x, by - 9, 7, 9, "#bfefff")
                c.rect(x + 1, by - 5, 5, 5, col)
                c.set(x + 1, by - 8, "#ffffff")
            elif kind == "burner":
                c.rect(x + 1, by - 4, 5, 4, STEEL["base"])
                c.vline(x + 3, by - 8, by - 5, "#5ff3ff")
                c.set(x + 3, by - 9, "#ffffff")
            elif kind == "tubes":
                c.rect(x, by - 3, 10, 3, "#6a4228")
                for k in range(3):
                    c.vline(x + 1 + k * 3, by - 10, by - 3, "#bfefff")
                    c.vline(x + 1 + k * 3, by - 6, by - 3, rng.choice(["#39ff14", "#ff5fd7", "#ffd93a"]))
            else:
                c.rect(x + 1, by - 2, 7, 2, "#2a2a3a")                # microscope
                c.line(x + 3, by - 3, x + 6, by - 11, "#2a2a3a", width=2)
                c.rect(x + 5, by - 13, 3, 3, "#2a2a3a")
            x += rng.randint(11, 16)

    return layered(c.w, c.h, [draw])
