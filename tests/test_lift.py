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

        print("Moving lift up 3 cm...")
        robot.lift.move_by(0.03)  # meters
        robot.push_command()
        time.sleep(3)

        print("Moving lift down 3 cm...")
        robot.lift.move_by(-0.03)
        robot.push_command()
        time.sleep(3)

        print("Lift test complete.")

    finally:
        robot.stop()


if __name__ == "__main__":
    main()