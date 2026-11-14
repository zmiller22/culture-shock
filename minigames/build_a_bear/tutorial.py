"""Build-A-Bear's how-to pages: grab a part, put it on the slab, throw the switch."""

from __future__ import annotations

import math

import pygame

from sprites.palette import LAB_DIM
from sprites.rig import GROUND, SIZE

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, caption, loop
from . import art

FLOOR = DEMO_H - 10              # feet row in the demo box
DEMO_BODY = {"HEAD": ("head", "teddy"), "LEFT ARM": ("arm", "doll"), "RIGHT ARM": ("arm", "teddy"),
             "LEFT LEG": ("leg", "bunny"), "RIGHT LEG": ("leg", "teddy")}


def make(a) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""

    def floor(s: pygame.Surface) -> None:
        s.blit(a.lab, (-40, -(art.FLOOR_TOP + 40)))

    def doc(s: pygame.Surface, x: float, name: str, f: int, facing: int, held=None) -> None:
        pygame.draw.ellipse(s, (16, 10, 30), (round(x) - 8, FLOOR, 16, 3))
        s.blit(a.doc[name][f][facing], (round(x) - SIZE // 2, FLOOR - GROUND))
        if held:
            px, py = a.carry_pts[name][f]
            if facing < 0:
                px = SIZE - 1 - px
            img = a.parts[held][0]
            s.blit(img, (round(x) - SIZE // 2 + px - img.get_width() // 2, FLOOR - GROUND + py - img.get_height() + 3))

    # 1. pick a part up
    def grab(s: pygame.Surface, t: float):
        floor(s)
        t = loop(t, 4.0) * 4.0
        part = ("head", "doll")
        if t < 1.4:
            x = 40 + 90 * t / 1.4
            doc(s, x, "run", int(t * 12) % 4, 1)
            held, stick, btn = None, (1, 0), False
        elif t < 1.8:
            doc(s, 130, "idle", 0, 1)
            held, stick, btn = None, (0, 0), 1.5 < t < 1.7
        else:
            k = min(1.0, (t - 1.8) / 1.4)
            doc(s, 130 - 80 * k, "carry_run" if k < 1 else "carry_idle", int(t * 12) % 4, -1, part)
            held, stick, btn = part, (-1 if k < 1 else 0, 0), False
            if t < 2.6:
                caption(s, "GOT IT!", 130, 20)
        if not held:
            img = a.parts[part][0]
            jig = 1 if int(t * 30) % 2 and t % 2 > 1.6 else 0
            s.blit(img, (142 - img.get_width() // 2 + jig, FLOOR - img.get_height() + 1))
        return [(stick[0], stick[1], False), (0, 0, btn)]

    # 2. the sewing screen: move the part round the body, button sews it on
    from .game import draw_body
    held = ("arm", "teddy")
    path = ["HEAD", "LEFT ARM", "RIGHT ARM"]                    # where the part hovers, in turn

    def sew(s: pygame.Surface, t: float):
        s.fill((16, 12, 30))
        t = loop(t, 5.0) * 5.0
        pygame.draw.rect(s, (40, 32, 70), (34, 4, 70, 96))
        step = min(len(path) - 1, int(t / 1.0))
        sewn = t > 3.4
        body = {k: v for k, v in DEMO_BODY.items() if k not in ("RIGHT ARM", "HEAD")}
        if sewn:
            body["RIGHT ARM"] = held
        draw_body(s, a, 43, 14, 1, body, None if sewn else held, path[step], t)
        img = a.upright(*held)
        s.blit(pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2)), (126, 14))
        caption(s, "TEDDY ARM", 186, 18)
        if sewn:
            caption(s, "STITCH STITCH!", 170, 52, "#d4ff7a")
        else:
            caption(s, "GOES ON THE", 186, 32, LAB_DIM)
            caption(s, path[step], 186, 40, "#d4ff7a")
        moving = 0.7 < t % 1.0 < 0.95 and t < 2.0
        stick = (0, 1) if moving and step == 0 else (1, 0) if moving else (0, 0)
        return [(stick[0], stick[1], False), (0, 0, 3.0 < t < 3.35)]

    # 3. throw the switch
    standing, lying, foot = a.creature(DEMO_BODY)

    def switch(s: pygame.Surface, t: float):
        floor(s)
        t = loop(t, 5.0) * 5.0
        sx = 20
        sy = FLOOR - a.slab.get_height() - 6
        s.blit(a.slab, (sx, sy))
        cx, cy = sx + a.slab.get_width() // 2, sy + 1 + art.SLAB_DEPTH // 2
        down = min(1.0, max(0.0, (t - 0.6) / 0.3))
        k = round(down * (len(a.blades) - 1))
        pygame.draw.rect(s, (62, 62, 82), (180, 8, 30, 46))
        pygame.draw.rect(s, (200, 120, 58), (190, 18, 9, 3))
        s.blit(a.blades[k], (195 - art.BLADE_BOX // 2, 44 - art.BLADE_BOX // 2))
        doc(s, 196, "interact" if 0.4 < t < 1.0 else "cheer" if t > 3.2 else "idle",
            min(3, int((t - 0.4) * 6)) if 0.4 < t < 1.0 else int(t * 5) % 2, -1)
        if t < 2.6:
            jx = (1 if int(t * 20) % 2 else -1) if 1.0 < t < 2.4 else 0
            s.blit(lying, (cx - lying.get_width() // 2 + jx, cy - lying.get_height() // 2))
            s.blit(a.straps, (sx, sy))
            if 1.0 < t < 2.4:
                for i in range(2):
                    bx = cx + (-30 if i else 30)
                    pts = [(bx, 2)] + [(bx + (cx - bx) * q / 4 + (5 if q % 2 else -5), 2 + (cy - 2) * q / 4)
                                       for q in range(1, 4)] + [(cx, cy)]
                    pygame.draw.lines(s, (255, 255, 255) if int(t * 20) % 2 else (95, 243, 255), False, pts, 1)
                caption(s, "ZZZAP!", cx, 6, "#5ff3ff")
        else:
            s.blit(standing, (cx - art.MW // 2, FLOOR - foot + (int(t * 4) % 2)))
            if t > 3.0:
                caption(s, "HUG ME!", cx, 4, "#d4ff7a")
        return 0, 0, 0.5 < t < 0.8

    return Tutorial(
        title="BUILD-A-BEAR",
        premise="LIFE IS STUFFING, STITCHES AND A LOT OF VOLTS.",
        pages=[
            Page(("GRAB TOY PARTS OFF THE FLOOR.", "BUTTON PICKS UP. BUTTON AGAIN DROPS."), grab,
                 ("stick", "button"), time=6.0),
            Page(("TAKE THEM TO THE SLAB AND PRESS BUTTON.", "MOVE THE PART ROUND THE BODY. BUTTON SEWS."), sew,
                 ("stick", "button"), time=7.0),
            Page(("HEAD, TWO ARMS, TWO LEGS ON?", "THROW THE SWITCH!"), switch, ("button",), time=6.0),
        ],
        accent="#d4ff7a",
    )
