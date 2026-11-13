# Notes for Claude

## Terminology

"Main game" means the sequence that runs from the mainframe start, through the
galaxy sequence, to the terminal screen.

## Running things

The project runs in the `8-bit` conda environment (see `environment.yml`). The
system `python` doesn't have pygame.

When you give the user terminal commands, make each one a single self-contained
line that runs from any directory in the right environment, so they can click it
to run without activating anything first. Don't give a separate `conda activate`
step. Use this form, one command per code block:

```bash
cd ~/dev/8-bit-art && conda run --no-capture-output -n 8-bit python -m lifesim --skip-boot
```

`--no-capture-output` makes the game's output show up live in the terminal.

When you run things yourself, use the env's interpreter the same way
(`conda run -n 8-bit python ...`).
