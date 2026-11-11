"""HX711 load-cell tester. Streams raw readings to the terminal so you can see
what the spit-jar scale is actually producing.

    python3 tools/hx711_test.py [--sck 5] [--data 13] [--gain 128] [--raw]

Wiring (Pi physical pins): VIO -> 1 (3.3 V), VIN -> 2 (5 V), GND -> 6,
SCK -> 29 (GPIO5), DATA -> 33 (GPIO13; GPIO6 is the audio HAT mute line), RATE -> GND (10 samples/s).

On start it averages a few samples as the tare (zero). Each line then shows the
raw 24-bit count, the change from tare, and a bar for that change. Every few
seconds a summary line shows the sample rate and the noise (std dev).
Readings that look wrong are tagged:
  SLOW   a clock pulse stayed high past 60 us (Linux paused us), so the value may be garbage
  RAIL   value is at the min/max (open wire, or DATA stuck high/low)
Ctrl+C quits.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import deque

import lgpio

GAIN_PULSES = {128: 25, 32: 26, 64: 27}   # total SCK pulses -> gain of the NEXT reading
MAX_HIGH_NS = 60_000                       # SCK high longer than this powers the chip down
READY_TIMEOUT = 1.0                        # s to wait for DATA to go low


class HX711:
    def __init__(self, chip: int, sck: int, data: int, gain: int):
        self.h = lgpio.gpiochip_open(chip)
        self.sck, self.data = sck, data
        self.pulses = GAIN_PULSES[gain]
        lgpio.gpio_claim_output(self.h, sck, 0)
        lgpio.gpio_claim_input(self.h, data)
        time.sleep(0.001)                  # SCK low >= 1 us wakes the chip

    def close(self):
        lgpio.gpio_write(self.h, self.sck, 0)
        lgpio.gpiochip_close(self.h)

    def read(self) -> tuple[int, bool]:
        """Return (signed value, slow) where slow means a pulse ran too long."""
        deadline = time.monotonic() + READY_TIMEOUT
        while lgpio.gpio_read(self.h, self.data):
            if time.monotonic() > deadline:
                raise TimeoutError("DATA never went low (no sample ready)")
            time.sleep(0.0005)
        h, sck, data, ns = self.h, self.sck, self.data, time.perf_counter_ns
        w, r = lgpio.gpio_write, lgpio.gpio_read
        v, worst = 0, 0
        for i in range(self.pulses):
            t0 = ns()
            w(h, sck, 1)
            w(h, sck, 0)
            worst = max(worst, ns() - t0)
            if i < 24:
                v = (v << 1) | r(h, data)
        if not r(h, data):                 # a real HX711 drives DATA high after the last pulse
            raise TimeoutError("DATA stuck low after a read (not connected, or no HX711 on this pin)")
        if v & 0x800000:
            v -= 1 << 24
        return v, worst > MAX_HIGH_NS


def bar(delta: float, span: float, width: int = 30) -> str:
    n = max(-width, min(width, round(delta / span * width))) if span else 0
    left = " " * (width + min(n, 0)) + "#" * -min(n, 0)
    right = "#" * max(n, 0) + " " * (width - max(n, 0))
    return f"[{left}|{right}]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chip", type=int, default=0, help="gpiochip (Pi 5 header = 0)")
    ap.add_argument("--sck", type=int, default=5, help="BCM GPIO for SCK")
    ap.add_argument("--data", type=int, default=13, help="BCM GPIO for DATA")
    ap.add_argument("--gain", type=int, default=128, choices=GAIN_PULSES)
    ap.add_argument("--tare", type=int, default=10, help="samples averaged for tare")
    ap.add_argument("--span", type=float, default=50_000, help="counts for a full bar")
    ap.add_argument("--summary", type=float, default=3.0, help="seconds between summaries")
    ap.add_argument("--count", type=int, default=0, help="stop after N samples (0 = forever)")
    ap.add_argument("--raw", action="store_true", help="no tare/bar, just raw values")
    args = ap.parse_args()

    hx = HX711(args.chip, args.sck, args.data, args.gain)
    print(f"HX711 on gpiochip{args.chip}: SCK=GPIO{args.sck} DATA=GPIO{args.data} gain={args.gain}", flush=True)
    try:
        hx.read()                          # first read sets the gain; discard it
        offset = 0
        if not args.raw:
            good = [v for v, slow in (hx.read() for _ in range(args.tare)) if not slow]
            offset = round(statistics.median(good)) if good else 0
            print(f"tare = {offset}  (median of {len(good)} samples)  -- add weight now", flush=True)
        window: deque[int] = deque(maxlen=50)
        n, t_start, t_sum, n_sum = 0, time.monotonic(), time.monotonic(), 0
        while not args.count or n < args.count:
            v, slow = hx.read()
            n, n_sum = n + 1, n_sum + 1
            tags = []
            if slow:
                tags.append("SLOW")
            if v in (0x7FFFFF, -0x800000, -1, 0):
                tags.append("RAIL")
            if not slow:
                window.append(v)
            t = time.monotonic() - t_start
            d = v - offset
            if args.raw:
                print(f"{t:8.2f}s {v:>9}  0x{v & 0xFFFFFF:06X}  {' '.join(tags)}", flush=True)
            else:
                print(f"{t:8.2f}s raw {v:>9}  0x{v & 0xFFFFFF:06X}  d {d:>+9}  {bar(d, args.span)} {' '.join(tags)}", flush=True)
            now = time.monotonic()
            if now - t_sum >= args.summary and len(window) > 1:
                print(f"   -- {n_sum / (now - t_sum):5.1f} samples/s   mean {statistics.fmean(window):.0f}"
                      f"   std {statistics.stdev(window):.0f}   min {min(window)}   max {max(window)}", flush=True)
                t_sum, n_sum = now, 0
    except KeyboardInterrupt:
        print()
    except TimeoutError as e:
        print(f"ERROR: {e}. Check power (VIN/VIO/GND) and the DATA wire.", file=sys.stderr)
        return 1
    finally:
        hx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
