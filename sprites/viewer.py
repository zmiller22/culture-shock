"""Interactive sprite viewer (pygame-ce). Runs on a desktop or a Raspberry Pi 5.

    python -m sprites.viewer [--fullscreen] [--scale 4]

Controls:
    LEFT / RIGHT   walk (the lab floor scrolls)
    UP / DOWN      previous / next character
    M              splice a brand-new random Kronenberg
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
from .rig import FPS, GROUND, SIZE
from .species.kronenberg import random_specimen

W, H = 320, 180          # internal resolution; scaled up to the window
FLOOR_Y = 150
WALK_SPEED = 1.5         # px per tick at 60 Hz


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


def run(scale: int = 4, fullscreen: bool = False, max_ticks: int | None = None, screenshot: str | None = None) -> None:
    pygame.init()
    flags = pygame.FULLSCREEN | pygame.SCALED if fullscreen else pygame.SCALED
    window = pygame.display.set_mode((W, H), flags) if fullscreen else pygame.display.set_mode((W * scale, H * scale))
    pygame.display.set_caption("Mad Science Gene Lab")
    screen = pygame.Surface((W, H))
    clock = pygame.time.Clock()

    cast = [Loaded(ch) for ch in roster()]
    help_text = text_surface("ARROWS: WALK/SWAP   M: SPLICE MUTANT   Q: QUIT", LAB_DIM)
    idx, facing, scroll, t = 0, 1, 0.0, 0.0
    ticks = 0
    running = True
    while running:
        dt = clock.tick(60) / 1000
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_DOWN:
                    idx = (idx + 1) % len(cast)
                elif ev.key == pygame.K_UP:
                    idx = (idx - 1) % len(cast)
                elif ev.key == pygame.K_m:
                    cast.append(Loaded(from_specimen(random_specimen(random.randrange(1000, 9999)))))
                    idx = len(cast) - 1

        keys = pygame.key.get_pressed()
        move = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        anim = "walk" if move else "idle"
        if move:
            facing = move
            scroll += move * WALK_SPEED * 60 * dt
        t += dt

        cur = cast[idx]
        frames = cur.frames[anim][facing]
        frame = frames[int(t * FPS[anim]) % len(frames)]

        draw_lab(screen, scroll)
        screen.blit(frame, (W // 2 - SIZE // 2, FLOOR_Y - GROUND - 1))
        screen.blit(cur.title, (8, 8))
        screen.blit(cur.sub, (8, 16))
        screen.blit(help_text, (8, H - 10))
        counter = text_surface(f"{idx + 1}/{len(cast)}", LAB_DIM)
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
