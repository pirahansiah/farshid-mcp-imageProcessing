"""Quick local smoke test - calls tool functions directly (no MCP transport).
Run:  python smoke_test.py
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from farshid_mcp_imageprocessing import server as M


OUT = Path(__file__).parent / ".farshid" / "test"
OUT.mkdir(parents=True, exist_ok=True)


def make_sample(path: Path) -> None:
    """Create a synthetic test image with shapes."""
    img = np.full((400, 600, 3), 30, dtype=np.uint8)
    cv2.rectangle(img, (60, 60), (220, 240), (0, 200, 255), -1)
    cv2.circle(img, (430, 150), 80, (50, 220, 50), -1)
    cv2.line(img, (50, 350), (550, 350), (255, 100, 100), 4)
    cv2.putText(img, "OpenCV MCP", (120, 320),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.imwrite(str(path), img)


def run() -> None:
    sample = OUT / "sample.png"
    make_sample(sample)

    print("image_info:", M.image_info(str(sample)))
    print(M.image_resize(str(sample), str(OUT / "resized.png"), scale=0.5))
    print(M.image_to_grayscale(str(sample), str(OUT / "gray.png")))
    print(M.image_resize(str(OUT / "gray.png"),
                         str(OUT / "gray_240x240.png"),
                         width=240, height=240))
    print(M.edges_canny(str(sample), str(OUT / "edges.png")))


if __name__ == "__main__":
    run()
