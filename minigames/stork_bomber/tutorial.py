"""Stork Bomber's how-to-play pages."""

from __future__ import annotations

import math

import pygame

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, along, blit_c, caption, loop, sign
from . import art

FLOOR = DEMO_H - 6                 # the ground line inside the demo
FALL_G = 200                       # px/s^2 for the demo's baby (gentler than the real thing, so you can follow it)


def make(a, need: int, babies: int) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""
    from .game import FLOOR_Y

    def sky(s: pygame.Surface, t: float) -> None:
        s.blit(a.backdrop, (-40, FLOOR - FLOOR_Y))
        for i, cloud in enumerate(a.clouds[:2]):
            s.blit(cloud, (round((i * 130 + t * 6) % (DEMO_W + 80)) - 80, 6 + i * 20))

    def stork(s: pygame.Surface, x: float, y: float, facing: int, carrying: bool, t: float) -> None:
        frame = int(t * 10) % 4
        img = a.stork[carrying][frame][facing]
        s.blit(img, (round(x) - art.STORK_CENTER[0], round(y) - art.STORK_CENTER[1] + (0, -1, 0, 1)[frame]))

    def target(s: pygame.Surface, x: float, pose: str, facing: int = 1) -> None:
        s.blit(a.target[pose][facing], (round(x) - art.TARGET_W // 2, FLOOR - art.TARGET_FEET))

    # 1. fly around
    loop_pts = [(50, 52), (190, 52), (190, 30), (50, 30)]

    def fly(s: pygame.Surface, t: float):
        sky(s, t)
        x, y, dx, dy = along(t, loop_pts, 70)
        target(s, 150, "walk0" if int(t * 4) % 2 else "walk1")
        stork(s, x, y, -1 if dx < 0 else 1, True, t)
        return dx, dy, False

    # 2. drop the baby, leading the target
    DROP, SPEED, TSPEED = 0.9, 60, 18
    hole = FLOOR - art.TARGET_FEET + art.TARGET_HOLE
    bdx, bdy = art.BUNDLE_AT[0] - art.STORK_CENTER[0], art.BUNDLE_AT[1] - art.STORK_CENTER[1]
    sy = 26
    fall_t = math.sqrt(2 * (hole - (sy + bdy)) / FALL_G)
    bvx = SPEED * 0.75
    land_x = 20 + SPEED * DROP + bdx + bvx * fall_t
    land_t = DROP + fall_t
    tx0 = land_x - TSPEED * land_t                    # so the target walks under it right on time

    def drop(s: pygame.Surface, t: float):
        t = loop(t, 3.6) * 3.6
        sky(s, t)
        x = 20 + SPEED * t
        tx = tx0 + TSPEED * min(t, land_t)
        dropped = t >= DROP
        if t < land_t:
            near = dropped and land_t - t < 0.35
            target(s, tx, "open" if near else ("walk0" if int(t * 6) % 2 else "walk1"))
        elif t < land_t + 0.8:
            target(s, tx, "chew0" if int(t * 6) % 2 else "chew1")
        else:
            target(s, tx, "happy")
            caption(s, "SPECIAL DELIVERY!", tx, 8 + 4 * max(0.0, land_t + 1.2 - t), "#ffe14d")
            blit_c(s, a.heart, tx + 3 * math.sin(t * 9), hole - 20 - (t - land_t - 0.8) * 20)
        if dropped and t < land_t:
            u = t - DROP
            bx = 20 + SPEED * DROP + bdx + bvx * u
            by = sy + bdy + FALL_G * u * u / 2
            w = max(4, 14 - int((FLOOR - by) / 10))
            pygame.draw.ellipse(s, (60, 50, 80), (round(bx) - w // 2, FLOOR + 1, w, 3))
            blit_c(s, a.baby[int(t * 6) % 2], bx, by)
        stork(s, x, sy, 1, not dropped, t)
        return 1, 0, DROP <= t < DROP + 0.25

    # 3. outfly the Flying Spaghetti Monster
    chase_pts = [(30, 30), (110, 60), (200, 26), (130, 20)]

    def chase(s: pygame.Surface, t: float):
        sky(s, t)
        target(s, 40, "walk0" if int(t * 4) % 2 else "walk1", -1)
        x, y, dx, dy = along(t, chase_pts, 80)
        mx, my, _, _ = along(max(0.0, t - 1.1), chase_pts, 80)
        if t < 1.1:
            mx, my = -30 + t * 40, 70
        img = a.fsm[int(t * 8) % art.FSM_FRAMES][1 if x >= mx else -1]
        blit_c(s, img, mx, my + 3 * math.sin(t * 5))
        stork(s, x, y, -1 if dx < 0 else 1, True, t)
        if int(t * 3) % 2:
            caption(s, "GIMME!", mx, my - 30, "#f0d27a")
        return dx, dy, False

    return Tutorial(
        "STORK BOMBER", "BABIES ARRIVE BY AIR. YOU ARE THE AIR.",
        [
            Page(("FLY THE STORK WITH THE STICK",), fly),
            Page(("BUTTON DROPS THE BABY. IT KEEPS YOUR SPEED", "SO LET GO EARLY AND LAND IT IN THE TARGET"),
                 drop, ("stick", "button"), time=7.2),
            Page((f"DELIVER {need} OF {babies} TO WIN. OUTFLY THE", "SPAGHETTI MONSTER OR IT STEALS THE BABY"),
                 chase),
        ],
    )
