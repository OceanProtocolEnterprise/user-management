#!/usr/bin/env python3
"""
Authentik Main Instance Blueprint Generator
Generates a complete blueprint YAML file for the main authentik instance with:
- Recovery Flow
- Federated JIT Enrollment Flow
- OAuth Source Property Mapping
- Scope Mappings
- All necessary flows, stages, and bindings
- Recovery flow attached to authentication flow
"""

import os
import secrets
import string
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    print("⚠️  ruamel.yaml not found. Installing...")
    os.system("pip install ruamel.yaml")
    from ruamel.yaml import YAML
    HAS_RUAMEL = True

# Load environment variables
load_dotenv()

def generate_random_client_id() -> str:
    """Generate a random client ID (32 characters)"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(32))

def generate_random_client_secret() -> str:
    """Generate a random client secret (43 characters)"""
    chars = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(chars) for _ in range(43))

def generate_redirect_uris(redirect_uris_list: List[str]) -> List[Dict[str, Any]]:
    """Generate redirect URIs structure for the blueprint"""
    return [
        {
            "matching_mode": "strict",
            "redirect_uri_type": "authorization",
            "url": url.strip()
        }
        for url in redirect_uris_list
    ]

def generate_blueprint(
    app_name: str = "main-oidc-app",
    app_slug: str = "main-oidc-app",
    provider_name: str = "main-oidc-provider",
    redirect_uris: List[str] = None,
    logout_uri: str = "",
    custom_scopes: List[str] = None
) -> Dict[str, Any]:
    """
    Generate the complete blueprint structure for the main authentik instance
    """
    
    # Default values
    if redirect_uris is None:
        redirect_uris = [
            "https://your-app-url.com/auth/callback",
            "https://your-app-url.com/auth/login"
        ]
    
    if logout_uri == "":
        logout_uri = redirect_uris[-1] if redirect_uris else "https://your-app-url.com/auth/callback/logout"
    
    if custom_scopes is None:
        custom_scopes = ["organizationId", "signerServer", "walletId", "federated_identity"]
    
    # Generate random credentials
    client_id = generate_random_client_id()
    client_secret = generate_random_client_secret()
    
    # Define the blueprint structure
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
    # 1. CUSTOM FLOWS
    # ================================================================
    
    # Flow: app-auth-flow (Authorization Flow)
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "app-auth-flow"},
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
    
    # Flow: app-invalidation-flow (Invalidation Flow)
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "app-invalidation-flow"},
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
    
    # Flow: recovery-flow (Recovery Flow)
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "recovery-flow"},
        "attrs": {
            "name": "recovery-flow",
            "title": "Recovery Flow",
            "designation": "recovery",
            "authentication": "none",
            "policy_engine_mode": "any",
            "compatibility_mode": False,
            "denied_action": "message_continue",
            "layout": "stacked"
        },
        "state": "present"
    })
    
    # Flow: federated-jit-enrollment (Federated JIT Enrollment Flow)
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "federated-jit-enrollment"},
        "attrs": {
            "name": "federated-jit-enrollment",
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
    
    # ================================================================
    # 2. CUSTOM STAGES
    # ================================================================
    
    # Stage: redirect-logout-stage
    entries.append({
        "model": "authentik_stages_redirect.redirectstage",
        "identifiers": {"name": "redirect-logout-stage"},
        "attrs": {
            "mode": "static",
            "target_static": logout_uri,
            "keep_context": True
        },
        "state": "present"
    })
    
    # Stage: recovery-email (Email Stage for Recovery)
    entries.append({
        "model": "authentik_stages_email.emailstage",
        "identifiers": {"name": "recovery-email"},
        "attrs": {
            "name": "recovery-email",
            "activate_user_on_success": False,
            "host": os.getenv("EMAIL_HOST", ""),
            "port": int(os.getenv("EMAIL_PORT", "587")),
            "username": os.getenv("EMAIL_USERNAME", ""),
            "password": os.getenv("EMAIL_PASSWORD", ""),
            "use_tls": True,
            "use_ssl": False,
            "timeout": 30,
            "from_address": os.getenv("EMAIL_FROM", "noreply@authentik.local"),
            "subject": "Recovery Email",
            "template": "email/recovery.html"
        },
        "state": "present"
    })
    
    # Stage: create-jit-user (User Write Stage for JIT Enrollment)
    entries.append({
        "model": "authentik_stages_user_write.userwritestage",
        "identifiers": {"name": "create-jit-user"},
        "attrs": {
            "create_users_as_inactive": False,
            "create_users_group": None,
            "user_creation_mode": "create_when_required",
            "user_path_template": "",
            "user_type": "internal"
        },
        "state": "present"
    })
    
    # ================================================================
    # 3. CUSTOM PROMPTS
    # ================================================================
    
    # Prompt: orgId (dropdown)
    entries.append({
        "model": "authentik_stages_prompt.prompt",
        "identifiers": {"name": "orgId"},
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
    
    # ================================================================
    # 4. IDENTIFICATION STAGES
    # ================================================================
    
    # Stage: recovery-authentication-identification (Identification for Recovery)
    # This stage should be simple - just identify user by email
    entries.append({
        "model": "authentik_stages_identification.identificationstage",
        "identifiers": {"name": "recovery-authentication-identification"},
        "attrs": {
            "name": "recovery-authentication-identification",
            "user_fields": ["email"],
            "pretend_user_exists": True,
            "sources": [],
            "show_source_labels": False,
            "enable_remember_me": False,
            "case_insensitive_matching": True
        },
        "state": "present"
    })
    
    # ================================================================
    # 5. PROMPT STAGES
    # ================================================================
    
    # Prompt Stage: default-password-change-prompt
    entries.append({
        "model": "authentik_stages_prompt.promptstage",
        "identifiers": {"name": "default-password-change-prompt"},
        "attrs": {
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
    # 6. CUSTOM PROPERTY MAPPINGS
    # ================================================================
    
    # OAuth Source Property Mapping: federated-oidc-mapping
    entries.append({
        "model": "authentik_sources_oauth.oauthsourcepropertymapping",
        "identifiers": {"name": "federated-oidc-mapping"},
        "attrs": {
            "name": "federated-oidc-mapping",
            "expression": 'return {\n    "username": info.get("preferred_username") or info.get("nickname") or info.get("sub"),\n    "email": info.get("email"),\n    "name": info.get("name") or info.get("given_name") or "Federated User",\n\n    "attributes": {\n        "upstream_idp": source.name if source else "unknown1",\n        "orgId": info.get("orgId", "unknown1"),\n        "walletId": info.get("walletId", "unknown1"),\n        "signerServer": info.get("signerServer", "unknown1"),\n        "external_subject": info.get("sub"),\n        "idp_issuer": info.get("iss"),\n    },\n\n    "orgId": info.get("orgId", "unknown7"),\n    "walletId": info.get("walletId", "unknown7"),\n    "signerServer": info.get("signerServer", "unknown7"),\n    "upstream_idp": source.name if source else "unknown7",\n    "external_subject": info.get("sub"),\n}'
        },
        "state": "present"
    })
    
    # Scope Mapping: organizationId
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "organizationId"},
        "attrs": {
            "scope_name": "organizationId",
            "description": "used to gain organization Id claim",
            "expression": 'return {\n    "orgId": request.user.attributes.get("orgId", "")\n}'
        },
        "state": "present"
    })
    
    # Scope Mapping: signerServer
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "signerServer"},
        "attrs": {
            "scope_name": "signerServer",
            "description": "Used to claim signer server url",
            "expression": 'return {\n    "signerServer": request.user.attributes.get("signerServer", "")\n}'
        },
        "state": "present"
    })
    
    # Scope Mapping: walletId
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "walletId"},
        "attrs": {
            "scope_name": "walletId",
            "description": "Used to claim wallet id",
            "expression": 'return {\n    "walletId": request.user.attributes.get("walletId", "")\n}'
        },
        "state": "present"
    })
    
    # Scope Mapping: federated_identity
    entries.append({
        "model": "authentik_providers_oauth2.scopemapping",
        "identifiers": {"name": "federated_identity"},
        "attrs": {
            "scope_name": "federated_identity",
            "description": "Federated identity information",
            "expression": 'return {\n    "upstream_idp": request.user.attributes.get("upstream_idp", "unknown3")\n}'
        },
        "state": "present"
    })
    
    # ================================================================
    # 7. CUSTOM POLICIES
    # ================================================================
    
    # Policy: save-user-attributes
    entries.append({
        "model": "authentik_policies_expression.expressionpolicy",
        "identifiers": {"name": "save-user-attributes"},
        "attrs": {
            "execution_logging": True,
            "expression": 'org = context.get("prompt_data", {}).get("orgId")\nwallet_id = context.get("prompt_data", {}).get("walletId")\nsigner_server = context.get("prompt_data", {}).get("signerServer")\n\nuser = context.get("pending_user")\n\nif user:\n    if org:\n        user.attributes["orgId"] = org\n    \n    if wallet_id:\n        user.attributes["walletId"] = wallet_id\n    \n    if signer_server:\n        user.attributes["signerServer"] = signer_server\n    \n    user.save()\n\nreturn True'
        },
        "state": "present"
    })
    
    # ================================================================
    # 8. FLOW STAGE BINDINGS FOR recovery-flow
    # ================================================================
    
    # Binding 1: recovery-authentication-identification (order: 10)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_identification.identificationstage, [name, recovery-authentication-identification]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, recovery-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # Binding 2: recovery-email (order: 20)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_email.emailstage, [name, recovery-email]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, recovery-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # Binding 3: default-password-change-prompt (order: 30)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 30,
            "stage": "!FIND_MARKER:[authentik_stages_prompt.promptstage, [name, default-password-change-prompt]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, recovery-flow]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # Binding 4: default-password-change-write (order: 40)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 40,
            "stage": "!FIND_MARKER:[authentik_stages_user_write.userwritestage, [name, default-password-change-write]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, recovery-flow]]"
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
    # 9. FLOW STAGE BINDINGS FOR federated-jit-enrollment
    # ================================================================
    
    # Binding 1: create-jit-user (order: 10)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_user_write.userwritestage, [name, create-jit-user]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, federated-jit-enrollment]]"
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
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, federated-jit-enrollment]]"
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
    # 10. FLOW STAGE BINDINGS FOR app-invalidation-flow
    # ================================================================
    
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_user_logout.userlogoutstage, [name, default-invalidation-logout]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, app-invalidation-flow]]"
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
            "stage": "!FIND_MARKER:[authentik_stages_redirect.redirectstage, [name, redirect-logout-stage]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, app-invalidation-flow]]"
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
    # 11. CUSTOM OAUTH2 PROVIDER
    # ================================================================
    
    property_mappings = []
    custom_scope_names = ["organizationId", "signerServer", "walletId", "federated_identity"]
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
            "authorization_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, default-provider-authorization-explicit-consent]]",
            "invalidation_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, app-invalidation-flow]]",
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
            "redirect_uris": redirect_uris_data
        },
        "state": "present"
    })
    
    # ================================================================
    # 12. CUSTOM APPLICATION
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
    
    # ================================================================
    # 13. UPDATE DEFAULT AUTHENTICATION FLOW WITH RECOVERY
    # ================================================================
    
    # Update the default authentication flow's identification stage
    # to include the recovery flow
    entries.append({
        "model": "authentik_stages_identification.identificationstage",
        "identifiers": {"name": "default-authentication-identification"},
        "attrs": {
            "recovery_flow": "!FIND_MARKER:[authentik_flows.flow, [slug, recovery-flow]]"
        },
        "state": "present"
    })
    
    blueprint["_metadata"] = {
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    return blueprint

def find_provider_entry(blueprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the OAuth2 provider entry in the blueprint"""
    for entry in blueprint["entries"]:
        if entry.get("model") == "authentik_providers_oauth2.oauth2provider":
            return entry
    return None

def save_blueprint_yaml(blueprint: Dict[str, Any], output_file: str = "main-authentik-blueprint.yaml"):
    """Save the blueprint as a YAML file with proper !Find and !KeyOf tags"""
    
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
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Blueprint saved to: {output_file}")

def main():
    """Main function to generate blueprint from environment variables"""
    
    # Read configuration from environment
    app_name = os.getenv("AUTHENTIK_APP_NAME", "main-oidc-app")
    app_slug = os.getenv("AUTHENTIK_APP_SLUG", "main-oidc-app")
    provider_name = os.getenv("AUTHENTIK_PROVIDER_NAME", "main-oidc-provider")
    
    # Read redirect URIs from .env file
    redirect_uris_env = os.getenv("AUTHENTIK_REDIRECT_URIS", "")
    if redirect_uris_env:
        redirect_uris = [uri.strip() for uri in redirect_uris_env.split(",")]
    else:
        redirect_uris = [
            "https://your-app-url.com/auth/callback",
            "https://your-app-url.com/auth/login"
        ]
        print("⚠️  No AUTHENTIK_REDIRECT_URIS found in .env, using defaults")
    
    logout_uri = os.getenv("AUTHENTIK_LOGOUT_URI", redirect_uris[-1] if redirect_uris else "")
    output_file = os.getenv("AUTHENTIK_OUTPUT_FILE", "main-authentik-blueprint.yaml")
    
    print("🚀 Generating Main Authentik Blueprint...")
    print(f"📋 App Name: {app_name}")
    print(f"📋 Provider: {provider_name}")
    print(f"🔗 Redirect URIs: {len(redirect_uris)} configured")
    print(f"🔗 Logout URI: {logout_uri}")
    print("")
    
    # Generate the blueprint
    blueprint = generate_blueprint(
        app_name=app_name,
        app_slug=app_slug,
        provider_name=provider_name,
        redirect_uris=redirect_uris,
        logout_uri=logout_uri
    )
    
    # Save the blueprint
    save_blueprint_yaml(blueprint, output_file)
    
    # Print summary
    print("\n📊 Blueprint Summary:")
    
    # Find the provider entry
    provider_entry = find_provider_entry(blueprint)
    if provider_entry:
        attrs = provider_entry.get("attrs", {})
        print(f"  ✅ Client ID: {attrs.get('client_id', 'N/A')}")
        print(f"  ✅ Client Secret: {attrs.get('client_secret', 'N/A')}")
        print(f"  ✅ Redirect URIs: {len(attrs.get('redirect_uris', []))}")
        print(f"  ✅ Logout URI: {attrs.get('logout_uri', 'N/A')}")
        print(f"  ✅ Backchannel Logout: {attrs.get('backchannel_logout_enabled', False)}")
    else:
        print("  ⚠️  No provider found in blueprint")
    
    print("\n📋 Components included:")
    print("  ✅ Recovery Flow (recovery-flow)")
    print("    - recovery-authentication-identification (Identification Stage - simple email lookup)")
    print("    - recovery-email (Email Stage)")
    print("    - default-password-change-prompt (Prompt Stage)")
    print("    - default-password-change-write (User Write Stage)")
    print("  ✅ Recovery Flow attached to default-authentication-identification")
    print("  ✅ Federated JIT Enrollment Flow (federated-jit-enrollment)")
    print("    - create-jit-user (User Write Stage)")
    print("    - default-authentication-login (User Login Stage)")
    print("  ✅ OAuth Source Property Mapping: federated-oidc-mapping")
    print("  ✅ Scope Mappings:")
    print("    - organizationId (returns 'orgId')")
    print("    - signerServer")
    print("    - walletId")
    print("    - federated_identity (returns 'upstream_idp')")
    print("  ✅ app-auth-flow")
    print("  ✅ app-invalidation-flow with default-invalidation-logout + redirect-logout-stage")
    print("  ✅ save-user-attributes Policy")
    print("  ✅ redirect-logout-stage")
    print("  ✅ orgId Prompt")
    print("  ✅ OAuth2 Provider with logout_uri")
    print("  ✅ Application")
    print(f"\n✅ Done! You can now import this blueprint in authentik.")
    print(f"📁 File: {output_file}")

if __name__ == "__main__":
    main()