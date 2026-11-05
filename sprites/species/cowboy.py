"""Cowboy: ten-gallon hat, red bandana, leather vest, jingling spurs.
Fastest draw in the lab. Blows the smoke off the barrel every time, especially when he misses."""

from ..canvas import Canvas
from ..font import draw_text
from ..palette import INK, COWBOY as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, star

SPECIES = "cowboy"
PREFIX, SUFFIX = "Yee", "haw"


BOOT = [
    ".bBB...",
    ".bBB...",
    ".bBBB..",
    ".bBBBBt",
    ".HH.SSS",
]


class CowboyLegs(Legs):
    """Denim and pointy boots with spurs. Bow-legged when standing still."""
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        stance = 1 if pose.swing == 0 and not pose.tuck else 0
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s + (stance if front else -2 * stance)
            lift = 0 if front else pose.lift
            foot_y = ground - 1 - lift
            c.line(cx - 1, hip, fx, foot_y - 3, P["jeans"] if front else P["jeans_sh"], width=3)
            boot = {
                "b": P["boot_sh"], "B": P["boot"] if front else P["boot_sh"],
                "t": P["boot_hi"] if front else P["boot_sh"], "H": P["boot_sh"], "S": P["boot_sh"],
            }
            c.stamp(fx - 1, foot_y - 3, BOOT, boot)
            # spur: shank off the heel, rowel on the end. Jingles on every footfall.
            moving = pose.anim in ("walk", "run")
            c.set(fx - 1, foot_y, P["spur"])
            rowel = P["spur_hi"] if moving and front and pose.swing else P["spur"]
            if moving and pose.frame % 2:                      # the rowel spins as he walks
                c.vline(fx - 2, foot_y - 1, foot_y + 1, rowel)
            else:
                c.hline(fx - 3, fx - 2, foot_y, rowel)
            if front:
                c.set(fx + 1, foot_y - 1, P["boot_hi"])       # stitching on the shaft


class CowboyTorso(Torso):
    """Leather vest over a denim shirt, big belt buckle. Owns the holster."""
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 11
        c.rect(cx - 3, top, 7, 1, P["vest"])
        c.rect(cx - 4, top + 1, 9, 10, P["vest"])
        c.vline(cx - 4, top + 1, hip - 1, P["vest_sh"])
        c.vline(cx + 2, top, hip - 2, P["shirt"])             # shirt down the open front
        c.vline(cx + 3, top + 1, hip - 2, P["shirt_sh"])
        c.vline(cx + 4, top + 2, hip - 2, P["vest_hi"])       # front panel
        c.hline(cx - 2, cx, top + 4, P["vest_sh"])            # pocket
        c.set(cx + 4, top + 5, P["buckle"])                   # snap button
        c.hline(cx - 4, cx + 4, hip - 1, P["belt"])
        c.hline(cx - 4, cx + 4, hip, P["belt"])
        c.stamp(cx + 2, hip - 1, ["GGG", "GgG"], {"G": P["buckle"], "g": P["buckle_hi"]})
        # holster on the hip, six-shooter in it until he draws
        drawn = pose.anim == "attack" and pose.frame >= 1
        c.stamp(cx - 3, hip - 1, ["hhh", "hHh", "hhh", ".hh", ".h."],
                {"h": P["boot"], "H": P["boot_hi"]})
        if not drawn:
            c.stamp(cx - 5, hip - 3, ["gg..", ".gg.", "..m."], {"g": P["grip"], "m": P["gun_sh"]})
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 2), top=top, bottom=hip)


# Ten-gallon hat pulled down to the eyebrows, big drooping mustache, three days of stubble.
HEAD = [
    "......hKK.KKK....",
    ".....hKKKKKKKK...",
    ".....hKKKKKKKK...",
    "KK...RRRRRRRR..KK",
    ".hKKKKKKKKKKKKKK.",
    "..kkkkkkkkkkkkk..",
    "...HHsssssssss...",
    "...HHSSSSSSSSS...",
    "...HHSSSSSSBBS...",
    "...HSSSSSSSSES...",
    "...HSeSSSSSSSSN..",
    "....sSSSSSmmmS...",
    "....sstttmmmmt...",
    ".....sstttttt....",
]


class CowboyHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "h": P["hat_hi"], "K": P["hat"], "k": P["hat_sh"], "R": P["band"],
            "H": P["hair"], "S": P["skin"], "s": P["skin_sh"], "e": P["skin_sh"],
            "B": P["hair"], "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"],
            "t": P["stubble"], "m": P["stache"],
        }
        c.stamp(nx - 8, ny - 15, HEAD, key)
        # bandana knotted at the throat, point hanging in front
        c.rect(nx - 2, ny - 1, 5, 2, P["bandana"])
        c.stamp(nx, ny + 1, ["XXX", ".X."], {"X": P["bandana"]})
        c.set(nx - 2, ny, P["bandana_sh"])
        c.set(nx + 1, ny, P["dot"])
        c.set(nx - 1, ny - 1, P["dot"])


def six_shooter(c: Canvas, hx: int, hy: int, aim: str) -> tuple[int, int]:
    """Revolver in the hand at (hx, hy). Returns the muzzle."""
    if aim == "right":
        c.hline(hx + 1, hx + 6, hy - 1, P["gun"])
        c.hline(hx + 4, hx + 6, hy - 2, P["gun_hi"])            # barrel rib
        c.rect(hx + 2, hy - 2, 2, 2, P["gun_sh"])               # cylinder
        c.set(hx + 1, hy - 3, P["gun_sh"])                      # hammer
        c.set(hx + 3, hy, P["gun_sh"])                          # trigger guard
        c.set(hx - 1, hy + 1, P["grip"])
        return hx + 7, hy - 1
    if aim == "up_right":                                       # kicked up by the recoil
        c.line(hx + 1, hy - 1, hx + 5, hy - 5, P["gun"])
        c.line(hx + 2, hy - 1, hx + 6, hy - 5, P["gun_hi"])
        c.rect(hx + 1, hy - 2, 2, 2, P["gun_sh"])
        c.set(hx - 1, hy + 1, P["grip"])
        return hx + 6, hy - 6
    c.vline(hx + 1, hy - 7, hy - 1, P["gun"])                   # barrel up, by the lips
    c.vline(hx + 2, hy - 7, hy - 4, P["gun_hi"])
    c.rect(hx + 1, hy - 3, 2, 2, P["gun_sh"])
    c.set(hx - 1, hy + 1, P["grip"])
    return hx + 1, hy - 8


def bang(fx: Canvas, x: int, y: int) -> None:
    """Comic-book BANG burst with its top-left at (x, y)."""
    fx.rect(x, y, 17, 7, P["flash"])
    for px, py in ((x - 1, y + 2), (x - 2, y + 5), (x + 17, y + 1), (x + 17, y + 4),
                   (x + 3, y + 7), (x + 4, y + 8), (x + 12, y + 7)):
        fx.set(px, py, P["flash"])                             # jagged spikes
    draw_text(fx, x + 1, y + 1, "BANG", P["bandana"])


GUN_AIM = {"strike": "right", "follow": "up_right", "recover": "up"}


class CowboyArm(Arm):
    """Denim sleeve, hand hovering by the hip. Attack: quick-draw, BANG, blow the smoke off."""
    species = SPECIES
    reach = 9
    fx_colors = (P["flash_hot"], P["flash"])
    targets = {
        "windup":  ((-0.15, 0.8), (-0.4, 0.85)),             # hand on the holster...
        "strike":  ((0.6, 0.45), (-0.7, 0.55)),              # ...draw and fire from the hip
        "follow":  ((0.85, -0.35), (-0.6, 0.7)),             # recoil
        "recover": ((0.85, 0.2), (-0.25, 0.95)),             # blow the smoke off the barrel
    }

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if front:                                              # gun hand, never far from the holster
            dx = -pose.swing if pose.anim != "run" else -2 * pose.swing
            hx, hy = sx - 1 + dx, sy + 6
            c.stroke(sx, sy, hx, hy - 1, P["shirt"], 2)
            c.rect(hx, hy, 2, 2, P["skin"])
            if pose.anim == "idle":                            # itchy trigger finger
                c.set(hx + (pose.frame % 2), hy + 2, P["skin"])
        else:
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 6, P["shirt_sh"], width=2)
            c.rect(sx + dx, sy + 7, 2, 2, P["skin_sh"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        sleeve = P["shirt"] if front else P["shirt_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, sleeve, 2)
        c.stroke(ex, ey, hx, hy, sleeve, 2)
        if front and mode in GUN_AIM:
            mx, my = six_shooter(c, hx, hy, GUN_AIM[mode])
            if mode == "recover":                              # wisp of smoke off the barrel
                c.stamp(mx, my - 3, ["..ss", ".sss", "s..."], {"s": P["smoke"]})
        c.rect(hx, hy, 2, 2, P["skin"] if front else P["skin_sh"])

    def attack_fx(self, fx: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose) -> None:
        dx, dy = self.direction("strike", True)
        y = sy + round(dy * self.reach) - 1                    # the line of fire
        x0 = min(sx + round(dx * self.reach) + 7, fx.w - 12)   # the muzzle
        x1 = fx.w - 3
        if pose.fx == "swoosh":                                # muzzle flash + bullet streak
            star(fx, x0 + 2, y, P["flash_hot"], P["flash_r"], r=3)
            fx.rect(x0 + 1, y - 1, 3, 3, P["flash"])
            fx.set(x0 + 2, y, P["flash_hot"])
            fx.hline(x0 + 6, x1, y, P["flash"])                # the bullet
            fx.hline(x0 + 8, x1, y, P["flash_hot"])
        else:                                                  # ricochet spark, and the word itself
            star(fx, x1 - 2, y, P["flash_hot"], P["flash"], r=2)
            bang(fx, x1 - 17, 2)


GENES = dict(legs=CowboyLegs(), torso=CowboyTorso(), head=CowboyHead(), arm=CowboyArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
