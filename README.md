# User Management

The **User Management** repository provides the deployment and configuration components required to provision and manage the services used by **Dataspace Operators** and **Participants** in the Ocean Enterprise Marketplace ecosystem.

The repository is organized into two major modules:

* [`dataspace-operator/`](./dataspace-operator) — deployment and configuration for a Dataspace Operator.
* [`participant/`](./participant) — deployment and configuration for a Participant.

Both modules follow a similar deployment architecture and provide the infrastructure and supporting services required for authentication, secrets management, databases, signing, networking, and wallet-related functionality.

---

## Repository Overview

```text
user-management/
│
├── dataspace-operator/
│   ├── authentik/
│   ├── docker-compose/
│   ├── .gitignore
│   ├── .env
│   ├── docker-compose.yml
│   ├── .env.config
│   ├── dataspace_operator_environment_configuration.py
│   ├── dataspace-operator-initial-setup.sh
│   └── requirements.txt
│
├── participant/
│   ├── authentik/
│   ├── docker-compose/
│   ├── .env
│   ├── docker-compose.yml
│   ├── .env.config
│   ├── participant_environment_configuration.py
│   ├── participant-initial-setup.sh
│   └── requirements.txt
│
├── .gitignore
└── README.md
```

The `docker-compose/` directory in each module contains the service-specific deployment configuration, while the module-level environment and setup files control how the complete deployment is configured.

---

# Architecture

The repository contains two independent deployment stacks.

```text
                    Ocean Enterprise Marketplace
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
     Dataspace Operator                  Participant
              │                               │
              │                               │
       ┌──────┴──────┐                 ┌──────┴──────┐
       │             │                 │             │
       ▼             ▼                 ▼             ▼
   Authentik     Supporting        Authentik     Supporting
                 Services                        Services
       │                               │
       ├── OpenBao                     ├── OpenBao
       ├── PostgreSQL                  ├── PostgreSQL
       ├── Signer Server               ├── Signer Server
       ├── Traefik                     ├── Traefik
       ├── Wallet API                  ├── Wallet API
       └── Wallet UI                   └── Wallet UI
```

The exact services and their configuration are defined by the Docker Compose files inside each module.

---

# Dataspace Operator

The `dataspace-operator` module is responsible for deploying the services required for a Dataspace Operator.

It contains:

* Authentik configuration and blueprints
* OpenBao for secrets management
* PostgreSQL initialization for Authentik
* Signer Server
* Traefik reverse proxy and TLS configuration
* Wallet API
* Wallet UI
* Operator-specific environment configuration
* Operator initial setup scripts

For detailed instructions, see:

**[Dataspace Operator README](./dataspace-operator/README.md)**

---

# Participant

The `participant` module provides the corresponding deployment stack for a Participant.

It contains:

* Authentik configuration and participant blueprints
* OpenBao for secrets management
* PostgreSQL initialization for Authentik
* Signer Server
* Traefik reverse proxy and TLS configuration
* Wallet API
* Wallet UI
* Participant-specific environment configuration
* Participant initial setup scripts

For detailed instructions, see:

**[Participant README](./participant/README.md)**

---

# Common Services

Both deployments contain a number of common infrastructure components.

## Authentik

Authentik provides the identity and authentication layer.

The repository contains custom Authentik blueprints for the different deployment types.

For example:

```text
dataspace-operator/
└── authentik/
    └── dataspace_operator_blueprint.py
```

and:

```text
participant/
└── authentik/
    └── participant_blueprint.py
```

The Docker Compose deployment also contains the corresponding Authentik blueprint YAML files.

---

## OpenBao

OpenBao is used as the secrets-management component.

It is responsible for securely storing and managing sensitive configuration and credentials required by the deployment.

The OpenBao deployment contains:

* OpenBao configuration
* Initialization scripts
* Account-management scripts
* Secret storage
* Private keys
* Environment configuration

Sensitive files should never be committed to source control.

---

## PostgreSQL

PostgreSQL is used as the database backend for services that require persistent database storage.

The repository contains initialization scripts specifically for creating the Authentik database.

Example:

```text
postgres-init/
├── .env.postgres
└── create-authentik-db.sh
```

---

## Signer Server

The Signer Server provides signing-related functionality required by the deployed ecosystem components.

Its deployment includes:

```text
signer-server/
├── certs/
└── .env.signer-server
```

---

## Traefik

Traefik acts as the reverse proxy and TLS entry point for the deployment.

Its configuration contains:

```text
traefik/
├── certs/
├── dynamic/
└── .env.traefik
```

TLS certificates and keys should be handled securely and should not be committed to Git unless they are explicitly intended to be public/test certificates.

---

## Wallet API and Wallet UI

The deployment includes both backend and frontend components for wallet functionality.

```text
wallet-api/
├── config/
├── data/
└── .env.wallet-api

wallet-ui/
├── .env.wallet-ui
└── .gitkeep
```

The Wallet API provides the backend functionality, while the Wallet UI provides the user-facing interface.

---

# Configuration Model

Configuration is separated between deployment-level configuration and service-specific configuration.

Typical configuration files include:

```text
.env
.env.config
```

and service-specific files such as:

```text
.env.authentik
.env.openbao
.env.postgres
.env.signer-server
.env.traefik
.env.wallet-api
.env.wallet-ui
```

The exact variables required by each deployment are defined by the corresponding Compose files and initialization scripts.

**Do not copy secrets directly into committed `.env` files unless the repository is explicitly designed for that purpose.**

For production deployments, sensitive values such as:

* passwords
* private keys
* signing keys
* tokens
* database credentials
* secret-management credentials
* TLS private keys

must be protected appropriately.

---

# Initial Setup

Each module provides an initial setup script.

For Dataspace Operator:

```bash
cd dataspace-operator
./dataspace-operator-initial-setup.sh
```

For Participant:

```bash
cd participant
./participant-initial-setup.sh
```

These scripts should be treated as the primary entry point for preparing a fresh deployment.

Before running an initial setup script, review the corresponding module README and configuration files.

---

# Running the Deployment

After configuration and initial setup, the Docker Compose stack can be started from the corresponding module directory.

For example:

```bash
cd dataspace-operator
docker compose up -d
```

or:

```bash
cd participant
docker compose up -d
```

Check the module-specific README for any required initialization or ordering steps before starting the complete stack.

---

# Stopping the Deployment

To stop a deployment:

```bash
docker compose down
```

Run this command from the relevant module directory.

To inspect the status of the services:

```bash
docker compose ps
```

To inspect service logs:

```bash
docker compose logs
```

For a specific service:

```bash
docker compose logs <service-name>
```

---

# Security Considerations

This repository deploys infrastructure that handles identities, credentials, secrets, private keys, and authentication.

Before using it in a production environment:

1. Replace all development/test credentials.
2. Use production TLS certificates.
3. Protect all private keys.
4. Review all `.env` files.
5. Do not commit secrets to Git.
6. Restrict access to OpenBao.
7. Use appropriate database credentials.
8. Review exposed ports and network access.
9. Review Traefik routing and TLS configuration.
10. Ensure persistent volumes and backups are secured.

---

# Development vs Production

The repository structure supports deployment configuration, but production readiness depends on the values supplied to the configuration files and environment variables.

A development deployment may use:

* local hostnames
* test certificates
* development credentials
* local Docker volumes
* locally accessible services

A production deployment should use:

* production DNS names
* trusted TLS certificates
* strong credentials
* securely managed secrets
* persistent and backed-up storage
* restricted network access

---

# Requirements

The deployment requires the tools used by the setup and Compose configuration.

At minimum, ensure that the host has:

* Docker
* Docker Compose
* Git
* Bash
* Python, where required by the environment configuration scripts

Python dependencies are documented in the respective:

```text
requirements.txt
```

files.

---

# Repository Structure

## Dataspace Operator

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
│   │
│   ├── openbao/
│   ├── postgres-init/
│   ├── signer-server/
│   ├── traefik/
│   └── wallet-api/
│
├── wallet-ui/
├── .env
├── docker-compose.yml
├── .env.config
├── dataspace_operator_environment_configuration.py
├── dataspace-operator-initial-setup.sh
└── requirements.txt
```

## Participant

```text
participant/
├── authentik/
│   └── participant_blueprint.py
│
├── docker-compose/
│   ├── authentik/
│   │   ├── blueprints/
│   │   └── certs/
│   │
│   ├── openbao/
│   ├── postgres-init/
│   ├── signer-server/
│   ├── traefik/
│   └── wallet-api/
│
├── wallet-ui/
├── .env
├── docker-compose.yml
├── .env.config
├── participant_environment_configuration.py
├── participant-initial-setup.sh
└── requirements.txt
```

---

# Choosing a Deployment

Use the **Dataspace Operator** deployment when provisioning infrastructure for an entity acting as the Dataspace Operator.

Use the **Participant** deployment when provisioning infrastructure for an entity participating in the dataspace.

Each module is independently configurable and deployable.

---

# Further Documentation

Detailed deployment instructions are available in:

* [Dataspace Operator](./dataspace-operator/README.md)
* [Participant](./participant/README.md)
