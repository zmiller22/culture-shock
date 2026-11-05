"""Alien: a little grey visitor in a silver jumpsuit. Big head, bigger eyes,
and a ray gun it is not afraid to use. Comes in peace. Mostly."""

from ..canvas import Canvas
from ..palette import INK, ALIEN as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "alien"
PREFIX, SUFFIX = "Zorp", "zorp"


class AlienLegs(Legs):
    species = SPECIES
    length = 10

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1, hip, fx, foot_y - 1, P["suit"] if front else P["suit_sh"], width=2)
            boot = P["boot"] if front else P["eye_hi"]
            c.rect(fx - 1, foot_y, 4, 2, boot)
            c.set(fx + 3, foot_y + 1, boot)                    # pointy space-toes
            if front:
                c.set(fx, foot_y, P["boot_hi"])


class AlienTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 9
        c.rect(cx - 2, top + 1, 5, hip - top, P["suit"])
        c.vline(cx - 2, top + 1, hip, P["suit_sh"])
        c.vline(cx + 2, top + 2, hip - 2, P["suit_hi"])
        c.hline(cx - 2, cx + 2, top, P["trim"])                # collar ring
        c.hline(cx - 2, cx + 2, hip - 2, P["trim"])            # utility belt
        c.set(cx + 1, hip - 2, P["suit_hi"])
        c.stamp(cx, top + 3, ["T.T", ".T."], {"T": P["trim"]})  # rank insignia
        c.hline(cx - 1, cx + 1, hip, P["suit_sh"])
        return Anchors(neck=(cx, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


HEAD = [
    "....hhhhhh.....",
    "..hhHHHHHHhh...",
    ".hHHHHHHHHHHh..",
    ".HHHHHHHHHHHHH.",
    "sHHHHHHHHHHHHHH",
    "sHHHeeeHHHHHHee",
    "sHHEEgEEEHHHEEE",
    "sHHEEEEEEEHHEEE",
    ".sHHEEEEEwHHEEH",
    ".sHHHHeeeeHHHeH",
    "..sHHHHHHHHHHHH",
    "...sHHHHHHHHmH.",
    "....ssHHHHHHH..",
    "......ssHHHH...",
]


class AlienHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx, ny - 2, 2, 3, P["skin_sh"])                 # pencil neck
        key = {
            "h": P["skin_hi"], "H": P["skin"], "s": P["skin_sh"], "m": P["mouth"],
            "E": P["eye"], "e": P["skin_sh"] if pose.blink else P["eye"],
            "g": P["eye"] if pose.blink else P["glint"],
            "w": P["eye"] if pose.blink else P["eye_hi"],     # wet sheen
        }
        c.stamp(nx - 7, ny - 14, HEAD, key)


GUN = [
    ".F.....",
    "RRRRmmE",
    "RrRR.m.",
    ".FG....",
]


class AlienArm(Arm):
    """Noodly grey arm in a silver sleeve. The front hand never puts down the ray gun.
    Attack: ZAP."""
    species = SPECIES
    reach = 8
    fx_colors = (P["beam"], "#ffffff")
    targets = {
        "windup": ((0.55, 0.65), (-0.4, 0.85)),              # charge it at the hip...
        "strike": ((1.0, -0.15), (-0.7, 0.55)),              # ...then snap it up and fire
        "follow": ((0.95, -0.3), (-0.6, 0.7)),               # recoil
        "recover": ((0.7, 0.5), (-0.25, 0.95)),
    }

    def gun(self, c: Canvas, hx: int, hy: int, firing: bool) -> None:
        key = {"R": P["gun"], "r": P["gun_hi"], "F": P["gun_sh"], "G": P["gun_sh"], "m": P["metal"],
               "E": "#ffffff" if firing else P["glow"]}
        c.stamp(hx - 1, hy - 2, GUN, key)

    def hand(self, c: Canvas, hx: int, hy: int, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        c.rect(hx, hy, 2, 2, skin)
        c.set(hx + 2, hy + 1, skin)                            # long finger

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if front:                                              # gun held low, pointed forward
            c.stroke(sx, sy, sx, sy + 4, P["suit"], 2)
            c.line(sx + 1, sy + 5, sx + 4, sy + 6, P["skin"])
            self.gun(c, sx + 4, sy + 6, False)
            c.rect(sx + 4, sy + 6, 2, 2, P["skin"])
        else:
            dx = 2 * pose.swing
            c.stroke(sx, sy, sx + dx // 2, sy + 4, P["suit_sh"], 2)
            c.line(sx + dx // 2, sy + 5, sx + dx, sy + 8, P["skin_sh"])
            self.hand(c, sx + dx, sy + 8, False)

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, P["suit"] if front else P["suit_sh"], 2)
        c.line(ex, ey, hx, hy, P["skin"] if front else P["skin_sh"])
        if front:
            self.gun(c, hx, hy, mode in ("windup", "strike"))
            c.rect(hx, hy, 2, 2, P["skin"])
        else:
            self.hand(c, hx, hy, False)

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        x0, y = hx + 6, hy - 1                                 # just past the muzzle
        x1 = fx.w - 3
        if pose.fx == "swoosh":                                # fat zigzag beam to the edge of the frame
            for i, x in enumerate(range(x0, x1 + 1)):
                dy = (0, -1, 0, 1)[i % 4]
                fx.vline(x, y + dy - 1, y + dy + 1, P["beam_alt"] if i % 4 == 2 else P["beam"])
                fx.set(x, y + dy, "#ffffff")
            fx.vline(x1, y - 2, y + 2, P["beam"])              # beam front
            star(fx, x0, y, "#ffffff", P["beam"], r=3)
        else:                                                  # zap rings fizzling out
            x = min(x0 + 4, x1 - 3)
            for r, col in ((3, P["beam"]), (1, "#ffffff")):
                for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                    fx.set(x + dx, y + dy, col)
            for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
                fx.set(x + dx, y + dy, P["beam_alt"])


GENES = dict(legs=AlienLegs(), torso=AlienTorso(), head=AlienHead(), arm=AlienArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
