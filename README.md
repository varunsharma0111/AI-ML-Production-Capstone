# AI/ML Production Capstone

## Vision

Build a realistic, local-first AI/ML platform for teams to submit governed AI tasks, receive model-assisted results, and track asynchronous work in real time. It is a B.Tech capstone designed to demonstrate sound AI/ML, backend, frontend, and production-engineering practices without inventing distributed complexity that a small team cannot operate.

## Architecture overview

The initial product is a **modular monolith**: the FastAPI application owns the public REST and WebSocket interfaces, identity enforcement, business workflows, and transactional data. It has explicit modules rather than prematurely split microservices. A background worker and model-inference service are separately deployable because they have different execution and scaling profiles. PostgreSQL is the system of record, Redis provides short-lived cache and task-queue support, and Kafka carries durable domain events once asynchronous integrations need replayable event streams.

AI-agent actions are constrained by user role, explicit tool permissions, validation, audit logging, and approval gates for sensitive operations. Models are trained and evaluated outside the request path, registered as versioned artifacts, and promoted only after evaluation criteria are met.

The project has three intentional deployment profiles: complete local development with Docker Compose; a deliberately limited $0 public demo using Vercel, Render, and Neon; and a full production target using independently scalable services and managed infrastructure. See [deployment profiles](docs/architecture/deployment-profiles.md).

## Technology overview

- Python and FastAPI for the API, domain modules, and ML-adjacent services.
- React and TypeScript for the browser client.
- PostgreSQL for transactional data; Redis for cache, rate limits, and queue coordination.
- Kafka for durable, replayable domain events; a task queue for bounded background execution.
- REST for command/query APIs and WebSockets for authenticated job-status notifications.
- JWT access tokens with OAuth/OIDC login integration, RBAC, and fine-grained permissions.
- Docker for reproducible local environments; Kubernetes, Helm, and Terraform for later production operation.
- OpenTelemetry-based logs, metrics, and traces; automated unit, integration, end-to-end, and performance tests.

MongoDB is deliberately not an initial dependency. PostgreSQL can store structured data and JSONB metadata; MongoDB may be reconsidered only if high-volume, flexible document persistence becomes a demonstrated workload.

## Development phases

The implementation proceeds from foundation and a secure vertical slice to async jobs, ML lifecycle, AI tools, and production hardening. Each stage has independently testable acceptance criteria; see the complete [project phases](docs/architecture/project-phases.md).

## Architecture documentation

- [System overview](docs/architecture/system-overview.md)
- [Detailed architecture](docs/architecture/architecture.md)
- [Data flows](docs/architecture/data-flow.md)
- [Technology decisions](docs/architecture/technology-decisions.md)
- [Deployment profiles](docs/architecture/deployment-profiles.md)
- [Implementation phases](docs/architecture/project-phases.md)
- [Implementation plan](docs/implementation-plan.md)
- [Local development](docs/development/local-development.md)
- [Progress](docs/progress.md)
- [Architecture decisions](docs/adr/)

## Current status

Phase 1 engineering foundation is complete. No product application code, runtime services, database migrations, or infrastructure implementations have been added. Phase 2 begins only after explicit approval.
