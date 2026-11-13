"""Primordial Soup's how-to-play pages."""

from __future__ import annotations

import math

import pygame

from sprites.rig import GROUND, SIZE

from ..tutorial import Page, Tutorial, along, blit_c, caption, loop
from . import art

OX, OY = -41, -48                  # the demo shows the kitchen around the pot
POT = (119, 74)                    # pot's feet, in the demo
RIM = (POT[0], POT[1] - art.POT_FEET + art.POT_RIM[1])


def make(a, need: int, time_limit: float) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""

    def kitchen(s: pygame.Surface) -> None:
        s.blit(a.kitchen, (OX, OY))

    def shadow(s: pygame.Surface, x: float, y: float, w: int) -> None:
        pygame.draw.ellipse(s, (16, 10, 30), (round(x) - w // 2, round(y), w, 3))

    def pot(s: pygame.Surface, t: float, level: int = 0) -> None:
        px, py = POT[0] - art.POT_RIM[0], POT[1] - art.POT_FEET
        s.blit(a.pot_back[level][int(t * 8) % 4], (px, py))
        s.blit(a.pot_front[int(t * 8) % 3], (px, py))

    def chef(s: pygame.Surface, x: float, y: float, name: str, f: int, facing: int, held: str | None = None,
             t: float = 0.0) -> None:
        shadow(s, x, y, 16)
        s.blit(a.chef[name][f][facing], (round(x) - SIZE // 2, round(y) - GROUND))
        if held:
            px, py = a.carry_pts[name][f]
            if facing < 0:
                px = SIZE - 1 - px
            img = a.crit[held][2 + int(t * 10) % 2][facing]
            s.blit(img, (round(x) - SIZE // 2 + px - art.CRIT_W // 2, round(y) - GROUND + py - art.CRIT_H // 2 - 1))

    def critter(s: pygame.Surface, kind: str, x: float, y: float, t: float, facing: int = 1, z: float = 0.0) -> None:
        shadow(s, x, y, 10)
        img = a.crit[kind][int(t * 10) % 2 if not z else 2 + int(t * 12) % 2][facing]
        s.blit(img, (round(x) - art.CRIT_W // 2, round(y - z) - art.CRIT_FEET))

    def draw_sorted(s: pygame.Surface, items: list) -> None:
        for _, fn in sorted(items, key=lambda it: it[0]):
            fn()

    # 1. run around
    ring = [(30, 98), (210, 98), (210, 60), (30, 60)]

    def run(s: pygame.Surface, t: float):
        kitchen(s)
        x, y, dx, dy = along(t, ring, 80)
        cx = 60 + 30 * math.sin(t * 1.3)
        draw_sorted(s, [
            (POT[1], lambda: pot(s, t)),
            (y, lambda: chef(s, x, y, "run", int(t * 12) % 4, -1 if dx < 0 else 1)),
            (88, lambda: critter(s, "eyeball", cx, 88, t, 1 if math.cos(t * 1.3) > 0 else -1)),
            (64, lambda: critter(s, "hotdog", 180 - 20 * math.sin(t), 66, t + 0.3)),
        ])
        return dx, dy, False

    # 2. pounce
    POUNCE, LUNGE = 1.2, 0.34

    def pounce(s: pygame.Surface, t: float):
        t = loop(t, 3.6) * 3.6
        kitchen(s)
        y = 94
        if t < POUNCE:
            x, name, f = 40 + 70 * t, "run", int(t * 12) % 4
        elif t < POUNCE + LUNGE:
            k = (t - POUNCE) / LUNGE
            x, name, f = 124 + 26 * k, "attack", min(3, int(k * 4))
        else:
            x, name, f = 150, "carry_idle", int(t * 4) % 4
        caught = t >= POUNCE + LUNGE          # in hand once the lunge ends: only carry poses have a hand spot
        items = [(POT[1], lambda: pot(s, t)),
                 (y, lambda: chef(s, x, y, name, f, 1, "legfish" if caught else None, t))]
        if not caught:
            items.append((y, lambda: critter(s, "legfish", 172 + 4 * math.sin(t * 6), y, t, -1)))
        draw_sorted(s, items)
        if caught and t < POUNCE + 1.6:
            caption(s, "GOTCHA!", x, y - 56, "#ffe14d")
            caption(s, "MY LEGS!", x + 34, y - 40)
        return (1 if t < POUNCE + LUNGE else 0), 0, POUNCE <= t < POUNCE + 0.2

    # 3. throw it in the pot
    THROW, FLIGHT = 1.1, 0.55
    stand = (78, 92)
    hand = (stand[0] + 6, stand[1] - 20)

    def throw(s: pygame.Surface, t: float):
        t = loop(t, 3.6) * 3.6
        kitchen(s)
        x, y, dx, dy = along(t, [(24, 100), stand], 60, closed=False)
        if t < THROW:
            name, f, held = ("carry_run", int(t * 12) % 4, "jello") if dx or dy else \
                ("carry_idle", int(t * 4) % 4, "jello")
        else:
            name, f, held = "attack", min(3, 1 + int((t - THROW) * 12)), None
        landed = t >= THROW + FLIGHT
        items = [(POT[1], lambda: pot(s, t, 1 if landed else 0)), (y, lambda: chef(s, x, y, name, f, 1, held, t))]
        draw_sorted(s, items)
        if THROW <= t < THROW + FLIGHT:                  # arcing over into the soup
            k = (t - THROW) / FLIGHT
            cx = hand[0] + (RIM[0] - hand[0]) * k
            cy = hand[1] + (RIM[1] - hand[1]) * k - 34 * math.sin(k * math.pi)
            img = a.crit["jello"][2 + int(t * 12) % 2][1]
            blit_c(s, img, cx, cy)
        elif landed and t < THROW + FLIGHT + 1.6:
            u = t - THROW - FLIGHT
            for i in range(6):                            # splash
                ang = math.pi + i * math.pi / 5
                blit_c(s, a.bits["soup"], RIM[0] + math.cos(ang) * 30 * u * 2,
                       RIM[1] + math.sin(ang) * 18 * u * 2 + 60 * u * u)
            caption(s, "SPLOOSH!", RIM[0], RIM[1] - 26 - 6 * u, "#9dff5a")
        caption(s, f"SOUP {int(landed)}/{need}", 30, 4, "#9dff5a" if landed else "#f4f4f4")
        return dx, dy, THROW <= t < THROW + 0.2

    # 4. the clock, and the haunted tool rack
    path = [(30, 88), (100, 88), (112, 100), (150, 100), (162, 88), (220, 88)]
    TOOL_AT, TOOL_FLY = 0.5, 1.0
    tool_from, tool_to = (190, -10), (130, 88)

    def dodge(s: pygame.Surface, t: float):
        t = loop(t, 3.8) * 3.8
        kitchen(s)
        x, y, dx, dy = along(t, path, 75, closed=False)
        moving = dx or dy
        items = [(POT[1], lambda: pot(s, t, 2)),
                 (y, lambda: chef(s, x, y, "run" if moving else "idle", int(t * (12 if moving else 4)) % 4, 1))]
        draw_sorted(s, items)
        k = (t - TOOL_AT) / TOOL_FLY
        img = a.tools["cleaver"]
        if k < 0:
            blit_c(s, img, tool_from[0] + (int(t * 30) % 2), tool_from[1] + 14)
        elif k < 1:
            img = pygame.transform.rotate(img, -int(k * 8) * 90)
            blit_c(s, img, tool_from[0] + (tool_to[0] - tool_from[0]) * k,
                   tool_from[1] + 14 + (tool_to[1] - 6 - tool_from[1] - 14) * k)
        else:
            blit_c(s, img, tool_to[0], tool_to[1] - 2)
            if k < 2.2:
                caption(s, "CLANG!", tool_to[0], tool_to[1] - 22, "#ffe14d")
                caption(s, "MISSED ME!", x, y - 56)
        secs = int(time_limit - (t * 5) % 30)
        caption(s, f"SOUP 2/{need}   TIME {secs:02d}", 52, 4, "#f4f4f4")
        return dx, dy, False

    return Tutorial(
        "PRIMORDIAL SOUP", "LIFE STARTED IN A WARM BROTH. COOK SOME UP.",
        [
            Page(("RUN AROUND THE KITCHEN WITH THE STICK",), run),
            Page(("GET CLOSE AND PRESS BUTTON", "TO POUNCE ON A CRITTER"), pounce, ("stick", "button"), time=5.4),
            Page(("PRESS BUTTON AGAIN NEAR THE POT", "TO THROW IT IN THE SOUP"), throw, ("stick", "button"), time=5.4),
            Page((f"GET {need} IN THE SOUP IN {int(time_limit)} SECONDS.", "DODGE THE TOOLS FLYING OFF THE WALL!"),
                 dodge),
        ],
    )
