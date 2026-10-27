"""The hairy man: what comes out after the target chews on a baby for a while.

A full-grown, bearded, hairy-chested newborn in a diaper, still on his pacifier.
He's built from rig genes like the main cast, so he gets every animation state.
"""

from sprites.canvas import Canvas
from sprites.palette import INK
from sprites.rig import Anchors, Arm, BodyPlan, Head, Legs, Pose, Torso, elbow, poses

SPECIES = "hairy_man"

P = {
    "skin": "#e8b48a", "skin_sh": "#c08a66", "shine": "#fff0dc",
    "hair": "#3a2414", "hair_hi": "#5a3a22",
    "diaper": "#f4f4f4", "diaper_sh": "#c8c8d8", "pin": "#9aa0b0",
    "paci": "#5ff3ff", "paci_ring": "#ff6a9a",
}


def hair_flicks(c: Canvas, x0: int, y0: int, x1: int, y1: int, step: int = 2) -> None:
    """Sprinkle short dark hairs over any skin in the box."""
    for y in range(y0, y1 + 1, step):
        for x in range(x0 + (y // step) % 2, x1 + 1, 2):
            if c.get(x, y) in (P["skin"], P["skin_sh"]):
                c.set(x, y, P["hair"])


class HairyLegs(Legs):
    species = SPECIES
    length = 12

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        for front in (False, True):
            s = pose.swing if front else -pose.swing
            fx = cx - 1 + 3 * s
            foot_y = ground - 1 - (0 if front else pose.lift)
            skin = P["skin"] if front else P["skin_sh"]
            c.line(cx - 1, hip, fx, foot_y - 1, skin, width=3)
            hair_flicks(c, min(cx, fx) - 2, hip + 3, max(cx, fx) + 3, foot_y - 2, step=3)
            c.rect(fx, foot_y, 5, 2, skin)                    # bare feet
            c.set(fx + 5, foot_y + 1, skin)
            if front:
                c.set(fx + 4, foot_y, P["skin_sh"])           # toes


class HairyTorso(Torso):
    species = SPECIES

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        top = hip - 13
        c.oval(cx - 5, top, 11, 15, P["skin"])                # pot belly
        c.oval(cx - 2, top + 5, 9, 9, P["skin"])
        c.vline(cx - 5, top + 3, hip - 3, P["skin_sh"])
        hair_flicks(c, cx - 4, top + 1, cx + 6, top + 6, step=1)   # carpet of chest hair
        hair_flicks(c, cx - 1, top + 7, cx + 4, hip - 4, step=2)   # happy trail
        c.set(cx + 4, hip - 5, P["skin_sh"])                  # belly button
        c.rect(cx - 5, hip - 3, 12, 5, P["diaper"])           # diaper
        c.hline(cx - 5, cx + 6, hip + 1, P["diaper_sh"])
        c.vline(cx - 5, hip - 3, hip + 1, P["diaper_sh"])
        c.set(cx + 5, hip - 2, P["pin"])                      # safety pin
        c.set(cx + 6, hip - 2, P["pin"])
        return Anchors(neck=(cx + 1, top), shoulder=(cx - 1, top + 3), top=top, bottom=hip)


HEAD = [
    "...SSSSS....",
    "..SSSSSSwS..",
    ".SSSSSSSSSS.",
    ".HSSSSSSSSS.",
    ".HHSSSbbbbS.",
    ".HHSSSSSESS.",
    ".HHSSSSSSSSN",
    ".HHHSSSSSSS.",
    ".HHHHBBBBBRP",
    "..HHBBBBBBRP",
    "..HBBBBBBBB.",
    "...BBBBBBB..",
    "....BBBBB...",
]


class HairyHead(Head):
    """Bald on top, a fringe at the back, unibrow, huge beard, pacifier."""
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.rect(nx - 1, ny - 2, 3, 3, P["skin"])
        key = {
            "S": P["skin"], "w": P["shine"], "H": P["hair"], "b": P["hair"], "B": P["hair"],
            "E": P["skin_sh"] if pose.blink else INK, "N": P["skin"],
            "R": P["paci_ring"], "P": P["paci"],
        }
        c.stamp(nx - 5, ny - 14, HEAD, key)
        c.set(nx + 1, ny - 4, P["hair_hi"])                  # a little beard texture
        c.set(nx - 1, ny - 3, P["hair_hi"])


class HairyArm(Arm):
    species = SPECIES
    reach = 9

    def draw_swing(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        dx = (2 if front else -2) * pose.swing
        c.line(sx, sy, sx + dx, sy + 7, skin, width=2)
        c.rect(sx + dx, sy + 8, 2, 2, skin)
        c.set(sx + dx // 2, sy + 3, P["hair"])

    def draw_limb(self, c: Canvas, sx: int, sy: int, hx: int, hy: int, pose: Pose, front: bool, mode: str) -> None:
        skin = P["skin"] if front else P["skin_sh"]
        ex, ey = elbow(sx, sy, hx, hy, 1.5)
        c.stroke(sx, sy, ex, ey, skin, 2)
        c.stroke(ex, ey, hx, hy, skin, 2)
        c.rect(hx, hy, 2, 2, skin)
        c.set(ex, ey, P["hair"])


def build() -> BodyPlan:
    arm = HairyArm()
    return BodyPlan(legs=HairyLegs(), torso=HairyTorso(), head=HairyHead(), front_arm=arm, back_arm=arm)


def frames() -> dict[str, list[Canvas]]:
    """Right-facing 48x48 frames for the states the mini-game uses."""
    plan = build()
    return {anim: [plan.render(p) for p in poses(anim)] for anim in ("idle", "run", "jump")}
