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

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            foot_y = ground - 1 - (0 if front else pose.lift)
            c.line(cx - 1, hip, fx, foot_y - 1, CHEF["check"], width=3)
            for y in range(hip, foot_y):                       # houndstooth: little light checks
                t = (y - hip) / max(1, foot_y - 1 - hip)
                x = round(cx - 1 + (fx - cx + 1) * t)
                if (y + front) % 2 == 0:
                    c.set(x + (y // 2) % 3, y, CHEF["check_hi"] if front else CHEF["white_dk"])
            c.rect(fx - 1, foot_y, 6, 2, CHEF["clog"])          # clogs
            if front:
                c.set(fx + 2, foot_y, CHEF["clog_hi"])


class ChefTorso(Torso):
    species = "chef"

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - TORSO_H
        c.oval(cx - 6, top, 13, TORSO_H + 3, CHEF["white"])    # a well-fed chef
        c.vline(cx - 6, top + 3, hip, CHEF["white_sh"])
        c.vline(cx - 5, top + 6, hip, CHEF["white_sh"])
        for y in range(top + 3, hip, 3):                       # double-breasted buttons
            c.set(cx + 1, y, CHEF["button"])
            c.set(cx + 4, y, CHEF["button"])
        c.set(cx + 3, top + 8, CHEF["stain"])                  # a splash of something
        c.set(cx + 2, top + 9, CHEF["stain"])
        c.hline(cx - 6, cx + 6, hip, CHEF["white_sh"])
        c.rect(cx - 1, top - 1, 5, 2, CHEF["scarf"])           # neckerchief
        c.set(cx + 3, top + 1, CHEF["scarf_sh"])
        c.set(cx + 4, top + 1, CHEF["scarf"])
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

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, CHEF["skin"])
        eye = CHEF["skin_sh"] if pose.blink else INK
        if pose.arm == "cower" or pose.anim == "hurt":
            eye = INK
        key = {
            "W": CHEF["white"], "w": CHEF["white_sh"], "b": CHEF["white_dk"],
            "H": CHEF["hair"], "S": CHEF["skin"], "s": CHEF["skin_sh"], "E": eye,
            "N": CHEF["nose"], "M": CHEF["stache"],
        }
        x0, y0 = nx - 6, ny - 16
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 8, y0 + 12, CHEF["stache_hi"])
        if pose.anim == "hurt" or pose.arm == "cower":         # mouth wide in horror
            c.rect(x0 + 8, y0 + 14, 2, 2, INK)
            c.set(x0 + 7, y0 + 9, INK)                         # raised brow
            c.set(x0 + 8, y0 + 9, INK)


class ChefArm(Arm):
    species = "chef"
    reach = CHEF_REACH
    targets = CHEF_TARGETS

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        cloth = CHEF["white"] if front else CHEF["white_sh"]
        dx = (2 if front else -2) * pose.swing
        c.line(sx, sy, sx + dx, sy + 7, cloth, width=2)
        c.rect(sx + dx, sy + 8, 2, 2, CHEF["skin"] if front else CHEF["skin_sh"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        cloth = CHEF["white"] if front else CHEF["white_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, cloth, 2)
        c.stroke(ex, ey, hx, hy, cloth, 2)
        c.rect(hx, hy, 2, 2, CHEF["skin"] if front else CHEF["skin_sh"])


def chef() -> BodyPlan:
    arm = ChefArm()
    return BodyPlan(legs=ChefLegs(), torso=ChefTorso(), head=ChefHead(), front_arm=arm, back_arm=arm)


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
