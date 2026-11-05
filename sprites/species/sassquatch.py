"""Sassquatch: a Sasquatch with a big pink bow, lashes and lipstick. Same knuckles."""

from ..canvas import Canvas
from ..palette import INK, SASQUATCH as F, SASSQUATCH as P
from ..rig import BodyPlan, Head, Pose
from .sasquatch import GENES as SQUATCH_GENES, HEAD as SQUATCH_HEAD

SPECIES = "sassquatch"
PREFIX, SUFFIX = "Sass", "sass"

# The Sasquatch head with lashes flicking off the brow and lipstick on the mouth.
HEAD = list(SQUATCH_HEAD)
HEAD[4] = ".FFFFFFFFFL."
HEAD[5] = "FFFFFFbbbbbL"
HEAD[10] = ".FFFFFcRRRc."

BOW = [
    "Pp...pP",
    "PhPkPhP",
    "PPpkpPP",
    "Pp...pP",
]


class SassquatchHead(Head):
    species = SPECIES

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        key = {
            "f": F["fur_hi"], "F": F["fur"], "d": F["fur_dk"], "b": F["fur_xdk"],
            "c": F["face"], "n": F["face_sh"], "R": P["lips"], "L": INK,
            "w": F["face_sh"] if pose.blink else F["eye"], "E": F["face_sh"] if pose.blink else INK,
        }
        c.stamp(nx - 6, ny - 11, HEAD, key)
        c.stamp(nx - 4, ny - 13, BOW, {"P": P["bow"], "p": P["bow_sh"], "h": P["bow_hi"], "k": P["bow_sh"]})


# Only the head is new; the rest of her is pure Sasquatch.
GENES = dict(head=SassquatchHead())


def build() -> BodyPlan:
    g = SQUATCH_GENES
    return BodyPlan(legs=g["legs"], torso=g["torso"], head=GENES["head"], front_arm=g["arm"], back_arm=g["arm"])
