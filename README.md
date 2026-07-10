# 🚀 Authentik Blueprint Automation Suite

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Authentik](https://img.shields.io/badge/Authentik-2024.10%2B-orange.svg)](https://goauthentik.io/)

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
