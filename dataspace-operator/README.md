# Dataspace Operator

The Dataspace Operator module deploys the services required to operate an Ocean Enterprise Dataspace Operator environment.

The deployment includes the identity, wallet, signing, database, secret-management, and reverse-proxy services required by the Dataspace Operator.

---

## Included services

The Dataspace Operator Docker Compose stack contains:

- **Authentik** — Identity Provider for the Dataspace Operator
- **OpenBao** — Secret management
- **PostgreSQL** — Database services
- **Signer Server** — Blockchain transaction signing
- **Traefik** — Reverse proxy and TLS termination
- **Wallet API** — walt.id SSI Wallet API
- **Wallet UI** — walt.id SSI Wallet UI

The Dataspace Operator also provides the **Central Identity Provider (Central IdP)** used by the Ocean Enterprise Marketplace and participating Dataspace Participants.

---

## Directory structure

The initial Dataspace Operator directory contains the deployment configuration and scripts:

```text
dataspace-operator/
├── authentik/
│   └── dataspace_operator_blueprint.py
│
├── docker-compose/
│   ├── authentik/
│   │   ├── blueprints/
│   │   ├── certs/
│   │   ├── participant-configs/
│   │   └── scripts/
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
├── dataspace_operator_environment_configuration.py
├── dataspace-operator-initial-setup.sh
└── requirements.txt
````

The `.env.*` files generated for individual services are not shown in the initial tree because they are created during the setup process.

---

## Prerequisites

Before starting the deployment, make sure that:

* Docker is installed.
* Docker Compose is installed.
* Docker and Docker Compose are up to date.
* The initialization script can be executed on the target Unix-like operating system.
* The required blockchain RPC provider URLs are available.
* Required database passwords and secret values are available.
* The Marketplace URL is known.
* The hostname and ports of the Central Identity Provider are known.
* If SMTP is required, the SMTP configuration is available.

The initial setup scripts support Unix-like environments including:

* Fedora
* Alpine
* openSUSE
* CentOS

---

## Configuration

The Dataspace Operator deployment uses two main configuration inputs:

* `.env.config`
* `docker-compose/.env`

### `.env.config`

The file:

```text
dataspace-operator/.env.config
```

contains the deployment-specific parameters.

It is the file that should be configured before running the environment generation script.

The main configuration areas are:

* Ocean Enterprise Marketplace
* Signer Server
* Wallet UI
* Wallet API
* PostgreSQL
* Central Identity Provider
* Authentik
* SMTP

### Marketplace

Configure the Marketplace URL:

```dotenv
MARKETPLACE_URL=https://market.example.com/
```

### Signer Server

Configure the blockchain RPC providers in `NODE_URI_MAP`.

Example:

```dotenv
NODE_URI_MAP='[{"11155111":{"key":"<your-sepolia-rpc-provider-url>","multiplier":3}},{"11155420":{"key":"<your-optimism-sepolia-rpc-provider-url>","multiplier":2}},{"10":{"key":"<your-optimism-rpc-provider-url>","multiplier":1.5}},{"1":{"key":"<your-mainnet-rpc-provider-url>","multiplier":2}}]'
```

Only include the blockchains required by the deployment.

### Wallet UI

Configure:

```dotenv
WALLET_UI_URL=https://waltid-ui.oceanenterprise.io
NUXT_ADMIN_USER_GROUP_NAME=""
```

`NUXT_ADMIN_USER_GROUP_NAME` should contain the Authentik administrator group used to access the Wallet UI.

### Wallet API

Configure:

```dotenv
WALLET_API_URL=https://waltid-api.oceanenterprise.io
DB_PASSWORD='<your-wallet-api-database-password>'
```

### PostgreSQL

Configure:

```dotenv
POSTGRES_PASSWORD='<your-root-user-database-password>'
```

### Central Identity Provider

Configure the Central IdP hostname and ports:

```dotenv
CENTRAL_IDP_HOSTNAME=<central-idp-hostname>
CENTRAL_IDP_PORT_HTTP=9000
CENTRAL_IDP_PORT_HTTPS=9443
```

Configure the Authentik application and provider:

```dotenv
AUTHENTIK_APP_SLUG=main-oidc-app
AUTHENTIK_PROVIDER_NAME=main-oidc-provider
```

Configure the Authentik database password and secret key:

```dotenv
AUTHENTIK_POSTGRESQL__PASSWORD='<authentik-database-password>'
AUTHENTIK_SECRET_KEY='<authentik-secret-key>'
```

### SMTP

SMTP configuration is optional.

If outbound email is required, configure the SMTP variables in `.env.config`:

```dotenv
AUTHENTIK_EMAIL__FROM=<support-email>
AUTHENTIK_EMAIL__USERNAME=<smtp-username>
AUTHENTIK_EMAIL__PASSWORD=<smtp-password>
AUTHENTIK_EMAIL__HOST=<smtp-host>
AUTHENTIK_EMAIL__PORT=<smtp-port>
```

### Authentik blueprint output

The generated Authentik blueprint is configured through:

```dotenv
AUTHENTIK_OUTPUT_FILE=dataspace-operator-authentik-blueprint.yaml
```

---

## `docker-compose/.env`

The file:

```text
dataspace-operator/docker-compose/.env
```

contains the Docker image tags/versions and common Docker Compose values.

The current recommended image tags are:

```dotenv
WALLET_API_TAG=gaiax-0.1.1-OE
DEV_WALLET_TAG=gaiax-0.1.5-OE
AUTHENTIK_TAG=2026.5.5
SIGNER_SERVER_TAG=v0.5.3
```

It also contains values such as:

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

This file is generated by:

```text
dataspace_operator_environment_configuration.py
```

Do not normally edit it manually. If image versions need to be changed, make the required configuration change according to the deployment process and regenerate the environment.

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

## Deployment

The Dataspace Operator deployment follows these steps.

### 1. Configure `.env.config`

From the Dataspace Operator directory, configure:

```text
.env.config
```

Set all required deployment-specific values, including:

* Marketplace URL
* Blockchain RPC providers
* Wallet configuration
* Database passwords
* Central IdP hostname and ports
* Authentik configuration
* SMTP configuration, if required

### 2. Review image tags

Review:

```text
docker-compose/.env
```

The environment generation process creates this file with the recommended image tags.

Update image tags only if a different version is intentionally required.

### 3. Run the initial setup

Make the setup script executable:

```bash
chmod +x dataspace-operator-initial-setup.sh
```

Run it:

```bash
./dataspace-operator-initial-setup.sh
```

The setup process generates the environment configuration required by the Docker Compose services and prepares the deployment.

### 4. Start the services

Change to the Docker Compose directory:

```bash
cd docker-compose
```

Start the deployment:

```bash
docker compose up -d
```

### 5. Verify the deployment

Check the running containers:

```bash
docker compose ps
```

Review service logs when troubleshooting:

```bash
docker compose logs
```

Individual service logs can be inspected with:

```bash
docker compose logs <service-name>
```

---

## Authentik configuration

The Dataspace Operator-specific Authentik configuration is **generated by running `dataspace-operator-initial-setup.sh`**.

The deployment contains:

```text
authentik/
└── blueprints/
    └── dataspace-operator-authentik-blueprint.yaml
```

The blueprint is generated for the configured Dataspace Operator environment and imported into the Authentik deployment.

The Authentik configuration script is also responsible for generating the Marketplace configuration required by the Ocean Enterprise Marketplace.

---

## Marketplace configuration

The Dataspace Operator Authentik configuration generates:

```text
dataspace-operator/.env.market
```

### Purpose of `.env.market`

`.env.market` contains the **environment variables required by the Ocean Enterprise Marketplace to use the Central Identity Provider (Central IdP) for user authentication**.

The generated file should be provided to the Marketplace deployment team/operator so that the Marketplace can be configured to use the Dataspace Operator Central IdP.

Do not manually add or modify the generated values unless required by the Marketplace deployment process.

---

# Participant onboarding

The Dataspace Operator can onboard a Participant by configuring a federation/social-login source in the Central Identity Provider.

The onboarding requires configuration information from the Participant.

## Prerequisite

The Participant must provide the Dataspace Operator with a JSON file containing the Participant Identity Provider instance configuration details.

The JSON file contains information such as:

* Participant Identity Provider Well-Known URL
* Participant Identity Provider client/consumer key
* Participant Identity Provider client/consumer secret
* Participant Authentik application slug
* Participant redirect URIs
* Central IdP provider name

---

## Participant configuration file

Copy the JSON file received from the Participant to:

```text
docker-compose/authentik/participant-configs/
```

For example:

```text
docker-compose/
└── authentik/
    └── participant-configs/
        └── config-for-onboarding-participant.json
```

### Example JSON

The following is an example structure. Replace the values with the configuration supplied by the Participant.

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

Treat the client/consumer secret as sensitive information.

---

## Run Participant onboarding

From the dataspace-operator/docker-compose/authentik, run:

```bash
./onboard-participant.sh <config-file-for-onboarding-participant.json>
```

The script reads the Participant configuration file from:

```text
docker-compose/authentik/participant-configs/
```

and configures the Participant federation/social-login source in the Central Identity Provider.

The onboarding should be performed using the provided onboarding script rather than manually modifying the Central IdP configuration.

---

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

* `DB_PASSWORD`
* `POSTGRES_PASSWORD`
* `AUTHENTIK_POSTGRESQL__PASSWORD`
* `AUTHENTIK_SECRET_KEY`
* SMTP passwords
* OIDC client secrets
* Participant federation client/consumer secrets
* Blockchain RPC credentials where applicable

Use secure, deployment-specific values in `.env.config`.

The generated `.env.*` files and Participant onboarding JSON files should also be treated as sensitive configuration.
