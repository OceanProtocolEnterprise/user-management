#!/bin/sh
set -eu

COMPONENT="entrypoint"

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  LEVEL="$1"
  shift
  printf "%s [%-5s] %s: %s\n" "$(timestamp)" "$LEVEL" "$COMPONENT" "$*"
}

info()  { log "INFO"  "$*"; }
warn()  { log "WARN"  "$*"; }
error() { log "ERROR" "$*"; }

TLS_CERT="/etc/openbao/tls/tls.crt"
TLS_KEY="/etc/openbao/tls/tls.key"


if [ -n "${TLS_CERT_SOURCE:-}" ] && [ -f "$TLS_CERT_SOURCE" ]; then
  info "copying provided TLS certificate  source=$TLS_CERT_SOURCE  dest=$TLS_CERT"
  cp "$TLS_CERT_SOURCE" "$TLS_CERT"
fi

if [ -n "${TLS_KEY_SOURCE:-}" ] && [ -f "$TLS_KEY_SOURCE" ]; then
  info "copying provided TLS private key  source=$TLS_KEY_SOURCE  dest=$TLS_KEY"
  cp "$TLS_KEY_SOURCE" "$TLS_KEY"
fi

if [ ! -f "$TLS_CERT" ] || [ ! -f "$TLS_KEY" ]; then
  info "no TLS certificate found — generating a self-signed one  valid_days=3650"

  if ! openssl req -x509 -nodes -newkey rsa:4096 \
      -keyout "$TLS_KEY" \
      -out    "$TLS_CERT" \
      -days   3650 \
      -subj   "/CN=openbao" \
      -addext "subjectAltName=DNS:openbao,DNS:localhost,IP:127.0.0.1" \
      2>&1; then
    error "failed to generate self-signed TLS certificate — cannot start"
    exit 1
  fi

  info "self-signed TLS certificate generated  cert=$TLS_CERT"
else
  info "using existing TLS certificate  cert=$TLS_CERT"
fi

chmod 600 "$TLS_KEY"

export BAO_ADDR="${BAO_ADDR:-https://127.0.0.1:8200}"
export BAO_CACERT="${BAO_CACERT:-$TLS_CERT}"

info "starting OpenBao  config=/etc/openbao/openbao.hcl  addr=$BAO_ADDR"

bao server -config=/etc/openbao/openbao.hcl &
BAO_PID="$!"

info "OpenBao server process started  pid=$BAO_PID"


if ! /opt/openbao/scripts/init-vault.sh; then
  STATUS="$?"
  error "initialisation script failed  exit_code=$STATUS — stopping OpenBao (pid=$BAO_PID)"
  kill "$BAO_PID" 2>/dev/null || true
  wait "$BAO_PID" 2>/dev/null || true
  exit "$STATUS"
fi

info "initialisation complete — OpenBao is ready"

wait "$BAO_PID"
