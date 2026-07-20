#!/bin/sh
set -eu

COMPONENT="init"

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  LEVEL="$1"
  shift
  printf "%s [%-5s] %s: %s\n" "$(timestamp)" "$LEVEL" "$COMPONENT" "$*"
}

info()  { log "INFO"  "$*"; }
warn()  { log "WARN"  "$*"; }
error() { log "ERROR" "$*"; }

START_TS="$(date +%s)"

INIT_FILE="/vault/keys/init.json"
ROOT_TOKEN_FILE="/vault/keys/root_token"
PLUGIN_PATH="/opt/openbao/plugins/secpsign"
TLS_CERT="/etc/openbao/tls/tls.crt"

export BAO_ADDR="${BAO_ADDR:-https://127.0.0.1:8200}"
export BAO_CACERT="${BAO_CACERT:-$TLS_CERT}"

#Wait for OpenBao API 

info "waiting for OpenBao API to become available  addr=$BAO_ADDR"

until bao status -format=json 2>/dev/null | jq -e 'has("initialized")' >/dev/null 2>&1; do
  sleep 2
done

info "OpenBao API is up"

#Init

STATUS_JSON="$(bao status -format=json 2>/dev/null || true)"
INITIALIZED="$(echo "$STATUS_JSON" | jq -r '.initialized // false')"

if [ "$INITIALIZED" != "true" ]; then
  info "first run detected — initialising OpenBao"

  bao operator init -format=json > "$INIT_FILE"
  jq -r '.root_token' "$INIT_FILE" > "$ROOT_TOKEN_FILE"
  chmod 600 "$INIT_FILE" "$ROOT_TOKEN_FILE"

  info "OpenBao initialised and unseal keys saved  init_file=$INIT_FILE"
else
  info "OpenBao was already initialised — skipping init"
fi

if [ ! -f "$INIT_FILE" ]; then
  error "init file not found at $INIT_FILE — cannot unseal without stored unseal keys"
  exit 1
fi

##Unseal

SEALED="$(bao status -format=json | jq -r '.sealed')"

if [ "$SEALED" = "true" ]; then
  UNSEAL_THRESHOLD="$(jq -r '.unseal_threshold // 3' "$INIT_FILE")"
  info "vault is sealed — unsealing  keys_required=$UNSEAL_THRESHOLD"

  bao operator unseal "$(jq -r '.unseal_keys_b64[0]' "$INIT_FILE")" >/dev/null
  bao operator unseal "$(jq -r '.unseal_keys_b64[1]' "$INIT_FILE")" >/dev/null
  bao operator unseal "$(jq -r '.unseal_keys_b64[2]' "$INIT_FILE")" >/dev/null

  info "unseal keys submitted — waiting for vault to confirm unsealed state"
else
  info "vault is already unsealed — skipping unseal"
fi

until [ "$(bao status -format=json | jq -r '.sealed')" = "false" ]; do
  info "still waiting for vault to finish unsealing…"
  sleep 2
done

export BAO_TOKEN
BAO_TOKEN="$(cat "$ROOT_TOKEN_FILE")"

info "vault is unsealed and ready"

#Register secpsign plugin 

if [ ! -f "$PLUGIN_PATH" ]; then
  error "plugin binary not found at $PLUGIN_PATH — cannot continue"
  exit 1
fi

SHA256="$(sha256sum "$PLUGIN_PATH" | awk '{print $1}')"
info "registering plugin  name=secpsign  sha256=$SHA256"

bao plugin register \
  -sha256="$SHA256" \
  -command=secpsign \
  secret \
  secpsign || true

#Enable secrets engines

if ! bao secrets list -format=json | jq -e 'has("ethereum/")' >/dev/null; then
  info "enabling ethereum secrets engine  path=ethereum  plugin=secpsign"
  bao secrets enable -path=ethereum -plugin-name=secpsign plugin
  info "ethereum secrets engine enabled"
else
  info "ethereum secrets engine already enabled — skipping"
fi

if ! bao secrets list -format=json | jq -e 'has("secret/")' >/dev/null; then
  info "enabling KV secrets engine  path=secret  type=kv-v2"
  bao secrets enable -path=secret kv-v2
  info "KV secrets engine enabled"
else
  info "KV secrets engine already enabled — skipping"
fi

#Import startup accounts

PRIVATE_KEYS_FILE="${PRIVATE_KEYS_FILE:-/run/secrets/private_keys}"
PERSISTENT_PRIVATE_KEYS_FILE="${PERSISTENT_PRIVATE_KEYS_FILE:-/run/secrets/private_keys}"

info "importing startup accounts  source=$PRIVATE_KEYS_FILE  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE"

# OPERATION_TRIGGER=startup distinguishes this automatic import from manual ones
# in the logs — every manage-accounts log line will show trigger=startup.
OPERATION_TRIGGER=startup \
PERSISTENT_PRIVATE_KEYS_FILE="$PERSISTENT_PRIVATE_KEYS_FILE" \
/opt/openbao/scripts/manage-accounts.sh import \
  --private-keys-file "$PRIVATE_KEYS_FILE" \
  --persist

END_TS="$(date +%s)"
DURATION="$((END_TS - START_TS))"
info "initialisation complete  duration=${DURATION}s"
