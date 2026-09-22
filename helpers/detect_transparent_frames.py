"""
Helper script to detect transparent frame regions in an image.
Scans for transparent (alpha == 0) pixels and groups them into bounding boxes.

Usage:
    uv run python helpers/detect_transparent_frames.py kaleidoscope-template.png
"""

import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def detect_transparent_frames(image_path: str, min_area: int = 5000) -> tuple[list[dict], int, int]:
    """
    Detect rectangular regions of transparent pixels in the image.

    Args:
        image_path: Path to the PNG image.
        min_area: Minimum pixel area to consider as a valid frame (filters noise).

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

    # Find bounding boxes of connected transparent regions
    frames = _find_bounding_boxes(transparent, min_area=min_area)

    # Sort: top-to-bottom, then left-to-right within each row
    frames = _sort_grid(frames)

    # Assign descriptions
    for i, frame in enumerate(frames):
        row = i // 2  # assume 2 columns
        col = i % 2
        row_label = "top" if row == 0 else "bottom"
        col_label = "left" if col == 0 else "right"
        frame["description"] = f"{row_label}-{col_label}"

    return frames, canvas_w, canvas_h


def _find_bounding_boxes(mask: np.ndarray, min_area: int) -> list[dict]:
    """
    Find bounding boxes of connected transparent regions using BFS (4-connectivity).
    This properly separates distinct regions even if they're in the same row/column.
    """
    rows, cols = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    regions = []

    for y in range(rows):
        for x in range(cols):
            if mask[y, x] and not visited[y, x]:
                # BFS to find the entire connected component
                component_pixels = []
                queue = deque([(y, x)])
                visited[y, x] = True

                while queue:
                    cy, cx = queue.popleft()
                    component_pixels.append((cy, cx))

                    # 4-connectivity: up, down, left, right
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < rows and 0 <= nx < cols:
                            if mask[ny, nx] and not visited[ny, nx]:
                                visited[ny, nx] = True
                                queue.append((ny, nx))

                # Compute bounding box for this component
                if component_pixels:
                    ys = [p[0] for p in component_pixels]
                    xs = [p[1] for p in component_pixels]

                    y_start, y_end = min(ys), max(ys)
                    x_start, x_end = min(xs), max(xs)

                    area = (y_end - y_start + 1) * (x_end - x_start + 1)
                    if area >= min_area:
                        regions.append(
                            {
                                "pos_x": int(x_start),
                                "pos_y": int(y_start),
                                "width": int(x_end - x_start + 1),
                                "height": int(y_end - y_start + 1),
                                "area": int(area),
                            }
                        )

    return regions


def _sort_grid(frames: list[dict]) -> list[dict]:
    """
    Sort frames into a grid layout: top-to-bottom, then left-to-right.
    Groups frames that share a similar y-position into rows.
    """
    if not frames:
        return frames

    # Sort by y position first
    frames.sort(key=lambda f: f["pos_y"])

    # Group into rows based on y-overlap
    rows = []
    current_row = [frames[0]]
    current_y_center = frames[0]["pos_y"] + frames[0]["height"] / 2

    for frame in frames[1:]:
        y_center = frame["pos_y"] + frame["height"] / 2
        if abs(y_center - current_y_center) < frame["height"] / 2:
            # Same row
            current_row.append(frame)
            current_y_center = (current_y_center * len(current_row) + y_center) / (len(current_row) + 1)
        else:
            # New row — sort left-to-right within the row
            current_row.sort(key=lambda f: f["pos_x"])
            rows.extend(current_row)
            current_row = [frame]
            current_y_center = y_center

    # Don't forget the last row
    current_row.sort(key=lambda f: f["pos_x"])
    rows.extend(current_row)

    return rows


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
