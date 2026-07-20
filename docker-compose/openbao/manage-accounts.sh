#!/bin/sh
set -eu

# =============================================================================
# manage-accounts.sh — import, delete, or list Ethereum accounts in OpenBao
#
# Usage:
#   manage-accounts.sh import [--private-keys-file <path>] [--persist|--no-persist]
#   manage-accounts.sh delete <wallet_id>
#   manage-accounts.sh list [--verify]
#
# Examples:
#   manage-accounts.sh import --private-keys-file /tmp/new_keys.txt --persist
#   manage-accounts.sh import --no-persist
#   manage-accounts.sh delete 5
#   manage-accounts.sh list
#   manage-accounts.sh list --verify
# =============================================================================

# ── Logging ───────────────────────────────────────────────────────────────────
# OPERATION_ID:      short random token included in every log line from this run.
#                    Lets you isolate all lines from one invocation: grep "op=xxxx"
# OPERATION_TRIGGER: who started this run.
#                    Set to "startup" by init-vault.sh; defaults to "manual".
# COMPONENT:         set after the subcommand is parsed so it reflects the action.

OPERATION_ID="$(cat /dev/urandom | tr -dc 'a-z0-9' | head -c 8 2>/dev/null || echo "00000000")"
OPERATION_TRIGGER="${OPERATION_TRIGGER:-manual}"
COMPONENT="manage-accounts"

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  LEVEL="$1"
  shift
  LINE="$(printf "%s [%-5s] %s: op=%s  trigger=%s  %s" \
    "$(timestamp)" "$LEVEL" "$COMPONENT" "$OPERATION_ID" "$OPERATION_TRIGGER" "$*")"

  printf "%s\n" "$LINE"

  if [ "$OPERATION_TRIGGER" = "manual" ] && [ -w /proc/1/fd/1 ]; then
    printf "%s\n" "$LINE" > /proc/1/fd/1 || true
  fi
}

info()  { log "INFO"  "$*"; }
warn()  { log "WARN"  "$*"; }
error() { log "ERROR" "$*"; }


if [ $# -eq 0 ]; then
  error "subcommand required"
  echo "Usage:"
  echo "  manage-accounts.sh import [--private-keys-file <path>] [--persist|--no-persist]"
  echo "  manage-accounts.sh delete <wallet_id>"
  echo "  manage-accounts.sh list [--verify]"
  exit 1
fi

SUBCOMMAND="$1"
shift

case "$SUBCOMMAND" in
  import) COMPONENT="import-account" ;;
  delete) COMPONENT="delete-account" ;;
  list)   COMPONENT="list-accounts"  ;;
  *)
    error "unknown subcommand: $SUBCOMMAND  (valid: import, delete, list)"
    exit 1
    ;;
esac

START_TS="$(date +%s)"

ROOT_TOKEN_FILE="/vault/keys/root_token"
ADDRESS_FILE="/vault/keys/addresses.json"
REGISTRY_FILE="/vault/keys/private_key_registry.json"
TLS_CERT="/etc/openbao/tls/tls.crt"
WORK_DIR="/vault/keys/tmp"

mkdir -p "$WORK_DIR"

export BAO_ADDR="${BAO_ADDR:-https://127.0.0.1:8200}"
export BAO_CACERT="${BAO_CACERT:-$TLS_CERT}"

if [ -z "${BAO_TOKEN:-}" ] && [ -f "$ROOT_TOKEN_FILE" ]; then
  export BAO_TOKEN
  BAO_TOKEN="$(cat "$ROOT_TOKEN_FILE")"
fi

if [ -z "${BAO_TOKEN:-}" ]; then
  error "BAO_TOKEN is not set and $ROOT_TOKEN_FILE does not exist — cannot authenticate"
  exit 1
fi

normalize_pk() {
  local key="$1"
  key="$(printf "%s" "$key" | tr '[:upper:]' '[:lower:]')"
  key="$(printf "%s" "$key" | sed 's/^0x//')"
  printf "0x%s" "$key"
}

validate_pk() {
  local key="$1" source_file="$2" line_number="$3"
  python3 - "$key" "$source_file" "$line_number" <<'PY'
import re, sys

key         = sys.argv[1].strip()
source_file = sys.argv[2]
line_number = sys.argv[3]

SECP256K1_ORDER = int(
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16
)

def fail(reason):
    print(f"{source_file}:{line_number}:{reason}")
    sys.exit(1)

if not re.fullmatch(r"0x[0-9a-f]{64}", key):
    fail("invalid format — expected 0x followed by 64 lowercase hex characters")

value = int(key[2:], 16)

if value == 0:
    fail("key value is zero — not a valid private key")

if value >= SECP256K1_ORDER:
    fail("key value exceeds the secp256k1 curve order — not a valid private key")
PY
}

pk_hash() {
  printf "%s" "$1" | sha256sum | awk '{print $1}'
}

count_keys_in_file() {
  local file="$1"
  [ -f "$file" ] || { echo "0"; return 0; }
  grep -cve '^[[:space:]]*$' "$file" || true
}


next_id() {
  jq -r 'keys | map(tonumber) | max // 0' "$ADDRESS_FILE"
}

registry_has_hash() {
  jq -e --arg hash "$1" 'has($hash)' "$REGISTRY_FILE" >/dev/null
}

registry_address_for_hash() {
  jq -r --arg hash "$1" '.[$hash].address // empty' "$REGISTRY_FILE"
}

registry_id_for_hash() {
  jq -r --arg hash "$1" '.[$hash].id // empty' "$REGISTRY_FILE"
}

registry_has_address() {
  jq -e --arg address "$1" '
    to_entries[] | select(.value.address | ascii_downcase == ($address | ascii_downcase))
  ' "$REGISTRY_FILE" >/dev/null
}

registry_hash_for_address() {
  jq -r --arg address "$1" '
    to_entries[]
    | select(.value.address | ascii_downcase == ($address | ascii_downcase))
    | .key
  ' "$REGISTRY_FILE" | head -n 1
}

delete_registry_entries_for_address_except_hash() {
  local address="$1" keep_hash="$2" tmp_file
  tmp_file="$(mktemp "$WORK_DIR/registry-clean.XXXXXX")"

  jq --arg address "$address" --arg keep_hash "$keep_hash" '
    with_entries(
      select(
        .key == $keep_hash or
        (.value.address | ascii_downcase) != ($address | ascii_downcase)
      )
    )
  ' "$REGISTRY_FILE" > "$tmp_file"

  mv "$tmp_file" "$REGISTRY_FILE"
}


address_exists_locally() {
  jq -e --arg address "$1" '
    to_entries[] | select(.value | ascii_downcase == ($address | ascii_downcase))
  ' "$ADDRESS_FILE" >/dev/null
}

id_for_address() {
  jq -r --arg address "$1" '
    to_entries[]
    | select(.value | ascii_downcase == ($address | ascii_downcase))
    | .key
  ' "$ADDRESS_FILE" | head -n 1
}

save_address() {
  local id="$1" address="$2" tmp_file
  tmp_file="$(mktemp "$WORK_DIR/address.XXXXXX")"
  jq --arg id "$id" --arg address "$address" \
    '. + {($id): $address}' "$ADDRESS_FILE" > "$tmp_file"
  mv "$tmp_file" "$ADDRESS_FILE"
}

save_registry_entry() {
  local key_hash="$1" id="$2" address="$3" tmp_file
  tmp_file="$(mktemp "$WORK_DIR/registry.XXXXXX")"

  jq --arg hash "$key_hash" --arg id "$id" --arg address "$address" '
    . + { ($hash): { id: ($id | tonumber), address: $address } }
  ' "$REGISTRY_FILE" > "$tmp_file"

  mv "$tmp_file" "$REGISTRY_FILE"
}


bao_accounts_json() {
  local raw
  raw="$(bao list -format=json ethereum/accounts 2>/dev/null || true)"
  [ -z "$raw" ] && { echo "[]"; return 0; }

  echo "$raw" | jq -c '
    if type == "array" then .
    elif type == "object" and has("keys") then .keys
    else []
    end
  ' 2>/dev/null || echo "[]"
}

bao_account_exists() {
  local address="$1" accounts_json="$2"
  echo "$accounts_json" | jq -e --arg address "$address" '
    map(ascii_downcase) | index($address | ascii_downcase)
  ' >/dev/null
}

# IMPORT

cmd_import() {
  local PRIVATE_KEYS_FILE="${PRIVATE_KEYS_FILE:-/run/secrets/private_keys}"
  local PERSISTENT_PRIVATE_KEYS_FILE="${PERSISTENT_PRIVATE_KEYS_FILE:-/run/secrets/private_keys}"
  local PERSIST="true"


  while [ $# -gt 0 ]; do
    case "$1" in
      --private-keys-file|--pk-file)
        PRIVATE_KEYS_FILE="${2:-}"
        shift 2
        ;;
      --persist)
        PERSIST="true"
        shift
        ;;
      --no-persist)
        PERSIST="false"
        shift
        ;;
      *)
        error "unknown argument: $1"
        exit 1
        ;;
    esac
  done

  if [ -z "$PRIVATE_KEYS_FILE" ]; then
    error "private keys file path is empty — set PRIVATE_KEYS_FILE or use --private-keys-file"
    exit 1
  fi

  if [ ! -f "$PRIVATE_KEYS_FILE" ]; then
    warn "private keys file not found — nothing to import  file=$PRIVATE_KEYS_FILE"
    exit 0
  fi

  [ -f "$ADDRESS_FILE"  ] || echo "{}" > "$ADDRESS_FILE"
  [ -f "$REGISTRY_FILE" ] || echo "{}" > "$REGISTRY_FILE"


  same_file() {
    local left="$1" right="$2"
    [ -e "$left"  ] || return 1
    [ -e "$right" ] || return 1
    [ "$(readlink -f "$left")" = "$(readlink -f "$right")" ]
  }

  normalize_to_temp_file() {
    local source_file="$1" target_file="$2"

    : > "$target_file"

    local line_number=0 valid_count=0 unique_count=0 duplicate_count=0
    local raw_normalized_file seen_file

    raw_normalized_file="$(mktemp "$WORK_DIR/raw-normalized.XXXXXX")"
    seen_file="$(mktemp "$WORK_DIR/seen-hashes.XXXXXX")"
    : > "$raw_normalized_file"
    : > "$seen_file"

    while IFS= read -r raw_key || [ -n "$raw_key" ]; do
      line_number=$((line_number + 1))

      raw_clean_key="$(printf "%s" "$raw_key" | tr -d ' \n\r\t')"
      [ -z "$raw_clean_key" ] && continue

      clean_key="$(normalize_pk "$raw_clean_key")"

      if ! validation_output="$(validate_pk "$clean_key" "$source_file" "$line_number" 2>&1)"; then
        error "invalid key — aborting  file=$source_file  line=$line_number  reason=$validation_output"
        rm -f "$raw_normalized_file" "$seen_file"
        exit 1
      fi

      valid_count=$((valid_count + 1))
      key_hash="$(pk_hash "$clean_key")"

      if grep -q "^$key_hash " "$seen_file"; then
        first_seen_line="$(grep "^$key_hash " "$seen_file" | awk '{print $2}' | head -n 1)"
        duplicate_count=$((duplicate_count + 1))
        warn "duplicate key ignored  file=$source_file  line=$line_number  first_seen_at_line=$first_seen_line  key_hash=$key_hash"
        continue
      fi

      printf "%s %s\n" "$key_hash" "$line_number" >> "$seen_file"
      printf "%s\n"    "$clean_key"                >> "$raw_normalized_file"
      unique_count=$((unique_count + 1))
    done < "$source_file"

    cat "$raw_normalized_file" > "$target_file"
    rm -f "$raw_normalized_file" "$seen_file"

    info "source file validated  file=$source_file  valid=$valid_count  unique=$unique_count  duplicates_skipped=$duplicate_count"
  }

  normalize_file_in_place() {
    local file="$1"
    [ -f "$file" ] || return 0

    local tmp_file
    tmp_file="$(mktemp "$WORK_DIR/normalize.XXXXXX")"
    normalize_to_temp_file "$file" "$tmp_file"
    cat "$tmp_file" > "$file"
    rm -f "$tmp_file"
  }


  PERSISTENT_HASHES=""

  load_persistent_hashes() {
    PERSISTENT_HASHES=""
    [ -f "$PERSISTENT_PRIVATE_KEYS_FILE" ] || return 0

    while IFS= read -r raw_key || [ -n "$raw_key" ]; do
      raw_clean_key="$(printf "%s" "$raw_key" | tr -d ' \n\r\t')"
      [ -z "$raw_clean_key" ] && continue
      clean_key="$(normalize_pk "$raw_clean_key")"
      h="$(pk_hash "$clean_key")"
      PERSISTENT_HASHES="${PERSISTENT_HASHES} ${h} "
    done < "$PERSISTENT_PRIVATE_KEYS_FILE"
  }

  persistent_has_hash() {
    case "$PERSISTENT_HASHES" in
      *" $1 "*) return 0 ;;
      *)        return 1 ;;
    esac
  }

  persist_key_if_missing() {
    local key="$1"
    local key_hash
    key_hash="$(pk_hash "$key")"

    [ "$PERSIST" = "true" ] || return 1
    [ -f "$PERSISTENT_PRIVATE_KEYS_FILE" ] || touch "$PERSISTENT_PRIVATE_KEYS_FILE"

    persistent_has_hash "$key_hash" && return 1

    printf "%s\n" "$key" >> "$PERSISTENT_PRIVATE_KEYS_FILE"
    PERSISTENT_HASHES="${PERSISTENT_HASHES} ${key_hash} "
    info "key added to persistent file  key_hash=$key_hash  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE"
    return 0
  }


  local PERSISTENT_SOURCE="false"
  same_file "$PRIVATE_KEYS_FILE" "$PERSISTENT_PRIVATE_KEYS_FILE" && PERSISTENT_SOURCE="true"

  info "starting import  source=$PRIVATE_KEYS_FILE  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE  persist=$PERSIST  persistent_source=$PERSISTENT_SOURCE"

  # Validate and normalise the source file into a temp working copy
  local IMPORT_WORK_FILE
  IMPORT_WORK_FILE="$(mktemp "$WORK_DIR/import.XXXXXX")"
  normalize_to_temp_file "$PRIVATE_KEYS_FILE" "$IMPORT_WORK_FILE"

  # Normalise the persistent file in place (deduplication, formatting)
  if [ "$PERSIST" = "true" ] && [ -f "$PERSISTENT_PRIVATE_KEYS_FILE" ]; then
    info "normalising persistent keys file  file=$PERSISTENT_PRIVATE_KEYS_FILE"
    normalize_file_in_place "$PERSISTENT_PRIVATE_KEYS_FILE"
  fi

  load_persistent_hashes

  # Fetch current vault accounts once — updated locally after each import
  local ACCOUNTS_JSON ACCOUNT_COUNT
  ACCOUNTS_JSON="$(bao_accounts_json)"
  ACCOUNT_COUNT="$(echo "$ACCOUNTS_JSON" | jq 'length')"
  info "loaded existing vault accounts  count=$ACCOUNT_COUNT"

  local IMPORTED=0 SKIPPED=0 REPAIRED=0 PERSISTENT_KEYS_ADDED=0 REGISTRY_REPAIRS=0

  while IFS= read -r clean_key || [ -n "$clean_key" ]; do
    [ -z "$clean_key" ] && continue

    local key_hash
    key_hash="$(pk_hash "$clean_key")"


    if registry_has_hash "$key_hash"; then
      local known_address known_id
      known_address="$(registry_address_for_hash "$key_hash")"
      known_id="$(registry_id_for_hash "$key_hash")"

      if [ -n "$known_address" ] && bao_account_exists "$known_address" "$ACCOUNTS_JSON"; then
        if persist_key_if_missing "$clean_key"; then
          PERSISTENT_KEYS_ADDED=$((PERSISTENT_KEYS_ADDED + 1))
        fi
        info "skipped — already imported  id=$known_id  address=$known_address  key_hash=$key_hash"
        SKIPPED=$((SKIPPED + 1))
        continue
      fi

      warn "registry entry exists but vault account is missing — will re-import  id=$known_id  address=$known_address  key_hash=$key_hash"
    fi


    local key_without_prefix response address
    key_without_prefix="$(printf "%s" "$clean_key" | sed 's/^0x//')"
    response="$(bao write -format=json ethereum/accounts privateKey="$key_without_prefix")"
    address="$(echo "$response" | jq -r '.data.address // empty')"

    if [ -z "$address" ]; then
      error "vault did not return an address — import failed  key_hash=$key_hash"
      echo "$response" | jq .
      rm -f "$IMPORT_WORK_FILE"
      exit 1
    fi


    local id
    if address_exists_locally "$address"; then
      id="$(id_for_address "$address")"

      if registry_has_address "$address"; then
        local old_hash
        old_hash="$(registry_hash_for_address "$address")"

        if [ "$old_hash" != "$key_hash" ]; then
          warn "address exists with a different key hash — replacing registry entry  id=$id  address=$address  old_hash=$old_hash  new_hash=$key_hash"
          delete_registry_entries_for_address_except_hash "$address" "$key_hash"
          REGISTRY_REPAIRS=$((REGISTRY_REPAIRS + 1))
        fi
      fi

      REPAIRED=$((REPAIRED + 1))
      info "repaired wallet metadata  id=$id  address=$address  key_hash=$key_hash"
    else
      id="$(( $(next_id) + 1 ))"
      save_address "$id" "$address"
      IMPORTED=$((IMPORTED + 1))
      info "new account imported  id=$id  address=$address  key_hash=$key_hash"
    fi


    bao kv put "secret/wallets/by-id/$id" address="$address" >/dev/null
    info "KV mapping saved  path=secret/wallets/by-id/$id  address=$address"

    save_registry_entry "$key_hash" "$id" "$address"
    info "registry entry saved  id=$id  address=$address  key_hash=$key_hash"

    if persist_key_if_missing "$clean_key"; then
      PERSISTENT_KEYS_ADDED=$((PERSISTENT_KEYS_ADDED + 1))
    fi

    ACCOUNTS_JSON="$(echo "$ACCOUNTS_JSON" | jq --arg addr "$address" '. + [$addr]')"
    ACCOUNT_COUNT=$((ACCOUNT_COUNT + 1))

  done < "$IMPORT_WORK_FILE"

  # Final normalisation pass on the persistent file
  if [ "$PERSIST" = "true" ]; then
    normalize_file_in_place "$PERSISTENT_PRIVATE_KEYS_FILE"
  fi

  rm -f "$IMPORT_WORK_FILE"

  local PERSISTENT_KEYS_TOTAL="0"
  if [ "$PERSIST" = "true" ] && [ -f "$PERSISTENT_PRIVATE_KEYS_FILE" ]; then
    PERSISTENT_KEYS_TOTAL="$(count_keys_in_file "$PERSISTENT_PRIVATE_KEYS_FILE")"
  fi

  local END_TS DURATION
  END_TS="$(date +%s)"
  DURATION="$((END_TS - START_TS))"

  if [ "$PERSISTENT_SOURCE" = "true" ]; then
    info "import complete  imported=$IMPORTED  repaired=$REPAIRED  skipped=$SKIPPED  total_accounts=$ACCOUNT_COUNT  persistent_keys_total=$PERSISTENT_KEYS_TOTAL  registry_repairs=$REGISTRY_REPAIRS  duration=${DURATION}s"
  else
    info "import complete  imported=$IMPORTED  repaired=$REPAIRED  skipped=$SKIPPED  total_accounts=$ACCOUNT_COUNT  persistent_keys_added=$PERSISTENT_KEYS_ADDED  persistent_keys_total=$PERSISTENT_KEYS_TOTAL  registry_repairs=$REGISTRY_REPAIRS  duration=${DURATION}s"
  fi
}

# DELETE

cmd_delete() {
  local PERSISTENT_PRIVATE_KEYS_FILE="${PERSISTENT_PRIVATE_KEYS_FILE:-/run/secrets/private_keys}"

  local WALLET_ID="${1:-}"

  if [ -z "$WALLET_ID" ]; then
    error "wallet ID is required"
    echo "Usage:   manage-accounts.sh delete <wallet_id>"
    echo "Example: manage-accounts.sh delete 1"
    exit 1
  fi

  if [ ! -f "$ADDRESS_FILE" ]; then
    error "address registry not found at $ADDRESS_FILE — cannot look up wallet"
    exit 1
  fi

  [ -f "$REGISTRY_FILE" ] || echo "{}" > "$REGISTRY_FILE"

  #Resolve wallet ID → address → key hash 

  local ADDRESS
  ADDRESS="$(jq -r --arg id "$WALLET_ID" '.[$id] // empty' "$ADDRESS_FILE")"

  if [ -z "$ADDRESS" ]; then
    error "wallet ID not found  id=$WALLET_ID"
    exit 1
  fi

  local HASH=""
  if [ -f "$REGISTRY_FILE" ]; then
    HASH="$(jq -r --arg address "$ADDRESS" '
      to_entries[]
      | select(.value.address | ascii_downcase == ($address | ascii_downcase))
      | .key
    ' "$REGISTRY_FILE" | head -n 1)"
  fi

  info "starting deletion  id=$WALLET_ID  address=$ADDRESS  key_hash=${HASH:-unknown}"

  #Remove from vault 

  info "deleting KV mapping  path=secret/wallets/by-id/$WALLET_ID"
  if bao kv delete "secret/wallets/by-id/$WALLET_ID" >/dev/null; then
    info "KV mapping deleted  id=$WALLET_ID"
  else
    warn "KV mapping was already missing or could not be deleted  id=$WALLET_ID"
  fi

  info "deleting ethereum account  address=$ADDRESS"
  if bao delete "ethereum/accounts/$ADDRESS" >/dev/null; then
    info "ethereum account deleted  address=$ADDRESS"
  else
    warn "ethereum account was already missing or could not be deleted  address=$ADDRESS"
  fi

  #Update local registries

  local TMP_FILE
  TMP_FILE="$(mktemp)"
  jq --arg id "$WALLET_ID" 'del(.[$id])' "$ADDRESS_FILE" > "$TMP_FILE"
  mv "$TMP_FILE" "$ADDRESS_FILE"
  info "removed from address registry  id=$WALLET_ID  file=$ADDRESS_FILE"

  if [ -f "$REGISTRY_FILE" ]; then
    TMP_FILE="$(mktemp)"
    jq --arg address "$ADDRESS" '
      with_entries(
        select(.value.address | ascii_downcase != ($address | ascii_downcase))
      )
    ' "$REGISTRY_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$REGISTRY_FILE"
    info "removed from key registry  address=$ADDRESS  file=$REGISTRY_FILE"
  else
    warn "key registry not found — skipping registry cleanup  file=$REGISTRY_FILE"
  fi

  #Remove from persistent keys file 

  local PERSISTENT_KEYS_REMOVED=0 PERSISTENT_KEYS_KEPT=0 PERSISTENT_KEYS_TOTAL="0"

  if [ -z "$HASH" ]; then
    PERSISTENT_KEYS_TOTAL="$(count_keys_in_file "$PERSISTENT_PRIVATE_KEYS_FILE")"
    warn "key hash is unknown (registry was missing) — cannot remove from persistent file  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE  keys_in_file=$PERSISTENT_KEYS_TOTAL"

  elif [ ! -f "$PERSISTENT_PRIVATE_KEYS_FILE" ]; then
    warn "persistent keys file not found — skipping persistent file cleanup  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE  key_hash=$HASH"

  else
    info "scanning persistent file for key to remove  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE  key_hash=$HASH"

    TMP_FILE="$(mktemp)"

    while IFS= read -r raw_key || [ -n "$raw_key" ]; do
      raw_clean_key="$(printf "%s" "$raw_key" | tr -d ' \n\r\t')"
      [ -z "$raw_clean_key" ] && continue

      local clean_key line_hash
      clean_key="$(normalize_pk "$raw_clean_key")"
      line_hash="$(pk_hash "$clean_key")"

      if [ "$line_hash" != "$HASH" ]; then
        printf "%s\n" "$clean_key" >> "$TMP_FILE"
        PERSISTENT_KEYS_KEPT=$((PERSISTENT_KEYS_KEPT + 1))
      else
        PERSISTENT_KEYS_REMOVED=$((PERSISTENT_KEYS_REMOVED + 1))
      fi
    done < "$PERSISTENT_PRIVATE_KEYS_FILE"

    cat "$TMP_FILE" > "$PERSISTENT_PRIVATE_KEYS_FILE"
    rm -f "$TMP_FILE"

    PERSISTENT_KEYS_TOTAL="$(count_keys_in_file "$PERSISTENT_PRIVATE_KEYS_FILE")"

    if [ "$PERSISTENT_KEYS_REMOVED" -gt 0 ]; then
      info "key removed from persistent file  key_hash=$HASH  keys_removed=$PERSISTENT_KEYS_REMOVED  keys_kept=$PERSISTENT_KEYS_KEPT  keys_remaining=$PERSISTENT_KEYS_TOTAL  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE"
    else
      warn "key not found in persistent file — nothing removed  key_hash=$HASH  keys_in_file=$PERSISTENT_KEYS_TOTAL  persistent_file=$PERSISTENT_PRIVATE_KEYS_FILE"
    fi
  fi

  local END_TS DURATION
  END_TS="$(date +%s)"
  DURATION="$((END_TS - START_TS))"

  info "deletion complete  id=$WALLET_ID  address=$ADDRESS  key_hash=${HASH:-unknown}  persistent_keys_removed=$PERSISTENT_KEYS_REMOVED  persistent_keys_remaining=$PERSISTENT_KEYS_TOTAL  duration=${DURATION}s"
}

# LIST

cmd_list() {
  local VERIFY="false"


  while [ $# -gt 0 ]; do
    case "$1" in
      --verify)
        VERIFY="true"
        shift
        ;;
      *)
        error "unknown argument: $1"
        exit 1
        ;;
    esac
  done

  if [ ! -f "$ADDRESS_FILE" ]; then
    error "address registry not found at $ADDRESS_FILE — no accounts to list"
    exit 1
  fi

  [ -f "$REGISTRY_FILE" ] || echo "{}" > "$REGISTRY_FILE"

  info "listing accounts  verify=$VERIFY"


  local ACCOUNTS_JSON="[]"
  if [ "$VERIFY" = "true" ]; then
    info "fetching live vault accounts for verification"
    ACCOUNTS_JSON="$(bao_accounts_json)"
    local VAULT_COUNT
    VAULT_COUNT="$(echo "$ACCOUNTS_JSON" | jq 'length')"
    info "vault accounts loaded  count=$VAULT_COUNT"
  fi


  # Separator width:
  #   5 (ID) + 2 + 42 (ADDRESS) + 2 + 64 (KEY_HASH) + 2 + 9 (STATUS col, --verify only)
  local SEP_BASE="────────────────────────────────────────────────────────────────────────"
  # Base width: 5 + 2 + 42 + 2 + 16 = 67
  local SEP="$SEP_BASE"

  local output_line
  emit() {
    printf "%s\n" "$1"
    if [ -w /proc/1/fd/1 ]; then
      printf "%s\n" "$1" > /proc/1/fd/1 || true
    fi
  }

  if [ "$VERIFY" = "true" ]; then
    # Extra 2 + 9 for the STATUS column when verifying
    SEP="${SEP_BASE}───────────"
    emit "$(printf "%-5s  %-42s  %-16s  %s" "ID" "ADDRESS" "KEY_HASH" "STATUS")"
  else
    emit "$(printf "%-5s  %-42s  %s" "ID" "ADDRESS" "KEY_HASH")"
  fi

  emit "$SEP"

  local TOTAL=0 MISSING=0

  while IFS= read -r wallet_id; do
    [ -z "$wallet_id" ] && continue

    local address key_hash status_col

    address="$(jq -r --arg id "$wallet_id" '.[$id] // empty' "$ADDRESS_FILE")"
    [ -z "$address" ] && continue

    # Look up key hash from registry (may be empty if registry is incomplete).
    key_hash="$(jq -r --arg address "$address" '
      to_entries[]
      | select(.value.address | ascii_downcase == ($address | ascii_downcase))
      | .key
    ' "$REGISTRY_FILE" 2>/dev/null | head -n 1)"

    key_hash="${key_hash:-unknown}"

    # Truncate to first 16 chars for readability — full hash is in the registry.
    local key_hash_short
    key_hash_short="$(printf "%.16s" "$key_hash")"

    TOTAL=$((TOTAL + 1))

    if [ "$VERIFY" = "true" ]; then
      if bao_account_exists "$address" "$ACCOUNTS_JSON"; then
        status_col="OK"
      else
        status_col="[MISSING]"
        MISSING=$((MISSING + 1))
      fi
      emit "$(printf "%-5s  %-42s  %-16s  %s" "$wallet_id" "$address" "$key_hash_short" "$status_col")"
    else
      emit "$(printf "%-5s  %-42s  %s" "$wallet_id" "$address" "$key_hash_short")"
    fi

  done << EOF
$(jq -r 'keys | map(tonumber) | sort | .[] | tostring' "$ADDRESS_FILE")
EOF

  emit "$SEP"

  if [ "$VERIFY" = "true" ]; then
    emit "$(printf "Total: %s wallet(s)  —  vault_missing: %s" "$TOTAL" "$MISSING")"
  else
    emit "$(printf "Total: %s wallet(s)" "$TOTAL")"
  fi


  local END_TS DURATION
  END_TS="$(date +%s)"
  DURATION="$((END_TS - START_TS))"

  if [ "$VERIFY" = "true" ]; then
    info "list complete  total=$TOTAL  vault_missing=$MISSING  duration=${DURATION}s"
  else
    info "list complete  total=$TOTAL  duration=${DURATION}s"
  fi
}

# Dispatch

case "$SUBCOMMAND" in
  import) cmd_import "$@" ;;
  delete) cmd_delete "$@" ;;
  list)   cmd_list   "$@" ;;
esac
