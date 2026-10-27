"""Shared harness for running a mini-game on its own, before it's wired into the
main game. It opens the same 320x180 scaled window as the viewer and reads the
same keyboard / arcade-stick inputs.

A mini-game is any object with:
    update(dt, inp: Input) -> None
    draw(screen: pygame.Surface) -> None
    result: "win" | "lose" | None      set when the round is decided
    done: bool                         True once the player has dismissed the end screen

The main game can drive the same object: call update/draw each tick and read
`result` once `done` goes True.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import pygame

from sprites.viewer import H, JOY_JUMP, W, stick

ACTION_KEYS = (pygame.K_SPACE, pygame.K_z, pygame.K_RETURN)


@dataclass
class Input:
    x: int = 0               # held stick / arrows, -1 / 0 / +1
    y: int = 0               # +1 = down
    action: bool = False     # pressed this tick: SPACE / Z / ENTER, or button 0


class MiniGame(Protocol):
    result: str | None
    done: bool

    def update(self, dt: float, inp: Input) -> None: ...
    def draw(self, screen: pygame.Surface) -> None: ...


def run(make_game: Callable[[], MiniGame], caption: str, scale: int = 4, fullscreen: bool = False,
        autopilot: Callable[[MiniGame], Input] | None = None,
        max_ticks: int | None = None, screenshot: str | None = None) -> None:
    """Play `make_game()` until quit, starting a fresh round whenever one is done.
    `autopilot` replaces the player's input (for demos and smoke tests)."""
    pygame.init()
    if fullscreen:
        window = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
    else:
        window = pygame.display.set_mode((W * scale, H * scale))
    pygame.display.set_caption(caption)
    screen = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    pads: dict[int, pygame.joystick.JoystickType] = {}

    game = make_game()
    ticks = 0
    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 1 / 20)       # don't tunnel through things after a hitch
        inp = Input()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key in ACTION_KEYS:
                inp.action = True
            elif ev.type == pygame.JOYDEVICEADDED:
                joy = pygame.joystick.Joystick(ev.device_index)
                pads[joy.get_instance_id()] = joy
            elif ev.type == pygame.JOYDEVICEREMOVED:
                pads.pop(ev.instance_id, None)
            elif ev.type == pygame.JOYBUTTONDOWN and ev.button == JOY_JUMP:
                inp.action = True

        keys = pygame.key.get_pressed()
        sx, sy = 0, 0
        for joy in pads.values():
            jx, jy = stick(joy)
            sx, sy = sx or jx, sy or jy
        inp.x = max(-1, min(1, keys[pygame.K_RIGHT] - keys[pygame.K_LEFT] + sx))
        inp.y = max(-1, min(1, keys[pygame.K_DOWN] - keys[pygame.K_UP] + sy))
        if autopilot:
            inp = autopilot(game)

        game.update(dt, inp)
        game.draw(screen)
        pygame.transform.scale(screen, window.get_size(), window)
        pygame.display.flip()
        if game.done:
            game = make_game()

        ticks += 1
        if max_ticks and ticks >= max_ticks:
            if screenshot:
                pygame.image.save(screen, screenshot)
            running = False
    pygame.quit()
