# Install / run guide (Windows 11, macOS latest, Linux latest)

This project (`farshid-mcp-imageProcessing`) exposes OpenCV functionality as
MCP tools (`webcam_capture`, `webcam_save`, `webcam_preview`, `webcam_record`,
plus ~35 image-processing tools). Use a single local **`.venv`** with
**Python 3.14**.

> All generated artifacts (snapshots, recordings, intermediate images, test
> data) are written under `./.farshid/`. That folder is git-ignored.

## 1. Prerequisites

- **Python 3.14** installed and on `PATH`
  - Windows: `winget install Python.Python.3.14`
  - macOS: `brew install python@3.14`
  - Linux: your distro's 3.14 package, or `pyenv install 3.14.0`
- A working webcam (only required for the `webcam_*` tools)
- VS Code with GitHub Copilot Chat (Agent mode)

## 2. Create the `.venv`

### Windows 11 (PowerShell)

```powershell
cd <path-to-repo>
py -3.14 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned   # one-time
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

### macOS / Linux (latest)

```bash
cd <path-to-repo>
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify:

```bash
python -c "import cv2, mcp; print('cv2', cv2.__version__)"
```

## 3. Configure VS Code MCP

[.vscode/mcp.json](.vscode/mcp.json) launches the server from the local venv:

```json
{
  "servers": {
    "imageProcessing": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "farshid_mcp_imageprocessing.server"]
    }
  }
}
```

On macOS/Linux change `command` to
`${workspaceFolder}/.venv/bin/python`.

## 4. Try the `/cv` slash command

Open Copilot Chat in **Agent** mode and type:

```
/cv take image from webcam and save it as gray scale 240 * 240
```

The prompt file at [.github/prompts/cv.prompt.md](.github/prompts/cv.prompt.md)
tells the agent to call this server's tools and write the result to
`./.farshid/cv/<timestamp>_gray_240x240.png`.

## 5. Run with the MCP Inspector (debug)

```bash
mcp dev -m farshid_mcp_imageprocessing.server
```

To skip auth for local-only testing:

```bash
# PowerShell
$env:DANGEROUSLY_OMIT_AUTH = "true" ; mcp dev -m farshid_mcp_imageprocessing.server
# bash/zsh
DANGEROUSLY_OMIT_AUTH=true mcp dev -m farshid_mcp_imageprocessing.server
```

## 6. Common issues

- **`ModuleNotFoundError: No module named 'mcp'`** — install into the *exact*
  venv used by `mcp.json`:
  `python -m pip install -e .`.
- **`Could not open webcam`** — another app (Teams, Zoom, Camera) is holding
  the device. Close it, or try `camera_index=1`.
- **No window appears at all** — `cv2.imshow` requires a local desktop. It
  will not work over plain SSH, in WSL without an X server, or inside a
  headless container.
- **Camera permission denied (macOS)** — grant access in *System Settings →
  Privacy & Security → Camera* to the process running the server (Terminal,
  iTerm, or Code).
- **Never use `print()` inside tools** — stdout is the MCP protocol channel.
  Use `sys.stderr` or `logging` instead.
