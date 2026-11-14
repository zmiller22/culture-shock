"""High scores: how many theories each visitor confirmed, and how fast.

One line per visit in ~/.life_lab/scores.txt (next to the visitor log; override
with LIFE_LAB_SCORES):

    0019 ZACH 3 412        visitor, name, theories confirmed, seconds to the last one

Only visitors who signed in get a line (not --skip-boot runs). A visitor who
comes back under the same name (see saves.py) keeps their number, so their next
line replaces the last one. More confirmed
ranks higher; on a tie, whoever got there in fewer seconds; then whoever came first.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SCORES_LOG = Path(os.environ.get("LIFE_LAB_SCORES", Path.home() / ".life_lab" / "scores.txt"))


@dataclass(frozen=True)
class Score:
    visitor: int
    name: str
    confirmed: int
    secs: int

    def key(self) -> tuple:
        return -self.confirmed, self.secs if self.confirmed else 1 << 30, self.visitor


def load(path: Path = SCORES_LOG) -> list[Score]:
    """Every visitor's latest line (a returning visitor writes another one)."""
    scores: dict[int, Score] = {}
    try:
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 4:
                try:
                    sc = Score(int(parts[0]), parts[1], int(parts[2]), int(parts[3]))
                except ValueError:
                    continue
                scores[sc.visitor] = sc
    except OSError:
        pass
    return list(scores.values())


def save(score: Score, path: Path = SCORES_LOG) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(f"{score.visitor:04d} {score.name} {score.confirmed} {score.secs}\n")
    except OSError:
        pass                                          # a read-only cabinet still plays


def ranked(scores: list[Score]) -> list[Score]:
    return sorted(scores, key=Score.key)


def clock(secs: int) -> str:
    """412 -> 6:52"""
    return f"{secs // 60}:{secs % 60:02d}"
