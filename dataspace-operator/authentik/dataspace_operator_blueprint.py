#!/usr/bin/env python3
"""
Authentik Main Instance Blueprint Generator
Generates a complete blueprint YAML file for the main authentik instance with:
- Enrollment Invitation Flow with email/username validation
- Federated JIT Enrollment Flow
- Recovery Flow with password reset
- Custom Authentication Flow with Recovery
- OAuth Source Property Mapping
- Scope Mappings
- All necessary flows, stages, and bindings
- Saves generated client credentials, JWKS URI, Issuer, and Audience to .env file
- Email notification to admin when duplicate email is detected
- SMTP config from .env or fallback to defaults
- Web certificate discovery and brand update
"""

import os
import secrets
import string
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from urllib.parse import urlparse

try:
    from is_safe_url import is_safe_url
except ImportError:
    print("Error: 'is-safe-url' package is not installed.")
    print("Please install it using: pip3 install is-safe-url")
    sys.exit(1)

try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    print("ruamel.yaml not found. Installing...")
    os.system("pip install ruamel.yaml")
    from ruamel.yaml import YAML
    HAS_RUAMEL = True

load_dotenv('.env.config')


def generate_random_client_id() -> str:
    """Generate a random client ID (32 characters)."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(32))


def generate_random_client_secret() -> str:
    """Generate a random client secret (43 characters)."""
    chars = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(chars) for _ in range(43))


def generate_redirect_uris(redirect_uris_list: List[str]) -> List[Dict[str, Any]]:
    """Generate redirect URIs structure for the blueprint."""
    return [
        {
            "matching_mode": "strict",
            "redirect_uri_type": "authorization",
            "url": url.strip()
        }
        for url in redirect_uris_list
    ]


def get_email_config():
    """
    Get email configuration from environment variables or use defaults.
    
    Reads SMTP configs from environment variables with AUTHENTIK_EMAIL__ prefix.
    Falls back to default localhost settings if not provided.
    """
    default_config = {
        "host": "localhost",
        "port": 25,
        "username": "",
        "password": "",
        "use_tls": False,
        "use_ssl": False,
        "timeout": 10,
        "from_address": "system@authentik.local"
    }
    
    env_config = {
        "host": os.getenv("AUTHENTIK_EMAIL__HOST"),
        "port": os.getenv("AUTHENTIK_EMAIL__PORT"),
        "username": os.getenv("AUTHENTIK_EMAIL__USERNAME"),
        "password": os.getenv("AUTHENTIK_EMAIL__PASSWORD"),
        "use_tls": os.getenv("AUTHENTIK_EMAIL__USE_TLS"),
        "use_ssl": os.getenv("AUTHENTIK_EMAIL__USE_SSL"),
        "timeout": os.getenv("AUTHENTIK_EMAIL__TIMEOUT"),
        "from_address": os.getenv("AUTHENTIK_EMAIL__FROM")
    }
    
    config = {}
    for key, default_value in default_config.items():
        env_value = env_config.get(key)
        if env_value is not None and env_value != "":
            if key in ["use_tls", "use_ssl"]:
                config[key] = env_value.lower() == "true"
            elif key == "port":
                try:
                    config[key] = int(env_value)
                except ValueError:
                    config[key] = default_value
            elif key == "timeout":
                try:
                    config[key] = int(env_value)
                except ValueError:
                    config[key] = default_value
            else:
                config[key] = env_value
        else:
            config[key] = default_value
    
    return config


def get_certificate_name(certs_dir: Optional[str] = None) -> Optional[str]:
    """
    Get the certificate name from the certs directory.
    
    Searches for .pem files and validates that matching .key files exist.
    Follows the naming conventions from the Authentik documentation.
    Supports root directory files, certbot convention, and -privkey naming.
    
    Args:
        certs_dir: Path to certificates directory. If None, tries to find it.
    """
    try:
        possible_paths = [
            certs_dir,
            "/certs",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "authentik", "certs"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "authentik", "certs"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "authentik", "certs"),
            os.path.join(os.environ.get("HOME", ""), "authentik", "certs"),
            os.path.join(os.getcwd(), "docker-compose", "authentik", "certs"), # docker-compose deployment path
        ]
        
        for path in possible_paths:
            if path is None:
                continue
            certs_path = Path(path)
            if certs_path.exists():
                print(f"Found certificates directory: {certs_path}")
                
                pem_files = list(certs_path.glob("*.pem"))
                fullchain_files = list(certs_path.glob("*/fullchain.pem"))
                
                if not pem_files and not fullchain_files:
                    print(f"No .pem files found in '{certs_path}'. Continue with next possible path.")
                    continue
                
                cert_names = set()
                for pem_file in pem_files:
                    cert_names.add(pem_file.stem)
                for fullchain_file in fullchain_files:
                    cert_names.add(fullchain_file.parent.name)
                
                key_files = list(certs_path.glob("*.key"))
                privkey_files = list(certs_path.glob("*-privkey"))
                key_files.extend(privkey_files)
                privkey_pem_files = list(certs_path.glob("*/privkey.pem"))
                
                key_names = set()
                for key_file in key_files:
                    if key_file.name.endswith("-privkey"):
                        key_names.add(key_file.stem.replace("-privkey", ""))
                    else:
                        key_names.add(key_file.stem)
                for privkey_file in privkey_pem_files:
                    key_names.add(privkey_file.parent.name)
                
                print(f"   Certificate names found: {cert_names}")
                if key_names:
                    print(f"   Private key names found: {key_names}")
                
                if key_names:
                    valid_certs = [name for name in cert_names if name in key_names]
                    
                    if valid_certs:
                        cert_name = valid_certs[0]
                        print(f"Found certificate with matching private key: {cert_name}")
                        return cert_name
                    else:
                        print(f"No matching private key found for certificates: {cert_names}")
                        print(f"   Using first certificate: {next(iter(cert_names))}")
                        return next(iter(cert_names))
                else:
                    if len(cert_names) == 1:
                        cert_name = cert_names.pop()
                        print(f"Found certificate: {cert_name}")
                        return cert_name
                    elif len(cert_names) > 1:
                        print(f"Multiple certificate names found: {cert_names}. Using first one: {next(iter(cert_names))}")
                        return next(iter(cert_names))
                    else:
                        return None
        
        print(f"No certificates directory found in any of: {possible_paths}")
        return None
            
    except Exception as e:
        print(f"Error checking certificates directory: {e}")
        return None


def save_credentials_to_env(client_id: str, client_secret: str, base_url: str, app_slug: str, redirect_uris: list, logout_uri: str, env_file: str = ".env.tmp"):
    """
    Save generated client credentials, JWKS URI, Issuer, and Audience to .env file.
    
    Also generates NUXT-specific variables for the application.
    """
    try:
        if not base_url.endswith('/'):
            base_url += '/'
        
        audience = client_id
        
        env_vars = {
            "CENTRAL_IDP_CLIENT_ID": audience,
            "CENTRAL_IDP_CLIENT_SECRET": client_secret,
            "AUTHENTIK_REDIRECT_URIS": redirect_uris,
            "AUTHENTIK_LOGOUT_URI": logout_uri,
            "AUTHENTIK_BASE_URL": base_url
        }
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        for var_name, var_value in env_vars.items():
            pattern = re.compile(rf'^{var_name}=.*$', re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f'{var_name}={var_value}', content)
            else:
                if content and not content.endswith('\n'):
                    content += '\n'
                content += f'{var_name}={var_value}\n'
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"Credentials saved to {env_file}")
        print(f"   Audience (Client ID): {audience}")
        print(f"   Client Secret: {client_secret}")
        return True
    except Exception as e:
        print(f"Could not save credentials to .env: {e}")
        return False


def save_marketplace_env(
    client_id: str, 
    client_secret: str, 
    central_idp_hostname: str, 
    central_idp_port_https: str, 
    app_slug: str, 
    marketplace_url: str,
    env_file: str = ".env.market"
):
    """
    Save marketplace OIDC configuration to .env.market file.
    
    Generates the following variables:
    - NEXT_PUBLIC_AUTH_ENABLED=true
    - NEXT_PUBLIC_AUTH_PROVIDER=oidc
    - NEXT_PUBLIC_OIDC_ISSUER=https://{hostname}:{port}/application/o/{app_slug}/
    - NEXT_PUBLIC_OIDC_CLIENT_ID={client_id}
    - OIDC_CLIENT_SECRET={client_secret}
    - NEXT_PUBLIC_OIDC_REDIRECT_URI={marketplace_url}/auth/callback
    - NEXT_PUBLIC_OIDC_TOKEN_URL=https://{hostname}:{port}/application/o/token/
    - NEXT_PUBLIC_CENTRAL_IDP_NAME={app_slug}
    """
    try:
        base_url = f"https://{central_idp_hostname}:{central_idp_port_https}"
        issuer_url = f"{base_url}/application/o/{app_slug}/"
        token_url = f"{base_url}/application/o/token/"
        redirect_uri = f"{marketplace_url}/auth/callback"
        
        env_vars = {
            "NEXT_PUBLIC_AUTH_ENABLED": "true",
            "NEXT_PUBLIC_AUTH_PROVIDER": "oidc",
            "NEXT_PUBLIC_OIDC_ISSUER": issuer_url,
            "NEXT_PUBLIC_OIDC_CLIENT_ID": client_id,
            "OIDC_CLIENT_SECRET": client_secret,
            "NEXT_PUBLIC_OIDC_REDIRECT_URI": redirect_uri,
            "NEXT_PUBLIC_OIDC_TOKEN_URL": token_url,
            "NEXT_PUBLIC_CENTRAL_IDP_NAME": app_slug
        }
        
        with open(env_file, 'w') as f:
            f.write("# MARKET-LEVEL AUTHENTICATION USING AUTHENTIK SERVER\n")
            for var_name, var_value in env_vars.items():
                f.write(f"{var_name}={var_value}\n")
        
        print(f"\nMarketplace OIDC configuration saved to {env_file}")
        print(f"   Issuer: {issuer_url}")
        print(f"   Token URL: {token_url}")
        print(f"   Redirect URI: {redirect_uri}")
        print(f"   Client ID: {client_id}")
        print(f"   Central IDP Name: {app_slug}")
        return True
    except Exception as e:
        print(f"Could not save marketplace environment file: {e}")
        return False


def save_federation_env(
    client_id: str,
    client_secret: str,
    central_idp_hostname: str,
    central_idp_port_https: str,
    app_slug: str,
    provider_name: str,
    env_file: str = ".env.federation"
):
    """
    Save federation configuration to .env.federation file.
    
    Generates the following variables:
    - CENTRAL_IDP_WELL_KNOWN_URL=https://{hostname}:{port}/application/o/{app_slug}/.well-known/openid-configuration
    - CENTRAL_IDP_CLIENT_ID={client_id}
    - CENTRAL_IDP_CLIENT_SECRET={client_secret}
    - CENTRAL_IDP_PROVIDER_NAME={provider_name}
    """
    try:
        base_url = f"https://{central_idp_hostname}:{central_idp_port_https}"
        well_known_url = f"{base_url}/application/o/{app_slug}/.well-known/openid-configuration"
        
        env_vars = {
            "CENTRAL_IDP_WELL_KNOWN_URL": well_known_url,
            "CENTRAL_IDP_CLIENT_ID": client_id,
            "CENTRAL_IDP_CLIENT_SECRET": client_secret,
            "CENTRAL_IDP_PROVIDER_NAME": provider_name
        }
        
        with open(env_file, 'w') as f:
            f.write("# FEDERATION CONFIGURATION FOR AUTHENTIK\n")
            for var_name, var_value in env_vars.items():
                f.write(f"{var_name}={var_value}\n")
        
        print(f"\nFederation configuration saved to {env_file}")
        print(f"   Well-Known URL: {well_known_url}")
        print(f"   Client ID: {client_id}")
        print(f"   Provider Name: {provider_name}")
        return True
    except Exception as e:
        print(f"Could not save federation environment file: {e}")
        return False


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

def generate_blueprint(
    app_name: str = "main-oidc-app",
    app_slug: str = "main-oidc-app",
    provider_name: str = "main-oidc-provider",
    custom_scopes: List[str] = None,
) -> Dict[str, Any]:
    """
    Generate the complete blueprint structure for the main authentik instance.
    
    Creates all necessary flows, stages, policies, mappings, provider, application,
    and certificate configuration for the main OIDC instance.
    """

    marketplace_url = sanitize_url(os.getenv('MARKETPLACE_URL').rstrip('/'))
    if not validate_url_format(marketplace_url):
        print(f"Error: Invalid MARKETPLACE_URL format: {marketplace_url}")
        sys.exit(1)
    
    wallet_ui_url = sanitize_url(os.getenv('WALLET_UI_URL').rstrip('/'))
    if not validate_url_format(wallet_ui_url):
        print(f"Error: Invalid WALLET_UI_URL format: {wallet_ui_url}")
        sys.exit(1)

    redirect_uris = [
        f"{marketplace_url}/auth/callback",
        f"{marketplace_url}/auth/login",
        f"{wallet_ui_url}/auth/callback",
        f"{wallet_ui_url}/auth/login"
    ]
    
    logout_uri = f"{marketplace_url}/auth/callback/logout"
    
    if custom_scopes is None:
        custom_scopes = ["oe-organizationId", "oe-signerServer", "oe-wellKnownUrl", "oe-walletId", "oe-central-federated_identity"]
    
    admin_email = os.getenv("AUTHENTIK_EMAIL__FROM", "system@authentik.local")

    central_idp_hostname = os.getenv("CENTRAL_IDP_HOSTNAME", "")
    central_idp_port_https = os.getenv("CENTRAL_IDP_PORT_HTTPS", "")

    base_url = f"https://{central_idp_hostname}:{central_idp_port_https}"
    
    email_config = get_email_config()
    cert_name = get_certificate_name()
    
    client_id = generate_random_client_id()
    client_secret = generate_random_client_secret()
    
    save_credentials_to_env(client_id, client_secret, base_url, app_slug, redirect_uris, logout_uri)
    
    save_marketplace_env(
        client_id=client_id,
        client_secret=client_secret,
        central_idp_hostname=central_idp_hostname,
        central_idp_port_https=central_idp_port_https,
        app_slug=app_slug,
        marketplace_url=marketplace_url
    )
    
    save_federation_env(
        client_id=client_id,
        client_secret=client_secret,
        central_idp_hostname=central_idp_hostname,
        central_idp_port_https=central_idp_port_https,
        app_slug=app_slug,
        provider_name=provider_name
    )
    
    blueprint = {
        "version": 1,
        "metadata": {
            "name": f"Main Authentik Configuration - {app_name}",
            "labels": {
                "blueprints.goauthentik.io/generated": "false"
            }
        },
        "entries": []
    }
    
    entries = blueprint["entries"]
    
    # ================================================================
    # PRIORITY 1: CERTIFICATE AND BRAND CONFIGURATION (Run First)
    # ================================================================
    
    if cert_name:
        entries.append({
            "model": "authentik_crypto.certificatekeypair",
            "identifiers": {
                "name": cert_name
            },
            "state": "present"
        })
        
        entries.append({
            "model": "authentik_brands.brand",
            "identifiers": {
                "domain": "authentik-default"
            },
            "attrs": {
                "web_certificate": f"!FIND_MARKER:[authentik_crypto.certificatekeypair, [name, {cert_name}]]",
                "client_certificates": [
                    f"!FIND_MARKER:[authentik_crypto.certificatekeypair, [name, {cert_name}]]"
                ]
            },
            "state": "present"
        })
        
        print(f"Added certificate '{cert_name}' and updated brand to use it (prioritized)")
    else:
        print("No custom certificate found. Using default self-signed certificate.")
    
    # ================================================================
    # 1. CUSTOM FLOWS
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "oe-app-auth-flow"},
        "attrs": {
            "name": "Application Authorization Flow",
            "title": "Authorize Application",
            "designation": "authorization",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": False,
            "denied_action": "message_continue",
            "layout": "stacked"
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "oe-app-invalidation-flow"},
        "attrs": {
            "name": "Application Invalidation Flow",
            "title": "Invalidate Session",
            "designation": "invalidation",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": False,
            "denied_action": "message_continue",
            "layout": "stacked"
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "oe-central-federated-jit-enrollment"},
        "attrs": {
            "name": "oe-central-federated-jit-enrollment",
            "title": "Federated JIT Enrollment",
            "designation": "enrollment",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": False,
            "denied_action": "message_continue",
            "layout": "stacked"
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "oe-enrollment-invitation"},
        "attrs": {
            "name": "oe-enrollment-invitation",
            "title": "Enrollment Invitation",
            "designation": "enrollment",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": True,
            "denied_action": "message_continue",
            "layout": "stacked"
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "oe-recovery"},
        "attrs": {
            "name": "oe-recovery",
            "title": "Recovery",
            "designation": "recovery",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": False,
            "denied_action": "message_continue",
            "layout": "stacked",
            "background": ""
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "oe-authentication-flow"},
        "attrs": {
            "name": "Custom Authentication Flow",
            "title": "Welcome to authentik!",
            "designation": "authentication",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": False,
            "denied_action": "message_continue",
            "layout": "stacked",
            "background": ""
        },
        "state": "present"
    })
    
    # ================================================================
    # 2. CUSTOM STAGES
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_redirect.redirectstage",
        "identifiers": {"name": "oe-redirect-logout-stage"},
        "attrs": {
            "mode": "static",
            "target_static": logout_uri,
            "keep_context": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_user_write.userwritestage",
        "identifiers": {"name": "oe-central-create-jit-user"},
        "attrs": {
            "create_users_as_inactive": False,
            "create_users_group": None,
            "user_creation_mode": "create_when_required",
            "user_path_template": "",
            "user_type": "internal"
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_user_write.userwritestage",
        "identifiers": {"name": "oe-enrollment-invitation-write"},
        "attrs": {
            "create_users_as_inactive": False,
            "create_users_group": None,
            "user_creation_mode": "create_when_required",
            "user_path_template": "",
            "user_type": "internal"
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_invitation.invitationstage",
        "identifiers": {"name": "oe-enrollment-invitation"},
        "attrs": {
            "continue_flow_without_invitation": False
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_deny.denystage",
        "identifiers": {"name": "oe-user-email-check-deny"},
        "attrs": {
            "deny_message": "Email already exists! Contact admin."
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_deny.denystage",
        "identifiers": {"name": "oe-user-username-check-deny"},
        "attrs": {
            "deny_message": "Username already exists! Try another one."
        },
        "state": "present"
    })
    
    # ================================================================
    # 2.5 RECOVERY FLOW STAGES
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_identification.identificationstage",
        "identifiers": {"name": "oe-recovery-authentication-identification"},
        "attrs": {
            "name": "oe-recovery-authentication-identification",
            "user_fields": ["username", "email"],
            "password_stage": None,
            "captcha_stage": None,
            "case_insensitive_matching": True,
            "pretend_user_exists": True,
            "show_matched_user": True,
            "show_source_labels": False,
            "sources": [],
            "enable_remember_me": False,
            "enrollment_flow": None,
            "passwordless_flow": None,
            "recovery_flow": None,
            "webauthn_stage": None
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_email.emailstage",
        "identifiers": {"name": "oe-recovery-email"},
        "attrs": {
            "name": "oe-recovery-email",
            "activate_user_on_success": True,
            "use_global_settings": False,
            "token_expiry": "minutes=30",
            "subject": "Password Recovery",
            "template": "email/password_reset.html",
            "recovery_max_attempts": 5,
            "recovery_cache_timeout": "minutes=5",
            "from_address": email_config["from_address"],
            "host": email_config["host"],
            "port": email_config["port"],
            "username": email_config["username"],
            "password": email_config["password"],
            "timeout": email_config["timeout"],
            "use_ssl": email_config["use_ssl"],
            "use_tls": email_config["use_tls"]
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_user_write.userwritestage",
        "identifiers": {"name": "default-password-change-write"},
        "attrs": {
            "name": "default-password-change-write",
            "user_creation_mode": "never_create",
            "create_users_as_inactive": False,
            "user_type": "external",
            "create_users_group": None,
            "user_path_template": ""
        },
        "state": "present"
    })
    
    # ================================================================
    # 3. PROMPT STAGES
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_prompt.promptstage",
        "identifiers": {"name": "default-source-enrollment-prompt"},
        "attrs": {
            "fields": [
                "!FIND_MARKER:[authentik_stages_prompt.prompt, [name, default-source-enrollment-field-username]]",
                "!FIND_MARKER:[authentik_stages_prompt.prompt, [name, default-user-settings-field-name]]",
                "!FIND_MARKER:[authentik_stages_prompt.prompt, [name, initial-setup-field-password]]",
                "!FIND_MARKER:[authentik_stages_prompt.prompt, [name, initial-setup-field-password-repeat]]"
            ],
            "validation_policies": []
        },
        "state": "present"
    })
    
    # ================================================================
    # 3.5 RECOVERY FLOW PROMPTS
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "default-password-change-field-password"},
        "attrs": {
            "field_key": "password",
            "label": "Password",
            "type": "password",
            "required": True,
            "order": 300,
            "placeholder": "Password",
            "placeholder_expression": False,
            "initial_value": "",
            "initial_value_expression": False,
            "sub_text": ""
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "default-password-change-field-password-repeat"},
        "attrs": {
            "field_key": "password_repeat",
            "label": "Password (repeat)",
            "type": "password",
            "required": True,
            "order": 301,
            "placeholder": "Password (repeat)",
            "placeholder_expression": False,
            "initial_value": "",
            "initial_value_expression": False,
            "sub_text": ""
        },
        "state": "present"
    })
    
    # ================================================================
    # 3.6 RECOVERY FLOW PASSWORD POLICY
    # ================================================================
    
    entries.append({
        "model": "authentik_policies_password.passwordpolicy",
        "identifiers": {"name": "default-password-change-password-policy"},
        "attrs": {
            "name": "default-password-change-password-policy",
            "password_field": "password",
            "length_min": 8,
            "amount_uppercase": 0,
            "amount_lowercase": 0,
            "amount_digits": 0,
            "amount_symbols": 0,
            "symbol_charset": '!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~ ',
            "error_message": "Password needs to be 8 characters or longer.",
            "check_static_rules": True,
            "check_zxcvbn": True,
            "zxcvbn_score_threshold": 2,
            "check_have_i_been_pwned": False,
            "hibp_allowed_count": 0
        },
        "state": "present"
    })
    
    # ================================================================
    # 3.7 RECOVERY FLOW PROMPT STAGE
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_prompt.promptstage",
        "identifiers": {"name": "default-password-change-prompt"},
        "attrs": {
            "name": "default-password-change-prompt",
            "fields": [
                "!FIND_MARKER:[authentik_stages_prompt.prompt, [name, default-password-change-field-password]]",
                "!FIND_MARKER:[authentik_stages_prompt.prompt, [name, default-password-change-field-password-repeat]]"
            ],
            "validation_policies": [
                "!FIND_MARKER:[authentik_policies_password.passwordpolicy, [name, default-password-change-password-policy]]"
            ]
        },
        "state": "present"
    })
    
    # ================================================================
    # 4. CUSTOM PROMPTS
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "oe-orgId"},
        "attrs": {
            "field_key": "orgId",
            "label": "Organization ID",
            "type": "dropdown",
            "required": True,
            "placeholder": 'return [\n    {"label": "ocean_enterprise", "value": "ocean_enterprise"},\n    {"label": "delta_dao", "value": "delta_dao"},\n    {"label": "other_org", "value": "other_org"},\n]',
            "placeholder_expression": True,
            "initial_value": "",
            "initial_value_expression": False,
            "order": 100
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "default-source-enrollment-field-username"},
        "attrs": {
            "field_key": "username",
            "label": "Username",
            "type": "text",
            "required": True,
            "order": 101,
            "placeholder": "Username",
            "placeholder_expression": False,
            "initial_value": "",
            "initial_value_expression": False,
            "sub_text": ""
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "default-user-settings-field-name"},
        "attrs": {
            "field_key": "name",
            "label": "Name",
            "type": "text",
            "required": True,
            "order": 200,
            "placeholder": "Full name",
            "placeholder_expression": False,
            "initial_value": "",
            "initial_value_expression": False,
            "sub_text": ""
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "initial-setup-field-password"},
        "attrs": {
            "field_key": "password",
            "label": "Password",
            "type": "password",
            "required": True,
            "order": 300,
            "placeholder": "Password",
            "placeholder_expression": False,
            "initial_value": "",
            "initial_value_expression": False,
            "sub_text": ""
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "initial-setup-field-password-repeat"},
        "attrs": {
            "field_key": "password_repeat",
            "label": "Password (repeat)",
            "type": "password",
            "required": True,
            "order": 301,
            "placeholder": "Password (repeat)",
            "placeholder_expression": False,
            "initial_value": "",
            "initial_value_expression": False,
            "sub_text": ""
        },
        "state": "present"
    })
    
    # ================================================================
    # 4.5 CUSTOM AUTHENTICATION FLOW - IDENTIFICATION STAGE
    # ================================================================
    
    entries.append({
        "model": "authentik_stages_identification.identificationstage",
        "identifiers": {"name": "oe-authentication-identification"},
        "attrs": {
            "name": "oe-authentication-identification",
            "user_fields": ["username", "email"],
            "password_stage": "!FIND_MARKER:[authentik_stages_password.passwordstage, [name, default-authentication-password]]",
            "captcha_stage": None,
            "case_insensitive_matching": True,
            "pretend_user_exists": True,
            "show_matched_user": True,
            "show_source_labels": False,
            "sources": [],
            "enable_remember_me": False,
            "enrollment_flow": None,
            "passwordless_flow": None,
            "recovery_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-recovery]]",
            "webauthn_stage": None
        },
        "state": "present"
    })
    
    # ================================================================
    # 4.6 CUSTOM AUTHENTICATION FLOW - STAGE BINDINGS
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 0,
            "stage": "!FIND_MARKER:[authentik_stages_identification.identificationstage, [name, oe-authentication-identification]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-authentication-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_authenticator_validate.authenticatorvalidatestage, [name, default-authentication-mfa-validation]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-authentication-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_user_login.userloginstage, [name, default-authentication-login]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-authentication-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # ================================================================
    # 5. CUSTOM PROPERTY MAPPINGS
    # ================================================================
    
    entries.append({
        "model": "authentik_sources_oauth.oauthsourcepropertymapping",
        "identifiers": {"name": "oe-central-federated-oidc-mapping"},
        "attrs": {
            "name": "oe-central-federated-oidc-mapping",
            "expression": 'return {\n    "username": info.get("preferred_username") or info.get("nickname") or info.get("sub"),\n    "email": info.get("email"),\n    "name": info.get("name") or info.get("given_name") or "Federated User",\n\n    "attributes": {\n        "upstream_idp": source.name if source else "unknown1",\n        "orgId": info.get("orgId", "unknown1"),\n        "walletId": info.get("walletId", "unknown1"),\n        "signerServer": info.get("signerServer", "unknown1"),\n        "wellKnownUrl": info.get("wellKnownUrl", "unknown1"),\n        "external_subject": info.get("sub"),\n        "idp_issuer": info.get("iss"),\n    },\n\n    "orgId": info.get("orgId", "unknown7"),\n    "walletId": info.get("walletId", "unknown7"),\n    "signerServer": info.get("signerServer", "unknown7"),\n    "wellKnownUrl": info.get("wellKnownUrl", "unknown7"),\n    "upstream_idp": source.name if source else "unknown7",\n    "external_subject": info.get("sub"),\n}'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "oe-organizationId"},
        "attrs": {
            "scope_name": "oe-organizationId",
            "description": "used to gain organization Id claim",
            "expression": 'return {\n    "orgId": request.user.attributes.get("orgId", "")\n}'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "oe-signerServer"},
        "attrs": {
            "scope_name": "oe-signerServer",
            "description": "Used to claim signer server url",
            "expression": 'return {\n    "signerServer": request.user.attributes.get("signerServer", "")\n}'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "oe-wellKnownUrl"},
        "attrs": {
            "scope_name": "oe-wellKnownUrl",
            "description": "Used to claim well-known url",
            "expression": 'return {\n    "wellKnownUrl": request.user.attributes.get("wellKnownUrl", "")\n}'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "oe-walletId"},
        "attrs": {
            "scope_name": "oe-walletId",
            "description": "Used to claim wallet id",
            "expression": 'return {\n    "walletId": request.user.attributes.get("walletId", "")\n}'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "oe-central-federated_identity"},
        "attrs": {
            "scope_name": "oe-central-federated_identity",
            "description": "Federated identity information",
            "expression": 'return {\n    "upstream_idp": request.user.attributes.get("upstream_idp", "unknown3")\n}'
        },
        "state": "present"
    })
    
    # ================================================================
    # 6. CUSTOM POLICIES
    # ================================================================
    
    entries.append({
        "model": "authentik_policies_expression.expressionpolicy",
        "identifiers": {"name": "oe-save-user-attributes"},
        "attrs": {
            "execution_logging": True,
            "expression": 'org = context.get("prompt_data", {}).get("orgId")\nwallet_id = context.get("prompt_data", {}).get("walletId")\nsigner_server = context.get("prompt_data", {}).get("signerServer")\nwell_known_url = context.get("prompt_data", {}).get("wellKnownUrl")\nupstream_idp = context.get("prompt_data", {}).get("upstream_idp")\n\nuser = context.get("pending_user")\n\nif user:\n    if org:\n        user.attributes["orgId"] = org\n    \n    if wallet_id:\n        user.attributes["walletId"] = wallet_id\n    \n    if signer_server:\n        user.attributes["signerServer"] = signer_server\n    \n    if well_known_url:\n        user.attributes["wellKnownUrl"] = well_known_url\n    \n    if upstream_idp:\n        user.attributes["upstream_idp"] = upstream_idp\n    \n    user.save()\n\nreturn True'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_policies_expression.expressionpolicy",
        "identifiers": {"name": "oe-check-email-exist-policy"},
        "attrs": {
            "execution_logging": True,
            "expression": f'from authentik.core.models import User\nfrom django.core.mail import send_mail\nfrom django.conf import settings\n\nemail = request.context.get("prompt_data", {{}}).get("email")\n\nif not email:\n    return False\n\nexists = User.objects.filter(email__iexact=email).exists()\n\nif exists:\n    send_mail(\n        subject="Invitation attempted for existing user",\n        message=(\n            f"An invitation was created for \'{{email}}\', "\n            "but a user with this email already exists."\n        ),\n        from_email=settings.DEFAULT_FROM_EMAIL,\n        recipient_list=["{admin_email}"],\n        fail_silently=False,\n    )\n\nreturn exists'
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_policies_expression.expressionpolicy",
        "identifiers": {"name": "oe-check-username-exist-policy"},
        "attrs": {
            "execution_logging": True,
            "expression": 'from authentik.core.models import User\n\nusername = request.context.get("prompt_data", {}).get("username")\n\nif not username:\n    return False\n\nexists = User.objects.filter(username__iexact=username).exists()\n\nreturn exists'
        },
        "state": "present"
    })
    
    # ================================================================
    # 7. FLOW STAGE BINDINGS FOR oe-recovery FLOW
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 0,
            "stage": "!FIND_MARKER:[authentik_stages_identification.identificationstage, [name, oe-recovery-authentication-identification]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-recovery]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_email.emailstage, [name, oe-recovery-email]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-recovery]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_prompt.promptstage, [name, default-password-change-prompt]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-recovery]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 30,
            "stage": "!FIND_MARKER:[authentik_stages_user_write.userwritestage, [name, default-password-change-write]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-recovery]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # ================================================================
    # 8. FLOW STAGE BINDINGS FOR oe-central-federated-jit-enrollment
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_user_write.userwritestage, [name, oe-central-create-jit-user]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-central-federated-jit-enrollment]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_user_login.userloginstage, [name, default-authentication-login]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-central-federated-jit-enrollment]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # ================================================================
    # 9. FLOW STAGE BINDINGS FOR oe-enrollment-invitation
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_invitation.invitationstage, [name, oe-enrollment-invitation]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "id": "oe-email-check-binding",
        "identifiers": {
            "order": 15,
            "stage": "!FIND_MARKER:[authentik_stages_deny.denystage, [name, oe-user-email-check-deny]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_prompt.promptstage, [name, default-source-enrollment-prompt]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "id": "oe-username-check-binding",
        "identifiers": {
            "order": 25,
            "stage": "!FIND_MARKER:[authentik_stages_deny.denystage, [name, oe-user-username-check-deny]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 30,
            "stage": "!FIND_MARKER:[authentik_stages_user_write.userwritestage, [name, oe-enrollment-invitation-write]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "id": "oe-local-flow-binding",
        "identifiers": {
            "order": 40,
            "stage": "!FIND_MARKER:[authentik_stages_redirect.redirectstage, [name, oe-redirect-logout-stage]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # ================================================================
    # 10. POLICY BINDINGS FOR oe-enrollment-invitation
    # ================================================================
    
    entries.append({
        "model": "authentik_policies.policybinding",
        "identifiers": {
            "order": 0,
            "policy": "!FIND_MARKER:[authentik_policies_expression.expressionpolicy, [name, oe-save-user-attributes]]",
            "target": "!KEYOF_MARKER:oe-local-flow-binding"
        },
        "attrs": {
            "enabled": True,
            "failure_result": False,
            "group": None,
            "negate": False,
            "timeout": 30,
            "user": None
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_policies.policybinding",
        "identifiers": {
            "order": 0,
            "policy": "!FIND_MARKER:[authentik_policies_expression.expressionpolicy, [name, oe-check-email-exist-policy]]",
            "target": "!KEYOF_MARKER:oe-email-check-binding"
        },
        "attrs": {
            "enabled": True,
            "failure_result": False,
            "group": None,
            "negate": False,
            "timeout": 30,
            "user": None
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_policies.policybinding",
        "identifiers": {
            "order": 0,
            "policy": "!FIND_MARKER:[authentik_policies_expression.expressionpolicy, [name, oe-check-username-exist-policy]]",
            "target": "!KEYOF_MARKER:oe-username-check-binding"
        },
        "attrs": {
            "enabled": True,
            "failure_result": False,
            "group": None,
            "negate": False,
            "timeout": 30,
            "user": None
        },
        "state": "present"
    })
    
    # ================================================================
    # 11. FLOW STAGE BINDINGS FOR oe-app-invalidation-flow
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_user_logout.userlogoutstage, [name, default-invalidation-logout]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-app-invalidation-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_redirect.redirectstage, [name, oe-redirect-logout-stage]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-app-invalidation-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # ================================================================
    # 12. CUSTOM OAUTH2 PROVIDER
    # ================================================================
    
    property_mappings = []
    custom_scope_names = ["oe-organizationId", "oe-signerServer", "oe-wellKnownUrl", "oe-walletId", "oe-central-federated_identity"]
    for scope_name in custom_scope_names:
        property_mappings.append(f"!FIND_MARKER:[authentik_providers_oauth2.scopemapping, [scope_name, {scope_name}]]")
    
    default_scopes = ["openid", "email", "profile", "offline_access"]
    for scope in default_scopes:
        property_mappings.append(f"!FIND_MARKER:[authentik_providers_oauth2.scopemapping, [scope_name, {scope}]]")
    
    redirect_uris_data = generate_redirect_uris(redirect_uris)
    
    entries.append({
        "model": "authentik_providers_oauth2.oauth2provider",
        "identifiers": {"name": provider_name},
        "attrs": {
            "name": provider_name,
            "authentication_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-authentication-flow]]",
            "authorization_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, default-provider-authorization-explicit-consent]]",
            "invalidation_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, oe-app-invalidation-flow]]",
            "client_id": client_id,
            "client_secret": client_secret,
            "client_type": "confidential",
            "grant_types": [
                "authorization_code",
                "implicit",
                "hybrid",
                "refresh_token",
                "client_credentials",
                "password",
                "urn:ietf:params:oauth:grant-type:device_code"
            ],
            "access_code_validity": "minutes=1",
            "access_token_validity": "hours=1",
            "refresh_token_validity": "days=30",
            "refresh_token_threshold": "hours=1",
            "include_claims_in_id_token": True,
            "issuer_mode": "per_provider",
            "logout_method": "backchannel",
            "logout_uri": logout_uri,
            "backchannel_logout_enabled": True,
            "sub_mode": "hashed_user_id",
            "property_mappings": property_mappings,
            "redirect_uris": redirect_uris_data,
            "signing_key": f"!FIND_MARKER:[authentik_crypto.certificatekeypair, [name, {cert_name}]]" if cert_name else None
        },
        "state": "present"
    })
    
    # ================================================================
    # 13. CUSTOM APPLICATION
    # ================================================================
    
    entries.append({
        "model": "authentik_core.application",
        "identifiers": {"slug": app_slug},
        "attrs": {
            "name": app_name,
            "provider": f"!FIND_MARKER:[authentik_providers_oauth2.oauth2provider, [name, {provider_name}]]",
            "policy_engine_mode": "any",
            "meta_description": "",
            "meta_icon": "",
            "meta_launch_url": "",
            "open_in_new_tab": False
        },
        "state": "present"
    })

    
    blueprint["_metadata"] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "certificate": cert_name if cert_name else "default"
    }
    
    return blueprint


def find_provider_entry(blueprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the OAuth2 provider entry in the blueprint."""
    for entry in blueprint["entries"]:
        if entry.get("model") == "authentik_providers_oauth2.oauth2provider":
            return entry
    return None


def save_blueprint_yaml(blueprint: Dict[str, Any], output_file: str):
    """Save the blueprint as a YAML file with proper !Find and !KeyOf tags."""
    
    blueprint_copy = blueprint.copy()
    blueprint_copy.pop("_metadata", None)
    yaml_obj = YAML()
    yaml_obj.indent(mapping=2, sequence=4, offset=2)
    yaml_obj.preserve_quotes = True
    
    with open(output_file, 'w') as f:
        yaml_obj.dump(blueprint_copy, f)
    
    with open(output_file, 'r') as f:
        content = f.read()
    
    import re
    
    content = re.sub(r'!FIND_MARKER:', '!Find ', content)
    content = re.sub(r'!KEYOF_MARKER:', '!KeyOf ', content)
    
    content = re.sub(r'"!Find\s+', '!Find ', content)
    content = re.sub(r'!Find\s+"', '!Find ', content)
    content = re.sub(r'!Find\s+\'([^\']+)\'', r'!Find \1', content)
    
    content = re.sub(r'"!KeyOf\s+', '!KeyOf ', content)
    content = re.sub(r'!KeyOf\s+"', '!KeyOf ', content)
    content = re.sub(r'!KeyOf\s+\'([^\']+)\'', r'!KeyOf \1', content)
    
    def fix_tags(match):
        return f'{match.group(1)} {match.group(2)}'
    
    content = re.sub(r'"(!Find)\s+([^"]+)"', fix_tags, content)
    content = re.sub(r"'(!Find)\s+([^']+)'", fix_tags, content)
    content = re.sub(r'"(!KeyOf)\s+([^"]+)"', fix_tags, content)
    content = re.sub(r"'(!KeyOf)\s+([^']+)'", fix_tags, content)
    content = re.sub(r'!Find\s+!Find', '!Find', content)
    content = re.sub(r'url:\s+\n\s+', 'url: ', content)
    content = re.sub(r'target_static:\s+\n\s+', 'target_static: ', content)
    content = re.sub(r'logout_uri:\s+\n\s+', 'logout_uri: ', content)
    content = re.sub(r'create_users_group:\s+None', 'create_users_group:', content)
    content = re.sub(r'group:\s+None', 'group:', content)
    content = re.sub(r'user:\s+None', 'user:', content)
    content = re.sub(r'signing_key:\s+null', 'signing_key:', content)
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Blueprint saved to: {output_file}")


def main():
    """Main function to generate blueprint from environment variables."""
    
    app_slug = os.getenv("AUTHENTIK_APP_SLUG", "main-oidc-app")
    app_name = app_slug
    provider_name = os.getenv("AUTHENTIK_PROVIDER_NAME", "main-oidc-provider")
    
    output_file = os.getenv("AUTHENTIK_OUTPUT_FILE", "dataspace-operator-authentik-blueprint.yaml")
    
    print("Generating Main Authentik Blueprint...")
    print(f"App Name: {app_name}")
    print(f"Provider: {provider_name}")
    print("")
    
    blueprint = generate_blueprint(
        app_name=app_name,
        app_slug=app_slug,
        provider_name=provider_name
    )
    
    save_blueprint_yaml(blueprint, output_file)
    
    print("\nBlueprint Summary:")
    
    provider_entry = find_provider_entry(blueprint)
    if provider_entry:
        attrs = provider_entry.get("attrs", {})
        print(f"  Client ID / Audience: {attrs.get('client_id', 'N/A')}")
        print(f"  Client Secret: {attrs.get('client_secret', 'N/A')}")
        print(f"  Backchannel Logout: {attrs.get('backchannel_logout_enabled', False)}")
        print(f"  Signing Key: {attrs.get('signing_key', 'Default (self-signed)')}")
    else:
        print("  No provider found in blueprint")
    
    print("\nComponents included:")
    print("  Custom Authentication Flow (oe-authentication-flow)")
    print("    - oe-authentication-identification (Identification Stage with Password Stage & Recovery)")
    print("    - default-authentication-mfa-validation (MFA Validation Stage)")
    print("    - default-authentication-login (User Login Stage)")
    print("  Recovery Flow (oe-recovery)")
    print("    - oe-recovery-authentication-identification (Identification Stage)")
    print("    - oe-recovery-email (Email Stage with SMTP config from .env or defaults)")
    print("    - default-password-change-prompt (Prompt Stage)")
    print("    - default-password-change-write (User Write Stage)")
    print("  Enrollment Invitation Flow (oe-enrollment-invitation)")
    print("    - oe-enrollment-invitation (Invitation Stage)")
    print("    - oe-user-email-check-deny (Deny Stage with email check policy & admin notification)")
    print("    - default-source-enrollment-prompt (Prompt Stage)")
    print("    - oe-user-username-check-deny (Deny Stage with username check policy)")
    print("    - oe-enrollment-invitation-write (User Write Stage)")
    print("    - oe-redirect-logout-stage (Redirect Stage)")
    print("  Federated JIT Enrollment Flow (oe-central-federated-jit-enrollment)")
    print("    - oe-central-create-jit-user (User Write Stage)")
    print("    - default-authentication-login (User Login Stage)")
    print("  OAuth Source Property Mapping: oe-central-federated-oidc-mapping")
    print("  Scope Mappings:")
    print("    - oe-organizationId (returns 'orgId')")
    print("    - oe-signerServer")
    print("    - oe-wellKnownUrl")
    print("    - oe-walletId")
    print("    - oe-central-federated_identity (returns 'upstream_idp')")
    print("  oe-app-auth-flow")
    print("  oe-app-invalidation-flow with default-invalidation-logout + oe-redirect-logout-stage")
    print("  OAuth2 Provider with Custom Authentication Flow")
    print("  oe-save-user-attributes Policy")
    print("  oe-check-email-exist-policy (with email notification to admin)")
    print("  oe-check-username-exist-policy")
    print("  oe-orgId Prompt")
    print("  All Flow Stage Bindings")
    print("  Policy Bindings with !KeyOf")
    print("  OAuth2 Provider with logout_uri")
    print("  Application")
    
    cert_name = blueprint["_metadata"].get("certificate", "default")
    if cert_name != "default":
        print("\nWeb Certificate:")
        print(f"  Certificate found: {cert_name}")
        print(f"  Brand updated to use certificate: {cert_name}")
        print(f"  Provider signing key set to: {cert_name}")
    else:
        print("\nWeb Certificate:")
        print("  No custom certificate found. Using default self-signed certificate.")
        print("  Provider signing key using default (self-signed)")
    
    print("\nEnvironment variables saved to .env:")
    print("  AUTHENTIK_AUDIENCE (Client ID)")
    print("  AUTHENTIK_CLIENT_SECRET")
    print("  AUTHENTIK_JWKS_URI")
    print("  AUTHENTIK_ISSUER")
    print("\nDone! You can now import this blueprint in authentik.")
    print(f"File: {output_file}")


if __name__ == "__main__":
    main()