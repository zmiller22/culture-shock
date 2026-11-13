"""Womb Rave's soundtrack and step chart, both generated from code.

The song is a 100 BPM chiptune: a square-wave bass and a lead that plays exactly on the notes you have to hit.
Contractions (a deep growl) are baked into the music as flavour; they aren't notes.

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
BPM = 100                        # the starting tempo (and the select-screen loop's)
BEAT = 60 / BPM
EIGHTH = BEAT / 2
BAR = BEAT * 4

# (kind of bar, how many). "count" is the count-in: no notes.
SECTIONS = [("count", 1), ("heart", 2), ("verse", 4), ("chorus", 4), ("break", 2),
            ("verse", 2), ("chorus", 4), ("push", 2)]
SONG = [kind for kind, n in SECTIONS for _ in range(n)]
# The song speeds up as it goes: bar index -> new tempo, each with a shout on screen.
TEMPO_CHANGES = {0: 100, 7: 105, 13: 110, 15: 115, 19: 120}
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
#   d = one stick direction   w = a contraction growl in the music (no note)
PATTERNS = {
    "count": [],
    "heart": [(0, "d"), (4, "d")],
    "verse": [(0, "d"), (2, "d"), (4, "d"), (6, "d")],
    "chorus": [(0, "dw"), (2, "d"), (4, "d"), (5, "d"), (6, "d")],
    "chorus2": [(0, "d"), (2, "d"), (3, "d"), (4, "dw"), (6, "d")],
    "break": [(0, "w"), (2, "d"), (4, "w"), (6, "d")],
    "push": [(0, "dw"), (2, "dw"), (4, "dw"), (6, "dw")],
}
CHART_SEED = 9

# Am - F - C - G, one chord per bar: (bass root Hz, chord tones for the lead)
CHORDS = [(110.0, (440.0, 523.25, 659.25)), (87.31, (349.23, 440.0, 523.25)),
          (130.81, (523.25, 659.25, 783.99)), (98.0, (392.0, 493.88, 587.33))]
MELODY = (0, 1, 2, 1, 2, 0, 1, 2)    # chord tone the lead plays at each eighth


@dataclass
class Note:
    t: float                    # seconds into the song when it should be hit
    lane: str                   # L R U D
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
            if "d" in what:
                ln = pick(t, eighth)
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
    """A contraction: a growl that sweeps down."""
    out, ph = [], 0.0
    for i in range(_n(length)):
        t = i / RATE
        ph += math.tau * (45 + 150 * math.exp(-t * 7)) / RATE
        s = math.sin(ph)
        out.append(max(-0.7, min(0.7, s * 1.6)) * math.exp(-t * 5) * amp * min(1, i / 80))
    return out


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
        if "w" in what:
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
# A small formant synth (Klatt-style): a glottal pulse with a little jitter and
# shimmer, plus breath that puffs with each cycle, through a cascade of four vowel
# resonators. Each sound starts on a breathy "h" and trails off into an exhale.

VOWELS = {                       # formant frequencies (Hz), F1..F4, female voice
    "mm": (270, 1150, 2500, 3500), "oo": (370, 950, 2670, 3600), "oh": (540, 920, 2710, 3700),
    "ah": (850, 1220, 2810, 3800), "uh": (760, 1400, 2780, 3700), "eh": (610, 2000, 2900, 3900),
}
BANDWIDTHS = (90, 110, 170, 250)
NASAL = {"mm": 1.0}              # how much each vowel is closed-mouth (muffled) 0..1


def _curve(points: list[tuple[float, float]], k: float) -> float:
    """Piecewise-linear value at k (0..1) through (k, value) points."""
    for (k0, v0), (k1, v1) in zip(points, points[1:]):
        if k <= k1:
            return v0 + (v1 - v0) * (k - k0) / max(1e-9, k1 - k0)
    return points[-1][1]


def _glottal(ph: float, open_q: float = 0.6) -> float:
    """Rosenberg glottal flow over one period (ph 0..1): open slowly, snap shut, rest."""
    rise, fall = open_q * 0.65, open_q * 0.35
    if ph < rise:
        return 0.5 * (1 - math.cos(math.pi * ph / rise))
    if ph < rise + fall:
        return math.cos(0.5 * math.pi * (ph - rise) / fall)
    return 0.0


def voice(length: float, pitch: list[tuple[float, float]], vowels: list[tuple[float, str]],
          amp: float = 0.5, breath: float = 0.25, vibrato: float = 0.02,
          env: list[tuple[float, float]] | None = None, onset: float = 0.06,
          exhale: float = 0.18, voiced: bool = True, scoop: float = 2.0,
          fry: float = 0.0) -> list[float]:
    """One breath of voice. pitch and vowels are (0..1 through the sound, value) points.
    onset: seconds of breathy "h" before the voice comes in; exhale: seconds of
    breath left after it stops. voiced=False is breath only (a gasp, a sigh).
    scoop: semitones below the note it slides up from; fry: seconds of croaky,
    crackly low voice (vocal fry) it trails off into at the end."""
    n_voice = _n(length)
    n_on, n_ex = _n(onset), _n(exhale)
    n = n_on + n_voice + n_ex
    env = env or [(0, 0), (0.12, 1), (0.75, 0.8), (1, 0)]
    rng = random.Random(round(length * 1000) + len(vowels))
    out = []
    ph = flow_prev = 0.0
    drift = drift_v = 0.0                                    # slow random pitch wander
    shimmer = cycle = 1.0
    n_fry = _n(fry)
    state = [[0.0, 0.0] for _ in range(4)]
    lp = noise_lp = 0.0
    for i in range(n):
        t = i / RATE
        k = min(1.0, max(0.0, (i - n_on) / n_voice))        # 0..1 through the voiced part
        if i < n_on:                                         # "h": breath swelling up
            v_amt, a_amt = 0.0, (i / max(1, n_on)) ** 0.5
            level = _curve(env, 0.08) * 0.9
        elif i < n_on + n_voice:
            v_amt = min(1.0, (i - n_on) / max(1, _n(0.04)))   # voicing fades in over 40 ms
            a_amt = 1.0
            level = _curve(env, k)
        else:                                                # exhale: breath, dying away
            e = (i - n_on - n_voice) / max(1, n_ex)
            v_amt, a_amt = 0.0, (1 - e) ** 2
            level = max(_curve(env, 0.85), 0.35) * 0.9
        if not voiced:
            v_amt = 0.0

        drift_v += rng.uniform(-1, 1) * 0.002 - drift_v * 0.002 - drift * 0.0005
        drift += drift_v * 0.01
        wob = math.sin(t * math.tau * (5.2 + 0.6 * math.sin(t * 1.7)))
        vib = vibrato * wob * min(1, k * 3)
        level *= 1 + 0.06 * wob * min(1, k * 3)              # tremor: loudness wavers with the pitch
        f0 = _curve(pitch, k) * (1 + vib + max(-0.03, min(0.03, drift)))
        f0 *= 2 ** (-scoop / 12 * max(0.0, 1 - (i - n_on) / _n(0.12)) ** 2)   # slide up into the note
        to_end = n_on + n_voice - i
        frying = n_fry and 0 < to_end < n_fry
        if frying:                                           # sag down into a croak
            fk = 1 - to_end / n_fry
            f0 = f0 * (1 - fk) + 75 * fk
        new_ph = ph + f0 * cycle / RATE
        if new_ph >= 1:                                      # a new cycle: a touch of shimmer (lots in fry)
            new_ph -= 1
            shimmer = 1 + rng.uniform(-0.08, 0.08)
            cycle = 1.0
            if frying:
                shimmer = 1 + rng.uniform(-0.45, 0.25)
                cycle = 1 + rng.uniform(-0.3, 0.3)
        ph = new_ph
        # louder means a tenser, brighter voice (shorter open phase); softer is breathier
        flow = _glottal(ph, 0.75 - 0.3 * level if not frying else 0.3)
        pulse = (flow - flow_prev) * RATE / (f0 * 4) * shimmer    # lips radiate the flow's slope
        flow_prev = flow
        noise_lp += (_noise.uniform(-1, 1) - noise_lp) * 0.5
        air = noise_lp * (0.35 + 0.65 * flow if v_amt else 1.0)   # breath puffs with each cycle
        breathiness = (breath + 0.15 * (1 - level)) * v_amt + (1 - v_amt) * 0.55
        src = pulse * v_amt * (1 - breath * 0.5) + air * breathiness * a_amt

        idx = max(j for j, (vk, _) in enumerate(vowels) if vk <= k or j == 0)
        if idx + 1 < len(vowels):
            (ka, va), (kb, vb) = vowels[idx], vowels[idx + 1]
            m = min(1.0, max(0.0, (k - ka) / max(1e-9, kb - ka)))
        else:
            va = vb = vowels[idx][1]
            m = 0.0
        y = src
        for j in range(4):                                   # cascade: unity gain at DC
            f = VOWELS[va][j] * (1 - m) + VOWELS[vb][j] * m
            r = math.exp(-math.pi * BANDWIDTHS[j] / RATE)
            c1, c2 = 2 * r * math.cos(math.tau * f / RATE), -r * r
            y = (1 - c1 - c2) * y + c1 * state[j][0] + c2 * state[j][1]
            state[j][1], state[j][0] = state[j][0], y
        nasal = NASAL.get(va, 0) * (1 - m) + NASAL.get(vb, 0) * m
        lp += (y - lp) * (0.12 + 0.88 * (1 - nasal))         # a closed mouth muffles it
        out.append(lp * amp * level)
    return out


def _room(snd: list[float], mix: float = 0.18, tail: float = 0.35) -> list[float]:
    """A small, soft room (Schroeder reverb): four combs into two allpasses."""
    dry = snd + [0.0] * _n(tail)
    wet = [0.0] * len(dry)
    for d_ms, g in ((29.7, 0.72), (37.1, 0.7), (41.1, 0.68), (43.7, 0.66)):
        d, buf = _n(d_ms / 1000), [0.0] * _n(d_ms / 1000)
        lp = 0.0
        for i, x in enumerate(dry):
            y = buf[i % d]
            lp += (y - lp) * 0.45                            # damp the highs as it bounces
            buf[i % d] = x + lp * g
            wet[i] += y
    for d_ms in (5.0, 1.7):
        d, buf = _n(d_ms / 1000), [0.0] * _n(d_ms / 1000)
        for i, x in enumerate(wet):
            b = buf[i % d]
            buf[i % d] = x + b * 0.5
            wet[i] = b - x * 0.5
    return [a + b * mix / 4 for a, b in zip(dry, wet)]


def moans() -> dict[str, list[float]]:
    """Moans for streaks, getting more worked up as the combo grows."""
    fall = [(0, 0), (0.1, 1), (0.6, 0.85), (1, 0)]
    short = [(0, 0), (0.12, 1), (0.5, 0.7), (1, 0)]
    gasp = voice(0.12, [(0, 300), (1, 300)], [(0, "ah"), (1, "ah")], amp=0.5, onset=0.08, exhale=0.0,
                 voiced=False, env=[(0, 0.4), (1, 1)])
    raw = {
        # warming up
        "mmm": voice(0.75, [(0, 200), (0.3, 235), (1, 190)], [(0, "mm"), (1, "mm")], amp=0.9,
                     breath=0.12, env=fall, onset=0.03, exhale=0.25, fry=0.15),
        "ooh": voice(0.65, [(0, 240), (0.4, 320), (1, 270)], [(0, "oo"), (0.6, "oh")], amp=0.8,
                     breath=0.2, env=fall, scoop=3),
        "oh": voice(0.38, [(0, 350), (1, 270)], [(0, "oh"), (1, "oh")], amp=0.8, env=short,
                    onset=0.04, exhale=0.15),
        "uhh": voice(0.65, [(0, 190), (1, 150)], [(0, "uh"), (1, "uh")], amp=0.85, breath=0.35,
                     env=fall, onset=0.08, exhale=0.3, fry=0.2),
        # into it
        "mmm-ahh": voice(0.95, [(0, 210), (0.4, 235), (0.55, 340), (1, 250)],
                         [(0, "mm"), (0.4, "mm"), (0.55, "ah"), (1, "ah")], amp=0.85, breath=0.2,
                         env=[(0, 0), (0.1, 0.7), (0.45, 0.7), (0.6, 1), (1, 0)], fry=0.12),
        "oh-yeah": voice(0.85, [(0, 310), (0.4, 260), (0.55, 360), (1, 280)],
                         [(0, "oh"), (0.4, "oh"), (0.55, "eh"), (0.75, "ah"), (1, "ah")], amp=0.8,
                         breath=0.2, env=fall, scoop=4, fry=0.1),
        "ah-ah": voice(0.28, [(0, 340), (1, 300)], [(0, "ah"), (1, "ah")], amp=0.8, env=short, exhale=0.06)
        + voice(0.5, [(0, 380), (0.3, 390), (1, 300)], [(0, "ah"), (1, "ah")], amp=0.85, env=fall,
                onset=0.03, breath=0.25, scoop=4, fry=0.12),
        # the big one
        "climax": gasp
        + voice(0.22, [(0, 320), (1, 340)], [(0, "ah"), (1, "ah")], amp=0.7, env=short, onset=0.02, exhale=0.05)
        + voice(0.24, [(0, 360), (1, 380)], [(0, "ah"), (1, "ah")], amp=0.8, env=short, onset=0.02, exhale=0.05)
        + gasp
        + voice(1.2, [(0, 420), (0.25, 480), (0.7, 420), (1, 290)], [(0, "ah"), (0.75, "ah"), (1, "oh")],
                amp=0.95, vibrato=0.045, breath=0.3, env=[(0, 0), (0.08, 1), (0.7, 0.9), (1, 0)],
                onset=0.02, exhale=0.4, scoop=5, fry=0.18),
        # when a big streak breaks
        "aww": voice(0.8, [(0, 320), (0.3, 300), (1, 160)], [(0, "ah"), (1, "oo")], amp=0.75,
                     breath=0.4, env=fall, exhale=0.3, scoop=0, fry=0.25),
    }
    out = {}
    for name, snd in raw.items():                            # all at the same loudness
        peak = max(abs(v) for v in snd) or 1.0
        out[name] = _room([v * 0.75 / peak for v in snd])
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
