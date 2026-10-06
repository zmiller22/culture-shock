"""Tech bro: puffer vest, chinos, white sneakers, AirPods, eyes locked on phone.
Totally normal. Probably."""

from ..canvas import Canvas
from ..palette import INK, TECH_BRO as P
from ..rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso

SPECIES = "tech_bro"
PREFIX, SUFFIX = "Bro", "bro"


class TechBroLegs(Legs):
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            lift = 1 if (pose.anim == "walk" and pose.swing == 0 and not front) else 0
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


HEAD = [
    "...hhhhh...",
    "..hHHHHHhh.",
    ".HHHHHHHHHh",
    ".HHHHHHHHHH",
    ".HHHHSSSSS.",
    ".HHHSSSBBS.",
    ".HHSSSSSES.",
    ".HSSSSSSSSN",
    ".HSASSSSSS.",
    "..sASSSSMS.",
    "...sSSSSS..",
    "....sSSS...",
]


class TechBroHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        c.vline(nx - 1, ny - 2, ny, P["skin_sh"])
        key = {
            "h": P["hair_hi"], "H": P["hair"], "S": P["skin"], "s": P["skin_sh"],
            "B": P["hair"], "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"],
            "A": P["airpod"], "M": P["skin_sh"],
        }
        c.stamp(nx - 5, ny - 13, HEAD, key)


class TechBroArm(Arm):
    """Front arm is permanently holding a phone. Back arm swings."""
    species = SPECIES

    def draw(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        if front:
            c.rect(sx, sy, 2, 5, P["shirt"])
            c.line(sx, sy + 5, sx + 4, sy + 4, P["shirt"])
            c.line(sx, sy + 4, sx + 4, sy + 3, P["shirt"])
            c.rect(sx + 5, sy + 3, 2, 2, P["skin"])
            c.rect(sx + 6, sy + 1, 2, 4, P["phone"])
            c.vline(sx + 6, sy + 1, sy + 3, P["screen"])
        else:
            dx = 2 * pose.swing
            c.line(sx, sy, sx + dx, sy + 7, P["shirt_sh"], width=2)
            c.rect(sx + dx, sy + 8, 2, 2, P["skin_sh"])


GENES = dict(legs=TechBroLegs(), torso=TechBroTorso(), head=TechBroHead(), arm=TechBroArm())


def build() -> BodyPlan:
    g = GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=g["head"], front_arm=g["arm"], back_arm=g["arm"])
