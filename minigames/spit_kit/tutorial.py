"""Spit Kit's how-to pages."""

from __future__ import annotations

import math

import pygame

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, blit_c, caption, loop

SPIT = (196, 220, 150)
FACE = (240, 190, 150)
INK = (20, 12, 28)


def make() -> Tutorial:
    from .game import BASE_COLS, JAR_SIDE, draw_arrow, draw_helix, draw_jar, rgb

    floor = DEMO_H - 4

    # 1. spit in the jar
    def spit(s: pygame.Surface, t: float):
        t = loop(t, 2.4) * 2.4
        draw_jar(s, 160, floor, 0.25 + (0.15 if t > 1.2 else 0), t, scale=2)
        # a face in profile, leaning in
        lean = 4 * math.sin(min(1.0, t / 0.8) * math.pi / 2)
        fx, fy = 48 + lean, 34
        pygame.draw.circle(s, INK, (fx, fy), 17)
        pygame.draw.circle(s, FACE, (fx, fy), 16)
        pygame.draw.rect(s, (90, 60, 40), (fx - 17, fy - 17, 22, 9))                    # hair
        pygame.draw.rect(s, INK, (fx + 6, fy - 5, 3, 3))                                # eye
        cheeks = t > 0.5 and t < 0.9
        pygame.draw.circle(s, (230, 140, 130), (fx + 6, fy + 7), 5 if cheeks else 3)    # puffed cheeks
        pygame.draw.ellipse(s, INK, (fx + 12, fy + 4, 6, 4 if t > 0.9 else 2))         # mouth
        if 0.9 < t < 1.25:                                                               # the gob, on its way
            k = (t - 0.9) / 0.35
            gx = fx + 18 + (160 - fx - 18) * k
            gy = fy + 6 - 30 * math.sin(k * math.pi) + 50 * k * k
            pygame.draw.circle(s, SPIT, (round(gx), round(gy)), 3)
        if 1.2 < t < 1.8:
            caption(s, "SPLAT!", 160, 6, "#ffe14d")
        # the real jar's next to the cabinet: point that way
        nudge = round(3 * math.sin(t * 8))
        if JAR_SIDE > 0:
            draw_arrow(s, DEMO_W - 22 + nudge, 48, 1)
        else:
            draw_arrow(s, 22 - nudge, 48, -1)
        return 0, 0, 1.2 < t < 1.45

    # 2. the mainframe reads it
    def read(s: pygame.Surface, t: float):
        draw_helix(s, 50, 6, DEMO_H - 6, t, speed=5, radius=14)
        bars = [("DOM", 40), ("BANANA", 30), ("GENIUS", 20), ("TECH BRO", 10)]
        for i, (name, pct) in enumerate(bars):
            k = max(0.0, min(1.0, (loop(t, 4.5) * 4.5 - i * 0.6) / 0.6))
            y = 14 + i * 22
            caption(s, f"{round(pct * k)}% {name}", 150, y - 8)
            pygame.draw.rect(s, (60, 52, 84), (96, y, 110, 5))
            pygame.draw.rect(s, rgb(BASE_COLS["ATCG"[i]]), (96, y, round(110 * pct / 40 * k), 5))
        return 0, 0, False

    # 3. meet the new you
    def you(s: pygame.Surface, t: float):
        t = loop(t, 3.0) * 3.0
        cols = [(230, 80, 140), (255, 225, 77), (120, 200, 255)]
        k = min(1.0, t / 1.4)
        for i, c in enumerate(cols):
            a = i / 3 * math.tau + k * k * 10
            r = 60 * (1 - k)
            x, y = DEMO_W / 2 + math.cos(a) * r, 50 + math.sin(a) * r * 0.5
            if k < 1:
                pygame.draw.rect(s, INK, (x - 7, y - 13, 14, 26))
                pygame.draw.rect(s, c, (x - 6, y - 12, 12, 24))
        if 1.4 <= t < 1.55:
            s.fill((255, 255, 255))
        elif t >= 1.55:
            x, y = DEMO_W / 2, 50
            for (dy, h), c in zip(((-24, 14), (-10, 20), (10, 14)), cols):          # stitched together
                pygame.draw.rect(s, INK, (x - 9, y + dy - 1, 18, h + 2))
                pygame.draw.rect(s, c, (x - 8, y + dy, 16, h))
            for sx in range(-7, 8, 3):
                pygame.draw.rect(s, (240, 240, 224), (x + sx, y - 11, 1, 2))
                pygame.draw.rect(s, (240, 240, 224), (x + sx, y + 9, 1, 2))
            caption(s, "IT'S YOU!", x, 82, "#ffe14d")
        return 0, 0, False

    return Tutorial(
        title="SPIT KIT",
        premise="YOU ARE WHAT YOU SPIT.",
        pages=[
            Page(("SPIT IN THE JAR NEXT TO THE CABINET.", "ONE GOOD GOB. WE'LL WAIT.",
                  "PLEASE DO NOT TOUCH THE JAR."), spit, ("jar",), time=7.0),
            Page(("THE MAINFRAME READS YOUR DNA", "AND FINDS OUT WHAT YOU'RE MADE OF."), read, ("jar",), time=7.0),
            Page(("THEN SPLICES THE REAL YOU TOGETHER.", "NO REFUNDS."), you, ("button",), time=6.0),
        ],
        accent="#c4dc96",
    )
