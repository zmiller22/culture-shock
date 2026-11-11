"""Spit-jar detector. Watches the HX711 for a step change in weight and reports
each spit as a change in counts, not an absolute weight. The jar fills up over
the night, so every spit is measured against the level the scale settled at
after the one before.

    python3 tools/spit_detector.py [--threshold 100] [--invert] [--no-log]

How it works (all numbers are raw HX711 counts until we calibrate to grams):
  START     the reading must hold still for --start-hold s; its average becomes the
            baseline and it reports READY. If that hasn't happened within
            --start-timeout s (someone is moving the jar), it reports ERROR and keeps
            trying; READY follows as soon as it holds still.
  baseline  the settled level. It slowly follows drift while nothing is happening.
  fast      the average of the last --fast samples (about 1 s).
  IDLE      when |fast - baseline| > --threshold, something is happening -> CHANGING.
  CHANGING  wait for the reading to hold still (std of the last --settle samples
            < --settle-std). Then delta = new level - baseline:
              delta > +threshold   SPIT    (baseline moves up to the new level)
              delta < -reset-drop  RESET   (jar lifted, emptied or knocked) -> RESET state
              delta > +lift        PLACED  (jar set down on an empty scale, e.g. at start-up)
              delta < -threshold   REMOVED (a little weight came off; baseline moves down)
              otherwise            BUMP    (someone touched it and it came back)
            If it never settles within --timeout s, it re-baselines and reports UNSETTLED.
  RESET     prints PLEASE RESET and ignores spits until the jar is back on the scale
            (within --lift of the old level) and has held still for --reset-hold s.
            Then READY: that level becomes the new baseline.
Positive delta is assumed to mean more weight. If adding weight gives
negative numbers, use --invert.

Every sample is written to logs/spit/<timestamp>.csv so the thresholds can be
tuned against real data. Ctrl+C quits.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from collections import deque
from pathlib import Path

from hx711_test import HX711

LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "spit"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chip", type=int, default=0)
    ap.add_argument("--sck", type=int, default=5)
    ap.add_argument("--data", type=int, default=13)
    ap.add_argument("--threshold", type=float, default=100, help="counts of change that count as an event")
    ap.add_argument("--fast", type=int, default=10, help="samples in the fast moving average")
    ap.add_argument("--settle", type=int, default=10, help="samples that must hold still to call it settled")
    ap.add_argument("--settle-std", type=float, default=60, help="max std (counts) of the settle window")
    ap.add_argument("--timeout", type=float, default=10, help="s to wait for a change to settle")
    ap.add_argument("--start-hold", type=float, default=3.0, help="s the reading must hold still to set the baseline")
    ap.add_argument("--start-timeout", type=float, default=10.0, help="s of start-up without holding still -> ERROR")
    ap.add_argument("--reset-drop", type=float, default=1000, help="counts of drop that ask for a reset")
    ap.add_argument("--reset-hold", type=float, default=3.0, help="s the jar must sit still to finish a reset")
    ap.add_argument("--lift", type=float, default=50_000,
                    help="counts below the pre-reset level that mean the jar is still off the scale")
    ap.add_argument("--drift", type=float, default=0.002, help="how fast the idle baseline follows drift (0..1)")
    ap.add_argument("--status", type=float, default=1.0, help="s between status lines (0 = off)")
    ap.add_argument("--invert", action="store_true", help="flip the sign if adding weight reads negative")
    ap.add_argument("--no-log", action="store_true", help="don't write a CSV")
    ap.add_argument("--replay", type=Path, help="run on a recorded CSV instead of the sensor (no log)")
    args = ap.parse_args()
    sign = -1 if args.invert else 1

    hx = None if args.replay else HX711(args.chip, args.sck, args.data, 128)
    log, writer = None, None
    if not args.no_log and not args.replay:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / time.strftime("%Y%m%d-%H%M%S.csv")
        log = path.open("w", newline="")
        writer = csv.writer(log)
        writer.writerow(["t", "raw", "slow", "fast", "baseline", "diff", "state", "event", "delta"])
        print(f"logging to {path}")
    print(f"threshold {args.threshold:.0f}  fast {args.fast}  settle {args.settle} @ std<{args.settle_std:.0f}"
          f"  timeout {args.timeout:.0f}s", flush=True)

    fast: deque[float] = deque(maxlen=args.fast)
    settle: deque[float] = deque(maxlen=args.settle)
    state, baseline, t_change, peak = "START", 0.0, 0.0, 0.0
    total, spits = 0.0, 0
    pre_drop = 0.0                             # baseline from before the drop that caused a RESET
    t_steady: float | None = None              # when the reading went still (start-up / RESET)
    t_start: float | None = None               # time of the first sample
    start_buf: list[float] = []                # still samples averaged into the start-up baseline
    errored = False

    def samples():
        """Yield (t, raw, slow) from the sensor, or from a recording with --replay."""
        if args.replay:
            with args.replay.open() as fh:
                for r in csv.DictReader(fh):
                    yield float(r["t"]), int(r["raw"]), r["slow"] == "1"
            return
        hx.read()                              # first read sets the gain
        t0 = time.monotonic()
        while True:
            raw, slow = hx.read()
            yield time.monotonic() - t0, raw, slow

    t_status = 0.0
    try:
        for t, raw, slow in samples():
            if slow:                           # a pulse ran long; the value can't be trusted
                if writer:
                    writer.writerow([f"{t:.3f}", raw, 1, "", "", "", state, "", ""])
                continue
            v = sign * raw
            fast.append(v)
            settle.append(v)
            f = statistics.fmean(fast)
            event, delta = "", ""
            steady = len(settle) == settle.maxlen and statistics.stdev(settle) < args.settle_std

            if t_start is None:
                t_start = t
            if state in ("START", "ERROR"):
                # The baseline is the average over --start-hold s of the reading holding still.
                # If that hasn't happened within --start-timeout s, raise ERROR, but keep
                # trying: once it holds still it recovers to READY by itself.
                if steady:
                    if t_steady is None:
                        t_steady, start_buf = t, []
                    start_buf.append(v)
                    if t - t_steady >= args.start_hold:
                        baseline = statistics.fmean(start_buf)
                        event, state, t_steady = "READY", "IDLE", None
                        note = " (recovered from ERROR)" if errored else ""
                        print(f"{t:8.2f}s  ** READY     baseline {baseline:.0f}{note}. Spit away.", flush=True)
                else:
                    t_steady = None
                    if state == "START" and t - t_start >= args.start_timeout:
                        event, state, errored = "ERROR", "ERROR", True
                        print(f"{t:8.2f}s  !! ERROR: the reading won't hold still. Please see a lab staff "
                              "member... or stop fucking around with the DNA sequencer and start again.",
                              flush=True)
                if event and log:
                    log.flush()
            elif state == "IDLE":
                if abs(f - baseline) > args.threshold:
                    state, t_change, peak = "CHANGING", t, f - baseline
                    print(f"{t:8.2f}s  change started ({f - baseline:+.0f})", flush=True)
                elif abs(f - baseline) < args.threshold / 2:
                    # Follow slow drift only while the reading sits near the baseline, so a
                    # small real step can't be quietly absorbed.
                    baseline += args.drift * (f - baseline)
                elif steady and abs(statistics.fmean(settle) - baseline) > args.threshold * 0.7:
                    # Settled somewhere new without crossing the trigger: hand it to the
                    # CHANGING logic, which decides SPIT / BUMP from the settled level.
                    state, t_change, peak = "CHANGING", t - args.settle * 0.1, f - baseline
            elif state == "CHANGING":
                if abs(f - baseline) > abs(peak):
                    peak = f - baseline
                settled_now = steady and t - t_change > args.settle * 0.1
                if settled_now or t - t_change > args.timeout:
                    level = statistics.fmean(settle)
                    d = level - baseline
                    if not settled_now:
                        event = "UNSETTLED"
                    elif d < -args.reset_drop:
                        event = "RESET"        # jar lifted, emptied or knocked: game asks for a reset
                    elif d > args.lift:
                        event = "PLACED"       # jar set down on an empty scale (e.g. at start-up)
                    elif d > args.threshold:
                        event, spits, total = "SPIT", spits + 1, total + d
                    elif d < -args.threshold:
                        event = "REMOVED"
                    else:
                        event = "BUMP"
                    delta = f"{d:.0f}"
                    took = t - t_change
                    extra = f"  #{spits}, total {total:+.0f}" if event == "SPIT" else ""
                    print(f"{t:8.2f}s  ** {event:<9} delta {d:+8.0f}   peak {peak:+8.0f}   "
                          f"took {took:4.1f}s{extra}", flush=True)
                    baseline, state = level, "IDLE"
                    if event == "RESET":
                        # Keep the pre-drop level as the baseline so the status line's
                        # diff shows how far the jar is from where it was.
                        state, pre_drop, t_steady = "RESET", level - d, None
                        baseline = pre_drop
                        print(f"{t:8.2f}s  !! PLEASE RESET: put the jar back and leave it still", flush=True)
                    if log:
                        log.flush()
            elif state == "RESET":
                # Wait for the jar to be back on (level within --lift of where it was) and
                # to hold still for --reset-hold s, then take that as the new baseline.
                level = statistics.fmean(settle)
                if steady and level > pre_drop - args.lift:
                    t_steady = t if t_steady is None else t_steady
                    if t - t_steady >= args.reset_hold:
                        event, delta = "READY", f"{level - pre_drop:.0f}"
                        baseline, state = level, "IDLE"
                        print(f"{t:8.2f}s  ** READY     baseline {baseline:.0f} "
                              f"({level - pre_drop:+.0f} vs before the reset). Spit away.", flush=True)
                        if log:
                            log.flush()
                else:
                    t_steady = None

            if writer:
                writer.writerow([f"{t:.3f}", raw, 0, f"{f:.1f}", f"{baseline:.1f}", f"{f - baseline:.1f}",
                                 state, event, delta])
            if args.status and t - t_status >= args.status and state != "START":
                t_status = t
                sd = statistics.stdev(settle) if len(settle) > 1 else 0
                print(f"{t:8.2f}s  {state:<8} fast {f:10.0f}  base {baseline:10.0f}  "
                      f"diff {f - baseline:+7.0f}  std {sd:5.0f}", flush=True)
        print(f"end of recording: {spits} spits, total change {total:+.0f} counts")
    except KeyboardInterrupt:
        print(f"\n{spits} spits, total change {total:+.0f} counts")
    except TimeoutError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        if hx:
            hx.close()
        if log:
            log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
