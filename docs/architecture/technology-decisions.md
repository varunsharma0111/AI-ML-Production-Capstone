# Technology Decisions

| Technology | Why it is needed / problem solved | Alternatives considered | Why not selected initially |
|---|---|---|---|
| Python | Strong ecosystem for ML workflows and productive backend development. | Java, Go. | Both are viable, but add a language boundary without improving the capstone's primary ML work. |
| FastAPI | Typed, validated REST/WebSocket API with async support and Python integration. | Django, Flask. | Django is broader than needed initially; Flask needs more assembly for validation and API conventions. |
| React + TypeScript | Mature interactive client with compile-time API/UI safety. | Vue, Angular. | Viable alternatives, but React has broad ecosystem support and TypeScript meets maintainability goals. |
| PostgreSQL | ACID system of record, relational integrity, JSONB metadata, full-text options, and outbox support. | MySQL, MongoDB. | MySQL offers fewer convenient document/query features; MongoDB weakens relational integrity for the core domain. |
| Redis | Low-latency, TTL-bound cache, rate limiting, and queue coordination. | In-process cache, Memcached. | In-process caches do not coordinate replicas; Memcached lacks useful data structures/queue ecosystem. |
| MongoDB | Deferred; only evaluate for a measured, document-heavy workload with unsuitable PostgreSQL access patterns. | PostgreSQL JSONB. | JSONB is sufficient for bounded flexible metadata and avoids a second database operation burden. |
| REST | Clear resource-oriented browser and integration API. | GraphQL, gRPC-only. | GraphQL adds schema/client complexity; gRPC is unsuitable as the primary browser interface. |
| WebSockets | Authenticated, low-latency job and agent progress notifications. | Polling, server-sent events. | Polling delays updates; SSE is simpler but less flexible for future client messages. |
| OAuth/OIDC + JWT | Delegated identity, standards-based login, and verifiable API credentials. | Homegrown passwords/tokens. | Custom identity is high-risk and distracts from the product. |
| RBAC + permissions | Enforces least privilege for resources and especially AI tools. | Role checks only, ABAC-only. | Role-only becomes coarse; ABAC-only is harder to operate initially. |
| Task queue + worker | Isolates slow/retryable work from request capacity. | In-process background tasks. | In-process tasks do not survive restarts or scale independently. |
| Kafka | Replayable durable events for lifecycle, integration, analytics, and eventual independent consumers. | Redis pub/sub, RabbitMQ only. | Redis pub/sub is not durable; RabbitMQ is excellent for commands but less suited to retained event streams. |
| Docker | Reproducible local services and build artifacts. | Host-only setup. | Host setup causes environment drift. |
| Kubernetes + Helm | Standardized later-stage deployment, scaling, rollout, and config packaging. | Docker Compose only, raw manifests. | Compose is local-first only; raw manifests duplicate environment configuration. |
| Terraform | Versioned cloud and cluster prerequisite provisioning. | ClickOps, Pulumi. | ClickOps is irreproducible; Pulumi is viable but Terraform has broad provider/module conventions. |
| OpenTelemetry | Vendor-neutral traces, metrics, and log correlation. | Vendor SDKs only. | Vendor lock-in and inconsistent instrumentation. |
| Automated testing | Prevents regressions across API, UI, workers, and deployment contracts. | Manual testing only. | Manual-only testing cannot sustain a production-oriented platform. |
| Vercel Hobby for public demo web | Free static React hosting with Git-linked preview/production deployments for a personal capstone. | Render static site, self-hosted frontend. | Vercel is a focused fit for the browser client; it is not used for long-running backend work. |
| Render Free web service for public demo API | Hosts one stateless FastAPI demo API without operating a server. | Serverless functions, self-hosted VM. | The demo needs an ASGI web service; it accepts cold starts and is not used for durable workers. |
| Neon Free PostgreSQL for public demo | Provides a managed PostgreSQL database with a free learning/demo allowance. | Render Free Postgres, local-only database. | Neon is not time-limited like Render's free database, though its capacity and restore window remain constrained. |
| Docker Compose + Kind/Minikube | Runs the complete system and Kubernetes demonstration locally at no cloud cost. | Free managed Kubernetes. | Free managed clusters are not dependable as a permanent demo target and obscure Kubernetes operations. |
