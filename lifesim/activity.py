"""The lab's play log: what each visitor got up to, one CSV row per event.

It's ON whenever the main game is really being played (demos and --ticks test
runs never write to it). Turn it off with `--no-log` or LIFE_LAB_ACTIVITY=0.
Rows go into the repo, in play_log/<machine>.csv, one file per machine so the
cabinet's log and test runs on a laptop never mix (or clash in git). Override
the path with LIFE_LAB_ACTIVITY_LOG. After an event, commit and push the
cabinet's file and read it anywhere.

Columns:

    time, session, visitor, name, event, theory, game, result, file, code, secs, detail

`session` is one visitor's go, from the start screen back to it. Anything an
event says that doesn't have its own column lands in `detail` as key=value.

Events:
    session_start / session_end    a visitor's go started / ended (session_end has secs)
    sign_in                        the visitor typed their name
    theory_start / theory_end      a game was picked / ended. theory_end has result
                                   (win, lose, quit = left from the exit menu) and secs played
    tutorial_done                  finished the tour of the map
    frontier                       every theory tested: the CONGRATULATIONS! screen (XXX IS THE ANSWER)
    files_open / files_close       C:/> FILES opened / backed out of
    file_open                      a file was opened. detail via=list, code or next
    code                           a password typed into UNLOCK.EXE. result: granted, denied, ooh or trip
    ooh_end                        the OOH sequence ended (or they backed out of it), secs in
    roll_end                       a rick roll finished. detail bailed=True if they skipped out early
    idle_prompt                    the exit menu came up. detail via=idle, hold or exit_tile
    menu_choice                    something was picked on the exit menu (detail option=...)
    idle_continue                  carried on from the exit menu
    idle_exit                      back to the start screen. detail why=timeout, hold, idle or exit_tile

To read it back as a summary (games played and how they went, files opened,
codes tried, and every visitor's go):

    python -m lifesim.activity [file.csv ...]      (default: every file in play_log/)
"""

from __future__ import annotations

import csv
import os
import re
import socket
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "play_log"
COLUMNS = ["time", "session", "visitor", "name", "event", "theory", "game", "result", "file", "code", "secs", "detail"]


def machine() -> str:
    """A short, file-safe name for this machine."""
    name = socket.gethostname().split(".")[0].lower()
    return re.sub(r"[^a-z0-9_-]+", "-", name).strip("-") or "machine"


def default_path() -> Path:
    override = os.environ.get("LIFE_LAB_ACTIVITY_LOG")
    return Path(override) if override else LOG_DIR / f"{machine()}.csv"


def disabled_by_env() -> bool:
    return os.environ.get("LIFE_LAB_ACTIVITY", "").lower() in ("0", "false", "no", "off")


class ActivityLog:
    """Appends events for one visitor's go. A disabled log takes the same calls and does nothing.
    `games` maps a theory code to its game's name, so rows say STORK BOMBER, not just 01."""

    def __init__(self, enabled: bool = True, path: Path | None = None, visitor: int = 0, name: str = "ANON",
                 games: dict[str, str] | None = None) -> None:
        self.enabled = enabled
        self.path = path or default_path()
        self.visitor = visitor
        self.name = name
        self.games = games or {}
        self.session = uuid.uuid4().hex[:6]
        self.started = time.monotonic()
        self.closed = False

    def __call__(self, event: str, **data) -> None:
        if not self.enabled:
            return
        row = {"time": datetime.now().isoformat(timespec="seconds"), "session": self.session,
               "visitor": self.visitor, "name": self.name, "event": event}
        theory = data.pop("theory", None)
        if theory is not None:
            row["theory"] = theory
            row["game"] = self.games.get(theory, "")
        for key in ("result", "file", "code", "secs"):
            if key in data:
                row[key] = data.pop(key)
        row["detail"] = " ".join(f"{k}={v}" for k, v in data.items())
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            new = not self.path.exists() or self.path.stat().st_size == 0
            with self.path.open("a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                if new:
                    w.writeheader()
                w.writerow(row)
        except OSError:
            self.enabled = False                      # a read-only cabinet still plays; stop trying

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self("session_end", secs=round(time.monotonic() - self.started))


# -- reading it back ------------------------------------------------------------------
def load(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        try:
            with path.open(newline="") as f:
                rows += list(csv.DictReader(f))
        except OSError:
            pass
    return rows


def report(rows: list[dict]) -> str:
    """A plain-text overview: games and how they went, files, codes, then every visitor's go."""
    if not rows:
        return "No activity logged."
    sessions: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        sessions[r["session"]].append(r)
    signed_in = sum(any(e["event"] == "sign_in" for e in evs) for evs in sessions.values())
    out = [f"{len(sessions)} visits ({signed_in} signed in), {rows[0]['time']} to {rows[-1]['time']}", ""]

    out.append("GAMES PLAYED")
    played: dict[str, Counter[str]] = defaultdict(Counter)
    secs: Counter[str] = Counter()
    for r in rows:
        if r["event"] == "theory_end":
            game = r["game"] or r["theory"]
            played[game][r["result"] or "?"] += 1
            secs[game] += int(float(r["secs"] or 0))
    for game, results in sorted(played.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(results.values())
        how = ", ".join(f"{k} {v}" for k, v in results.most_common())
        out.append(f"    {n:3d}x  {game:<16} {how}   (avg {secs[game] // n}s)")
    out.append("")

    out.append("FILES OPENED")
    files = Counter(r["file"] for r in rows if r["event"] == "file_open")
    for name, n in files.most_common():
        out.append(f"    {n:3d}x  {name}")
    opened = sum(r["event"] == "files_open" for r in rows)
    out.append(f"    (the file system was opened {opened} times)")
    out.append("")

    codes = Counter(f"{r['code']} ({r['result']})" for r in rows if r["event"] == "code")
    if codes:
        out.append("CODES TRIED")
        for code, n in codes.most_common():
            out.append(f"    {n:3d}x  {code}")
        out.append("")

    other = Counter(r["event"] for r in rows if r["event"] in ("frontier", "ooh_end", "roll_end", "tutorial_done"))
    exits = Counter(dict(kv.split("=", 1) for kv in r["detail"].split() if "=" in kv).get("why", "?")
                    for r in rows if r["event"] == "idle_exit")
    out.append("OTHER")
    for ev, n in other.most_common():
        out.append(f"    {n:3d}x  {ev}")
    for why, n in exits.most_common():
        out.append(f"    {n:3d}x  back to the start screen ({why})")
    out.append("")

    out.append("EVERY VISIT")
    for evs in sessions.values():
        last = evs[-1]
        games = [f"{e['game'] or e['theory']}:{e['result']}" for e in evs if e["event"] == "theory_end"]
        opened = [e["file"] for e in evs if e["event"] == "file_open"]
        line = f"    {evs[0]['time']}  VISITOR {int(last['visitor'] or 0):04d} {last['name']:<5}"
        if games:
            line += "  games: " + " ".join(games)
        if opened:
            line += "  files: " + " ".join(opened)
        out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] or sorted(LOG_DIR.glob("*.csv"))
    print(report(load(paths)))
