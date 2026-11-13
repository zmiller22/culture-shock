"""The theory map: where the spirit goes once it has formed.

Every theory of life is a tile in a grid, playing a little looping clip of its
simulation (baked by tools/make_map_previews.py), in the order life supposedly
happens. SYSTEM FILES, the lab's file drawer, is a tall tile down the left.
The stick floats the spirit from tile to tile.

The map only knows about places and moving between them: LifeSim decides what
picking one does.
"""

from __future__ import annotations

import math
from collections import deque
from pathlib import Path

import pygame

from minigames.shell import Input

from .art import CRT_BG, PHOSPHOR, PHOSPHOR_DIM, PHOSPHOR_FAINT

PREVIEW_DIR = Path(__file__).resolve().parent.parent / "assets" / "map"
TILE_W, TILE_H = 80, 45         # a 320x180 frame shrunk 4x
PREVIEW_FPS = 6
PREVIEW_FRAMES = 24             # a 4 s clip
SPEED = 260.0                   # px/s the spirit floats between tiles
VOID = (4, 6, 14)

COLS = 3
GRID_X, GRID_Y, GAP_X, GAP_Y = 66, 22, 4, 15
FILES = -1                      # the SYSTEM FILES tile; theories are 0, 1, 2...
FILES_RECT = pygame.Rect(6, GRID_Y, 54, 2 * TILE_H + GAP_Y)


def rgb(c: str) -> tuple[int, int, int]:
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def tile_at(i: int) -> tuple[int, int]:
    """Top-left of theory i's tile."""
    c, r = i % COLS, i // COLS
    return GRID_X + c * (TILE_W + GAP_X), GRID_Y + r * (TILE_H + GAP_Y)


def tile_rect(node: int) -> pygame.Rect:
    return FILES_RECT if node == FILES else pygame.Rect(*tile_at(node), TILE_W, TILE_H)


def load_preview(code: str) -> list[pygame.Surface]:
    """The tile's clip, or a blank card if it hasn't been baked."""
    path = PREVIEW_DIR / f"{code}.png"
    if path.exists():
        strip = pygame.image.load(str(path)).convert()
        n = strip.get_width() // TILE_W
        return [strip.subsurface((i * TILE_W, 0, TILE_W, TILE_H)).copy() for i in range(n)]
    card = pygame.Surface((TILE_W, TILE_H))
    card.fill(rgb(CRT_BG))
    return [card]


class WorldMap:
    def __init__(self, codes: list[str]) -> None:
        self.n = len(codes)
        self.previews = [load_preview(c) for c in codes]
        self.row = 0                    # the grid row the spirit left by, to come back to it from the files
        self.place(0)

    @property
    def moving(self) -> bool:
        return self.target is not None

    def place(self, node: int) -> None:
        self.sel, self.target = node, None
        self.pos = tile_rect(node).center

    def neighbour(self, node: int, dx: int, dy: int) -> int | None:
        if node == FILES:
            return min(self.row * COLS, self.n - 1) if dx > 0 else None
        c, r = node % COLS + dx, node // COLS + dy
        if c < 0:
            return FILES
        nxt = r * COLS + c
        return nxt if 0 <= c < COLS and 0 <= nxt < self.n and r >= 0 else None

    def update(self, dt: float, inp: Input) -> None:
        if self.target is None:
            # the stick: sideways wins if it's pushed both ways. Hold it to keep going
            d = (inp.x, 0) if inp.x else (0, inp.y) if inp.y else None
            nxt = self.neighbour(self.sel, *d) if d else None
            if nxt is not None:
                if nxt == FILES:
                    self.row = self.sel // COLS
                self.target = nxt
            return
        tx, ty = tile_rect(self.target).center
        x, y = self.pos
        dist = math.hypot(tx - x, ty - y)
        step = SPEED * dt
        if dist <= step:
            self.place(self.target)
        else:
            self.pos = (x + (tx - x) / dist * step, y + (ty - y) / dist * step)

    def steer(self, want: int) -> Input:
        """Stick input for the first step toward `want` (for the autopilot)."""
        inp = Input()
        if self.moving or want == self.sel:
            return inp
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        first: dict[int, tuple[int, int]] = {self.sel: (0, 0)}
        todo = deque([self.sel])
        while todo:
            node = todo.popleft()
            for d in dirs:
                nxt = self.neighbour(node, *d)
                if nxt is not None and nxt not in first:
                    first[nxt] = first[node] if node != self.sel else d
                    todo.append(nxt)
        inp.x, inp.y = first.get(want, (0, 0))
        return inp

    # -- drawing -----------------------------------------------------------------------
    def draw_tile(self, screen: pygame.Surface, i: int, t: float, lit: bool) -> None:
        x, y = tile_at(i)
        frames = self.previews[i]
        img = frames[int(t * PREVIEW_FPS) % len(frames)]
        if not lit:                                       # the others play on, dimmer
            img = img.copy()
            img.fill((140, 140, 140), special_flags=pygame.BLEND_MULT)
        screen.blit(img, (x, y))
        self._frame(screen, pygame.Rect(x, y, TILE_W, TILE_H), t, lit)

    def draw_empty(self, screen: pygame.Surface, i: int) -> None:
        """A grid slot with no tape in it yet: a dashed outline."""
        r = pygame.Rect(*tile_at(i), TILE_W, TILE_H)
        col = rgb(PHOSPHOR_FAINT)
        for x in range(r.left, r.right, 4):
            screen.fill(col, (x, r.top, 2, 1))
            screen.fill(col, (x, r.bottom - 1, 2, 1))
        for y in range(r.top, r.bottom, 4):
            screen.fill(col, (r.left, y, 1, 2))
            screen.fill(col, (r.right - 1, y, 1, 2))

    def draw_files(self, screen: pygame.Surface, t: float, lit: bool) -> None:
        """A tall tile with a little filing cabinet in it, three drawers."""
        r = FILES_RECT
        screen.fill(rgb(CRT_BG), r)
        col = rgb(PHOSPHOR if lit else PHOSPHOR_DIM)
        w, h = 24, 30
        x, y = r.centerx - w // 2, r.top + 14
        pygame.draw.rect(screen, col, (x, y, w, h), 1)
        for i in range(3):
            dy = y + 2 + i * 9
            pygame.draw.rect(screen, col, (x + 2, dy, w - 4, 8), 1)
            screen.fill(col, (x + w // 2 - 3, dy + 3, 6, 1))           # the handle
        screen.fill(col, (x + 2, y + h, 3, 2))                          # feet
        screen.fill(col, (x + w - 5, y + h, 3, 2))
        self._frame(screen, r, t, lit)

    def _frame(self, screen: pygame.Surface, r: pygame.Rect, t: float, lit: bool) -> None:
        if not lit:
            pygame.draw.rect(screen, rgb(PHOSPHOR_FAINT), r.inflate(2, 2), 1)
            return
        pygame.draw.rect(screen, rgb(PHOSPHOR if int(t * 3) % 3 else PHOSPHOR_DIM), r.inflate(2, 2), 1)
        pygame.draw.rect(screen, rgb(PHOSPHOR_FAINT), r.inflate(6, 6), 1)
