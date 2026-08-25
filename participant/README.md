# Participant

The `participant` module contains everything required to configure and deploy the services associated with a **Participant** in the Ocean Enterprise Marketplace ecosystem.

The deployment provides the infrastructure required for authentication, secrets management, database services, signing, reverse proxy/TLS, and wallet functionality.

The deployment is managed using Docker Compose and is independently configurable from the Dataspace Operator deployment.

---

# Overview

The Participant deployment consists of the following major components:

| Component                 | Purpose                            |
| ------------------------- | ---------------------------------- |
| Authentik                 | Identity and authentication        |
| OpenBao                   | Secrets management                 |
| PostgreSQL                | Database backend                   |
| Signer Server             | Signing functionality              |
| Traefik                   | Reverse proxy and TLS              |
| Wallet API                | Wallet backend                     |
| Wallet UI                 | Wallet frontend                    |
| Environment Configuration | Participant-specific configuration |
| Initial Setup             | Automated deployment preparation   |

---

# Directory Structure

```text
participant/
│
├── authentik/
│   └── participant_blueprint.py
│
├── docker-compose/
│   │
│   ├── authentik/
│   │   ├── blueprints/
│   │   │   └── participant-authentik-blueprint.yaml
│   │   ├── certs/
│   │   └── .env.authentik
│   │
│   ├── openbao/
│   │   ├── certs/
│   │   ├── secrets/
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
├── participant_environment_configuration.py
├── participant-initial-setup.sh
└── requirements.txt
```

---

# Components

## 1. Authentik

Authentik provides the identity and authentication functionality for the Participant deployment.

The repository contains a participant-specific Authentik blueprint:

```text
authentik/
└── participant_blueprint.py
```

The Docker Compose deployment contains:

```text
docker-compose/authentik/
├── blueprints/
│   └── participant-authentik-blueprint.yaml
├── certs/
└── .env.authentik
```

The participant blueprint provides the deployment-specific Authentik configuration.

---

# 2. OpenBao

OpenBao is used as the secrets-management component.

The deployment contains:

```text
openbao/
├── certs/
├── secrets/
├── .env.openbao
├── Dockerfile
├── docker-entrypoint.sh
├── init-vault.sh
├── manage-accounts.sh
└── openbao.hcl
```

OpenBao is responsible for securely managing sensitive information used by the participant deployment.

Sensitive information can include:

* Credentials
* Tokens
* Secrets
* Private keys
* Service credentials

The `secrets/` directory and environment configuration should therefore be treated as sensitive.

---

# 3. PostgreSQL

PostgreSQL provides the database backend used by the deployment.

The initialization configuration is located at:

```text
postgres-init/
├── .env.postgres
└── create-authentik-db.sh
```

The database initialization script prepares the Authentik database.

Make sure PostgreSQL credentials are correctly configured before starting the deployment.

---

# 4. Signer Server

The Signer Server provides signing-related functionality.

Configuration:

```text
signer-server/
├── certs/
└── .env.signer-server
```

Review the signer configuration and certificates before starting the participant deployment.

---

# 5. Traefik

Traefik acts as the reverse proxy and TLS entry point.

Configuration:

```text
traefik/
├── certs/
├── dynamic/
└── .env.traefik
```

Before deployment, verify:

* Participant hostname/domain
* TLS certificates
* TLS private keys
* Routing rules
* Backend service addresses
* Required ports

---

# 6. Wallet API

The Wallet API provides backend wallet functionality.

Configuration:

```text
wallet-api/
├── config/
├── data/
└── .env.wallet-api
```

The Wallet API configuration should be reviewed together with the Traefik and Wallet UI configuration.

---

# 7. Wallet UI

The Wallet UI provides the frontend interface for wallet functionality.

Configuration:

```text
wallet-ui/
└── .env.wallet-ui
```

The UI configuration should point to the appropriate wallet and backend endpoints exposed by the Participant deployment.

---

# Configuration

The Participant deployment has several configuration levels.

## Main configuration

```text
.env
.env.config
```

## Participant environment configuration

```text
participant_environment_configuration.py
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

The exact environment variables and their accepted values should be taken from the corresponding Compose files and setup scripts.

---

# Configuration Checklist

Before deploying a Participant, verify:

* [ ] Participant environment values are configured.
* [ ] `.env` is configured.
* [ ] `.env.config` is configured.
* [ ] Authentik configuration is populated.
* [ ] Authentik certificates are available.
* [ ] OpenBao configuration is populated.
* [ ] OpenBao certificates are available.
* [ ] OpenBao secrets are configured securely.
* [ ] PostgreSQL credentials are configured.
* [ ] Signer Server configuration is populated.
* [ ] Signer Server certificates are available.
* [ ] Traefik configuration is populated.
* [ ] Traefik certificates are available.
* [ ] Wallet API configuration is populated.
* [ ] Wallet UI configuration is populated.
* [ ] Participant DNS/hostname is configured where required.
* [ ] Required ports are available.
* [ ] Docker and Docker Compose are installed.

---

# Initial Setup

The Participant module provides an initial setup script:

```text
participant-initial-setup.sh
```

Make it executable if necessary:

```bash
chmod +x participant-initial-setup.sh
```

Run the initial setup:

```bash
./participant-initial-setup.sh
```

The script should be used as the primary entry point for preparing a fresh Participant deployment.

Before running it, review the script to understand the operations it performs and the configuration it expects.

---

# Starting the Participant

After the configuration and initial setup are complete:

```bash
docker compose up -d
```

Check the deployment:

```bash
docker compose ps
```

View all logs:

```bash
docker compose logs
```

Follow logs:

```bash
docker compose logs -f
```

View logs for a specific service:

```bash
docker compose logs -f <service-name>
```

---

# Stopping the Participant

To stop the deployment:

```bash
docker compose down
```

Be careful when removing Docker volumes because they may contain persistent application data.

---

# Restarting the Participant

Restart all services:

```bash
docker compose restart
```

Restart a specific service:

```bash
docker compose restart <service-name>
```

---

# Updating the Deployment

After updating the repository:

```bash
git pull
```

Review the changes, then update the Docker images:

```bash
docker compose pull
```

Start the updated deployment:

```bash
docker compose up -d
```

If local images are used:

```bash
docker compose build
docker compose up -d
```

---

# Deployment Flow

The recommended Participant deployment flow is:

```text
1. Clone repository
        │
        ▼
2. Enter participant/
        │
        ▼
3. Configure environment
        │
        ▼
4. Configure certificates
        │
        ▼
5. Configure secrets
        │
        ▼
6. Run participant-initial-setup.sh
        │
        ▼
7. Start Docker Compose
        │
        ▼
8. Verify services
        │
        ▼
9. Verify Authentik
        │
        ▼
10. Verify OpenBao
        │
        ▼
11. Verify Signer Server
        │
        ▼
12. Verify Wallet API/UI
        │
        ▼
13. Verify Traefik/TLS access
```

---

# Security

The Participant deployment contains security-sensitive infrastructure.

The following should be treated as sensitive:

```text
.env*
certs/
secrets/
```

Depending on the deployment, private keys and credentials may also be stored or referenced by these locations.

For production deployments:

* Use strong credentials.
* Do not commit secrets to Git.
* Protect TLS private keys.
* Protect signing keys.
* Restrict access to OpenBao.
* Use production TLS certificates.
* Restrict network access to exposed services.
* Secure PostgreSQL credentials.
* Back up persistent data securely.

---

# Troubleshooting

## Check running services

```bash
docker compose ps
```

## View all logs

```bash
docker compose logs
```

## View one service

```bash
docker compose logs <service-name>
```

## Follow service logs

```bash
docker compose logs -f <service-name>
```

If a service does not start, check the following in order:

1. `.env`
2. `.env.config`
3. Service-specific `.env` files
4. Certificates
5. DNS/hostnames
6. Docker configuration
7. PostgreSQL initialization
8. OpenBao initialization
9. Signer Server configuration
10. Traefik routing
11. Wallet API configuration
12. Wallet UI configuration

---

# Production Deployment Checklist

* [ ] Participant domain/hostname configured.
* [ ] Production TLS certificates installed.
* [ ] TLS private keys secured.
* [ ] Authentik configured.
* [ ] PostgreSQL credentials secured.
* [ ] OpenBao initialized securely.
* [ ] OpenBao secrets configured.
* [ ] Signer Server configured.
* [ ] Traefik routing reviewed.
* [ ] Wallet API configured.
* [ ] Wallet UI configured.
* [ ] Docker volumes backed up.
* [ ] Firewall rules reviewed.
* [ ] External access tested.
* [ ] Authentication tested.
* [ ] Wallet functionality tested.
* [ ] TLS configuration verified.

---

# Participant vs Dataspace Operator

The Participant deployment shares much of its infrastructure with the Dataspace Operator deployment, but the configurations and Authentik blueprints are specific to the Participant role.

The main distinction is the purpose of the deployment:

```text
Dataspace Operator
        │
        ├── Operator identity/authentication
        ├── Operator infrastructure
        ├── Participant onboarding
        └── Operator wallet/services


Participant
        │
        ├── Participant identity/authentication
        ├── Participant infrastructure
        └── Participant wallet/services
```

The Participant should therefore be configured using the files under:

```text
participant/
```

and should not reuse the Dataspace Operator environment configuration unless explicitly required by the deployment architecture.

---

# Related Documentation

For the overall User Management repository, see:

```text
../README.md
```

For Dataspace Operator deployment instructions, see:

```text
../dataspace-operator/README.md
```
