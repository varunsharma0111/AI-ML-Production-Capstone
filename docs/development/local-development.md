# Local Development

## Current foundation scope

Phase 1 establishes repository conventions and quality checks only. It does not provide application services, dependency installation, Docker Compose, Kubernetes manifests, or deployment configuration. Those arrive in later approved phases.

## Prerequisites

- Git
- Python 3.11 or later
- Docker Desktop, Kind/Minikube, and Node.js are not required until their respective phases.

## Quality-tool setup

From the repository root, create an isolated virtual environment and install only the development-quality tools:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ruff==0.12.11 mypy==1.18.2 pytest==8.4.2 pre-commit==4.3.0
```

Run the complete Phase 1 check set:

```powershell
ruff format --check .
ruff check .
mypy tests
pytest
pre-commit run --all-files
```

## Environment and secrets conventions

- Never commit `.env` files, access tokens, credentials, certificates, or private keys.
- Future services will document their required variables in committed `*.env.example` files containing placeholders only.
- Local-only state belongs in Docker volumes or ignored directories, never in source-controlled paths.

## Deployment profiles

The complete local stack will be introduced with Docker Compose. The public demo and full production profiles are documented in [deployment profiles](../architecture/deployment-profiles.md). Phase 1 does not attempt to run these profiles.
