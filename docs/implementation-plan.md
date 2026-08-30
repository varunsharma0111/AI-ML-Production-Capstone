# Complete Implementation Roadmap

## Governing principles

This roadmap implements the approved modular-monolith architecture and ADRs. It starts local-first, preserves PostgreSQL as the system of record, and keeps the $0 public demo deliberately smaller than the complete local and paid-production profiles. A phase is complete only after its acceptance criteria, quality checks, documentation update, review, and Git checkpoint pass. No phase introduces a technology whose workload is not present.

## Dependency map

```text
Phase 1 Foundation
  → Phase 2 Secure API and PostgreSQL vertical slice
    → Phase 3 React client and OIDC browser flow
      → Phase 4 Durable asynchronous jobs and real-time notifications
        → Phase 5 ML lifecycle and controlled inference
          → Phase 6 Transactional outbox and Kafka events
            → Phase 7 Governed agent tools and safety evaluation
              → Phase 8 Delivery, observability, and production hardening
```

Phases 4–7 require a demonstrated use case from prior phases. Phase 8 packages and operates the services already justified; it does not invent additional product scope.

## Phase 1 — Engineering foundation

**Status:** Complete.

- **Objective/features:** repository conventions, local quality guidance, formatting/lint/type/test tooling, CI hygiene.
- **Dependencies:** Python quality tools only.
- **Files/modules:** root quality configuration, CI workflow, contributor/development documentation, foundation tests.
- **Database/APIs/security:** none; ignore rules protect common secrets and artifacts.
- **Tests:** Ruff, mypy, pytest foundation checks, pre-commit, TOML/YAML parsing.
- **Definition of done:** all checks pass and no application implementation exists.

## Phase 2 — Secure FastAPI and PostgreSQL vertical slice

**Status:** In progress.

- **Objective/features:** FastAPI modular monolith; PostgreSQL schema/migrations; OIDC JWT resource-server verification; workspace RBAC; audited task create/list/read/update; health endpoints; safe errors and structured logs.
- **Dependencies:** FastAPI, SQLAlchemy async + asyncpg, Alembic, Pydantic Settings, PyJWT cryptography, HTTP test client, pytest-asyncio. No Redis, Kafka, worker, MongoDB, frontend, or container orchestration.
- **Files/modules:** `apps/api/app/{api,core,db,domains,services}`, `database/migrations`, `tests/{unit,integration,api}`, `.env.example`, CI PostgreSQL service configuration.
- **Database:** `users`, `workspaces`, `workspace_memberships`, `tasks`, `audit_events`; initial Alembic revision only.
- **APIs:** `GET /health/live`, `GET /health/ready`, `GET /api/v1/me`, and workspace-scoped task create/list/read/update routes.
- **Security:** issuer-agnostic JWKS JWT verification; strict issuer/audience/expiry/algorithm validation; local roles `owner`, `editor`, `viewer`; safe problem responses; request IDs; secret redaction.
- **Tests:** unit policy/security/schema tests; migration test against PostgreSQL; API authorization and cross-workspace integration tests; audit-transaction test.
- **Acceptance criteria / definition of done:** migration runs on clean PostgreSQL; invalid/absent JWTs yield 401; non-members/unauthorized roles yield 403; mutations are workspace-scoped and auditable; all Phase 1 + Phase 2 checks pass; Git commit created.

## Phase 3 — React client and browser authentication

**Status:** Blocked pending identity-provider decision when implementation begins.

- **Objective/features:** React + TypeScript application; protected task workflow; typed API client; OIDC Authorization Code + PKCE; accessible error/loading states.
- **Dependencies:** React, TypeScript, Vite, a minimal client-side query/state library only if native React state is insufficient, and a provider-supported OIDC client. Selection must be compatible with the free-demo profile.
- **Files/modules:** `apps/web`, frontend tests, shared API-contract generation/type definitions only if justified.
- **Database/APIs:** consume Phase 2 APIs; no schema change expected.
- **Security:** never expose client secrets; no tokens in URLs/logs; configured origins; secure production session/token handling consistent with ADR 0004.
- **Tests:** component tests, accessibility checks, API-client contract tests, browser end-to-end task workflow.
- **Acceptance criteria / definition of done:** authenticated user sees only authorized workspace task data; browser E2E passes; no custom password/token issuer exists; Git commit created.

## Phase 4 — Durable asynchronous jobs and real-time status

**Status:** Pending.

- **Objective/features:** job state, bounded task queue/worker, retries/idempotency, Redis-backed ephemeral coordination, authenticated WebSocket status notification with REST reconciliation.
- **Dependencies:** Redis and one task-queue library selected for Python/FastAPI compatibility. No Kafka yet.
- **Files/modules:** `services/worker`, task/job domain modules, Redis configuration, WebSocket router, job tests.
- **Database:** `jobs`, `job_attempts`, and durable job state; no outbox publisher until Phase 6.
- **APIs:** job submission/query endpoints; authorized WebSocket job channels.
- **Security:** queue payload minimization, scoped job access, idempotency keys, message validation.
- **Tests:** retry, restart, cancellation, authorization, Redis-loss/degradation, reconnect/reconciliation tests.
- **Acceptance criteria / definition of done:** durable job intent survives API restart; retries are bounded/observable; browser recovery uses REST; all checks pass; Git commit created.

## Phase 5 — ML lifecycle and controlled inference

**Status:** Blocked pending first ML use-case, dataset, evaluation thresholds, and artifact-store decision.

- **Objective/features:** reproducible training, versioned artifacts, model registry metadata, evaluation gates, approved model inference.
- **Dependencies:** select only libraries required by the approved ML problem; object-storage-compatible local artifact store; no GPU requirement unless justified by the use case.
- **Files/modules:** `ml/{training,evaluation,experiments}`, `services/ml-inference`, model registry API/domain modules.
- **Database:** model versions, evaluations, promotion records, artifact references.
- **APIs:** model metadata and controlled inference request/result contracts.
- **Security:** approved-version-only serving, input limits, artifact integrity, sensitive-data minimization.
- **Tests:** training reproducibility, evaluation threshold regression, version pinning, inference schema/latency tests.
- **Acceptance criteria / definition of done:** only approved models serve; every prediction is versioned; failed evaluation blocks promotion; all checks pass; Git commit created.

## Phase 6 — Transactional outbox and Kafka events

**Status:** Pending; depends on proven async and ML event consumers.

- **Objective/features:** transactional outbox, versioned event schemas, Kafka publisher/consumers, replay and dead-letter procedures.
- **Dependencies:** Kafka only after Phase 4/5 generate durable event consumers.
- **Files/modules:** `messaging/schemas`, outbox publisher, Kafka consumer modules, event runbook.
- **Database:** `outbox_events`, processed-event idempotency records as needed.
- **APIs:** no public API required beyond existing lifecycle visibility.
- **Security:** minimal event payloads, tenant scope, correlation IDs, no credentials/PII in topics.
- **Tests:** commit-to-publish recovery, duplicate delivery, replay, schema compatibility, dead-letter routing.
- **Acceptance criteria / definition of done:** no dual-write loss; consumers are idempotent; replay is safe; all checks pass; Git commit created.

## Phase 7 — Governed AI agent tools and safety evaluation

**Status:** Blocked pending LLM/provider, approved tool set, data-retention policy, and human-approval policy.

- **Objective/features:** narrow agent workflow with typed internal tools, explicit policy checks, approval gates, evaluation cases, budgets, and audit trail.
- **Dependencies:** one approved model provider or local model runtime; no arbitrary code, shell, or database tools.
- **Files/modules:** agent orchestrator, typed tool adapters, policy/approval domain modules, safety evaluations.
- **Database:** agent runs, tool calls, approval decisions, bounded/redacted audit metadata.
- **APIs:** agent task lifecycle and approval endpoints built on Phase 4 jobs.
- **Security:** role/scope checks per tool call, allowlist, schema validation, rate/cost/iteration limits, redaction and retention controls.
- **Tests:** permission denial, approval gate, tool-schema validation, loop limits, safety benchmark cases.
- **Acceptance criteria / definition of done:** agent cannot exceed a user's authority; consequential actions require approval; every run is auditable; all checks pass; Git commit created.

## Phase 8 — Delivery, observability, and production hardening

**Status:** Pending; depends on implemented workloads.

- **Objective/features:** Docker images, complete local Docker Compose, Kind/Minikube Helm demonstration, CI/CD promotion gates, Terraform for chosen paid provider, OpenTelemetry, dashboards, alerts, backups, scans, load tests, and runbooks.
- **Dependencies:** Docker, Kubernetes/Helm, Terraform, cloud provider, managed service choices, telemetry backend. Cloud/provider and billing choices require approval before implementation.
- **Files/modules:** `infra/{docker,kubernetes,terraform,observability}`, `deploy/helm`, CI deployment workflows, runbooks.
- **Database:** backup/restore and migration-release procedures; no unreviewed destructive migration.
- **APIs:** deployment health/readiness and operational endpoints only.
- **Security:** image/dependency scanning, managed secrets, least-privilege service identities, TLS, network boundaries, release approvals.
- **Tests:** image build, Compose integration, Helm/Kubernetes smoke tests, migration/rollback exercise, load/security checks, alert/runbook drill.
- **Acceptance criteria / definition of done:** complete stack works locally; bounded demo deploys to Vercel/Render/Neon; full target is declarative and observable; rollback/runbooks exercised; all checks pass; Git commit created.

## Deployment profile controls

| Profile | Allowed scope |
|---|---|
| Local | Complete services only after their respective phases; Docker Compose is Phase 8. |
| Free public demo | Vercel web + one stateless Render API + Neon PostgreSQL; no worker, Redis dependency, Kafka, hosted inference, or Kubernetes. |
| Full production | Paid managed PostgreSQL/Redis/Kafka/object store with Kubernetes/Helm/Terraform only in Phase 8. |

## Risks and approval gates

- **Identity provider:** Phase 2 remains issuer-agnostic; Phase 3 requires a provider and claim/session decision.
- **ML use case/data/evaluation:** Phase 5 cannot proceed without a concrete problem, lawful dataset, metrics, thresholds, and artifact-store choice.
- **LLM/agent provider and retention:** Phase 7 cannot proceed without approval of tool authority, data handling, and provider/cost model.
- **Cloud/billing:** Phase 8 requires the selected paid production cloud and secret-management approach.
- **Database evolution:** destructive migrations, retention changes, and privacy-sensitive data require explicit review.
- **Free-tier drift:** provider limits must be revalidated immediately before public deployment.
