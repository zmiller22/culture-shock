#!/usr/bin/env bash
# What the cabinet Pi runs at boot (see tools/install_autostart.sh): wait a few seconds for the
# sound server and the arcade sticks, then the main game, fullscreen, under tools/run_cabinet.sh, which
# restarts it if it crashes or freezes. The game's output goes to ~/.life_lab/game.log, crashes to
# ~/.life_lab/crashes.log, and the monitor's own notes to ~/.life_lab/autostart.log.
set -uo pipefail
mkdir -p "$HOME/.life_lab"
sleep 5
exec "$(cd "$(dirname "$0")/.." && pwd)/tools/run_cabinet.sh" >> "$HOME/.life_lab/autostart.log" 2>&1
