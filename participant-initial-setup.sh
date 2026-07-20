#!/usr/bin/env bash
set -euo pipefail

# Config
PYTHON=${PYTHON_BIN:-python3}
VENV_DIR=".venv"
ENV_EXAMPLE=".env.example"
ENV_FILE=".env"
SCRIPT="authentik/idp_generate_blueprint.py"

echo "==> Checking python3.10-venv..."
if $PYTHON -m ensurepip --version &>/dev/null; then
  echo "    Already available, skipping."
else
  echo "    Installing python3.10-venv..."
  sudo apt install -y --reinstall python3.10-venv
  echo "    Done."
fi

echo "==> Setting up Python environment..."

# 1. Create venv if it doesn't exist or is incomplete
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
  if [ -d "$VENV_DIR" ]; then
    echo "    Existing virtual environment is incomplete, recreating..."
    rm -rf "$VENV_DIR"
  else
    echo "    Creating virtual environment in $VENV_DIR/"
  fi
  $PYTHON -m venv "$VENV_DIR"
else
  echo "    Virtual environment already exists, skipping creation."
fi

# 2. Activate venv
source "$VENV_DIR/bin/activate"
echo "    Activated: $(which python)"

# 3. Upgrade pip (optional but recommended)
pip install --upgrade pip --quiet

# 4. Install dependencies
echo "==> Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet
echo "    Done."

# 5. Copy .env.example to .env (only if .env doesn't already exist)
if [ ! -f "$ENV_EXAMPLE" ]; then
  echo "==> Please create .env.example file "
  exit
else
  echo "==> .env already exists, skipping copy."
fi

# 6. Run the script
echo "==> Running $SCRIPT..."
python "$SCRIPT"

echo "==> All done!"