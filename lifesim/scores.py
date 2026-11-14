"""High scores: how many theories each visitor explored, and how many points they got.

One line per visit in ~/.life_lab/scores.txt (next to the visitor log; override
with LIFE_LAB_SCORES):

    0019 ZACH 4 5230 3     visitor, name, theories explored, total points, theories confirmed

A theory is explored once it's been played, won or lost. Total points add up the
best score on each theory, so playing one again can only raise it.

Only visitors who signed in get a line (not --skip-boot runs). A visitor who
comes back under the same name (see saves.py) keeps their number, so their next
line replaces the last one. More explored ranks higher; on a tie, more points;
then whoever came first. Old lines (visitor, name, confirmed, seconds) still
load, as that many explored and no points.
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
    explored: int
    points: int
    confirmed: int = 0

    def key(self) -> tuple:
        return -self.explored, -self.points, self.visitor


def load(path: Path = SCORES_LOG) -> list[Score]:
    """Every visitor's latest line (a returning visitor writes another one)."""
    scores: dict[int, Score] = {}
    try:
        for line in path.read_text().splitlines():
            parts = line.split()
            try:
                if len(parts) == 5:
                    sc = Score(int(parts[0]), parts[1], int(parts[2]), int(parts[3]), int(parts[4]))
                elif len(parts) == 4:                 # the old format: confirmed, seconds
                    sc = Score(int(parts[0]), parts[1], int(parts[2]), 0, int(parts[2]))
                else:
                    continue
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
            f.write(f"{score.visitor:04d} {score.name} {score.explored} {score.points} {score.confirmed}\n")
    except OSError:
        pass                                          # a read-only cabinet still plays


def ranked(scores: list[Score]) -> list[Score]:
    return sorted(scores, key=Score.key)
