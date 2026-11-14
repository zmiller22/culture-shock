"""Stork Bomber's how-to-play pages."""

from __future__ import annotations

import math

import pygame

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, along, blit_c, caption, loop
from . import art

FLOOR = DEMO_H - 6                 # the ground line inside the demo
FALL_G = 200                       # px/s^2 for the demo's baby (gentler than the real thing, so you can follow it)


def make(a, need: int, babies: int) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""
    from .game import CARRY, FLOOR_Y, STORK_ACCEL, STORK_DRAG, STORK_MAX

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

    # the lap the stick icon acts out on the flying page
    loop_pts = [(50, 52), (190, 52), (190, 30), (50, 30)]

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

    # -- try it --------------------------------------------------------------------------
    class Flight:
        """The stork on the stick, with the game's own feel, kept inside the box."""
        cheer = "NICE FLYING!"

        def __init__(self) -> None:
            self.x, self.y, self.vx, self.vy = 60.0, 40.0, 0.0, 0.0
            self.flown = 0.0
            self.done = False
            self.t = 0.0

        @property
        def facing(self) -> int:
            return 1 if self.vx >= 0 else -1

        def fly(self, dt: float, inp) -> None:
            self.t += dt
            self.vx += inp.x * STORK_ACCEL * dt - self.vx * STORK_DRAG * dt
            self.vy += inp.y * STORK_ACCEL * dt - self.vy * STORK_DRAG * dt
            speed = math.hypot(self.vx, self.vy)
            if speed > STORK_MAX:
                self.vx, self.vy = self.vx * STORK_MAX / speed, self.vy * STORK_MAX / speed
            x, y = self.x + self.vx * dt, self.y + self.vy * dt
            self.x, self.y = max(24, min(DEMO_W - 24, x)), max(20, min(56, y))
            if self.x != x:
                self.vx = 0.0
            if self.y != y:
                self.vy = 0.0
            if inp.x or inp.y:
                self.flown += speed * dt

        def update(self, dt: float, inp) -> None:
            self.fly(dt, inp)
            self.done = self.flown > 180

        def draw(self, s: pygame.Surface, t: float):
            sky(s, t)
            target(s, 170, "walk0" if int(t * 4) % 2 else "walk1")
            stork(s, self.x, self.y, self.facing, True, t)
            _, _, dx, dy = along(t, loop_pts, 70)            # the icons show a lap until they have a go
            return dx, dy, False

    class Delivery(Flight):
        """Fly about with the stick; the button drops the baby, which keeps the stork's speed.
        Land one in the target walking up and down."""
        cheer = "SPECIAL DELIVERY!"

        def __init__(self) -> None:
            super().__init__()
            self.baby: list[float] | None = None              # x, y, vx, vy while one's falling
            self.reload = 0.0                                 # s until the stork has another
            self.tx, self.tdir = 150.0, -1
            self.miss = 0.0                                   # s left on WAAH!
            self.hit: float | None = None

        def update(self, dt: float, inp) -> None:
            self.fly(dt, inp)
            self.tx += self.tdir * 18 * dt
            if not 40 < self.tx < DEMO_W - 40:
                self.tdir = -self.tdir
                self.tx = max(40, min(DEMO_W - 40, self.tx))
            self.reload = max(0.0, self.reload - dt)
            self.miss = max(0.0, self.miss - dt)
            if self.hit is not None:
                self.hit += dt
                self.done = self.hit > 0.6
                return
            if inp.action and not self.baby and self.reload == 0:
                bx = self.x + self.facing * (art.BUNDLE_AT[0] - art.STORK_CENTER[0])
                self.baby = [bx, self.y + art.BUNDLE_AT[1] - art.STORK_CENTER[1], self.vx * CARRY, self.vy * CARRY * 0.5]
            if self.baby:
                b = self.baby
                b[3] += FALL_G * dt
                b[0] += b[2] * dt
                b[1] += b[3] * dt
                hole = FLOOR - art.TARGET_FEET + art.TARGET_HOLE
                if b[1] >= hole and abs(b[0] - self.tx) <= art.GRAB_REACH:
                    self.baby, self.hit = None, 0.0
                elif b[1] >= FLOOR - 4 or not -10 < b[0] < DEMO_W + 10:
                    self.baby, self.reload, self.miss = None, 0.6, 1.0

        def draw(self, s: pygame.Surface, t: float):
            sky(s, t)
            if self.hit is not None:
                target(s, self.tx, "chew0" if int(t * 6) % 2 else "chew1")
            else:
                near = self.baby and self.baby[1] > 40 and abs(self.baby[0] - self.tx) < 30
                target(s, self.tx, "open" if near else ("walk0" if int(t * 6) % 2 else "walk1"), self.tdir)
            if self.baby:
                bx, by = self.baby[0], self.baby[1]
                w = max(4, 14 - int((FLOOR - by) / 10))
                pygame.draw.ellipse(s, (60, 50, 80), (round(bx) - w // 2, FLOOR + 1, w, 3))
                blit_c(s, a.baby[int(t * 6) % 2], bx, by)
            if self.miss:
                caption(s, "WAAH! TRY AGAIN", DEMO_W / 2, 6, "#f0d27a")
            stork(s, self.x, self.y, self.facing, not self.baby and self.reload == 0 and self.hit is None, t)
            return 1 if loop(t, 2.0) < 0.5 else 0, 0, 0.5 <= loop(t, 2.0) < 0.62

    return Tutorial(
        "STORK BOMBER", "",
        [
            Page(("MOVE THE STICK TO FLY THE STORK",), trial=Flight),
            Page(("PRESS THE BUTTON TO DROP THE BABY. IT KEEPS", "YOUR SPEED, SO LET GO EARLY. HIT THE TARGET!"),
                 controls=("stick", "button"), trial=Delivery),
            Page((f"DELIVER {need} OF {babies} TO WIN. OUTFLY THE", "SPAGHETTI MONSTER OR IT STEALS THE BABY"),
                 chase),
        ],
        intro="OUTSIDE MATERIALS INDICATE STORKS ARE INVOLVED IN CONCEPTION. YOU ARE THE STORK.",
    )
