#!/usr/bin/env python3

import math
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LidarTest(Node):
    def __init__(self):
        super().__init__("stretch_lidar_test")
        self.subscription = self.create_subscription(
            LaserScan,
            "/scan",
            self.scan_callback,
            10,
        )
        self.received_scan = False
        self.timeout_timer = self.create_timer(10.0, self.timeout_callback)
        print("Waiting for a lidar scan on /scan...")

    def scan_callback(self, message):
        if self.received_scan:
            return

        self.received_scan = True

        valid_ranges = [
            distance
            for distance in message.ranges
            if math.isfinite(distance)
            and message.range_min <= distance <= message.range_max
        ]

        print(f"Received {len(message.ranges)} measurements.")
        print(f"Valid measurements: {len(valid_ranges)}")
        print(f"Sensor range: {message.range_min:.2f}–"
              f"{message.range_max:.2f} meters")

        if valid_ranges:
            print(f"Nearest detected object: {min(valid_ranges):.3f} meters")
            print("Lidar test successful.")
        else:
            print("A scan arrived, but it contained no valid ranges.")

        rclpy.shutdown()

    def timeout_callback(self):
        if not self.received_scan:
            print(
                "No /scan message received within 10 seconds.",
                file=sys.stderr,
            )
            rclpy.shutdown()


def main():
    rclpy.init()
    node = LidarTest()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()


if __name__ == "__main__":
    main()