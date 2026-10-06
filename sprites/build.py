"""Export every character to sprite sheets + a JSON atlas, plus preview art.

    python -m sprites.build                      # control group + curated Kronenbergs
    python -m sprites.build --mutants 12 --seed 500   # ...plus 12 random splices

Outputs (under --out, default ./assets):
    sprites/<slug>.png          sheet: one row per animation state, one 48x48 cell per frame
    sprites/atlas.json          frame size, rows, frame counts, fps, looping, recipes
    previews/lineup.png         the whole cast, scaled up
    previews/<slug>.gif         every state in sequence, scaled up
    previews/states/<slug>.png  labeled grid of every state, scaled up
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .canvas import Canvas
from .characters import Character, roster
from .font import draw_text, draw_text_centered, text_width
from .palette import LAB_BG, LAB_DIM, LAB_FLOOR, LAB_GRID, LAB_TEXT, MUTANT
from .rig import ANIMATIONS, FPS, GROUND, LOOP, SIZE

ROOT = Path(__file__).resolve().parent.parent

# How each state is used in-game; copied into the atlas for whoever writes the engine side.
STATE_NOTES = {
    "idle": "loop while standing still",
    "walk": "loop while moving",
    "run": "loop while moving fast",
    "jump": "0 = crouch on take-off, 1 = rising, 2 = apex, 3 = falling; pick by vertical velocity. "
            "Height is not baked in: move the sprite with physics.",
    "attack": "play once; the hit lands on frame 2 (impact effect)",
    "hurt": "play once on taking damage; frame 1 is the white hit-flash",
    "death": "play once and hold the last frame (puddle of goo)",
}


def sheet(frames: dict[str, list[Canvas]]) -> Image.Image:
    cols = max(len(f) for f in frames.values())
    img = Image.new("RGBA", (cols * SIZE, len(frames) * SIZE), (0, 0, 0, 0))
    for row, anim in enumerate(frames):
        for col, frame in enumerate(frames[anim]):
            img.alpha_composite(frame.to_image(), (col * SIZE, row * SIZE))
    return img


def lab_floor(c: Canvas, x: int, y: int, w: int, scroll: int = 0) -> None:
    """A strip of lab floor whose top edge sits just under the feet at row y."""
    c.rect(x, y, w, 3, LAB_FLOOR)
    for gx in range(x - scroll % 8, x + w, 8):
        if x <= gx < x + w:
            c.vline(gx, y, y + 2, LAB_GRID)


# (state, times through) for the preview GIF, plus jump-arc heights for show
GIF_SEQUENCE = [("idle", 2), ("walk", 2), ("run", 3), ("jump", 1), ("attack", 2), ("hurt", 2), ("death", 1)]
JUMP_ARC = [0, 6, 10, 5]
HEADROOM = 12


def gif(ch: Character, path: Path, scale: int) -> None:
    images, durations = [], []
    scroll = 0
    for anim, repeats in GIF_SEQUENCE:
        frames = ch.frames(anim)
        for _ in range(repeats):
            for i, frame in enumerate(frames):
                scroll += {"walk": 1, "run": 3}.get(anim, 0)
                c = Canvas(SIZE, SIZE + 2 + HEADROOM)
                c.rect(0, 0, c.w, c.h, LAB_BG)
                lab_floor(c, 0, HEADROOM + GROUND + 2, c.w, scroll=scroll)
                lift = JUMP_ARC[i] if anim == "jump" else 0
                c.paste(frame, 0, HEADROOM - lift)
                draw_text(c, 2, 2, anim, LAB_DIM)
                images.append(c.to_image(scale).convert("RGB"))
                durations.append(1000 // FPS[anim])
    durations[-1] = 1500                                     # linger on the puddle
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0, disposal=2)


def state_sheet(ch: Character) -> Image.Image:
    """Labeled grid: one row per state, for eyeballing every frame at once."""
    label_w, row_h = 30, SIZE + 4
    frames = ch.all_frames()
    cols = max(len(f) for f in frames.values())
    c = Canvas(label_w + cols * SIZE + 4, 14 + len(frames) * row_h)
    c.rect(0, 0, c.w, c.h, LAB_BG)
    draw_text(c, 4, 4, ch.name, LAB_TEXT)
    for row, anim in enumerate(frames):
        y = 14 + row * row_h
        draw_text(c, 4, y + SIZE // 2 - 2, anim, MUTANT["fluid"])
        for col, frame in enumerate(frames[anim]):
            x = label_w + col * SIZE
            lab_floor(c, x + 2, y + GROUND + 2, SIZE - 4)
            c.paste(frame, x, y)
    return c.to_image(4)


def lineup(chars: list[Character], cols: int = 7) -> Image.Image:
    cell_w, cell_h, margin = 56, 66, 8
    sections = [
        ("CONTROL GROUP", [c for c in chars if c.kind == "control"]),
        ("KRONENBERG SERIES", [c for c in chars if c.kind == "kronenberg"]),
    ]
    rows = sum(-(-len(members) // cols) for _, members in sections)
    width = cols * cell_w + 2 * margin
    height = 16 + len(sections) * 12 + rows * cell_h + margin
    c = Canvas(width, height)
    c.rect(0, 0, width, height, LAB_BG)
    draw_text_centered(c, width // 2, 5, "MAD SCIENCE GENE LAB", LAB_TEXT)
    y = 16
    for title, members in sections:
        draw_text(c, margin, y + 2, title, MUTANT["fluid"])
        c.hline(margin + text_width(title) + 3, width - margin, y + 4, LAB_GRID)
        y += 12
        for i, ch in enumerate(members):
            col, row = i % cols, i // cols
            x0, y0 = margin + col * cell_w + (cell_w - SIZE) // 2, y + row * cell_h
            lab_floor(c, x0 + 2, y0 + GROUND + 2, SIZE - 4)
            c.paste(ch.frames("idle")[0], x0, y0)
            cx = margin + col * cell_w + cell_w // 2
            draw_text_centered(c, cx, y0 + 51, ch.name, LAB_TEXT)
            if ch.kind == "kronenberg":
                draw_text_centered(c, cx, y0 + 58, f"NO. {ch.meta['specimen']:03d}", LAB_DIM)
        y += -(-len(members) // cols) * cell_h
    return c.to_image()


def build(out: Path, mutants: int, seed: int, scale: int) -> None:
    sprites_dir, previews_dir = out / "sprites", out / "previews"
    for d in (sprites_dir, previews_dir / "states"):
        d.mkdir(parents=True, exist_ok=True)

    chars = roster(mutants=mutants, seed=seed)
    atlas = {
        "frame_size": [SIZE, SIZE],
        "facing": "right",
        "ground_row": GROUND,
        "states": STATE_NOTES,
        "characters": {},
    }
    for ch in chars:
        frames = ch.all_frames()
        sheet(frames).save(sprites_dir / f"{ch.slug}.png")
        gif(ch, previews_dir / f"{ch.slug}.gif", scale)
        state_sheet(ch).save(previews_dir / "states" / f"{ch.slug}.png")
        atlas["characters"][ch.slug] = {
            "name": ch.name,
            "kind": ch.kind,
            "sheet": f"{ch.slug}.png",
            "animations": {
                anim: {"row": row, "frames": len(frames[anim]), "fps": FPS[anim], "loop": LOOP[anim]}
                for row, anim in enumerate(ANIMATIONS)
            },
            **ch.meta,
        }
        print(f"  {ch.kind:<10} {ch.slug}")
    (sprites_dir / "atlas.json").write_text(json.dumps(atlas, indent=2) + "\n")
    img = lineup(chars)
    img.resize((img.width * 4, img.height * 4), Image.NEAREST).save(previews_dir / "lineup.png")
    print(f"wrote {len(chars)} characters to {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "assets")
    ap.add_argument("--mutants", type=int, default=0, help="extra random Kronenbergs to splice")
    ap.add_argument("--seed", type=int, default=100, help="seed for the first random Kronenberg")
    ap.add_argument("--scale", type=int, default=6, help="upscale factor for preview GIFs")
    args = ap.parse_args()
    build(args.out, args.mutants, args.seed, args.scale)


if __name__ == "__main__":
    main()
