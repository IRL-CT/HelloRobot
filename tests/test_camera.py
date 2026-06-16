#!/usr/bin/env python3

import sys

import cv2
import numpy as np
import pyrealsense2 as rs


def main():
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    print("Starting RealSense camera...")

    try:
        pipeline.start(config)

        # Discard initial frames while auto-exposure settles.
        for _ in range(30):
            pipeline.wait_for_frames()

        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            raise RuntimeError("Could not obtain color and depth frames")

        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())

        center_y = depth_image.shape[0] // 2
        center_x = depth_image.shape[1] // 2
        distance_m = depth_frame.get_distance(center_x, center_y)

        if not cv2.imwrite("camera_rgb_test.jpg", color_image):
            raise RuntimeError("Could not save RGB image")

        # Convert depth data to a visible 8-bit heat-map image.
        depth_display = cv2.convertScaleAbs(depth_image, alpha=0.03)
        depth_colormap = cv2.applyColorMap(
            depth_display, cv2.COLORMAP_JET
        )

        if not cv2.imwrite("camera_depth_test.jpg", depth_colormap):
            raise RuntimeError("Could not save depth image")

        print("Camera test successful.")
        print(f"Center-pixel depth: {distance_m:.3f} meters")
        print("Saved camera_rgb_test.jpg")
        print("Saved camera_depth_test.jpg")

    finally:
        pipeline.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Camera test failed: {exc}", file=sys.stderr)
        sys.exit(1)