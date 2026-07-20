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

# 5. Sync Authentik env vars from .env.example → .env
AUTHENTIK_KEYS=(
  AUTHENTIK_APP_NAME
  AUTHENTIK_APP_SLUG
  AUTHENTIK_PROVIDER_NAME
  AUTHENTIK_REDIRECT_URIS
  AUTHENTIK_LOGOUT_URI
  AUTHENTIK_OUTPUT_FILE
  AUTHENTIK_ADMIN_EMAIL
  AUTHENTIK_BASE_URL
)
 
if [ ! -f "$ENV_FILE" ]; then
  echo "==> No .env found, copying $ENV_EXAMPLE to $ENV_FILE"
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "    .env created."
else
  echo "==> Syncing Authentik variables from $ENV_EXAMPLE to $ENV_FILE..."
  MISSING=false
  for KEY in "${AUTHENTIK_KEYS[@]}"; do
    if ! grep -q "^${KEY}=" "$ENV_FILE"; then
      MISSING=true
      break
    fi
  done
 
  if [ "$MISSING" = true ]; then
    # One or more keys missing — append all from .env.example
    echo "    Missing keys detected, appending from $ENV_EXAMPLE..."
    echo "" >> "$ENV_FILE"
    cat "$ENV_EXAMPLE" >> "$ENV_FILE"
  else
    echo "    All Authentik keys already present, skipping sync."
  fi
  echo "    Done."
fi

# 6. Run the script
echo "==> Running $SCRIPT..."
python "$SCRIPT"

# 7. Copy generated blueprint to authentik blueprints directory
BLUEPRINTS_DIR="$(pwd)/docker-compose/authentik/blueprints"
OUTPUT_FILE=$(grep "^AUTHENTIK_OUTPUT_FILE=" "$ENV_FILE" | cut -d'=' -f2-)
 
if [ -n "$OUTPUT_FILE" ] && [ -f "$OUTPUT_FILE" ]; then
  rm -rf "$BLUEPRINTS_DIR"
  mkdir -p "$BLUEPRINTS_DIR"
  mv "$OUTPUT_FILE" "$BLUEPRINTS_DIR/"
  echo "==> Moved $OUTPUT_FILE to $BLUEPRINTS_DIR/"
else
  echo "[ERROR] Blueprint file '$OUTPUT_FILE' not found. Did the script fail?"
  exit 1
fi

mv "$ENV_FILE" "$(pwd)/docker-compose"

echo "==> All done!"