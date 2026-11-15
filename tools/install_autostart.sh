#!/usr/bin/env bash
# Cabinet Pi only: launch the main game fullscreen every time the desktop comes up after a boot.
#
#   tools/install_autostart.sh            install (or refresh) the autostart entry
#   tools/install_autostart.sh --remove   take it out again
#
# The Pi logs in to the labwc desktop by itself, and labwc runs everything in
# ~/.config/autostart/. The entry runs tools/cabinet_start.sh, which runs the game under
# tools/run_cabinet.sh (restarts it if it crashes or freezes) and logs to ~/.life_lab/.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
entry="$HOME/.config/autostart/culture-shock.desktop"

if [[ "${1:-}" == "--remove" ]]; then
    rm -f "$entry"
    echo "removed $entry"
    exit 0
fi

mkdir -p "$(dirname "$entry")"
cat > "$entry" <<EOF
[Desktop Entry]
Type=Application
Name=Theories of Life
Comment=The Life Lab cabinet: start the main game after boot
Exec="$repo/tools/cabinet_start.sh"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
echo "installed $entry"
