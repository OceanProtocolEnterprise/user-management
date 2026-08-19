#!/usr/bin/env python3

"""
Create or update an OAuth/OIDC Federation Source in Authentik.

Append participant redirect URIs to an existing
central OAuth/OIDC provider without modifying its other settings.
"""

import os
import sys
import json
import argparse
from pathlib import Path

import requests


if "/" not in sys.path:
    sys.path.insert(0, "/")


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "authentik.root.settings",
)


try:
    import django

    django.setup()

except Exception as exc:
    print(
        f"ERROR: Failed to initialize Django/AuthentiK: "
        f"{type(exc).__name__}: {exc}"
    )
    sys.exit(1)


from authentik.sources.oauth.models import (
    OAuthSource,
    OAuthSourcePropertyMapping,
)

from authentik.flows.models import Flow

from authentik.stages.identification.models import (
    IdentificationStage,
)

from authentik.providers.oauth2.models import (
    OAuth2Provider,
    RedirectURI,
    RedirectURIMatchingMode,
    RedirectURIType,
)


def fetch_oidc_discovery(well_known_url: str) -> dict:
    print()
    print("==========================================")
    print(" Fetching OIDC Discovery")
    print("==========================================")

    print(f"Well-Known URL: {well_known_url}")

    try:
        response = requests.get(
            well_known_url,
            timeout=15,
            verify=False,
        )
    except requests.RequestException as exc:
        print(
            f"ERROR: Failed to fetch OIDC discovery document: {exc}"
        )
        sys.exit(1)

    if response.status_code != 200:
        print(
            f"ERROR: OIDC discovery returned HTTP "
            f"{response.status_code}"
        )
        sys.exit(1)

    try:
        discovery = response.json()
    except ValueError as exc:
        print(
            f"ERROR: OIDC discovery response is not valid JSON: {exc}"
        )
        sys.exit(1)

    required_fields = [
        "authorization_endpoint",
        "token_endpoint",
        "jwks_uri",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not discovery.get(field)
    ]

    if missing_fields:
        print(
            "ERROR: OIDC discovery document is missing required fields:"
        )

        for field in missing_fields:
            print(f"  - {field}")

        sys.exit(1)

    print()
    print("OIDC discovery endpoints:")

    print(
        f"  Authorization URL : "
        f"{discovery.get('authorization_endpoint')}"
    )

    print(
        f"  Access Token URL  : "
        f"{discovery.get('token_endpoint')}"
    )

    print(
        f"  Profile URL       : "
        f"{discovery.get('userinfo_endpoint') or '(not provided)'}"
    )

    print(
        f"  OIDC JWKS URL     : "
        f"{discovery.get('jwks_uri')}"
    )

    return discovery


def fetch_oidc_jwks(jwks_url: str) -> dict:
    print()
    print(
        f"Fetching OIDC JWKS: {jwks_url}"
    )

    try:
        response = requests.get(
            jwks_url,
            timeout=15,
            verify=False,
        )
    except requests.RequestException as exc:
        print(
            f"WARNING: Failed to fetch OIDC JWKS: {exc}"
        )
        return {}

    if response.status_code != 200:
        print(
            f"WARNING: OIDC JWKS returned HTTP "
            f"{response.status_code}"
        )
        return {}

    try:
        jwks = response.json()
    except ValueError:
        print(
            "WARNING: OIDC JWKS response is not valid JSON."
        )
        return {}

    if not isinstance(jwks, dict):
        print(
            "WARNING: OIDC JWKS response is not a JSON object."
        )
        return {}

    if "keys" not in jwks:
        print(
            "WARNING: OIDC JWKS response does not contain 'keys'."
        )
        return {}

    print(
        f"✓ OIDC JWKS loaded: {len(jwks['keys'])} key(s)"
    )

    return jwks


def append_redirect_uris(
    provider_name: str,
    participant_redirect_uris: list[str],
) -> None:

    print()
    print("==========================================")
    print(" Updating Central OIDC Provider")
    print("==========================================")

    print(
        f"Provider name: {provider_name}"
    )

    print(
        "Redirect URIs to append:"
    )

    for uri in participant_redirect_uris:
        print(f"  + {uri}")

    print()

    if not participant_redirect_uris:
        print(
            "No participant redirect URIs supplied."
        )
        return

    if not isinstance(
        participant_redirect_uris,
        list,
    ):
        print(
            "ERROR: participant_redirect_uris must be a JSON array."
        )
        sys.exit(1)

    participant_redirect_uris = [
        uri.strip()
        for uri in participant_redirect_uris
        if isinstance(uri, str) and uri.strip()
    ]

    if not participant_redirect_uris:
        print(
            "No valid participant redirect URIs supplied."
        )
        return

    try:
        provider = OAuth2Provider.objects.get(
            name=provider_name
        )

    except OAuth2Provider.DoesNotExist:

        print()
        print(
            f"ERROR: OAuth2/OIDC provider "
            f"'{provider_name}' was not found."
        )

        print()
        print(
            "Available OAuth2/OIDC providers:"
        )

        for existing_provider in (
            OAuth2Provider.objects.all()
            .order_by("name")
        ):
            print(
                f"  - {existing_provider.name}"
            )

        sys.exit(1)

    except OAuth2Provider.MultipleObjectsReturned:

        print()
        print(
            f"ERROR: Multiple OAuth2/OIDC providers "
            f"with name '{provider_name}' were found."
        )

        print(
            "Provider name must uniquely identify the provider."
        )

        sys.exit(1)

    existing_redirect_uris = list(
        provider.redirect_uris
    )

    print(
        f"Existing redirect URI count: "
        f"{len(existing_redirect_uris)}"
    )

    for redirect in existing_redirect_uris:
        print(
            f"  Existing: "
            f"{redirect.url} "
            f"[{redirect.redirect_uri_type.value}]"
        )

    existing_authorization_urls = {
        redirect.url
        for redirect in existing_redirect_uris
        if redirect.redirect_uri_type
        == RedirectURIType.AUTHORIZATION
    }

    added_count = 0
    skipped_count = 0

    for uri in participant_redirect_uris:

        if uri in existing_authorization_urls:
            print(
                f"  ✓ Already exists: {uri}"
            )
            skipped_count += 1
            continue

        new_redirect = RedirectURI(
            matching_mode=RedirectURIMatchingMode.STRICT,
            url=uri,
            redirect_uri_type=RedirectURIType.AUTHORIZATION,
        )

        existing_redirect_uris.append(
            new_redirect
        )

        existing_authorization_urls.add(
            uri
        )

        print(
            f"  + Adding: {uri}"
        )

        added_count += 1

    if added_count == 0:

        print()
        print(
            "✓ No new redirect URIs needed."
        )

        print(
            "✓ Existing provider was not modified."
        )

        return

    provider.redirect_uris = (
        existing_redirect_uris
    )

    provider.save(
        update_fields=[
            "_redirect_uris"
        ]
    )

    provider.refresh_from_db()

    updated_redirect_uris = list(
        provider.redirect_uris
    )

    print()
    print(
        "=========================================="
    )

    print(
        " Central OIDC Provider Updated"
    )

    print(
        "=========================================="
    )

    print(
        f"Provider              : {provider.name}"
    )

    print(
        f"Added redirect URIs   : {added_count}"
    )

    print(
        f"Already existed       : {skipped_count}"
    )

    print(
        f"Total redirect URIs   : "
        f"{len(updated_redirect_uris)}"
    )

    print()
    print(
        "Current authorization redirect URIs:"
    )

    for redirect in updated_redirect_uris:

        if (
            redirect.redirect_uri_type
            == RedirectURIType.AUTHORIZATION
        ):

            print(
                f"  - {redirect.url}"
            )

    print()
    print(
        "✓ Only redirect URIs were updated."
    )

    print(
        "✓ Other provider settings were not changed."
    )

    print()


def add_source_to_authentication_identification(
    source: OAuthSource,
) -> None:

    flow_slug = "oe-authentication-flow"

    identification_stage_name = (
        "oe-authentication-identification"
    )

    print()
    print("==========================================")
    print(" Updating Authentication Identification")
    print("==========================================")

    print(
        f"Flow       : {flow_slug}"
    )

    print(
        f"Stage      : {identification_stage_name}"
    )

    print(
        f"Source     : {source.name}"
    )

    print()

    try:

        authentication_flow = Flow.objects.get(
            slug=flow_slug
        )

    except Flow.DoesNotExist:

        print(
            f"ERROR: Authentication flow "
            f"'{flow_slug}' not found."
        )

        sys.exit(1)

    except Flow.MultipleObjectsReturned:

        print(
            f"ERROR: Multiple flows with slug "
            f"'{flow_slug}' were found."
        )

        sys.exit(1)

    print(
        f"✓ Authentication flow found: "
        f"{authentication_flow.slug}"
    )

    try:

        identification_stage = (
            IdentificationStage.objects.get(
                name=identification_stage_name
            )
        )

    except IdentificationStage.DoesNotExist:

        print(
            f"ERROR: Identification Stage "
            f"'{identification_stage_name}' not found."
        )

        sys.exit(1)

    except IdentificationStage.MultipleObjectsReturned:

        print(
            f"ERROR: Multiple Identification Stages "
            f"with name '{identification_stage_name}' "
            f"were found."
        )

        sys.exit(1)

    print(
        f"✓ Identification Stage found: "
        f"{identification_stage.name}"
    )

    if not authentication_flow.stages.filter(
        pk=identification_stage.pk
    ).exists():

        print()
        print(
            f"ERROR: Identification Stage "
            f"'{identification_stage_name}' "
            f"is not bound to flow "
            f"'{flow_slug}'."
        )

        sys.exit(1)

    print(
        f"✓ Identification Stage belongs to "
        f"'{flow_slug}'"
    )

    existing_sources = list(
        identification_stage.sources.all()
    )

    print()
    print(
        "Existing Identification Stage sources:"
    )

    if existing_sources:

        for existing_source in existing_sources:
            print(
                f"  - {existing_source.name}"
            )

    else:

        print(
            "  (none)"
        )

    source_already_exists = (
        identification_stage.sources.filter(
            pk=source.pk
        ).exists()
    )

    if source_already_exists:

        print()
        print(
            f"✓ Source '{source.name}' is already "
            f"configured on the Identification Stage."
        )

    else:

        identification_stage.sources.add(
            source
        )

        print()
        print(
            f"✓ Source '{source.name}' added to "
            f"Identification Stage."
        )

    if not identification_stage.show_source_labels:

        identification_stage.show_source_labels = True

        identification_stage.save(
            update_fields=[
                "show_source_labels"
            ]
        )

        print(
            "✓ 'Show source labels' enabled."
        )

    else:

        print(
            "✓ 'Show source labels' was already enabled."
        )

    identification_stage.refresh_from_db()

    updated_sources = list(
        identification_stage.sources.all()
    )

    print()
    print(
        "=========================================="
    )

    print(
        " Authentication Identification Updated"
    )

    print(
        "=========================================="
    )

    print(
        f"Flow                 : "
        f"{authentication_flow.slug}"
    )

    print(
        f"Identification Stage : "
        f"{identification_stage.name}"
    )

    print(
        f"Show source labels    : "
        f"{identification_stage.show_source_labels}"
    )

    print(
        "Configured sources:"
    )

    for configured_source in updated_sources:

        print(
            f"  - {configured_source.name}"
        )

    print()
    print(
        "✓ Existing sources were preserved."
    )

    print(
        "✓ Federation source was added."
    )

    print(
        "✓ Source labels are enabled."
    )

    print(
        "✓ No other Identification Stage settings "
        "were modified."
    )

    print()


def configure_oidc_discovery(
    source: OAuthSource,
    well_known_url: str,
) -> None:

    discovery = fetch_oidc_discovery(
        well_known_url
    )

    authorization_url = discovery.get(
        "authorization_endpoint"
    )

    access_token_url = discovery.get(
        "token_endpoint"
    )

    profile_url = discovery.get(
        "userinfo_endpoint"
    )

    jwks_url = discovery.get(
        "jwks_uri"
    )

    source.oidc_well_known_url = (
        well_known_url
    )

    if authorization_url:
        source.authorization_url = (
            authorization_url
        )

    if access_token_url:
        source.access_token_url = (
            access_token_url
        )

    if profile_url:
        source.profile_url = (
            profile_url
        )

    if jwks_url:
        source.oidc_jwks_url = (
            jwks_url
        )

        jwks = fetch_oidc_jwks(
            jwks_url
        )

        if jwks:
            source.oidc_jwks = jwks

    source.save()

    source.refresh_from_db()

    print()
    print(
        "=========================================="
    )

    print(
        " OIDC Source URLs Configured"
    )

    print(
        "=========================================="
    )

    print(
        f"Well-Known URL     : "
        f"{source.oidc_well_known_url}"
    )

    print(
        f"Authorization URL  : "
        f"{source.authorization_url}"
    )

    print(
        f"Access Token URL   : "
        f"{source.access_token_url}"
    )

    print(
        f"Profile URL        : "
        f"{source.profile_url}"
    )

    print(
        f"OIDC JWKS URL      : "
        f"{source.oidc_jwks_url}"
    )

    if source.oidc_jwks:
        print(
            f"OIDC JWKS Keys     : "
            f"{len(source.oidc_jwks.get('keys', []))}"
        )
    else:
        print(
            "OIDC JWKS Keys     : 0"
        )

    print()


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Create/update Authentik OAuth federation source "
            "and append participant redirect URIs"
        )
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Participant configuration JSON",
    )

    parser.add_argument(
        "--auth-flow",
        default="default-source-authentication",
    )

    parser.add_argument(
        "--enrollment-flow",
        default="oe-central-federated-jit-enrollment",
    )

    parser.add_argument(
        "--property-mapping",
        default="oe-central-federated-oidc-mapping",
    )

    args = parser.parse_args()

    config_path = Path(args.config)

    if not config_path.exists():

        print(
            f"ERROR: Config file not found: {config_path}"
        )

        sys.exit(1)

    try:

        with config_path.open(
            "r",
            encoding="utf-8",
        ) as f:
            config = json.load(f)

    except json.JSONDecodeError as exc:

        print(
            f"ERROR: Invalid JSON configuration: {exc}"
        )

        sys.exit(1)

    app_slug = config.get(
        "authentik_app_slug"
    )

    client_id = config.get(
        "participant_idp_consumer_key"
    )

    client_secret = config.get(
        "participant_idp_consumer_secret"
    )

    well_known = config.get(
        "participant_idp_well_known_url"
    )

    central_provider_name = config.get(
        "central_idp_provider_name"
    )

    participant_redirect_uris = config.get(
        "participant_redirect_uris",
        []
    )

    required = {

        "authentik_app_slug":
            app_slug,

        "participant_idp_consumer_key":
            client_id,

        "participant_idp_consumer_secret":
            client_secret,

        "participant_idp_well_known_url":
            well_known,

        "central_idp_provider_name":
            central_provider_name,
    }

    missing = [

        key

        for key, value
        in required.items()

        if not value
    ]

    if missing:

        print(
            "ERROR: Missing required configuration:"
        )

        for key in missing:

            print(
                f"  - {key}"
            )

        sys.exit(1)

    print()
    print(
        "=========================================="
    )

    print(
        " Authentik Federation Source Setup"
    )

    print(
        "=========================================="
    )

    print(
        f"Source slug : {app_slug}"
    )

    print(
        f"Client ID   : {client_id}"
    )

    print(
        f"Well-Known  : {well_known}"
    )

    print(
        f"Central provider : {central_provider_name}"
    )

    print()

    try:

        auth_flow = Flow.objects.get(
            slug=args.auth_flow
        )

        print(
            f"✓ Authentication flow found: "
            f"{auth_flow.slug}"
        )

    except Flow.DoesNotExist:

        print(
            f"ERROR: Authentication flow "
            f"'{args.auth_flow}' not found"
        )

        sys.exit(1)

    try:

        enrollment_flow = Flow.objects.get(
            slug=args.enrollment_flow
        )

        print(
            f"✓ Enrollment flow found: "
            f"{enrollment_flow.slug}"
        )

    except Flow.DoesNotExist:

        print(
            f"ERROR: Enrollment flow "
            f"'{args.enrollment_flow}' not found"
        )

        sys.exit(1)

    try:

        property_mapping = (
            OAuthSourcePropertyMapping.objects.get(
                name=args.property_mapping
            )
        )

        print(
            f"✓ Property mapping found: "
            f"{property_mapping.name}"
        )

    except OAuthSourcePropertyMapping.DoesNotExist:

        print(
            f"ERROR: Property mapping "
            f"'{args.property_mapping}' not found"
        )

        sys.exit(1)

    scopes = (
        "openid "
        "profile "
        "email "
        "offline_access "
        "oe-central-federated_identity "
        "oe-organizationId "
        "oe-walletId "
        "oe-signerServer "
        "oe-wellKnownUrl"
    )

    print()
    print(
        "OAuth scopes:"
    )

    print(
        f"  {scopes}"
    )

    print()

    source, created = OAuthSource.objects.get_or_create(

        slug=app_slug,

        defaults={

            "name": app_slug,

            "slug": app_slug,

            "enabled": True,

            "provider_type": "openidconnect",

            "pkce": "none",

            "consumer_key": client_id,

            "consumer_secret": client_secret,

            "oidc_well_known_url": well_known,

            "additional_scopes": scopes,

            "authentication_flow": auth_flow,

            "enrollment_flow": enrollment_flow,

            "user_matching_mode": "identifier",

            "policy_engine_mode": "any",
        },
    )

    if not created:

        print(
            f"✓ Existing source found: {app_slug}"
        )

        source.name = app_slug

        source.enabled = True

        source.provider_type = "openidconnect"

        source.pkce = "none"

        source.consumer_key = client_id

        source.consumer_secret = client_secret

        source.oidc_well_known_url = well_known

        source.additional_scopes = scopes

        source.authentication_flow = auth_flow

        source.enrollment_flow = enrollment_flow

        source.user_matching_mode = "identifier"

        source.policy_engine_mode = "any"

        source.save()

        print(
            f"✓ Updated existing source: "
            f"{app_slug}"
        )

    else:

        print(
            f"✓ Created new source: "
            f"{app_slug}"
        )

    source.user_property_mappings.set(
        [property_mapping]
    )

    source.save()

    configure_oidc_discovery(
        source=source,
        well_known_url=well_known,
    )

    source.refresh_from_db()

    print()
    print(
        "=========================================="
    )

    print(
        " Federation Source Successfully Configured"
    )

    print(
        "=========================================="
    )

    print(
        f"Source             : {source.name}"
    )

    print(
        f"Slug               : {source.slug}"
    )

    print(
        f"Enabled            : {source.enabled}"
    )

    print(
        f"Provider type      : {source.provider_type}"
    )

    print(
        f"PKCE               : {source.pkce}"
    )

    print(
        f"Client ID          : {source.consumer_key}"
    )

    print(
        f"OIDC discovery     : "
        f"{source.oidc_well_known_url}"
    )

    print(
        f"Authorization URL  : "
        f"{source.authorization_url}"
    )

    print(
        f"Access Token URL   : "
        f"{source.access_token_url}"
    )

    print(
        f"Profile URL        : "
        f"{source.profile_url}"
    )

    print(
        f"OIDC JWKS URL      : "
        f"{source.oidc_jwks_url}"
    )

    print(
        f"Authentication     : "
        f"{source.authentication_flow.slug}"
    )

    print(
        f"Enrollment         : "
        f"{source.enrollment_flow.slug}"
    )

    print(
        f"User matching      : "
        f"{source.user_matching_mode}"
    )

    print(
        f"Policy engine      : "
        f"{source.policy_engine_mode}"
    )

    print(
        "Property mappings  : "
        + ", ".join(
            mapping.name
            for mapping
            in source.user_property_mappings.all()
        )
    )

    print(
        f"Scopes             : "
        f"{source.additional_scopes}"
    )

    print()
    print(
        "✓ Federation source is ready."
    )

    print()


    append_redirect_uris(
        provider_name=central_provider_name,
        participant_redirect_uris=participant_redirect_uris,
    )

    add_source_to_authentication_identification(
        source=source
    )


if __name__ == "__main__":
    main()