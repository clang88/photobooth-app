"""
Helper script to detect transparent frame regions in an image.
Scans for transparent (alpha == 0) pixels, bridges small gaps via morphological
dilation, then groups them into bounding boxes.

Usage:
    uv run python helpers/detect_transparent_frames.py kaleidoscope-template.png
    uv run python helpers/detect_transparent_frames.py image.png --gap 30
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def detect_transparent_frames(
    image_path: str,
    min_area: int = 5000,
    gap: int = 30,
) -> tuple[list[dict], int, int]:
    """
    Detect rectangular regions of transparent pixels in the image.

    Uses morphological dilation to bridge small gaps caused by non-transparent
    elements (borders, decorative pixels) that intrude into transparent areas.

    Args:
        image_path: Path to the PNG image.
        min_area: Minimum pixel area to consider as a valid frame (filters noise).
        gap: Maximum gap size in pixels to bridge via dilation. Larger values
             merge regions that are farther apart. Default 30px works well for
             most template images with decorative borders.

    Returns:
        Tuple of (frames, canvas_width, canvas_height).
    """
    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)

    canvas_w, canvas_h = img.size
    print(f"Canvas size: {canvas_w} × {canvas_h}")

    # Alpha channel: 0 = fully transparent, 255 = fully opaque
    alpha = arr[:, :, 3]

    # Find transparent pixels (alpha < 50 to allow for anti-aliasing)
    transparent = alpha < 50

    # Dilate to bridge small gaps, then erode to restore original shape
    # The dilation kernel is a square of size (2*gap+1) to bridge gaps up to `gap` pixels
    if gap > 0:
        kernel_size = 2 * gap + 1
        mask = cv2.dilate(transparent.astype(np.uint8), np.ones((kernel_size, kernel_size), dtype=np.uint8))
    else:
        mask = transparent.astype(np.uint8)

    # Find bounding boxes of connected transparent regions using cv2 connectedComponents
    frames = _find_bounding_boxes(mask, min_area=min_area)

    # Sort and assign descriptive names based on spatial position
    frames = _sort_and_label(frames, canvas_w, canvas_h)

    return frames, canvas_w, canvas_h


def _find_bounding_boxes(mask: np.ndarray, min_area: int) -> list[dict]:
    """
    Find bounding boxes of connected transparent regions using cv2 connectedComponents.
    """
    # Label connected components (8-connectivity)
    num_labels, labeled = cv2.connectedComponents(mask)

    regions = []
    for component_id in range(1, num_labels):
        component_mask = labeled == component_id

        # Get coordinates of all pixels in this component
        ys, xs = np.where(component_mask)

        if len(xs) == 0:
            continue

        y_start, y_end = int(ys.min()), int(ys.max())
        x_start, x_end = int(xs.min()), int(xs.max())

        area = (y_end - y_start + 1) * (x_end - x_start + 1)
        if area >= min_area:
            regions.append(
                {
                    "pos_x": x_start,
                    "pos_y": y_start,
                    "width": x_end - x_start + 1,
                    "height": y_end - y_start + 1,
                    "area": int(area),
                }
            )

    return regions


def _sort_and_label(frames: list[dict], canvas_w: int, canvas_h: int) -> list[dict]:
    """
    Sort frames and assign descriptive names based on spatial position.

    Strategy:
    1. Group frames into vertical zones (left half vs right half) by x-center.
    2. Within each zone, group into horizontal zones (top/middle/bottom).
    3. Special handling: if a frame spans >70% of canvas height, label it as
       a "full-height" frame on that side (e.g., "left", "right").

    Naming scheme:
    - Full-height frames: "left", "right" (no row prefix)
    - Small frames: "top-left", "top-right", "middle-left", "middle-right",
      "bottom-left", "bottom-right"
    """
    if not frames:
        return frames

    # Sort by y position
    frames.sort(key=lambda f: f["pos_y"])

    # Separate full-height frames from small ones
    # If a frame spans >50% of canvas height, treat it as a full-height frame
    full_height_threshold = canvas_h * 0.5
    full_height_frames: list[dict] = []
    small_frames: list[dict] = []

    for frame in frames:
        if frame["height"] >= full_height_threshold:
            full_height_frames.append(frame)
        else:
            small_frames.append(frame)

    # Assign names to full-height frames (just left/right based on x position)
    full_height_frames.sort(key=lambda f: f["pos_x"])
    for frame in full_height_frames:
        # Use left edge position to determine side
        if frame["pos_x"] < canvas_w * 0.4:
            frame["description"] = "left"
        elif frame["pos_x"] > canvas_w * 0.6:
            frame["description"] = "right"
        else:
            frame["description"] = "center"

    # Group small frames into vertical zones (left/right)
    small_frames.sort(key=lambda f: f["pos_x"])
    left_frames: list[dict] = []
    right_frames: list[dict] = []

    for frame in small_frames:
        x_center = frame["pos_x"] + frame["width"] / 2
        if x_center < canvas_w * 0.5:
            left_frames.append(frame)
        else:
            right_frames.append(frame)

    # Within each zone, group into rows (top/middle/bottom)
    def group_into_rows(frames_in_zone: list[dict]) -> list[list[dict]]:
        if not frames_in_zone:
            return []
        frames_in_zone.sort(key=lambda f: f["pos_y"])
        rows_in_zone: list[list[dict]] = []
        current_row = [frames_in_zone[0]]
        current_y_center = frames_in_zone[0]["pos_y"] + frames_in_zone[0]["height"] / 2
        avg_h = np.mean([f["height"] for f in frames_in_zone])

        for frame in frames_in_zone[1:]:
            y_center = frame["pos_y"] + frame["height"] / 2
            if abs(y_center - current_y_center) < avg_h / 2:
                current_row.append(frame)
                current_y_center = (current_y_center * len(current_row) + y_center) / (len(current_row) + 1)
            else:
                rows_in_zone.append(current_row)
                current_row = [frame]
                current_y_center = y_center
        rows_in_zone.append(current_row)
        return rows_in_zone

    left_rows = group_into_rows(left_frames)
    right_rows = group_into_rows(right_frames)

    # Assign names
    for row_frames in left_rows:
        row_label = _get_row_label(row_frames, canvas_h)
        for frame in row_frames:
            frame["description"] = f"{row_label}-left"

    for row_frames in right_rows:
        row_label = _get_row_label(row_frames, canvas_h)
        for frame in row_frames:
            frame["description"] = f"{row_label}-right"

    # Sort all frames by y position for consistent output
    frames.sort(key=lambda f: f["pos_y"])
    return frames


def _get_row_label(row_frames: list[dict], canvas_h: int) -> str:
    """Get the row label (top/middle/bottom) based on the y-center of the row."""
    if not row_frames:
        return "top"
    avg_y_center = np.mean([f["pos_y"] + f["height"] / 2 for f in row_frames])
    if avg_y_center < canvas_h * 0.3:
        return "top"
    elif avg_y_center > canvas_h * 0.7:
        return "bottom"
    else:
        return "middle"


def to_collage_config(frames: list[dict], canvas_width: int = 1024, canvas_height: int = 1536) -> dict:
    """
    Convert detected frames into a photobooth collage config snippet.
    """
    merge_definition = []
    for frame in frames:
        merge_definition.append(
            {
                "description": frame["description"],
                "pos_x": frame["pos_x"],
                "pos_y": frame["pos_y"],
                "pos_z": 0,
                "width": frame["width"],
                "height": frame["height"],
                "rotate": 0,
                "predefined_image": None,
                "image_filter": "original",
            }
        )

    return {
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "merge_definition": merge_definition,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python detect_transparent_frames.py <image.png>")
        sys.exit(1)

    image_path = sys.argv[1]
    path = Path(image_path)

    if not path.exists():
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    print(f"Analyzing: {path.absolute()}\n")

    frames, canvas_w, canvas_h = detect_transparent_frames(str(path))

    if not frames:
        print("No transparent frame regions detected.")
        print("Try lowering the --min-area parameter or checking the image has transparent regions.")
        sys.exit(0)

    print(f"Detected {len(frames)} frame(s):\n")
    for i, frame in enumerate(frames):
        print(f"  [{i}] {frame['description']}: x={frame['pos_x']}, y={frame['pos_y']}, w={frame['width']}, h={frame['height']}")

    # Print JSON config snippet
    print("\n--- JSON config snippet ---\n")
    import json

    config = to_collage_config(frames, canvas_width=canvas_w, canvas_height=canvas_h)
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
