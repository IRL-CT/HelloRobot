#!/usr/bin/env python3
"""Detect and inspect a Bluetooth (or any SDL-visible) gamepad.

Use this before ``test_w_gamepad.py`` to confirm pairing and axis layout.

Examples:
  python3 test_gamepad_detect.py --list
  python3 test_gamepad_detect.py
  python3 test_gamepad_detect.py --index 0
"""

from __future__ import annotations

import argparse
import sys
import time

from bluetooth_gamepad_controller import (
    BT_AXIS_MAP,
    BT_BUTTON_MAP,
    DEFAULT_STATE,
    list_joysticks,
)


HELP = """
Stretch Bluetooth gamepad detector

This prints raw pygame axis/button values and the mapped Stretch gamepad state.
Use it to verify your controller is paired and that sticks, triggers, and the
D-pad match the official stretch_gamepad_teleop mapping.

Official mapping (same as stretch_gamepad_teleop.py):
  Left stick            base drive (forward/back + rotate)
  Right stick X         arm extend/retract
  Right stick Y         lift up/down
  LB / RB               wrist yaw
  D-pad                 head pan/tilt (or dex wrist when toggled)
  Left trigger (hold)   precision mode
  Right trigger (hold)  fast base mode (when arm/lift stowed)
  A / B                 gripper close / open (if gripper installed)
  X                     toggle D-pad between head and dex wrist
  Y (hold 2 s)          stow robot
  Start                 home robot if not calibrated
  Back (hold 2 s)       ignored in test_w_gamepad.py (no PC shutdown)

Press Ctrl+C to exit.
"""


def print_device_list():
    devices = list_joysticks()
    if not devices:
        print("No gamepads detected.")
        print("Pair your controller over Bluetooth, then run this again.")
        return 1

    print("Detected gamepads:")
    for index, name in devices:
        print(f"  [{index}] {name}")
    return 0


def run_monitor(joystick_index):
    try:
        import pygame
    except ImportError:
        print(
            "ERROR: pygame is not installed. "
            "Install with: python3 -m pip install pygame",
            file=sys.stderr,
        )
        return 1

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("ERROR: No gamepad detected.", file=sys.stderr)
        print("Pair your controller over Bluetooth first.", file=sys.stderr)
        return 1

    if joystick_index >= pygame.joystick.get_count():
        print(
            f"ERROR: Index {joystick_index} out of range "
            f"(found {pygame.joystick.get_count()} device(s)).",
            file=sys.stderr,
        )
        return 1

    stick = pygame.joystick.Joystick(joystick_index)
    stick.init()

    print(HELP)
    print(f"Using [{joystick_index}] {stick.get_name()}")
    print(f"Axes: {stick.get_numaxes()}  Buttons: {stick.get_numbuttons()}  "
          f"Hats: {stick.get_numhats()}")
    print("-" * 72)

    try:
        while True:
            pygame.event.pump()

            axis_values = [
                f"{idx}:{stick.get_axis(idx):+.2f}"
                for idx in range(stick.get_numaxes())
            ]
            button_values = [
                f"{idx}"
                for idx in range(stick.get_numbuttons())
                if stick.get_button(idx)
            ]
            hat_value = stick.get_hat(0) if stick.get_numhats() > 0 else (0, 0)

            mapped = dict(DEFAULT_STATE)
            for name, axis_index in BT_AXIS_MAP.items():
                if axis_index >= stick.get_numaxes():
                    continue
                raw = stick.get_axis(axis_index)
                if name.endswith("_x"):
                    mapped[name] = raw
                elif name.endswith("_y"):
                    mapped[name] = -raw
                elif name == "left_trigger":
                    mapped["left_trigger_pulled"] = raw
                elif name == "right_trigger":
                    mapped["right_trigger_pulled"] = raw

            for button_index, state_key in BT_BUTTON_MAP.items():
                if button_index < stick.get_numbuttons():
                    mapped[state_key] = bool(stick.get_button(button_index))

            if stick.get_numhats() > 0:
                mapped["left_pad_pressed"] = hat_value[0] == -1
                mapped["right_pad_pressed"] = hat_value[0] == 1
                mapped["top_pad_pressed"] = hat_value[1] == 1
                mapped["bottom_pad_pressed"] = hat_value[1] == -1

            print(
                f"\rAxes [{', '.join(axis_values)}]  "
                f"Buttons [{', '.join(button_values) or 'none'}]  "
                f"Hat {hat_value}  "
                f"Base stick ({mapped['left_stick_x']:+.2f}, "
                f"{mapped['left_stick_y']:+.2f})",
                end="",
                flush=True,
            )
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nDetector stopped.")
        return 0

    finally:
        stick.quit()
        pygame.joystick.quit()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect a Bluetooth gamepad for Stretch teleop.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List connected gamepads and exit.",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Joystick index to monitor (default: 0).",
    )
    args = parser.parse_args()

    if args.list:
        return print_device_list()

    return run_monitor(args.index)


if __name__ == "__main__":
    sys.exit(main())
