#!/usr/bin/env python3

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


HELP = """
Stretch keyboard base test

    W / Up Arrow      forward
    S / Down Arrow    backward
    A / Left Arrow    rotate counterclockwise
    D / Right Arrow   rotate clockwise
    Space or X        stop
    Q                 stop and quit

Commands stop automatically when no key is received.
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


def main():
    if not sys.stdin.isatty():
        print("ERROR: Run this script from an interactive terminal.")
        return 1

    robot = stretch_body.robot.Robot()
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

                else:
                    send_velocity(robot, 0.0, 0.0)
                    moving = False

                last_command_time = now

            # Dead-man timeout: stop unless movement keys are repeated.
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

        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            old_terminal_settings,
        )
        robot.stop()


if __name__ == "__main__":
    sys.exit(main())