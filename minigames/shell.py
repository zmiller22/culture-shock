"""Shared harness for running a mini-game on its own, before it's wired into the
main game. It opens the same 320x180 scaled window as the viewer and reads the
same keyboard / arcade-stick inputs.

A mini-game is any object with:
    update(dt, inp: Input) -> None
    draw(screen: pygame.Surface) -> None
    result: "win" | "lose" | None      set when the round is decided
    done: bool                         True once the player has dismissed the end screen
    cutscene: bool                     optional: True while nobody's expected to touch anything,
                                       so the main game holds off its "still there?" countdown

The main game can drive the same object: call update/draw each tick and read
`result` once `done` goes True.

Two-player games read `inp.players` instead: one Input per player. Player 1 is
WASD plus the left stick (by USB port), player 2 is the arrows plus the right
stick. The top-level x / y / action stay merged across everything, so one-player
games work as before.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import pygame

from sprites.viewer import H, JOY_JUMP, W, open_pad, players, stick

ACTION_KEYS = (pygame.K_SPACE, pygame.K_z, pygame.K_RETURN)
P1_KEYS = (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, (pygame.K_SPACE, pygame.K_LSHIFT))   # left right up down action
# The cabinet's 27" 16:9 monitor sits behind a bezel, so fullscreen leaves a black border round the
# picture: BORDER_IN inches top and bottom. The picture keeps its 16:9 shape, so the sides come out
# a little wider than that.
MONITOR_DIAG_IN = 27.0
BORDER_IN = 0.5


def bordered_size(diag_in: float = MONITOR_DIAG_IN, border_in: float = BORDER_IN) -> tuple[int, int]:
    """The fullscreen canvas, in game pixels: the W x H picture plus the border, shaped like the monitor."""
    height_in = diag_in * 9 / (16 ** 2 + 9 ** 2) ** 0.5
    h = round(H * height_in / (height_in - 2 * border_in))
    return round(h * 16 / 9), h


P2_KEYS = (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, (pygame.K_RETURN, pygame.K_RSHIFT))


@dataclass
class Input:
    x: int = 0               # held stick / arrows, -1 / 0 / +1
    y: int = 0               # +1 = down
    action: bool = False     # pressed this tick: SPACE / Z / ENTER, or button 0
    held: bool = False       # an action key or button 0 is down right now (on any stick)
    players: tuple["Input", ...] = ()   # per-player inputs, for two-player games


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
        cw, ch = bordered_size()
        window = pygame.display.set_mode((cw, ch), pygame.FULLSCREEN | pygame.SCALED)
        window.fill((0, 0, 0))
        view = window.subsurface(((cw - W) // 2, (ch - H) // 2, W, H))     # the picture, inside the border
        pygame.mouse.set_visible(False)                                   # no pointer on the cabinet
    else:
        window = view = pygame.display.set_mode((W * scale, H * scale))
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
        pressed_keys: set[int] = set()
        pad_presses: set[int] = set()        # instance ids of pads whose button 0 went down
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif ev.type == pygame.KEYDOWN:
                pressed_keys.add(ev.key)
                if ev.key in ACTION_KEYS:
                    inp.action = True
            elif ev.type == pygame.JOYDEVICEADDED:
                joy = open_pad(ev.device_index)
                pads[joy.get_instance_id()] = joy
            elif ev.type == pygame.JOYDEVICEREMOVED:
                pads.pop(ev.instance_id, None)
            elif ev.type == pygame.JOYBUTTONDOWN and ev.button == JOY_JUMP:
                inp.action = True
                pad_presses.add(ev.instance_id)

        keys = pygame.key.get_pressed()
        sx, sy = 0, 0
        for joy in players(pads):
            jx, jy = stick(joy)
            sx, sy = sx or jx, sy or jy
        inp.x = max(-1, min(1, keys[pygame.K_RIGHT] - keys[pygame.K_LEFT] + sx))
        inp.y = max(-1, min(1, keys[pygame.K_DOWN] - keys[pygame.K_UP] + sy))
        inp.held = any(keys[k] for k in (*ACTION_KEYS, *P1_KEYS[4], *P2_KEYS[4])) or \
            any(j.get_numbuttons() > JOY_JUMP and j.get_button(JOY_JUMP) for j in pads.values())
        joys = players(pads)                  # P1 = left stick, by USB port
        per_player = []
        for i, (left, right, up, down, acts) in enumerate((P1_KEYS, P2_KEYS)):
            px, py = keys[right] - keys[left], keys[down] - keys[up]
            act = bool(pressed_keys & set(acts))
            if i < len(joys):
                jx, jy = stick(joys[i])
                px, py = px or jx, py or jy
                act = act or joys[i].get_instance_id() in pad_presses
            per_player.append(Input(max(-1, min(1, px)), max(-1, min(1, py)), act))
        inp.players = tuple(per_player)
        if autopilot:
            inp = autopilot(game)

        game.update(dt, inp)
        game.draw(screen)
        pygame.transform.scale(screen, view.get_size(), view)
        overlay = getattr(game, "overlay", None)     # optional: draw on the window itself, at full res
        if overlay:
            overlay(view)
        pygame.display.flip()
        if game.done:
            game = make_game()

        ticks += 1
        if max_ticks and ticks >= max_ticks:
            if screenshot:
                pygame.image.save(screen, screenshot)
            running = False
    pygame.quit()
