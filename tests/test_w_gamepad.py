#!/usr/bin/env python3
"""Stretch gamepad teleop test using a Bluetooth gamepad.

Uses the same joint mapping as the official ``stretch_gamepad_teleop.py``
(``stretch_body.gamepad_teleop.GamePadTeleop``), but reads input through
pygame/SDL instead of the Hello Robot USB dongle.

Requirements:
  - Robot homed: ``stretch_robot_home.py``
  - pygame: ``python3 -m pip install pygame``
  - Gamepad paired over Bluetooth

Quick start:
  python3 test_gamepad_detect.py --list
  python3 test_gamepad_detect.py
  python3 test_w_gamepad.py --profile 8bitdo

Mapping (matches official gamepad teleop):
  Left stick                 base tank drive
  Right stick X / Y          arm / lift
  LB / RB                    wrist yaw
  D-pad                      head pan/tilt
  Left trigger (hold)        precision mode
  Right trigger (hold)       fast base mode
  A / B                      gripper close / open
  X                          toggle D-pad head vs dex wrist (if installed)
  Y (hold 2 s)               stow
  Start                      home if not calibrated

This test script disables the official long-press Back PC shutdown behavior.
Keep the runstop within reach.
"""

from __future__ import annotations

import argparse
import sys
import time

import stretch_body.gamepad_teleop as gamepad_teleop_module

from bluetooth_gamepad_controller import BluetoothGamepadController, list_joysticks


HELP = """
Stretch Bluetooth gamepad control test

Official mapping (stretch_gamepad_teleop.py):
  Left stick            drive base
  Right stick X         arm
  Right stick Y         lift
  LB / RB               wrist yaw left / right
  D-pad                 head pan/tilt
  Left trigger (hold)   precision mode
  Right trigger (hold)  fast base mode
  A / B                 gripper close / open
  X                     toggle D-pad target (head vs dex wrist)
  Y (hold 2 s)          stow robot
  Start                 home robot if not calibrated

Long-press Back is disabled in this test script (no PC shutdown).
Press Ctrl+C to quit.
"""


class BluetoothGamePadTeleop(gamepad_teleop_module.GamePadTeleop):
    """GamePadTeleop with a pygame-based Bluetooth controller."""

    def __init__(
        self,
        joystick_index=0,
        print_status=True,
        collision_mgmt=True,
        profile="auto",
    ):
        super().__init__(
            robot_instance=True,
            print_dongle_status=False,
            collision_mgmt=collision_mgmt,
        )
        self.gamepad_controller = BluetoothGamepadController(
            joystick_index=joystick_index,
            print_status=print_status,
            profile=profile,
        )
        self.controller_state = self.gamepad_controller.gamepad_state

    def manage_shutdown(self, robot):
        """Disable the official long-press Back PC shutdown in test mode."""
        if self.controller_state["select_button_pressed"]:
            if not self._last_shutdwon_btn_press:
                self._last_shutdwon_btn_press = time.time()
            if time.time() - self._last_shutdwon_btn_press >= 2:
                print(
                    "\nLong Back press ignored "
                    "(PC shutdown disabled in test_w_gamepad.py)."
                )
                self._last_shutdwon_btn_press = None
        else:
            self._last_shutdwon_btn_press = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Teleoperate Stretch with a Bluetooth gamepad.",
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
        help="Joystick index to use (default: 0).",
    )
    parser.add_argument(
        "--no-collision-mgmt",
        action="store_true",
        help="Disable stretch_body collision management.",
    )
    parser.add_argument(
        "--profile",
        default="auto",
        choices=["auto", "xbox", "8bitdo_lite2"],
        help="Controller mapping profile (default: auto-detect).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list:
        devices = list_joysticks()
        if not devices:
            print("No gamepads detected.")
            return 1
        print("Detected gamepads:")
        for index, name in devices:
            print(f"  [{index}] {name}")
        return 0

    print("Starting Stretch Bluetooth gamepad test...")
    print(HELP)

    teleop = BluetoothGamePadTeleop(
        joystick_index=args.index,
        print_status=True,
        collision_mgmt=not args.no_collision_mgmt,
        profile=args.profile,
    )

    teleop.startup()

    if not teleop.robot.is_calibrated():
        print(
            "WARNING: Robot is not calibrated. "
            "Press Start on the gamepad to home, or run stretch_robot_home.py.",
            file=sys.stderr,
        )

    try:
        teleop.mainloop()
        return 0
    except KeyboardInterrupt:
        print("\nGamepad test interrupted.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        teleop.stop()


if __name__ == "__main__":
    sys.exit(main())
