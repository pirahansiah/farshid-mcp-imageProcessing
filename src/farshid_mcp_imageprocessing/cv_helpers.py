"""Shared helpers for the OpenCV MCP server."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from mcp.server.fastmcp import Image


# ---------- I/O ----------

def read_image(path: str, flag: int = cv2.IMREAD_UNCHANGED) -> np.ndarray:
    """Read an image from disk, raising a clear error on failure."""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    img = cv2.imread(str(p), flag)
    if img is None:
        raise RuntimeError(f"OpenCV could not decode image: {p}")
    return img


def write_image(path: str, img: np.ndarray) -> Path:
    """Write an image, creating parent dirs."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(p), img)
    if not ok:
        raise RuntimeError(f"OpenCV could not write image: {p}")
    return p


def to_mcp_image(img: np.ndarray, fmt: str = "png") -> Image:
    """Encode an ndarray as an MCP Image payload."""
    fmt = fmt.lower().lstrip(".")
    ext = "." + fmt
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise RuntimeError(f"Could not encode image as {fmt}")
    return Image(data=buf.tobytes(), format=fmt)


# ---------- Webcam ----------

def grab_frame(camera_index: int = 0, warmup_frames: int = 2) -> np.ndarray:
    """Open webcam, discard a few warmup frames, return one frame."""
    cap = cv2.VideoCapture(camera_index)
    try:
        if not cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam at camera_index={camera_index}. "
                "Check OS camera permissions and whether another app is using it."
            )
        frame = None
        for _ in range(max(1, warmup_frames + 1)):
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Webcam opened, but no frame could be read.")
        return frame
    finally:
        cap.release()


# ---------- Geometry / parsing ----------

def parse_color(color: "str | Tuple[int, int, int]") -> Tuple[int, int, int]:
    """Accept '#rrggbb', 'r,g,b', or tuple. Returns BGR for OpenCV."""
    if isinstance(color, (tuple, list)) and len(color) == 3:
        r, g, b = [int(c) for c in color]
        return (b, g, r)
    s = str(color).strip()
    if s.startswith("#") and len(s) == 7:
        r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
        return (b, g, r)
    parts = [p.strip() for p in s.split(",")]
    if len(parts) == 3:
        r, g, b = [int(p) for p in parts]
        return (b, g, r)
    raise ValueError(f"Cannot parse color: {color!r}")


def ensure_bgr(img: np.ndarray) -> np.ndarray:
    """Convert grayscale or BGRA to 3-channel BGR."""
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def odd(n: int, minimum: int = 1) -> int:
    """Force value to an odd integer >= minimum (kernel sizes need odd)."""
    n = int(n)
    if n < minimum:
        n = minimum
    if n % 2 == 0:
        n += 1
    return n
