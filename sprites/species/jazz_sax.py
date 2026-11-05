"""Jazz saxophonist: porkpie hat, shades, goatee, turtleneck under a sharp suit, and a
gleaming alto sax he never puts down. Plays the notes you don't hear. Then the ones that hurt."""

import math

from ..canvas import Canvas
from ..palette import JAZZ_SAX as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow

SPECIES = "jazz_sax"
PREFIX, SUFFIX = "Jazz", "phone"


# Alto sax with the mouthpiece at (3, 0): crook bends back into the body, bell flares
# forward at the bottom. k = keys (they catch the light), O = inside of the bell.
SAX = [
    "...ml.....",
    "..nn......",
    ".nn.......",
    ".hBk......",
    ".hBB......",
    ".hBk......",
    ".hBB...rr.",
    ".hBk..rOOr",
    ".hBBb.hBBb",
    ".hBBk.hBb.",
    ".hBBb.hBb.",
    "..hBBBBb..",
    "...bbbb...",
]
SAX_MOUTH = (3, 0)       # mouthpiece tip
SAX_HAND = (2, 8)        # where the front hand works the lower keys
SAX_BELL = (8, 7)        # middle of the bell opening


def sheared(x: int, y: int, tilt: float) -> int:
    """Column shift for row y when the sax is tilted (+ = bell swung forward)."""
    return x + round(y * tilt)


def sax(c: Canvas, x0: int, y0: int, tilt: float, frame: int) -> None:
    """Sax stamp with its top-left at (x0, y0), each row nudged forward by `tilt`.
    One key at a time catches the light, and every other frame the bell rim twinkles."""
    keys = [(i, j) for j, row in enumerate(SAX) for i, ch in enumerate(row) if ch == "k"]
    shine = keys[frame % len(keys)]
    key = {
        "m": P["reed"], "l": P["lig"], "n": P["brass"], "h": P["brass_hi"], "B": P["brass"], "b": P["brass_sh"],
        "k": P["key"], "r": P["brass_hi"], "O": P["brass_dk"],
    }
    for j, row in enumerate(SAX):
        c.stamp(sheared(x0, j, tilt), y0 + j, [row], key)
    c.set(sheared(x0 + shine[0], shine[1], tilt), y0 + shine[1], "#ffffff")
    if frame % 2 == 0:                                         # bell rim sparkle
        bx, by = sheared(x0 + 7, 6, tilt), y0 + 6
        c.set(bx, by, "#ffffff")
        c.set(bx, by - 1, P["brass_hi"])


# Sax tilt per arm pose: lean back to fill the lungs, swing the bell up to let it rip.
TILT = {
    "crouch": 0.0, "up": 0.3, "reach": 0.3, "out": 0.2,
    "windup": -0.2, "strike": 0.45, "follow": 0.35, "recover": 0.1, "flail": -0.3, "use": 0.2,
}


class JazzSaxLegs(Legs):
    """Sharp suit trousers and two-tone spectator shoes. Taps his foot on the off-beat."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1, hip, fx, foot_y - 1, P["suit"] if front else P["suit_sh"], width=3)
            if front:
                c.line(cx + 1, hip + 1, fx + 2, foot_y - 1, P["suit_hi"])   # pressed crease
            tap = front and pose.anim == "idle" and pose.frame % 2 == 1
            if tap:                                            # heel down, toe up
                c.rect(fx - 1, foot_y + 1, 3, 1, P["shoe_tip"])
                c.rect(fx, foot_y, 3, 1, P["shoe"])
                c.hline(fx + 2, fx + 4, foot_y - 1, P["shoe"])
                c.set(fx + 4, foot_y - 1, P["shoe_tip"])
                continue
            shoe = P["shoe"] if front else P["suit_sh"]
            c.rect(fx, foot_y, 4, 1, shoe)
            c.rect(fx - 1, foot_y + 1, 6, 1, shoe)
            c.hline(fx + 3, fx + 4, foot_y + 1, P["shoe_tip"])     # black wingtip toe...
            c.set(fx - 1, foot_y + 1, P["shoe_tip"])               # ...and heel


class JazzSaxTorso(Torso):
    """Black turtleneck under an open suit jacket, pocket square peeking out."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 3, top + 1, 8, 10, P["suit"])
        c.hline(cx - 2, cx + 3, top, P["suit"])
        c.vline(cx - 3, top + 1, hip - 1, P["suit_sh"])
        c.vline(cx + 4, top + 2, hip - 1, P["suit_hi"])
        c.rect(cx + 2, top, 2, hip - top - 2, P["turtle"])     # turtleneck down the open front
        c.rect(cx - 1, top - 1, 4, 2, P["turtle"])             # rolled collar
        c.hline(cx - 1, cx + 2, top - 1, P["turtle_hi"])
        for i in range(5):                                     # lapel
            c.set(cx + 1 + (i > 2), top + 1 + i, P["suit_hi"])
        c.set(cx + 2, hip - 4, P["suit"])                      # single button, buttoned
        c.set(cx + 3, hip - 4, P["suit_hi"])
        c.hline(cx - 2, cx, top + 4, P["square"])              # pocket square
        c.set(cx - 1, top + 3, P["square"])
        c.hline(cx - 3, cx + 4, hip, P["suit_sh"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


# Porkpie hat, shades with the arm back to the ear, pencil goatee.
HEAD = [
    "..ccccccc..",
    "..CCCCCCC..",
    "..RRRRRRR..",
    "bWWWWWWWWWb",
    ".HHHSSSSSSS",
    ".HHkkkKKKKS",
    ".HHSSSKKKKN",
    ".HsSSSSSSSS",
    "..sSSSSSSSS",
    "..sSSSSSSLL",
    "...sSSSGGS.",
    "....sSGGG..",
]


class JazzSaxHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 5, ny - 12
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "c": P["hat_hi"], "C": P["hat"], "R": P["band"], "W": P["hat"], "b": P["hat_sh"],
            "H": P["hair"], "S": P["skin"], "s": P["skin_sh"], "k": P["shades"], "K": P["shades"],
            "N": P["skin"], "L": P["skin_sh"], "G": P["goatee"],
        }
        c.stamp(x0, y0, HEAD, key)
        c.set(x0 + 9 - pose.frame % 2, y0 + 5, P["shades_hi"])   # glint slides across the lens
        c.set(x0 + 1, y0 + 4, P["hat_hi"])                     # dent in the crown
        if pose.anim == "attack" and pose.frame in (0, 1):     # Dizzy cheeks: puffed right out
            c.stamp(x0 + 8, y0 + 7, [".SS", "SSSs", ".sS"], {"S": P["skin_hi"], "s": P["skin"]})


class JazzSaxArm(Arm):
    """Front hand works the keys of the sax, which never leaves his lips (unless you hit him).
    Attacks by letting rip: a sound wave full of eighth notes that bursts on impact."""
    species = SPECIES
    reach = 8
    fx_colors = (P["note"], P["wave"])

    @staticmethod
    def sax_origin(sx: int, sy: int) -> tuple[int, int]:
        """Top-left of the sax stamp, with the mouthpiece where the mouth usually is."""
        return sx + 8 - SAX_MOUTH[0], sy - 5

    def play(self, c: Canvas, sx: int, sy: int, tilt: float, pose: Pose) -> None:
        x0, y0 = self.sax_origin(sx, sy)
        sax(c, x0, y0, tilt, pose.frame)
        hx, hy = sheared(x0 + SAX_HAND[0], SAX_HAND[1], tilt), y0 + SAX_HAND[1]
        ex, ey = sx + 1, sy + 6                                # elbow tucked in at the side
        c.stroke(sx, sy, ex, ey, P["suit"], 2)
        c.stroke(ex, ey, hx - 1, hy, P["suit"], 2)
        c.set(hx - 1, hy + 1, P["square"])                     # shirt cuff
        c.rect(hx, hy, 2, 2, P["skin"])
        c.set(hx + 1, hy - 1 - pose.frame % 2, P["skin"])      # fingers dancing on the keys

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if front:                                              # sways with the music
            tilt = {"idle": (0.0, 0.1, 0.2, 0.1), "run": (0.25,) * 4}.get(pose.anim, (0.05, 0.1, 0.05, 0.1))
            self.play(c, sx, sy, tilt[pose.frame % 4], pose)
            return
        dx = 2 * pose.swing
        c.line(sx, sy, sx + dx, sy + 7, P["suit_sh"], width=2)
        c.rect(sx + dx, sy + 8, 2, 2, P["skin_sh"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        if front and mode != "flail":                          # jumping, swinging: still playing
            self.play(c, sx, sy, TILT[mode], pose)
            return
        sleeve = P["suit"] if front else P["suit_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        if front:                                              # knocked off his lips, hangs from the hand
            tilt = TILT[mode]
            sax(c, hx - sheared(SAX_HAND[0], SAX_HAND[1], tilt), hy - SAX_HAND[1], tilt, pose.frame)
        c.rect(hx, hy, 2, 2, P["skin"] if front else P["skin_sh"])

    def bell(self, sx: int, sy: int, mode: str) -> tuple[int, int]:
        x0, y0 = self.sax_origin(sx, sy)
        return sheared(x0 + SAX_BELL[0], SAX_BELL[1], TILT[mode]), y0 + SAX_BELL[1]

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        bx, by = self.bell(sx, sy, "strike" if pose.fx == "swoosh" else "follow")
        if pose.fx == "swoosh":                                # BWAAAP: sound waves roll off the bell...
            for r, col in ((3, "#ffffff"), (6, P["wave"])):
                for i in range(9):
                    a = -1.2 + i * 0.2
                    x, y = round(bx + 1 + math.cos(a) * r), round(by + math.sin(a) * r)
                    if 2 <= x <= 45 and 2 <= y <= 45:
                        fx.set(x, y, col)
            note(fx, min(bx + 2, 40), by - 13)
            return
        x, y = min(bx + 2, 38), by - 13                        # ...and land in a burst of notes
        beamed(fx, x, y)
        note(fx, x - 6, y - 4)
        for i in range(5):                                     # one last wave fading off the bell
            fx.set(min(bx + 4, 45), by - 2 + i, P["wave"])
        for dx, dy in ((-2, -2), (8, 8), (-3, 4), (8, -2), (3, -3)):   # sparkle around the chord
            fx.set(min(x + dx, 45), y + dy, "#ffffff" if dx > 0 else P["wave"])


NOTE = ["..X..", "..XX.", "..X.X", "..X..", "XXX..", "XXX.."]
BEAMED = ["..XXXXX", "..XXXXX", "..X...X", "..X...X", "XXX.XXX", "XXX.XXX"]


def note(c: Canvas, x: int, y: int) -> None:
    """Eighth note with its top-left at (x, y)."""
    c.stamp(x, y, NOTE, {"X": P["note"]})
    c.set(x, y + 4, "#ffffff")


def beamed(c: Canvas, x: int, y: int) -> None:
    """Pair of beamed eighth notes."""
    c.stamp(x, y, BEAMED, {"X": P["note"]})
    c.set(x, y + 4, "#ffffff")
    c.set(x + 4, y + 4, "#ffffff")


GENES = dict(legs=JazzSaxLegs(), torso=JazzSaxTorso(), head=JazzSaxHead(), arm=JazzSaxArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
