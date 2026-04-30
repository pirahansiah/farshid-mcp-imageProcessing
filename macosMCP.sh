#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"
VENV_PY="$VENV_DIR/bin/python"
MCP_EXE="$VENV_DIR/bin/farshid-mcp-imageprocessing"
VSCODE_DIR=".vscode"
MCP_JSON="$VSCODE_DIR/mcp.json"
PYTHON_CMD=""
USE_CONDA=0

write_venv_mcp_config() {
  mkdir -p "$VSCODE_DIR"
  cat > "$MCP_JSON" <<'EOF'
{
  "servers": {
    "imageProcessing": {
      "command": ".venv/bin/farshid-mcp-imageprocessing",
      "type": "stdio"
    }
  }
}
EOF
}

write_conda_mcp_config() {
  mkdir -p "$VSCODE_DIR"
  cat > "$MCP_JSON" <<'EOF'
{
  "servers": {
    "imageProcessing": {
      "command": "conda",
      "args": ["run", "--no-capture-output", "-n", "py314", "farshid-mcp-imageprocessing"],
      "type": "stdio"
    }
  }
}
EOF
}

ensure_python_installed() {
  if command -v python3.14 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3.14)"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python)"
    return 0
  fi

  if ! command -v brew >/dev/null 2>&1; then
    echo "Python was not found and Homebrew is not available."
    echo "Install Homebrew or Python 3.14+, then run this script again."
    return 1
  fi

  echo "Python was not found. Installing Python 3.14 with Homebrew..."
  if ! brew install python@3.14; then
    echo "Python 3.14 formula was not installed. Trying the latest Python 3..."
    brew install python
  fi

  if command -v python3.14 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3.14)"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
    return 0
  fi

  echo "Automatic Python installation failed."
  return 1
}

if command -v conda >/dev/null 2>&1; then
  if conda env list | awk '{print $1}' | grep -Fx "py314" >/dev/null 2>&1; then
    USE_CONDA=1
  fi
fi

if [[ "$USE_CONDA" == "1" ]]; then
  echo "Using conda environment py314..."
  conda run -n py314 python -m pip install --upgrade pip
  echo "Installing farshid_mcp_imageprocessing in conda env py314..."
  conda run -n py314 python -m pip install farshid_mcp_imageprocessing
  write_conda_mcp_config
  echo "Starting MCP server..."
  exec conda run --no-capture-output -n py314 farshid-mcp-imageprocessing
fi

ensure_python_installed

if [[ ! -x "$VENV_PY" ]]; then
  echo "Creating virtual environment with $PYTHON_CMD..."
  "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

echo "Upgrading pip in $VENV_DIR..."
"$VENV_PY" -m pip install --upgrade pip

echo "Installing farshid_mcp_imageprocessing in $VENV_DIR..."
"$VENV_PY" -m pip install farshid_mcp_imageprocessing

if [[ ! -x "$MCP_EXE" ]]; then
  echo "Expected MCP executable was not created:"
  echo "$MCP_EXE"
  exit 1
fi

write_venv_mcp_config

echo "Starting MCP server..."
exec "$MCP_EXE"