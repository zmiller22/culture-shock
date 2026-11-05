"""Tech bro: puffer vest, chinos, white sneakers, AirPods, eyes locked on phone.
Totally normal. Probably."""

from ..canvas import Canvas
from ..font import draw_text, text_width
from ..palette import INK, OUTLINE, TECH_BRO as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "tech_bro"
PREFIX, SUFFIX = "Bro", "bro"


class TechBroLegs(Legs):
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            pants = P["pants"] if front else P["pants_sh"]
            shoe = P["shoe"] if front else P["sole"]
            c.line(cx - 1, hip, fx, foot_y - 1, pants, width=3)
            c.rect(fx, foot_y, 4, 1, shoe)
            c.rect(fx - 1, foot_y + 1, 6, 1, shoe)
            if front:
                c.hline(fx - 1, fx + 4, foot_y + 1, P["sole"])
                c.set(fx + 1, foot_y, P["shirt_sh"])  # tiny logo swoosh


class TechBroTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 3, top, 7, 1, P["vest"])
        c.rect(cx - 4, top + 1, 9, 10, P["vest"])
        c.vline(cx + 4, top + 1, hip - 2, P["vest_hi"])
        c.vline(cx - 4, top + 1, hip - 2, P["vest_sh"])
        for y in (top + 4, top + 7):                      # puffer quilting
            c.hline(cx - 3, cx + 3, y, P["vest_sh"])
        c.hline(cx - 4, cx + 4, hip - 1, P["shirt"])      # untucked shirt hem
        c.hline(cx - 4, cx + 4, hip, P["belt"])
        c.set(cx + 3, hip, P["buckle"])
        c.stamp(cx + 1, top, ["SSS", "..S"], {"S": P["shirt"]})  # collar
        c.set(cx + 2, top + 2, P["logo"])
        c.set(cx + 3, top + 2, P["logo"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


# Chin tucked, eyes down, face lit by the screen.
HEAD = [
    "...hhhhh...",
    "..hHHHHHhh.",
    ".HHHHHHHHHh",
    ".HHHHHHHHHH",
    ".HHHHSSSSS.",
    ".HHHSSSSSS.",
    ".HHSSSSBBS.",
    ".HSSSSSSEg.",
    ".HSASSSSSgN",
    "..sASSSSSg.",
    "...sSSSMg..",
    "....sSSg...",
]


class TechBroHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "S": P["skin"], "s": P["skin_sh"],
            "B": P["hair"], "E": P["glow_sh"] if pose.blink else INK, "N": P["glow"],
            "A": P["airpod"], "M": P["glow_sh"], "g": P["glow"],
        }
        c.stamp(nx - 5, ny - 13, HEAD, key)


def phone(c: Canvas, x: int, y: int, frame: int) -> None:
    """3x5 phone, screen toward us, doomscrolling (a bright line slides up the feed)."""
    c.rect(x, y, 3, 5, P["phone"])
    c.rect(x + 1, y + 1, 2, 3, P["screen"])
    c.set(x + 1 + frame % 2, y + 3 - frame % 3, "#ffffff")


class TechBroArm(Arm):
    """Front arm holds the phone up to his face, permanently. His attack: a point-blank camera flash."""
    species = SPECIES
    reach = 9
    fx_colors = ("#ffffff", P["screen"])
    targets = {"strike": ((1.0, -0.25), (-0.7, 0.55)), "follow": ((1.0, -0.15), (-0.6, 0.7))}

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if front:
            ex, ey = sx + 1, sy + 6                            # elbow tucked at the waist
            hx, hy = sx + 7, sy - 2
            c.stroke(sx, sy, ex, ey, P["shirt"], 2)
            c.stroke(ex, ey, hx - 1, hy + 1, P["shirt"], 2)
            phone(c, hx + 1, hy - 4, pose.frame)
            c.rect(hx, hy - 1, 2, 2, P["skin"])
            c.set(hx + 1, hy - 2 - pose.frame % 2, P["skin"])  # thumb tapping the glass
        else:
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 7, P["shirt_sh"], width=2)
            c.rect(sx + dx, sy + 8, 2, 2, P["skin_sh"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = P["shirt"] if front else P["shirt_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        if front:                                              # never lets go of the phone
            phone(c, hx + 1, hy - 3, pose.frame)
            if mode not in ("strike", "follow"):               # screen only faces out to take the shot
                c.rect(hx + 2, hy - 2, 1, 3, P["phone"])
        c.rect(hx, hy, 2, 2, P["skin"] if front else P["skin_sh"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        x, y = hx + 5, hy - 1
        if pose.fx == "swoosh":                                # FLASH
            star(fx, x, y, "#ffffff", P["screen"], r=4)
            fx.oval(x - 1, y - 1, 3, 3, "#ffffff")
        else:
            for dx, dy in ((1, -3), (3, 0), (1, 3), (4, -2), (4, 2)):   # afterglow sparkles
                fx.set(x + dx, y + dy, "#ffffff")


def speech_bubble(c: Canvas, x: int, y: int, text: str) -> None:
    """Outlined speech bubble with its top-left corner at (x, y) and the tail at the bottom left."""
    w, h = text_width(text) + 4, 9
    c.rect(x + 1, y, w - 2, h, OUTLINE)                        # rounded corners
    c.rect(x, y + 1, w, h - 2, OUTLINE)
    c.rect(x + 1, y + 1, w - 2, h - 2, P["bubble"])
    draw_text(c, x + 2, y + 2, text, INK)
    c.stamp(x, y + h - 1, ["..WW", ".KWK", "KWK.", "KK.."], {"W": P["bubble"], "K": OUTLINE})


def pitch(out: Canvas, layers: dict, info: dict, pose: Pose) -> None:
    """Always pitching. A hit only interrupts him for a frame; dying finally shuts him up."""
    if pose.flash or pose.melt:
        return
    nx, ny = info["anchors"].neck
    speech_bubble(out, nx + 5, max(1, ny - 21), "!?" if pose.anim == "hurt" else "YC")


GENES = dict(legs=TechBroLegs(), torso=TechBroTorso(), head=TechBroHead(), arm=TechBroArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"],
                    decorations=[pitch])
