"""The spit jar: the HX711 load cell under the jar next to the cabinet.

`SpitWatcher` is the state machine from tools/spit_detector.py (same states,
same thresholds, same events), with the printing and CSV logging taken out so
the game can drive it. If you retune the tool, copy the numbers into `Tuning`.

`Jar` runs the sensor in a child process (this file, run as a script) (so the game loop can't hold the
GIL in the middle of an HX711 read and stretch a clock pulse), and the game
polls it once a tick:

    jar = get_jar()
    jar.poll()                 # -> [("SPIT", 4210.0), ...] since the last poll
    jar.state, jar.diff        # "IDLE" / "CHANGING" / ..., counts above the baseline

If there's no sensor (no lgpio, e.g. on a laptop, or the HX711 doesn't answer),
`jar.live` is False and the game takes the button as the spit instead.

Environment:
    SPIT_JAR=off          don't look for the sensor at all
    SPIT_JAR_INVERT=1     adding weight reads negative (same as the tool's --invert)
    SPIT_JAR_PINS=0,5,13  gpiochip, SCK, DATA
"""

from __future__ import annotations

import importlib.util
import atexit
import os
import queue
import statistics
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"


@dataclass
class Tuning:
    """Defaults match tools/spit_detector.py's flags."""
    threshold: float = 100
    fast: int = 10
    settle: int = 10
    settle_std: float = 60
    timeout: float = 10
    start_hold: float = 3.0
    start_timeout: float = 10.0
    reset_drop: float = 1000
    reset_hold: float = 3.0
    lift: float = 50_000
    drift: float = 0.002


class SpitWatcher:
    """Feed it (t, value) samples; it returns an event name when something happens.
    Events: READY, ERROR, SPIT, RESET, PLACED, REMOVED, BUMP, UNSETTLED."""

    def __init__(self, tuning: Tuning | None = None) -> None:
        self.k = k = tuning or Tuning()
        self.fast: deque[float] = deque(maxlen=k.fast)
        self.settle: deque[float] = deque(maxlen=k.settle)
        self.state, self.baseline, self.t_change, self.peak = "START", 0.0, 0.0, 0.0
        self.pre_drop = 0.0
        self.t_steady: float | None = None
        self.t_start: float | None = None
        self.start_buf: list[float] = []
        self.diff = 0.0
        self.delta = 0.0                       # size of the last event's step

    def feed(self, t: float, v: float) -> str:
        k = self.k
        self.fast.append(v)
        self.settle.append(v)
        f = statistics.fmean(self.fast)
        event = ""
        steady = len(self.settle) == self.settle.maxlen and statistics.stdev(self.settle) < k.settle_std
        if self.t_start is None:
            self.t_start = t

        if self.state in ("START", "ERROR"):
            if steady:
                if self.t_steady is None:
                    self.t_steady, self.start_buf = t, []
                self.start_buf.append(v)
                if t - self.t_steady >= k.start_hold:
                    self.baseline = statistics.fmean(self.start_buf)
                    event, self.state, self.t_steady = "READY", "IDLE", None
            else:
                self.t_steady = None
                if self.state == "START" and t - self.t_start >= k.start_timeout:
                    event, self.state = "ERROR", "ERROR"
        elif self.state == "IDLE":
            if abs(f - self.baseline) > k.threshold:
                self.state, self.t_change, self.peak = "CHANGING", t, f - self.baseline
            elif abs(f - self.baseline) < k.threshold / 2:
                self.baseline += k.drift * (f - self.baseline)
            elif steady and abs(statistics.fmean(self.settle) - self.baseline) > k.threshold * 0.7:
                self.state, self.t_change, self.peak = "CHANGING", t - k.settle * 0.1, f - self.baseline
        elif self.state == "CHANGING":
            if abs(f - self.baseline) > abs(self.peak):
                self.peak = f - self.baseline
            settled_now = steady and t - self.t_change > k.settle * 0.1
            if settled_now or t - self.t_change > k.timeout:
                level = statistics.fmean(self.settle)
                d = level - self.baseline
                if not settled_now:
                    event = "UNSETTLED"
                elif d < -k.reset_drop:
                    event = "RESET"
                elif d > k.lift:
                    event = "PLACED"
                elif d > k.threshold:
                    event = "SPIT"
                elif d < -k.threshold:
                    event = "REMOVED"
                else:
                    event = "BUMP"
                self.delta = d
                self.baseline, self.state = level, "IDLE"
                if event == "RESET":
                    self.state, self.pre_drop, self.t_steady = "RESET", level - d, None
                    self.baseline = self.pre_drop
        elif self.state == "RESET":
            level = statistics.fmean(self.settle)
            if steady and level > self.pre_drop - k.lift:
                self.t_steady = t if self.t_steady is None else self.t_steady
                if t - self.t_steady >= k.reset_hold:
                    event, self.delta = "READY", level - self.pre_drop
                    self.baseline, self.state = level, "IDLE"
            else:
                self.t_steady = None
        self.diff = f - self.baseline
        return event


def _load_hx711():
    """tools/hx711_test.py's HX711 class (it imports lgpio, so this fails off the Pi)."""
    spec = importlib.util.spec_from_file_location("hx711_test", TOOLS / "hx711_test.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.HX711


def sensor_loop(chip: int, sck: int, data: int, sign: int) -> None:
    """Runs in the child process: read, watch, report one line per message on stdout.
    Restarts the chip on errors."""
    HX711 = _load_hx711()

    def say(*parts: object) -> None:
        print(" ".join(str(p) for p in parts), flush=True)

    while True:
        try:
            hx = HX711(chip, sck, data, 128)
        except Exception as e:                       # noqa: BLE001 - report anything, keep trying
            say("status", "OFFLINE", 0, type(e).__name__)
            time.sleep(2.0)
            continue
        w = SpitWatcher()
        t0, t_status = time.monotonic(), 0.0
        try:
            hx.read()                                # first read sets the gain
            while True:
                raw, slow = hx.read()
                if slow:
                    continue
                t = time.monotonic() - t0
                event = w.feed(t, sign * raw)
                if event:
                    say("event", event, f"{w.delta:.0f}")
                if event or t - t_status > 0.1:
                    t_status = t
                    say("status", w.state, f"{w.diff:.0f}")
        except Exception as e:                       # noqa: BLE001
            say("status", "OFFLINE", 0, type(e).__name__)
            time.sleep(1.0)
        finally:
            try:
                hx.close()
            except Exception:                        # noqa: BLE001
                pass


class Jar:
    def __init__(self) -> None:
        self.live = False                            # a sensor process is running
        self.state = "OFFLINE"
        self.diff = 0.0
        self.error = ""
        self.threshold = Tuning().threshold
        self._lines: queue.Queue[str] = queue.Queue()
        self._events: list[tuple[str, float]] = []
        if os.environ.get("SPIT_JAR", "").lower() in ("off", "0", "no"):
            self.error = "SPIT_JAR=off"
            return
        if importlib.util.find_spec("lgpio") is None:
            self.error = "no lgpio"
            return
        pins = os.environ.get("SPIT_JAR_PINS", "0,5,13").split(",")
        sign = "-1" if os.environ.get("SPIT_JAR_INVERT") else "1"
        # A child process, not a thread: the game loop can't stretch an HX711 clock pulse.
        self._proc = subprocess.Popen([sys.executable, "-u", __file__, *pins, sign], stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, text=True, cwd=ROOT)
        atexit.register(self._proc.kill)
        threading.Thread(target=self._pump, daemon=True).start()
        self.live = True
        self.state = "START"

    def _pump(self) -> None:
        for line in self._proc.stdout:
            self._lines.put(line)
        self._lines.put("status OFFLINE 0 exited")

    def poll(self) -> list[tuple[str, float]]:
        """Events since the last poll (and refresh state / diff)."""
        while True:
            try:
                parts = self._lines.get_nowait().split()
            except queue.Empty:
                break
            if len(parts) < 3:
                continue
            kind, name, value = parts[:3]
            if kind == "status":
                self.state, self.diff = name, float(value)
                self.error = parts[3] if len(parts) > 3 else ""
            elif kind == "event":
                self._events.append((name, float(value)))
        out, self._events = self._events, []
        return out

    @property
    def ready(self) -> bool:
        """Watching for a spit right now."""
        return self.live and self.state in ("IDLE", "CHANGING")


_JAR: Jar | None = None


def get_jar() -> Jar:
    """One sensor process for the whole session: it keeps its baseline between rounds."""
    global _JAR
    if _JAR is None:
        _JAR = Jar()
    return _JAR


if __name__ == "__main__":
    chip, sck, data, sign = (int(v) for v in sys.argv[1:5])
    sensor_loop(chip, sck, data, sign)
