"""Womb Rave's soundtrack and step chart, both generated from code.

The song is a 120 BPM chiptune: amniotic whooshes,
a square-wave bass and a lead that plays exactly on the notes you have to hit. Every SQUEEZE note has a contraction
(a deep womp) baked into the music, so the button hits are audible too.

The song is a list of bars (SONG). Each kind of bar has a fixed rhythm (PATTERNS);
the lanes the notes come down are dealt from a fixed seed, so the chart is the
same every time and can be learned.
"""

from __future__ import annotations

import bisect
import io
import math
import random
import wave
from dataclasses import dataclass

RATE = 22050                     # synth sample rate; the mixer resamples
BPM = 120                        # the starting tempo (and the select-screen loop's)
BEAT = 60 / BPM
EIGHTH = BEAT / 2
BAR = BEAT * 4

# (kind of bar, how many). "count" is the count-in: no notes.
SECTIONS = [("count", 1), ("heart", 2), ("verse", 4), ("chorus", 4), ("break", 2),
            ("verse", 2), ("chorus", 4), ("push", 2)]
SONG = [kind for kind, n in SECTIONS for _ in range(n)]
# The song speeds up as it goes: bar index -> new tempo, each with a shout on screen.
TEMPO_CHANGES = {0: 120, 7: 128, 13: 136, 15: 144, 19: 152}
SPEEDUPS = {7: "FASTER!", 13: "HARDER!", 15: "DEEPER!", 19: "DON'T STOP!"}
BAR_BPM: list[float] = []
for _i in range(len(SONG)):
    BAR_BPM.append(TEMPO_CHANGES.get(_i, BAR_BPM[-1] if BAR_BPM else BPM))
BAR_START = [0.0]                # song time each bar starts (plus the end of the last one)
for _bpm in BAR_BPM:
    BAR_START.append(BAR_START[-1] + 240 / _bpm)
SONG_LEN = BAR_START[-1]
# Bar index each trimester starts on (shown in the HUD), and a cue shown when a section starts.
TRIMESTERS = (1, 7, 15)
CUES = {1: "FIRST TRIMESTER", 7: "SECOND TRIMESTER", 11: "CONTRACTIONS!", 13: "THIRD TRIMESTER", 19: "PUSH!"}

# Rhythm per kind of bar: (eighth-note position 0..7, what's there).
#   d = one stick direction   dd = a diagonal (two directions at once)
#   b = SQUEEZE (button)      bd = button and a direction together
PATTERNS = {
    "count": [],
    "heart": [(0, "d"), (4, "d")],
    "verse": [(0, "d"), (2, "d"), (4, "d"), (6, "d")],
    "chorus": [(0, "bd"), (2, "d"), (3, "d"), (4, "d"), (6, "dd")],
    "chorus2": [(0, "d"), (1, "d"), (2, "d"), (4, "bd"), (6, "d"), (7, "d")],
    "break": [(0, "b"), (2, "d"), (4, "b"), (6, "d")],
    "push": [(0, "b"), (2, "b"), (4, "b"), (6, "bd")],
}
CHART_SEED = 9

# Am - F - C - G, one chord per bar: (bass root Hz, chord tones for the lead)
CHORDS = [(110.0, (440.0, 523.25, 659.25)), (87.31, (349.23, 440.0, 523.25)),
          (130.81, (523.25, 659.25, 783.99)), (98.0, (392.0, 493.88, 587.33))]
MELODY = (0, 1, 2, 1, 2, 0, 1, 2)    # chord tone the lead plays at each eighth


@dataclass
class Note:
    t: float                    # seconds into the song when it should be hit
    lane: str                   # L R U D (stick) or B (button)
    snack: int = 0              # which snack, for U notes
    judged: str | None = None   # perfect | great | ok | miss
    hit_t: float = 0.0          # song time it was judged
    approach: float = 1.6       # s it takes to arrive (shorter once the song speeds up)


def bar_at(t: float) -> int:
    """The bar playing at song time t (clamped to the song)."""
    return max(0, min(len(SONG) - 1, bisect.bisect_right(BAR_START, t) - 1))


def beats(t: float) -> float:
    """Beats elapsed at song time t, counting through the tempo changes."""
    if t < 0:
        return t / BEAT
    i = bar_at(t)
    return i * 4 + (t - BAR_START[i]) * BAR_BPM[i] / 60


def bpm_at(t: float) -> float:
    return BAR_BPM[bar_at(t)]


def bar_kind(i: int) -> str:
    """The pattern bar i uses (choruses alternate between two)."""
    kind = SONG[i]
    if kind == "chorus" and i % 2:
        return "chorus2"
    return kind


def chart() -> list[Note]:
    rng = random.Random(CHART_SEED)
    notes: list[Note] = []
    last: dict[str, float] = {}
    prev = ""

    def pick(t: float, eighth: float, avoid: str = "") -> str:
        nonlocal prev
        options = [ln for ln in "LRUD" if ln != prev and ln not in avoid and t - last.get(ln, -9) > eighth * 1.5]
        lane = rng.choice(options or [ln for ln in "LRUD" if ln not in avoid])
        prev = lane
        return lane

    for i in range(len(SONG)):
        for pos, what in PATTERNS[bar_kind(i)]:
            eighth = 30 / BAR_BPM[i]
            t = BAR_START[i] + pos * eighth
            lanes = []
            if "b" in what:
                lanes.append("B")
            if what == "dd":                                 # stick diagonals: one horizontal, one vertical
                lanes += [rng.choice("LR"), rng.choice("UD")]
            elif "d" in what:
                lanes.append(pick(t, eighth))
            for ln in lanes:
                last[ln] = t
                notes.append(Note(t, ln, rng.randrange(4)))
    return notes


# -- synth --------------------------------------------------------------------------

_noise = random.Random(1)


def _n(seconds: float) -> int:
    return round(seconds * RATE)


def _smooth(s: list[float], a: float) -> list[float]:
    """One-pole lowpass (a: 0..1, lower is darker)."""
    out, y = [], 0.0
    for v in s:
        y += (v - y) * a
        out.append(y)
    return out


def thump(f0: float, f1: float, length: float, decay: float, amp: float) -> list[float]:
    """A kick: a sine that drops in pitch from f0 to f1."""
    out, ph = [], 0.0
    for i in range(_n(length)):
        t = i / RATE
        ph += math.tau * (f1 + (f0 - f1) * math.exp(-t * 28)) / RATE
        out.append(math.sin(ph) * math.exp(-t * decay) * amp * min(1, i / 40))
    return out


def square(f: float, length: float, decay: float, amp: float, duty: float = 0.5, soft: float = 0.4) -> list[float]:
    out = []
    for i in range(_n(length)):
        t = i / RATE
        ph = (t * f) % 1
        out.append((1 if ph < duty else -1) * math.exp(-t * decay) * amp * min(1, i / 60))
    return _smooth(out, soft)


def hiss(length: float, decay: float, amp: float, tone: float = 1.0) -> list[float]:
    raw = [_noise.uniform(-1, 1) for _ in range(_n(length))]
    if tone < 1:
        raw = _smooth(raw, tone)
    else:                                                    # bright: first difference
        raw = [b - a for a, b in zip([0.0] + raw, raw)]
    return [v * math.exp(-i / RATE * decay) * amp for i, v in enumerate(raw)]


def swell(length: float, amp: float, tone: float = 0.05) -> list[float]:
    """A whoosh that fades in and out: the sound of the inside of a womb."""
    raw = _smooth([_noise.uniform(-1, 1) for _ in range(_n(length))], tone)
    n = len(raw)
    return [v * math.sin(math.pi * i / n) ** 2 * amp * 6 for i, v in enumerate(raw)]


def womp(length: float = 0.45, amp: float = 0.55) -> list[float]:
    """A contraction: a growl that sweeps down, over a dark whoosh."""
    out, ph = [], 0.0
    for i in range(_n(length)):
        t = i / RATE
        ph += math.tau * (45 + 150 * math.exp(-t * 7)) / RATE
        s = math.sin(ph)
        out.append(max(-0.7, min(0.7, s * 1.6)) * math.exp(-t * 5) * amp * min(1, i / 80))
    w = swell(length, amp * 0.6, 0.08)
    return [a + b for a, b in zip(out, w)]


def _add(buf: list[float], at: int, snd: list[float]) -> None:
    end = min(len(buf), at + len(snd))
    if at < end:
        buf[at:end] = [a + b for a, b in zip(buf[at:end], snd)]


class _Kit:
    def __init__(self, bpm: float = BPM) -> None:
        BEAT = 60 / bpm
        EIGHTH = BEAT / 2
        self.bar_n = round(BEAT * 4 * RATE)
        self.eighth = EIGHTH
        self.hat = hiss(0.05, 70, 0.18)
        self.snare = [a + b for a, b in zip(hiss(0.2, 18, 0.38, 0.6), thump(220, 160, 0.2, 30, 0.3))]
        self.tick = square(1760, 0.05, 50, 0.18)
        self.whoosh = swell(BEAT, 0.22)
        self.womp = womp()
        self.bass = {f: square(f, EIGHTH * 0.95, 7, 0.26, 0.5, 0.25) for f, _ in CHORDS}
        self.bass_hi = {f: square(f * 2, EIGHTH * 0.95, 9, 0.2, 0.5, 0.25) for f, _ in CHORDS}
        self.bass_long = {f: square(f, BEAT * 1.9, 2.5, 0.24, 0.5, 0.15) for f, _ in CHORDS}
        tones = {f for _, ch in CHORDS for f in ch}
        self.lead = {f: square(f, 0.22, 9, 0.16, 0.25, 0.5) for f in tones}
        self.arp = {f: square(f * 2, EIGHTH / 2 * 0.9, 18, 0.05, 0.125, 0.5) for f in tones}


def render_bar(kind: str, chord: int, k: _Kit) -> list[float]:
    buf = [0.0] * k.bar_n
    root, tones = CHORDS[chord]
    at = lambda pos: round(pos * k.eighth * RATE)
    pattern = PATTERNS[kind]
    base = "chorus" if kind == "chorus2" else kind

    if base == "count":
        for beat in range(4):
            _add(buf, at(beat * 2), k.tick)
    if base in ("heart", "break"):
        for beat in range(4):
            _add(buf, at(beat * 2), k.whoosh)
    if base in ("verse", "chorus", "push"):
        for pos in range(8):
            _add(buf, at(pos), (k.bass if pos % 2 == 0 else k.bass_hi)[root])
            if pos % 2:
                _add(buf, at(pos), k.hat)
    if base == "break":
        _add(buf, at(0), k.bass_long[root])
        _add(buf, at(4), k.bass_long[root])
    if base in ("chorus", "push"):
        _add(buf, at(2), k.snare)
        _add(buf, at(6), k.snare)
    if base == "chorus":
        for i in range(16):
            _add(buf, at(i / 2), k.arp[tones[i % 3]])
    if base == "push":
        for pos in (7, 7.5):
            _add(buf, at(pos), k.snare)
    for pos, what in pattern:
        if "d" in what:
            _add(buf, at(pos), k.lead[tones[MELODY[pos]]])
        if "b" in what:
            _add(buf, at(pos), k.womp)
    return buf


def _wav(samples: list[float], volume: float = 0.8) -> io.BytesIO:
    raw = bytearray()
    for v in samples:
        v = math.tanh(v * 1.1) * volume                     # soft clip
        raw += int(v * 32767).to_bytes(2, "little", signed=True)
    f = io.BytesIO()
    with wave.open(f, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(raw))
    f.seek(0)
    return f


def song_wav() -> io.BytesIO:
    kits: dict[float, _Kit] = {}
    cache: dict[tuple[str, int, float], list[float]] = {}
    out: list[float] = []
    for i in range(len(SONG)):
        bpm = BAR_BPM[i]
        key = (bar_kind(i), i % 4, bpm)
        if key not in cache:
            if bpm not in kits:
                kits[bpm] = _Kit(bpm)
            cache[key] = render_bar(key[0], key[1], kits[bpm])
        start = round(BAR_START[i] * RATE)             # place bars by the tempo map so rounding never drifts
        out += [0.0] * (start - len(out))
        out[start:] = cache[key]
    tail = [0.0] * _n(1.7)                                     # let it ring out
    return _wav(out + tail)


def lobby_wav() -> io.BytesIO:
    """The dancer-select loop: four bars of the intro tune, seamless when looped."""
    kit = _Kit()
    return _wav([v for chord in range(4) for v in render_bar("heart", chord, kit)], volume=0.6)


# -- voice ------------------------------------------------------------------------
# A tiny formant synth: a breathy buzz at the pitch, through three resonators tuned
# to a vowel. Good enough for moans and groans, which is all it's for.

VOWELS = {                       # formant frequencies (Hz): F1, F2, F3
    "mm": (250, 1700, 2600), "oo": (330, 800, 2300), "oh": (480, 860, 2450),
    "ah": (760, 1200, 2550), "uh": (600, 1050, 2400), "eh": (560, 1800, 2550),
}


def _curve(points: list[tuple[float, float]], k: float) -> float:
    """Piecewise-linear value at k (0..1) through (k, value) points."""
    for (k0, v0), (k1, v1) in zip(points, points[1:]):
        if k <= k1:
            return v0 + (v1 - v0) * (k - k0) / max(1e-9, k1 - k0)
    return points[-1][1]


def voice(length: float, pitch: list[tuple[float, float]], vowels: list[tuple[float, str]],
          amp: float = 0.5, breath: float = 0.25, vibrato: float = 0.025,
          env: list[tuple[float, float]] | None = None) -> list[float]:
    n = _n(length)
    env = env or [(0, 0), (0.12, 1), (0.75, 0.8), (1, 0)]
    out, ph = [], 0.0
    state = [[0.0, 0.0] for _ in range(3)]
    for i in range(n):
        t, k = i / RATE, i / n
        f0 = _curve(pitch, k) * (1 + vibrato * math.sin(t * math.tau * 5.5) * min(1, t * 4))
        ph = (ph + f0 / RATE) % 1
        src = (1 - 2 * ph) * (1 - breath) + _noise.uniform(-1, 1) * breath   # buzz plus air
        # glide between the vowels' formants
        idx = max(j for j, (vk, _) in enumerate(vowels) if vk <= k or j == 0)
        if idx + 1 < len(vowels):
            (ka, va), (kb, vb) = vowels[idx], vowels[idx + 1]
            m = min(1.0, max(0.0, (k - ka) / max(1e-9, kb - ka)))
        else:
            va = vb = vowels[idx][1]
            m = 0.0
        y = 0.0
        for j in range(3):
            f = VOWELS[va][j] * (1 - m) + VOWELS[vb][j] * m
            bw = 80 + 40 * j
            r = math.exp(-math.pi * bw / RATE)
            c1, c2 = 2 * r * math.cos(math.tau * f / RATE), -r * r
            s0 = (1 - r) * src + c1 * state[j][0] + c2 * state[j][1]
            state[j][1], state[j][0] = state[j][0], s0
            y += s0 * (1.0, 0.6, 0.3)[j]
        out.append(y * amp * _curve(env, k))
    return out


def moans() -> dict[str, list[float]]:
    """Little 8-bit moans for streaks, getting more worked up as the combo grows."""
    raw = {
        # warming up
        "mmm": voice(0.7, [(0, 210), (0.6, 250), (1, 230)], [(0, "mm"), (1, "mm")], amp=0.9, breath=0.15),
        "ooh": voice(0.6, [(0, 230), (1, 320)], [(0, "oo"), (0.6, "oh")], amp=0.7),
        "oh": voice(0.35, [(0, 340), (1, 280)], [(0, "oh"), (1, "oh")], amp=0.7, env=[(0, 0), (0.08, 1), (1, 0)]),
        "uhh": voice(0.6, [(0, 120), (1, 98)], [(0, "uh"), (1, "uh")], amp=0.8, breath=0.3),
        # into it
        "mmm-ahh": voice(0.85, [(0, 220), (0.45, 240), (0.6, 330), (1, 260)], [(0, "mm"), (0.4, "mm"), (0.55, "ah"), (1, "ah")], amp=0.75),
        "oh-yeah": voice(0.8, [(0, 300), (0.4, 260), (0.55, 350), (1, 300)], [(0, "oh"), (0.45, "oh"), (0.55, "eh"), (1, "ah")], amp=0.7),
        "ah-ah": voice(0.3, [(0, 330), (1, 300)], [(0, "ah"), (1, "ah")], amp=0.7, env=[(0, 0), (0.1, 1), (1, 0)])
        + [0.0] * _n(0.08)
        + voice(0.45, [(0, 360), (1, 310)], [(0, "ah"), (1, "ah")], amp=0.75, env=[(0, 0), (0.1, 1), (1, 0)]),
        # the big one
        "climax": voice(0.25, [(0, 300), (1, 320)], [(0, "ah"), (1, "ah")], amp=0.6, env=[(0, 0), (0.1, 1), (1, 0)])
        + voice(0.25, [(0, 350), (1, 370)], [(0, "ah"), (1, "ah")], amp=0.7, env=[(0, 0), (0.1, 1), (1, 0)])
        + voice(1.1, [(0, 400), (0.3, 470), (1, 330)], [(0, "ah"), (0.7, "ah"), (1, "oh")], amp=0.85, vibrato=0.05),
        # when a big streak breaks
        "aww": voice(0.8, [(0, 300), (1, 150)], [(0, "ah"), (1, "oo")], amp=0.6, breath=0.35),
    }
    out = {}
    for name, snd in raw.items():                            # all at the same loudness
        peak = max(abs(v) for v in snd) or 1.0
        out[name] = [v * 0.75 / peak for v in snd]
    return out


def sfx_wavs() -> dict[str, io.BytesIO]:
    """One-shot effects that play over (or instead of) the song."""
    ph, scratch = 0.0, []
    for i in range(_n(0.7)):                                # record scratch: the music grinds to a halt
        t = i / RATE
        ph += math.tau * (600 * math.exp(-t * 4) + 40 * math.sin(t * 60)) / RATE
        scratch.append(math.sin(ph) * 0.4 * (1 - t / 0.7) + _noise.uniform(-0.15, 0.15) * (1 - t / 0.7))
    slurp, ph = [], 0.0
    for i in range(_n(0.6)):                                # SHLOOP: rising and wet
        t = i / RATE
        ph += math.tau * (120 + 500 * t + 60 * math.sin(t * 50)) / RATE
        slurp.append(math.sin(ph) * 0.4 * math.sin(math.pi * t / 0.6))
    slurp = [a + b for a, b in zip(slurp, swell(0.6, 0.3, 0.2))]
    pop = thump(300, 60, 0.3, 12, 0.7)
    pop = [a + b for a, b in zip(pop + [0.0] * _n(0.6), hiss(0.9, 4, 0.3, 0.3))]   # POP, then the splash
    miss = square(70, 0.18, 10, 0.25, 0.5, 0.2)
    riser, ph = [], 0.0
    for i in range(_n(0.5)):                                # the tempo kicks up a gear
        t = i / RATE
        ph += math.tau * (180 * 2 ** (t * 5)) / RATE
        riser.append((1 if math.sin(ph) > 0 else -1) * 0.16 * (t / 0.5) ** 0.5 * (1 - (t / 0.5) ** 6))
    cheer = []
    for j, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        cheer += square(f, 0.12, 6, 0.2, 0.25, 0.5)
    return {"scratch": _wav(scratch), "slurp": _wav(slurp), "pop": _wav(pop), "miss": _wav(miss),
            "fanfare": _wav(cheer), "tick": _wav(square(1318.5, 0.05, 40, 0.18, 0.25, 0.5)),
            "speedup": _wav(riser), **{f"moan_{k}": _wav(v) for k, v in moans().items()}}
