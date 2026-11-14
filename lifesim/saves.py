"""Saved games, one per visitor name, so a returning visitor picks up where they
left off: straight to the theory map, with the same body and the same results.

    ~/.life_lab/players/<NAME>/state.json     visitor number, results, timings
    ~/.life_lab/players/<NAME>/<anim>.png     the body Spit Kit spliced them, one strip per animation

Move it with LIFE_LAB_PLAYERS. A save only exists once they've got a body (the
end of Spit Kit); before that there's nothing to pick up.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

PLAYERS_DIR = Path(os.environ.get("LIFE_LAB_PLAYERS", Path.home() / ".life_lab" / "players"))


@dataclass
class Save:
    name: str
    visitor: int
    results: dict[str, list[str]] = field(default_factory=dict)   # theory code -> every result, in order
    frontier_shown: bool = False
    confirmed_at: float = 0.0       # s of play when they confirmed their latest new theory
    played: float = 0.0             # s of play so far, over every visit
    frames: dict[str, int] = field(default_factory=dict)          # animation -> frames in its strip


def _dir(name: str, root: Path) -> Path:
    return root / name


def exists(name: str, root: Path = PLAYERS_DIR) -> bool:
    return (_dir(name, root) / "state.json").is_file()


def names(root: Path = PLAYERS_DIR) -> set[str]:
    try:
        return {p.name for p in root.iterdir() if (p / "state.json").is_file()}
    except OSError:
        return set()


def load(name: str, root: Path = PLAYERS_DIR) -> Save | None:
    try:
        data = json.loads((_dir(name, root) / "state.json").read_text())
        return Save(**data)
    except (OSError, ValueError, TypeError):
        return None


def save(state: Save, avatar=None, root: Path = PLAYERS_DIR) -> None:
    """Write the state, and the body's frames too when given (anim -> list of Canvas)."""
    d = _dir(state.name, root)
    try:
        d.mkdir(parents=True, exist_ok=True)
        if avatar:
            from PIL import Image
            state.frames = {}
            for anim, canvases in avatar.items():
                imgs = [c.to_image() for c in canvases]
                if not imgs:
                    continue
                w, h = imgs[0].size
                strip = Image.new("RGBA", (w * len(imgs), h))
                for i, img in enumerate(imgs):
                    strip.paste(img, (i * w, 0))
                strip.save(d / f"{anim}.png")
                state.frames[anim] = len(imgs)
        tmp = d / "state.json.part"
        tmp.write_text(json.dumps(asdict(state), indent=1))
        tmp.replace(d / "state.json")
    except OSError:
        pass                                          # a read-only cabinet still plays


def load_avatar(state: Save, root: Path = PLAYERS_DIR):
    """The saved body as pygame surfaces: anim -> frames facing right. None if it's missing."""
    import pygame
    d = _dir(state.name, root)
    out = {}
    try:
        for anim, n in state.frames.items():
            strip = pygame.image.load(str(d / f"{anim}.png")).convert_alpha()
            w = strip.get_width() // n
            out[anim] = [strip.subsurface((i * w, 0, w, strip.get_height())).copy() for i in range(n)]
    except (OSError, pygame.error, ZeroDivisionError):
        return None
    return out if "idle" in out else None


def forget(name: str, root: Path = PLAYERS_DIR) -> None:
    shutil.rmtree(_dir(name, root), ignore_errors=True)
