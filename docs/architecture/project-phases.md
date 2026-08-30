# Implementation Phases

Each phase is intentionally small enough to demonstrate and test independently. Later phases are not authorization to bypass earlier acceptance criteria.

## 1. Engineering foundation

Set repository conventions, local environment documentation, formatting/linting/test configuration, and CI checks without product features.

**Acceptance criteria:** clean clone instructions work; CI runs formatting, static checks, and a minimal test command; no credentials are committed.

## 2. Secure API vertical slice

Implement the FastAPI modular-monolith skeleton, PostgreSQL migrations, health endpoints, OIDC/JWT validation, local RBAC, audit logging, and one permission-protected task resource.

**Acceptance criteria:** unauthorized and forbidden requests are rejected; authorized CRUD obeys workspace scope; migrations and API integration tests run against PostgreSQL; audit records exist for mutations.

## 3. Web client vertical slice

Implement the React/TypeScript client login flow, protected task view, typed REST client, accessibility baseline, and end-to-end test for the phase-2 resource.

**Acceptance criteria:** a user can sign in, see only permitted data, create/view an allowed task, and receive usable error states; an automated browser test passes.

## 4. Async jobs and real-time status

Add durable job state, a worker/task queue, retries/idempotency, Redis rate limiting/cache-aside for one safe query, and authenticated WebSocket job notifications.

**Acceptance criteria:** a queued job survives API restart; retry behavior is observable and bounded; reconnecting client reconciles final job state; Redis outage degrades safely without data loss.

## 5. ML lifecycle and inference

Create a small, well-defined ML use case; add reproducible training, artifact storage, registry metadata, offline evaluation, approval/promotion, and separately deployable inference.

**Acceptance criteria:** a versioned model can be trained/evaluated, only an approved version serves requests, inference records version/latency, and rejection thresholds prevent promotion.

## 6. Event-driven integration

Introduce transactional outbox publishing, Kafka topics/schemas, idempotent consumers, dead-letter handling, and event traceability.

**Acceptance criteria:** a committed job event is eventually published exactly-at-least-once safely; replay does not corrupt state; failed events are observable and recoverable through a runbook.

## 7. Governed AI agent and tools

Add a narrow agent workflow with typed internal tools, prompt/context controls, permission checks, approval gates, cost/iteration limits, and evaluation cases.

**Acceptance criteria:** the agent cannot call unapproved tools or exceed scope; consequential actions wait for explicit approval; every run is auditable; safety evaluation cases pass.

## 8. Production delivery and observability

Add Docker builds, complete local Compose, a $0 public-demo deployment profile, Kubernetes/Helm manifests for Kind/Minikube, Terraform foundations for paid infrastructure, CI/CD promotion gates, OpenTelemetry, dashboards, alerts, backup/restore checks, security scanning, and load tests.

**Acceptance criteria:** a GitHub-validated change can deploy the bounded frontend/API/PostgreSQL demo to Vercel/Render/Neon; the demo has documented cold-start and feature limitations; the complete stack runs through Docker Compose; the same images deploy to local Kubernetes through Helm; traces connect browser/API/worker/inference locally; dashboards and alerts cover failure modes; rollback, migration, and incident runbooks are exercised.
