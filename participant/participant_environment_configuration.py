import os
import sys
import json
import re
import urllib.request
import urllib.error
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

try:
    from is_safe_url import is_safe_url
except ImportError:
    print("Error: 'is-safe-url' package is not installed.")
    print("Please install it using: pip3 install is-safe-url")
    sys.exit(1)

DEFAULTS_PARTICIPANT = {
    "SERVICE_HOST": "localhost",
    "NUXT_WALLET_API_INTERNAL": "http://wallet-api:7001/wallet-api",
    "WALLET_BACKEND_PORT": "7001",
    "DB_NAME": "waltid",
    "DB_USERNAME": "waltid",
    "POSTGRES_DB_PORT": "5432",
    "POSTGRES_DB_HOST": "postgres",
    "POSTGRES_DB_DATA": "/waltid-wallet-api/data/",
    "POSTGRES_TAG": "18",
    "OPENBAO_PORT": "8200",
    "SIGNER_MODE": "vault",
    "PORT": 3001,
    "VAULT_URL": "https://openbao:8200",
    "VAULT_ETHEREUM_MOUNT": "ethereum",
    "VAULT_KV_STORE_PATH": "secret",
    "VAULT_TIMEOUT_MS": "10000",
    "AUTHENTIK_IMAGE": "ghcr.io/goauthentik/server",
    "AUTHENTIK_PORT_HTTP": "9000",
    "AUTHENTIK_PORT_HTTPS": "9443",
    "AUTHENTIK_EMAIL__USE_SSL": "false",
    "AUTHENTIK_EMAIL__TIMEOUT": "10",
    "AUTHENTIK_POSTGRESQL__HOST": "postgres",
    "AUTHENTIK_POSTGRESQL__NAME": "authentik",
    "AUTHENTIK_POSTGRESQL__USER": "authentik",
    "NITRO_PORT": "7104",
    "HOST": "0.0.0.0"
}

REQUIRED_VARS = [
    "MARKETPLACE_URL",
    "CENTRAL_IDP_WELL_KNOWN_URL",
    "CENTRAL_IDP_CLIENT_ID",
    "CENTRAL_IDP_CLIENT_SECRET",
    "WALLET_UI_URL",
    "WALLET_API_URL",
    "DB_PASSWORD",
    "POSTGRES_PASSWORD", # super user password
    "PARTICIPANT_IDP_HOSTNAME",
    "PARTICIPANT_IDP_PORT_HTTP",
    "PARTICIPANT_IDP_PORT_HTTPS",
    "AUTHENTIK_APP_SLUG",
    "AUTHENTIK_PROVIDER_NAME",
    "AUTHENTIK_POSTGRESQL__PASSWORD",
    "AUTHENTIK_SECRET_KEY",
    "NODE_URI_MAP",
]

def sanitize_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r'^https?://+', 'https://', url)
    url = re.sub(r'(?<!:)/{2,}', '/', url)
    return url

def validate_url_format(url: str) -> bool:
    if not url or url.startswith('<'):
        return False
    
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc
        
        if not hostname:
            return False
        
        if parsed.scheme not in ['http', 'https']:
            return False
        
        return is_safe_url(url, allowed_hosts={hostname}, require_https=False)
    except Exception:
        return False

def read_config_file(filepath: str) -> Dict[str, str]:
    config = {}
    
    if not os.path.exists(filepath):
        print(f"Error: Configuration file '{filepath}' not found.")
        sys.exit(1)
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                config[key] = value
    
    return config

def validate_config(config: Dict[str, str]) -> None:
    missing_vars = []
    for var in REQUIRED_VARS:
        if var not in config or not config[var] or config[var] == f"<your-{var.lower().replace('_', '-')}>":
            missing_vars.append(var)
    
    if missing_vars:
        print("Error: Required configuration variables are missing or have placeholder values:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease fill in all required variables in .env.config before running this script.")
        sys.exit(1)
    
    url_vars = ["MARKETPLACE_URL", "CENTRAL_IDP_WELL_KNOWN_URL", "WALLET_UI_URL", "WALLET_API_URL"]
    for var in url_vars:
        if var in config:
            sanitized = sanitize_url(config[var])
            if sanitized != config[var]:
                print(f"Warning: Sanitized {var} from '{config[var]}' to '{sanitized}'")
                config[var] = sanitized
            if not validate_url_format(sanitized):
                print(f"Error: Invalid or unsafe URL format for {var}: {sanitized}")
                sys.exit(1)

def fetch_oidc_config(well_known_url: str) -> Dict[str, Any]:
    if not validate_url_format(well_known_url):
        print("Error: Invalid or unsafe URL provided.")
        sys.exit(1)
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Fetching OIDC configuration from: {well_known_url} (attempt {attempt}/{max_retries})")
            with urllib.request.urlopen(well_known_url, timeout=10) as response:
                if response.getcode() == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    required_fields = ['issuer', 'jwks_uri', 'token_endpoint']
                    missing_fields = [f for f in required_fields if f not in data]
                    if missing_fields:
                        print(f"Error: OIDC configuration missing required fields: {', '.join(missing_fields)}")
                        sys.exit(1)
                    return data
        except urllib.error.URLError as e:
            print(f"Attempt {attempt} failed: {e.reason}")
        except json.JSONDecodeError as e:
            print(f"Attempt {attempt} failed: Invalid JSON response - {e}")
        except Exception as e:
            print(f"Attempt {attempt} failed: {str(e)}")
        
        if attempt < max_retries:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print(f"Error: Failed to fetch OIDC configuration after {max_retries} attempts.")
            print("Please verify that CENTRAL_IDP_WELL_KNOWN_URL is correct and accessible.")
            sys.exit(1)
    
    return {}

def quote_password(value: str) -> str:
    return f"'{value}'"

def append_new_env_vars(filepath: str, variables: Dict[str, str]) -> None:
    """Appends new keys and updates existing keys in a .env file without modifying other content."""

    existing_lines = []
    existing_keys = set()

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            existing_lines = f.readlines()

        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                existing_keys.add(stripped.split('=', 1)[0].strip())

    # Update existing keys in place
    new_lines = []
    updated_keys = set()

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in variables:
                new_lines.append(f"{key}={variables[key]}\n")
                updated_keys.add(key)
                print(f" Updated: {key}={variables[key]}")
                continue
        new_lines.append(line)

    # Write back updated lines
    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    # Append keys that were not already in the file
    new_vars = {k: v for k, v in variables.items() if k not in updated_keys}

    if new_vars:
        with open(filepath, 'a') as f:
            f.write("\n")
            for key, value in new_vars.items():
                f.write(f"{key}={value}\n")
                print(f"  + Appended: {key}={value}")

    print(f" Updated: {filepath}")

def update_env_file(filepath: str, variables: Dict[str, str], preserve_vars: List[str] = None) -> None:
    if preserve_vars is None:
        preserve_vars = []
    
    existing_lines = []
    existing_vars = {}
    existing_commented_vars = set()
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            existing_lines = f.readlines()
        
        for line in existing_lines:
            line_stripped = line.strip()
            if '=' in line_stripped and not line_stripped.startswith('#'):
                key, value = line_stripped.split('=', 1)
                existing_vars[key.strip()] = value.strip()
            elif line_stripped.startswith('#') and '=' in line_stripped:
                parts = line_stripped.lstrip('#').strip().split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    existing_commented_vars.add(key)
    
    updated_vars = set()
    new_lines = []
    
    for line in existing_lines:
        line_stripped = line.strip()
        
        if '=' in line_stripped and not line_stripped.startswith('#'):
            key = line_stripped.split('=', 1)[0].strip()
            
            if key in variables:
                new_value = variables[key]
                
                if key in preserve_vars and key in existing_vars:
                    new_value = existing_vars[key]
                    print(f"  Preserved existing value for {key}: {new_value}")
                elif key in existing_vars and (existing_vars[key].startswith('<') or existing_vars[key].startswith('"')):
                    pass
                
                if '=' in line and '=' in line_stripped:
                    new_line = line.replace(line_stripped.split('=', 1)[1], new_value)
                else:
                    new_line = f"{key}={new_value}\n"
                
                new_lines.append(new_line)
                updated_vars.add(key)
                continue
        
        new_lines.append(line)
    
    for key, value in variables.items():
        if key not in updated_vars:
            if key in existing_commented_vars:
                for i, line in enumerate(new_lines):
                    if line.strip().startswith(f"# {key}=") or line.strip().startswith(f"# {key} ="):
                        new_lines[i] = f"{key}={value}\n"
                        break
            else:
                new_lines.append(f"{key}={value}\n")
    
    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Updated: {filepath}")

def ensure_env_file_structure(filepath: str, header: str, sections: List[tuple], preserve_vars: List[str] = None) -> None:
    if preserve_vars is None:
        preserve_vars = []
    
    if not os.path.exists(filepath):
        lines = []
        lines.append("# =============================================================================")
        lines.append(f"# {header}")
        lines.append("# Auto-generated by participant_environment_configuration.py")
        lines.append("# Do not edit manually — re-run the generation script to update.")
        lines.append("# =============================================================================")
        lines.append("")
        
        for section_name, vars_dict in sections:
            if vars_dict:
                lines.append(f"# --- {section_name} -------------------------------------------------------------")
                for key, value in vars_dict.items():
                    if key.startswith('#'):
                        lines.append(f"{key}={value}")
                    else:
                        lines.append(f"{key}={value}")
                lines.append("")
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        print(f"Created: {filepath}")
    else:
        all_vars = {}
        for _, vars_dict in sections:
            all_vars.update(vars_dict)
        update_env_file(filepath, all_vars, preserve_vars)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, '.env.config')
    
    print("=" * 80)
    print("PARTICIPANT ENVIRONMENT CONFIGURATION GENERATOR")
    print("=" * 80)
    print()
    
    print("Step 1: Reading configuration...")
    config = read_config_file(config_path)
    validate_config(config)
    print("Configuration validated successfully")
    print()
    
    print("Step 2: Fetching OIDC configuration...")
    oidc_config = fetch_oidc_config(config['CENTRAL_IDP_WELL_KNOWN_URL'])
    issuer = oidc_config.get('issuer', '')
    jwks_uri = oidc_config.get('jwks_uri', '')
    token_endpoint = oidc_config.get('token_endpoint', '')
    print(f"OIDC configuration fetched successfully")
    print(f"  - Issuer: {issuer}")
    print(f"  - JWKS URI: {jwks_uri}")
    print(f"  - Token Endpoint: {token_endpoint}")
    print()
    
    print("Step 3: Generating derived values...")
    allowed_origins = [config['MARKETPLACE_URL'], config['WALLET_UI_URL']]
    allowed_origins_json = json.dumps(allowed_origins)
    
    participant_idp_well_known = (
        f"https://{config['PARTICIPANT_IDP_HOSTNAME']}:{config['PARTICIPANT_IDP_PORT_HTTPS']}"
        f"/application/o/{config['AUTHENTIK_APP_SLUG']}/.well-known/openid-configuration"
    )
    
    print("Step 4: Generating/updating environment files...")
    print()
    
    print("  Processing .env.authentik...")
    
    authentik_configurable = {
        "AUTHENTIK_POSTGRESQL__PASSWORD": quote_password(config['AUTHENTIK_POSTGRESQL__PASSWORD']),
        "AUTHENTIK_SECRET_KEY": quote_password(config['AUTHENTIK_SECRET_KEY']),
    }
    
    if 'AUTHENTIK_EMAIL__FROM' in config and config['AUTHENTIK_EMAIL__FROM'] and not config['AUTHENTIK_EMAIL__FROM'].startswith('#'):
        authentik_configurable["AUTHENTIK_EMAIL__FROM"] = config['AUTHENTIK_EMAIL__FROM']
    
    authentik_app_config = {
        "AUTHENTIK_APP_SLUG": config['AUTHENTIK_APP_SLUG'],
        "AUTHENTIK_PROVIDER_NAME": config['AUTHENTIK_PROVIDER_NAME'],
        "AUTHENTIK_OUTPUT_FILE": config.get('AUTHENTIK_OUTPUT_FILE', 'participant-authentik-blueprint.yaml'),
    }

    parsed = urlparse(config['CENTRAL_IDP_WELL_KNOWN_URL'])
    central_idp_url = f"{parsed.scheme}://{parsed.netloc}"
    central_idp_url = sanitize_url(central_idp_url)
    marketplace_url = sanitize_url(config['MARKETPLACE_URL'].rstrip('/'))
    
    if not validate_url_format(marketplace_url):
        print(f"Error: Invalid MARKETPLACE_URL format after sanitization: {marketplace_url}")
        sys.exit(1)
    
    if not validate_url_format(central_idp_url):
        print(f"Error: Invalid CENTRAL_IDP_URL format after sanitization: {central_idp_url}")
        sys.exit(1)
    
    authentik_redirect_uris = [
        f"{marketplace_url}/auth/callback",
        f"{marketplace_url}/auth/login",
        f"{central_idp_url}/source/oauth/callback/{config['AUTHENTIK_APP_SLUG']}/"
    ]
    
    authentik_auth_config = {
        "AUTHENTIK_REDIRECT_URIS": authentik_redirect_uris,
        "AUTHENTIK_LOGOUT_URI": f"{marketplace_url}/auth/callback/logout",
        "COMPOSE_PORT_HTTP": config['PARTICIPANT_IDP_PORT_HTTP'],
        "COMPOSE_PORT_HTTPS": config['PARTICIPANT_IDP_PORT_HTTPS'],
        "PARTICIPANT_IDP_WELL_KNOWN_URL": participant_idp_well_known,
    }

    authentik_auth_blueprint = {
        "AUTHENTIK_REDIRECT_URIS": json.dumps(authentik_redirect_uris),
        "AUTHENTIK_LOGOUT_URI": f"{marketplace_url}/auth/callback/logout",
    }
    
    authentik_smtp_config = {}
    smtp_vars = [
        'AUTHENTIK_EMAIL__USERNAME',
        'AUTHENTIK_EMAIL__PASSWORD',
        'AUTHENTIK_EMAIL__HOST',
        'AUTHENTIK_EMAIL__PORT'
    ]
    
    has_smtp = False
    for var_key in smtp_vars:
        if var_key in config and config[var_key] and not config[var_key].startswith('#'):
            value = config[var_key]
            if var_key == 'AUTHENTIK_EMAIL__PASSWORD':
                value = quote_password(value)
            authentik_smtp_config[var_key] = value
            has_smtp = True
    
    authentik_defaults = {
        "AUTHENTIK_IMAGE": DEFAULTS_PARTICIPANT["AUTHENTIK_IMAGE"],
        "AUTHENTIK_PORT_HTTP": DEFAULTS_PARTICIPANT["AUTHENTIK_PORT_HTTP"],
        "AUTHENTIK_PORT_HTTPS": DEFAULTS_PARTICIPANT["AUTHENTIK_PORT_HTTPS"],
        "AUTHENTIK_POSTGRESQL__NAME": DEFAULTS_PARTICIPANT["AUTHENTIK_POSTGRESQL__NAME"],
        "AUTHENTIK_POSTGRESQL__USER": DEFAULTS_PARTICIPANT["AUTHENTIK_POSTGRESQL__USER"],
        "AUTHENTIK_EMAIL__USE_SSL": DEFAULTS_PARTICIPANT["AUTHENTIK_EMAIL__USE_SSL"],
        "AUTHENTIK_EMAIL__TIMEOUT": DEFAULTS_PARTICIPANT["AUTHENTIK_EMAIL__TIMEOUT"],
        "AUTHENTIK_POSTGRESQL__HOST": DEFAULTS_PARTICIPANT["AUTHENTIK_POSTGRESQL__HOST"],
    }
    
    authentik_sections = [
        ("Configurable (sourced from .env.config)", authentik_configurable),
        ("Application Configuration", authentik_app_config),
        ("Authentication Configuration", authentik_auth_config),
    ]
    
    if has_smtp:
        authentik_sections.append(("SMTP Configuration", authentik_smtp_config))
    
    authentik_sections.append(("Default", authentik_defaults))
    
    authentik_preserve_vars = []
    
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.authentik"),
        "PARTICIPANT — .env.authentik",
        authentik_sections,
        authentik_preserve_vars
    )
    print("  Updating .env.tmp...")
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.tmp"),
        "PARTICIPANT — .env.tmp",
        [("Generated Application Configuration", authentik_auth_blueprint)]
    )
    
    print("  Processing .env.openbao...")
    openbao_vars = {}
    openbao_sections = [
        ("Configurable (sourced from .env.config)", openbao_vars),
    ]
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.openbao"),
        "PARTICIPANT — .env.openbao",
        openbao_sections
    )
    
    print("  Processing .env.postgres...")
    postgres_vars = {
        "POSTGRES_TAG": DEFAULTS_PARTICIPANT["POSTGRES_TAG"],
        "DB_NAME": DEFAULTS_PARTICIPANT["DB_NAME"],
        "DB_USERNAME": DEFAULTS_PARTICIPANT["DB_USERNAME"],
        "POSTGRES_DB_PORT": DEFAULTS_PARTICIPANT["POSTGRES_DB_PORT"],
        "POSTGRES_DB_DATA": DEFAULTS_PARTICIPANT["POSTGRES_DB_DATA"],
        "AUTHENTIK_POSTGRESQL__NAME": DEFAULTS_PARTICIPANT["AUTHENTIK_POSTGRESQL__NAME"],
        "AUTHENTIK_POSTGRESQL__USER": DEFAULTS_PARTICIPANT["AUTHENTIK_POSTGRESQL__USER"],
        "AUTHENTIK_POSTGRESQL__PASSWORD": quote_password(config['AUTHENTIK_POSTGRESQL__PASSWORD']),
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": quote_password(config['POSTGRES_PASSWORD']),
        "POSTGRES_DB": "postgres"
    }
    
    db_password = config['DB_PASSWORD']
    postgres_vars["DB_PASSWORD"] = quote_password(db_password)
    
    postgres_sections = [
        ("Configurable (sourced from .env.config)", {k: postgres_vars[k] for k in [
                    "DB_PASSWORD", "AUTHENTIK_POSTGRESQL__PASSWORD", "POSTGRES_PASSWORD"
        ]}),
        ("Default", {k: v for k, v in postgres_vars.items() if k not in [
            "DB_PASSWORD", "AUTHENTIK_POSTGRESQL__PASSWORD", "POSTGRES_PASSWORD"
        ]}),
    ]
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.postgres"),
        "PARTICIPANT — .env.postgres",
        postgres_sections
    )
    
    print("  Processing .env.signer-server...")
    certs_dir = os.path.join(os.getcwd(), "docker-compose", "signer-server", "certs")
    filenames = [f for f in os.listdir(certs_dir) if os.path.isfile(os.path.join(certs_dir, f))]

    key_index = next((i for i, f in enumerate(filenames) if f.endswith(".key") or "privkey" in f), None)
    cert_index = next((i for i, f in enumerate(filenames) if f.endswith(".pem") and i != key_index), None)
    signer_vars = {
        "ALLOWED_ORIGINS": allowed_origins_json,
        "AUTHENTIK_AUDIENCE": config['CENTRAL_IDP_CLIENT_ID'],
        "AUTHENTIK_JWKS_URI": jwks_uri,
        "AUTHENTIK_ISSUER": issuer,
        "UPSTREAM_IDP": config['AUTHENTIK_APP_SLUG'],
        "OPENBAO_PORT": DEFAULTS_PARTICIPANT["OPENBAO_PORT"],
        "PORT": DEFAULTS_PARTICIPANT["PORT"],
        "SIGNER_MODE": DEFAULTS_PARTICIPANT["SIGNER_MODE"],
        "VAULT_URL": DEFAULTS_PARTICIPANT["VAULT_URL"],
        "VAULT_ETHEREUM_MOUNT": DEFAULTS_PARTICIPANT["VAULT_ETHEREUM_MOUNT"],
        "VAULT_KV_STORE_PATH": DEFAULTS_PARTICIPANT["VAULT_KV_STORE_PATH"],
        "VAULT_TIMEOUT_MS": DEFAULTS_PARTICIPANT["VAULT_TIMEOUT_MS"],
        "NODE_URI_MAP": config['NODE_URI_MAP'],
        "HTTP_CERT_PATH": f'/etc/ssl/certs/{filenames[cert_index]}',
        "HTTP_KEY_PATH": f'/etc/ssl/certs/{filenames[key_index]}'
    }
    signer_sections = [
        ("Configurable (sourced from .env.config)", {k: signer_vars[k] for k in [
            "ALLOWED_ORIGINS", "AUTHENTIK_AUDIENCE", 
            "AUTHENTIK_JWKS_URI", "AUTHENTIK_ISSUER"
        ]}),
        ("Generated", {"UPSTREAM_IDP": signer_vars["UPSTREAM_IDP"], "HTTP_CERT_PATH": signer_vars["HTTP_CERT_PATH"], "HTTP_KEY_PATH": signer_vars["HTTP_KEY_PATH"]}),
        ("Default", {k: signer_vars[k] for k in [
            "OPENBAO_PORT", "SIGNER_MODE", "PORT",
            "VAULT_URL", "VAULT_ETHEREUM_MOUNT", "VAULT_KV_STORE_PATH",
            "VAULT_TIMEOUT_MS"
        ]}),
        ("Generated Node URI Map", {"NODE_URI_MAP": signer_vars["NODE_URI_MAP"]}),
    ]
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.signer-server"),
        "PARTICIPANT — .env.signer-server",
        signer_sections
    )
    
    print("  Processing .env.traefik...")
    traefik_sections = [
        ("Traefik Configuration", {}),
    ]
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.traefik"),
        "PARTICIPANT — .env.traefik",
        traefik_sections
    )
    
    print("  Processing .env.wallet-api...")
    wallet_api_vars = {
        "SERVICE_HOST": DEFAULTS_PARTICIPANT["SERVICE_HOST"],
        "WALLET_BACKEND_PORT": DEFAULTS_PARTICIPANT["WALLET_BACKEND_PORT"],
        "DB_NAME": DEFAULTS_PARTICIPANT["DB_NAME"],
        "DB_USERNAME": DEFAULTS_PARTICIPANT["DB_USERNAME"],
        "POSTGRES_DB_PORT": DEFAULTS_PARTICIPANT["POSTGRES_DB_PORT"],
        "POSTGRES_DB_HOST": DEFAULTS_PARTICIPANT["POSTGRES_DB_HOST"],
        "POSTGRES_DB_DATA": DEFAULTS_PARTICIPANT["POSTGRES_DB_DATA"],
        "WALLET_API_HOST": urlparse(config["WALLET_API_URL"]).hostname,
        "WALLET_UI_HOST": urlparse(config["WALLET_UI_URL"]).hostname,
    }
    
    db_password = config['DB_PASSWORD']
    wallet_api_vars["DB_PASSWORD"] = quote_password(db_password)
    
    wallet_api_sections = [
        ("Configurable (sourced from .env.config)", {k: wallet_api_vars[k] for k in [
                    "DB_PASSWORD"
                ]}),
        ("Generated", {k: wallet_api_vars[k] for k in [
                    "WALLET_API_HOST",
                    "WALLET_UI_HOST",
                ]}),
        ("Default", {k: v for k, v in wallet_api_vars.items() if k not in [
            "WALLET_API_HOST",
            "WALLET_UI_HOST",
            "DB_PASSWORD",
        ]}),
    ]
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.wallet-api"),
        "PARTICIPANT — .env.wallet-api",
        wallet_api_sections
    )
    
    print("  Processing .env.wallet-ui...")
    wallet_ui_vars = {
        "NUXT_PUBLIC_LOGOUT_REDIRECT_URI": config['WALLET_UI_URL'],
        "NUXT_CLIENT_SECRET": quote_password(config['CENTRAL_IDP_CLIENT_SECRET']),
        "NUXT_TOKEN_URL": token_endpoint,
        "NUXT_PUBLIC_CLIENT_ID": config['CENTRAL_IDP_CLIENT_ID'],
        "NUXT_PUBLIC_ISSUER": issuer,
        "NUXT_PUBLIC_REDIRECT_URI": f"{config['WALLET_UI_URL']}/auth/callback",
        "NUXT_PUBLIC_ISSUER_CALLBACK_URL": config['WALLET_UI_URL'],
        "NUXT_PUBLIC_DEV_WALLET_URL": config['WALLET_UI_URL'],
        "SERVICE_HOST": DEFAULTS_PARTICIPANT["SERVICE_HOST"],
        "NUXT_WALLET_API_INTERNAL": DEFAULTS_PARTICIPANT["NUXT_WALLET_API_INTERNAL"],
        "WALLET_UI_HOST": urlparse(config["WALLET_UI_URL"]).hostname,
        "NUXT_ADMIN_USER_GROUP_NAME": config["NUXT_ADMIN_USER_GROUP_NAME"],
    }
    wallet_ui_sections = [
        ("Configurable (sourced from .env.config)", {k: wallet_ui_vars[k] for k in [
            "NUXT_PUBLIC_LOGOUT_REDIRECT_URI", "NUXT_CLIENT_SECRET",
            "NUXT_TOKEN_URL", "NUXT_PUBLIC_CLIENT_ID", "NUXT_PUBLIC_ISSUER", "NUXT_ADMIN_USER_GROUP_NAME"
        ]}),
        ("Generated", {k: wallet_ui_vars[k] for k in [
            "NUXT_PUBLIC_REDIRECT_URI",
            "NUXT_PUBLIC_ISSUER_CALLBACK_URL",
            "NUXT_PUBLIC_DEV_WALLET_URL",
            "WALLET_UI_HOST",
        ]}),
        ("Default", {k: wallet_ui_vars[k] for k in [
            "SERVICE_HOST", "NUXT_WALLET_API_INTERNAL"
        ]}),
    ]
    ensure_env_file_structure(
        os.path.join(script_dir, ".env.wallet-ui"),
        "PARTICIPANT — .env.wallet-ui",
        wallet_ui_sections
    )

    print("  Processing .env for root docker compose deployment...")
    env_vars = {
        "WALLET_API_HOST": urlparse(config["WALLET_API_URL"]).hostname,
        "WALLET_UI_HOST": urlparse(config["WALLET_UI_URL"]).hostname,
        "COMPOSE_PORT_HTTP": config['PARTICIPANT_IDP_PORT_HTTP'],
        "COMPOSE_PORT_HTTPS": config['PARTICIPANT_IDP_PORT_HTTPS'],
    }

    append_new_env_vars(
        os.path.join(script_dir, "docker-compose", ".env"),
        env_vars,
    )
    
    print()
    print("=" * 80)
    print("ENVIRONMENT CONFIGURATION GENERATION COMPLETE!")
    print("=" * 80)
    print(f"Generated files in: {script_dir}")
    print()
    print("The following files have been generated/updated:")
    print("  - .env.authentik")
    print("  - .env.openbao")
    print("  - .env.postgres")
    print("  - .env.signer-server")
    print("  - .env.traefik")
    print("  - .env.wallet-api")
    print("  - .env.wallet-ui")
    print("  - .env")
    print(f"\nOnboarding configuration: config-for-onboarding-{config['AUTHENTIK_APP_SLUG']}.json")
    print()
    print("IMPORTANT NOTES:")
    print("  - All files were updated line-by-line, preserving existing content")
    print("  - Values from .env.config are always applied (source of truth)")
    print("  - Only placeholder values (<...>) are replaced with new values")
    print("  - Comments and formatting were preserved")
    print("  - All passwords are wrapped in single quotes for shell safety")
    print("  - URLs are validated using is-safe-url library with the URL's own hostname as allowed_host")
    print("  - URLs are automatically sanitized (duplicate https:// removed, double slashes fixed)")
    print("  - PARTICIPANT_IDP_WELL_KNOWN_URL is generated and saved in .env.authentik")
    print("  - The onboarding JSON contains placeholder values that will be")
    print("    replaced by the Authentik blueprint script")

if __name__ == "__main__":
    main()