#!/usr/bin/env python3

import math
import sys
import time

import stretch_body.robot


TEST_ANGLE_DEG = 10.0
MOVE_TIME_S = 3.0


def rotate(robot, degrees):
    """Command a relative base rotation in degrees."""
    print(f"Rotating {degrees:+.1f} degrees...")

    robot.base.rotate_by(math.radians(degrees))
    robot.push_command()

    # Allow time for this small test movement to finish.
    time.sleep(MOVE_TIME_S)


def main():
    robot = stretch_body.robot.Robot()

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

        print("Clear the floor around the robot.")
        print("Keep the runstop within reach.")

        rotate(robot, TEST_ANGLE_DEG)
        rotate(robot, -2.0 * TEST_ANGLE_DEG)
        rotate(robot, TEST_ANGLE_DEG)

        print("Rotation test complete.")
        return 0

    except KeyboardInterrupt:
        print("\nTest interrupted.")
        return 130

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    finally:
        robot.stop()


if __name__ == "__main__":
    sys.exit(main())