"""
farshid_mcp_imageprocessing.server — A comprehensive OpenCV image-processing MCP server.

Run as a stdio MCP server; do NOT use print() (stdout is the protocol channel).
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

import cv2
import numpy as np

from mcp.server.fastmcp import FastMCP, Image

from .cv_helpers import (
    read_image,
    write_image,
    to_mcp_image,
    grab_frame,
    parse_color,
    ensure_bgr,
    odd,
)

# All generated artifacts (images, videos, data) are written under this folder.
DATA_DIR = Path.cwd() / ".farshid"

mcp = FastMCP("imageProcessing")

# ============================================================================
# 1. WEBCAM / CAPTURE
# ============================================================================

@mcp.tool()
def webcam_capture(camera_index: int = 0) -> Image:
    """Capture one frame from the webcam and return it as a PNG image."""
    frame = grab_frame(camera_index)
    return to_mcp_image(frame, "png")


@mcp.tool()
def webcam_save(output_path: str = "", camera_index: int = 0) -> str:
    """Capture a webcam frame and save to disk. If output_path is empty,
    saves to ./.farshid/captures/snapshot_<timestamp>.png."""
    frame = grab_frame(camera_index)
    if not output_path:
        out_dir = DATA_DIR / "captures"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    p = write_image(output_path, frame)
    return f"Saved webcam snapshot to: {p}"


@mcp.tool()
def webcam_preview(camera_index: int = 0, seconds: int = 10) -> str:
    """Open a local OpenCV preview window for up to N seconds (max 120).
    Press 'q' in the window to close early. Requires a local display."""
    seconds = max(1, min(int(seconds), 120))
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam at camera_index={camera_index}.")
    win = "OpenCV MCP preview - press q to quit"
    start = time.time()
    try:
        while time.time() - start < seconds:
            ok, frame = cap.read()
            if not ok:
                break
            cv2.imshow(win, frame)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return f"Closed preview after {round(time.time() - start, 1)}s."


@mcp.tool()
def webcam_record(output_path: str = "", seconds: int = 5,
                  camera_index: int = 0, fps: float = 20.0) -> str:
    """Record a short MP4 from the webcam for N seconds (max 120).
    If output_path is empty, saves to ./.farshid/videos/clip_<timestamp>.mp4."""
    seconds = max(1, min(int(seconds), 120))
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam at camera_index={camera_index}.")
    ok, frame = cap.read()
    if not ok:
        cap.release()
        raise RuntimeError("Webcam returned no frames.")
    h, w = frame.shape[:2]
    if not output_path:
        out_dir = DATA_DIR / "videos"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"clip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
    p = Path(output_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(p), fourcc, float(fps), (w, h))
    n = 0
    start = time.time()
    try:
        while time.time() - start < seconds:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
            n += 1
    finally:
        cap.release()
        writer.release()
    return f"Recorded {n} frames ({round(time.time() - start, 1)}s) to {p}"


# ============================================================================
# 2. IMAGE I/O AND INFO
# ============================================================================

@mcp.tool()
def image_show(path: str) -> Image:
    """Load an image from disk and return it as PNG to the chat."""
    img = read_image(path)
    return to_mcp_image(ensure_bgr(img), "png")


@mcp.tool()
def image_info(path: str) -> dict:
    """Return shape, dtype, channel count, file size, and basic stats."""
    img = read_image(path)
    p = Path(path).expanduser()
    h, w = img.shape[:2]
    ch = 1 if img.ndim == 2 else img.shape[2]
    info = {
        "path": str(p),
        "file_size_bytes": p.stat().st_size,
        "width": int(w),
        "height": int(h),
        "channels": int(ch),
        "dtype": str(img.dtype),
        "min": float(img.min()),
        "max": float(img.max()),
        "mean": float(img.mean()),
    }
    return info


@mcp.tool()
def image_convert(input_path: str, output_path: str, quality: int = 95) -> str:
    """Convert an image between formats by extension (e.g. .jpg, .png, .webp, .bmp).
    `quality` applies to JPEG/WebP."""
    img = read_image(input_path)
    p = Path(output_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    ext = p.suffix.lower()
    params = []
    if ext in (".jpg", ".jpeg"):
        params = [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
    elif ext == ".webp":
        params = [cv2.IMWRITE_WEBP_QUALITY, int(quality)]
    elif ext == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
    ok = cv2.imwrite(str(p), img, params)
    if not ok:
        raise RuntimeError(f"Could not write {p}")
    return f"Wrote {p} ({p.stat().st_size} bytes)"


# ============================================================================
# 3. GEOMETRIC TRANSFORMS
# ============================================================================

@mcp.tool()
def image_resize(input_path: str, output_path: str,
                 width: int = 0, height: int = 0,
                 scale: float = 0.0,
                 interpolation: str = "area") -> str:
    """Resize an image. Provide either (width, height), or scale, or one of
    width/height (the other is computed to keep aspect ratio).
    interpolation: nearest, linear, cubic, area, lanczos."""
    img = read_image(input_path)
    h, w = img.shape[:2]
    if scale and scale > 0:
        nw, nh = int(w * scale), int(h * scale)
    elif width and height:
        nw, nh = int(width), int(height)
    elif width:
        nw = int(width); nh = int(h * (nw / w))
    elif height:
        nh = int(height); nw = int(w * (nh / h))
    else:
        raise ValueError("Provide width, height, or scale.")
    interp_map = {
        "nearest": cv2.INTER_NEAREST, "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC, "area": cv2.INTER_AREA,
        "lanczos": cv2.INTER_LANCZOS4,
    }
    out = cv2.resize(img, (nw, nh), interpolation=interp_map.get(interpolation, cv2.INTER_AREA))
    p = write_image(output_path, out)
    return f"Resized {w}x{h} -> {nw}x{nh}, saved {p}"


@mcp.tool()
def image_crop(input_path: str, output_path: str,
               x: int, y: int, width: int, height: int) -> str:
    """Crop a rectangular region (x, y, width, height) from an image."""
    img = read_image(input_path)
    h, w = img.shape[:2]
    x2, y2 = min(w, x + width), min(h, y + height)
    x, y = max(0, x), max(0, y)
    if x2 <= x or y2 <= y:
        raise ValueError("Crop region is empty or out of bounds.")
    out = img[y:y2, x:x2]
    p = write_image(output_path, out)
    return f"Cropped to {out.shape[1]}x{out.shape[0]}, saved {p}"


@mcp.tool()
def image_rotate(input_path: str, output_path: str,
                 angle: float, scale: float = 1.0,
                 keep_size: bool = False) -> str:
    """Rotate an image by `angle` degrees (CCW). If keep_size is False the
    output canvas is expanded to fit the rotated image."""
    img = read_image(input_path)
    h, w = img.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    M = cv2.getRotationMatrix2D((cx, cy), float(angle), float(scale))
    if keep_size:
        nw, nh = w, h
    else:
        cos, sin = abs(M[0, 0]), abs(M[0, 1])
        nw = int(h * sin + w * cos)
        nh = int(h * cos + w * sin)
        M[0, 2] += nw / 2 - cx
        M[1, 2] += nh / 2 - cy
    out = cv2.warpAffine(img, M, (nw, nh))
    p = write_image(output_path, out)
    return f"Rotated by {angle}deg, saved {p}"


@mcp.tool()
def image_flip(input_path: str, output_path: str, direction: str = "horizontal") -> str:
    """Flip image: horizontal (mirror), vertical, or both."""
    img = read_image(input_path)
    code = {"horizontal": 1, "vertical": 0, "both": -1}.get(direction)
    if code is None:
        raise ValueError("direction must be horizontal, vertical, or both")
    p = write_image(output_path, cv2.flip(img, code))
    return f"Flipped ({direction}), saved {p}"


@mcp.tool()
def image_pad(input_path: str, output_path: str,
              top: int = 0, bottom: int = 0, left: int = 0, right: int = 0,
              border_type: str = "constant", color: str = "0,0,0") -> str:
    """Add borders/padding around an image.
    border_type: constant, replicate, reflect, reflect101, wrap."""
    img = read_image(input_path)
    bmap = {"constant": cv2.BORDER_CONSTANT, "replicate": cv2.BORDER_REPLICATE,
            "reflect": cv2.BORDER_REFLECT, "reflect101": cv2.BORDER_REFLECT101,
            "wrap": cv2.BORDER_WRAP}
    bgr = parse_color(color)
    out = cv2.copyMakeBorder(img, top, bottom, left, right,
                             bmap.get(border_type, cv2.BORDER_CONSTANT), value=bgr)
    p = write_image(output_path, out)
    return f"Padded image, saved {p}"


# ============================================================================
# 4. COLOR
# ============================================================================

@mcp.tool()
def image_to_grayscale(input_path: str, output_path: str) -> str:
    """Convert image to single-channel grayscale."""
    img = read_image(input_path, cv2.IMREAD_COLOR)
    p = write_image(output_path, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    return f"Grayscale image saved to {p}"


@mcp.tool()
def color_convert(input_path: str, output_path: str, target: str) -> str:
    """Convert color space. target: gray, hsv, hls, lab, ycrcb, rgb, bgr."""
    img = read_image(input_path, cv2.IMREAD_COLOR)
    cmap = {
        "gray": cv2.COLOR_BGR2GRAY, "hsv": cv2.COLOR_BGR2HSV,
        "hls": cv2.COLOR_BGR2HLS, "lab": cv2.COLOR_BGR2LAB,
        "ycrcb": cv2.COLOR_BGR2YCrCb, "rgb": cv2.COLOR_BGR2RGB,
        "bgr": None,
    }
    if target not in cmap:
        raise ValueError(f"Unknown target {target}")
    out = img if cmap[target] is None else cv2.cvtColor(img, cmap[target])
    p = write_image(output_path, out)
    return f"Converted to {target}, saved {p}"


@mcp.tool()
def adjust_brightness_contrast(input_path: str, output_path: str,
                               brightness: int = 0, contrast: float = 1.0) -> str:
    """Adjust brightness (-255..255) and contrast (multiplier, e.g. 1.2)."""
    img = read_image(input_path)
    out = cv2.convertScaleAbs(img, alpha=float(contrast), beta=float(brightness))
    p = write_image(output_path, out)
    return f"Adjusted brightness/contrast, saved {p}"


@mcp.tool()
def histogram_equalize(input_path: str, output_path: str, method: str = "clahe") -> str:
    """Equalize histogram. method: 'global' (single-channel only) or
    'clahe' (adaptive, works on color via LAB L-channel)."""
    img = read_image(input_path)
    if method == "global":
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        out = cv2.equalizeHist(img)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        if img.ndim == 2:
            out = clahe.apply(img)
        else:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            lab[..., 0] = clahe.apply(lab[..., 0])
            out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    p = write_image(output_path, out)
    return f"Histogram equalized ({method}), saved {p}"


@mcp.tool()
def histogram_data(input_path: str, bins: int = 32) -> dict:
    """Return per-channel histograms as lists (B, G, R or single 'gray')."""
    img = read_image(input_path)
    bins = int(max(2, min(bins, 256)))
    out: dict = {"bins": bins, "range": [0, 256]}
    if img.ndim == 2:
        h = cv2.calcHist([img], [0], None, [bins], [0, 256]).flatten().tolist()
        out["gray"] = h
    else:
        for i, name in enumerate(["b", "g", "r"]):
            h = cv2.calcHist([img], [i], None, [bins], [0, 256]).flatten().tolist()
            out[name] = h
    return out


# ============================================================================
# 5. FILTERING / BLUR / SHARPEN
# ============================================================================

@mcp.tool()
def blur_gaussian(input_path: str, output_path: str, ksize: int = 5, sigma: float = 0.0) -> str:
    """Apply Gaussian blur. ksize is forced to odd."""
    img = read_image(input_path)
    k = odd(ksize, 1)
    p = write_image(output_path, cv2.GaussianBlur(img, (k, k), float(sigma)))
    return f"Gaussian blur k={k} sigma={sigma}, saved {p}"


@mcp.tool()
def blur_median(input_path: str, output_path: str, ksize: int = 5) -> str:
    """Median blur — good for salt-and-pepper noise."""
    img = read_image(input_path)
    k = odd(ksize, 3)
    p = write_image(output_path, cv2.medianBlur(img, k))
    return f"Median blur k={k}, saved {p}"


@mcp.tool()
def blur_bilateral(input_path: str, output_path: str,
                   d: int = 9, sigma_color: float = 75, sigma_space: float = 75) -> str:
    """Edge-preserving bilateral filter."""
    img = read_image(input_path)
    p = write_image(output_path,
                    cv2.bilateralFilter(img, int(d), float(sigma_color), float(sigma_space)))
    return f"Bilateral filter, saved {p}"


@mcp.tool()
def sharpen(input_path: str, output_path: str, amount: float = 1.0) -> str:
    """Unsharp-mask sharpening. `amount` ~ 0.5–2.0."""
    img = read_image(input_path)
    blur = cv2.GaussianBlur(img, (0, 0), 3)
    out = cv2.addWeighted(img, 1 + float(amount), blur, -float(amount), 0)
    p = write_image(output_path, out)
    return f"Sharpened (amount={amount}), saved {p}"


@mcp.tool()
def denoise(input_path: str, output_path: str, strength: int = 10) -> str:
    """Non-local means denoising for color images."""
    img = read_image(input_path, cv2.IMREAD_COLOR)
    out = cv2.fastNlMeansDenoisingColored(img, None, float(strength), float(strength), 7, 21)
    p = write_image(output_path, out)
    return f"Denoised (strength={strength}), saved {p}"


# ============================================================================
# 6. EDGES / GRADIENTS
# ============================================================================

@mcp.tool()
def edges_canny(input_path: str, output_path: str,
                threshold1: int = 100, threshold2: int = 200) -> str:
    """Canny edge detector."""
    img = read_image(input_path, cv2.IMREAD_GRAYSCALE)
    p = write_image(output_path, cv2.Canny(img, int(threshold1), int(threshold2)))
    return f"Canny edges saved to {p}"


@mcp.tool()
def edges_sobel(input_path: str, output_path: str, ksize: int = 3) -> str:
    """Sobel gradient magnitude."""
    img = read_image(input_path, cv2.IMREAD_GRAYSCALE)
    k = odd(ksize, 1)
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=k)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=k)
    mag = cv2.magnitude(gx, gy)
    out = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    p = write_image(output_path, out)
    return f"Sobel magnitude saved to {p}"


@mcp.tool()
def edges_laplacian(input_path: str, output_path: str, ksize: int = 3) -> str:
    """Laplacian of an image."""
    img = read_image(input_path, cv2.IMREAD_GRAYSCALE)
    out = cv2.convertScaleAbs(cv2.Laplacian(img, cv2.CV_16S, ksize=odd(ksize, 1)))
    p = write_image(output_path, out)
    return f"Laplacian saved to {p}"


# ============================================================================
# 7. THRESHOLDING / MORPHOLOGY
# ============================================================================

@mcp.tool()
def threshold(input_path: str, output_path: str,
              method: str = "otsu", thresh: int = 127, maxval: int = 255) -> str:
    """Binary threshold. method: binary, binary_inv, otsu, adaptive_mean, adaptive_gaussian."""
    img = read_image(input_path, cv2.IMREAD_GRAYSCALE)
    if method == "binary":
        _, out = cv2.threshold(img, thresh, maxval, cv2.THRESH_BINARY)
    elif method == "binary_inv":
        _, out = cv2.threshold(img, thresh, maxval, cv2.THRESH_BINARY_INV)
    elif method == "otsu":
        _, out = cv2.threshold(img, 0, maxval, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive_mean":
        out = cv2.adaptiveThreshold(img, maxval, cv2.ADAPTIVE_THRESH_MEAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
    elif method == "adaptive_gaussian":
        out = cv2.adaptiveThreshold(img, maxval, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
    else:
        raise ValueError(f"Unknown method {method}")
    p = write_image(output_path, out)
    return f"Thresholded ({method}), saved {p}"


@mcp.tool()
def morphology(input_path: str, output_path: str, op: str = "open",
               ksize: int = 3, iterations: int = 1) -> str:
    """Morphological op: erode, dilate, open, close, gradient, tophat, blackhat."""
    img = read_image(input_path)
    k = odd(ksize, 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    omap = {"erode": cv2.MORPH_ERODE, "dilate": cv2.MORPH_DILATE,
            "open": cv2.MORPH_OPEN, "close": cv2.MORPH_CLOSE,
            "gradient": cv2.MORPH_GRADIENT, "tophat": cv2.MORPH_TOPHAT,
            "blackhat": cv2.MORPH_BLACKHAT}
    if op not in omap:
        raise ValueError(f"Unknown op {op}")
    out = cv2.morphologyEx(img, omap[op], kernel, iterations=int(iterations))
    p = write_image(output_path, out)
    return f"Morphology {op} k={k}, saved {p}"


# ============================================================================
# 8. CONTOURS / SHAPES
# ============================================================================

@mcp.tool()
def find_contours(input_path: str, output_path: str = "",
                  thresh: int = 127, min_area: float = 50.0) -> dict:
    """Find contours after thresholding. Optionally draw them onto output_path.
    Returns count and bounding boxes."""
    src = read_image(input_path)
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY) if src.ndim == 3 else src
    _, bw = cv2.threshold(gray, int(thresh), 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    keep = [c for c in contours if cv2.contourArea(c) >= min_area]
    boxes = []
    for c in keep:
        x, y, w, h = cv2.boundingRect(c)
        boxes.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h),
                      "area": float(cv2.contourArea(c))})
    if output_path:
        vis = ensure_bgr(src).copy()
        cv2.drawContours(vis, keep, -1, (0, 255, 0), 2)
        write_image(output_path, vis)
    return {"count": len(keep), "boxes": boxes,
            "annotated_image": output_path or None}


@mcp.tool()
def detect_circles(input_path: str, output_path: str = "",
                   dp: float = 1.2, min_dist: float = 30,
                   param1: float = 100, param2: float = 30,
                   min_radius: int = 0, max_radius: int = 0) -> dict:
    """Hough circle detection."""
    img = read_image(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gray = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=float(dp),
                               minDist=float(min_dist), param1=float(param1),
                               param2=float(param2), minRadius=int(min_radius),
                               maxRadius=int(max_radius))
    out_list = []
    if circles is not None:
        for x, y, r in np.round(circles[0]).astype(int):
            out_list.append({"x": int(x), "y": int(y), "r": int(r)})
    if output_path:
        vis = ensure_bgr(img).copy()
        for c in out_list:
            cv2.circle(vis, (c["x"], c["y"]), c["r"], (0, 255, 0), 2)
            cv2.circle(vis, (c["x"], c["y"]), 2, (0, 0, 255), 3)
        write_image(output_path, vis)
    return {"count": len(out_list), "circles": out_list,
            "annotated_image": output_path or None}


@mcp.tool()
def detect_lines(input_path: str, output_path: str = "",
                 canny1: int = 50, canny2: int = 150,
                 threshold: int = 80, min_line_length: int = 50,
                 max_line_gap: int = 10) -> dict:
    """Probabilistic Hough line detection."""
    img = read_image(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    edges = cv2.Canny(gray, canny1, canny2)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, int(threshold),
                            minLineLength=int(min_line_length),
                            maxLineGap=int(max_line_gap))
    out_list = []
    if lines is not None:
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            out_list.append({"x1": int(x1), "y1": int(y1),
                             "x2": int(x2), "y2": int(y2)})
    if output_path:
        vis = ensure_bgr(img).copy()
        for L in out_list:
            cv2.line(vis, (L["x1"], L["y1"]), (L["x2"], L["y2"]), (0, 255, 0), 2)
        write_image(output_path, vis)
    return {"count": len(out_list), "lines": out_list,
            "annotated_image": output_path or None}


@mcp.tool()
def detect_corners(input_path: str, output_path: str = "",
                   max_corners: int = 100, quality: float = 0.01,
                   min_distance: float = 10) -> dict:
    """Shi-Tomasi good-features-to-track corner detection."""
    img = read_image(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    pts = cv2.goodFeaturesToTrack(gray, int(max_corners), float(quality), float(min_distance))
    out_list = []
    if pts is not None:
        for x, y in pts.reshape(-1, 2):
            out_list.append({"x": float(x), "y": float(y)})
    if output_path:
        vis = ensure_bgr(img).copy()
        for c in out_list:
            cv2.circle(vis, (int(c["x"]), int(c["y"])), 4, (0, 255, 0), -1)
        write_image(output_path, vis)
    return {"count": len(out_list), "corners": out_list,
            "annotated_image": output_path or None}


# ============================================================================
# 9. FEATURE MATCHING (ORB)
# ============================================================================

@mcp.tool()
def feature_match(image1: str, image2: str, output_path: str = "",
                  max_features: int = 500, top_matches: int = 50) -> dict:
    """Detect and match ORB features between two images. Optionally save a
    side-by-side visualization."""
    a = read_image(image1, cv2.IMREAD_GRAYSCALE)
    b = read_image(image2, cv2.IMREAD_GRAYSCALE)
    orb = cv2.ORB_create(nfeatures=int(max_features))
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None:
        return {"keypoints_a": 0, "keypoints_b": 0, "matches": 0}
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(da, db), key=lambda m: m.distance)[: int(top_matches)]
    if output_path:
        vis = cv2.drawMatches(a, ka, b, kb, matches, None,
                              flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        write_image(output_path, vis)
    return {
        "keypoints_a": len(ka), "keypoints_b": len(kb),
        "matches": len(matches),
        "mean_distance": float(np.mean([m.distance for m in matches])) if matches else 0.0,
        "annotated_image": output_path or None,
    }


# ============================================================================
# 10. OBJECT DETECTION (Haar cascades, bundled with OpenCV)
# ============================================================================

def _cascade(name: str) -> cv2.CascadeClassifier:
    path = Path(cv2.data.haarcascades) / name
    cc = cv2.CascadeClassifier(str(path))
    if cc.empty():
        raise RuntimeError(f"Could not load cascade: {path}")
    return cc


@mcp.tool()
def detect_faces(input_path: str, output_path: str = "",
                 scale_factor: float = 1.1, min_neighbors: int = 5) -> dict:
    """Detect faces with the bundled Haar cascade. Returns bounding boxes."""
    img = read_image(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    cc = _cascade("haarcascade_frontalface_default.xml")
    faces = cc.detectMultiScale(gray, scaleFactor=float(scale_factor),
                                minNeighbors=int(min_neighbors))
    boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in faces]
    if output_path:
        vis = ensure_bgr(img).copy()
        for b in boxes:
            cv2.rectangle(vis, (b["x"], b["y"]),
                          (b["x"] + b["w"], b["y"] + b["h"]), (0, 255, 0), 2)
        write_image(output_path, vis)
    return {"count": len(boxes), "faces": boxes, "annotated_image": output_path or None}


@mcp.tool()
def detect_eyes(input_path: str, output_path: str = "") -> dict:
    """Detect eyes with the bundled Haar cascade."""
    img = read_image(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    cc = _cascade("haarcascade_eye.xml")
    eyes = cc.detectMultiScale(gray)
    boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in eyes]
    if output_path:
        vis = ensure_bgr(img).copy()
        for b in boxes:
            cv2.rectangle(vis, (b["x"], b["y"]),
                          (b["x"] + b["w"], b["y"] + b["h"]), (255, 0, 0), 2)
        write_image(output_path, vis)
    return {"count": len(boxes), "eyes": boxes, "annotated_image": output_path or None}


@mcp.tool()
def detect_bodies(input_path: str, output_path: str = "") -> dict:
    """Detect full bodies with the bundled Haar cascade (low recall, demo only)."""
    img = read_image(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    cc = _cascade("haarcascade_fullbody.xml")
    boxes_raw = cc.detectMultiScale(gray)
    boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in boxes_raw]
    if output_path:
        vis = ensure_bgr(img).copy()
        for b in boxes:
            cv2.rectangle(vis, (b["x"], b["y"]),
                          (b["x"] + b["w"], b["y"] + b["h"]), (0, 0, 255), 2)
        write_image(output_path, vis)
    return {"count": len(boxes), "bodies": boxes, "annotated_image": output_path or None}


@mcp.tool()
def detect_qrcode(input_path: str) -> dict:
    """Detect and decode QR codes."""
    img = read_image(input_path)
    det = cv2.QRCodeDetector()
    data, points, _ = det.detectAndDecode(img)
    return {
        "data": data,
        "found": bool(data) or points is not None,
        "points": points.tolist() if points is not None else None,
    }


# ============================================================================
# 11. DRAWING / ANNOTATION
# ============================================================================

@mcp.tool()
def draw_rectangle(input_path: str, output_path: str,
                   x: int, y: int, width: int, height: int,
                   color: str = "0,255,0", thickness: int = 2) -> str:
    """Draw a rectangle on an image."""
    img = ensure_bgr(read_image(input_path)).copy()
    cv2.rectangle(img, (x, y), (x + width, y + height), parse_color(color), int(thickness))
    p = write_image(output_path, img)
    return f"Saved {p}"


@mcp.tool()
def draw_circle(input_path: str, output_path: str,
                x: int, y: int, radius: int,
                color: str = "0,255,0", thickness: int = 2) -> str:
    """Draw a circle. thickness=-1 fills."""
    img = ensure_bgr(read_image(input_path)).copy()
    cv2.circle(img, (x, y), int(radius), parse_color(color), int(thickness))
    p = write_image(output_path, img)
    return f"Saved {p}"


@mcp.tool()
def draw_line(input_path: str, output_path: str,
              x1: int, y1: int, x2: int, y2: int,
              color: str = "0,255,0", thickness: int = 2) -> str:
    """Draw a line."""
    img = ensure_bgr(read_image(input_path)).copy()
    cv2.line(img, (x1, y1), (x2, y2), parse_color(color), int(thickness))
    p = write_image(output_path, img)
    return f"Saved {p}"


@mcp.tool()
def draw_text(input_path: str, output_path: str,
              text: str, x: int, y: int,
              color: str = "255,255,255", scale: float = 1.0, thickness: int = 2) -> str:
    """Draw text on an image."""
    img = ensure_bgr(read_image(input_path)).copy()
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                float(scale), parse_color(color), int(thickness), cv2.LINE_AA)
    p = write_image(output_path, img)
    return f"Saved {p}"


# ============================================================================
# 12. COMPOSITION / ARITHMETIC
# ============================================================================

@mcp.tool()
def image_blend(image1: str, image2: str, output_path: str, alpha: float = 0.5) -> str:
    """Blend two same-size images: out = a*img1 + (1-a)*img2."""
    a = read_image(image1)
    b = read_image(image2)
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    out = cv2.addWeighted(a, float(alpha), b, 1 - float(alpha), 0)
    p = write_image(output_path, out)
    return f"Blended (alpha={alpha}), saved {p}"


@mcp.tool()
def image_diff(image1: str, image2: str, output_path: str = "") -> dict:
    """Absolute difference between two images. Returns mean/max diff."""
    a = read_image(image1)
    b = read_image(image2)
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    diff = cv2.absdiff(a, b)
    if output_path:
        write_image(output_path, diff)
    return {
        "mean_difference": float(diff.mean()),
        "max_difference": int(diff.max()),
        "annotated_image": output_path or None,
    }


@mcp.tool()
def image_concat(images: List[str], output_path: str, direction: str = "horizontal") -> str:
    """Concatenate images horizontally or vertically (resized to common dim)."""
    if not images:
        raise ValueError("Need at least one image.")
    arrs = [read_image(p) for p in images]
    arrs = [ensure_bgr(a) for a in arrs]
    if direction == "horizontal":
        h = min(a.shape[0] for a in arrs)
        arrs = [cv2.resize(a, (int(a.shape[1] * h / a.shape[0]), h)) for a in arrs]
        out = np.hstack(arrs)
    elif direction == "vertical":
        w = min(a.shape[1] for a in arrs)
        arrs = [cv2.resize(a, (w, int(a.shape[0] * w / a.shape[1]))) for a in arrs]
        out = np.vstack(arrs)
    else:
        raise ValueError("direction must be horizontal or vertical")
    p = write_image(output_path, out)
    return f"Concatenated {len(images)} images, saved {p}"


@mcp.tool()
def template_match(image_path: str, template_path: str,
                   output_path: str = "", threshold: float = 0.8) -> dict:
    """Find a template inside an image (TM_CCOEFF_NORMED). Returns matches above threshold."""
    img = read_image(image_path)
    tpl = read_image(template_path)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    t = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY) if tpl.ndim == 3 else tpl
    res = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(res >= float(threshold))
    th, tw = t.shape[:2]
    matches = [{"x": int(x), "y": int(y), "score": float(res[y, x])}
               for y, x in zip(ys, xs)]
    matches.sort(key=lambda m: -m["score"])
    if output_path:
        vis = ensure_bgr(img).copy()
        for m in matches[:50]:
            cv2.rectangle(vis, (m["x"], m["y"]),
                          (m["x"] + tw, m["y"] + th), (0, 255, 0), 2)
        write_image(output_path, vis)
    return {"count": len(matches), "template_size": [int(tw), int(th)],
            "top_matches": matches[:20], "annotated_image": output_path or None}


# ============================================================================
# 13. VIDEO PROCESSING
# ============================================================================

@mcp.tool()
def video_info(path: str) -> dict:
    """Return video metadata (fps, width, height, frame count, duration)."""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(p)
    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {p}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return {"path": str(p), "fps": float(fps), "frame_count": n,
                "width": w, "height": h,
                "duration_seconds": float(n / fps) if fps > 0 else None}
    finally:
        cap.release()


@mcp.tool()
def video_extract_frames(video_path: str, output_dir: str,
                         every_n: int = 30, max_frames: int = 100,
                         ext: str = "jpg") -> dict:
    """Sample frames from a video and save them. Returns saved paths."""
    cap = cv2.VideoCapture(str(Path(video_path).expanduser()))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    i = 0
    try:
        while len(saved) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if i % max(1, int(every_n)) == 0:
                p = out / f"frame_{i:06d}.{ext}"
                cv2.imwrite(str(p), frame)
                saved.append(str(p))
            i += 1
    finally:
        cap.release()
    return {"saved_count": len(saved), "frames": saved}


@mcp.tool()
def video_thumbnail(video_path: str, output_path: str, time_seconds: float = 1.0) -> str:
    """Save a single frame from a video at a given time as a thumbnail."""
    cap = cv2.VideoCapture(str(Path(video_path).expanduser()))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(time_seconds) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Could not read frame at requested time.")
        p = write_image(output_path, frame)
        return f"Thumbnail saved to {p}"
    finally:
        cap.release()


# ============================================================================
# Entry point
# ============================================================================

def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    """Console-script entry point: run the image-processing MCP server over stdio."""
    _log("farshid-mcp-imageProcessing server starting (stdio)")
    mcp.run()


if __name__ == "__main__":
    main()
