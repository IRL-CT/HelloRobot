#!/usr/bin/env python3

import time
import stretch_body.robot


def main():
    robot = stretch_body.robot.Robot()

    if not robot.startup():
        raise RuntimeError("Robot startup failed")

    try:
        if not robot.is_calibrated():
            raise RuntimeError(
                "Robot is not calibrated. Run stretch_robot_home.py first."
            )

        print("Make sure the floor is clear.")
        print("Moving forward 5 cm...")

        robot.base.translate_by(0.05)  # meters
        robot.push_command()
        time.sleep(3)

        print("Moving backward 5 cm...")
        robot.base.translate_by(-0.05)
        robot.push_command()
        time.sleep(3)

        print("Wheel test complete.")

    finally:
        robot.stop()


if __name__ == "__main__":
    main()