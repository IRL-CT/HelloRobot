#!/usr/bin/env python3
"""Detect and inspect a Bluetooth (or any SDL-visible) gamepad.

Use this before ``test_w_gamepad.py`` to confirm pairing and axis layout.

Examples:
  python3 test_gamepad_detect.py --list
  python3 test_gamepad_detect.py
  python3 test_gamepad_detect.py --profile 8bitdo
"""

from __future__ import annotations

import argparse
import sys
import time

from bluetooth_gamepad_controller import (
    DEFAULT_STATE,
    _normalize_stick,
    _normalize_trigger,
    detect_profile,
    get_profile,
    list_joysticks,
    list_profiles,
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

8BitDo Lite 2 notes:
  - Set the rear switch to D mode before pairing with Ubuntu.
  - Right stick Y controls lift; L2/R2 act as precision / fast-base buttons.

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
        suggested = detect_profile(name)
        print(f"  [{index}] {name}  (suggested profile: {suggested})")
    return 0


def map_state(stick, profile_name):
    profile = get_profile(profile_name)
    axis_map = profile["axis_map"]
    button_map = profile["button_map"]
    trigger_buttons = profile.get("trigger_buttons", {})

    mapped = dict(DEFAULT_STATE)

    for name, axis_index in axis_map.items():
        if axis_index >= stick.get_numaxes():
            continue
        raw = stick.get_axis(axis_index)
        if name in ("left_stick_x", "right_stick_x"):
            mapped[name] = _normalize_stick(raw)
        elif name in ("left_stick_y", "right_stick_y"):
            mapped[name] = _normalize_stick(-raw)
        elif name == "left_trigger":
            mapped["left_trigger_pulled"] = _normalize_trigger(raw)
        elif name == "right_trigger":
            mapped["right_trigger_pulled"] = _normalize_trigger(raw)

    for button_index, state_key in button_map.items():
        if button_index < stick.get_numbuttons():
            mapped[state_key] = bool(stick.get_button(button_index))

    for button_index, trigger_key in trigger_buttons.items():
        if button_index < stick.get_numbuttons() and stick.get_button(button_index):
            mapped[trigger_key] = 1.0

    if stick.get_numhats() > 0:
        hat_x, hat_y = stick.get_hat(0)
        mapped["left_pad_pressed"] = hat_x == -1
        mapped["right_pad_pressed"] = hat_x == 1
        mapped["top_pad_pressed"] = hat_y == 1
        mapped["bottom_pad_pressed"] = hat_y == -1

    return mapped


def run_monitor(joystick_index, profile_name):
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
    device_name = stick.get_name()

    if profile_name == "auto":
        profile_name = detect_profile(device_name)

    print(HELP)
    print(f"Using [{joystick_index}] {device_name}")
    print(f"Profile: {profile_name} ({get_profile(profile_name)['label']})")
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
            mapped = map_state(stick, profile_name)

            print(
                f"\rAxes [{', '.join(axis_values)}]  "
                f"Buttons [{', '.join(button_values) or 'none'}]  "
                f"Hat {hat_value}  "
                f"Base ({mapped['left_stick_x']:+.2f}, {mapped['left_stick_y']:+.2f})  "
                f"Lift {mapped['right_stick_y']:+.2f}",
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
    parser.add_argument(
        "--profile",
        default="auto",
        choices=["auto", "xbox", "8bitdo"],
        help="Controller mapping profile (default: auto-detect).",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available mapping profiles and exit.",
    )
    args = parser.parse_args()

    if args.list_profiles:
        print("Available profiles:")
        for name, label in list_profiles().items():
            print(f"  {name}: {label}")
        return 0

    if args.list:
        return print_device_list()

    return run_monitor(args.index, args.profile)


if __name__ == "__main__":
    sys.exit(main())
