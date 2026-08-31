# AuraML — Production AI/ML Lifecycle & Governance Platform

> **Cloud-Native Enterprise Platform for Dataset Management, Asynchronous Model Training, ML Governance, Controlled Inference, and Autonomous AI Analysis**

AuraML is a production-grade AI/ML developer platform designed for data science and engineering teams to securely ingest datasets, profile data asynchronously out-of-process, execute background model training, evaluate quality through automated governance gates, promote models across isolated environments, serve controlled inferences, and inspect system telemetry—backed by S3 object storage, PostgreSQL, Redis task queues, and OIDC RBAC security.

---

## 🏛 System Architecture

```mermaid
graph TD
    User([User / Browser Client]) -->|HTTPS / WSS| WebSPA[React 18 TypeScript SPA]
    WebSPA -->|REST API / WebSockets| APINode[FastAPI API Gateway Node]
    
    subgraph Core Infrastructure
        APINode -->|Auth & RBAC| AuthModule[JWT / OIDC Auth Module]
        APINode -->|Rate Limit / Cache| Redis[Redis Broker & Queue]
        APINode -->|Transactional Data| PostgreSQL[(PostgreSQL Database)]
        APINode -->|Object Storage| S3[S3 Object Storage]
    end

    subgraph Asynchronous Worker Layer
        Redis -->|Job Queue| Worker[Async Worker Process]
        Worker -->|Atomic Claims| PostgreSQL
        Worker -->|Save Artifacts & SHA-256| S3
        Worker -->|Real-time PubSub| Redis
    end

    Redis -->|WebSocket Broadcasts| WebSPA
```

---

## 🔄 ML Lifecycle & Governance

```mermaid
flowchart LR
    A[Dataset Upload] --> B[Async Profiling]
    B --> C[Dataset READY]
    C --> D[Model Training Job]
    D --> E[S3 Weights & SHA-256 Digest]
    E --> F[Quality Gate Evaluation]
    F -->|Metrics Passed| G[APPROVED Status]
    G --> H[Environment Promotion]
    H -->|STAGING / PRODUCTION| I[Controlled Inference]
    I --> J[Prediction Log & Telemetry]
```

---

## 🔒 Security & Governance Architecture

```mermaid
graph TB
    ClientRequest[Client API Request] --> TokenCheck{JWT Valid?}
    TokenCheck -- No --> DenyAuth[HTTP 401 Unauthorized]
    TokenCheck -- Yes --> RBACCheck{Has Role Permission?}
    RBACCheck -- No --> DenyPerm[HTTP 403 Forbidden]
    RBACCheck -- Yes --> WorkspaceCheck{Valid Workspace ID?}
    WorkspaceCheck -- No --> DenyIsolation[HTTP 404 Not Found]
    WorkspaceCheck -- Yes --> ExecOperation[Execute Operation & Log Audit Event]
```

---

## ✨ Key Platform Features

- **Dataset Management & Automated Profiling**: Streamlined CSV ingestion with MIME-type verification, path-traversal prevention, file size limits (50MB), and asynchronous column statistics profiling.
- **Asynchronous Redis Worker Engine**: Decoupled background task execution with connection pooling, Pub/Sub WebSocket status updates, atomic claims (`SELECT FOR UPDATE / SKIP LOCKED`), retry policy execution, and 15-minute stuck-job recovery.
- **Cloud-Native S3 Object Storage**: Pluggable `StorageBackend` abstraction supporting AWS S3, MinIO, Cloudflare R2, and local fallback with tenant workspace prefixing (`workspaces/{workspace_id}/...`).
- **Cryptographic SHA-256 Artifact Integrity**: Mandatory hash computation during model persistence with mandatory hash validation on loading; tampered artifacts are instantly rejected.
- **ML Governance & Quality Gates**: Automated validation checks (accuracy threshold, F1 score, latency bounds) guarding model promotion from `draft` to `approved`, `staging`, and `production`.
- **Controlled Inference Engine**: Schema-validated prediction endpoint strictly limited to promoted models with real-time confidence scores and inference latency tracking.
- **Autonomous AI Agent**: Tool-augmented AI assistant capable of workspace dataset inspection, model evaluation analysis, and automated promotion recommendation using constrained tool permissions.
- **Enterprise Security & Audit Trail**: OIDC JWT token verification, fine-grained RBAC (`viewer`, `editor`, `owner`), workspace tenant isolation, Redis rate-limiting (120 req/min), structured JSON logging with credential redaction, and audit trail logging.

---

## 🛠 Technology Stack

| Layer | Technologies |
|---|---|
| **API Gateway & Core** | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| **Database & ORM** | PostgreSQL, SQLAlchemy 2.0 (AsyncIO), Alembic |
| **Task Queue & Cache** | Redis 5.x, `redis.asyncio` |
| **Object Storage** | AWS S3 SDK (`boto3` / `botocore`), MinIO |
| **ML Engine** | Scikit-Learn, NumPy, Pandas |
| **Frontend SPA** | React 18, TypeScript, Vite, TailwindCSS |
| **Observability** | Prometheus (`prometheus_client`), OpenTelemetry-compatible JSON Logs |

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Python `3.11+`
- Node.js `20+` & `npm`
- PostgreSQL & Redis (or Docker Compose)

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/varunsharma0111/AI-ML-Production-Capstone.git
cd AI-ML-Production-Capstone

# Install backend package in editable mode
pip install -e .[dev]

# Install frontend web dependencies
cd apps/web
npm install
cd ../..
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/auraml_dev
REDIS_URL=redis://localhost:6379/0
STORAGE_BACKEND=local
STORAGE_PATH=./data/uploads
OIDC_ISSUER=https://issuer.example.com/
OIDC_AUDIENCE=auraml-api
OIDC_JWKS_URL=https://issuer.example.com/.well-known/jwks.json
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start Local Development Services

**Terminal 1 — API Server:**
```bash
uvicorn apps.api.app.main:app --reload --port 8000
```

**Terminal 2 — Async Worker:**
```bash
python services/worker/main.py
```

**Terminal 3 — React Frontend:**
```bash
cd apps/web
npm run dev
```

---

## 🧪 Quality Gates & Automated Verification

```bash
# Static Analysis & Formatting
ruff check .
ruff format --check .

# Strict Type Checking
mypy --explicit-package-bases apps/api services tests

# Unit, Integration, Security, and Load Tests
pytest -v

# Frontend Production Build Verification
cd apps/web && npm run build
```

---

## 📚 Product Documentation & Guides

- [Architecture Guide](docs/architecture.md) — Architectural design, modules, and component interactions.
- [Deployment Guide](docs/deployment.md) — Production deployment guidelines for Vercel, Render, Neon, and AWS S3.
- [Security Guide](docs/security.md) — Security model, RBAC policies, input sanitization, and secret protection.
- [API Reference](docs/api.md) — Complete REST & WebSocket endpoint documentation.
- [Live Presentation & Demo Guide](docs/demo-guide.md) — Step-by-step 5-10 minute presentation guide.
- [Resume Project Description](docs/resume-project-description.md) — Resume bullet points and technical summary.
- [Engineering Interview Q&A Guide](docs/interview-guide.md) — System design and technical Q&A.
- [Portfolio Readiness Report](docs/portfolio-readiness.md) — Final portfolio verification report.
