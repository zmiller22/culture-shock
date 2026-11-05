"""The chef and the hungry diners, built from rig genes like the main cast so
they get every animation state for free.

The chef: toque, double-breasted whites, houndstooth trousers, black clogs and a
magnificent moustache. His "carry" arm pose holds a squirming creature out in
front of him at arm's length.

Diners: a few palettes and hairdos, a napkin tucked in the collar, a fork in the
front hand and a steak knife in the back one. Their attack is a stab.
"""

from __future__ import annotations

import math

from sprites.canvas import Canvas
from sprites.palette import INK
from sprites.rig import ANIMATIONS, CX, GROUND, Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, poses

CHEF = {
    "skin": "#f0c09a", "skin_sh": "#c98f6e", "nose": "#e8907a",
    "white": "#f4f4f4", "white_sh": "#c8c8d8", "white_dk": "#9a9ab8",
    "button": "#5a6070", "scarf": "#e83b3b", "scarf_sh": "#a82434",
    "stain": "#c8402a",
    "check": "#2a2a3a", "check_hi": "#d8d8e0",
    "clog": "#1e1828", "clog_hi": "#4a4a5a",
    "stache": "#5a3a22", "stache_hi": "#7a5232", "hair": "#4a2f1b",
}

# The chef's own arm poses, on top of the rig's. "carry": both arms straight out
# in front, holding something at chest height.
CHEF_TARGETS = {
    "carry": ((1.0, -0.15), (0.95, 0.05)),
    "cower": ((0.3, -0.95), (-0.2, -1.0)),       # hands up over the face
    "tray": ((1.0, -0.3), (0.8, -0.2)),          # a tray carried out in front
}
CHEF_REACH = 9
LEGS_LEN = 11
TORSO_H = 12


def carry_point(pose: Pose) -> tuple[int, int]:
    """Where, inside a right-facing frame, the hands hold a carried creature."""
    hip = GROUND - LEGS_LEN + pose.bob
    sx, sy = CX + pose.lean, hip - TORSO_H + 3
    dx, dy = CHEF_TARGETS["carry"][0]
    return sx + round(dx * CHEF_REACH) + 1, sy + round(dy * CHEF_REACH)


class ChefLegs(Legs):
    species = "chef"
    length = LEGS_LEN

    def __init__(self, look: dict | None = None) -> None:
        self.L = look or CHEF

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            foot_y = ground - 1 - (0 if front else pose.lift)
            c.line(cx - 1, hip, fx, foot_y - 1, self.L["check"], width=3)
            for y in range(hip, foot_y):                       # houndstooth: little light checks
                t = (y - hip) / max(1, foot_y - 1 - hip)
                x = round(cx - 1 + (fx - cx + 1) * t)
                if (y + front) % 2 == 0:
                    c.set(x + (y // 2) % 3, y, self.L["check_hi"] if front else self.L["white_dk"])
            c.rect(fx - 1, foot_y, 6, 2, self.L["clog"])          # clogs
            if front:
                c.set(fx + 2, foot_y, self.L["clog_hi"])


class ChefTorso(Torso):
    species = "chef"

    def __init__(self, look: dict | None = None) -> None:
        self.L = look or CHEF

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - TORSO_H
        c.oval(cx - 6, top, 13, TORSO_H + 3, self.L["white"])    # a well-fed chef
        c.vline(cx - 6, top + 3, hip, self.L["white_sh"])
        c.vline(cx - 5, top + 6, hip, self.L["white_sh"])
        for y in range(top + 3, hip, 3):                       # double-breasted buttons
            c.set(cx + 1, y, self.L["button"])
            c.set(cx + 4, y, self.L["button"])
        c.set(cx + 3, top + 8, self.L["stain"])                  # a splash of something
        c.set(cx + 2, top + 9, self.L["stain"])
        c.hline(cx - 6, cx + 6, hip, self.L["white_sh"])
        c.rect(cx - 1, top - 1, 5, 2, self.L["scarf"])           # neckerchief
        c.set(cx + 3, top + 1, self.L["scarf_sh"])
        c.set(cx + 4, top + 1, self.L["scarf"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx, top + 3), top=top, bottom=hip)


HEAD = [
    "...WWW.WWW...",
    "..WWWWWWWWWW.",
    ".WWWWWWWWWWWw",
    ".WWWWWWWWWWWw",
    "..wWWWWWWWWw.",
    "...WWWWWWWw..",
    "...wWWWWWWw..",
    "...bbbbbbbb..",
    "...HSSSSSSS..",
    "...HSSSSSSSS.",
    "...HSSSSSESS.",
    "...SSSSSSSSNN",
    "...SSSSMMMMN.",
    "....SSMMssMM.",
    "....SSSSSSS..",
    ".....SSSSS...",
]


class ChefHead(Head):
    species = "chef"

    def __init__(self, look: dict | None = None) -> None:
        self.L = look or CHEF

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, self.L["skin"])
        eye = self.L["skin_sh"] if pose.blink else INK
        if pose.arm == "cower" or pose.anim == "hurt":
            eye = INK
        key = {
            "W": self.L["white"], "w": self.L["white_sh"], "b": self.L["white_dk"],
            "H": self.L["hair"], "S": self.L["skin"], "s": self.L["skin_sh"], "E": eye,
            "N": self.L["nose"], "M": self.L["stache"],
        }
        x0, y0 = nx - 6, ny - 16
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 8, y0 + 12, self.L["stache_hi"])
        if pose.anim == "hurt" or pose.arm == "cower":         # mouth wide in horror
            c.rect(x0 + 8, y0 + 14, 2, 2, INK)
            c.set(x0 + 7, y0 + 9, INK)                         # raised brow
            c.set(x0 + 8, y0 + 9, INK)


class ChefArm(Arm):
    species = "chef"
    reach = CHEF_REACH
    targets = CHEF_TARGETS

    def __init__(self, look: dict | None = None) -> None:
        self.L = look or CHEF

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        cloth = self.L["white"] if front else self.L["white_sh"]
        dx = (2 if front else -2) * pose.swing
        c.line(sx, sy, sx + dx, sy + 7, cloth, width=2)
        c.rect(sx + dx, sy + 8, 2, 2, self.L["skin"] if front else self.L["skin_sh"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        cloth = self.L["white"] if front else self.L["white_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, cloth, 2)
        c.stroke(ex, ey, hx, hy, cloth, 2)
        c.rect(hx, hy, 2, 2, self.L["skin"] if front else self.L["skin_sh"])
        if mode == "tray" and front:                           # silver tray, cloche on top
            c.hline(hx - 2, hx + 10, hy - 1, STEEL_SH)
            c.hline(hx - 1, hx + 9, hy - 2, STEEL)
            c.oval(hx, hy - 7, 9, 6, STEEL)
            c.hline(hx + 1, hx + 7, hy - 3, STEEL_SH)
            c.set(hx + 2, hy - 5, STEEL_HI)
            c.set(hx + 4, hy - 8, STEEL_SH)


def chef_plan(look: dict | None = None) -> BodyPlan:
    arm = ChefArm(look)
    return BodyPlan(legs=ChefLegs(look), torso=ChefTorso(look), head=ChefHead(look), front_arm=arm, back_arm=arm)


def chef() -> BodyPlan:
    return chef_plan()


def chef_frames() -> dict[str, list[Canvas]]:
    """Right-facing 48x48 frames: the rig states the game uses, plus carrying
    (idle and run with both arms out front) and cowering."""
    plan = chef()
    out = {anim: [plan.render(p) for p in poses(anim)] for anim in ("idle", "run", "attack", "hurt", "death")}
    for name, base in (("carry_idle", "idle"), ("carry_run", "run")):
        out[name] = [plan.render(Pose(base, i, len(ANIMATIONS[base]), **{**kw, "arm": "carry", "back_arm": None}))
                     for i, kw in enumerate(ANIMATIONS[base])]
    out["cower"] = [plan.render(Pose("hurt", i, 2, bob=1 + i, lean=-1, arm="cower")) for i in range(2)]
    return out


# -- diners ------------------------------------------------------------------------

DINER_LOOKS = [
    dict(skin="#f0c09a", skin_sh="#c98f6e", hair="#e8c050", hair_sh="#b08a2a", style="bob",
         shirt="#5f9fd8", shirt_sh="#3a6aa8", pants="#2a2a3a", shoe="#5a2a18"),
    dict(skin="#8a5a3a", skin_sh="#6a4028", hair="#1e1828", hair_sh="#3a2f44", style="bun",
         shirt="#e83b3b", shirt_sh="#a82434", pants="#3a3044", shoe="#1e1828"),
    dict(skin="#e8b48a", skin_sh="#c08a66", hair="#b8b4cc", hair_sh="#8a86a8", style="bald",
         shirt="#6a9a3a", shirt_sh="#4a6a26", pants="#6a4228", shoe="#1e1828"),
    dict(skin="#c08a5a", skin_sh="#9a6a40", hair="#4a2f1b", hair_sh="#2c1a0e", style="quiff",
         shirt="#a24bff", shirt_sh="#6a2aa8", pants="#2c2350", shoe="#e8e8e8"),
    dict(skin="#f4d0b0", skin_sh="#d0a080", hair="#c8402a", hair_sh="#8a2a1a", style="bob",
         shirt="#f0d27a", shirt_sh="#c8a050", pants="#25365e", shoe="#5a2a18"),
    dict(skin="#6a4028", skin_sh="#4a2a18", hair="#1e1828", hair_sh="#3a2f44", style="quiff",
         shirt="#ff6fb5", shirt_sh="#c8407f", pants="#1e1828", shoe="#e83b3b"),
]
NAPKIN, NAPKIN_SH, SAUCE = "#f4f4f4", "#c8c8d8", "#d8302a"
STEEL, STEEL_HI, STEEL_SH, HANDLE = "#d0d4e0", "#ffffff", "#7a8090", "#5a3a22"
UTENSIL_LEN = 7


def utensil(c: Canvas, hx: int, hy: int, dx: float, dy: float, kind: str) -> None:
    """A fork or knife gripped at (hx, hy), pointing along (dx, dy)."""
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    c.line(hx, hy, round(hx - ux * 2), round(hy - uy * 2), HANDLE)           # handle out the back
    for k in range(1, UTENSIL_LEN + 1):
        x, y = round(hx + ux * k), round(hy + uy * k)
        c.set(x, y, STEEL_HI if k == UTENSIL_LEN else STEEL)
        if kind == "knife" and 1 < k < UTENSIL_LEN:                        # blade: a second row
            c.set(round(x - uy), round(y + ux), STEEL_SH)
    if kind == "fork":                                                     # tines fan out at the tip
        px, py = -uy, ux
        tx, ty = hx + ux * (UTENSIL_LEN - 1), hy + uy * (UTENSIL_LEN - 1)
        for side in (-1, 1):
            c.set(round(tx + px * side * 1.5), round(ty + py * side * 1.5), STEEL)
            c.set(round(tx + ux + px * side * 1.5), round(ty + uy + py * side * 1.5), STEEL_HI)


class DinerLegs(Legs):
    length = 12

    def __init__(self, look: dict) -> None:
        self.L = look

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            foot_y = ground - 1 - (0 if front else pose.lift)
            c.line(cx - 1, hip, fx, foot_y - 1, self.L["pants"], width=3)
            c.rect(fx, foot_y, 5, 2, self.L["shoe"])


class DinerTorso(Torso):
    def __init__(self, look: dict) -> None:
        self.L = look

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 4, top, 9, 12, self.L["shirt"])
        c.vline(cx - 4, top + 1, hip, self.L["shirt_sh"])
        c.set(cx - 4, top, None)
        c.set(cx + 4, top, None)
        c.stamp(cx - 1, top, ["#####", "#####", ".###.", ".###.", "..#.."], {"#": NAPKIN})   # tucked-in napkin
        c.set(cx, top + 3, NAPKIN_SH)
        c.set(cx + 2, top + 2, SAUCE)                           # they've eaten here before
        return Anchors(neck=(cx + 1, top), shoulder=(cx, top + 2), top=top, bottom=hip)


HAIRDOS = {
    "bob":   ["..hHHHHHH...", ".hHHHHHHHH..", ".HHHHHHHHHH.", ".HH.......H.", ".HH.........", ".HH.........",
              ".hH.........", ".h.........."],
    "bun":   ["....hHHh....", "....HHHH....", "..hHHHHHHH..", ".HHHHHHHHHH.", ".HH.........", ".H.........."],
    "bald":  ["............", "............", "............", "............", ".hH.........", ".hH........."],
    "quiff": [".......hHH..", "...hHHHHHHHH", "..HHHHHHHHH.", ".HHHHHHHHH..", ".HH.........", ".H.........."],
}
FACE = [
    "............",
    "............",
    "..SSSSSSSS..",
    ".SSSSSSSSSS.",
    ".SSSSSSBBSS.",
    ".SSSSSSSESS.",
    ".SSSSSSSSSSN",
    ".SSSSSSSSSS.",
    "..sSSSSMMMS.",
    "...sSSSSSS..",
    "....sSSSS...",
]


class DinerHead(Head):
    def __init__(self, look: dict) -> None:
        self.L = look

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        L = self.L
        c.rect(nx - 1, ny - 2, 3, 3, L["skin"])
        x0, y0 = nx - 5, ny - 12
        c.stamp(x0, y0, FACE, {"S": L["skin"], "s": L["skin_sh"], "N": L["skin"], "B": INK,
                               "E": INK, "M": "#5a1a1a"})
        c.stamp(x0, y0, HAIRDOS[L["style"]], {"H": L["hair"], "h": L["hair_sh"]})
        if L["style"] == "bald":
            c.set(x0 + 4, y0 + 3, "#ffffff")                    # shine
        if pose.anim == "attack":                               # snarling
            c.hline(x0 + 7, x0 + 9, y0 + 8, "#5a1a1a")
            c.set(x0 + 8, y0 + 8, "#ffffff")


class DinerArm(Arm):
    reach = 9
    fx_colors = (STEEL_HI, SAUCE)
    targets = {"windup": ((0.2, -1.0), (-0.3, -0.95)), "strike": ((1.0, 0.25), (0.6, 0.6)),
               "follow": ((0.95, 0.4), (0.7, 0.5))}

    def __init__(self, look: dict) -> None:
        self.L = look

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        dx = (2 if front else -2) * pose.swing
        sleeve = self.L["shirt"] if front else self.L["shirt_sh"]
        c.line(sx, sy, sx + dx, sy + 5, sleeve, width=2)
        hx, hy = sx + dx + 1, sy + 7
        utensil(c, hx, hy, 0.25, -1.0, "fork" if front else "knife")
        c.rect(sx + dx, sy + 6, 2, 2, self.L["skin"] if front else self.L["skin_sh"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = self.L["shirt"] if front else self.L["shirt_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, self.L["skin"] if front else self.L["skin_sh"], 2)
        dx, dy = (hx - sx, hy - sy) if mode in ("strike", "follow") else (0.3, -1.0)
        utensil(c, hx + 1, hy, dx, dy, "fork" if front else "knife")
        c.rect(hx, hy, 2, 2, self.L["skin"] if front else self.L["skin_sh"])


def diner(look: dict) -> BodyPlan:
    return BodyPlan(legs=DinerLegs(look), torso=DinerTorso(look), head=DinerHead(look),
                    front_arm=DinerArm(look), back_arm=DinerArm(look))


def diner_frames(look: dict) -> dict[str, list[Canvas]]:
    plan = diner(look)
    return {anim: [plan.render(p) for p in poses(anim)] for anim in ("idle", "run", "attack")}


# -- the other staff: obstacles running around the kitchen ---------------------------

SOUS = dict(CHEF, skin="#8a5a3a", skin_sh="#6a4028", nose="#a8704a", scarf="#3aa04a", scarf_sh="#26703a",
            hair="#1e1828", stache="#1e1828", stache_hi="#3a2f44", check="#3a3044")

SCIENTIST = {
    "skin": "#f0c8a8", "skin_sh": "#c89878", "coat": "#e8ecf4", "coat_sh": "#b8c0d0", "coat_dk": "#8a92a8",
    "shirt": "#5f9fd8", "tie": "#e83b3b", "pants": "#4a4a5a", "shoe": "#5a2a18",
    "hair": "#f4f4f4", "hair_sh": "#c8c8d8", "lens": "#5ff3ff", "rim": "#9aa0b0",
    "stain": "#39ff14", "flask": "#bfefff", "brew": "#39ff14", "pen": ("#e83b3b", "#2a6ac8"),
    "style": "einstein",
}
INTERN = dict(SCIENTIST, skin="#c08a5a", skin_sh="#9a6a40", hair="#1e1828", hair_sh="#3a2f44",
              tie="#ffd93a", shirt="#a24bff", pants="#25365e", shoe="#e8e8e8", style="onfire")
FIRE = ("#ff9a3a", "#ffd93a", "#e83b3b")
SCI_TARGETS = {
    "panic0": ((0.25, -1.0), (-0.6, -0.8)),       # running around screaming, arms up
    "panic1": ((0.6, -0.8), (-0.2, -1.0)),
    "pour":   ((0.95, -0.35), (0.6, 0.2)),        # holding the flask up to the light
}


class SciLegs(Legs):
    length = 11

    def __init__(self, look: dict) -> None:
        self.L = look

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            foot_y = ground - 1 - (0 if front else pose.lift)
            c.line(cx - 1, hip, fx, foot_y - 1, self.L["pants"], width=2)
            c.rect(fx, foot_y, 4, 2, self.L["shoe"])


class SciTorso(Torso):
    """Lab coat down past the hips, shirt and tie, pens in the pocket, a stain."""

    def __init__(self, look: dict) -> None:
        self.L = look

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        L = self.L
        top = hip - 11
        flap = (pose.frame % 2) if pose.anim == "run" else 0
        for y in range(top, hip + 6):                           # coat flares out toward the hem
            w = 4 + (y - top) // 5
            c.hline(cx - w - (flap if y > hip else 0), cx + w, y, L["coat"])
            c.set(cx - w - (flap if y > hip else 0), y, L["coat_sh"])
        c.vline(cx, top + 1, hip + 5, L["coat_sh"])            # the opening
        c.stamp(cx, top, ["###", ".#.", ".T.", ".T.", ".T."], {"#": L["shirt"], "T": L["tie"]})
        c.rect(cx + 2, top + 5, 3, 3, L["coat_sh"])            # breast pocket and pens
        c.set(cx + 2, top + 4, L["pen"][0])
        c.set(cx + 4, top + 4, L["pen"][1])
        c.set(cx - 2, top + 9, L["stain"])
        c.set(cx - 3, top + 10, L["stain"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx, top + 2), top=top, bottom=hip)


SCI_FACE = [
    "............",
    "..SSSSSSSS..",
    ".SSSSSSSSSS.",
    ".SSSSGGGGGG.",
    ".SSSSGLGGLG.",
    ".SSSSGGGGGGN",
    ".SSSSSSSSSNN",
    ".SSSSSSSSSS.",
    "..sSSSMMMMS.",
    "...sSSTTTS..",
    "....sSSSS...",
]
HAIR = {
    "einstein": ["H.h..H.H..h.", ".HHhHHHHHH..", "HHHHHHHHHHH.", "HHHH.......H", "HHH.........",
                 "HHHH........", ".HH.........", "HH.........."],
    "onfire": ["............", "..hHHHHHH...", ".HHHHHHHHHH.", ".HHH........", ".HH.........",
               ".HH........."],
}


class SciHead(Head):
    """Goggles, a manic grin, and either Einstein hair or hair that's on fire."""

    def __init__(self, look: dict) -> None:
        self.L = look

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        L = self.L
        c.rect(nx - 1, ny - 2, 3, 3, L["skin"])
        x0, y0 = nx - 5, ny - 12
        c.stamp(x0, y0, SCI_FACE, {"S": L["skin"], "s": L["skin_sh"], "N": L["skin"], "G": L["rim"],
                                   "L": L["lens"], "M": "#5a1a1a", "T": "#ffffff"})
        c.stamp(x0, y0 - 1, HAIR[L["style"]], {"H": L["hair"], "h": L["hair_sh"]})
        if L["style"] == "onfire":                              # flames dancing on top
            f = pose.frame % 2
            for i, fx in enumerate(range(x0 + 2, x0 + 10, 2)):
                h = 3 + (i + f) % 3
                c.vline(fx, y0 - h, y0, FIRE[0])
                c.vline(fx + 1, y0 - h + 2, y0, FIRE[1])
                c.set(fx, y0 - h, FIRE[2])
        else:
            c.set(x0 + 11, y0 - 1 + pose.frame % 2, L["hair"])      # a stray tuft that won't lie down


class SciArm(Arm):
    reach = 9
    targets = SCI_TARGETS

    def __init__(self, look: dict) -> None:
        self.L = look

    def flask(self, c: Canvas, hx: int, hy: int, frame: int) -> None:
        L = self.L
        c.stamp(hx - 1, hy - 7, ["..#..", "..#..", ".###.", "#####", "#####"], {"#": L["flask"]})
        c.hline(hx - 1, hx + 3, hy - 3, L["brew"])
        c.hline(hx - 1, hx + 3, hy - 4, L["brew"])
        c.set(hx + 1, hy - 9 - frame % 2, L["brew"])           # it bubbles over

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        sleeve = self.L["coat"] if front else self.L["coat_sh"]
        dx = (2 if front else -2) * pose.swing
        c.line(sx, sy, sx + dx, sy + 6, sleeve, width=2)
        c.rect(sx + dx, sy + 7, 2, 2, self.L["skin"] if front else self.L["skin_sh"])
        if front and self.L["style"] == "einstein":
            self.flask(c, sx + dx + 1, sy + 8, pose.frame)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = self.L["coat"] if front else self.L["coat_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        c.rect(hx, hy, 2, 2, self.L["skin"] if front else self.L["skin_sh"])
        if front and self.L["style"] == "einstein":
            self.flask(c, hx + 1, hy, pose.frame)


def scientist(look: dict) -> BodyPlan:
    return BodyPlan(legs=SciLegs(look), torso=SciTorso(look), head=SciHead(look),
                    front_arm=SciArm(look), back_arm=SciArm(look))


def _with_arms(plan: BodyPlan, base: str, arms) -> list[Canvas]:
    """Render an animation with the arm pose swapped: arms(i) -> (front, back)."""
    out = []
    for i, kw in enumerate(ANIMATIONS[base]):
        front, back = arms(i)
        out.append(plan.render(Pose(base, i, len(ANIMATIONS[base]), **{**kw, "arm": front, "back_arm": back})))
    return out


def staff_frames(who: str) -> dict[str, list[Canvas]]:
    """Frames for the other kitchen staff. Every one has walk, idle and hurt."""
    if who == "sous":
        plan = chef_plan(SOUS)
        out = {"walk": _with_arms(plan, "walk", lambda i: ("tray", None)),
               "idle": _with_arms(plan, "idle", lambda i: ("tray", None))}
    elif who == "scientist":
        plan = scientist(SCIENTIST)
        out = {anim: [plan.render(p) for p in poses(anim)] for anim in ("walk", "idle")}
        out["pour"] = _with_arms(plan, "idle", lambda i: ("pour", "recover"))
    else:
        plan = scientist(INTERN)
        out = {"walk": _with_arms(plan, "run", lambda i: (f"panic{i % 2}", None)),
               "idle": _with_arms(plan, "idle", lambda i: (f"panic{i % 2}", None))}
    out["hurt"] = [plan.render(p) for p in poses("hurt")]
    return out
