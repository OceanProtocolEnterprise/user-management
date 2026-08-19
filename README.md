# 🚀 Authentik Blueprint Automation Suite

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Authentik](https://img.shields.io/badge/Authentik-2026.5%2B-orange.svg)](https://goauthentik.io/)

Automated blueprint generator for Authentik Identity Provider (IDP) and Main OIDC instances.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output](#output)
- [Directory Structure](#directory-structure)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

---

## 📖 Overview

This automation suite helps you quickly generate Authentik blueprint YAML files with pre-configured:

### 🔐 IDP Instance Blueprint
- Custom enrollment flow with organization selection dropdown
- User attribute saving (orgId, walletId, signerServer)
- OAuth2 provider with custom scope mappings
- Custom logout flow with redirect
- All necessary policies, stages, and bindings

### 🆔 Main OIDC Instance Blueprint
- Recovery flow with email-based password reset
- Federated JIT (Just-In-Time) enrollment for OAuth sources
- Custom OAuth source property mapping (federated-oidc-mapping)
- Custom scope mappings (organizationId, signerServer, walletId, federated_identity)
- Policy for saving user attributes
- OAuth2 provider with logout and backchannel logout

---

## ✨ Features

| Feature | IDP | Main OIDC |
|---------|-----|-----------|
| Custom Enrollment Flow | ✅ | ✅ |
| Organization Selection | ✅ | ✅ |
| User Attribute Saving | ✅ | ✅ |
| Scope Mappings | ✅ | ✅ |
| Recovery Flow | ❌ | ✅ |
| Federated JIT Enrollment | ❌ | ✅ |
| OAuth Source Mapping | ❌ | ✅ |
| Custom Logout Flow | ✅ | ✅ |
| Backchannel Logout | ✅ | ✅ |
| Email Configuration | ❌ | ✅ |

---

## 📌 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.7 or later | Required for running scripts |
| **pip** | Latest | Package installer |
| **Authentik** | 2024.10+ | Running instance (Docker/K8s/VM) |
| **Admin Access** | - | Authentik admin credentials |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/authentik-blueprint-automation.git
cd authentik-blueprint-automation

# 2. Run the automated setup
chmod +x setup.sh
./setup.sh

# 3. Edit configuration files
nano .env.idp
nano .env.main-oidc

# 4. Generate blueprints
python generate.py

# 5. Find your blueprints in the output/ directory
ls output/


## Manual start

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env files from examples
cp .env.idp.example .env.idp
cp .env.main-oidc.example .env.main-oidc

# Create output directories
mkdir -p output logs

# Edit .env files with your configuration
nano .env.idp
nano .env.main-oidc

python3 main_oidc_blueprint.py --env .env_main

python3 idp_generate_blueprint.py --env .env_idp

# /////////////////////////////Federation and Social Login Source Onboarding \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# running federation source file in authentik docker
#Step 1 
# create config-for-onboarding-tvl-participant.json and Copy the script to container
# pwd :: ubuntu@vm1-stage:~/user-management/dataspace-operator
nano config-for-onboarding-tvl-participant.json
docker cp config-for-onboarding-tvl-participant.json authentik-server:/tmp/

#Step 2 
# create create_oauth_source.py and Copy the script to container
# pwd :: ubuntu@vm1-stage:~/user-management/dataspace-operator/authentik$ 
nano create_federation_source.py
docker cp create_federation_source.py authentik-server:/tmp/

# step 3 run this command 
# pwd :: ubuntu@vm1-stage:~/user-management/dataspace-operator/authentik$ 
docker exec -it authentik-server \
  /ak-root/.venv/bin/python \
  /tmp/create_federation_source.py \
  --config /tmp/config-for-onboarding-tvl-participant.json
