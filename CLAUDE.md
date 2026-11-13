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

**Cabinet Pi (no conda):** the system `python3` has pygame. Launch the main game
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
