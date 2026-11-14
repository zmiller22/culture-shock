"""WE KNOW LIFE STARTS WITH DNA: the lab's evidence board, by someone who has
completely misunderstood how it works.

A cork board bigger than the screen, covered in pinned cards, photos and notes,
with red yarn from every one of them to the card in the middle. The camera
reads its way round a few of them up close, then pulls back to show the whole
mess, and WE'RE PRETTY SURE. comes up.

    board = Board()
    board.update(dt)          # the camera
    board.draw(screen)        # the whole 320x180 screen
    board.skip()              # straight to the pulled-back view
    board.settled             # True once it's pulled back
"""

from __future__ import annotations

import math
import random

import pygame

from sprites.viewer import H, W, text_surface

BW, BH = 480, 270               # the board, in px (the screen is 320x180)
CORK, CORK_DARK, CORK_LIGHT = (150, 104, 62), (118, 80, 46), (176, 130, 84)
FRAME = (78, 50, 30)
INK = (34, 26, 40)
PAPER = (240, 234, 214)
NOTE = (255, 226, 92)
YARN, YARN_DARK = (214, 40, 40), (140, 20, 24)
PIN = (232, 59, 59)

CARD_W, CARD_H = 88, 60
CENTER = (BW // 2, BH // 2)
# where the camera stops to read, in board px (the middle of a 320x180 view), and for how long
TOUR = [((160, 90), 2.6), ((320, 90), 2.6), ((320, 180), 2.6), ((160, 180), 2.6)]
GLIDE = 0.7                      # s to glide between stops
PULL_BACK = 1.4                  # s to pull back to the whole board


def wrap(text: str, width: int) -> list[str]:
    from sprites.font import text_width
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and text_width(trial) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


# -- the little pictures on the cards (each draws into a 40x24 box, top-left at x, y) -----------
def _slide(s, x, y):
    pygame.draw.rect(s, (120, 120, 130), (x + 4, y + 2, 3, 22))                 # ladder
    for ry in range(y + 4, y + 22, 4):
        pygame.draw.line(s, (120, 120, 130), (x + 4, ry), (x + 10, ry))
    pygame.draw.rect(s, (120, 120, 130), (x + 10, y + 2, 2, 22))
    pts = [(x + 12 + 12 * math.sin(a / 3), y + 3 + a * 1.1) for a in range(0, 19)]   # the twisty bit
    pygame.draw.lines(s, (230, 180, 40), False, pts, 4)
    pygame.draw.lines(s, (250, 220, 90), False, pts, 1)


def _jeans(s, x, y):
    blue, dark = (64, 96, 170), (40, 60, 120)
    pygame.draw.rect(s, blue, (x + 12, y + 1, 18, 7))
    pygame.draw.polygon(s, blue, [(x + 12, y + 8), (x + 20, y + 8), (x + 19, y + 23), (x + 12, y + 23)])
    pygame.draw.polygon(s, blue, [(x + 22, y + 8), (x + 30, y + 8), (x + 30, y + 23), (x + 23, y + 23)])
    pygame.draw.line(s, dark, (x + 12, y + 3), (x + 29, y + 3))
    pygame.draw.line(s, (220, 180, 80), (x + 21, y + 4), (x + 21, y + 9))     # the zip


def _magnets(s, x, y):
    for i, (ch, col) in enumerate(zip("ATCG", ((232, 59, 59), (74, 163, 255), (255, 225, 77), (57, 211, 83)))):
        r = pygame.Rect(x + 1 + i * 10, y + 6 + (i % 2) * 4, 9, 11)
        pygame.draw.rect(s, col, r)
        pygame.draw.rect(s, INK, r, 1)
        img = text_surface(ch, "#221a28")
        s.blit(img, (r.x + 3, r.y + 3))


def _banana(s, x, y):
    pts = [(x + 6 + i, y + 8 + 10 * math.sin(i / 28 * math.pi)) for i in range(0, 29, 2)]
    inner = [(px, py - 6) for px, py in pts]
    pygame.draw.polygon(s, (250, 214, 60), pts + inner[::-1])
    pygame.draw.lines(s, (150, 110, 20), False, pts, 1)
    pygame.draw.rect(s, (90, 60, 20), (x + 4, y + 2, 3, 3))


def _hubcap(s, x, y):
    c = (x + 20, y + 12)
    pygame.draw.circle(s, (90, 90, 100), c, 11)
    pygame.draw.circle(s, (200, 200, 210), c, 10)
    for a in range(0, 360, 60):
        r = math.radians(a)
        pygame.draw.line(s, (130, 130, 140), c, (c[0] + 9 * math.cos(r), c[1] + 9 * math.sin(r)), 2)
    pygame.draw.circle(s, (250, 250, 255), c, 3)


def _cousin(s, x, y):
    pygame.draw.rect(s, (110, 150, 200), (x + 8, y, 24, 24))                  # school photo backdrop
    pygame.draw.circle(s, (230, 180, 140), (x + 20, y + 10), 7)
    pygame.draw.rect(s, (60, 40, 30), (x + 13, y + 3, 14, 4))                 # bowl cut
    pygame.draw.circle(s, INK, (x + 17, y + 11), 2, 1)                        # glasses
    pygame.draw.circle(s, INK, (x + 23, y + 11), 2, 1)
    pygame.draw.rect(s, (200, 60, 60), (x + 12, y + 18, 16, 6))               # sweater


def _ancestry(s, x, y):
    c = (x + 20, y + 12)
    pygame.draw.circle(s, (120, 120, 140), c, 10)                            # 98%: disappointment
    pygame.draw.polygon(s, (214, 40, 40), [c, (c[0] + 10, c[1]), (c[0] + 10, c[1] - 2)])   # 2%: viking
    pygame.draw.circle(s, INK, c, 10, 1)


def _locker(s, x, y):
    r = pygame.Rect(x + 10, y, 20, 24)
    pygame.draw.rect(s, (90, 120, 150), r)
    pygame.draw.rect(s, INK, r, 1)
    for vy in range(y + 3, y + 9, 2):
        pygame.draw.line(s, INK, (x + 13, vy), (x + 27, vy))
    s.blit(text_surface("46", "#f0eadc"), (x + 15, y + 13))


def _family(s, x, y):
    pygame.draw.rect(s, (160, 200, 150), (x + 2, y, 36, 24))                  # backyard
    for i, (fx, h) in enumerate(((10, 9), (20, 10), (30, 7))):
        pygame.draw.circle(s, (230, 180, 140), (x + fx, y + 24 - h - 5), 4)
        pygame.draw.rect(s, (90, 90, 160), (x + fx - 3, y + 24 - h, 7, h))
        if i == 0:                                                            # mom: eyes cut out
            pygame.draw.rect(s, CORK_DARK, (x + fx - 3, y + 24 - h - 7, 7, 2))


# (board x, y of the card's middle, picture, caption, how far it's knocked off level in px, card colour)
# (not rotated: turning pixel text garbles it, so they sit a little crooked instead)
CARDS = [
    (62, 48, _slide, "DOUBLE HELIX IS A TWISTY SLIDE??", -2, PAPER),
    (176, 40, _jeans, "GENES. JEANS. COINCIDENCE?", 2, PAPER),
    (304, 44, _magnets, "ALL THE CATS GO... WHERE??", -1, PAPER),
    (420, 52, _banana, "BANANAS SHARE 60% OF YOUR DNA. WHICH 60%", 3, PAPER),
    (58, 140, _hubcap, "CHROME-OSOMES", 2, PAPER),
    (424, 140, None, "MITOCHONDRIA IS THE POWERHOUSE OF THE CELL", -3, NOTE),
    (66, 224, _cousin, "RNA. DNA'S COUSIN. SUSPICIOUS.", -2, PAPER),
    (178, 230, _ancestry, "ANCESTRY TEST: 2% VIKING. 98% DISAPPOINTMENT", 1, PAPER),
    (302, 228, _locker, "46 CHROMOSOMES. MY LOCKER WAS 46", -2, PAPER),
    (418, 226, _family, "I HAVE MY MOM'S EYES. WHERE ARE HERS", 2, PAPER),
]
SCRAWL = [(110, 90, "WAKE UP"), (350, 92, "?!?"), (104, 175, "THEY KNOW"), (296, 175, "ALL CONNECTED")]


def _card(pic, caption: str, colour) -> pygame.Surface:
    card = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    pygame.draw.rect(card, (0, 0, 0, 70), (2, 2, CARD_W - 2, CARD_H - 2))      # shadow
    pygame.draw.rect(card, colour, (0, 0, CARD_W - 2, CARD_H - 2))
    pygame.draw.rect(card, (180, 170, 150) if colour == PAPER else (210, 170, 40), (0, 0, CARD_W - 2, CARD_H - 2), 1)
    text_top = 6
    if pic:
        pic(card, (CARD_W - 2) // 2 - 20, 5)
        text_top = 33
    lines = wrap(caption, CARD_W - 10)
    if not pic:                                                               # the note: big circles round it
        text_top = (CARD_H - 2 - len(lines) * 7) // 2
        for k in range(3):
            pygame.draw.ellipse(card, (214, 40, 40), (3 + k, text_top - 6 + k, CARD_W - 8 - 2 * k,
                                                      len(lines) * 7 + 11 - 2 * k), 1)
    for i, line in enumerate(lines):
        img = text_surface(line, "#221a28")
        card.blit(img, ((CARD_W - 2) // 2 - img.get_width() // 2, text_top + i * 7))
    return card


def _pin(s, x, y):
    pygame.draw.circle(s, (60, 10, 10), (x + 1, y + 1), 3)
    pygame.draw.circle(s, PIN, (x, y), 3)
    s.set_at((x - 1, y - 1), (255, 170, 160))


def _yarn(s, a, b):
    """Red yarn from a to b, sagging a little in the middle."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 6
    pts = [a, (mx, my), b]
    pygame.draw.lines(s, YARN_DARK, False, [(px + 1, py + 1) for px, py in pts], 1)
    pygame.draw.lines(s, YARN, False, pts, 1)


def build_board(seed: int = 7) -> pygame.Surface:
    rng = random.Random(seed)
    s = pygame.Surface((BW, BH))
    s.fill(CORK)
    for _ in range(2600):                                                     # cork speckle
        s.set_at((rng.randrange(BW), rng.randrange(BH)), rng.choice((CORK_DARK, CORK_LIGHT)))
    pygame.draw.rect(s, FRAME, (0, 0, BW, BH), 6)
    pygame.draw.rect(s, (110, 74, 44), (6, 6, BW - 12, BH - 12), 1)
    for x, y, text in SCRAWL:                                                 # marker on the cork
        img = text_surface(text, "#c81e1e")
        s.blit(pygame.transform.rotate(pygame.transform.scale_by(img, 2), rng.uniform(-8, 8)), (x, y))
    pins = [(x, y - CARD_H // 2 + 4 + tilt) for x, y, _, _, tilt, _ in CARDS]
    centre_pin = (CENTER[0], CENTER[1] - 20)
    for p in pins:                                                            # everything's connected
        _yarn(s, p, centre_pin)
    for a, b in ((0, 1), (1, 3), (4, 6), (7, 8), (2, 5), (5, 9)):             # and to each other, somehow
        _yarn(s, pins[a], pins[b])
    for x, y, pic, caption, tilt, colour in CARDS:                            # the cards hang over the yarn
        card = _card(pic, caption, colour)
        s.blit(card, (x - CARD_W // 2, y - CARD_H // 2 + tilt))
    # the middle of it all
    mid = pygame.Surface((110, 46), pygame.SRCALPHA)
    pygame.draw.rect(mid, (0, 0, 0, 70), (2, 2, 108, 44))
    pygame.draw.rect(mid, PAPER, (0, 0, 108, 44))
    pygame.draw.rect(mid, (214, 40, 40), (0, 0, 108, 44), 2)
    w = text_surface("THE TRUTH", "#c81e1e")
    mid.blit(w, (54 - w.get_width() // 2, 12))
    img = text_surface("SPIT->JAR->???->YOU", "#221a28")
    mid.blit(img, (54 - img.get_width() // 2, 26))
    s.blit(mid, (CENTER[0] - 55, CENTER[1] - 23))
    for p in pins + [centre_pin]:
        _pin(s, *p)
    return s


_BOARD: pygame.Surface | None = None


class Board:
    def __init__(self) -> None:
        global _BOARD
        _BOARD = _BOARD or build_board()
        self.surf = _BOARD
        self.t = 0.0
        self.length = sum(h for _, h in TOUR) + GLIDE * (len(TOUR) - 1)

    @property
    def settled(self) -> bool:
        return self.t >= self.length + PULL_BACK

    @property
    def since_settled(self) -> float:
        return self.t - (self.length + PULL_BACK)

    def skip(self) -> None:
        self.t = max(self.t, self.length + PULL_BACK)

    def update(self, dt: float) -> None:
        self.t += dt

    def _view(self) -> tuple[float, float, float]:
        """Camera middle (board px) and zoom (1 = one board px per screen px)."""
        t = self.t
        for i, ((x, y), hold) in enumerate(TOUR):
            if t < hold:
                return x, y, 1.0
            t -= hold
            if i == len(TOUR) - 1:
                break
            if t < GLIDE:
                k = t / GLIDE
                k = k * k * (3 - 2 * k)
                (nx, ny), _ = TOUR[i + 1]
                return x + (nx - x) * k, y + (ny - y) * k, 1.0
            t -= GLIDE
        k = min(1.0, t / PULL_BACK)
        k = k * k * (3 - 2 * k)
        (x, y), _ = TOUR[-1]
        zoom = 1.0 + (W / BW - 1.0) * k
        return x + (BW / 2 - x) * k, y + (BH / 2 - y) * k, zoom

    def draw(self, screen: pygame.Surface) -> None:
        cx, cy, zoom = self._view()
        vw, vh = W / zoom, H / zoom
        r = pygame.Rect(round(cx - vw / 2), round(cy - vh / 2), round(vw), round(vh))
        r.clamp_ip(self.surf.get_rect())
        view = self.surf.subsurface(r)
        if r.size == (W, H):
            screen.blit(view, (0, 0))
        else:                                       # pulled back: smooth, so the scrawl blurs rather than breaks
            pygame.transform.smoothscale(view, (W, H), screen)
