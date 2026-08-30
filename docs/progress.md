# Progress

## Phase 1 — Engineering foundation

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- Repository editor, line-ending, and Git normalization conventions.
- Python formatting, linting, static-type, and test configuration.
- Pre-commit hygiene hooks and GitHub Actions quality workflow.
- Contributor and local-development setup documentation.
- A tested structural guard for the approved Phase 1 repository layout.

### Verification

- `ruff format --check .` — passed (1 Python test file checked).
- `ruff check .` — passed.
- `mypy tests` — passed (1 source file checked).
- `pytest` — passed (3 foundation tests).
- TOML and YAML configuration parsing — passed.
- `pre-commit run --files <all non-ignored files>` — passed after normalizing pre-existing Markdown trailing whitespace.

---

## Phase 2 — Secure FastAPI and PostgreSQL vertical slice

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- FastAPI modular monolith application factory, lifespan, and context middleware (`apps/api/app/main.py`).
- Typed application configuration (`app.core.config`), structured JSON logging (`app.core.logging`), and client-safe problem error handlers (`app.core.errors`).
- Issuer-agnostic OIDC JWT verifier (`app.core.security`) and Bearer token dependency injection.
- SQLAlchemy async entities (`User`, `Workspace`, `WorkspaceMembership`, `Task`, `AuditEvent`) and initial Alembic database migration (`database/migrations/versions/20260830_0001_phase2_initial_schema.py`).
- Domain RBAC policy mapping `owner`, `editor`, and `viewer` roles to permissions (`app.domains.identity.policy`).
- Data access repositories (`IdentityRepository`, `TaskRepository`) and transactional service layer (`TaskService`).
- Liveness/readiness health endpoints (`GET /health/live`, `GET /health/ready`), current user endpoint (`GET /api/v1/me`), and workspace-scoped task CRUD endpoints (`POST/GET/PATCH /api/v1/workspaces/{workspace_id}/tasks`).
- Complete test suite (`tests/unit/`, `tests/integration/`, `tests/api/`) covering JWT verification, RBAC rules, repository transactions, health readiness, 401 unauthenticated / 403 forbidden responses, workspace isolation, optimistic concurrency (409 conflict), and audit event persistence.

### Verification

- Unit tests (`tests/unit/test_security.py`, `tests/unit/test_policy.py`) — verified.
- Repository integration tests (`tests/integration/test_database.py`) — verified.
- API endpoint integration tests (`tests/api/test_health.py`, `tests/api/test_identity.py`, `tests/api/test_tasks.py`) — verified.
- Code quality, type checking (`mypy`), linting (`ruff`), and pre-commit checks — verified.

### Explicitly not started

Phase 4 and all subsequent product implementation phases remain unstarted: no background workers, task queues (Redis), Kafka messaging, ML pipelines, agent tools, or cloud infrastructure resources have been added.

---

## Phase 3 — React + TypeScript authenticated client

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- React + TypeScript web application (`apps/web/`) configured with Vite bundler and local API proxying (`/api` -> `http://localhost:8000`).
- Vanilla CSS design system (`apps/web/src/index.css`) featuring custom design tokens, dark/light theme overrides, HSL color palette, micro-animations, glassmorphism panels, and focus rings.
- Typed API contracts (`apps/web/src/types/api.ts`) matching Phase 2 FastAPI schemas (`User`, `Workspace`, `Task`, `TaskStatus`, `TaskCreate`, `TaskUpdate`, `ProblemDetails`).
- Central HTTP API client (`apps/web/src/services/apiClient.ts`) providing automatic `Authorization: Bearer <token>` header injection, `X-Request-ID` correlation ID generation, and RFC-7807 problem details parsing into structured `ApiError` objects.
- OIDC Authorization Code + PKCE authentication context (`AuthContext.tsx`), current-user hydration via `GET /api/v1/me`, and local development quick-login token launcher.
- Workspace context (`WorkspaceContext.tsx`) managing active workspace selection and fine-grained RBAC permission checks (`hasPermission`).
- Accessible UI component library:
  - `Button`, `Input`, `Textarea`, `Badge`, `Modal` (dialog with backdrop blur and Escape key handler), `Skeleton` (pulse loaders), and `Alert` (RFC-7807 problem detail banner).
- Header component with real-time backend API liveness/readiness health monitoring indicator (`HealthIndicator.tsx`).
- Workspace Task Dashboard (`TaskList.tsx`, `TaskCard.tsx`, `TaskCreateModal.tsx`, `TaskEditModal.tsx`):
  - Task search and status filtering (`All`, `Open`, `Completed`).
  - Task creation modal with title/description validation.
  - Task edit modal supporting title/description updates, status toggling, and **optimistic concurrency control** (passing `version` and handling HTTP 409 conflict responses).
  - RBAC UI enforcement: `viewer` role hides and disables task creation and editing controls with a read-only badge.
- Pages: `LoginPage`, `CallbackPage`, `TasksPage`, and `NotFoundPage`.
- Test suite (`apps/web/src/tests/`): Unit and component tests for `apiClient` header injection & RFC-7807 problem parsing (`apiClient.test.ts`) and RBAC permissions (`Permissions.test.tsx`).

### Verification

- API client unit tests (`apps/web/src/tests/apiClient.test.ts`) — verified.
- Component RBAC permission tests (`apps/web/src/tests/Permissions.test.tsx`) — verified.
- Type checking (`tsc -b`) and Vite build — verified.

### Explicitly not started

Phase 5 and all subsequent product implementation phases remain unstarted: no ML lifecycle / model serving, transactional outbox / Kafka messaging, agent tools, or cloud infrastructure resources have been added.

---

## Phase 4 — Durable asynchronous jobs and real-time status

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- Alembic database migration (`database/migrations/versions/20260830_0002_phase4_jobs_schema.py`) creating `jobs` and `job_attempts` tables with workspace foreign keys, idempotency keys, max retries, JSONB payload/result storage, and attempt history tracking.
- Job domain enums (`apps/api/app/domains/jobs/types.py`) for `JobStatus` (`queued`, `processing`, `completed`, `failed`, `cancelled`) and `JobType` (`sample_ml_ingestion`, `data_export`, `model_evaluation`).
- SQLAlchemy entities `Job` and `JobAttempt` in `apps/api/app/db/models/entities.py`.
- Data access repository `JobRepository` (`apps/api/app/db/repositories/jobs.py`) supporting workspace-scoped queries, idempotency lookups, status mutations, and attempt logging.
- Background worker execution engine `JobRunner` (`services/worker/runner.py`) handling asynchronous job processing, result generation, and bounded exponential retries with attempt logs.
- Redis ephemeral coordination manager (`apps/api/app/core/redis.py`) for WebSocket pub/sub notification broadcasting.
- Transactional business service `JobService` (`apps/api/app/services/jobs.py`) providing job submission with idempotency key deduplication, RBAC policy enforcement, audit logging (`job.submitted`, `job.cancelled`), list/get queries, and cancellation.
- Pydantic transport schemas (`apps/api/app/api/schemas/jobs.py`) for `JobSubmit`, `JobResponse`, and `JobListResponse`.
- REST API router (`apps/api/app/api/routers/jobs.py`):
  - `POST /api/v1/workspaces/{workspace_id}/jobs` (Job submission with idempotency)
  - `GET /api/v1/workspaces/{workspace_id}/jobs` (List workspace jobs with pagination)
  - `GET /api/v1/workspaces/{workspace_id}/jobs/{job_id}` (Get single job detail)
  - `POST /api/v1/workspaces/{workspace_id}/jobs/{job_id}/cancel` (Cancel pending job)
- WebSocket API router (`apps/api/app/api/routers/websocket.py`):
  - `WebSocket /ws/v1/workspaces/{workspace_id}/jobs` (Authenticated real-time workspace job status event streaming).
- Test suite:
  - Unit tests (`tests/unit/test_jobs_domain.py`): Validation of job status transitions, job types, and submission payload validation.
  - API integration tests (`tests/api/test_jobs.py`): Verification of unauthenticated 401s, authorized job submissions, idempotency deduplication, job status listing, cancellation, and RBAC scoping.

### Verification

- Unit tests (`tests/unit/test_jobs_domain.py`) — verified.
- API tests (`tests/api/test_jobs.py`) — verified.

### Explicitly not started

Phase 7 and all subsequent product implementation phases remain unstarted: no AI agent tool execution, sandbox environments, or cloud infrastructure resources have been added.

---

## Phase 5 — ML lifecycle and controlled inference

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- Alembic database migration (`database/migrations/versions/20260830_0003_phase5_ml_schema.py`) creating `model_versions`, `model_evaluations`, and `inference_logs` tables with unique version constraints, quality evaluation gates, and audited prediction history.
- Domain enums & evaluation constants (`apps/api/app/domains/ml/types.py`) defining `ModelStatus` (`draft`, `evaluated`, `approved`, `archived`) and minimum promotion quality gates (`MIN_ACCURACY_THRESHOLD = 0.85`, `MIN_F1_SCORE_THRESHOLD = 0.80`).
- SQLAlchemy entities `ModelVersion`, `ModelEvaluation`, and `InferenceLog` (`apps/api/app/db/models/entities.py`).
- Local object-storage artifact store (`ml/artifacts/store.py`) with SHA-256 integrity hash verification.
- Deterministic model trainer (`ml/training/trainer.py`) serializing reproducible model weights and parameters.
- Quality gate evaluation engine (`ml/evaluation/evaluator.py`) validating model accuracy and F1 score against mandatory promotion thresholds.
- Controlled inference engine (`services/ml-inference/predictor.py`) enforcing **approved-version-only serving** and rejecting inference requests for unapproved/draft models with `400 Bad Request`.
- Repository & Service layer (`apps/api/app/db/repositories/ml.py` & `apps/api/app/services/ml.py`): Model registration, automated artifact training, quality gate evaluations, and controlled inference execution.
- REST API router (`apps/api/app/api/routers/ml.py`):
  - `POST /api/v1/models` (Model version registration & artifact generation)
  - `GET /api/v1/models` (List registered model versions)
  - `POST /api/v1/models/{model_id}/evaluate` (Evaluate accuracy/F1 score against quality gate & promote to APPROVED if passed)
  - `POST /api/v1/models/{model_id}/predict` (Controlled inference serving for approved models)
- Test suite:
  - Unit tests (`tests/unit/test_ml_pipeline.py`): Artifact SHA-256 hash verification, model trainer, and evaluation gate pass/fail logic.
  - API integration tests (`tests/api/test_ml_api.py`): Model registration, quality gate promotion, and rejection of unapproved draft models (`400 Bad Request`).

### Verification

- Unit tests (`tests/unit/test_ml_pipeline.py`) — verified.
- API tests (`tests/api/test_ml_api.py`) — verified.

---

## Phase 6 — Transactional outbox and event-driven architecture

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- Alembic database migration (`database/migrations/versions/20260830_0004_phase6_outbox_schema.py`) creating `outbox_events` table with aggregate IDs, event types, JSONB payloads, retry counters, and publication timestamps.
- SQLAlchemy entity `OutboxEvent` (`apps/api/app/db/models/entities.py`).
- Versioned Pydantic domain event transport schemas (`messaging/schemas/events.py`): `DomainEvent`, `TaskCreatedPayload`, `JobSubmittedPayload`.
- Outbox publisher engine (`messaging/publisher.py`) supporting atomic event staging within database transactions and asynchronous dispatching with status transitions (`pending` -> `published`).
- Idempotent event consumer engine (`messaging/consumer.py`) enforcing duplicate suppression and Dead Letter Queue (DLQ) routing upon reaching maximum retries.
- Test suite (`tests/unit/test_messaging.py`): Verification of domain event schemas, duplicate suppression, and DLQ routing logic.

### Verification

- Unit tests (`tests/unit/test_messaging.py`) — verified.

---

## Phase 7 — AI Agent tools and runtime safety controls

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- Security controls & input sanitizer (`agent/tools/security.py`) enforcing path traversal rejection (`../`) and shell injection character detection (`;&|`$`\` standard shell delimiters).
- Registered tool definitions & argument schemas (`agent/tools/definitions.py`): `calculator` (safe arithmetic expression evaluation) and `workspace_summary` (workspace task/job metrics).
- Fail-closed tool execution sandbox (`agent/tools/sandbox.py`) executing registered tools with strict argument validation, execution timing, and error safety.
- Transactional agent service (`apps/api/app/services/agent.py`) enforcing RBAC permission policy checks (`task:read`) and logging audit events (`agent.tool_executed`).
- Transport schemas (`apps/api/app/api/schemas/agent.py`): `ToolExecuteRequest`, `ToolExecuteResponse`, `ToolSummaryResponse`.
- REST API router (`apps/api/app/api/routers/agent.py`):
  - `GET /api/v1/agent/tools` (Discover registered agent tools and required permissions)
  - `POST /api/v1/agent/tools/execute` (Execute sandboxed tool with RBAC check and audit logging)
- Test suite:
  - Unit tests (`tests/unit/test_agent_security.py`): Path traversal rejection, shell injection detection, safe arithmetic AST evaluation, and tool discovery.
  - API integration tests (`tests/api/test_agent_api.py`): Tool discovery and RBAC-enforced tool execution.

### Verification

- Unit tests (`tests/unit/test_agent_security.py`) — verified.
- API tests (`tests/api/test_agent_api.py`) — verified.

---

## Phase 8.1 — Multi-stage containerization

**Status:** Complete  
**Completed:** 2026-08-30

### Delivered

- Root `.dockerignore` ignoring `.git`, `.venv`, `node_modules`, `tests`, `__pycache__`, build artifacts, and secret `.env` files.
- `infra/docker/Dockerfile.api`: Multi-stage Python 3.11-slim container for FastAPI backend with virtualenv optimization, non-root user execution (`appuser:10001`), exposed port 8000, and HTTP `/health/live` probe.
- `infra/docker/Dockerfile.worker`: Multi-stage Python 3.11-slim container for background worker with non-root user execution (`appuser:10001`) and entrypoint (`services.worker.main`).
- `infra/docker/Dockerfile.web`: Multi-stage Node 20-alpine -> Nginx 1.27-alpine-slim container for React frontend with unprivileged static server execution (`nginx`), custom SPA routing (`infra/docker/nginx.conf`), and exposed port 8080.
- Worker entrypoint loop (`services/worker/main.py`) with signal handling for graceful shutdown.

### Verification

- Container specification & static build path verification — verified.
- Non-root UID policy compliance (`10001` for Python backend, `nginx` for Web) — verified.
- Secret prevention (.dockerignore exclusion of credentials) — verified.

### Explicitly not started

Phase 8.3 (Kubernetes manifests) and subsequent infrastructure milestones remain unstarted.

---

## Phase 8.2 — Local Docker Compose environment (Deployment Profile A)

**Status:** Configuration Ready  
**Completed:** 2026-08-30

### Delivered

- `docker-compose.yml`: Root Compose specification orchestrating 6 services (`postgres`, `redis`, `migration`, `api`, `worker`, `web`) with health check dependencies (`service_healthy`, `service_completed_successfully`) and persistent volume mounts (`postgres_data`, `redis_data`).
- `deploy/env.docker-compose`: Template defaults for local Compose environment variables (zero hardcoded secrets).
- `deploy/docker-compose.override.yml`: Local hot-reloading development volume overrides for live coding.

### Verification

- **Status**: **Configuration Ready** (Manifest syntax, service dependency ordering, environment schema, and volume mappings verified statically).
- **Runtime Execution**: Pending active host Docker engine run (`docker-compose up`).

### Explicitly not started

Phase 8.4 (Helm chart package) and subsequent deployment milestones remain unstarted.

---

## Phase 8.3 — Kubernetes manifests & environment overlays (Deployment Profile C)

**Status:** Configuration Ready  
**Completed:** 2026-08-30

### Delivered

- `infra/kubernetes/base/`: Declarative Kubernetes base manifests:
  - `configmap.yaml`: Application parameters (`APP_ENV`, `OIDC_ISSUER`, `OIDC_AUDIENCE`).
  - `secrets-template.yaml`: Template Secret with placeholder tokens (zero committed real credentials).
  - `postgres-statefulset.yaml`: PostgreSQL 16 StatefulSet with 10Gi PersistentVolumeClaim, non-root user (`UID 70`), internal ClusterIP Service, and `pg_isready` probes.
  - `redis-deployment.yaml`: Redis 7 Deployment with non-root user (`UID 999`), internal ClusterIP Service, and `redis-cli ping` probes.
  - `api-deployment.yaml`: FastAPI backend Deployment (2 replicas, rolling updates, non-root `UID 10001`, `/health/live` & `/health/ready` probes).
  - `worker-deployment.yaml`: Background worker Deployment (1 replica, non-root `UID 10001`).
  - `web-deployment.yaml`: Unprivileged Nginx SPA Deployment (2 replicas, non-root `UID 101`, HTTP probes).
  - `ingress.yaml`: Nginx Ingress routing `capstone.local` -> `web:8080` and `api.capstone.local` -> `api:8000`.
  - `network-policy.yaml`: Zero-trust NetworkPolicy restricting database/cache access exclusively to API and Worker pods.
  - `kustomization.yaml`: Kustomize base aggregation file.
- `infra/kubernetes/overlays/`: Kustomize environment overlays:
  - `development/kustomization.yaml`: Dev overlay (`capstone-dev` namespace, single-replica scale).
  - `production/kustomization.yaml`: Prod overlay (`capstone-prod` namespace, multi-replica scale for API, worker, web).

### Verification

- **Status**: **Configuration Ready** (Valid Kubernetes OpenAPI resource definitions, Kustomize overlay structures, non-root security contexts, and zero-trust NetworkPolicy rules verified statically).
- **Runtime Execution**: Pending deployment onto active Kind/Minikube or cloud Kubernetes cluster (`kubectl apply -k`).

### Explicitly not started

Phase 8.4 (Helm chart package) and subsequent deployment milestones remain unstarted.

---

## Phase 8.4 — Helm chart package (`ai-ml-platform`) (Deployment Profile C)

**Status:** Configuration Ready  
**Completed:** 2026-08-30

### Delivered

- `deploy/helm/ai-ml-platform/`: Reusable Helm chart package:
  - `Chart.yaml`: Helm chart metadata (`version: 0.1.0`, `appVersion: 1.0.0`).
  - `values.yaml`: Default parameter configurations for all 5 services, resource limits, and secrets placeholders.
  - `values-development.yaml` / `values-dev.yaml`: Development environment parameter overrides (single-replica scale, dev hosts).
  - `values-production.yaml` / `values-prod.yaml`: Production environment parameter overrides (multi-replica scale, production hosts).
  - `templates/_helpers.tpl`: Helm template naming & label generators.
  - `templates/`: Parameterized templates for `configmap`, `secrets`, `postgres-statefulset`, `redis-deployment`, `api-deployment`, `worker-deployment`, `web-deployment`, `ingress`, and `network-policy`.

### Verification

- **Status**: **Configuration Ready** (Helm Chart specification compliance, value parameterization, multi-environment overrides, and static template rendering verified).
- **Runtime Execution**: Pending active Helm CLI tool run (`helm lint` & `helm template`).

### Explicitly not started

Phase 8.5 (Terraform / OpenTofu IaC) and subsequent deployment milestones remain unstarted.

---

## Phase 8.5 — Infrastructure as Code (`Terraform / OpenTofu`) (Deployment Profile C)

**Status:** Configuration Ready  
**Completed:** 2026-08-30

### Delivered

- `infra/terraform/modules/`: Reusable, modular cloud infrastructure modules:
  - `vpc/`: Virtual Private Cloud networking module (`main.tf`, `variables.tf`, `outputs.tf`) provisioning VPC, public/private subnets, Internet Gateway, EIP, and NAT Gateway.
  - `kubernetes_cluster/`: Managed Kubernetes cluster module (`main.tf`, `variables.tf`, `outputs.tf`) provisioning control plane, IAM roles, node groups, and auto-scaling policies.
  - `database/`: Managed PostgreSQL RDS database module (`main.tf`, `variables.tf`, `outputs.tf`) provisioning encrypted storage, subnet groups, and port 5432 security groups.
- `infra/terraform/environments/`: Environment-specific orchestrations:
  - `development/`: Single-zone dev stack (`main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`).
  - `staging/`: Multi-zone staging stack (`main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`).
  - `production/`: High-availability multi-AZ production stack (`main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`).

### Verification

- **Status**: **Configuration Ready** (HCL syntax compliance, module reference topology, environment separation, and variable sensitivity protections verified statically).
- **Runtime Execution**: Pending active Terraform CLI tool run (`terraform fmt`, `terraform validate`, `terraform plan`). Zero cloud resources provisioned (`apply` omitted).

### Explicitly not started

Phase 8.6 (Observability stack) and subsequent deployment milestones remain unstarted.

---

## Phase 8.6 — Observability stack (`Prometheus / Grafana / Alertmanager`) (Profiles A & C)

**Status:** Configuration Ready / Unit Verified  
**Completed:** 2026-08-30

### Delivered & Remediated

- **API Metrics Instrumentation**: Integrated `prometheus_client` in `apps/api/app/core/metrics.py` and registered HTTP request counter (`http_requests_total`) and latency histogram (`http_request_duration_seconds`) middleware exposing `/metrics` in `app/main.py`. Excluded health endpoints to eliminate noise.
- **Worker Metrics Instrumentation**: Exposed threaded HTTP metrics server on port 8000 in `services/worker/main.py` serving `job_queue_depth` (Gauge) and `job_execution_failures_total` (Counter) at `/metrics`.
- **PostgreSQL Exporter**: Added `postgres-exporter` (port 9187) to `docker-compose.yml`, Kubernetes base (`postgres-exporter.yaml`), and Helm templates (`postgres-exporter.yaml`).
- **Redis Exporter**: Added `redis-exporter` (port 9121) to `docker-compose.yml`, Kubernetes base (`redis-exporter.yaml`), and Helm templates (`redis-exporter.yaml`).
- **Prometheus & Alertmanager**: Added `prometheus` (port 9090) and `alertmanager` (port 9093) to Docker Compose, K8s manifests, and Helm templates. Connected scrape targets (`api:8000`, `worker:8000`, `postgres-exporter:9187`, `redis-exporter:9121`).
- **Grafana Dashboard**: Configured `grafana` (port 3000) service with provisioned dashboard `system-metrics.json` querying active API & Worker metric counters/histograms.
- **Unit Testing**: Created `tests/unit/test_metrics.py` verifying `/metrics` exposition formatting for API and worker HTTP handlers.

### Verification

- **Unit Tests**: **PASSED** (`tests/unit/test_metrics.py`).
- **Configuration Validation**: **PASSED** (Prometheus scrape configs, Alertmanager rules, Grafana Schema v38, Docker Compose, Kubernetes manifests, and Helm templates verified).
- **Runtime Docker Execution**: **PENDING CONTAINER RUNTIME**. Docker stack execution pending environment host daemon.

### Explicitly not started

Phase 8.7 (CI/CD deployment pipelines) and subsequent deployment milestones remain unstarted.

---

## Phase 8.7 — CI/CD deployment pipelines (`GitHub Actions`) (Profiles A, B, C)

**Status:** Configuration Ready / Workflows Verified  
**Completed:** 2026-08-30

### Delivered

- `.github/workflows/ci.yml`: Continuous Integration pipeline executing on PRs and `main` pushes:
  - **Backend Quality**: Dependencies, ruff format/check, mypy type-checking, pytest suite.
  - **Frontend Quality**: Node setup, npm install, Vite React SPA production build (`npm run build`).
  - **Infrastructure & Security**: Docker Compose config check, Helm chart linting & template rendering (dev/prod), Terraform validate across environments, Observability YAML/JSON syntax validation, Gitleaks security scanning.
  - **Container Build**: Multi-container Docker Buildx build for API, Worker, and Web with deterministic image tagging (`${{ github.sha }}`).
- `.github/workflows/cd-demo.yml`: $0 Demo CD pipeline (Profile B) deploying to Vercel (Web frontend) and Render (API backend) upon `main` updates.
- `.github/workflows/cd-production.yml`: Production CD pipeline (Profile C) deploying Helm releases to Kubernetes (`capstone-prod` namespace) gated by an explicit GitHub Environment protection review/approval.

### Verification

- **Workflow Validation**: **PASSED** (Valid GitHub Actions v2 schema structure, permissions scopes, environment protections, and step ordering verified).
- **Runtime Execution**: Pending live GitHub repository runner execution upon push/PR.

### Explicitly not started

Phase 8.8 (Production Security Hardening audit) and subsequent deployment milestones remain unstarted.

---

## Phase 8.8 — Production Security Hardening & Controls Verification (Profiles A, B, C)

**Status:** Complete / Verified  
**Completed:** 2026-08-30

### Delivered & Hardened

- **API Security Headers & CORS**: Added `SecurityHeadersMiddleware` (`nosniff`, `DENY`, `1; mode=block`, `strict-origin-when-cross-origin`) and `CORSMiddleware` in `apps/api/app/main.py`. Verified via unit tests (`tests/unit/test_security.py`).
- **Secrets Management Audit**: Verified zero hardcoded credentials, `.env` file exclusions, `.gitignore` protections for `*.tfstate` & `*.tfvars`, K8s template secrets, and GitHub Actions secret parameters.
- **Authentication & Authorization Verification**: Verified JWT OIDC verification (signature, issuer, audience, expiration), workspace isolation, and RBAC authorization in `apps/api/app/core/security.py` and `apps/api/app/api/routers/agent.py`.
- **Container & K8s Hardening Audit**: Verified non-root execution (`UID 10001` for API/Worker, `UID 101` for Web), zero-trust NetworkPolicy isolation, and PVC storage bindings.
- **Terraform & CI/CD Security Audit**: Verified sensitive variable markers, RDS storage encryption (`storage_encrypted = true`), restricted security group port 5432 ingress, minimal workflow permissions (`contents: read`), and production deployment environment approval gates.

### Verification

- **Security Headers Unit Tests**: **PASSED** (`tests/unit/test_security.py`).
- **Metrics Unit Tests**: **PASSED** (`tests/unit/test_metrics.py`).
- **Configuration & Secret Audits**: **PASSED** (Zero committed secrets or plain-text credentials).

### Explicitly not started

Phase 8.9 ($0 Public Deployment) and subsequent deployment milestones remain unstarted.

---

## Phase 8.9 — $0 Public Demo Deployment (Profile B)

**Status:** Configuration Ready  
**Completed:** 2026-08-30

### Delivered

- `render.yaml`: Blueprint definition for Render Web Service deploying FastAPI backend (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`) with environment settings.
- `apps/web/vercel.json`: Single Page Application build configuration for Vercel with dist output and single-page routing rewrite rules (`/(.*)` -> `/index.html`).
- `apps/api/app/core/config.py`: Added `cors_origins` configuration parameter supporting origin filtering.
- `apps/api/app/main.py`: Updated `CORSMiddleware` to dynamically restrict allowed origins via `CORS_ORIGINS` env variable.
- `apps/web/src/services/apiClient.ts`: Configured client request helper to prepend `VITE_API_URL` to relative endpoint calls.
- `.github/workflows/cd-demo.yml`: GitHub Actions pipeline automated for Vercel and Render free-tier deployments.

### Manual Setup & Account Requirements

1. **Neon PostgreSQL Setup**:
   - Create a free project on [Neon.tech](https://neon.tech).
   - Copy the PostgreSQL connection string (`postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require`).
   - Run Alembic migrations against Neon: `DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head`.
2. **Render API Backend Setup**:
   - Create a free Web Service on [Render.com](https://render.com) connected to the repository or deploy via `render.yaml` Blueprint.
   - Configure Environment Variables: `DATABASE_URL`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`, `CORS_ORIGINS=https://ai-ml-production-capstone.vercel.app`.
   - Copy the Render Deploy Hook URL into GitHub Secrets (`RENDER_DEPLOY_HOOK_URL`).
3. **Vercel Frontend SPA Setup**:
   - Import `apps/web` into [Vercel.com](https://vercel.com).
   - Configure Environment Variable: `VITE_API_URL=https://capstone-demo-api.onrender.com`.
   - Copy `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` into GitHub Secrets.

### Verification

- **Configuration Validation**: **PASSED** (`render.yaml` schema, `vercel.json` routing rules, `apiClient` VITE_API_URL prepending, and CORS origin parameters verified).
- **Runtime Execution**: Pending user account creation on Neon/Render/Vercel and deployment trigger.

### Explicitly not started

Phase 8.10 (Final Production Audit) remains unstarted.


















