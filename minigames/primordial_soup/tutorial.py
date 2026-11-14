"""Primordial Soup's how-to-play pages."""

from __future__ import annotations

import math
import random

import pygame

from sprites.rig import GROUND, SIZE
from sprites.viewer import text_surface

from ..tutorial import DEMO_H, DEMO_W, Page, Tutorial, along, blit_c, caption, loop, sign
from . import art

OX, OY = -41, -48                  # the demo shows the kitchen around the pot (game x, y + this = demo x, y)
POT = (119, 74)                    # pot's feet, in the demo
X0, X1, Y0, Y1 = 12, DEMO_W - 12, 54, DEMO_H - 4       # where the chef's feet can go in the box
CRAWL = 16                         # px/s the try-it critter wanders (slower than the real ones, so anyone can catch it)
REACH = 4                          # px of extra grab reach (across and in depth), so a near miss still counts
RANGE = 16                         # px of extra throwing range
INK = "#140c1c"


def inked(text: str, color: str) -> pygame.Surface:
    """Text with a dark rim, so it reads over the counter and the pot too."""
    img, rim = text_surface(text, color), text_surface(text, INK)
    out = pygame.Surface((img.get_width() + 2, img.get_height() + 2), pygame.SRCALPHA)
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(rim, (dx, dy))
    out.blit(img, (1, 1))
    return out


def make(a, need: int, time_limit: float) -> Tutorial:
    """`a` is the game's Art (pre-rendered surfaces)."""
    from .game import (AIM_RANGE, CARRY_MAX, CHEF_GRIP, CHEF_MAX, CRIT_STUN, DEPTH, FEET_R, GRAB_DEPTH,
                       GRAB_LINES, GRAB_REACH, GRAVITY, HAND_Z, LUNGE_SPEED, LUNGE_T, MISS_LINES, PERSONALITY,
                       POT_FOOT, POT_RIM_Z, SOUP_LINES, SQUEAL_LINES, THROW_SPEED, THROW_T, THROW_UP, Critter)

    foot = (POT_FOOT[0] + OX, POT_FOOT[1] + OY, POT_FOOT[2], POT_FOOT[3])

    def kitchen(s: pygame.Surface) -> None:
        s.blit(a.kitchen, (OX, OY))

    def shadow(s: pygame.Surface, x: float, y: float, w: int) -> None:
        pygame.draw.ellipse(s, (16, 10, 30), (round(x) - w // 2, round(y), w, 3))

    def pot(s: pygame.Surface, t: float, level: int = 0) -> None:
        px, py = POT[0] - art.POT_RIM[0], POT[1] - art.POT_FEET
        s.blit(a.pot_back[level][int(t * 8) % 4], (px, py))
        s.blit(a.pot_front[int(t * 8) % 3], (px, py))

    whole = a.pot_back[0][0].copy()                # the pot's silhouette, for the highlight
    whole.blit(a.pot_front[0], (0, 0))
    rim = pygame.mask.from_surface(whole).outline()

    def glow(s: pygame.Surface, t: float) -> None:
        """A pulsing outline round the pot and an arrow bobbing over it: go here."""
        px, py = POT[0] - art.POT_RIM[0], POT[1] - art.POT_FEET
        color = (255, 225, 77) if int(t * 4) % 2 else (240, 160, 40)
        for ox, oy in rim:
            s.set_at((px + ox, py + oy), color)
        bob = round(2 * math.sin(t * 6))
        ax, ay = POT[0], py - 4 + bob
        pygame.draw.polygon(s, INK, [(ax - 5, ay - 5), (ax + 5, ay - 5), (ax, ay + 1)])
        pygame.draw.polygon(s, color, [(ax - 4, ay - 5), (ax + 4, ay - 5), (ax, ay)])

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

    def draw_sorted(s: pygame.Surface, items: list) -> None:
        for _, fn in sorted(items, key=lambda it: it[0]):
            fn()

    def blocked(x: float, y: float, r: float = FEET_R) -> bool:
        """Off the floor in the box, or in the pot (the same shape the game uses)."""
        if not (X0 <= x <= X1 and Y0 <= y <= Y1):
            return True
        cx, cy, rx, ry = foot
        return ((x - cx) / (rx + r)) ** 2 + ((y - cy) / (ry + 3)) ** 2 <= 1

    def over_pot(x: float, y: float) -> bool:
        cx, cy, rx, ry = foot
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.15

    def at_pot(x: float, y: float) -> bool:
        """Feet right up against the pot (he can't walk into it, so this is as close as he gets)."""
        cx, cy, rx, ry = foot
        return ((x - cx) / (rx + FEET_R + 8)) ** 2 + ((y - cy) / (ry + 9)) ** 2 <= 1

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

    # -- try it --------------------------------------------------------------------------
    class Run:
        """The chef on the stick, with the game's own feel, kept inside the box and out of the pot."""
        cheer = "YES CHEF!"

        def __init__(self) -> None:
            self.x, self.y, self.vx, self.vy = 40.0, 90.0, 0.0, 0.0
            self.facing = 1
            self.lunge = self.throw = 0.0                 # s left on the pounce / the throw
            self.held: str | None = None                  # the kind he's carrying
            self.ran = 0.0
            self.said: list[list] = []                    # popups: [image, x, y, age]
            self.done = False
            self.t = 0.0

        def run(self, dt: float, inp) -> None:
            self.t += dt
            self.lunge = max(0.0, self.lunge - dt)
            self.throw = max(0.0, self.throw - dt)
            for line in self.said:
                line[3] += dt
            self.said = [line for line in self.said if line[3] < 1.0]
            if self.lunge <= 0:
                ix, iy = inp.x, inp.y * DEPTH
                n = math.hypot(inp.x, inp.y)
                if n > 1:                                 # diagonals aren't faster
                    ix, iy = ix / n, iy / n
                top = CARRY_MAX if self.held else CHEF_MAX
                k = min(1.0, CHEF_GRIP * dt)
                self.vx += (ix * top - self.vx) * k
                self.vy += (iy * top - self.vy) * k
            else:
                self.vx -= self.vx * 4 * dt
                self.vy -= self.vy * 4 * dt
            if blocked(self.x + self.vx * dt, self.y):    # slide along whatever's in the way
                self.vx = 0.0
            self.x += self.vx * dt
            if blocked(self.x, self.y + self.vy * dt):
                self.vy = 0.0
            self.y += self.vy * dt
            if inp.x and self.lunge <= 0:
                self.facing = inp.x
            if inp.x or inp.y:
                self.ran += math.hypot(self.vx, self.vy) * dt

        def update(self, dt: float, inp) -> None:
            self.run(dt, inp)
            self.done = at_pot(self.x, self.y)

        def say(self, text: str, x: float, y: float, color: str = "#f4f4f4") -> None:
            self.said.append([inked(text, color), x, y, 0.0])

        def pose(self) -> tuple[str, int]:
            moving = math.hypot(self.vx, self.vy) > 12
            if self.held:
                return ("carry_run", int(self.t * 12) % 4) if moving else ("carry_idle", int(self.t * 4) % 4)
            if self.lunge > 0:
                return "attack", min(3, int((LUNGE_T - self.lunge) / LUNGE_T * 4))
            if self.throw > 0:
                return "attack", 1 + min(2, int((THROW_T - self.throw) / THROW_T * 3))
            return ("run", int(self.t * 12) % 4) if moving else ("idle", int(self.t * 4) % 4)

        def draw_chef(self, s: pygame.Surface) -> None:
            name, f = self.pose()
            chef(s, self.x, self.y, name, f, self.facing, self.held, self.t)

        def draw_said(self, s: pygame.Surface) -> None:
            for img, x, y, age in self.said:
                half = img.get_width() / 2 + 2
                blit_c(s, img, max(half, min(DEMO_W - half, x)), max(4, y - age * 10))

        def draw(self, s: pygame.Surface, t: float):
            kitchen(s)
            draw_sorted(s, [(POT[1], lambda: (pot(s, t), glow(s, t))), (self.y, lambda: self.draw_chef(s))])
            self.draw_said(s)
            # the icons steer toward the pot until they have a go
            return sign(POT[0] - self.x, 4), sign(POT[1] - 3 - self.y, 2), False

    class Hunt(Run):
        """Run about with one slow critter: the button pounces on it, and once it's in hand the
        button throws it. Near the pot it goes in; too far and it lands dazed, to be caught again."""
        kind = "legfish"
        soup_hud = False

        def __init__(self) -> None:
            super().__init__()
            self.rng = random.Random()
            self.c = Critter(self.kind, 170.0, 88.0, speed=CRAWL, facing=-1, hop=PERSONALITY[self.kind][1])
            self.c.goal = self.c.x, self.c.y
            self.flight = 0.0                             # s an aimed throw takes to reach the soup
            self.soup: float | None = None                # s since it landed in the soup
            self.won: float | None = None                 # s since they managed it

        def update(self, dt: float, inp) -> None:
            self.run(dt, inp)
            self.critter(dt)
            if self.soup is not None:
                self.soup += dt
            if self.won is not None:
                self.won += dt
                self.done = self.won > 0.8
                return
            if inp.action and self.lunge <= 0 and self.throw <= 0:
                if self.held:
                    self.toss(inp)
                else:
                    self.lunge = LUNGE_T
                    self.vx = self.facing * LUNGE_SPEED
                    self.vy = inp.y * LUNGE_SPEED * 0.4
            if self.lunge > 0 and not self.held:
                c, hx = self.c, self.x + self.facing * 10
                if c.state in ("roam", "stun") and abs(c.x - hx) < GRAB_REACH + REACH \
                        and abs(c.y - self.y) < GRAB_DEPTH + REACH:
                    c.state, c.t, c.z = "held", 0.0, 0.0
                    self.held = c.kind
                    self.lunge = min(self.lunge, 0.08)
                    self.say(self.rng.choice(GRAB_LINES), self.x, self.y - 52)
                    self.say(self.rng.choice(SQUEAL_LINES.get(c.kind, ["EEK!"])), self.x, self.y - 62, "#5ff3ff")
                    self.caught()
                elif self.lunge <= dt:
                    self.say(self.rng.choice(MISS_LINES), self.x, self.y - 52, "#a89cc8")

        def caught(self) -> None:
            pass

        def toss(self, inp) -> None:
            """The game's throw, but he turns to the pot by himself, and from a bit further off."""
            c, self.held = self.c, None
            self.throw = THROW_T
            near = self.near
            if near:
                self.facing = 1 if POT[0] >= self.x else -1
            hx = self.x + self.facing * 10
            c.x, c.y, c.z, c.state, c.t, c.facing = hx, self.y, HAND_Z, "air", 0.0, self.facing
            if near:
                dx, dy = POT[0] - hx, POT[1] - 3 - self.y
                t = max(0.35, min(0.8, math.hypot(dx, dy) / THROW_SPEED))
                c.vx, c.vy = dx / t, dy / t
                c.vz = (POT_RIM_Z + 4 - HAND_Z + 0.5 * GRAVITY * t * t) / t
                c.aim, self.flight = True, t
            else:
                c.vx = self.facing * THROW_SPEED + self.vx * 0.4
                c.vy = inp.y * 60 + self.vy * 0.4
                c.vz, c.aim = THROW_UP, False

        @property
        def near(self) -> bool:
            """Close enough to the pot that a throw goes in."""
            return math.hypot(POT[0] - self.x, (POT[1] - 3 - self.y) * 1.5) <= AIM_RANGE + RANGE

        def critter(self, dt: float) -> None:
            c = self.c
            c.t += dt
            if c.state == "air":
                c.vz -= GRAVITY * dt
                c.z += c.vz * dt
                nx, ny = c.x + c.vx * dt, max(Y0, min(Y1, c.y + c.vy * dt))
                if (c.aim and c.t >= self.flight) or (over_pot(nx, ny) and c.vz < 0 and c.z <= POT_RIM_Z + 4):
                    self.into_soup()
                    return
                if over_pot(nx, ny) and c.z < POT_RIM_Z:  # hit the side of the pot
                    c.vx, c.vy = -c.vx * 0.4, -c.vy * 0.4
                    self.say("CLANG!", c.x, c.y - 30, "#a89cc8")
                elif not X0 <= nx <= X1:                  # off the wall of the box
                    c.vx = -c.vx * 0.4
                else:
                    c.x, c.y = nx, ny
                if c.z <= 0:
                    c.z, c.state, c.t, c.vx, c.vy = 0.0, "stun", 0.0, 0.0, 0.0
                    if blocked(c.x, c.y, 4):
                        c.x, c.y = self.spot()
                    self.say("TOO FAR! GET CLOSER", DEMO_W / 2, 24, "#f0d27a")
            elif c.state == "stun":
                if c.t >= CRIT_STUN:
                    c.state, c.t = "roam", 0.0
            elif c.state == "roam":                       # wander about, in no hurry
                gx, gy = c.goal
                tx, ty = gx - c.x, gy - c.y
                d = math.hypot(tx, ty)
                if d < 4 or c.t > 4:
                    c.goal, c.t = self.spot(), 0.0
                    return
                c.vx, c.vy = tx / d * c.speed, ty / d * c.speed * DEPTH
                if not blocked(c.x + c.vx * dt, c.y + c.vy * dt, 4):
                    c.x, c.y = c.x + c.vx * dt, c.y + c.vy * dt
                else:
                    c.goal = self.spot()
                if abs(c.vx) > 2:
                    c.facing = 1 if c.vx > 0 else -1
                c.z = abs(math.sin(c.t * 7)) * 5 if c.hop else 0.0

        def spot(self) -> tuple[float, float]:
            """Somewhere free on the floor, a little way from the chef."""
            for _ in range(100):
                x, y = self.rng.uniform(24, DEMO_W - 24), self.rng.uniform(62, Y1 - 2)
                if not blocked(x, y, 8) and math.hypot(x - self.x, y - self.y) > 40:
                    return x, y
            return 200.0, 90.0

        def into_soup(self) -> None:
            self.c.state, self.soup, self.won = "soup", 0.0, 0.0
            self.say(self.rng.choice(SOUP_LINES), POT[0], POT[1] - 58, art.GOO_HI)

        def draw_crit(self, s: pygame.Surface) -> None:
            c = self.c
            if c.state == "air":
                f = 2 + int(c.t * 12) % 2
            elif c.state == "roam":
                f = int(c.t * 10) % 2
            else:
                f = 0
            if not over_pot(c.x, c.y):
                shadow(s, c.x, c.y, 10)
            s.blit(a.crit[c.kind][f][c.facing], (round(c.x) - art.CRIT_W // 2, round(c.y - c.z) - art.CRIT_FEET))
            if c.state == "stun":
                spin = self.t * 8
                for k in (0, math.pi):
                    s.blit(a.stars, (round(c.x + 7 * math.cos(spin + k)) - 3, round(c.y - 18 + 2 * math.sin(spin + k))))

        def draw(self, s: pygame.Surface, t: float):
            kitchen(s)
            c = self.c
            items = [(POT[1], lambda: pot(s, t, 1 if self.soup is not None else 0)),
                     (self.y, lambda: self.draw_chef(s))]
            if c.state in ("roam", "stun"):
                items.append((c.y, lambda: self.draw_crit(s)))
            draw_sorted(s, items)
            if c.state == "air":                          # on top of everything, so it's seen going in
                self.draw_crit(s)
            if self.soup is not None:                     # splash
                u = self.soup
                rx, ry = POT[0], POT[1] - art.POT_FEET + art.POT_RIM[1]
                for i in range(6):
                    ang = math.pi + i * math.pi / 5
                    blit_c(s, a.bits["soup"], rx + math.cos(ang) * 60 * u, ry + math.sin(ang) * 36 * u + 60 * u * u)
            if self.soup_hud:
                n = int(self.soup is not None)
                blit_c(s, inked(f"SOUP {n}/{need}", "#9dff5a" if n else "#f4f4f4"), 30, 7)
            self.draw_said(s)
            # the icons: head for the critter (or, with one in hand, the pot), then press the button
            if self.held:
                tx, ty = POT[0] - 50 if self.x < POT[0] else POT[0] + 50, POT[1] + 14
            else:
                tx, ty = c.x - 14 * (1 if c.x >= self.x else -1), c.y
            dx, dy = sign(tx - self.x, 6), sign(ty - self.y, 6)
            k = loop(t, 2.0)
            if not (dx or dy) or (self.held and self.near):                             # already there: just the button
                return 0, 0, k % 0.5 < 0.12
            return (dx, dy, False) if k < 0.6 else (0, 0, k < 0.72)

    class Pounce(Hunt):
        cheer = "GOT ONE!"

        def caught(self) -> None:
            self.won = 0.0

    class Toss(Hunt):
        """Starts with a critter in hand, a little way from the pot."""
        cheer = "SOUP'S ON!"
        kind = "jello"
        soup_hud = True

        def __init__(self) -> None:
            super().__init__()
            self.x, self.y = 24.0, 94.0
            self.c.state, self.held = "held", self.c.kind

    return Tutorial(
        "PRIMORDIAL SOUP", "LIFE STARTED IN A WARM BROTH. COOK SOME UP.",
        [
            Page(("MOVE THE STICK TO RUN AROUND", "WALK TO THE POT TO CONTINUE"), trial=Run),
            Page(("GET CLOSE AND PRESS THE BUTTON", "TO POUNCE ON A CRITTER"), controls=("stick", "button"),
                 trial=Pounce),
            Page(("PRESS THE BUTTON AGAIN NEAR THE POT", "TO THROW IT IN THE SOUP"), controls=("stick", "button"),
                 trial=Toss),
            Page((f"GET {need} IN THE SOUP IN {int(time_limit)} SECONDS.", "DODGE THE TOOLS FLYING OFF THE WALL!"),
                 dodge),
        ],
    )
