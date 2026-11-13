"""Womb Rave's how-to-play pages, starring whichever dancer was just picked."""

from __future__ import annotations

import math
from typing import Callable

import pygame

from sprites.canvas import mix
from sprites.rig import GROUND, SIZE

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, blit_c, caption, loop
from . import art
from .art import F, MEM_RX, MEM_RY, SAC_RX, SAC_RY

CX, CY = DEMO_W // 2, 50           # the sac's middle, in the demo
TRAVEL = 0.9                       # s a thing takes to reach the membrane
HOP = 9
STICK = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}
RECEPTOR = {"L": (CX - MEM_RX, CY), "R": (CX + MEM_RX, CY), "U": (CX, CY - MEM_RY), "D": (CX, CY + MEM_RY)}
START = {"L": (-8, CY), "R": (DEMO_W + 8, CY), "U": (CX, -10), "D": (CX, DEMO_H + 10)}
MOVE = {"L": "walk", "R": "walk", "U": "jump", "D": "crouch", "B": "attack", "miss": "hurt"}


def rgb(c: str) -> tuple[int, int, int]:
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def make(a, frame: Callable[[str, int, int], pygame.Surface]) -> Tutorial:
    """`a` is the game's Art; `frame(anim, i, facing)` gets the picked dancer's frames."""

    def stage(s: pygame.Surface, t: float) -> None:
        s.fill(rgb(F["deep"]))
        pulse = (1 - (t * 2) % 1) ** 3                # the heartbeat, 120 BPM
        for i in range(5, 0, -1):
            r = i * 20 + pulse * 4 + (t * 10) % 20
            col = mix(F["deep"], F["pink"], 0.12 + 0.05 * (i % 2))
            pygame.draw.ellipse(s, rgb(col), (CX - r * 1.6, CY - r * 0.9, r * 3.2, r * 1.8), 2)
        s.blit(a.sac, (CX - SAC_RX - 1, CY - SAC_RY - 1))

    def note_img(lane: str, t: float) -> pygame.Surface:
        if lane in "LR":
            return a.egg[int(t * 8) % 4]
        if lane == "U":
            return a.snack[2]
        return pygame.transform.rotate(a.sperm[int(t * 10) % 3], 90)

    def dancer(s: pygame.Surface, t: float, move: tuple[str, float] | None) -> None:
        img, height, nudge = None, 0.0, 0
        if move:
            lane, dt = move
            anim = MOVE[lane]
            if dt < 0.35:
                k = dt / 0.35
                if anim == "walk":
                    nudge = 5 * STICK[lane][0]
                    img = frame("walk", int(dt * 16) % 4, STICK[lane][0])
                elif anim == "jump":
                    height = math.sin(k * math.pi) * HOP
                    img = frame("jump", 1 if k < 0.4 else 2 if k < 0.6 else 3, 1)
                elif anim == "crouch":
                    img = frame("crouch", 0 if dt < 0.06 else 1, 1)
                elif anim == "attack":
                    img = frame("attack", int(dt * 12), 1)
                else:
                    img = frame("hurt", int(dt * 10), 1)
        if img is None:
            img = frame("idle", int(t * 4) % 4, 1)
        y = CY + 15 - height
        s.blit(img, (round(CX + nudge) - SIZE // 2, round(y) - GROUND - 1))
        s.blit(a.rim, (CX - SAC_RX - 1, CY - SAC_RY - 1))

    def receptors(s: pygame.Surface, lit: set[str]) -> None:
        for lane, (rx, ry) in RECEPTOR.items():
            s.blit(a.receptor[(lane, "flash" if lane in lit else "idle")], (rx - 5, ry - 5))

    def run_notes(s: pygame.Surface, t: float, notes: list[tuple[float, str, bool]]):
        """notes: (time it reaches the membrane, lane, hit?). Draws them and returns
        (lit receptors, the dancer's latest move, stick x, stick y, judge text, judge time)."""
        lit, move, sx, sy, judge = set(), None, 0, 0, None
        for at, lane, hit in notes:
            k = (t - (at - TRAVEL)) / TRAVEL
            if 0 <= k < 1:
                (x0, y0), (x1, y1) = START[lane], RECEPTOR[lane]
                blit_c(s, note_img(lane, t), x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)
            elif 1 <= k and not hit and t - at < 0.4:          # sails on through
                (x0, y0), (x1, y1) = START[lane], RECEPTOR[lane]
                img = note_img(lane, t).copy()
                img.set_alpha(120)
                blit_c(s, img, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)
            dt = t - at
            if 0 <= dt:
                if hit:
                    if dt < 0.15:
                        lit.add(lane)
                    if dt < 0.25:
                        sx, sy = sx + STICK[lane][0], sy + STICK[lane][1]
                    if dt < 0.4:
                        rx, ry = RECEPTOR[lane]
                        s.blit(a.burst[lane][min(3, int(dt / 0.1))], (rx - 10, ry - 10))
                    move = (lane, dt)
                    judge = ("PERFECT!", "#ffe14d", dt)
                else:
                    move = ("miss", dt) if dt < 0.3 else move
                    judge = ("MISS", "#ff4a6a", dt)
        return lit, move, sx, sy, judge

    def show_judge(s: pygame.Surface, judge) -> None:
        if judge and judge[2] < 0.6:
            caption(s, judge[0], CX, 4 - judge[2] * 4 + 4, judge[1])

    # 1. hit the direction as it touches the bubble
    seq = [(0.9 + i, lane, True) for i, lane in enumerate("LURD")]

    def lanes(s: pygame.Surface, t: float):
        t = loop(t, 4.0) * 4.0
        stage(s, t)
        lit, move, sx, sy, judge = run_notes(s, t, seq + [(at + 4, ln, h) for at, ln, h in seq] +
                                             [(at - 4, ln, h) for at, ln, h in seq])
        receptors(s, lit)
        dancer(s, t, move)
        show_judge(s, judge)
        return sx, sy, False

    # 2. the vitals: misses drain them, hits fill them
    vit = [(0.9, "L", False), (1.7, "R", True), (2.5, "U", True), (3.3, "D", True)]
    LIFE = [60, 34, 46, 58, 70]

    def vitals(s: pygame.Surface, t: float):
        t = loop(t, 4.2) * 4.2
        stage(s, t)
        lit, move, sx, sy, judge = run_notes(s, t, vit)
        receptors(s, lit)
        dancer(s, t, move)
        show_judge(s, judge)
        n = sum(t >= at for at, _, _ in vit)
        life = LIFE[n]
        s.blit(a.heart, (4, 4))
        pygame.draw.rect(s, (40, 30, 60), (15, 5, 62, 6))
        col = "#ffffff" if n == 1 and int(t * 8) % 2 else "#ff4a6a"
        pygame.draw.rect(s, rgb(col), (16, 6, round(60 * life / 100), 4))
        caption(s, "VITALS", 30, 13)
        return sx, sy, False

    return Tutorial(
        "WOMB RAVE", "LIFE IS A NINE MONTH PARTY IN A VERY SMALL CLUB.",
        [
            Page(("PUSH THE STICK THAT WAY JUST AS", "EACH THING TOUCHES YOUR BUBBLE"), lanes, time=6.0),
            Page(("MISSES DRAIN YOUR VITALS. LAST THE", "WHOLE SONG AND YOU GET BORN!"), vitals),
        ],
        accent=F["hi"],
    )
