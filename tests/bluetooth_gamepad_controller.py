#!/usr/bin/env python3
"""Bluetooth gamepad input via pygame (SDL).

Produces the same ``gamepad_state`` dict as
``stretch_body.gamepad_controller.GamePadController`` so it can plug into
``stretch_body.gamepad_teleop.GamePadTeleop`` with the official joint mapping.

Pair the gamepad over Bluetooth first, then run ``test_gamepad_detect.py`` to
confirm axis and button layout on your controller.
"""

from __future__ import annotations

import threading
import time

try:
    import pygame
except ImportError as exc:
    raise ImportError(
        "pygame is required for Bluetooth gamepad support. "
        "Install with: python3 -m pip install pygame"
    ) from exc


# Default axis layout for Bluetooth Xbox-style controllers under pygame/SDL.
# Run test_gamepad_detect.py if sticks or triggers feel wrong on your pad.
BT_AXIS_MAP = {
    "left_stick_x": 0,
    "left_stick_y": 1,
    "right_stick_x": 3,
    "right_stick_y": 4,
    "left_trigger": 2,
    "right_trigger": 5,
}

# Pygame button index -> stretch gamepad_state key (Xbox layout).
BT_BUTTON_MAP = {
    0: "bottom_button_pressed",           # A
    1: "right_button_pressed",            # B
    2: "left_button_pressed",             # X
    3: "top_button_pressed",              # Y
    4: "left_shoulder_button_pressed",    # LB
    5: "right_shoulder_button_pressed",   # RB
    6: "select_button_pressed",           # Back / View
    7: "start_button_pressed",            # Start / Menu
    8: "left_stick_button_pressed",
    9: "right_stick_button_pressed",
    10: "middle_led_ring_button_pressed",  # Guide / Xbox (if exposed)
}

DEFAULT_STATE = {
    "middle_led_ring_button_pressed": False,
    "left_stick_x": 0.0,
    "left_stick_y": 0.0,
    "right_stick_x": 0.0,
    "right_stick_y": 0.0,
    "left_stick_button_pressed": False,
    "right_stick_button_pressed": False,
    "bottom_button_pressed": False,
    "top_button_pressed": False,
    "left_button_pressed": False,
    "right_button_pressed": False,
    "left_shoulder_button_pressed": False,
    "right_shoulder_button_pressed": False,
    "select_button_pressed": False,
    "start_button_pressed": False,
    "left_trigger_pulled": 0.0,
    "right_trigger_pulled": 0.0,
    "bottom_pad_pressed": False,
    "top_pad_pressed": False,
    "left_pad_pressed": False,
    "right_pad_pressed": False,
}

DEAD_ZONE = 0.08


def list_joysticks():
    """Return connected SDL joystick names and indices."""
    pygame.init()
    pygame.joystick.init()
    devices = []
    for index in range(pygame.joystick.get_count()):
        stick = pygame.joystick.Joystick(index)
        stick.init()
        devices.append((index, stick.get_name()))
    pygame.joystick.quit()
    pygame.quit()
    return devices


def _apply_dead_zone(value):
    if abs(value) < DEAD_ZONE:
        return 0.0
    return value


def _normalize_stick(value):
    return _apply_dead_zone(max(-1.0, min(1.0, value)))


def _normalize_trigger(value):
    """Convert pygame trigger range to Stretch's [0.0, 1.0] pulled value."""
    value = max(-1.0, min(1.0, value))
    if value < 0.0:
        return (value + 1.0) / 2.0
    return value


class BluetoothGamepadController(threading.Thread):
    """Threaded gamepad reader compatible with stretch_body GamePadTeleop."""

    def __init__(
        self,
        joystick_index=0,
        print_status=True,
        axis_map=None,
        button_map=None,
    ):
        super().__init__(name=self.__class__.__name__)
        self.daemon = True
        self.joystick_index = joystick_index
        self.print_status = print_status
        self.axis_map = dict(axis_map or BT_AXIS_MAP)
        self.button_map = dict(button_map or BT_BUTTON_MAP)

        self.lock = threading.Lock()
        self.stop_thread = False
        self.shutdown_flag = threading.Event()
        self.is_gamepad_dongle = False  # name kept for GamePadTeleop compatibility

        self._joystick = None
        self._poll_counter = 0
        self.gamepad_state = self.get_state()

    def run(self):
        clock = pygame.time.Clock()
        while not self.shutdown_flag.is_set() and not self.stop_thread:
            self.update()
            clock.tick(60)

        self._disconnect()

    def _connect(self):
        pygame.init()
        pygame.joystick.init()

        count = pygame.joystick.get_count()
        if count == 0:
            if self.print_status:
                print("Waiting for Bluetooth gamepad...")
            return False

        if self.joystick_index >= count:
            print(
                f"ERROR: Joystick index {self.joystick_index} out of range "
                f"(found {count} device(s)).",
            )
            return False

        self._joystick = pygame.joystick.Joystick(self.joystick_index)
        self._joystick.init()

        with self.lock:
            self.is_gamepad_dongle = True

        if self.print_status:
            print(
                f"Bluetooth gamepad connected: "
                f"[{self.joystick_index}] {self._joystick.get_name()}"
            )
        return True

    def _disconnect(self):
        if self._joystick is not None:
            self._joystick.quit()
            self._joystick = None
        pygame.joystick.quit()
        pygame.quit()

        with self.lock:
            self.is_gamepad_dongle = False
            self._set_zero_state_locked()

    def update(self):
        if self._joystick is None:
            if not self._connect():
                self._poll_counter += 1
                if self._poll_counter % 50 == 0 and self.print_status:
                    print("Waiting for Bluetooth gamepad...")
                with self.lock:
                    self._set_zero_state_locked()
                    self.gamepad_state = dict(self._state_locked())
                time.sleep(0.05)
            return

        pygame.event.pump()

        with self.lock:
            self._set_zero_state_locked()
            state = self._state_locked()

            for name, axis_index in self.axis_map.items():
                if axis_index >= self._joystick.get_numaxes():
                    continue
                raw = self._joystick.get_axis(axis_index)
                if name in ("left_stick_x", "right_stick_x"):
                    state[name] = _normalize_stick(raw)
                elif name in ("left_stick_y", "right_stick_y"):
                    state[name] = _normalize_stick(-raw)
                elif name == "left_trigger":
                    state["left_trigger_pulled"] = _normalize_trigger(raw)
                elif name == "right_trigger":
                    state["right_trigger_pulled"] = _normalize_trigger(raw)

            for button_index, state_key in self.button_map.items():
                if button_index >= self._joystick.get_numbuttons():
                    continue
                state[state_key] = bool(self._joystick.get_button(button_index))

            if self._joystick.get_numhats() > 0:
                hat_x, hat_y = self._joystick.get_hat(0)
                state["left_pad_pressed"] = hat_x == -1
                state["right_pad_pressed"] = hat_x == 1
                state["top_pad_pressed"] = hat_y == 1
                state["bottom_pad_pressed"] = hat_y == -1

            self.gamepad_state = dict(state)

    def _state_locked(self):
        return {
            key: (0.0 if "trigger" in key or "stick" in key else False)
            for key in DEFAULT_STATE
        }

    def _set_zero_state_locked(self):
        self.gamepad_state = self._state_locked()

    def get_state(self):
        with self.lock:
            return dict(self.gamepad_state)

    def stop(self):
        if not self.stop_thread:
            with self.lock:
                self.stop_thread = True
            self.shutdown_flag.set()
