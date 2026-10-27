"""Interactive sprite viewer (pygame-ce). Runs on a desktop or a Raspberry Pi 5.

    python -m sprites.viewer [--fullscreen] [--scale 4]

Controls (keyboard, or an arcade stick / gamepad):
    LEFT / RIGHT   walk (hold SHIFT to run)                stick left / right
    SPACE / Z      jump                                     button 0
    X              attack                                   button 1
    H              take a hit
    K              die (melts, then respawns)
    DOWN           crouch (hold)                            stick down
    UP             interact (doors, switches)               stick up
    TAB            next character (SHIFT+TAB: previous)
    M              splice a brand-new random Kronenberg     button 3
    ESC / Q        quit
"""

from __future__ import annotations

import argparse
import random

import pygame

from .canvas import Canvas, hex_to_rgba, mix
from .characters import Character, from_specimen, roster
from .font import draw_text, text_width
from .palette import LAB_BG, LAB_DIM, LAB_FLOOR, LAB_GRID, LAB_TEXT, MUTANT
from .rig import ANIMATIONS, FPS, GROUND, SIZE
from .species.kronenberg import random_specimen

W, H = 320, 180          # internal resolution; scaled up to the window
FLOOR_Y = 150
WALK_SPEED = 90          # px/s
RUN_SPEED = 180
JUMP_VELOCITY = 260      # px/s upward at take-off
GRAVITY = 900            # px/s^2
CROUCH_TIME = 1 / FPS["jump"]
RESPAWN_DELAY = 1.5      # seconds the puddle lingers
STICK_THRESHOLD = 0.5    # arcade sticks are digital; this also ignores floating axes
JOY_JUMP, JOY_ATTACK, JOY_MUTATE = 0, 1, 3   # button indices as reported by tools/controller_test.py


def stick(joy: pygame.joystick.JoystickType) -> tuple[int, int]:
    """Stick direction as (x, y) in -1/0/+1, y down. Reads hat 0 if the encoder
    reports one, otherwise axes 0/1."""
    if joy.get_numhats() and joy.get_hat(0) != (0, 0):
        hx, hy = joy.get_hat(0)
        return hx, -hy
    axis = lambda i: joy.get_axis(i) if joy.get_numaxes() > i else 0.0
    zone = lambda v: (v > STICK_THRESHOLD) - (v < -STICK_THRESHOLD)
    return zone(axis(0)), zone(axis(1))


class Actor:
    """Animation state machine for one character. No pygame in here, so the same
    logic can be lifted straight into the game.

    Call `update(dt, move, run, jump, attack, hurt, die, crouch, interact)` once
    per tick (`crouch` is held, the rest are presses), then read
    `state`, `frame` (index into that state's row) and `height` (px above floor).
    """

    ONE_SHOTS = ("attack", "hurt", "death", "interact")

    def __init__(self) -> None:
        self.state, self.t = "idle", 0.0
        self.facing, self.height, self.vy = 1, 0.0, 0.0
        self.dx = 0.0                         # horizontal speed this tick, px/s

    @property
    def grounded(self) -> bool:
        return self.height <= 0 and self.vy <= 0

    def _enter(self, state: str) -> None:
        if state != self.state:
            self.state, self.t = state, 0.0

    def _done(self) -> bool:
        return self.t * FPS[self.state] >= len(ANIMATIONS[self.state])

    def update(self, dt: float, move: int = 0, run: bool = False, jump: bool = False,
               attack: bool = False, hurt: bool = False, die: bool = False,
               crouch: bool = False, interact: bool = False) -> None:
        self.t += dt
        if die and self.state != "death":
            self._enter("death")
        elif hurt and self.state not in ("hurt", "death"):
            self._enter("hurt")
        elif attack and self.state not in self.ONE_SHOTS:
            self._enter("attack")
        elif jump and self.grounded and self.state not in self.ONE_SHOTS + ("jump",):
            self._enter("jump")
        elif interact and self.grounded and self.state not in self.ONE_SHOTS + ("jump",):
            self._enter("interact")

        # crouch while DOWN is held on the ground; stand back up on release
        if crouch and self.grounded and self.state in ("idle", "walk", "run"):
            self._enter("crouch")
        elif self.state == "crouch" and not crouch:
            self._enter("idle")

        # one-shots end on their own; death lingers, then respawns
        if self.state in ("attack", "hurt", "interact") and self._done():
            self._enter("idle")
        if self.state == "death" and self.t * FPS["death"] >= len(ANIMATIONS["death"]) + RESPAWN_DELAY * FPS["death"]:
            self.__init__()

        # jump: crouch, launch, then physics until we land
        if self.state == "jump" and self.vy == 0 and self.height == 0 and self.t >= CROUCH_TIME:
            self.vy = JUMP_VELOCITY
        if self.vy or self.height > 0:
            self.vy -= GRAVITY * dt
            self.height = max(0.0, self.height + self.vy * dt)
            if self.height == 0 and self.vy < 0:
                self.vy = 0.0
                if self.state == "jump":
                    self._enter("idle")

        # horizontal movement (none while attacking, hurt or dead; knockback when hurt)
        self.dx = 0.0
        if self.state == "hurt":
            self.dx = -self.facing * 40
        elif self.state not in self.ONE_SHOTS and move:
            self.facing = move
            if self.state != "crouch":                     # crouched: turn, but stay put
                self.dx = move * (RUN_SPEED if run else WALK_SPEED)
        if self.state in ("idle", "walk", "run"):
            self._enter("run" if move and run else "walk" if move else "idle")

    @property
    def frame(self) -> int:
        n = len(ANIMATIONS[self.state])
        if self.state == "jump":
            if self.height == 0 and self.vy == 0:
                return 0                                   # crouch
            return 1 if self.vy > 60 else 2 if self.vy > -60 else 3
        i = int(self.t * FPS[self.state])
        return i % n if self.state in ("idle", "walk", "run") else min(i, n - 1)


def to_surface(c: Canvas) -> pygame.Surface:
    img = c.to_image()
    return pygame.image.frombytes(img.tobytes(), img.size, "RGBA").convert_alpha()


def text_surface(text: str, color: str) -> pygame.Surface:
    c = Canvas(max(1, text_width(text)), 5)
    draw_text(c, 0, 0, text, color)
    return to_surface(c)


class Loaded:
    """A character with every frame pre-rendered to surfaces (both facings)."""

    def __init__(self, ch: Character):
        self.ch = ch
        self.frames = {}
        for anim, frames in ch.all_frames().items():
            right = [to_surface(f) for f in frames]
            self.frames[anim] = {1: right, -1: [pygame.transform.flip(s, True, False) for s in right]}
        self.title = text_surface(ch.name, LAB_TEXT)
        if ch.kind == "kronenberg":
            r = ch.meta["recipe"]
            sub = f"NO. {ch.meta['specimen']:03d}  HEAD:{r['head']} BODY:{r['torso']} LEGS:{r['legs']}"
            self.sub = text_surface(sub.replace("_", " "), LAB_DIM)
        else:
            self.sub = text_surface("CONTROL GROUP", LAB_DIM)


def draw_lab(screen: pygame.Surface, scroll: float) -> None:
    screen.fill(hex_to_rgba(LAB_BG))
    # back wall: specimen tubes
    for i in range(-1, 7):
        x = int(i * 56 - scroll * 0.5) % (56 * 7) - 28
        pygame.draw.rect(screen, hex_to_rgba(LAB_GRID), (x, 40, 18, 90), 1)
        pygame.draw.rect(screen, hex_to_rgba(mix(MUTANT["fluid_dk"], LAB_BG, 0.6)), (x + 2, 70, 14, 58))
        pygame.draw.rect(screen, hex_to_rgba(LAB_FLOOR), (x - 2, 36, 22, 5))
    # floor
    pygame.draw.rect(screen, hex_to_rgba(LAB_FLOOR), (0, FLOOR_Y, W, H - FLOOR_Y))
    for gx in range(-16, W + 16, 16):
        x = gx - int(scroll) % 16
        pygame.draw.line(screen, hex_to_rgba(LAB_GRID), (x, FLOOR_Y), (x - 12, H), 1)
    pygame.draw.line(screen, hex_to_rgba(LAB_GRID), (0, FLOOR_Y), (W, FLOOR_Y), 1)


def mutant() -> Loaded:
    return Loaded(from_specimen(random_specimen(random.randrange(1000, 9999))))


def run(scale: int = 4, fullscreen: bool = False, max_ticks: int | None = None, screenshot: str | None = None) -> None:
    pygame.init()
    flags = pygame.FULLSCREEN | pygame.SCALED if fullscreen else pygame.SCALED
    window = pygame.display.set_mode((W, H), flags) if fullscreen else pygame.display.set_mode((W * scale, H * scale))
    pygame.display.set_caption("Mad Science Gene Lab")
    screen = pygame.Surface((W, H))
    clock = pygame.time.Clock()

    cast = [Loaded(ch) for ch in roster()]
    help_text = text_surface("ARROWS: MOVE/CROUCH/USE  SPACE: JUMP  X: ATTACK  TAB: NEXT  H K M", LAB_DIM)
    idx, scroll = 0, 0.0
    actor = Actor()
    pads: dict[int, pygame.joystick.JoystickType] = {}
    last_y = 0                                  # stick up acts on the edge, like a key press
    ticks = 0
    running = True
    while running:
        dt = clock.tick(60) / 1000
        pressed = set()
        joy_pressed = set()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif ev.type == pygame.KEYDOWN:
                pressed.add(ev.key)
                if ev.key == pygame.K_TAB:
                    idx = (idx + (-1 if ev.mod & pygame.KMOD_SHIFT else 1)) % len(cast)
                elif ev.key == pygame.K_m:
                    cast.append(mutant())
                    idx = len(cast) - 1
            elif ev.type == pygame.JOYDEVICEADDED:
                joy = pygame.joystick.Joystick(ev.device_index)
                pads[joy.get_instance_id()] = joy
            elif ev.type == pygame.JOYDEVICEREMOVED:
                pads.pop(ev.instance_id, None)
            elif ev.type == pygame.JOYBUTTONDOWN:
                joy_pressed.add(ev.button)
                if ev.button == JOY_MUTATE:
                    cast.append(mutant())
                    idx = len(cast) - 1

        # Any connected pad drives the actor (one player for now).
        sx, sy = 0, 0
        for joy in pads.values():
            jx, jy = stick(joy)
            sx, sy = sx or jx, sy or jy
        interact = sy < 0 and last_y >= 0
        last_y = sy

        keys = pygame.key.get_pressed()
        actor.update(
            dt,
            move=max(-1, min(1, keys[pygame.K_RIGHT] - keys[pygame.K_LEFT] + sx)),
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=bool(pressed & {pygame.K_SPACE, pygame.K_z}) or JOY_JUMP in joy_pressed,
            attack=pygame.K_x in pressed or JOY_ATTACK in joy_pressed,
            hurt=pygame.K_h in pressed,
            die=pygame.K_k in pressed,
            crouch=bool(keys[pygame.K_DOWN]) or sy > 0,
            interact=pygame.K_UP in pressed or interact,
        )
        scroll += actor.dx * dt

        cur = cast[idx]
        frame = cur.frames[actor.state][actor.facing][actor.frame]
        x, y = W // 2 - SIZE // 2, FLOOR_Y - GROUND - 1

        draw_lab(screen, scroll)
        if actor.height > 0:                                  # shadow while airborne
            w = max(6, 18 - int(actor.height) // 4)
            pygame.draw.ellipse(screen, hex_to_rgba(LAB_GRID), (W // 2 - w // 2, FLOOR_Y - 1, w, 3))
        screen.blit(frame, (x, y - round(actor.height)))
        screen.blit(cur.title, (8, 8))
        screen.blit(cur.sub, (8, 16))
        screen.blit(help_text, (8, H - 10))
        counter = text_surface(f"{idx + 1}/{len(cast)}  {actor.state}", LAB_DIM)
        screen.blit(counter, (W - counter.get_width() - 8, 8))

        pygame.transform.scale(screen, window.get_size(), window)
        pygame.display.flip()

        ticks += 1
        if max_ticks and ticks >= max_ticks:
            if screenshot:
                pygame.image.save(window, screenshot)
            running = False
    pygame.quit()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=4, help="window scale (internal res is 320x180)")
    ap.add_argument("--fullscreen", action="store_true")
    args = ap.parse_args()
    run(scale=args.scale, fullscreen=args.fullscreen)


if __name__ == "__main__":
    main()
