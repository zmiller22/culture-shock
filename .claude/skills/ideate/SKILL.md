---
name: ideate
description: Rapid-fire ideate-then-build loop for this 8-bit arcade project. The user dumps ideas over several messages, says "build", answers a few quick questions (including which git branch), reviews 8-bit mockups and a storyboard, then says go. Use when the user runs /ideate or says they want to brainstorm or jam on a new mini-game, character, level or feature before building it.
---

# Ideate → Build

A fast loop: **collect → ask → mock up → build**. Keep every message short. This is a jam, not a planning meeting.

## Phase 1: Collect (repeat until "build")

The user will send ideas over several messages. For **each** message in this phase:

- Read it and keep it in mind. Don't summarize it, critique it, plan, read files, or call tools.
- Reply with exactly:

  > say 'build' when you are done ideating

Stay in this phase across turns until the user's message is (or plainly means) **build** ("build", "build it", "ok build", "done"). Any idea text in that same message counts as one more chunk.

If the skill was invoked with arguments, treat them as the first chunk and reply the same way.

## Phase 2: Clarify (one round)

1. Run `git branch --format='%(refname:short)'` and `git branch --show-current`.
2. Call **AskUserQuestion** once, with up to 4 questions total:
   - **Branch** (always): "New branch" (Recommended, suggest a kebab-case name from the idea), "Current branch (<name>)", plus up to 2 other recent existing branches. The user can type any other branch name via Other.
   - **1–3 questions only where the ideas are genuinely ambiguous** and the answer changes what gets built. Examples: 1P vs 2P, standalone mini-game vs part of the Theories of Life main game, which existing cast members appear, win/lose condition. Skip anything with a sensible default; state the default later instead.
3. Don't switch branches yet.

## Phase 3: Mock up (show, don't tell)

Render real 8-bit pixel images with the project's own tools, so they match the game. Write the mockup script in the scratchpad directory, not the repo, and run it from the repo root so imports work (`python -c` / `PYTHONPATH=.`).

Make 2–3 PNGs, each at native 320×180 (the game's resolution, see `minigames/shell.py`) and upscaled 4× with nearest-neighbor:

- **key_frame.png**: the main gameplay screen. Characters, playfield, HUD (score, timer, lives) placed where they'd really sit.
- **layout.png**: the same screen with labeled zones or arrows: where the player moves, where enemies spawn, where the goal is, which controls do what.
- **storyboard.png**: 3–5 small panels in a strip (intro → core loop → twist → win/lose), each with a one-line caption in the pixel font.

Aesthetic rules (non-negotiable):
- Colors from `sprites/palette.py`. Outline everything with `OUTLINE` (`#140c1c`). Limited ramps (shadow / base / highlight), no gradients, no anti-aliasing.
- Draw on `sprites.canvas.Canvas`, text with `sprites.font.draw_text` / `draw_text_centered`.
- Reuse existing sprites where they fit (`assets/sprites/`, `sprites/characters.py`, `sprites/species/`). Rough placeholder shapes are fine for new things: it's a sketch, not final art.
- The tone is the project's: weird, cheeky, arcade cabinet.

Show the images with **SendUserFile** (`display: "render"`). Then send at most ~5 lines: the one-sentence pitch, the core loop, controls, the defaults you picked, and:

> Feedback, or say 'go'.

If they give feedback, update only the affected images, re-send them, and ask again. Keep each round fast.

## Phase 4: Build

On "go" (or "go ahead", "ship it", "looks good"):

1. Set up the branch they chose (`git switch -c <name>` or `git switch <name>`). If the working tree has uncommitted changes that would conflict or get carried along, say so in one line and ask before switching.
2. Build it, following the existing patterns:
   - Mini-games live in `minigames/<slug>/` (`__init__.py`, `__main__.py`, `game.py`, `art.py`) and follow the `minigames/shell.py` protocol. Look at `minigames/meet_cute/` as the model.
   - Sprites and characters follow `sprites/` and get added to the README cast table if they're new.
   - Add a preview image to `assets/previews/` and a short README section, matching the existing voice.
3. Run it headless (`SDL_VIDEODRIVER=dummy`) for a few seconds to make sure it starts and draws without errors, and grab a screenshot to show the user.
4. Wrap up briefly: what got built, how to run it, and what's not done. Don't commit unless the user asks.
