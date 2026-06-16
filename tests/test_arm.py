#!/usr/bin/env python3

import time
import stretch_body.robot


robot = stretch_body.robot.Robot()

try:
    if not robot.startup():
        raise RuntimeError("Robot startup failed")

    if not robot.is_calibrated():
        raise RuntimeError("Robot is not calibrated")

    print("Extending arm 5 cm...")
    robot.arm.move_by(0.05)  # meters
    robot.push_command()
    time.sleep(3)

    print("Retracting arm 5 cm...")
    robot.arm.move_by(-0.05)
    robot.push_command()
    time.sleep(3)

    print("Arm test complete.")

finally:
    robot.stop()