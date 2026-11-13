#!/usr/bin/env bash
# Launch the main game (Theories of Life) fullscreen on the cabinet monitor. Works from the Pi's desktop
# or over SSH (it attaches to the desktop session already running on the monitor).
#
#   ./play.sh            fullscreen
#   ./play.sh --scale 3  windowed, any game flags pass through (see python -m lifesim --help)
set -euo pipefail
cd "$(dirname "$0")"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [[ -z "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]]; then
    export WAYLAND_DISPLAY=wayland-0
fi
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-wayland,x11}"

[[ $# -eq 0 ]] && set -- --fullscreen
exec python3 -m lifesim "$@"
