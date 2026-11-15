#!/usr/bin/env bash
# Cabinet Pi: stop the game and the monitor that keeps restarting it (tools/run_cabinet.sh).
# Just killing the game makes the monitor start it again, which is handy for picking up new code.
set -uo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
dir="$HOME/.life_lab"
touch "$dir/stop"                                        # the monitor sees this and doesn't restart
pkill -f "python3 -m (lifesim|minigames)|$repo/minigames/" 2>/dev/null
for _ in $(seq 20); do                                   # give it up to 10 s to notice
    pgrep -f "$repo/tools/run_cabinet.sh" > /dev/null || break
    sleep 0.5
done
pkill -f "$repo/tools/run_cabinet.sh" 2>/dev/null
rm -f "$dir/stop"
echo "stopped"
