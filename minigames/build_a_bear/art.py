"""Build-A-Bear art: the castle lab, the slab, the big knife switch, the mad
scientist, and a pile of spare toy parts (teddies, dolls, bunnies, sock monkeys)
that sew onto one plush body.

Same arcade overhead view as Primordial Soup: the back wall shows its face across
the top, the floor is stone flags, and things on the floor sort by their front edge.

Every part is drawn standing up, with a socket where it joins the torso. Arms and
legs hang down from theirs; heads sit up on theirs. Put a part in a slot that
points the other way (an arm where the head goes) and it's turned upside down.
Right-hand slots use the part as drawn, left-hand slots mirror it.
"""

from __future__ import annotations

import math
import random

from sprites.canvas import Canvas, mix
from sprites.font import draw_text, text_width
from sprites.palette import INK, LAB_BG, OUTLINE
from sprites.rig import ANIMATIONS, CX, GROUND, BodyPlan, Pose, poses


from ..primordial_soup.art import STEEL
from ..primordial_soup.people import SCIENTIST, SciArm, SciHead, SciLegs, SciTorso
from ..stork_bomber.art import layered, poly

# -- the room ------------------------------------------------------------------------

WALL_FACE = 44                   # rows of back-wall face
FLOOR_TOP = 58                   # first floor row (below the ledge)
WALL_L, WALL_R, WALL_B = 8, 312, 176
FLAG = 16                        # flagstone size
WINDOWS = [(26, 6, 30, 34), (196, 6, 30, 34)]      # x, y, w, h: arched windows with a storm outside
SWITCH = (262, 4, 38, 38)        # the knife-switch panel on the wall
LEVER_PIVOT = (281, 32)          # where the blade hinges (the game draws the blade)
LEVER_LEN = 20
SLAB_X, SLAB_FRONT = 160, 124   # the slab's center column and the floor row of its front edge
SLAB_W, SLAB_DEPTH, SLAB_FACE = 92, 30, 10
COILS = [(100, 96), (220, 96)]   # feet of the two Tesla coils behind the slab's corners
TORCHES = [(80, 18), (172, 18), (246, 18)]         # wall sconces (the game flickers them)
STONE, STONE_HI, STONE_DK = "#3a3550", "#4a4466", "#24203a"


def lab(w: int, h: int, seed: int = 7) -> Canvas:
    """The castle laboratory from above: a stone back wall with storm windows,
    shelves of jars and a hanging chain; a ledge of clutter along it; the knife
    switch on the right; and a flagstone floor with a drain and old stains."""
    rng = random.Random(seed)
    c = Canvas(w, h)
    for y in range(WALL_FACE):                                       # big castle blocks
        row = y // 8
        for x in range(w):
            gx = (x + (10 if row % 2 else 0)) % 20
            edge = y % 8 == 0 or gx == 0
            col = STONE_DK if edge else STONE_HI if y % 8 == 1 or gx == 1 else STONE
            c.set(x, y, col)
    for _ in range(60):                                              # moss and grime
        x, y = rng.randrange(w), rng.randrange(WALL_FACE)
        if c.get(x, y) == STONE:
            c.set(x, y, rng.choice(["#2f4a3a", "#33304a", "#45405e"]))

    # the floor: big uneven flagstones
    dark, light = "#2a2540", "#322c4c"
    for y in range(FLOOR_TOP, h):
        row = (y - FLOOR_TOP) // FLAG
        for x in range(w):
            col = (x + (8 if row % 2 else 0)) // FLAG
            c.set(x, y, light if (col * 7 + row * 3) % 5 < 2 else dark)
    grout = "#1a1630"
    for y in range(FLOOR_TOP, h):
        row = (y - FLOOR_TOP) // FLAG
        if (y - FLOOR_TOP) % FLAG == 0:
            c.hline(0, w - 1, y, grout)
        for x in range(0, w + FLAG, FLAG):
            c.set(x - (8 if row % 2 else 0), y, grout)
    for sx, sy, col in ((60, 150, "#6a1a2a"), (250, 140, "#2f6a3a"), (150, 160, "#6a1a2a"), (36, 80, "#4a3a2a")):
        for _ in range(16):                                          # stains. don't ask
            c.set(sx + rng.randint(-5, 5), sy + rng.randint(-2, 2), mix(col, dark, 0.4))
    c.rect(148, 150, 10, 10, STEEL["dk"])                            # floor drain
    for k in range(3):
        c.hline(149, 156, 152 + k * 3, "#140f26")

    # storm windows (the game draws the rain and the lightning inside them)
    for wx, wy, ww, wh in WINDOWS:
        c.rect(wx - 3, wy - 2, ww + 6, wh + 4, STONE_DK)
        c.oval(wx - 3, wy - 4, ww + 6, 14, STONE_DK)
        c.rect(wx, wy + 4, ww, wh - 4, "#141a3a")
        c.oval(wx, wy - 2, ww, 12, "#141a3a")
        c.vline(wx + ww // 2, wy, wy + wh - 1, "#1e1828")            # mullions
        c.hline(wx, wx + ww - 1, wy + wh // 2, "#1e1828")
        c.rect(wx - 4, wy + wh, ww + 8, 3, STONE_HI)                 # sill

    # a shelf of jars between the windows
    c.rect(92, 34, 70, 3, "#5a3a22")
    c.hline(92, 161, 34, "#7a5232")
    x = 95
    while x < 154:
        jw, jh = rng.randint(7, 10), rng.randint(9, 14)
        fluid = rng.choice(["#39ff14", "#5ff3ff", "#ff9ab8", "#f0d27a", "#b07ad0"])
        c.rect(x, 34 - jh, jw, jh, mix(fluid, LAB_BG, 0.45))
        c.rect(x, 34 - jh, jw, 2, "#c8c8d8")
        c.vline(x + 1, 34 - jh + 3, 32, "#dfffff")
        mx, my = x + jw // 2, 34 - jh // 2
        what = rng.choice(["eye", "brain", "hand", "eye"])
        if what == "eye":
            c.oval(mx - 2, my - 1, 4, 4, "#f4f4f4")
            c.set(mx, my, "#e83b3b")
        elif what == "brain":
            c.oval(mx - 3, my - 1, 6, 4, "#e89ab0")
        else:
            c.rect(mx - 2, my - 1, 4, 3, "#c8d8a0")
            for k in range(3):
                c.vline(mx - 2 + k * 1 + k, my - 3, my - 2, "#c8d8a0")
        x += jw + rng.randint(2, 4)

    # a chain hanging from the ceiling with a hook
    for y in range(0, 30, 3):
        c.rect(178, y, 2, 2, "#5a6070")
        c.set(179, y + 2, "#9aa0b0")
    c.line(178, 30, 176, 34, "#9aa0b0")
    c.line(176, 34, 180, 35, "#9aa0b0")

    # a chalk blackboard of equations, nearly right
    c.rect(118, 4, 50, 16, "#5a3a22")
    c.rect(119, 5, 48, 14, "#1e3a2a")
    draw_text(c, 121, 6, "FLUFF", "#f4f4f4")
    draw_text(c, 142, 6, "+ZAP", "#d4ff7a")
    draw_text(c, 121, 12, "LOVE???", "#ff9ab8")

    # torch sconces
    for tx, ty in TORCHES:
        c.rect(tx - 2, ty, 5, 3, "#5a3a22")
        c.rect(tx - 1, ty + 3, 3, 6, "#3a2414")

    # the knife-switch panel: slate on bolts, two copper jaws, a sign
    sx, sy, sw, sh = SWITCH
    c.rect(sx, sy, sw, sh, "#2a2a3a")
    c.rect(sx + 1, sy + 1, sw - 2, sh - 2, "#3e3e52")
    for bx, by in ((sx + 2, sy + 2), (sx + sw - 3, sy + 2), (sx + 2, sy + sh - 3), (sx + sw - 3, sy + sh - 3)):
        c.set(bx, by, STEEL["hi"])
    c.rect(sx + 4, sy + 3, sw - 8, 7, "#ffd93a")
    draw_text(c, sx + sw // 2 - text_width("DANGER") // 2, sy + 4, "DANGER", "#1e1828")
    px, py = LEVER_PIVOT
    c.rect(px - 4, py - 1, 9, 4, "#c8783a")                          # the hinge block
    c.hline(px - 4, px + 4, py - 1, "#f0a060")
    c.rect(px - 4, sy + 13, 9, 3, "#c8783a")                         # the jaws it slams into (up = live)
    c.hline(px - 4, px + 4, sy + 13, "#f0a060")
    for k in range(3):
        c.set(sx + 5, sy + 15 + k * 4, ("#39ff14", "#e83b3b", "#ffd93a")[k])
    # cables from the switch down the wall to the coils
    for x0 in (sx + 6, sx + sw - 6):
        c.vline(x0, sy + sh, WALL_FACE - 1, "#140f26")
        c.vline(x0 + 1, sy + sh, WALL_FACE - 1, "#3a3f4e")

    # the ledge along the wall: stone top and face, with clutter
    c.rect(0, WALL_FACE, w, 8, "#55506e")
    c.hline(0, w - 1, WALL_FACE, "#6a6488")
    c.rect(0, WALL_FACE + 8, w, FLOOR_TOP - WALL_FACE - 8, STONE_DK)
    c.hline(0, w - 1, FLOOR_TOP - 1, "#140f26")
    for x in range(0, w, 20):
        c.vline(x, WALL_FACE + 8, FLOOR_TOP - 2, "#1a1630")
    c.oval(20, WALL_FACE + 1, 12, 6, "#f8e6da")                      # a spare doll head, watching
    c.oval(20, WALL_FACE, 12, 3, "#f0c440")
    c.rect(22, WALL_FACE + 3, 2, 2, "#3a7ad8")
    c.rect(27, WALL_FACE + 3, 2, 2, "#3a7ad8")
    c.rect(40, WALL_FACE + 1, 3, 6, "#e8e0c8")                       # candles
    c.rect(46, WALL_FACE + 2, 3, 5, "#e8e0c8")
    c.oval(96, WALL_FACE + 1, 18, 6, "#5a3a22")                      # a saw, a mallet, a big needle
    c.rect(100, WALL_FACE + 2, 14, 3, STEEL["hi"])
    for k in range(0, 14, 2):
        c.set(100 + k, WALL_FACE + 5, STEEL["sh"])
    c.rect(130, WALL_FACE + 2, 12, 3, "#7a5232")
    c.rect(142, WALL_FACE + 1, 5, 5, "#5a3a22")
    c.line(160, WALL_FACE + 6, 172, WALL_FACE + 1, STEEL["hi"])
    c.oval(212, WALL_FACE + 1, 10, 6, "#bfefff")                     # a flask of something
    c.oval(214, WALL_FACE + 3, 6, 3, "#39ff14")
    c.rect(234, WALL_FACE + 1, 14, 6, "#8a3a2a")                     # a book: HOW TO
    draw_text(c, 236, WALL_FACE + 1, "HUG", "#f0d27a")

    # cables from the wall down to the coils
    for (x0, y0), x1 in ((COILS[0], WALL_L + 4), (COILS[1], WALL_R - 4)):
        pts = [(x0, y0 - 3)]
        for k in range(1, 9):
            t = k / 8
            pts.append((round(x0 + (x1 - x0) * t), round(y0 - 3 + 5 * math.sin(t * 6) + 30 * t)))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            c.stroke(ax, ay, bx, by, "#140f26", 3)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            c.line(ax, ay - 1, bx, by - 1, "#3a3f4e")

    # side walls and the near wall
    cap, cap_hi = "#140f26", "#2c2350"
    c.rect(0, WALL_FACE, WALL_L, h - WALL_FACE, cap)
    c.vline(WALL_L - 1, WALL_FACE, h - 1, cap_hi)
    c.rect(WALL_R, WALL_FACE, w - WALL_R, h - WALL_FACE, cap)
    c.vline(WALL_R, WALL_FACE, h - 1, cap_hi)
    c.rect(0, WALL_B, w, h - WALL_B, cap)
    c.hline(0, w - 1, WALL_B, cap_hi)
    return c


def slab() -> Canvas:
    """The operating slab from above: a stone top with straps and drain grooves,
    then its front face with a gauge. Its floor footprint is the bottom SLAB_DEPTH rows
    of the top. Canvas is SLAB_W x (top + face); the top starts at row 0."""
    def draw(c: Canvas) -> None:
        c.rect(0, 0, SLAB_W, SLAB_DEPTH, "#8a86a0")
        c.hline(0, SLAB_W - 1, 0, "#b8b4cc")
        c.rect(3, 3, SLAB_W - 6, SLAB_DEPTH - 6, "#9a96b0")
        c.hline(4, SLAB_W - 5, SLAB_DEPTH // 2, "#7a7690")              # drain groove
        for k in range(6):
            c.set(10 + k * 14, SLAB_DEPTH - 4, mix("#6a1a2a", "#9a96b0", 0.3))
        c.rect(0, SLAB_DEPTH, SLAB_W, SLAB_FACE, "#4a4660")
        c.hline(0, SLAB_W - 1, SLAB_DEPTH, "#2a2a3a")
        for x in range(6, SLAB_W - 6, 20):
            c.rect(x, SLAB_DEPTH + 3, 3, SLAB_FACE - 4, STEEL["dk"])
        c.oval(SLAB_W // 2 - 4, SLAB_DEPTH + 1, 8, 8, "#f4f0e0")        # a gauge
        c.line(SLAB_W // 2, SLAB_DEPTH + 5, SLAB_W // 2 + 2, SLAB_DEPTH + 3, "#e83b3b")
    c = layered(SLAB_W + 2, SLAB_DEPTH + SLAB_FACE + 2, [lambda c: draw_at(c, draw)])
    return c


def draw_at(c: Canvas, draw) -> None:
    """Draw with a 1px margin so the outline fits."""
    inner = Canvas(c.w - 2, c.h - 2)
    draw(inner)
    c.paste(inner, 1, 1)


def straps() -> Canvas:
    """Leather straps across the slab, drawn over the body."""
    c = Canvas(SLAB_W + 2, SLAB_DEPTH + 2)
    for x in (24, 46, 68):
        c.rect(x, 1, 4, SLAB_DEPTH, "#5a3a22")
        c.vline(x, 1, SLAB_DEPTH, "#7a5232")
        c.rect(x, SLAB_DEPTH // 2 - 1, 4, 3, STEEL["hi"])
    return c


def blade(down: float) -> Canvas:
    """The knife-switch blade and its red handle, hinged at the pivot. down 0 = hanging
    open, 1 = slammed up into the live jaws. It swings out toward you on the way."""
    c = Canvas(BLADE_BOX, BLADE_BOX)
    m = BLADE_BOX // 2
    reach = math.cos(math.pi * down)                                  # +1 down, -1 up, 0 pointing at you
    ey = m + round(LEVER_LEN * reach)
    c.stroke(m - 2, m, m - 2, ey, "#d0d4e0", 2)
    c.stroke(m + 2, m, m + 2, ey, "#d0d4e0", 2)
    c.hline(m - 3, m + 3, ey, "#9aa0b0")
    grow = 2 if abs(reach) < 0.5 else 0                               # the handle looms as it comes at you
    hy = ey + (1 if reach >= 0 else -4 - grow)
    c.rect(m - 2 - grow // 2, hy, 5 + grow, 4 + grow, "#e83b3b")
    c.set(m - 1, hy, "#ff8a7a")
    c.outline(OUTLINE)
    return c


BLADE_BOX = LEVER_LEN * 2 + 10


# -- the scientist -------------------------------------------------------------------

DOC = dict(SCIENTIST, coat="#e8ecf4", tie="#1e1828", shirt="#6a1a2a", stain="#c8402a",
           lens="#ffd93a", rim="#5a6070", pants="#2a2a3a", shoe="#1e1828")
DOC_TARGETS = {
    "carry": ((1.0, -0.15), (0.95, 0.05)),
    "cheer0": ((0.4, -1.0), (-0.4, -1.0)),
    "cheer1": ((0.7, -0.75), (-0.7, -0.75)),
}
DOC_REACH = 9


class DocArm(SciArm):
    targets = DOC_TARGETS

    def flask(self, c: Canvas, hx: int, hy: int, frame: int) -> None:
        pass                                                       # hands free for body parts


def doc_plan() -> BodyPlan:
    arm = DocArm(DOC)
    return BodyPlan(legs=SciLegs(DOC), torso=SciTorso(DOC), head=SciHead(DOC), front_arm=arm, back_arm=arm)


def doc_frames() -> dict[str, list[Canvas]]:
    """Right-facing 48x48 frames: idle, run, carrying, pulling the lever, cheering."""
    plan = doc_plan()
    out = {anim: [plan.render(p) for p in poses(anim)] for anim in ("idle", "run", "interact", "hurt")}
    for name, base in (("carry_idle", "idle"), ("carry_run", "run")):
        out[name] = [plan.render(Pose(base, i, len(ANIMATIONS[base]), **{**kw, "arm": "carry", "back_arm": None}))
                     for i, kw in enumerate(ANIMATIONS[base])]
    out["cheer"] = [plan.render(Pose("idle", i, 2, bob=i, arm=f"cheer{i}")) for i in range(2)]
    return out


def carry_point(pose: Pose) -> tuple[int, int]:
    """Where, inside a right-facing frame, the hands hold a carried part."""
    hip = GROUND - 11 + pose.bob
    sx, sy = CX + pose.lean, hip - 11 + 2
    dx, dy = DOC_TARGETS["carry"][0]
    return sx + round(dx * DOC_REACH) + 1, sy + round(dy * DOC_REACH)


# -- body parts ----------------------------------------------------------------------

SLOTS = ("HEAD", "LEFT ARM", "RIGHT ARM", "LEFT LEG", "RIGHT LEG")
SLOT_KIND = {"HEAD": "head", "LEFT ARM": "arm", "RIGHT ARM": "arm", "LEFT LEG": "leg", "RIGHT LEG": "leg"}
FAMILIES = {"head": ("teddy", "doll", "bunny", "monkey"),
            "arm": ("teddy", "doll", "monkey", "octopus"),
            "leg": ("teddy", "doll", "bunny", "monkey")}
PART_NAMES = {
    ("head", "teddy"): "TEDDY HEAD", ("head", "doll"): "DOLL HEAD", ("head", "bunny"): "BUNNY HEAD",
    ("head", "monkey"): "SOCK MONKEY HEAD",
    ("arm", "teddy"): "TEDDY ARM", ("arm", "doll"): "DOLL ARM", ("arm", "monkey"): "SOCK MONKEY ARM",
    ("arm", "octopus"): "PLUSH TENTACLE",
    ("leg", "teddy"): "TEDDY LEG", ("leg", "doll"): "DOLL LEG", ("leg", "bunny"): "BUNNY FOOT",
    ("leg", "monkey"): "SOCK MONKEY LEG",
}
TEDDY = {"fur": "#b07a40", "sh": "#7e5028", "hi": "#d09a5a", "pad": "#ecd0a0", "pad_sh": "#c8a878"}
DOLL = {"skin": "#f8e6da", "sh": "#d8b8a8", "cheek": "#f49aa8", "hair": "#f0c440", "hair_sh": "#c8962a",
        "eye": "#3a7ad8", "lips": "#d8304a", "dress": "#e88ab0", "dress_sh": "#b85a88", "lace": "#ffffff",
        "sock": "#f4f4f4", "shoe": "#1e1828"}
BUNNY = {"fur": "#f4dcea", "sh": "#d4a8c4", "inner": "#ff9ac8", "pad": "#ff9ac8"}
MONKEY = {"sock": "#8a7e70", "sh": "#665c52", "hi": "#a89c8c", "cream": "#f0e8d4", "red": "#c83a3a"}
OCTO = {"skin": "#a87adf", "sh": "#7a4ab8", "hi": "#c8a4f4", "sucker": "#ffd0ee"}
SEAM = "#3a2418"
BUTTON = "#1e1828"


def _head(fam: str) -> Canvas:
    """16x16 head, chin at the bottom center (socket at (8, 15))."""
    c = Canvas(16, 16)
    if fam == "teddy":
        t = TEDDY
        c.oval(0, 0, 6, 6, t["fur"])                                # round ears
        c.oval(10, 0, 6, 6, t["fur"])
        c.oval(1, 1, 4, 4, t["pad"])
        c.oval(11, 1, 4, 4, t["pad"])
        c.oval(1, 2, 14, 13, t["fur"])
        c.vline(1, 6, 11, t["sh"])
        c.rect(4, 6, 2, 2, BUTTON)                                  # button eyes
        c.rect(10, 6, 2, 2, BUTTON)
        c.set(4, 6, "#5a5a6a")
        c.oval(5, 9, 6, 5, t["pad"])                                # muzzle
        c.rect(7, 9, 2, 2, BUTTON)
        c.vline(8, 11, 12, SEAM)
        c.vline(8, 2, 5, SEAM)                                      # seam over the crown
        c.rect(6, 14, 4, 2, t["sh"])
    elif fam == "doll":
        d = DOLL
        c.oval(1, 0, 14, 13, d["hair"])                             # golden ringlets
        for x in (0, 13):
            for y in (5, 8, 11):
                c.oval(x, y, 3, 3, d["hair"])
                c.set(x + 1, y + 2, d["hair_sh"])
        c.oval(3, 3, 10, 11, d["skin"])
        c.hline(4, 11, 3, d["hair"])                                # bangs
        c.set(5, 4, d["hair"])
        c.set(9, 4, d["hair"])
        c.rect(4, 6, 3, 3, "#ffffff")                               # big glassy eyes
        c.rect(9, 6, 3, 3, "#ffffff")
        c.rect(5, 7, 2, 2, d["eye"])
        c.rect(10, 7, 2, 2, d["eye"])
        c.set(5, 7, INK)
        c.set(10, 7, INK)
        c.set(4, 10, d["cheek"])
        c.set(11, 10, d["cheek"])
        c.rect(7, 11, 2, 1, d["lips"])
        c.line(10, 3, 12, 6, d["sh"])                               # a hairline crack. it's fine
        c.set(11, 6, d["sh"])
        c.rect(6, 14, 4, 2, d["sh"])
    elif fam == "bunny":
        b = BUNNY
        c.rect(3, 0, 3, 7, b["fur"])                                # tall floppy ears
        c.rect(10, 0, 3, 5, b["fur"])
        c.line(12, 5, 14, 7, b["fur"])
        c.vline(4, 1, 6, b["inner"])
        c.vline(11, 1, 4, b["inner"])
        c.oval(2, 5, 12, 10, b["fur"])
        c.vline(2, 8, 12, b["sh"])
        c.rect(5, 8, 1, 2, BUTTON)
        c.rect(10, 8, 1, 2, BUTTON)
        c.rect(7, 10, 2, 1, b["inner"])                             # pink nose
        c.set(7, 12, SEAM)
        c.set(8, 12, SEAM)
        c.hline(3, 5, 11, b["sh"])                                  # whiskers
        c.hline(10, 12, 11, b["sh"])
        c.rect(6, 14, 4, 2, b["sh"])
    else:
        m = MONKEY
        c.oval(0, 5, 4, 5, m["red"])                                # red-lined ears
        c.oval(12, 5, 4, 5, m["red"])
        c.oval(2, 1, 12, 14, m["sock"])
        for x in range(3, 13, 2):                                   # heathered knit
            c.set(x, 3 + (x % 3), m["hi"])
        c.vline(2, 4, 11, m["sh"])
        c.rect(7, 0, 2, 2, m["red"])                                # pom-pom hat
        c.rect(4, 5, 2, 2, BUTTON)
        c.rect(10, 5, 2, 2, BUTTON)
        c.oval(3, 8, 10, 7, m["cream"])                             # big cream muzzle
        c.hline(4, 11, 11, m["red"])                                # red-heel lips
        c.hline(5, 10, 12, m["red"])
        c.rect(6, 14, 4, 2, m["sh"])
    c.outline(OUTLINE)
    return c


def _arm(fam: str) -> Canvas:
    """A right arm hanging down from its shoulder socket at the top center."""
    if fam == "octopus":
        c = Canvas(10, 22)
        o = OCTO
        for y in range(0, 20):
            w = max(2, 5 - y // 6)
            x = 4 + round(2 * math.sin(y / 3.4))
            c.hline(x - w // 2, x + w // 2, y, o["skin"])
            c.set(x - w // 2, y, o["sh"])
            if y % 4 == 2:
                c.set(x + w // 2, y, o["sucker"])
        x = 4 + round(2 * math.sin(20 / 3.4))
        c.oval(x - 1, 19, 4, 3, o["skin"])                          # curly plush tip
        c.set(x, 20, o["sucker"])
        c.outline(OUTLINE)
        return c
    c = Canvas(9, 20)
    if fam == "teddy":
        t = TEDDY
        c.rect(2, 0, 5, 14, t["fur"])                               # stubby plush arm
        c.vline(2, 0, 13, t["sh"])
        c.oval(1, 12, 7, 7, t["fur"])
        c.oval(2, 14, 5, 4, t["pad"])                               # paw pad
        c.vline(6, 2, 10, t["hi"])
    elif fam == "doll":
        d = DOLL
        c.oval(0, 0, 9, 7, d["dress"])                              # puffed sleeve
        c.hline(1, 7, 6, d["lace"])
        c.set(2, 3, d["dress_sh"])
        c.rect(3, 7, 3, 9, d["skin"])                               # porcelain arm
        c.vline(3, 7, 15, d["sh"])
        c.rect(2, 15, 5, 3, d["skin"])                              # little hand
        c.vline(2, 18, 18, d["skin"])
        c.vline(4, 18, 18, d["sh"])
    else:
        m = MONKEY
        c.rect(2, 0, 5, 14, m["sock"])
        for y in range(1, 14, 3):                                   # knit ribs
            c.hline(3, 5, y, m["hi"])
        c.vline(2, 0, 13, m["sh"])
        c.oval(1, 13, 7, 6, m["cream"])                             # cream cuff hand
    c.outline(OUTLINE)
    return c


def _leg(fam: str) -> Canvas:
    """A right leg hanging from its hip socket at the top center."""
    c = Canvas(12, 20)
    if fam == "teddy":
        t = TEDDY
        c.rect(2, 0, 7, 12, t["fur"])
        c.vline(2, 0, 11, t["sh"])
        c.vline(8, 2, 9, t["hi"])
        c.oval(1, 10, 10, 8, t["fur"])
        c.oval(3, 12, 6, 5, t["pad"])                               # foot pad, with a heart
        c.set(5, 14, "#e83b5a")
        c.set(6, 14, "#e83b5a")
        c.set(5, 15, "#e83b5a")
    elif fam == "doll":
        d = DOLL
        c.rect(1, 0, 9, 4, d["dress"])                              # frilly bloomers
        for x in range(1, 10, 2):
            c.set(x, 4, d["lace"])
        c.rect(4, 4, 3, 10, d["sock"])                              # white stocking
        c.vline(4, 4, 13, "#c8c8d8")
        c.rect(3, 14, 6, 3, d["shoe"])                              # Mary Jane
        c.hline(4, 7, 14, "#4a4a5a")
        c.set(7, 15, "#c8c8d8")
    elif fam == "bunny":
        b = BUNNY
        c.rect(3, 0, 6, 8, b["fur"])
        c.vline(3, 0, 7, b["sh"])
        c.oval(0, 7, 12, 11, b["fur"])                              # a huge flat bunny foot
        c.oval(3, 10, 6, 6, b["pad"])
        for x in (2, 5, 8):
            c.set(x, 8, b["pad"])
    else:
        m = MONKEY
        c.rect(3, 0, 6, 12, m["sock"])
        for y in range(1, 12, 3):
            c.hline(4, 7, y, m["hi"])
        c.vline(3, 0, 11, m["sh"])
        c.oval(2, 11, 9, 7, m["red"])                               # the red heel of the sock
        c.oval(4, 13, 5, 4, m["cream"])
    c.outline(OUTLINE)
    return c


def part(kind: str, fam: str) -> Canvas:
    return {"head": _head, "arm": _arm, "leg": _leg}[kind](fam)


def socket(kind: str, img: Canvas) -> tuple[int, int]:
    """Where a part joins the torso, in its own canvas."""
    return (img.w // 2, img.h - 1) if kind == "head" else (img.w // 2, 0)


def rot180(c: Canvas) -> Canvas:
    out = Canvas(c.w, c.h)
    out.px = [list(reversed(row)) for row in reversed(c.px)]
    return out


def rot90(c: Canvas) -> Canvas:
    """Quarter turn counterclockwise (the top ends up on the left)."""
    out = Canvas(c.h, c.w)
    for y in range(c.h):
        for x in range(c.w):
            out.px[c.w - 1 - x][y] = c.px[y][x]
    return out


def lying(kind: str, fam: str, i: int = 0) -> Canvas:
    """A part as it lies on the floor: heads sit upright, limbs lie on their side."""
    img = part(kind, fam)
    if kind == "head":
        return img
    img = rot90(img)
    return img.flipped() if i % 2 else img


# The creature, standing: one stitched torso, sockets at the neck, shoulders and hips.
MW, MH = 52, 76
NECK = (26, 26)
SHOULDERS = {"LEFT ARM": (17, 28), "RIGHT ARM": (35, 28)}
HIPS = {"LEFT LEG": (22, 46), "RIGHT LEG": (30, 46)}
SLOT_AT = {"HEAD": NECK, **SHOULDERS, **HIPS}
SLOT_UP = {"HEAD": True, "LEFT ARM": False, "RIGHT ARM": False, "LEFT LEG": False, "RIGHT LEG": False}


def torso() -> Canvas:
    """The one body everything sews onto: a plush teddy tummy, patched and restuffed,
    with a red bow at the neck and a little stuffing poking out of a seam."""
    c = Canvas(MW, MH)
    t = TEDDY
    nx, ny = NECK
    hip = HIPS["LEFT LEG"][1]
    c.oval(nx - 10, ny, 20, hip - ny + 5, t["fur"])                  # round and squishy
    c.vline(nx - 10, ny + 6, hip - 2, t["sh"])
    c.vline(nx - 9, ny + 4, hip, t["sh"])
    c.oval(nx - 6, ny + 6, 12, hip - ny - 4, t["pad"])                # cream belly
    c.vline(nx, ny + 2, hip + 2, SEAM)                                # the seam down the front
    for y in range(ny + 4, hip, 3):
        c.set(nx - 1, y, SEAM)
        c.set(nx + 1, y, SEAM)
    c.rect(nx + 4, ny + 3, 5, 5, "#5f9fd8")                           # a patch, stitched on
    for k in range(5):
        c.set(nx + 4 + k, ny + 3, "#2a6ac8" if k % 2 else "#5f9fd8")
    c.set(nx - 5, ny + 14, "#ffffff")                                 # stuffing coming out
    c.set(nx - 6, ny + 15, "#ffffff")
    c.set(nx - 5, ny + 15, "#e8e8f0")
    c.rect(nx - 4, ny - 1, 3, 3, "#e83b3b")                           # bow tie
    c.rect(nx + 1, ny - 1, 3, 3, "#e83b3b")
    c.rect(nx - 1, ny, 2, 2, "#a82434")
    c.outline(OUTLINE)
    return c


def place(slot: str, kind: str, fam: str) -> tuple[Canvas, int, int]:
    """A part turned for a slot, and where its top-left goes on the creature canvas."""
    img = part(kind, fam)
    sx, sy = socket(kind, img)
    natural_up = kind == "head"
    if natural_up != SLOT_UP[slot]:
        img = rot180(img)
        sx, sy = img.w - 1 - sx, img.h - 1 - sy
    if slot.startswith("LEFT"):
        img = img.flipped()
        sx = img.w - 1 - sx
    ax, ay = SLOT_AT[slot]
    return img, ax - sx, ay - sy


def creature(parts: dict[str, tuple[str, str]]) -> Canvas:
    """The creature as built so far. parts: slot -> (kind, family)."""
    c = Canvas(MW, MH)
    order = ["LEFT LEG", "RIGHT LEG", "TORSO", "LEFT ARM", "RIGHT ARM", "HEAD"]
    for slot in order:
        if slot == "TORSO":
            c.paste(torso())
        elif slot in parts:
            img, x, y = place(slot, *parts[slot])
            c.paste(img, x, y)
    return c


def spark() -> Canvas:
    c = Canvas(7, 7)
    c.stamp(0, 0, ["...#...", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "...#..."],
            {"#": "#fff27a"})
    c.set(3, 3, "#ffffff")
    return c


def smoke(frame: int) -> Canvas:
    c = Canvas(12, 10)
    r = 2 + frame
    c.oval(6 - r, 5 - r // 2, 2 * r, r + 1, mix("#8a86a8", LAB_BG, 0.2 * frame))
    return c


def star() -> Canvas:
    c = Canvas(5, 5)
    c.stamp(0, 0, ["..#..", ".###.", "#####", ".###.", "..#.."], {"#": "#ffd93a"})
    return c
