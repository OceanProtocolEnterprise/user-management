# Participant

The Participant module deploys the services required to operate an Ocean Enterprise Dataspace Participant environment.

The deployment includes identity management, wallet, signing, database, secret-management, and reverse-proxy services.

The Participant also integrates with the **Central Identity Provider (Central IdP)** provided by the Dataspace Operator.

---

## Included services

The Participant Docker Compose stack contains:

- **Authentik** — Identity Provider for the Participant
- **OpenBao** — Secret management
- **PostgreSQL** — Database services
- **Signer Server** — Blockchain transaction signing
- **Traefik** — Reverse proxy and TLS termination
- **Wallet API** — walt.id SSI Wallet API
- **Wallet UI** — walt.id SSI Wallet UI

---

## Directory structure

The initial Participant directory contains:

```text
participant/
├── authentik/
│   └── participant_blueprint.py
│
├── docker-compose/
│   ├── authentik/
│   │   ├── blueprints/
│   │   └── certs/
│   ├── openbao/
│   │   ├── certs/
│   │   └── secrets/
│   ├── postgres-init/
│   ├── signer-server/
│   │   └── certs/
│   ├── traefik/
│   │   ├── certs/
│   │   └── dynamic/
│   ├── wallet-api/
│   │   ├── config/
│   │   └── data/
│   └── wallet-ui/
│   │   
│   └── .env      
│
├── .env.config
├── participant_environment_configuration.py
├── participant-initial-setup.sh
└── requirements.txt
````

The service-specific `.env.*` files are generated during the setup process and are therefore not shown as initial files.

---

## Prerequisites

Before starting the deployment, make sure that:

* Docker is installed.
* Docker Compose is installed.
* Docker and Docker Compose are up to date.
* The initialization script can be executed on the target Unix-like operating system.
* Required blockchain RPC provider URLs are available.
* Required database passwords and secret values are available.
* The Marketplace URL is known.
* The Dataspace Operator has provided the required Central IdP configuration.

The initial setup scripts support Unix-like environments including:

* Fedora
* Alpine
* openSUSE
* CentOS

---

## Central Identity Provider prerequisite

The **Dataspace Operator should provide the Participant with the configuration details of the Central Identity Provider** before Participant initialization.

The Participant requires the following Central IdP information:

* Central IdP Well-Known URL
* Central IdP client ID
* Central IdP client secret
* Central IdP provider name

These values are configured in:

```text
participant/.env.config
```

Example:

```dotenv
CENTRAL_IDP_WELL_KNOWN_URL=https://<central-idp-host>:9443/application/o/<application>/.well-known/openid-configuration
CENTRAL_IDP_CLIENT_ID=<central-idp-client-id>
CENTRAL_IDP_CLIENT_SECRET=<central-idp-client-secret>
CENTRAL_IDP_PROVIDER_NAME=<central-idp-provider-name>
```

The Central IdP must be accessible when the Participant initialization is performed.

---

## Configuration

The Participant deployment uses two main configuration inputs:

* `.env.config`
* `docker-compose/.env`

### `.env.config`

The file:

```text
participant/.env.config
```

contains the deployment-specific configuration.

The main configuration areas are:

* Ocean Enterprise Marketplace
* Central Identity Provider
* Signer Server
* Wallet UI
* Wallet API
* PostgreSQL
* Participant Identity Provider
* Authentik
* SMTP

---

### Marketplace

Configure the Marketplace URL:

```dotenv
MARKETPLACE_URL=https://market.example.com/
```

---

### Central Identity Provider

The Participant consumes the Central IdP configuration provided by the Dataspace Operator.

Configure:

```dotenv
CENTRAL_IDP_WELL_KNOWN_URL=<central-idp-well-known-url>
CENTRAL_IDP_CLIENT_ID=<central-idp-client-id>
CENTRAL_IDP_CLIENT_SECRET=<central-idp-client-secret>
CENTRAL_IDP_PROVIDER_NAME=<central-idp-provider-name>
```

These values must correspond to the Central IdP configuration provided by the Dataspace Operator.

---

### Signer Server

Configure the blockchain RPC providers in `NODE_URI_MAP`.

Example:

```dotenv
NODE_URI_MAP='[{"11155111":{"key":"<your-sepolia-rpc-provider-url>","multiplier":3}},{"11155420":{"key":"<your-optimism-sepolia-rpc-provider-url>","multiplier":2}},{"10":{"key":"<your-optimism-rpc-provider-url>","multiplier":1.5}},{"1":{"key":"<your-mainnet-rpc-provider-url>","multiplier":2}}]'
```

Only include the blockchains required by the deployment.

---

### Wallet UI

Configure:

```dotenv
WALLET_UI_URL=https://waltid-ui.oceanenterprise.io
NUXT_ADMIN_USER_GROUP_NAME=""
```

`NUXT_ADMIN_USER_GROUP_NAME` should contain the Authentik administrator group used to access the Wallet UI.

#### Important Notes
For wallet UI on Participant side granting access, user group from Participant Identity Provider Authentik must not have super user priviledges.

---

### Wallet API

Configure:

```dotenv
WALLET_API_URL=https://waltid-api.oceanenterprise.io
DB_PASSWORD='<your-wallet-api-database-password>'
```

---

### PostgreSQL

Configure:

```dotenv
POSTGRES_PASSWORD='<your-root-user-database-password>'
```

---

### Participant Identity Provider

Configure the Participant Identity Provider hostname and ports:

```dotenv
PARTICIPANT_IDP_HOSTNAME=<participant-idp-hostname>
PARTICIPANT_IDP_PORT_HTTP=9000
PARTICIPANT_IDP_PORT_HTTPS=9443
```

Configure the Authentik application and provider:

```dotenv
AUTHENTIK_APP_SLUG=<participant-authentik-app-slug>
AUTHENTIK_PROVIDER_NAME=<participant-authentik-provider-name>
```

Configure the Authentik database password and secret key:

```dotenv
AUTHENTIK_POSTGRESQL__PASSWORD='<authentik-database-password>'
AUTHENTIK_SECRET_KEY='<authentik-secret-key>'
```

---

### SMTP

SMTP configuration is optional.

If outbound email is required, configure:

```dotenv
AUTHENTIK_EMAIL__FROM=<support-email>
AUTHENTIK_EMAIL__USERNAME=<smtp-username>
AUTHENTIK_EMAIL__PASSWORD=<smtp-password>
AUTHENTIK_EMAIL__HOST=<smtp-host>
AUTHENTIK_EMAIL__PORT=<smtp-port>
```

---

### Authentik blueprint output

The generated Participant Authentik blueprint is configured through:

```dotenv
AUTHENTIK_OUTPUT_FILE=participant-authentik-blueprint.yaml
```

---

## `docker-compose/.env`

The file:

```text
participant/docker-compose/.env
```

contains the Docker image tags/versions and common Docker Compose values.

The current recommended image tags are:

```dotenv
WALLET_API_TAG=gaiax-0.1.1-OE
DEV_WALLET_TAG=gaiax-0.1.5-OE
AUTHENTIK_TAG=2026.5.5
SIGNER_SERVER_TAG=v0.5.3
```

Common values include:

```dotenv
SERVICE_HOST=localhost
WALLET_BACKEND_PORT=7001
NITRO_PORT=7104
PORT=7104
HOST=0.0.0.0
NITRO_HOST=0.0.0.0

WALLET_API_HOST=waltid-api.oceanenterprise.io
WALLET_UI_HOST=waltid-ui.oceanenterprise.io
```

The file is generated by:

```text
participant_environment_configuration.py
```

Do not normally edit it manually. If a different image version is intentionally required, update the image tag configuration according to the deployment process and regenerate the environment.

---

## Generated service-specific `.env` files

The environment configuration process generates the `.env.*` files required by the individual services.

Examples include:

```text
docker-compose/authentik/.env.authentik
docker-compose/openbao/.env.openbao
docker-compose/signer-server/.env.signer-server
docker-compose/traefik/.env.traefik
docker-compose/wallet-api/.env.wallet-api
docker-compose/wallet-ui/.env.wallet-ui
```

These files are generated from `.env.config` and should not normally be configured manually.

---

# Deployment

The Participant deployment follows these steps.

## 1. Obtain Central IdP configuration

Before initializing the Participant, obtain the Central IdP configuration details from the Dataspace Operator.

The required values are:

```text
CENTRAL_IDP_WELL_KNOWN_URL
CENTRAL_IDP_CLIENT_ID
CENTRAL_IDP_CLIENT_SECRET
CENTRAL_IDP_PROVIDER_NAME
```

---

## 2. Configure `.env.config`

From the Participant directory, edit:

```text
.env.config
```

Configure the required values, including:

* Marketplace URL
* Central IdP configuration
* Blockchain RPC providers
* Wallet configuration
* Database passwords
* Participant Identity Provider configuration
* Authentik configuration
* SMTP configuration, if required

---

## 3. Review image tags

Review:

```text
docker-compose/.env
```

The environment generation process creates this file with the recommended image tags.

Update image tags only if a different version is intentionally required.

---

## 4. Run the initial setup

Make the setup script executable:

```bash
chmod +x participant-initial-setup.sh
```

Run the setup:

```bash
./participant-initial-setup.sh
```

The setup process generates the environment configuration required by the Docker Compose services and prepares the Participant deployment.

---

## 5. Start the services

Change to the Docker Compose directory:

```bash
cd docker-compose
```

Start the services:

```bash
docker compose up -d
```

---

## 6. Verify the deployment

Check the running containers:

```bash
docker compose ps
```

Review logs when troubleshooting:

```bash
docker compose logs
```

Individual service logs can be inspected with:

```bash
docker compose logs <service-name>
```

---

# Participant onboarding information

After configuring the Participant Identity Provider, the Participant must provide the Dataspace Operator with the information required to configure federation/social login.

The Participant generates a JSON configuration containing its Identity Provider details.

The JSON configuration is then provided to the Dataspace Operator.

The Dataspace Operator uses this information to configure the Participant federation/social-login source in the Central IdP.

---

## JSON configuration

The JSON file contains the Participant Identity Provider configuration required by the Dataspace Operator.

An example structure is:

```json
{
  "participant_idp_well_known_url": "https://participant.example.com:9443/application/o/<participant-app-slug>/.well-known/openid-configuration",
  "participant_idp_consumer_key": "<participant-client-id>",
  "participant_idp_consumer_secret": "<participant-client-secret>",
  "authentik_app_slug": "<participant-app-slug>",
  "participant_redirect_uris": [
    "https://waltid-ui.example.com/auth/callback",
    "https://waltid-ui.example.com/auth/login",
    "https://waltid-ui.example.com"
  ],
  "central_idp_provider_name": "<central-idp-provider-name>"
}
```


The following information is especially important:

* `participant_idp_well_known_url` — Participant Identity Provider OpenID Connect Well-Known URL.
* `participant_idp_consumer_key` — Participant Identity Provider client/consumer identifier.
* `participant_idp_consumer_secret` — Participant Identity Provider client/consumer secret.
* `authentik_app_slug` — Participant Authentik application slug.
* `participant_redirect_uris` — Redirect URIs used by the Participant application.
* `central_idp_provider_name` — Central IdP provider name configured for the Marketplace.

The consumer secret is sensitive and must be transferred securely.


## Stopping the deployment

From the docker-compose directory:

```bash
cd docker-compose
```

Stop the running services:

```bash
docker compose down
```

---

## Security considerations

The following values are sensitive and must not be committed with real production values:

* `CENTRAL_IDP_CLIENT_SECRET`
* `DB_PASSWORD`
* `POSTGRES_PASSWORD`
* `AUTHENTIK_POSTGRESQL__PASSWORD`
* `AUTHENTIK_SECRET_KEY`
* `AUTHENTIK_EMAIL__PASSWORD`
* Blockchain RPC credentials where applicable
* `participant_idp_consumer_secret`

Use secure, deployment-specific values in `.env.config`.

Generated `.env.*` files and the Participant JSON configuration should also be treated as sensitive configuration.
