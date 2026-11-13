# Notes for Claude

## Terminology

"Main game" means the sequence that runs from the mainframe start, through the
galaxy sequence, to the terminal screen.

## Keeping machines in sync

Development moves often between the Mac and the cabinet Pi, so keep GitHub
up to date:

- At the start of every session, before doing anything else, run `git fetch`
  and pull any new commits on the current branch (`git pull --ff-only`). If the
  pull can't fast-forward, or there are local changes in the way, stop and tell
  the user instead of merging or stashing.
- Push every commit right after you make it. Don't leave commits sitting
  locally.

## Running things

Which Python to use depends on the machine. Check with `command -v conda`.

**Cabinet Pi (no conda):** there's no conda and no active virtualenv. The game
runs on the system `python3` (Debian/Raspberry Pi OS, Python 3.13), with its
packages installed through apt, not pip:

- `python3-pygame`: plain pygame 2.6.1, **not** pygame-ce. It has no
  `pygame.image.load_animation`, among other gaps, so anything pygame-ce-only
  needs a fallback.
- `python3-pil`: Pillow 11.1.
- `ffmpeg` and `ffprobe` on the PATH, which the rick roll video uses.

To add a package, use `sudo apt install python3-<name>` (pip is blocked on the
system Python). There's also a stale `.venv/` in the repo, git-ignored, from
the README's pip setup. It has pygame-ce 2.5.8 and Pillow 13, but `play.sh`
doesn't use it and nothing else does either. Launch the main game
with `./play.sh`, which also attaches to the desktop session on the cabinet
monitor (it works over SSH too). It runs fullscreen by default. Any flags you
pass go to the game, and passing a flag also turns off the fullscreen default:

```bash
cd ~/dev/culture-shock && ./play.sh
```

```bash
cd ~/dev/culture-shock && ./play.sh --scale 3 --skip-boot
```

For anything else, use `python3` directly (`python3 -m lifesim ...`).

**Machines with conda:** the project runs in the `8-bit` conda environment (see
`environment.yml`), and the system `python` there doesn't have pygame. Use the
env's interpreter without activating it first:

```bash
cd ~/dev/culture-shock && conda run --no-capture-output -n 8-bit python -m lifesim --skip-boot
```

`--no-capture-output` makes the game's output show up live in the terminal.
When you run things yourself, use `conda run -n 8-bit python ...`.

Either way, when you give the user terminal commands, make each one a single
self-contained line that runs from any directory, so they can click it to run.
Don't give a separate `conda activate` step, and put one command per code block.
