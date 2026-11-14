"""Build-A-Bear's how-to-play pages. Each one looks through a window onto the real
lab, and the try-it pages run on the game's own floor, speeds and reach, so what
works here works in the round.

    1. Grab a toy part (done when you pick it up).
    2. Carry it to the slab and press the button (done at the slab).
    3. The sewing screen: move the part round the body, button sews (done when sewn).
    4. Watch out (a show-me): the toy train and the chattering teeth knock you flat.
    5. Beat the storm (a show-me): when the clock runs out, so does the lightning.
    6. All five on? Throw the switch (done when you pull it, and the round starts).
"""

from __future__ import annotations

import math

import pygame

from sprites.rig import GROUND, SIZE

from ..primordial_soup import art as soup_art
from ..shell import Input
from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, caption, loop
from . import art

INK = "#140c1c"
YELLOW, PINK, CYAN, ORANGE, GREEN = "#ffe14d", "#ff7a9a", "#5ff3ff", "#ff9a3a", "#d4ff7a"
BODY = {"HEAD": ("head", "teddy"), "LEFT ARM": ("arm", "doll"), "RIGHT ARM": ("arm", "teddy"),
        "LEFT LEG": ("leg", "bunny"), "RIGHT LEG": ("leg", "teddy")}
FLOOR_VIEW = (40, 64)            # game x, y at the box's top-left, for the floor pages
SWITCH_VIEW = (82, 0)            # ...and for the switch page


def make(a) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""
    from .game import (CARRY_MAX, DEPTH, DOC_MAX, GRAB_R, GRIP, LEVER_REACH, LEVER_SPOT, NAV, PULL_T,
                       SLAB_BACK, SLAB_L, SLAB_R, SLAB_REACH, SLOTS, STORM_TIME, blocked_at, draw_body)

    # -- drawing helpers ------------------------------------------------------------------
    def shout(s: pygame.Surface, text: str, x: float, y: float, col: str) -> None:
        caption(s, text, x + 1, y + 1, INK)
        caption(s, text, x, y, col)

    def ring(s: pygame.Surface, x: float, y: float, t: float, col: str, label: str = "", r: int = 12) -> None:
        """A callout: a pulsing ring, and a label over it."""
        rr = r + round(math.sin(t * 8) * 1.5)
        x, y = round(x), round(y)
        pygame.draw.circle(s, (20, 12, 28), (x + 1, y + 1), rr, 2)
        pygame.draw.circle(s, col, (x, y), rr, 2)
        if label:
            shout(s, label, min(DEMO_W - 30, max(30, x)), y - rr - 8, col)

    def box(s: pygame.Surface, rect: tuple, t: float, col: str, label: str = "") -> None:
        """A callout for something wide: a pulsing box."""
        x, y, w, h = rect
        g = round(math.sin(t * 8) * 1.5)
        pygame.draw.rect(s, (20, 12, 28), (x - g + 1, y - g + 1, w + 2 * g, h + 2 * g), 2)
        pygame.draw.rect(s, col, (x - g, y - g, w + 2 * g, h + 2 * g), 2)
        if label:
            shout(s, label, min(DEMO_W - 30, max(30, x + w / 2)), y - g - 9, col)

    def view(s: pygame.Surface, at: tuple[int, int]) -> None:
        s.blit(a.lab, (-at[0], -at[1]))

    def shadow(s: pygame.Surface, x: float, y: float, w: int) -> None:
        pygame.draw.ellipse(s, (16, 10, 30), (round(x) - w // 2, round(y), w, 3))

    def doc(s: pygame.Surface, x: float, y: float, name: str, f: int, facing: int, held=None) -> None:
        """The scientist, feet at (x, y) in the box."""
        shadow(s, x, y, 16)
        s.blit(a.doc[name][f][facing], (round(x) - SIZE // 2, round(y) - GROUND))
        if held:
            px, py = a.carry_pts[name][f] if name in a.carry_pts else (SIZE // 2 + 10, 20)
            if facing < 0:
                px = SIZE - 1 - px
            img = a.parts[held][0]
            s.blit(img, (round(x) - SIZE // 2 + px - img.get_width() // 2, round(y) - GROUND + py - img.get_height() + 3))

    def part(s: pygame.Surface, kind_fam: tuple, x: float, y: float, z: float = 0.0, flip: int = 0) -> None:
        img = a.parts[kind_fam][flip]
        shadow(s, x, y, img.get_width() - 2)
        s.blit(img, (round(x - img.get_width() / 2), round(y - z - img.get_height()) + 1))

    def stars(s: pygame.Surface, x: float, y: float, t: float) -> None:
        for k in (0, 2.1, 4.2):
            s.blit(a.star, (round(x + 9 * math.cos(t * 7 + k)) - 2, round(y - 48 + 2 * math.sin(t * 7 + k))))

    def coils(s: pygame.Surface, at: tuple[int, int], q: int = 0) -> None:
        for x, y in art.COILS:
            s.blit(a.coil[q], (x - soup_art.TESLA_W // 2 - at[0], y - soup_art.TESLA_H + 2 - at[1]))

    def coil_top(x: int, y: int, at: tuple[int, int]) -> tuple[int, int]:
        return (x - soup_art.TESLA_W // 2 + soup_art.TESLA_TOP[0] - at[0],
                y - soup_art.TESLA_H + 2 + soup_art.TESLA_TOP[1] - at[1])

    def slab(s: pygame.Surface, at: tuple[int, int], body: dict) -> tuple[float, float]:
        """The slab with the toy so far on it. Returns the toy's middle, in the box."""
        sx, sy = SLAB_L - 1 - at[0], art.SLAB_FRONT - a.slab.get_height() + 1 - at[1]
        s.blit(a.slab, (sx, sy))
        _, lying, _ = a.creature(body)
        cx, cy = art.SLAB_X - at[0], sy + 1 + art.SLAB_DEPTH / 2
        s.blit(lying, (round(cx - lying.get_width() / 2), round(cy - lying.get_height() / 2)))
        s.blit(a.straps, (sx, sy))
        return cx, cy

    # -- try it: walk the real floor ------------------------------------------------------
    class Walk:
        """The scientist loose on a window of the lab floor, with the game's speeds and grip.
        Coordinates are the game's; `at` is where the window starts."""
        cheer = "NICE!"
        at = FLOOR_VIEW
        start = (80.0, 140.0)

        def __init__(self) -> None:
            self.x, self.y = self.start
            self.vx = self.vy = 0.0
            self.facing = 1
            self.anim = 0.0
            self.held: tuple | None = None
            self.done = False

        def blocked(self, x: float, y: float) -> bool:
            ax, ay = self.at
            return blocked_at(x, y) or not (ax + 12 <= x <= ax + DEMO_W - 12 and y <= ay + DEMO_H - 3)

        def walk(self, dt: float, inp: Input) -> None:
            self.anim += dt
            ix, iy = inp.x, inp.y * DEPTH
            n = math.hypot(inp.x, inp.y)
            if n > 1:
                ix, iy = ix / n, iy / n
            top = CARRY_MAX if self.held else DOC_MAX
            k = min(1.0, GRIP * dt)
            self.vx += (ix * top - self.vx) * k
            self.vy += (iy * top - self.vy) * k
            if not self.blocked(self.x + self.vx * dt, self.y):
                self.x += self.vx * dt
            if not self.blocked(self.x, self.y + self.vy * dt):
                self.y += self.vy * dt
            if inp.x:
                self.facing = inp.x

        def draw_doc(self, s: pygame.Surface) -> None:
            moving = math.hypot(self.vx, self.vy) > 12
            if self.held:
                name, f = ("carry_run", int(self.anim * 12) % 4) if moving else ("carry_idle", int(self.anim * 4) % 4)
            else:
                name, f = ("run", int(self.anim * 12) % 4) if moving else ("idle", int(self.anim * 4) % 4)
            doc(s, self.x - self.at[0], self.y - self.at[1], name, f, self.facing, self.held)

        def toward(self, x: float, y: float, k: float) -> tuple[int, int, bool]:
            """What the stick icon hints: head for (x, y), the button once there."""
            dx, dy = x - self.x, y - self.y
            sx = (dx > 4) - (dx < -4)
            sy = (dy > 4) - (dy < -4)
            return sx, sy, False

    class Grab(Walk):
        """A doll head on the floor; walk up to it and press the button."""
        cheer = "GOT IT!"
        thing = ("head", "doll")
        spot = (220.0, 132.0)

        def update(self, dt: float, inp: Input) -> None:
            self.walk(dt, inp)
            if inp.action:
                hx = self.x + self.facing * 10
                px, py = self.spot
                if min(math.hypot(px - hx, (py - self.y) * 1.4), math.hypot(px - self.x, (py - self.y) * 1.4)) < GRAB_R:
                    self.held = self.thing
                    self.done = True

        def draw(self, s: pygame.Surface, t: float):
            view(s, self.at)
            px, py = self.spot[0] - self.at[0], self.spot[1] - self.at[1]
            items = [(self.y, lambda: self.draw_doc(s))]
            if not self.held:
                items.append((self.spot[1], lambda: part(s, self.thing, px, py)))
            for _, fn in sorted(items, key=lambda it: it[0]):
                fn()
            if not self.held:
                ring(s, px, py - 7, t, YELLOW, "DOLL HEAD")
            sx, sy, _ = self.toward(self.spot[0] - 12, self.spot[1], t)
            near = not (sx or sy)
            return [(sx, sy, False), (0, 0, near and int(t * 3) % 2 == 0)]

    class Carry(Walk):
        """Carrying a part; take it to the slab and press the button."""
        cheer = "SEWING TIME!"
        start = (250.0, 150.0)

        def __init__(self) -> None:
            super().__init__()
            self.held = ("arm", "teddy")
            self.facing = -1

        def at_slab(self) -> bool:
            dx = max(SLAB_L - self.x, 0, self.x - SLAB_R)
            dy = max(SLAB_BACK - self.y, 0, self.y - art.SLAB_FRONT)
            return dx <= SLAB_REACH and dy <= SLAB_REACH

        def update(self, dt: float, inp: Input) -> None:
            self.walk(dt, inp)
            if inp.action and self.at_slab():
                self.done = True

        def draw(self, s: pygame.Surface, t: float):
            view(s, self.at)
            body = {k: v for k, v in BODY.items() if k not in ("RIGHT ARM", "HEAD")}
            items = [(art.COILS[0][1], lambda: coils(s, self.at)), (art.SLAB_FRONT, lambda: slab(s, self.at, body)),
                     (self.y + 0.1, lambda: self.draw_doc(s))]
            for _, fn in sorted(items, key=lambda it: it[0]):
                fn()
            if not self.done:
                x0, y0 = SLAB_L - self.at[0], art.SLAB_FRONT - a.slab.get_height() + 1 - self.at[1]
                box(s, (x0, y0, art.SLAB_W, art.SLAB_DEPTH + art.SLAB_FACE + 2), t,
                    YELLOW if self.at_slab() else CYAN, "PRESS BUTTON HERE" if self.at_slab() else "THE SLAB")
            sx, sy, _ = self.toward(art.SLAB_X + 20, art.SLAB_FRONT + 6, t)
            return [(sx, sy, False), (0, 0, self.at_slab() and int(t * 3) % 2 == 0)]

    class Sew:
        """The sewing screen, small: the stick moves the teddy arm round the body,
        the button sews it on."""
        cheer = "STITCH STITCH!"
        held = ("arm", "teddy")

        def __init__(self) -> None:
            self.sel = "LEFT LEG"
            self.prev = (0, 0)
            self.body = {k: v for k, v in BODY.items() if k not in ("RIGHT ARM", "HEAD")}
            self.done = False
            self.moved = False

        def update(self, dt: float, inp: Input) -> None:
            stick = (inp.x, inp.y)
            if stick != (0, 0) and stick != self.prev:
                moves = [(inp.x, 0)] if inp.x and inp.x != self.prev[0] else []
                moves += [(0, inp.y)] if inp.y else []
                moves += [(inp.x, 0)] if inp.x and not moves else []
                for move in moves:
                    if move in NAV[self.sel]:
                        self.sel = NAV[self.sel][move]
                        self.moved = True
                        break
            self.prev = stick
            if inp.action and self.sel in SLOTS:
                self.body[self.sel] = self.held
                self.done = True

        def draw(self, s: pygame.Surface, t: float):
            s.fill((16, 12, 30))
            pygame.draw.rect(s, (40, 32, 70), (36, 2, 70, 100))
            ox, oy = 45, 14
            draw_body(s, a, ox, oy, 1, self.body, None if self.done else self.held, self.sel, t)
            img = a.upright(*self.held)
            s.blit(pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2)), (122, 12))
            caption(s, "TEDDY ARM", 186, 16)
            if not self.done:
                caption(s, "GOES ON THE", 186, 30, "#8a7ac8")
                caption(s, self.sel, 186, 38, GREEN)
                ex, ey = art.SLOT_AT["RIGHT ARM"]                             # point at an empty slot
                if self.sel != "RIGHT ARM":
                    ring(s, ox + ex + 2, oy + ey + 9, t, YELLOW, "EMPTY", r=10)
            hint = (0, -1, False) if self.sel in ("LEFT LEG", "RIGHT LEG") else (1, 0, False) \
                if self.sel == "LEFT ARM" else (0, 0, False)
            return [hint, (0, 0, self.sel == "RIGHT ARM" and int(t * 3) % 2 == 0)]

    class Switch(Walk):
        """The toy's finished; walk to the knife switch and haul on it."""
        cheer = "IT'S ALIVE!"
        at = SWITCH_VIEW
        start = (236.0, 84.0)

        def __init__(self) -> None:
            super().__init__()
            self.pull = 0.0
            self.done_t: float | None = None

        def at_lever(self) -> bool:
            return abs(self.x - LEVER_SPOT[0]) <= LEVER_REACH[0] and self.y - LEVER_SPOT[1] <= LEVER_REACH[1]

        def update(self, dt: float, inp: Input) -> None:
            if self.pull > 0:
                self.pull = max(0.0, self.pull - dt)
                if self.pull <= PULL_T / 2:
                    self.done = True
                return
            self.walk(dt, inp)
            if inp.action and self.at_lever():
                self.pull = PULL_T
                self.facing = 1

        def draw(self, s: pygame.Surface, t: float):
            view(s, self.at)
            if self.done and self.done_t is None:
                self.done_t = t
            live = self.done_t is not None
            coils(s, self.at, 2 if live and int(t * 12) % 2 else 0)
            cx, cy = slab(s, self.at, BODY)
            px, py = art.LEVER_PIVOT[0] - self.at[0], art.LEVER_PIVOT[1] - self.at[1]
            k = len(a.blades) - 1 if live else round((1 - self.pull / PULL_T) * 2) if self.pull else 0
            s.blit(a.blades[k], (px - art.BLADE_BOX // 2, py - art.BLADE_BOX // 2))
            if self.pull > 0 or live:
                f = 2 if live else min(3, int((PULL_T - self.pull) / PULL_T * 4))
                doc(s, self.x - self.at[0], self.y - self.at[1], "interact", f, self.facing)
            else:
                self.draw_doc(s)
            if live:                                                       # both coils let rip
                u = t - self.done_t
                for i, coil in enumerate(art.COILS):
                    bx, by = coil_top(*coil, self.at)
                    if int(u * 20 + i) % 2:
                        pts = [(bx, by)] + [(bx + (cx - bx) * q / 4 + (4 if q % 2 else -4), by + (cy - by) * q / 4)
                                            for q in range(1, 4)] + [(cx, cy)]
                        pygame.draw.lines(s, (255, 255, 255), False, pts, 1)
                shout(s, "ZZZAP!", cx, 6, CYAN)
            else:
                ring(s, px, py - 10, t, YELLOW, "THE SWITCH", r=14)
            sx, sy, _ = self.toward(LEVER_SPOT[0] - 4, LEVER_SPOT[1] + 2, t)
            return [(sx, sy, False), (0, 0, self.at_lever() and int(t * 3) % 2 == 0)]

    # -- show me: the toys knock you flat --------------------------------------------------
    SPAN = 6.4

    def toys(s: pygame.Surface, t: float):
        t = loop(t, SPAN) * SPAN
        view(s, FLOOR_VIEW)
        ox, oy = FLOOR_VIEW
        held = ("leg", "monkey")
        if t < 3.2:                                                        # the train
            ty = art.TRACK[1] + art.TRACK[3] - oy                          # the bottom of the loop
            hit = 1.3
            tx = 30 + 110 * t
            dx = 150
            for i, kind in enumerate(("engine", "wagon0", "wagon1")):
                img = a.cars[kind][1]
                x = tx - i * 17
                s.blit(img, (round(x) - 9, round(ty) - 13 - (int(t * 10) % 2 if i == 0 else 0)))
            if t < hit:
                doc(s, dx, ty, "carry_idle", int(t * 4) % 4, 1, held)
                ring(s, tx, ty - 6, t, ORANGE, "TOY TRAIN")
            else:
                u = t - hit
                k = min(1.0, u / 0.35)
                doc(s, dx + 22 * k, ty - 14 * k, "hurt", int(t * 10) % 2, -1)
                if u < 1.6:
                    stars(s, dx + 22 * k, ty - 14 * k, t)
                fk = min(1.0, u / 0.5)                                     # the part goes flying
                part(s, held, dx + 10 + 40 * fk, ty - 18 * fk, 28 * math.sin(fk * math.pi))
                if u < 1.4:
                    shout(s, "CHOO CHOO!", dx, 8, ORANGE)
                if u > 0.5:
                    shout(s, "YOU DROP IT!", dx + 50, ty - 50, PINK)
        else:                                                              # the teeth
            u = t - 3.2
            hit = 1.6
            dx, dy = 110, 72
            cx = 210 - min(u, hit) * 48
            f = int(u * 14) % 2 + 2 * (int(u * 5) % 2)
            s.blit(a.chomper[f][-1], (round(cx) - 8, dy - 14 - (int(u * 6) % 2)))
            if u < hit:
                doc(s, dx, dy, "idle", int(u * 4) % 4, 1)
                ring(s, cx, dy - 7, u, PINK, "CHATTER TEETH", r=10)
                if int(u * 6) % 2:
                    shout(s, "!", cx, dy - 26, PINK)
            else:
                k = min(1.0, (u - hit) / 0.35)
                doc(s, dx - 20 * k, dy + 6 * k, "hurt", int(u * 10) % 2, 1)
                stars(s, dx - 20 * k, dy + 6 * k, t)
                shout(s, "CHOMP!", cx, 8, PINK)
        return [(0, 0, False), (0, 0, False)]

    # -- show me: the storm is the clock ---------------------------------------------------
    STORM_SPAN = 5.0

    def storm(s: pygame.Surface, t: float):
        t = loop(t, STORM_SPAN) * STORM_SPAN
        at = (10, 0)
        view(s, at)
        secs = max(0, 3 - int(t))
        calm = t >= 3.0
        for wx, wy, ww, wh in art.WINDOWS:
            x, y = wx - at[0], wy - at[1]
            if x > DEMO_W:
                continue
            if calm:
                s.fill((40, 52, 110), (x, y - 1, ww, wh + 1))
                pygame.draw.circle(s, (244, 240, 210), (x + ww - 9, y + 7), 5)
            else:
                flash = int(t * 5) % 3 == 0
                s.fill((150, 160, 220) if flash else (20, 26, 58), (x, y - 1, ww, wh + 1))
                if flash:
                    pygame.draw.lines(s, (255, 255, 255), False, [(x + 12, y - 1), (x + 16, y + 10), (x + 11, y + 18),
                                                                  (x + 14, y + wh)], 1)
                for k in range(8):
                    rx = x + (k * 7 + int(t * 40)) % ww
                    ry = y + (k * 13 + int(t * 160)) % wh
                    pygame.draw.line(s, (90, 110, 170), (rx, ry), (rx - 1, ry + 3))
            pygame.draw.line(s, (30, 24, 40), (x + ww // 2, y), (x + ww // 2, y + wh - 1))
        clock = pygame.Surface((96, 16))                                    # the HUD's storm clock, blown up
        clock.fill((20, 15, 38))
        col = "#ff5f5f" if secs <= 3 and int(t * 4) % 2 else CYAN
        s.blit(clock, (DEMO_W // 2 - 48, 70))
        from .game import big_text
        txt = big_text(f"STORM {secs:02d}", col)
        s.blit(txt, (DEMO_W // 2 - txt.get_width() // 2, 73))
        box(s, (DEMO_W // 2 - 48, 70, 96, 16), t, YELLOW, "" if calm else f"{round(STORM_TIME)}S OF LIGHTNING")
        if calm:
            shout(s, "NO LIGHTNING, NO LIFE.", DEMO_W // 2, 92, PINK)
        return [(0, 0, False)]

    return Tutorial(
        "BUILD-A-BEAR", "",
        [
            Page(("STICK TO MOVE. BUTTON TO GRAB A PART.",), controls=("stick", "button"), trial=Grab),
            Page(("WALK TO THE SLAB. BUTTON TO SEW.",), controls=("stick", "button"), trial=Carry),
            Page(("STICK PICKS THE SPOT. BUTTON SEWS IT ON.",), controls=("stick", "button"), trial=Sew),
            Page(("DODGE THE TRAIN AND THE TEETH.",), toys, ("stick", "button"), time=SPAN),
            Page(("FINISH BEFORE THE STORM ENDS.",), storm, ("button",), time=STORM_SPAN),
            Page(("ALL 5 ON? BUTTON AT THE SWITCH.",), controls=("stick", "button"), trial=Switch),
        ],
        accent=GREEN,
        intro="SPARKS WILL FLY",
    )
