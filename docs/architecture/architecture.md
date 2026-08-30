# Detailed Architecture

## Architectural style and service boundaries

The initial deployment contains three workloads: `apps/api` (the modular monolith), `services/worker`, and `services/ml-inference`. The API retains modules for identity, authorization, tasks/jobs, model registry, agent governance, notifications, and audit. Modules communicate in-process through interfaces and domain events; they do not share ad-hoc database access. Extracting a module later requires a demonstrated independent scaling, ownership, or failure-isolation need.

The worker is separate because long-running/retried jobs must not consume API capacity. Inference is separate because it has model-runtime dependencies and scales by prediction load. Kafka consumers may initially run with the worker; they do not become a new service without need.

## Frontend architecture

React + TypeScript is a feature-oriented single-page application. Features own pages, UI state, API clients, and tests; a small shared design system is kept separate. Server state is fetched through typed API clients and reconciled after WebSocket events. Tokens are never exposed in URLs or logs; OIDC uses Authorization Code with PKCE, with the preferred production design using a backend-for-frontend/session approach or secure HttpOnly cookies.

## Backend architecture

FastAPI exposes versioned REST resources for tasks, jobs, models, approvals, and administrative actions. It also hosts WebSocket endpoints for scoped job notifications. Request middleware handles correlation IDs, authentication, authorization context, validation, rate limits, structured logs, and OpenTelemetry spans. Each domain module has API, application/service, domain, and persistence boundaries. Transactions are short; external calls occur after commit through queued work.

## ML architecture

`ml/training` contains reproducible pipelines and configuration; `ml/experiments` contains experiment metadata conventions; `ml/evaluation` owns offline quality, robustness/safety, latency, and cost checks. Artifacts reside in object storage and are immutable/versioned. PostgreSQL records registry metadata, metrics, lineage, promotion stage, and approval. The inference service loads a pinned approved version, validates schema, applies input limits, and reports prediction metrics. Online monitoring detects latency/error and data-quality drift; automatic promotion is out of scope initially.

## AI agent architecture

An agent is an application capability, not a privileged autonomous service. It receives a narrowly defined task, policy-limited context, and a tool allowlist. The orchestrator validates every requested tool action against RBAC permissions, workspace scope, tool schema, rate/cost budgets, and safety rules. Read-only tools may be auto-executed when authorized; state-changing or externally consequential tools require an explicit approval record. All prompts, tool inputs/outputs (redacted as necessary), decisions, model version, and approvals are audit-linked. Tools are internal, typed APIs—never arbitrary shell or database access.

## Database architecture

PostgreSQL is the system of record. Relational tables model identities, memberships, roles, permissions, tasks, jobs, job attempts, model versions, evaluations, approvals, audit events, and outbox events. JSONB is reserved for bounded variable metadata such as model parameters or evaluation details. Foreign keys, unique constraints, optimistic concurrency where needed, tenant/workspace scoping, migrations, backups, and retention policies protect integrity. MongoDB is not used initially: it would duplicate operational cost without a current access-pattern advantage.

## Cache architecture

Redis holds only ephemeral, derivable data: rate-limit counters, short session/authorization lookups if required, idempotency coordination, job-queue coordination, and cache-aside read responses. Keys are namespaced and TTL-bound. Cache misses must be correct; invalidation follows writes or short TTLs. PostgreSQL remains authoritative, and Redis loss must not lose user data or job intent.

## Messaging architecture

The task queue dispatches individual work with retry, visibility, and scheduling semantics. Kafka carries durable domain events for independently consumable job lifecycle, audit, and analytics streams. PostgreSQL's transactional outbox avoids the dual-write problem. Producers attach event version, correlation ID, actor/workspace scope, idempotency key, and minimal non-sensitive payloads. Consumers are idempotent and use dead-letter handling. Kafka is introduced only in the event-driven phase; local work begins with the queue and outbox-compatible schema.

## Deployment architecture

Deployment is profile-based. **Local development** uses Docker Compose for web, API, PostgreSQL, Redis, worker, inference, Kafka, and object-storage emulators. Kind or Minikube deploys the same container images with Helm for Kubernetes demonstrations. **The free public demo** deploys the static React build to Vercel, a single stateless FastAPI web service to Render, and PostgreSQL to Neon. It serves only a bounded synchronous vertical slice; its API must tolerate cold starts and has no dependency on Redis, Kafka, a worker, or a hosted model runtime. **Full production** uses versioned images deployed to Kubernetes with Helm, while Terraform provisions managed data/messaging/object-storage and cluster prerequisites.

The API has deployment-profile configuration, health checks, migrations, and graceful degradation boundaries from the start. Features requiring durable async execution, Kafka consumers, continuous WebSockets, or substantial model resources are feature-flagged or hidden in the free demo, not simulated. GitHub Actions runs tests/builds and deploys the demo only after checks pass. Secrets are supplied by each environment; no secret is committed. Environments progress development → staging → production, with migrations as an explicit, controlled release step.

## Security architecture

An external OAuth/OIDC provider authenticates users; the API verifies JWT issuer, audience, expiry, signature, and scopes. Authorization is enforced server-side at every resource and tool action using RBAC plus permission checks and workspace ownership. TLS, secure cookies, CORS allowlists, input/output validation, rate limiting, secret rotation, dependency/image scanning, least-privilege service accounts, encryption at rest/in transit, audit trails, and retention/redaction controls are baseline requirements. WebSockets undergo the same authentication and authorization controls as REST.

## Observability architecture

Every request, job, event, inference, and tool execution carries a correlation/trace ID. Structured logs use redaction and avoid access tokens, raw secrets, and unnecessary prompt/user content. OpenTelemetry emits traces across API, worker, inference, and messaging. Metrics cover golden signals, queue depth, retry/dead-letter rates, cache behavior, database health, model latency/errors, evaluation quality, and agent tool approval/denial rates. Dashboards and actionable alerts live under `infra/observability`; runbooks document response procedures.
