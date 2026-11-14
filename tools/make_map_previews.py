"""Bake the little looping previews on the theory map's tiles.

Each simulation plays itself on its own autopilot, skipping its title screen,
and a few seconds of it are shrunk down to tile size and saved as a strip of
frames side by side: assets/map/<code>.png. The main game just loads them, so
re-run this after a mini-game's look changes:

    conda run -n 8-bit python -m tools.make_map_previews
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from lifesim.worldmap import PREVIEW_DIR, PREVIEW_FPS, PREVIEW_FRAMES, TILE_H, TILE_W
from sprites.viewer import H, W

DT = 1 / 60
# (module, class, seconds of play to skip before the clip starts): skip past any
# intro so the clip shows the game being played
GAMES = {
    "01": ("minigames.stork_bomber.game", "StorkBomber", 3.0),
    "02": ("minigames.primordial_soup.game", "PrimordialSoup", 4.0),
    "03": ("minigames.it_takes_two.game", "ItTakesTwo", 24.6),
    "04": ("minigames.womb_rave.game", "WombRave", 5.0),
    "06": ("minigames.build_a_bear.game", "BuildABear", 3.0),
}


def bake(code: str, module: str, cls: str, warmup: float) -> Path:
    mod = importlib.import_module(module)
    kwargs = {"seed": 7, "show_title": False}
    if cls == "WombRave":
        kwargs["mute"] = True
    game = getattr(mod, cls)(**kwargs)
    screen = pygame.Surface((W, H))
    every = round(1 / (PREVIEW_FPS * DT))
    for _ in range(round(warmup / DT)):
        game.update(DT, mod.autopilot(game))
    strip = pygame.Surface((TILE_W * PREVIEW_FRAMES, TILE_H))
    for i in range(PREVIEW_FRAMES * every):
        game.update(DT, mod.autopilot(game))
        if i % every == 0:
            game.draw(screen)
            strip.blit(pygame.transform.smoothscale(screen, (TILE_W, TILE_H)), (TILE_W * (i // every), 0))
    out = PREVIEW_DIR / f"{code}.png"
    pygame.image.save(strip, out)
    return out


def main() -> None:
    pygame.init()
    pygame.display.set_mode((W, H))
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for code, (module, cls, warmup) in GAMES.items():
        print("baked", bake(code, module, cls, warmup))


if __name__ == "__main__":
    main()
