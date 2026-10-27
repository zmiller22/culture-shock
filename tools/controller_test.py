"""Controller tester (pygame-ce). Checks that the arcade encoders, sticks and
buttons are wired up and reach the game.

    python3 tools/controller_test.py [--headless]

Every pad is listed on start-up and every input event is logged to the terminal.
The window draws each pad's stick position plus a row of button lamps that light
while held. --headless skips the window (e.g. over SSH) and only logs.

Hot-plugging is reported, so wiggling the USB cable shows a loose connection.
ESC / Q / Ctrl+C quits.
"""

from __future__ import annotations

import argparse
import os

# Keep receiving joystick events when the window isn't focused (or doesn't exist).
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame

W = 640
PAD_H = 170
BG, DIM, TEXT, LIT = (20, 20, 24), (60, 60, 70), (220, 220, 220), (90, 220, 120)
DEADZONE = 0.05
AXIS_LOG = 0.5           # log an axis only when it crosses into a new -1/0/+1 zone
_axis_zone: dict[tuple[int, int], int] = {}


def describe(joy: pygame.joystick.JoystickType) -> str:
    return (f"[{joy.get_instance_id()}] {joy.get_name()!r}  guid={joy.get_guid()}  "
            f"axes={joy.get_numaxes()} buttons={joy.get_numbuttons()} hats={joy.get_numhats()}")


def log_event(e: pygame.event.Event) -> None:
    if e.type == pygame.JOYAXISMOTION:
        # Encoders often have unwired axes that float with noise; ignore jitter.
        zone = (e.value > AXIS_LOG) - (e.value < -AXIS_LOG)
        if _axis_zone.get((e.instance_id, e.axis), 0) != zone:
            _axis_zone[(e.instance_id, e.axis)] = zone
            print(f"pad {e.instance_id}  axis {e.axis}  {e.value:+.2f}")
    elif e.type == pygame.JOYBUTTONDOWN:
        print(f"pad {e.instance_id}  button {e.button}  DOWN")
    elif e.type == pygame.JOYBUTTONUP:
        print(f"pad {e.instance_id}  button {e.button}  up")
    elif e.type == pygame.JOYHATMOTION:
        print(f"pad {e.instance_id}  hat {e.hat}  {e.value}")


def draw_pad(screen: pygame.Surface, font: pygame.font.Font, joy, top: int) -> None:
    screen.blit(font.render(f"P{joy.get_instance_id() + 1}  {joy.get_name()}", True, TEXT), (12, top + 8))

    # Stick: axes 0/1 if present, overridden by hat 0 when it's pushed.
    x = joy.get_axis(0) if joy.get_numaxes() > 0 else 0.0
    y = joy.get_axis(1) if joy.get_numaxes() > 1 else 0.0
    if joy.get_numhats() and joy.get_hat(0) != (0, 0):
        hx, hy = joy.get_hat(0)
        x, y = hx, -hy
    box = pygame.Rect(12, top + 34, 120, 120)
    pygame.draw.rect(screen, DIM, box, 2)
    pygame.draw.line(screen, DIM, box.midtop, box.midbottom)
    pygame.draw.line(screen, DIM, box.midleft, box.midright)
    dot = (box.centerx + x * 55, box.centery + y * 55)
    pygame.draw.circle(screen, LIT if (abs(x) > DEADZONE or abs(y) > DEADZONE) else TEXT, dot, 8)
    screen.blit(font.render(f"x {x:+.2f}  y {y:+.2f}", True, TEXT), (box.right + 12, box.bottom - 18))

    # Button lamps, 8 per row, labelled with the index the game will see.
    for b in range(joy.get_numbuttons()):
        cx = box.right + 30 + (b % 8) * 56
        cy = top + 50 + (b // 8) * 50
        held = joy.get_button(b)
        pygame.draw.circle(screen, LIT if held else DIM, (cx, cy), 18)
        label = font.render(str(b), True, BG if held else TEXT)
        screen.blit(label, label.get_rect(center=(cx, cy)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--headless", action="store_true", help="no window, just log events")
    args = ap.parse_args()

    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.joystick.init()

    pads: dict[int, pygame.joystick.JoystickType] = {}
    print(f"{pygame.joystick.get_count()} controller(s) detected at start-up")

    screen = font = None
    if not args.headless:
        screen = pygame.display.set_mode((W, PAD_H * 2))
        pygame.display.set_caption("Controller test")
        font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    try:
        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.type == pygame.JOYDEVICEADDED:
                    joy = pygame.joystick.Joystick(e.device_index)
                    pads[joy.get_instance_id()] = joy
                    print("ADDED   " + describe(joy))
                elif e.type == pygame.JOYDEVICEREMOVED:
                    joy = pads.pop(e.instance_id, None)
                    print(f"REMOVED [{e.instance_id}] {joy.get_name() if joy else ''}")
                else:
                    log_event(e)

            if screen:
                screen.fill(BG)
                if not pads:
                    screen.blit(font.render("No controllers. Plug in an encoder.", True, TEXT), (12, 12))
                for i, joy in enumerate(sorted(pads.values(), key=lambda j: j.get_instance_id())):
                    draw_pad(screen, font, joy, i * PAD_H)
                pygame.display.flip()
            clock.tick(60)
    except KeyboardInterrupt:
        pass
    pygame.quit()


if __name__ == "__main__":
    main()
