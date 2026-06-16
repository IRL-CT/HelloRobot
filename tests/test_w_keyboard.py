#!/usr/bin/env python3

import math
import select
import sys
import termios
import time
import tty

import stretch_body.robot


LINEAR_SPEED_MPS = 0.05
ROTATION_SPEED_RAD_S = 0.20
COMMAND_TIMEOUT_S = 0.30
LOOP_PERIOD_S = 0.05

LIFT_STEP_M = 0.01
ARM_STEP_M = 0.01
WRIST_STEP_RAD = math.radians(10)
HEAD_PAN_STEP_RAD = math.radians(5)
HEAD_TILT_STEP_RAD = math.radians(5)


HELP = """
Stretch keyboard control test

Base:
    W / Up Arrow      forward
    S / Down Arrow    backward
    A / Left Arrow    rotate counterclockwise
    D / Right Arrow   rotate clockwise
    Space or X        stop base

Lift:
    R                 up
    F                 down

Arm:
    T                 extend
    G                 retract

Wrist:
    Z                 yaw counterclockwise
    V                 yaw clockwise

Head / camera:
    J                 pan left
    L                 pan right
    I                 tilt up
    K                 tilt down

Capture:
    P                 save RGB and depth images

    Q                 stop base and quit

Base commands stop automatically when no movement key is received.
Keep the runstop within reach.
"""


def read_key(timeout):
    """Read one key or arrow-key sequence without blocking indefinitely."""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)

    if not ready:
        return None

    first = sys.stdin.read(1)

    # Arrow keys arrive as three-character escape sequences.
    if first == "\x1b":
        sequence = first

        for _ in range(2):
            ready, _, _ = select.select([sys.stdin], [], [], 0.01)
            if ready:
                sequence += sys.stdin.read(1)

        return sequence

    return first


def send_velocity(robot, linear, angular):
    robot.base.set_velocity(linear, angular)
    robot.push_command()


def move_lift(robot, delta_m):
    robot.lift.move_by(delta_m)
    robot.push_command()


def move_arm(robot, delta_m):
    robot.arm.move_by(delta_m)
    robot.push_command()


def move_wrist(robot, delta_rad):
    robot.end_of_arm.move_by("wrist_yaw", delta_rad)
    robot.push_command()


def move_head_pan(robot, delta_rad):
    robot.head.move_by("head_pan", delta_rad)


def move_head_tilt(robot, delta_rad):
    robot.head.move_by("head_tilt", delta_rad)


class CameraCapture:
    """Lazy RealSense capture used by the P key."""

    def __init__(self):
        self._pipeline = None
        self._cv2 = None
        self._np = None

    def _ensure_started(self):
        if self._pipeline is not None:
            return True

        try:
            import cv2
            import numpy as np
            import pyrealsense2 as rs
        except ImportError as exc:
            print(f"\nCamera unavailable: missing dependency ({exc})")
            return False

        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

        try:
            print("\nStarting RealSense camera...")
            pipeline.start(config)

            for _ in range(30):
                pipeline.wait_for_frames()
        except Exception as exc:
            print(f"\nCamera unavailable: {exc}")
            return False

        self._pipeline = pipeline
        self._cv2 = cv2
        self._np = np
        return True

    def capture(self):
        if not self._ensure_started():
            return

        frames = self._pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            print("\nCapture failed: could not obtain color and depth frames")
            return

        color_image = self._np.asanyarray(color_frame.get_data())
        depth_image = self._np.asanyarray(depth_frame.get_data())

        center_y = depth_image.shape[0] // 2
        center_x = depth_image.shape[1] // 2
        distance_m = depth_frame.get_distance(center_x, center_y)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rgb_path = f"camera_rgb_{timestamp}.jpg"
        depth_path = f"camera_depth_{timestamp}.jpg"

        if not self._cv2.imwrite(rgb_path, color_image):
            print("\nCapture failed: could not save RGB image")
            return

        depth_display = self._cv2.convertScaleAbs(depth_image, alpha=0.03)
        depth_colormap = self._cv2.applyColorMap(
            depth_display,
            self._cv2.COLORMAP_JET,
        )

        if not self._cv2.imwrite(depth_path, depth_colormap):
            print("\nCapture failed: could not save depth image")
            return

        print(
            f"\rCaptured {rgb_path}, {depth_path} "
            f"(center depth {distance_m:.3f} m)   ",
            end="",
            flush=True,
        )

    def stop(self):
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None


def main():
    if not sys.stdin.isatty():
        print("ERROR: Run this script from an interactive terminal.")
        return 1

    robot = stretch_body.robot.Robot()
    camera = CameraCapture()
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    print("Starting Stretch...")
    if not robot.startup():
        print("ERROR: Robot startup failed.", file=sys.stderr)
        return 1

    try:
        if not robot.is_calibrated():
            print(
                "ERROR: Robot is not calibrated. "
                "Run stretch_robot_home.py first.",
                file=sys.stderr,
            )
            return 1

        tty.setcbreak(sys.stdin.fileno())
        print(HELP)

        last_command_time = 0.0
        moving = False

        while True:
            key = read_key(LOOP_PERIOD_S)
            now = time.monotonic()

            if key is not None:
                key_lower = key.lower()

                if key_lower in ("q", "\x03"):  # q or Ctrl+C
                    break

                if key_lower in ("w", "\x1b[A"):
                    send_velocity(robot, LINEAR_SPEED_MPS, 0.0)
                    print("\rForward                  ", end="", flush=True)
                    moving = True

                elif key_lower in ("s", "\x1b[B"):
                    send_velocity(robot, -LINEAR_SPEED_MPS, 0.0)
                    print("\rBackward                 ", end="", flush=True)
                    moving = True

                elif key_lower in ("a", "\x1b[D"):
                    send_velocity(robot, 0.0, ROTATION_SPEED_RAD_S)
                    print(
                        "\rRotate counterclockwise   ",
                        end="",
                        flush=True,
                    )
                    moving = True

                elif key_lower in ("d", "\x1b[C"):
                    send_velocity(robot, 0.0, -ROTATION_SPEED_RAD_S)
                    print(
                        "\rRotate clockwise          ",
                        end="",
                        flush=True,
                    )
                    moving = True

                elif key_lower in (" ", "x"):
                    send_velocity(robot, 0.0, 0.0)
                    print("\rStopped                  ", end="", flush=True)
                    moving = False

                elif key_lower == "r":
                    move_lift(robot, LIFT_STEP_M)
                    print("\rLift up                  ", end="", flush=True)
                    moving = False

                elif key_lower == "f":
                    move_lift(robot, -LIFT_STEP_M)
                    print("\rLift down                ", end="", flush=True)
                    moving = False

                elif key_lower == "t":
                    move_arm(robot, ARM_STEP_M)
                    print("\rArm extend               ", end="", flush=True)
                    moving = False

                elif key_lower == "g":
                    move_arm(robot, -ARM_STEP_M)
                    print("\rArm retract              ", end="", flush=True)
                    moving = False

                elif key_lower == "z":
                    move_wrist(robot, WRIST_STEP_RAD)
                    print(
                        "\rWrist yaw counterclockwise",
                        end="",
                        flush=True,
                    )
                    moving = False

                elif key_lower == "v":
                    move_wrist(robot, -WRIST_STEP_RAD)
                    print(
                        "\rWrist yaw clockwise       ",
                        end="",
                        flush=True,
                    )
                    moving = False

                elif key_lower == "j":
                    move_head_pan(robot, HEAD_PAN_STEP_RAD)
                    print("\rHead pan left            ", end="", flush=True)
                    moving = False

                elif key_lower == "l":
                    move_head_pan(robot, -HEAD_PAN_STEP_RAD)
                    print("\rHead pan right           ", end="", flush=True)
                    moving = False

                elif key_lower == "i":
                    move_head_tilt(robot, HEAD_TILT_STEP_RAD)
                    print("\rHead tilt up             ", end="", flush=True)
                    moving = False

                elif key_lower == "k":
                    move_head_tilt(robot, -HEAD_TILT_STEP_RAD)
                    print("\rHead tilt down           ", end="", flush=True)
                    moving = False

                elif key_lower == "p":
                    camera.capture()
                    moving = False

                else:
                    send_velocity(robot, 0.0, 0.0)
                    moving = False

                last_command_time = now

            # Dead-man timeout: stop base unless movement keys are repeated.
            if moving and now - last_command_time > COMMAND_TIMEOUT_S:
                send_velocity(robot, 0.0, 0.0)
                print("\rStopped                  ", end="", flush=True)
                moving = False

        print("\nExiting keyboard test.")
        return 0

    except KeyboardInterrupt:
        print("\nKeyboard test interrupted.")
        return 130

    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    finally:
        # Explicitly send zero velocity before shutting down.
        try:
            send_velocity(robot, 0.0, 0.0)
            time.sleep(0.1)
        except Exception:
            pass

        camera.stop()
        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            old_terminal_settings,
        )
        robot.stop()


if __name__ == "__main__":
    sys.exit(main())
