"""Walk a level with any character (pygame-ce). Currently there is one level: the Court House.

    python -m sprites.play [--fullscreen] [--scale 4]

Controls are the viewer's:
    LEFT / RIGHT   walk (hold SHIFT to run)
    SPACE / Z      jump
    X              attack
    UP / DOWN      previous / next character
    M              splice a brand-new random Kronenberg
    R              start over (and un-dismiss the judge)
    ESC / Q        quit

The physics here are deliberately small: the floor under your feet comes from the
level's colliders, `Actor` (from the viewer) handles jumping and animation, and
the judge is a few lines of state machine. `World` has no pygame in it.
"""

from __future__ import annotations

import argparse
import math
import random

import pygame

from .bosses import spaghetti_judge as judge
from .characters import from_specimen, roster
from .levels import courthouse as L
from .palette import COURT as K, LAB_DIM, LAB_TEXT, SPAGHETTI_JUDGE
from .rig import GROUND, SIZE
from .species.kronenberg import random_specimen
from .viewer import JUMP_VELOCITY, Actor, Loaded, text_surface, to_surface
from .canvas import hex_to_rgba

VW, VH = L.VIEW
STEP = 6                  # px you can walk up without jumping
HALF = 5                  # half the player's width, for walls and ledges
BODY = 28                 # player height, for walls
JUDGE_SPEED = 45          # px/s
JUDGE_COOLDOWN = 1.6      # s between gavel slams
JUDGE_HITS = 6
SLIP_SPEED = 130          # px/s you skid forward after stepping on a banana peel


class Judge:
    """Hovers over the bench, drifts toward you, and slams the gavel when you're under it."""

    def __init__(self, home: tuple[int, int]):
        self.x, self.y = float(home[0]), float(home[1])
        self.state, self.t = "idle", 0.0
        self.facing = -1
        self.hp = JUDGE_HITS
        self.cooldown = 1.0
        self.struck = False                       # this slam already landed

    def _enter(self, state: str) -> None:
        self.state, self.t, self.struck = state, 0.0, False

    @property
    def frame(self) -> int:
        n = judge.ANIMATIONS[self.state]
        i = int(self.t * judge.FPS[self.state])
        return i % n if judge.LOOP[self.state] else min(i, n - 1)

    @property
    def gavel_x(self) -> float:
        ix = judge.IMPACT[0]
        return self.x + (ix if self.facing > 0 else judge.W - 1 - ix)

    @property
    def center(self) -> tuple[float, float]:
        return self.x + judge.W / 2, self.y + judge.CY

    def update(self, dt: float, px: float, active: bool) -> bool:
        """Returns True on the tick a gavel slam lands where the player is standing."""
        self.t += dt
        self.cooldown -= dt
        if self.state == "death":
            return False
        if self.state in ("attack", "hurt") and self.t * judge.FPS[self.state] >= judge.ANIMATIONS[self.state]:
            self._enter("idle")
        if self.state == "attack":
            if not self.struck and self.frame == 2:
                self.struck = True
                return abs(self.gavel_x - px) < 14
            return False
        if self.state == "hurt" or not active:
            return False
        self.facing = -1 if px < self.center[0] else 1
        target = px - (self.gavel_x - self.x)               # line the gavel up over the player
        lo, hi = 100 * L.TILE, (L.COLS - 1) * L.TILE - judge.W
        target = min(max(target, lo), hi)
        dx = target - self.x
        moving = abs(dx) > 2
        if moving:
            self.x += math.copysign(min(abs(dx), JUDGE_SPEED * dt), dx)
        if self.state != ("fly" if moving else "idle"):
            self._enter("fly" if moving else "idle")
        if self.cooldown <= 0 and abs(self.gavel_x - px) < 18:
            self._enter("attack")
            self.cooldown = JUDGE_COOLDOWN
        return False

    def hit(self) -> None:
        if self.state in ("hurt", "death"):
            return
        self.hp -= 1
        self._enter("death" if self.hp <= 0 else "hurt")


class World:
    """Player + level + judge. Call `step(dt, **inputs)` once per tick."""

    def __init__(self, info: dict):
        self.info = info
        self.colliders = info["colliders"]
        self.zones = info["zones"]
        self.restart()

    def restart(self) -> None:
        self.actor = Actor()
        self.x, self.feet = map(float, self.info["spawn"])
        self.checkpoint = tuple(self.info["spawn"])
        self.contempt = 0                         # times the court has had to hurt you
        self.slipping = False
        self.judge = Judge(tuple(self.info["boss"]["home"]))

    # -- level queries --------------------------------------------------------
    def floor(self, x: float, feet: float, grounded: bool) -> tuple[float, dict | None]:
        """Highest standable top at or below the feet (or a step above them, if grounded)."""
        best: tuple[float, dict | None] = (self.info["size"][1] + 400, None)    # nothing: fall forever
        reach = STEP if grounded else 0
        for r in self.colliders:
            if r["type"] in ("hazard", "water"):
                continue
            if r["x"] - HALF + 2 <= x <= r["x"] + r["w"] + HALF - 2 and feet - reach <= r["y"] < best[0]:
                best = (r["y"], r)
        return best

    def blocked(self, x: float, feet: float) -> bool:
        for r in self.colliders:
            if r["type"] not in ("solid", "conveyor"):
                continue
            if r["y"] < feet - STEP and r["y"] + r["h"] > feet - BODY and r["x"] < x + HALF and x - HALF < r["x"] + r["w"]:
                return True
        return not HALF <= x <= self.info["size"][0] - HALF

    def touching(self, kind: str, x: float, feet: float) -> dict | None:
        for r in self.colliders:
            if r["type"] == kind and r["x"] <= x <= r["x"] + r["w"] and r["y"] - 2 <= feet <= r["y"] + r["h"] + 2:
                return r
        return None

    def zone(self) -> str:
        return next((z["name"] for z in self.zones if z["x0"] <= self.x < z["x1"]), "")

    # -- tick ----------------------------------------------------------------------
    def step(self, dt: float, move: int = 0, run: bool = False, jump: bool = False, attack: bool = False) -> None:
        a = self.actor
        dead = a.state == "death"
        grounded = a.height <= 0 and a.vy <= 0
        top, under = (self.feet, None) if dead else self.floor(self.x, self.feet, grounded)
        a.height = max(0.0, top - self.feet)
        if grounded and under and under["type"] == "bounce" and not dead:      # ALL RISE
            a.vy, a.height = under["launch"], 0.01
            a._enter("jump")

        hurt = False
        if grounded and not dead and a.state != "hurt" and self.touching("hazard", self.x, self.feet):
            hurt = self.slipping = True                                          # slipped on an a-peel
        die = not dead and (self.touching("water", self.x, self.feet) is not None or self.feet > self.info["size"][1] + 24)
        if die:
            a.vy, a.height, top = 0.0, 0.0, self.feet
        if self.judge.update(dt, self.x, active=self.x > self.info["boss"]["arena"][0] and not dead) and a.height < 12:
            hurt = True                                                          # ORDER!
        was = a.state
        a.update(dt, move=move, run=run, jump=jump, attack=attack, hurt=hurt, die=die)
        if hurt and was != "hurt" and a.state == "hurt":
            self.contempt += 1
        if was == "death" and a.state == "idle":                                 # respawned
            self.x, self.feet = map(float, self.checkpoint)
            return
        if a.state == "attack" and a.frame == 2:                                 # whack the judge
            jx, jy = self.judge.center
            reach = self.x + a.facing * 18
            if abs(reach - jx) < 24 and self.feet - 44 < jy + 12:
                self.judge.hit()
        if a.state != "jump" and a.height > 0 and a.state in ("idle", "walk", "run"):
            a._enter("jump")                                                     # walked off a ledge: falling frames

        self.feet = top - a.height
        self.slipping = self.slipping and a.state == "hurt"
        dx = (a.facing * SLIP_SPEED if self.slipping else a.dx) * dt
        if grounded and under and under["type"] == "conveyor":                   # MOTION TO DISMISS
            dx += under["push"] * dt
        if dx and not self.blocked(self.x + dx, self.feet):
            crouching = a.state == "jump" and a.vy == 0 and a.height == 0
            if crouching and self.floor(self.x + dx, self.feet, True)[0] > self.feet:
                a.vy, a.height = JUMP_VELOCITY, 0.01                             # don't crouch off a ledge: launch now
            self.x += dx
        for cp in self.info["checkpoints"]:
            if cp[0] <= self.x and cp[0] > self.checkpoint[0]:
                self.checkpoint = tuple(cp)


class Screen:
    """Pre-rendered level + judge surfaces, and a draw() for any World."""

    def __init__(self):
        far, level, props = L.render()
        self.info = L.data(props)
        self.far, self.level = to_surface(far), to_surface(level)
        self.judge = {}
        for anim, frames in judge.all_frames().items():
            right = [to_surface(f) for f in frames]
            self.judge[anim] = {1: right, -1: [pygame.transform.flip(s, True, False) for s in right]}
        self.texts: dict[tuple[str, str], pygame.Surface] = {}

    def text(self, s: str, color: str) -> pygame.Surface:
        if (s, color) not in self.texts:
            self.texts[(s, color)] = text_surface(s, color)
        return self.texts[(s, color)]

    def label(self, screen: pygame.Surface, s: str, color: str, x: int, y: int, scale: int = 1, right: bool = False) -> None:
        """HUD text on a dark plate, so it reads over the busy walls."""
        t = self.text(s, color)
        if scale > 1:
            t = pygame.transform.scale_by(t, scale)
        if right:
            x -= t.get_width()
        pygame.draw.rect(screen, hex_to_rgba(K["frame"]), (x - 2, y - 2, t.get_width() + 4, t.get_height() + 4))
        screen.blit(t, (x, y))

    def draw(self, screen: pygame.Surface, world: World, who: Loaded) -> None:
        lw, lh = self.info["size"]
        cam_x = int(min(max(world.x - VW // 2, 0), lw - VW))
        cam_y = self.info["camera_y"]
        off = (cam_x // 2) % L.FAR_W
        for k in range(VW // L.FAR_W + 2):
            screen.blit(self.far, (k * L.FAR_W - off, -cam_y))
        screen.blit(self.level, (-cam_x, -cam_y))

        j = world.judge
        frame = self.judge[j.state][j.facing][j.frame]
        screen.blit(frame, (round(j.x) - cam_x, round(j.y) - cam_y))

        a = world.actor
        sprite = who.frames[a.state][a.facing][a.frame]
        screen.blit(sprite, (round(world.x) - SIZE // 2 - cam_x, round(world.feet) - 1 - GROUND - cam_y))
        if j.state == "attack" and j.frame >= 2:
            order = self.text("ORDER!", SPAGHETTI_JUDGE["text"])
            screen.blit(order, (round(j.gavel_x) - order.get_width() // 2 - cam_x, round(j.y) + judge.IMPACT[1] - 14 - cam_y))

        self.label(screen, world.zone(), K["sign_text"], 6, 6)
        self.label(screen, who.ch.name, LAB_TEXT, 6, 15)
        self.label(screen, f"CONTEMPT OF COURT: {world.contempt}", K["neon"], VW - 6, 6, right=True)
        if world.x > self.info["boss"]["arena"][0] - VW // 2:
            self.label(screen, "JUDGE SPAGHETTI", SPAGHETTI_JUDGE["noodle"], VW - 6, 15, right=True)
            pygame.draw.rect(screen, hex_to_rgba(K["frame"]), (VW - 8 - JUDGE_HITS * 6, 22, JUDGE_HITS * 6 + 2, 6))
            for i in range(JUDGE_HITS):
                col = SPAGHETTI_JUDGE["sauce"] if i < j.hp else K["grey_sh"]
                pygame.draw.rect(screen, hex_to_rgba(col), (VW - 6 - (JUDGE_HITS - i) * 6, 23, 5, 3))
        if j.state == "death" and j.t > 1.0:
            for k, (s, col) in enumerate((("CASE DISMISSED", K["sign_text"]), ("R TO START OVER", LAB_DIM))):
                scale = 2 if k == 0 else 1
                self.label(screen, s, col, VW // 2 - self.text(s, col).get_width() * scale // 2, 44 + k * 16, scale)


def run(scale: int = 4, fullscreen: bool = False) -> None:
    pygame.init()
    flags = pygame.FULLSCREEN | pygame.SCALED if fullscreen else 0
    window = pygame.display.set_mode((VW, VH), flags) if fullscreen else pygame.display.set_mode((VW * scale, VH * scale))
    pygame.display.set_caption(L.NAME)
    screen = pygame.Surface((VW, VH))
    clock = pygame.time.Clock()

    view = Screen()
    world = World(view.info)
    cast = [Loaded(ch) for ch in roster()]
    idx = 0
    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 1 / 20)
        pressed = set()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif ev.type == pygame.KEYDOWN:
                pressed.add(ev.key)
                if ev.key == pygame.K_DOWN:
                    idx = (idx + 1) % len(cast)
                elif ev.key == pygame.K_UP:
                    idx = (idx - 1) % len(cast)
                elif ev.key == pygame.K_m:
                    cast.append(Loaded(from_specimen(random_specimen(random.randrange(1000, 9999)))))
                    idx = len(cast) - 1
                elif ev.key == pygame.K_r:
                    world.restart()
        keys = pygame.key.get_pressed()
        world.step(
            dt,
            move=keys[pygame.K_RIGHT] - keys[pygame.K_LEFT],
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=bool(pressed & {pygame.K_SPACE, pygame.K_z}),
            attack=pygame.K_x in pressed,
        )
        view.draw(screen, world, cast[idx])
        pygame.transform.scale(screen, window.get_size(), window)
        pygame.display.flip()
    pygame.quit()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help=f"window scale (internal res is {VW}x{VH})")
    ap.add_argument("--fullscreen", action="store_true")
    args = ap.parse_args()
    run(scale=args.scale, fullscreen=args.fullscreen)


if __name__ == "__main__":
    main()
