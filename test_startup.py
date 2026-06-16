#!/usr/bin/env python3

import sys
import stretch_body.robot


def main() -> int:
    robot = stretch_body.robot.Robot()

    print("Connecting to Stretch RE1...")
    if not robot.startup():
        print("ERROR: Robot startup failed.")
        return 1

    try:
        print("Startup successful.")
        print(f"Robot calibrated: {robot.is_calibrated()}")

        # Read and print the current robot status.
        status = robot.get_status()
        print(f"Battery voltage: {status['pimu']['voltage']:.2f} V")
        print("Hello, Stretch RE1!")

    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    finally:
        print("Shutting down robot connection...")
        robot.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())