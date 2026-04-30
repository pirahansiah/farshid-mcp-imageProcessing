<!-- mcp-name: io.github.pirahansiah/farshid-mcp-imageProcessing -->

# farshid-mcp-imageProcessing

A comprehensive **OpenCV image-processing MCP server** for VS Code Copilot
Agent Mode (or any MCP client). Exposes ~40 tools across webcam capture, image
I/O, transforms, color, filtering, edges, thresholding, morphology,
contours/shapes, feature matching, object detection (faces / eyes / bodies /
QR), drawing, image arithmetic, template matching, and video processing.

- **PyPI:** [`farshid-mcp-imageProcessing`](https://pypi.org/project/farshid-mcp-imageProcessing/)
- **MCP Registry:** `io.github.pirahansiah/farshid-mcp-imageProcessing`
- **Python:** 3.14+
- **OS:** latest Windows 11, latest macOS, latest mainstream Linux (Ubuntu 24.04+/Fedora 41+)

## Install (PyPI)

```bash
pip install farshid-mcp-imageProcessing
farshid-mcp-imageprocessing          # runs the stdio MCP server
```

## Register in VS Code

Add this to your user or workspace `mcp.json`:

```jsonc
{
  "servers": {
    "imageProcessing": {
      "command": "farshid-mcp-imageprocessing",
      "type": "stdio"
    }
  }
}
```

Or, if you cloned the repo and want to run from source with the local `.venv`:

```bash
git clone https://github.com/pirahansiah/farshid-mcp-imageProcessing
cd farshid-mcp-imageProcessing
# Windows (PowerShell):
py -3.14 -m venv .venv ; .\.venv\Scripts\Activate.ps1
# macOS / Linux:
python3.14 -m venv .venv && source .venv/bin/activate

pip install -U pip
pip install -e .
```

`opencv-contrib-python` is used so the bundled Haar cascades and extra
algorithms are available.

## Quick start: the `/cv` Copilot prompt

This repo ships a workspace prompt file at
[.github/prompts/cv.prompt.md](.github/prompts/cv.prompt.md). In VS Code
Copilot Chat (Agent mode), type:

```
/cv take image from webcam and save it as gray scale 240 * 240
```

The agent will call `webcam_save`, `image_to_grayscale`, and `image_resize`
from this server to produce the requested file under `./.farshid/cv/`.

## Tool catalog

### Webcam / capture
- `webcam_capture(camera_index=0)` → returns a PNG image
- `webcam_save(output_path="", camera_index=0)`
- `webcam_preview(camera_index=0, seconds=10)` (local desktop window)
- `webcam_record(output_path, seconds=5, camera_index=0, fps=20)`

### Image I/O & info
- `image_show(path)` — return image to chat
- `image_info(path)` — shape, dtype, mean, file size
- `image_convert(input_path, output_path, quality=95)`

### Geometric transforms
- `image_resize(... width|height|scale, interpolation)`
- `image_crop(input_path, output_path, x, y, width, height)`
- `image_rotate(input_path, output_path, angle, scale=1, keep_size=False)`
- `image_flip(input_path, output_path, direction)`
- `image_pad(... top, bottom, left, right, border_type, color)`

### Color
- `image_to_grayscale`
- `color_convert(target=gray|hsv|hls|lab|ycrcb|rgb|bgr)`
- `adjust_brightness_contrast`
- `histogram_equalize(method=clahe|global)`
- `histogram_data(bins=32)`

### Filtering
- `blur_gaussian(ksize, sigma)`
- `blur_median(ksize)`
- `blur_bilateral(d, sigma_color, sigma_space)`
- `sharpen(amount)`
- `denoise(strength)`

### Edges / gradients
- `edges_canny(threshold1, threshold2)`
- `edges_sobel(ksize)`
- `edges_laplacian(ksize)`

### Thresholding & morphology
- `threshold(method=otsu|binary|binary_inv|adaptive_mean|adaptive_gaussian)`
- `morphology(op=erode|dilate|open|close|gradient|tophat|blackhat)`

### Contours & shapes
- `find_contours(input_path, output_path?, thresh, min_area)`
- `detect_circles(...)` — Hough
- `detect_lines(...)` — Probabilistic Hough
- `detect_corners(...)` — Shi-Tomasi

### Feature matching
- `feature_match(image1, image2, output_path?)` — ORB + BFMatcher

### Object detection (Haar)
- `detect_faces`
- `detect_eyes`
- `detect_bodies`
- `detect_qrcode`

### Drawing
- `draw_rectangle`, `draw_circle`, `draw_line`, `draw_text`

### Composition / arithmetic
- `image_blend(image1, image2, output_path, alpha)`
- `image_diff(image1, image2, output_path?)` → mean/max diff
- `image_concat(images, output_path, direction)`
- `template_match(image_path, template_path, output_path?, threshold)`

### Video
- `video_info(path)`
- `video_extract_frames(video_path, output_dir, every_n, max_frames, ext)`
- `video_thumbnail(video_path, output_path, time_seconds)`

## Build & publish

```bash
pip install -U build twine mcp-publisher
python -m build
twine upload dist/*
mcp-publisher login github
mcp-publisher publish .mcp/server.json
```

## OS notes

- **Windows 11 (latest):** webcam works out of the box; ensure *Settings →
  Privacy & security → Camera → Let desktop apps access your camera* is **On**.
- **macOS (latest):** the first webcam call triggers a system Camera
  permission prompt; grant it to the terminal/VS Code process.
- **Linux (latest):** requires a working `/dev/video*` device. Headless
  servers without a display cannot use `webcam_preview` (it opens an OpenCV
  window).

## Notes

- Never use `print()` in tool functions: stdout is the MCP protocol channel.
  Use `sys.stderr` (the `_log` helper at the bottom of `server.py`).
- `webcam_preview` opens a real desktop window — only works where the server
  has a display (not over plain SSH or in a headless container).
- All paths support `~` expansion. Output directories are created
  automatically.
- Tools that return annotated images take an optional `output_path`; when
  omitted they only return the JSON metadata.
