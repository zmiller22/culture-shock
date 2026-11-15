#!/usr/bin/env bash
# Cabinet Pi: run the main game (./play.sh) and keep it running. If the game crashes, or freezes
# (stops touching its heartbeat file for FROZEN_AFTER seconds), this starts it again.
#
#   tools/run_cabinet.sh               fullscreen, like ./play.sh (any flags pass through to it)
#   tools/stop_cabinet.sh              stop the monitor and the game (otherwise killing the game restarts it)
#
# Quitting the game on purpose (ESC or Q on a keyboard) stops the monitor too. Anything else that
# ends it (an error, a kill, a freeze) gets a restart a few seconds later.
#
# Everything the game prints goes to ~/.life_lab/game.log. Each crash or freeze is written to
# ~/.life_lab/crashes.log, with the end of the game's output (the Python traceback). A mini-game
# that throws an error doesn't get this far: the main game catches it, logs it to crashes.log and
# carries on (see LifeSim._sim_crashed).
set -uo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
dir="$HOME/.life_lab"
mkdir -p "$dir"
game_log="$dir/game.log"
crash_log="$dir/crashes.log"
export LIFE_LAB_HEARTBEAT="$dir/heartbeat"
FROZEN_AFTER=${LIFE_LAB_FROZEN_AFTER:-90}          # s without a heartbeat before the game counts as frozen (a first rick roll can
                         # spend up to a minute pulling its soundtrack out with ffmpeg)
QUICK=30                 # a crash within this many s of starting counts as a quick one...
BACKOFF=30               # ...and after 3 quick ones in a row, wait this long before the next try

exec 9>"$dir/monitor.lock"
if ! flock -n 9; then
    echo "run_cabinet.sh is already running" >&2
    exit 0
fi
rm -f "$dir/stop"

note() { echo "=== $(date '+%F %T') $*" | tee -a "$game_log" >&2; }

jar_pids=""
cleanup_jar() {          # the spit jar's sensor runs as a child of the game: don't leave it behind
    [[ -n "$jar_pids" ]] && kill $jar_pids 2>/dev/null
    jar_pids=""
}

quick=0
while true; do
    started=$(date +%s)
    log_start=0
    [[ -f "$game_log" ]] && log_start=$(wc -l < "$game_log")
    note "starting the game"
    touch "$LIFE_LAB_HEARTBEAT"
    "${LIFE_LAB_GAME_CMD:-$repo/play.sh}" "$@" >> "$game_log" 2>&1 9>&- &   # (LIFE_LAB_GAME_CMD: for testing)
    pid=$!
    frozen=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 5
        found="$(pgrep -P "$pid" -f spit_kit/jar.py | tr '\n' ' ')"
        [[ -n "${found// /}" ]] && jar_pids="$found"
        [[ -e "$dir/stop" ]] && break
        age=$(( $(date +%s) - $(stat -c %Y "$LIFE_LAB_HEARTBEAT" 2>/dev/null || date +%s) ))
        if (( age > FROZEN_AFTER )); then
            frozen=1
            note "the game has been frozen for ${age}s: killing it"
            kill -TERM "$pid" 2>/dev/null
            sleep 3
            kill -KILL "$pid" 2>/dev/null
            break
        fi
    done
    wait "$pid" 2>/dev/null
    code=$?
    cleanup_jar
    if [[ -e "$dir/stop" ]]; then
        note "stopped (tools/stop_cabinet.sh)"
        rm -f "$dir/stop"
        exit 0
    fi
    if (( code == 0 && frozen == 0 )); then
        note "the game quit on purpose: not restarting"
        exit 0
    fi
    why=$([[ $frozen == 1 ]] && echo "froze" || echo "exited with code $code")
    note "the game $why: restarting"
    {
        echo "=== $(date '+%F %T') the game $why (ran $(( $(date +%s) - started ))s). The end of its output:"
        tail -n +"$(( log_start + 1 ))" "$game_log" | tail -n 40
        echo
    } >> "$crash_log"
    if (( $(date +%s) - started < QUICK )); then
        quick=$(( quick + 1 ))
    else
        quick=0
    fi
    if (( quick >= 3 )); then
        note "crashed $quick times in a row right after starting: waiting ${BACKOFF}s"
        sleep "$BACKOFF"
    else
        sleep 3
    fi
done
