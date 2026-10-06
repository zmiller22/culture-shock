"""Genes that only exist in the lab: they never occur in a "normal" creature,
but the splicer can graft them onto anything."""

import math

from ..canvas import Canvas
from ..palette import INK, MUTANT as P
from ..rig import Anchors, Arm, Head, Legs, Pose, Torso


def eyeball(c: Canvas, x: int, y: int, pose: Pose, iris: str = P["iris"]) -> None:
    """3x3 eyeball with its top-left at (x, y). Pupil darts around; blinks with the body."""
    if pose.blink:
        c.hline(x, x + 2, y + 1, P["flesh_dk"])
        return
    c.stamp(x, y, [".w.", "www", ".w."], {"w": P["eye_w"]})
    look = (1, 1, 0, 1)[pose.frame % 4]
    c.set(x + look, y + 1, iris)
    c.set(x + look + 1, y + 1, INK)


class TentacleLegs(Legs):
    species = "tentacle"
    length = 10

    def draw(self, c: Canvas, cx: int, hip: int, ground: int, pose: Pose) -> None:
        phase = 2 * math.pi * pose.frame / pose.n
        speed = 1.6 if pose.anim == "walk" else 0.8
        for j in range(4):
            back = j % 2 == 0
            base = cx - 3 + 2 * j
            end = cx - 8 + 5 * j
            col = P["tent_sh"] if back else P["tent"]
            pts = []
            for y in range(hip, ground + 1):
                t = (y - hip) / max(1, ground - hip)
                x = base + (end - base) * t + 1.3 * math.sin(t * 4 + phase * speed + j * 1.7) * t
                w = 3 if t < 0.35 else 2 if t < 0.75 else 1
                xi = round(x)
                c.hline(xi, xi + w - 1, y, col)
                pts.append((xi + w - 1, y))
            tip_x = round(end + 1.3 * math.sin(4 + phase * speed + j * 1.7))
            c.set(tip_x + (1 if j >= 2 else -1), ground, col)          # curled tip
            if not back:
                for x, y in pts[2::3]:
                    c.set(x, y, P["sucker"])


class BlobTorso(Torso):
    """A pulsing sack of flesh with a mouth where the belly button should be."""
    species = "blob"

    def draw(self, c: Canvas, cx: int, hip: int, pose: Pose) -> Anchors:
        pulse = 1 if pose.frame % 2 else 0
        top = hip - 13
        c.oval(cx - 8 - pulse, top - pulse, 16 + 2 * pulse, 15 + pulse, P["flesh"])
        c.oval(cx - 5, top + 1, 9, 5, P["flesh_hi"])
        c.oval(cx - 8, top + 8, 6, 6, P["flesh_sh"])
        for pts in (((cx - 6, top + 3), (cx - 3, top + 7), (cx - 4, top + 11)),
                    ((cx + 4, top + 2), (cx + 2, top + 5))):
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                c.line(x0, y0, x1, y1, P["vein"])
        # belly mouth
        mx, my = cx + 1, top + 9
        open_ = pose.frame % 2
        c.rect(mx, my, 6, 2 + open_, P["mouth"])
        for x in range(mx, mx + 6, 2):
            c.set(x, my, P["teeth"])
            c.set(x + 1, my + 1 + open_, P["teeth"])
        return Anchors(neck=(cx + 1, top + 1), shoulder=(cx - 2, top + 4), top=top, bottom=hip)


class BrainJarHead(Head):
    """Brain in a jar of glowing goo, screwed onto the neck with a metal collar."""
    species = "brain"

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        x0, y0 = nx - 5, ny - 13
        c.rect(nx - 4, ny - 2, 9, 3, P["metal"])
        c.hline(nx - 4, nx + 4, ny - 2, P["metal_hi"])
        c.set(nx - 3, ny - 1, P["metal_dk"])
        c.set(nx + 3, ny - 1, P["metal_dk"])
        c.oval(x0, y0, 11, 11, P["glass"])
        for y in range(y0 + 5, y0 + 11):                       # goo fills the bottom
            for x in range(x0, x0 + 11):
                if c.get(x, y) == P["glass"]:
                    c.set(x, y, P["fluid_dk"] if y > y0 + 8 else P["fluid"])
        bob = (0, 0, 1, 1)[pose.frame % 4]
        c.oval(x0 + 2, y0 + 3 + bob, 7, 5, P["brain"])
        c.line(x0 + 3, y0 + 4 + bob, x0 + 5, y0 + 5 + bob, P["brain_dk"])
        c.line(x0 + 5, y0 + 6 + bob, x0 + 7, y0 + 4 + bob, P["brain_dk"])
        c.vline(x0 + 5, y0 + 8 + bob, y0 + 9, P["brain_dk"])   # brain stem
        eyeball(c, x0 + 7, y0 + 5 + bob, pose, iris=P["iris_alt"])
        for i, bx in enumerate((x0 + 2, x0 + 8)):              # rising bubbles
            by = y0 + 9 - (pose.frame + 2 * i) % 4
            c.set(bx, by, P["glass_hi"])
        c.vline(x0 + 2, y0 + 2, y0 + 3, P["glass_hi"])         # glass glint
        c.set(x0 + 3, y0 + 1, P["glass_hi"])


class EyestalkHead(Head):
    """A knob of flesh sprouting three wobbly eyestalks."""
    species = "eyestalk"

    def draw(self, c: Canvas, nx: int, ny: int, pose: Pose) -> None:
        c.oval(nx - 4, ny - 5, 9, 7, P["flesh"])
        c.hline(nx - 2, nx + 2, ny - 4, P["flesh_hi"])
        c.hline(nx + 1, nx + 4, ny - 1, P["mouth"])           # drooling slit
        c.set(nx + 2, ny, P["teeth"])
        for k, (dx, h) in enumerate(((-3, 6), (0, 8), (3, 5))):
            sway = round(math.sin(2 * math.pi * pose.frame / pose.n + k * 2.1))
            bx, by = nx + dx, ny - 5
            tx, ty = bx + sway + (k - 1), by - h
            c.line(bx, by, tx, ty + 1, P["flesh_sh"])
            eyeball(c, tx - 1, ty - 2, pose)


class ClawArm(Arm):
    """Crustacean pincer. Snaps open and shut."""
    species = "claw"

    def draw(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        base, hi = (P["claw"], P["claw_hi"]) if front else (P["claw_sh"], P["claw"])
        dy = -pose.swing if front else pose.swing
        open_ = pose.frame % 2
        c.line(sx, sy, sx + 3, sy + 5 + dy, base, width=3)
        c.oval(sx + 3, sy + 3 + dy, 5, 5, base)
        c.line(sx + 7, sy + 4 + dy, sx + 10, sy + 2 + dy - open_, base, width=2)
        c.line(sx + 7, sy + 6 + dy, sx + 9, sy + 7 + dy + open_, base, width=2)
        c.set(sx + 4, sy + 4 + dy, hi)
        c.set(sx + 1, sy + 1, hi)
        for k in range(2):                                     # shell segments
            c.set(sx + 1 + k, sy + 2 + 2 * k, P["claw_sh"] if front else INK)


class TentacleArm(Arm):
    species = "tentacle"

    def draw(self, c: Canvas, sx: int, sy: int, pose: Pose, front: bool) -> None:
        col = P["tent"] if front else P["tent_sh"]
        phase = 2 * math.pi * pose.frame / pose.n
        for i in range(12):
            t = i / 11
            x = sx + round(9 * t)
            y = sy + round(4 * t + 2.2 * math.sin(t * 5 + phase))
            w = 2 if t < 0.6 else 1
            c.rect(x, y, 1, w, col)
            c.rect(x, y + 1, 1, w, col)
            if front and i % 3 == 1:
                c.set(x, y + w + 1 - 1, P["sucker"])
