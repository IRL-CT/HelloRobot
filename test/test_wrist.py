#!/usr/bin/env python3

import math
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

        angle = math.radians(14)

        print("Rotating wrist yaw in one direction...")
        robot.end_of_arm.move_by("wrist_yaw", angle)
        robot.push_command()
        time.sleep(2)

        print("Rotating wrist yaw in the opposite direction...")
        robot.end_of_arm.move_by("wrist_yaw", -2 * angle)
        robot.push_command()
        time.sleep(2)

        print("Returning wrist to its starting position...")
        robot.end_of_arm.move_by("wrist_yaw", angle)
        robot.push_command()
        time.sleep(2)

        print("Wrist test complete.")

    finally:
        robot.stop()


if __name__ == "__main__":
    main()