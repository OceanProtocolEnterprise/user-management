#!/usr/bin/env bash
set -euo pipefail

# Config
PYTHON=${PYTHON_BIN:-python3}
VENV_DIR=".venv"
ENV_CONFIG=".env.config"
ENV_TEMP_FILE=".env.tmp"
BLUEPRINT_SCRIPT="authentik/dataspace_operator_blueprint.py"
CONFIG_SCRIPT="dataspace_operator_environment_configuration.py"
COMPOSE_DIR="$(pwd)/docker-compose"

# Distro detection
detect_distro() {
  if [ -f /etc/os-release ]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    echo "${ID:-unknown}"
  elif [ -f /etc/redhat-release ]; then
    echo "rhel"
  elif [ -f /etc/debian_version ]; then
    echo "debian"
  else
    echo "unknown"
  fi
}

# Install a package using the distro-appropriate package manager.
# Usage: pkg_install <package-name>
pkg_install() {
  local pkg="$1"
  local distro
  distro="$(detect_distro)"

  case "$distro" in
    ubuntu | debian | linuxmint | pop | elementary | kali | raspbian)
      echo "    [apt] Installing $pkg..."
      sudo apt-get install -y --reinstall "$pkg"
      ;;
    fedora)
      echo "    [dnf] Installing $pkg..."
      sudo dnf install -y "$pkg"
      ;;
    centos | rhel | almalinux | rocky | ol)
      if command -v dnf &>/dev/null; then
        echo "    [dnf] Installing $pkg..."
        sudo dnf install -y "$pkg"
      else
        echo "    [yum] Installing $pkg..."
        sudo yum install -y "$pkg"
      fi
      ;;
    opensuse* | sles)
      echo "    [zypper] Installing $pkg..."
      sudo zypper install -y "$pkg"
      ;;
    arch | manjaro | endeavouros | garuda)
      echo "    [pacman] Installing $pkg..."
      sudo pacman -Sy --noconfirm "$pkg"
      ;;
    alpine)
      echo "    [apk] Installing $pkg..."
      sudo apk add --no-cache "$pkg"
      ;;
    *)
      echo "    [WARN] Unknown distro '$distro'. Attempting apt-get as fallback..."
      sudo apt-get install -y --reinstall "$pkg" || {
        echo "    [ERROR] Could not install $pkg. Please install it manually."
        exit 1
      }
      ;;
  esac
}

# Map the generic 'python3-venv' package to the distro-specific name.
python_venv_package() {
  local distro
  distro="$(detect_distro)"
  local pyver
  pyver="$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

  case "$distro" in
    ubuntu | debian | linuxmint | pop | elementary | kali | raspbian)
      echo "python3-venv"
      ;;
    fedora | centos | rhel | almalinux | rocky | ol)
      echo "python${pyver}-venv" 2>/dev/null || echo "python3-venv"
      ;;
    opensuse* | sles)
      echo "python3-venv"
      ;;
    arch | manjaro | endeavouros | garuda)
      echo "python"
      ;;
    alpine)
      echo "py3-virtualenv"
      ;;
    *)
      echo "python3-venv"
      ;;
  esac
}

# Main
echo "==> Detected Linux distribution: $(detect_distro)"

echo "==> Checking python3-venv..."
if $PYTHON -m ensurepip --version &>/dev/null; then
  echo "    Already available, skipping."
else
  echo "    Installing python3-venv..."
  pkg_install "$(python_venv_package)"
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

# 5. Validate Authentik variables in .env.config
AUTHENTIK_KEYS=(
  AUTHENTIK_APP_SLUG
  AUTHENTIK_PROVIDER_NAME
  AUTHENTIK_OUTPUT_FILE
)

if [ ! -f "$ENV_CONFIG" ]; then
  echo "[ERROR] $ENV_CONFIG not found in $(pwd). Cannot proceed."
  exit 1
fi

echo "==> Validating Authentik variables in $ENV_CONFIG..."
MISSING_KEYS=()
for KEY in "${AUTHENTIK_KEYS[@]}"; do
  if ! grep -q "^${KEY}=" "$ENV_CONFIG"; then
    MISSING_KEYS+=("$KEY")
  fi
done

if [ "${#MISSING_KEYS[@]}" -gt 0 ]; then
  echo "    [WARN] Missing keys in $ENV_CONFIG (blueprint will use defaults):"
  for KEY in "${MISSING_KEYS[@]}"; do
    echo "      - $KEY"
  done
else
  echo "    All Authentik keys present."
fi
echo "    Done."

# 6. Run the blueprint script (reads .env.config, generates .env with credentials)
echo "==> Running $BLUEPRINT_SCRIPT..."
python "$BLUEPRINT_SCRIPT"

# 7. Run environment configuration (reads .env.config + .env, generates .env.* files)
echo "==> Running $CONFIG_SCRIPT..."
python "$CONFIG_SCRIPT"

# 8. Copy generated blueprint to authentik blueprints directory
BLUEPRINTS_DIR="${COMPOSE_DIR}/authentik/blueprints"
OUTPUT_FILE=$(grep "^AUTHENTIK_OUTPUT_FILE=" "$ENV_CONFIG" | head -1 | cut -d'=' -f2-)

if [ -n "$OUTPUT_FILE" ] && [ -f "$OUTPUT_FILE" ]; then
  rm -rf "$BLUEPRINTS_DIR"
  mkdir -p "$BLUEPRINTS_DIR"
  mv "$OUTPUT_FILE" "$BLUEPRINTS_DIR/"
  echo "==> Moved $OUTPUT_FILE to $BLUEPRINTS_DIR/"
else
  echo "[ERROR] Blueprint file '$OUTPUT_FILE' not found. Did the script fail?"
  exit 1
fi

# 9. Distribute .env files to docker-compose subdirectories
echo "==> Distributing .env files to docker-compose..."
distribute_env() {
  local src="$1" dest="${COMPOSE_DIR}/$2"
  if [ -f "$src" ]; then
    mkdir -p "$dest"
    mv "$src" "${dest}/"
    echo "    $src -> ${dest}/"
  else
    echo "    [SKIP] $src not found"
  fi
}

distribute_env ".env.wallet-ui"     "wallet-ui"
distribute_env ".env.wallet-api"    "wallet-api"
distribute_env ".env.traefik"       "traefik"
distribute_env ".env.openbao"       "openbao"
distribute_env ".env.signer-server" "signer-server"
distribute_env ".env.authentik"     "authentik"
distribute_env ".env.postgres"      "postgres-init"

# 10. Clean up intermediate .env (credentials already consumed by config script)
if [ -f "$ENV_TEMP_FILE" ]; then
  rm -f "$ENV_TEMP_FILE"
  echo "==> Removed intermediate $ENV_TEMP_FILE"
fi

echo "==> All done!"