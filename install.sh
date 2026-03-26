#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"

is_supported_python() {
  local py_bin="$1"
  "$py_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
}

pick_python() {
  local candidates=(python3.12 python3.11 python3.10 python3)
  local candidate
  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if is_supported_python "$candidate"; then
        echo "$candidate"
        return 0
      fi
    fi
  done

  echo "No supported Python (>=3.10) found in PATH." >&2
  echo "Install Python 3.10+ and rerun this script." >&2
  return 1
}

PYTHON_BIN="$(pick_python)"

echo "Using Python: $PYTHON_BIN"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Using existing virtual environment at $VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"

echo "Upgrading pip/setuptools/wheel"
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

echo "Installing runtime dependencies"
"$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"

echo "Installing project in editable mode with dev dependencies"
"$VENV_PYTHON" -m pip install -e "$PROJECT_ROOT[dev]"

echo
echo "Install complete."
echo "Activate with: source .venv/bin/activate"
echo "Then run: ipb --help"
