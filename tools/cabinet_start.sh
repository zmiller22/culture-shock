#!/usr/bin/env bash
# What the cabinet Pi runs at boot (see tools/install_autostart.sh): wait a few seconds for the
# sound server and the arcade sticks, then the main game, fullscreen. Output goes to ~/.life_lab/autostart.log.
set -uo pipefail
mkdir -p "$HOME/.life_lab"
sleep 5
exec "$(cd "$(dirname "$0")/.." && pwd)/play.sh" >> "$HOME/.life_lab/autostart.log" 2>&1
