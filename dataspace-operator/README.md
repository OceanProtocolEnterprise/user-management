# Dataspace Operator

The `dataspace-operator` module contains everything required to configure and deploy the services associated with a **Dataspace Operator** in the Ocean Enterprise Marketplace ecosystem.

The deployment is based on Docker Compose and consists of identity management, secrets management, database, signing, reverse-proxy, and wallet-related services.

---

# Overview

The Dataspace Operator deployment provides the following major components:

| Component                 | Purpose                           |
| ------------------------- | --------------------------------- |
| Authentik                 | Identity and authentication       |
| OpenBao                   | Secrets management                |
| PostgreSQL                | Database backend                  |
| Signer Server             | Signing functionality             |
| Traefik                   | Reverse proxy and TLS termination |
| Wallet API                | Wallet backend services           |
| Wallet UI                 | Wallet frontend                   |
| Environment Configuration | Operator-specific configuration   |
| Initial Setup             | Automated deployment preparation  |

The complete deployment is orchestrated through:

```text
docker-compose.yml
```

---

# Directory Structure

```text
dataspace-operator/
│
├── authentik/
│   └── dataspace_operator_blueprint.py
│
├── docker-compose/
│   │
│   ├── authentik/
│   │   ├── blueprints/
│   │   │   └── dataspace-operator-authentik-blueprint.yaml
│   │   ├── certs/
│   │   ├── participant-configs/
│   │   ├── scripts/
│   │   │   └── dataspace_operator_add_participant.py
│   │   ├── .env.authentik
│   │   └── onboard-participant.sh
│   │
│   ├── openbao/
│   │   ├── certs/
│   │   ├── secrets/
│   │   ├── private_keys/
│   │   ├── .env.openbao
│   │   ├── Dockerfile
│   │   ├── docker-entrypoint.sh
│   │   ├── init-vault.sh
│   │   ├── manage-accounts.sh
│   │   └── openbao.hcl
│   │
│   ├── postgres-init/
│   │   ├── .env.postgres
│   │   └── create-authentik-db.sh
│   │
│   ├── signer-server/
│   │   ├── certs/
│   │   └── .env.signer-server
│   │
│   ├── traefik/
│   │   ├── certs/
│   │   ├── dynamic/
│   │   └── .env.traefik
│   │
│   └── wallet-api/
│       ├── config/
│       ├── data/
│       └── .env.wallet-api
│
├── wallet-ui/
│   ├── .env.wallet-ui
│   └── .gitkeep
│
├── .env
├── docker-compose.yml
├── .env.config
├── dataspace_operator_environment_configuration.py
├── dataspace-operator-initial-setup.sh
└── requirements.txt
```

---

# Components

## 1. Authentik

Authentik provides the identity and authentication layer for the Dataspace Operator deployment.

The repository contains a dedicated operator blueprint:

```text
authentik/
└── dataspace_operator_blueprint.py
```

and the Docker Compose deployment contains the corresponding Authentik blueprint:

```text
docker-compose/authentik/blueprints/
└── dataspace-operator-authentik-blueprint.yaml
```

The Authentik configuration also contains:

```text
docker-compose/authentik/
├── certs/
├── participant-configs/
├── scripts/
├── .env.authentik
└── onboard-participant.sh
```

### Participant onboarding

The operator deployment contains tooling for onboarding participants.

For example:

```text
scripts/
└── dataspace_operator_add_participant.py
```

and:

```text
onboard-participant.sh
```

These components are intended to support adding and configuring participants within the operator environment.

---

# 2. OpenBao

OpenBao is used as the secrets-management layer.

The deployment contains:

```text
openbao/
├── certs/
├── secrets/
├── private_keys/
├── .env.openbao
├── Dockerfile
├── docker-entrypoint.sh
├── init-vault.sh
├── manage-accounts.sh
└── openbao.hcl
```

The important responsibilities of this component include:

* Secret storage
* Private-key management
* OpenBao initialization
* Account management
* Secure communication using certificates
* Loading the OpenBao server configuration

### Important

The following directories/files may contain sensitive material:

```text
secrets/
private_keys/
certs/
.env.openbao
```

Do not commit production credentials or private keys to the repository.

---

# 3. PostgreSQL

PostgreSQL provides the database backend required by the deployment.

The initialization configuration is located at:

```text
postgres-init/
├── .env.postgres
└── create-authentik-db.sh
```

The database initialization script is responsible for preparing the Authentik database.

Before starting the complete deployment, ensure that the database configuration is correctly populated.

---

# 4. Signer Server

The Signer Server provides signing functionality required by the deployment.

Configuration:

```text
signer-server/
├── certs/
└── .env.signer-server
```

The certificate configuration should be reviewed before deploying into a production environment.

---

# 5. Traefik

Traefik is used as the reverse proxy and TLS entry point.

Configuration:

```text
traefik/
├── certs/
├── dynamic/
└── .env.traefik
```

The `certs/` directory contains TLS-related material, while `dynamic/` contains dynamic Traefik configuration.

Review:

* Hostnames
* Routing rules
* TLS certificates
* TLS private keys
* Service endpoints
* External/internal ports

before deploying the stack.

---

# 6. Wallet API

The Wallet API is the backend component of the wallet functionality.

Its configuration is located under:

```text
wallet-api/
├── config/
├── data/
└── .env.wallet-api
```

The environment configuration should be reviewed and populated before starting the deployment.

---

# 7. Wallet UI

The Wallet UI provides the frontend interface for the wallet functionality.

Configuration:

```text
wallet-ui/
└── .env.wallet-ui
```

The UI configuration should be consistent with the URLs and endpoints exposed by the Wallet API and Traefik configuration.

---

# Configuration

The operator deployment has multiple configuration layers.

## Main configuration

```text
.env
.env.config
```

## Operator environment configuration

```text
dataspace_operator_environment_configuration.py
```

## Service-specific configuration

```text
docker-compose/authentik/.env.authentik
docker-compose/openbao/.env.openbao
docker-compose/postgres-init/.env.postgres
docker-compose/signer-server/.env.signer-server
docker-compose/traefik/.env.traefik
docker-compose/wallet-api/.env.wallet-api
wallet-ui/.env.wallet-ui
```

The exact values required by each environment should be taken from the corresponding Compose configuration and setup scripts.

---

# Configuration Checklist

Before starting a fresh deployment, verify the following.

* [ ] Operator-specific environment values are configured.
* [ ] `.env` is configured.
* [ ] `.env.config` is configured.
* [ ] Authentik configuration is populated.
* [ ] Authentik certificates are available.
* [ ] OpenBao configuration is populated.
* [ ] OpenBao certificates are available.
* [ ] OpenBao secrets and private keys are securely configured.
* [ ] PostgreSQL credentials are configured.
* [ ] Signer Server configuration is populated.
* [ ] Signer Server certificates are available.
* [ ] Traefik configuration is populated.
* [ ] Traefik certificates are available.
* [ ] Wallet API configuration is populated.
* [ ] Wallet UI configuration is populated.
* [ ] DNS/hostnames point to the deployment where required.
* [ ] Required ports are available.
* [ ] Docker and Docker Compose are installed.

---

# Initial Setup

The repository provides an initial setup script:

```text
dataspace-operator-initial-setup.sh
```

Make the script executable if required:

```bash
chmod +x dataspace-operator-initial-setup.sh
```

Then run:

```bash
./dataspace-operator-initial-setup.sh
```

The initial setup script should be considered the preferred mechanism for preparing a new Dataspace Operator deployment.

Before executing it, review the script to understand which configuration files, directories, secrets, certificates, and services it initializes.

---

# Starting the Deployment

After completing configuration and initial setup:

```bash
docker compose up -d
```

Check the running containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs
```

To follow logs:

```bash
docker compose logs -f
```

To inspect a particular service:

```bash
docker compose logs -f <service-name>
```

---

# Stopping the Deployment

To stop the deployment:

```bash
docker compose down
```

To stop the deployment while preserving Docker-managed volumes:

```bash
docker compose down
```

Be careful when removing volumes because persistent service data may be stored there.

---

# Restarting Services

To restart the complete deployment:

```bash
docker compose restart
```

To restart an individual service:

```bash
docker compose restart <service-name>
```

---

# Updating the Deployment

When configuration or images are updated, review the changes before restarting the stack.

A typical update flow is:

```bash
git pull
```

Then:

```bash
docker compose pull
```

and:

```bash
docker compose up -d
```

If the deployment contains locally built images, rebuild them as required:

```bash
docker compose build
docker compose up -d
```

---

# Participant Onboarding

One of the specific capabilities of the Dataspace Operator deployment is participant onboarding.

The relevant tooling is located under:

```text
docker-compose/authentik/
├── participant-configs/
├── scripts/
│   └── dataspace_operator_add_participant.py
└── onboard-participant.sh
```

The exact onboarding workflow should be performed through the provided scripts rather than manually modifying generated configuration.

Before onboarding a participant, make sure the operator's:

* authentication configuration
* certificates
* participant configuration
* secrets
* wallet configuration
* routing configuration

are correctly configured.

---

# Security

This deployment contains sensitive infrastructure.

Pay particular attention to:

```text
.env*
certs/
secrets/
private_keys/
```

Production deployments should use securely managed:

* passwords
* API credentials
* signing keys
* private keys
* TLS certificates
* database credentials
* OpenBao credentials

Never commit production secrets or private keys to Git.

---

# Troubleshooting

## Check service status

```bash
docker compose ps
```

## Check all logs

```bash
docker compose logs
```

## Check one service

```bash
docker compose logs <service-name>
```

## Follow logs

```bash
docker compose logs -f <service-name>
```

## Check configuration

If the deployment fails to start, first check:

1. `.env`
2. `.env.config`
3. service-specific `.env` files
4. certificates
5. DNS/hostnames
6. Docker volumes
7. service dependencies
8. OpenBao initialization
9. PostgreSQL initialization
10. Traefik routing configuration

---

# Deployment Flow

The recommended high-level flow is:

```text
1. Clone repository
        │
        ▼
2. Enter dataspace-operator/
        │
        ▼
3. Configure environment files
        │
        ▼
4. Configure certificates and secrets
        │
        ▼
5. Run initial setup
        │
        ▼
6. Start Docker Compose
        │
        ▼
7. Verify services
        │
        ▼
8. Verify authentication
        │
        ▼
9. Verify wallet services
        │
        ▼
10. Onboard participants
```

---

# Production Deployment Checklist

* [ ] Production domain names configured.
* [ ] Production TLS certificates installed.
* [ ] TLS private keys secured.
* [ ] Strong database credentials configured.
* [ ] OpenBao initialized securely.
* [ ] Production secrets stored securely.
* [ ] Signer Server configured.
* [ ] Traefik routing reviewed.
* [ ] Wallet API configured.
* [ ] Wallet UI configured.
* [ ] Authentik configuration verified.
* [ ] Docker volumes backed up.
* [ ] Required firewall rules configured.
* [ ] Participant onboarding tested.
* [ ] Service health verified.

---

# Related Documentation

For the overall repository architecture, see:

```text
../README.md
```

For participant deployment documentation, see:

```text
../participant/README.md
```
