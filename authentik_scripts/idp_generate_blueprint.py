#!/usr/bin/env python3
"""
Authentik Blueprint Generator
Generates a complete blueprint YAML file for IDP authentik with custom configurations
Includes: enrollment invitation flow, custom policies, mappings, stages, provider, and application
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
    app_name: str = "vm1-federated-app",
    app_slug: str = "vm1-federated-app",
    provider_name: str = "vm1-federated-provider",
    redirect_uris: List[str] = None,
    logout_uri: str = "",
    custom_scopes: List[str] = None
) -> Dict[str, Any]:
    """
    Generate the complete blueprint structure
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
        custom_scopes = ["organizationId", "signerServer", "walletId"]
    
    # Generate random credentials
    client_id = generate_random_client_id()
    client_secret = generate_random_client_secret()
    
    # Define the blueprint structure
    blueprint = {
        "version": 1,
        "metadata": {
            "name": f"Custom authentik Configuration - {app_name}",
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
    
    # Flow: app-auth-flow
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
    
    # Flow: app-invalidation-flow
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
    
    # Flow: enrollment-invitation
    entries.append({
        "model": "authentik_flows.flow",
        "identifiers": {"slug": "enrollment-invitation"},
        "attrs": {
            "name": "enrollment-invitation",
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
    
    # Stage: enrollment-invitation-write
    entries.append({
        "model": "authentik_stages_user_write.userwritestage",
        "identifiers": {"name": "enrollment-invitation-write"},
        "attrs": {
            "create_users_as_inactive": False,
            "create_users_group": None,
            "user_creation_mode": "create_when_required",
            "user_path_template": "",
            "user_type": "internal"
        },
        "state": "present"
    })
    
    # Stage: enrollment-invitation (invitation stage)
    entries.append({
        "model": "authentik_stages_invitation.invitationstage",
        "identifiers": {"name": "enrollment-invitation"},
        "attrs": {
            "continue_flow_without_invitation": False
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
    # 4. CUSTOM PROMPT STAGE
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
    # 5. CUSTOM PROPERTY MAPPINGS (Scope Mappings)
    # ================================================================
    
    # organizationId scope - returns "orgId" in the JWT token
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
    
    # signerServer scope - returns "signerServer" in the JWT token
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
    
    # walletId scope - returns "walletId" in the JWT token
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
    
    # ================================================================
    # 6. CUSTOM POLICY (save-user-attributes)
    # ================================================================
    
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
    # 7. FLOW STAGE BINDINGS FOR enrollment-invitation FLOW
    # ================================================================
    
    # Binding 1: Invitation stage (order: 10)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 10,
            "stage": "!FIND_MARKER:[authentik_stages_invitation.invitationstage, [name, enrollment-invitation]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # Binding 2: Prompt stage (order: 20)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 20,
            "stage": "!FIND_MARKER:[authentik_stages_prompt.promptstage, [name, default-source-enrollment-prompt]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # Binding 3: User write stage (order: 30)
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "identifiers": {
            "order": 30,
            "stage": "!FIND_MARKER:[authentik_stages_user_write.userwritestage, [name, enrollment-invitation-write]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, enrollment-invitation]]"
        },
        "attrs": {
            "evaluate_on_plan": False,
            "invalid_response_action": "retry",
            "policy_engine_mode": "any",
            "re_evaluate_policies": True
        },
        "state": "present"
    })
    
    # Binding 4: Redirect stage (order: 40) - This has the ID for !KeyOf reference
    entries.append({
        "model": "authentik_flows.flowstagebinding",
        "id": "local-flow-binding",
        "identifiers": {
            "order": 40,
            "stage": "!FIND_MARKER:[authentik_stages_redirect.redirectstage, [name, redirect-logout-stage]]",
            "target": "!FIND_MARKER:[authentik_flows.flow, [slug, enrollment-invitation]]"
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
    # 8. POLICY BINDING (Attach save-user-attributes to the redirect stage)
    # ================================================================
    
    entries.append({
        "model": "authentik_policies.policybinding",
        "identifiers": {
            "order": 0,
            "policy": "!FIND_MARKER:[authentik_policies_expression.expressionpolicy, [name, save-user-attributes]]",
            "target": "!KEYOF_MARKER:local-flow-binding"
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
    # 9. FLOW STAGE BINDINGS FOR app-invalidation-flow
    # ================================================================
    
    # Binding 1: default-invalidation-logout stage (order: 10)
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
    
    # Binding 2: redirect-logout-stage (order: 20)
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
    # 10. CUSTOM OAUTH2 PROVIDER
    # ================================================================
    
    # Build property mappings list
    property_mappings = []
    for scope_name in ["organizationId", "signerServer", "walletId"]:
        property_mappings.append(f"!FIND_MARKER:[authentik_providers_oauth2.scopemapping, [scope_name, {scope_name}]]")
    
    # Add default scopes
    default_scopes = ["openid", "email", "profile", "offline_access"]
    for scope in default_scopes:
        property_mappings.append(f"!FIND_MARKER:[authentik_providers_oauth2.scopemapping, [scope_name, {scope}]]")
    
    # Generate redirect URIs
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
    # 11. CUSTOM APPLICATION
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
    
    # Store metadata for summary
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

def save_blueprint_yaml(blueprint: Dict[str, Any], output_file: str = "authentik-blueprint.yaml"):
    """Save the blueprint as a YAML file with proper !Find and !KeyOf tags"""
    
    # Remove metadata before saving
    blueprint_copy = blueprint.copy()
    blueprint_copy.pop("_metadata", None)
    
    # Use ruamel.yaml for better control
    yaml_obj = YAML()
    yaml_obj.indent(mapping=2, sequence=4, offset=2)
    yaml_obj.preserve_quotes = True
    
    # Write the blueprint as YAML
    with open(output_file, 'w') as f:
        yaml_obj.dump(blueprint_copy, f)
    
    # Post-process the file to replace markers with proper tags
    with open(output_file, 'r') as f:
        content = f.read()
    
    import re
    
    # Replace !FIND_MARKER with !Find
    content = re.sub(r'!FIND_MARKER:', '!Find ', content)
    
    # Replace !KEYOF_MARKER with !KeyOf
    content = re.sub(r'!KEYOF_MARKER:', '!KeyOf ', content)
    
    # Remove quotes around !Find tags
    content = re.sub(r'"!Find\s+', '!Find ', content)
    content = re.sub(r'!Find\s+"', '!Find ', content)
    content = re.sub(r'!Find\s+\'([^\']+)\'', r'!Find \1', content)
    
    # Remove quotes around !KeyOf tags
    content = re.sub(r'"!KeyOf\s+', '!KeyOf ', content)
    content = re.sub(r'!KeyOf\s+"', '!KeyOf ', content)
    content = re.sub(r'!KeyOf\s+\'([^\']+)\'', r'!KeyOf \1', content)
    
    # Fix any remaining quoted tags
    def fix_tags(match):
        return f'{match.group(1)} {match.group(2)}'
    
    content = re.sub(r'"(!Find)\s+([^"]+)"', fix_tags, content)
    content = re.sub(r"'(!Find)\s+([^']+)'", fix_tags, content)
    content = re.sub(r'"(!KeyOf)\s+([^"]+)"', fix_tags, content)
    content = re.sub(r"'(!KeyOf)\s+([^']+)'", fix_tags, content)
    
    # Fix nested !Find tags
    content = re.sub(r'!Find\s+!Find', '!Find', content)
    
    # Fix URL formatting issues
    content = re.sub(r'url:\s+\n\s+', 'url: ', content)
    content = re.sub(r'target_static:\s+\n\s+', 'target_static: ', content)
    content = re.sub(r'logout_uri:\s+\n\s+', 'logout_uri: ', content)
    
    # Fix create_users_group: None to create_users_group: null
    content = re.sub(r'create_users_group:\s+None', 'create_users_group:', content)
    
    # Fix group: None to group:
    content = re.sub(r'group:\s+None', 'group:', content)
    
    # Fix user: None to user:
    content = re.sub(r'user:\s+None', 'user:', content)
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Blueprint saved to: {output_file}")

def main():
    """Main function to generate blueprint from environment variables"""
    
    # Read configuration from environment
    app_name = os.getenv("AUTHENTIK_APP_NAME", "my-vm1-federated-app")
    app_slug = os.getenv("AUTHENTIK_APP_SLUG", "vm1-federated-app")
    provider_name = os.getenv("AUTHENTIK_PROVIDER_NAME", "vm1-federated-provider")
    
    # Read redirect URIs from .env file
    redirect_uris_env = os.getenv("AUTHENTIK_REDIRECT_URIS", "")
    if redirect_uris_env:
        redirect_uris = [uri.strip() for uri in redirect_uris_env.split(",")]
    else:
        redirect_uris = [
            "https://ocean-node-vm2.oceanenterprise.io:8443/source/oauth/callback/vm1-partner-source/",
            "https://market-git-feat-stage-ocean-enterprise.vercel.app/auth/login",
            "https://market-git-feat-stage-ocean-enterprise.vercel.app/auth/callback/logout"
        ]
        print("⚠️  No AUTHENTIK_REDIRECT_URIS found in .env, using defaults")
    
    logout_uri = os.getenv("AUTHENTIK_LOGOUT_URI", redirect_uris[-1] if redirect_uris else "")
    output_file = os.getenv("AUTHENTIK_OUTPUT_FILE", "authentik-blueprint.yaml")
    
    print("🚀 Generating Authentik Blueprint...")
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
    print("  ✅ enrollment-invitation Flow")
    print("  ✅ app-auth-flow")
    print("  ✅ app-invalidation-flow with default-invalidation-logout + redirect-logout-stage")
    print("  ✅ save-user-attributes Policy")
    print("  ✅ redirect-logout-stage")
    print("  ✅ enrollment-invitation-write")
    print("  ✅ enrollment-invitation (invitation stage)")
    print("  ✅ orgId Prompt")
    print("  ✅ All Flow Stage Bindings")
    print("  ✅ Policy Binding with !KeyOf")
    print("  ✅ OAuth2 Provider with logout_uri")
    print("  ✅ Application")
    print(f"\n✅ Done! You can now import this blueprint in authentik.")
    print(f"📁 File: {output_file}")

if __name__ == "__main__":
    main()