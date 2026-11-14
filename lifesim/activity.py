"""The lab's activity log: what each visitor got up to, one JSON line per event.

It's OFF until you switch it on, either with `--log-activity` or by setting
LIFE_LAB_ACTIVITY=1. When it's on, events go to ~/.life_lab/activity.jsonl (next
to the visitor log; override with LIFE_LAB_ACTIVITY_LOG). Demos and --ticks
test runs never write to it.

Each line looks like

    {"t": "2026-11-13T15:02:11", "session": "a1b2c3", "visitor": 12, "name": "ZACH",
     "event": "file_open", "file": "NOTEBOOK_001.TXT", "via": "list"}

Events:
    session_start / session_end    the game opened / closed (session_end has "secs")
    sign_in                        the visitor typed their name
    files_open / files_close       C:/> FILES opened / backed out of
    file_open                      a file was opened. "via": list, code or next (the button a message ends on)
    code                           a password was typed into UNLOCK.EXE. "result": granted, denied, ooh or trip
    ooh_end                        the OOH sequence ended (or they backed out of it): "secs" in
    roll_end                       a rick roll finished. "bailed": true if they skipped out early
    theory_start / theory_end      a simulation was picked / ended (theory_end has "result")
    frontier                       every theory tested: the CONGRATULATIONS! screen (OOH IS THE ANSWER)
    idle_prompt                    nobody touched anything for a while: the countdown came up ("phase")
    idle_continue                  someone tapped to carry on
    idle_exit                      back to the start screen. "why": hold (held the button) or timeout

To read it back as a per-visitor summary (files opened and how many times, codes
tried, theories played):

    python -m lifesim.activity [path]
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(os.environ.get("LIFE_LAB_ACTIVITY_LOG", Path.home() / ".life_lab" / "activity.jsonl"))


def enabled_by_env() -> bool:
    return os.environ.get("LIFE_LAB_ACTIVITY", "").lower() in ("1", "true", "yes", "on")


class ActivityLog:
    """Appends events for one play session. A disabled log takes the same calls and does nothing."""

    def __init__(self, enabled: bool = False, path: Path = LOG_PATH, visitor: int = 0, name: str = "ANON") -> None:
        self.enabled = enabled
        self.path = path
        self.visitor = visitor
        self.name = name
        self.session = uuid.uuid4().hex[:6]
        self.started = time.monotonic()

    def __call__(self, event: str, **data) -> None:
        if not self.enabled:
            return
        row = {"t": datetime.now().isoformat(timespec="seconds"), "session": self.session,
               "visitor": self.visitor, "name": self.name, "event": event, **data}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(row) + "\n")
        except OSError:
            self.enabled = False                      # a read-only cabinet still plays; stop trying

    def close(self) -> None:
        self("session_end", secs=round(time.monotonic() - self.started))


# -- reading it back ------------------------------------------------------------------
def load(path: Path = LOG_PATH) -> list[dict]:
    rows = []
    try:
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except OSError:
        pass
    return rows


def report(rows: list[dict]) -> str:
    """A plain-text summary: every visitor's files, codes and theories, then lab-wide file totals."""
    if not rows:
        return "No activity logged."
    by_session: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_session[r["session"]].append(r)
    totals: Counter[str] = Counter()
    readers: dict[str, set[str]] = defaultdict(set)
    out = []
    for evs in by_session.values():
        last = evs[-1]
        who = f"VISITOR {last['visitor']:04d} {last['name']}"
        out.append(f"{who}  (session {last['session']}, {evs[0]['t']})")
        files = Counter(e["file"] for e in evs if e["event"] == "file_open")
        for name, n in files.most_common():
            out.append(f"    {n:3d}x  {name}")
            totals[name] += n
            readers[name].add(e_key(last))
        codes = [f"{e['code']}:{e['result']}" for e in evs if e["event"] == "code"]
        if codes:
            out.append("    codes: " + " ".join(codes))
        played = [f"{e['theory']}:{e.get('result', '?')}" for e in evs if e["event"] == "theory_end"]
        if played:
            out.append("    theories: " + " ".join(played))
        if not files and not codes and not played:
            out.append("    (nothing opened)")
        out.append("")
    out.append("ALL VISITORS")
    for name, n in totals.most_common():
        out.append(f"    {n:3d}x  {name}  ({len(readers[name])} visitor{'s' * (len(readers[name]) != 1)})")
    return "\n".join(out)


def e_key(e: dict) -> str:
    return f"{e['visitor']}:{e['name']}:{e['session']}"


if __name__ == "__main__":
    print(report(load(Path(sys.argv[1]) if len(sys.argv) > 1 else LOG_PATH)))
