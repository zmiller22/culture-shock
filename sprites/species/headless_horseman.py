"""Headless Horseman: a rider in a tattered cloak on a black horse with a burning eye.
Lost his head years ago. Has been throwing pumpkins about it ever since."""

from ..canvas import Canvas, wave
from ..palette import HEADLESS_HORSEMAN as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star
from .centaur import GALLOP, JUMP, SINK, knee

SPECIES = "headless_horseman"
PREFIX, SUFFIX = "Headless", "horseman"


def smoke_wisp(c: Canvas, pts: list[tuple[int, int]], frame: int) -> None:
    """A trail of smoke, thick at the root and fraying into loose puffs at the end."""
    n = len(pts)
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(pts, pts[1:])):
        w = 3 if i < n // 2 else 2
        c.stroke(x0, y0, x1, y1, P["smoke"], w)
        if i < n - 2:
            c.line(x0, y0 - 1, x1, y1 - 1, P["smoke_hi"])
    ex, ey = pts[-1]
    for k, (dx, dy) in enumerate(((-2, -1), (-1, 2), (-3, 1))):     # puffs drifting off the tip
        if (frame + k) % 3:
            c.set(ex + dx - (frame + k) % 2, ey + dy, P["smoke_dk"] if k else P["smoke_hi"])


class HorseLegs(Legs):
    """The whole black horse: barrel, neck, head with a burning eye, four legs, a tail
    and mane of smoke. The rider's leg rides along, boot in the stirrup."""
    species = SPECIES
    length = 16

    def gait(self, pose: Pose) -> list[tuple[int, int]]:
        if pose.anim == "run":
            return GALLOP[pose.frame % 4]
        if pose.anim == "jump":
            return JUMP[pose.frame]
        s = 3 * pose.swing                                   # walk: diagonal pairs move together
        a_lift = pose.lift * 3 if pose.frame % 4 == 3 else 0
        b_lift = pose.lift * 3 if pose.frame % 4 == 1 else 0
        return [(s, a_lift), (-s, b_lift), (-s, b_lift), (s, a_lift)]

    def leg(self, c: Canvas, tx: int, ty: int, hx: int, ground: int, lift: int, fore: bool, near: bool) -> None:
        coat = P["coat"] if near else P["coat_sh"]
        lower = P["coat"] if near else P["coat_dk"]
        bottom = ground - lift
        fx, fy = hx, bottom - 2                              # fetlock
        kx, ky = knee(tx, ty, fx, fy, 5.6 if fore else 6.2, forward=fore)
        if not fore:
            c.oval(tx - 3, ty - 3, 6, 6, coat)               # gaskin muscle
        c.stroke(tx, ty, kx, ky, coat, 3)
        c.stroke(kx, ky, fx, fy, lower, 2)
        c.rect(fx, bottom - 1, 3, 2, P["hoof"])
        if near:
            c.set(fx + 2, bottom - 1, P["hoof_hi"])
            c.line(kx + 1, ky + 1, fx + 1, fy, P["coat_hi"])    # shine down the front of the cannon
            c.set(kx + (1 if fore else 0), ky, P["coat_hi"])

    def neck_tilt(self, pose: Pose) -> int:
        """How far the head drops (+) or rears up (-)."""
        if pose.anim == "run":
            return 2 + (pose.frame % 2)
        if pose.anim == "jump":
            return (-2, -3, 0, 1)[pose.frame]
        if pose.anim in ("hurt", "death"):
            return -3                                          # rears up
        if pose.anim == "attack":
            return (0, -1, -2, -1)[pose.frame]
        return pose.frame % 2 if pose.anim == "walk" else (0, 0, 1, 1)[pose.frame % 4]

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        g = self.gait(pose)
        back = hip - SINK                                    # the horse's back line
        fore_x, hind_x, top = cx + 4, cx - 9, back + 5
        # far side legs first
        self.leg(c, fore_x - 2, top, fore_x - 2 + g[1][0], ground, g[1][1], True, False)
        self.leg(c, hind_x - 2, top, hind_x - 2 + g[3][0], ground, g[3][1], False, False)
        self.tail(c, cx, back, pose)
        # neck and head
        t = self.neck_tilt(pose)
        hx, hy = cx + 13, back - 10 + t                      # poll (top of the head)
        c.stroke(cx + 6, back + 2, hx, hy + 3, P["coat"], 5)
        c.stroke(cx + 4, back + 2, hx - 2, hy + 4, P["coat"], 3)
        self.head(c, hx, hy, pose)
        # barrel: rump, belly, chest
        c.oval(cx - 13, back - 2, 9, 8, P["coat"])
        c.oval(cx - 11, back - 1, 19, 8, P["coat"])
        c.oval(cx + 2, back - 1, 8, 8, P["coat"])
        for x in range(cx - 13, cx + 10):                    # belly shadow, back highlight
            span = [y for y in range(back - 3, back + 8) if c.get(x, y) == P["coat"]]
            if span:
                c.set(x, span[-1], P["coat_sh"])
                if cx - 11 <= x <= cx - 4:
                    c.set(x, span[0], P["coat_hi"])
        c.line(cx + 8, back - 1, hx - 1, hy + 2, P["coat_hi"])   # crest of the neck catching the light
        self.mane(c, cx, back, hx, hy, pose)
        # saddle blanket, saddle
        c.rect(cx - 5, back - 1, 9, 5, P["blanket"])
        c.hline(cx - 5, cx + 3, back + 3, P["lining_sh"])
        c.rect(cx - 4, back - 2, 7, 2, P["tack"])
        c.set(cx - 5, back - 3, P["tack"])                   # cantle
        c.set(cx + 3, back - 3, P["tack_hi"])                # pommel
        # near side legs on top
        self.leg(c, hind_x, top, hind_x + g[2][0], ground, g[2][1], False, True)
        self.leg(c, fore_x, top, fore_x + g[0][0], ground, g[0][1], True, True)
        self.rider_leg(c, cx, hip, back, pose)

    def head(self, c: Canvas, hx: int, hy: int, pose: Pose) -> None:
        """Long head angled down toward the muzzle; (hx, hy) is the poll."""
        c.set(hx, hy - 1, P["coat"])                         # ears
        c.set(hx + 1, hy - 2, P["coat_hi"])
        c.set(hx + 1, hy - 1, P["coat"])
        c.oval(hx - 2, hy, 6, 6, P["coat"])                  # cheek
        c.stroke(hx + 1, hy + 2, hx + 5, hy + 6, P["coat"], 4)   # face, down to the muzzle
        c.oval(hx + 4, hy + 5, 4, 4, P["coat"])
        c.line(hx + 1, hy, hx + 6, hy + 5, P["coat_hi"])     # bony ridge of the face
        c.hline(hx - 1, hx + 2, hy + 5, P["coat_sh"])        # jaw
        c.set(hx + 7, hy + 7, P["coat_dk"])                  # nostril
        c.hline(hx + 4, hx + 6, hy + 8, P["coat_sh"])        # lips
        c.line(hx - 1, hy + 1, hx + 4, hy + 6, P["tack"])    # bridle
        c.vline(hx + 4, hy + 6, hy + 7, P["bit"])
        c.set(hx + 1, hy + 1, P["eye"])                      # the burning eye
        c.set(hx + 2, hy + 1, P["eye_hot"])
        c.set(hx + 2, hy + 2, P["eye"])

    def mane(self, c: Canvas, cx: int, back: int, hx: int, hy: int, pose: Pose) -> None:
        """Smoke smouldering along the crest of the neck, streaming back faster the faster he goes."""
        speed = {"run": 2, "jump": 2, "walk": 1}.get(pose.anim, 0)
        x0, y0, x1, y1 = hx - 1, hy, cx + 7, back - 2
        c.line(x0, y0, x1, y1, P["smoke"])
        c.line(x0 - 1, y0, x1 - 1, y1, P["smoke"])
        for k in range(3):                                   # wisps curling up off the crest
            u = (k + 0.5) / 3
            bx, by = round(x0 + (x1 - x0) * u), round(y0 + (y1 - y0) * u)
            flick = (pose.frame + k) % 2
            pts = [(bx, by), (bx - 1 - speed, by - 2), (bx - 2 - 2 * speed + flick, by - 3 - flick)]
            for (ax, ay), (bx2, by2) in zip(pts, pts[1:]):
                c.line(ax, ay, bx2, by2, P["smoke"])
            c.set(*pts[-1], P["smoke_hi"])
            c.set(pts[1][0] + 1, pts[1][1], P["smoke_hi"])

    def tail(self, c: Canvas, cx: int, back: int, pose: Pose) -> None:
        """A tail made of smoke: hangs and curls when idle, streams out behind at a gallop."""
        sway = wave(pose.frame, pose.n, 1.0)
        if pose.anim in ("run", "jump"):
            pts = [(cx - 12, back - 1), (cx - 15, back - 1), (cx - 17, back + 1), (cx - 18, back + 3 + sway)]
        else:
            pts = [(cx - 12, back - 1), (cx - 15, back + 1), (cx - 16 + sway, back + 6), (cx - 15 + sway, back + 11)]
        smoke_wisp(c, pts, pose.frame)

    def rider_leg(self, c: Canvas, cx: int, hip: int, back: int, pose: Pose) -> None:
        """The rider's near leg: thigh over the saddle, boot in the stirrup."""
        kx, ky = cx + 2, back + 3
        ankle_y = back + 8 - (1 if pose.anim == "run" and pose.frame % 2 else 0)
        c.stroke(cx - 1, hip, kx, ky, P["breeches"], 3)
        c.stroke(kx, ky, kx, ankle_y - 1, P["boot"], 3)
        c.rect(kx - 1, ankle_y, 4, 2, P["boot"])
        c.vline(kx + 1, ky + 1, ankle_y - 1, P["boot_hi"])
        c.set(kx, ky, P["boot_hi"])                          # top of the boot cuff
        c.line(kx - 2, back + 2, kx - 2, ankle_y, P["tack"])  # stirrup leather
        c.hline(kx - 1, kx + 2, ankle_y + 2, P["iron"])      # stirrup iron


class HorsemanTorso(Torso):
    """Long dark coat with a high collar and a tattered cloak lined in red."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        self.cloak(c, cx, top, hip, pose)
        c.rect(cx - 3, top + 1, 7, 10, P["cloak"])
        c.rect(cx - 2, top, 5, 1, P["cloak"])
        c.vline(cx + 3, top + 1, hip - 1, P["cloak_hi"])
        c.vline(cx - 3, top + 1, hip, P["cloak_sh"])
        for y in (top + 3, top + 5, top + 7):                 # brass buttons
            c.set(cx + 2, y, P["brass"])
        c.hline(cx - 3, cx + 3, hip - 2, P["boot"])           # sword belt
        c.set(cx + 1, hip - 2, P["brass"])
        c.rect(cx - 3, hip - 1, 7, 2, P["cloak_sh"])          # coat skirt
        c.set(cx + 3, hip, P["cloak"])
        # high collar standing up around the (missing) neck
        c.stamp(cx - 2, top - 3, ["Cl...h", "CL...C", "CCCWCC"], {
            "L": P["lining"], "l": P["lining_sh"], "C": P["cloak"], "h": P["cloak_hi"], "W": P["cravat"]})
        c.set(cx + 2, top + 1, P["cravat"])                    # a gentleman, once
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)

    def cloak(self, c: Canvas, cx: int, top: int, hip: int, pose: Pose) -> None:
        """Cloak hanging off the shoulders; it billows out behind at speed. Ragged hem."""
        flow = {"run": 5, "jump": 4, "walk": 2, "hurt": 3, "death": 3}.get(pose.anim, 0)
        flap = wave(pose.frame, pose.n)
        x0, hem = cx - 2, hip + 2 - flow // 2
        for y in range(top, hem + 1):
            u = (y - top) / max(1, hem - top)
            left = round(x0 - 1 - (flow + 1) * u - (flap if u > 0.6 else 0))
            c.hline(left, x0 + 1, y, P["cloak_sh"])
            c.set(left, y, P["lining"])
        for k, x in enumerate(range(x0 - flow - 2, x0 + 2)):  # tattered hem
            if (k + pose.frame) % 3:
                c.vline(x, hem + 1, hem + 1 + (k * 7 + pose.frame) % 3, P["cloak_sh"])


# Ghost-fire, four flickers. Bottom row sits just above the neck stump.
FLAMES = [
    ["...o...", "..g....", "..gg.o.", ".gGg.g.", ".gGgggg", "ggGWGg.", ".gGWGgg", ".gGWWGg", "..gGGg."],
    [".o.....", "..g..o.", "..gg.g.", ".gGg.gg", ".gGGgg.", "ggGWGgg", ".gGWWg.", ".gGWWGg", "..gGGg."],
    ["....o..", "...g...", ".o.gg..", ".g.gGg.", ".ggGGg.", "ggGWGgg", "gGGWGg.", ".gGWWGg", "..gGGg."],
    ["..o....", "..g..o.", "..gg..g", ".ggGg.g", ".gGGggg", ".gGWGg.", "ggGWWgg", ".gGWWGg", "..gGGg."],
]


class HeadlessHead(Head):
    """No head at all: a neck stump, and ghost-fire where the head used to be."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.hline(nx - 1, nx + 1, ny - 1, P["stump"])
        c.hline(nx - 1, nx + 1, ny - 2, P["stump_hi"])
        trail = {"run": -3, "jump": -2, "walk": -1, "hurt": 2, "death": 2}.get(pose.anim, 0)   # blown back by speed
        rows = FLAMES[(pose.frame + (pose.anim == "walk")) % len(FLAMES)]
        key = {"g": P["flame"], "G": P["flame_hi"], "W": P["flame_core"], "o": P["ember"]}
        n = len(rows)
        for j, row in enumerate(rows):
            shear = round(trail * (n - 1 - j) / (n - 1))
            c.stamp(nx - 3 + shear, ny - 2 - n + j, [row], key)


def jack(c: Canvas, x: int, y: int, frame: int, lit: bool = True) -> None:
    """Carved jack-o'-lantern, 7x6, top-left at (x, y), grinning to the right."""
    key = {"O": P["pumpkin"], "o": P["pumpkin_sh"], "h": P["pumpkin_hi"], "s": P["stem"],
           "f": P["candle"] if frame % 2 else P["candle_hot"], "F": P["candle"]}
    c.stamp(x, y, [
        "...s...",
        ".oOOhO.",
        "oOfOOfO",
        "oOOOOOh",
        "oOfFfFO",
        ".oOOOO.",
    ], key)


class HorsemanArm(Arm):
    """Dark sleeve, black glove, and a jack-o'-lantern. Attack: hurls it, flaming."""
    species = SPECIES
    reach = 9
    fx_colors = (P["ember"], P["candle"])
    targets = {
        "windup": ((-0.6, -0.8), (-0.4, 0.85)),              # pumpkin cocked back over the shoulder...
        "strike": ((1.0, -0.3), (-0.7, 0.55)),                # ...and let fly
        "follow": ((0.9, 0.35), (-0.6, 0.7)),
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        sleeve = P["cloak"] if front else P["cloak_sh"]
        if front:                                            # lantern held out front, swaying
            ex, ey = sx + 1, sy + 5
            hx, hy = sx + 5, sy + 6 + abs(pose.swing) // 2
            c.stroke(sx, sy, ex, ey, sleeve, 2)
            c.stroke(ex, ey, hx, hy, sleeve, 2)
            jack(c, hx, hy - 2, pose.frame)
            c.rect(hx, hy - 1, 2, 2, P["glove"])
        else:
            dx = 2 * pose.swing
            c.stroke(sx, sy, sx + dx, sy + 6, sleeve, 2)
            c.rect(sx + dx, sy + 7, 2, 2, P["glove"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = P["cloak"] if front else P["cloak_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        if front and mode not in ("strike", "follow"):        # the pumpkin's in the air on those
            jack(c, hx - 2, hy - 6, pose.frame)
        c.rect(hx, hy, 2, 2, P["glove"])
        if front:
            c.set(hx + 1, hy, P["glove_hi"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        if pose.fx == "swoosh":                              # the pumpkin in flight, trailing fire
            px, py = min(hx + 4, 37), hy - 6
            for i in range(1, 10):                           # comet tail, sweeping down from the wind-up
                x, y = px - i + 1, py + 2 - round(0.08 * i * i)
                w = 3 if i < 4 else 2 if i < 7 else 1
                col = P["candle_hot"] if i < 3 else P["candle"] if i < 5 else P["ember"] if i < 8 else P["pumpkin_sh"]
                fx.vline(x, y - w // 2, y - w // 2 + w - 1, col)
            jack(fx, px, py, pose.frame)
        else:                                                # SPLAT: pumpkin guts and green fire
            x, y = min(hx + 8, 40), hy - 7
            star(fx, x, y, P["candle"], P["ember"], r=5)
            fx.oval(x - 2, y - 2, 5, 5, P["ember"])
            fx.oval(x - 1, y - 1, 3, 3, P["candle"])
            fx.set(x, y, P["candle_hot"])
            for dx, dy, col in ((-4, -3, P["pumpkin"]), (3, -4, P["pumpkin_hi"]), (4, 2, P["pumpkin"]),
                                (-4, 2, P["pumpkin_sh"]), (1, 4, P["flame"]), (-1, -5, P["flame_hi"])):
                fx.rect(x + dx, y + dy, 2, 2, col)
            for dx, dy in ((-2, -5), (5, -1), (-5, 0), (2, 5)):   # seeds
                fx.set(x + dx, y + dy, P["cravat"])


GENES = dict(legs=HorseLegs(), torso=HorsemanTorso(), head=HeadlessHead(), arm=HorsemanArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
