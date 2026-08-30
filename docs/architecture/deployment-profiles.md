# Deployment Profiles

## Principle

The platform remains production-grade in its boundaries, contracts, security controls, and operational design, but its deployment footprint matches the goal. The public $0 demo proves a secure vertical slice; it does not pretend to provide production durability or availability. Features absent from that profile are disabled with clear UI/API capability configuration—not replaced with fake implementations.

## 1. Local development architecture

Docker Compose runs the complete stack on a developer machine:

```text
React web → FastAPI modular monolith → PostgreSQL
                                  ├→ Redis → worker/task queue
                                  ├→ Kafka → event consumers
                                  └→ ML inference → local object storage
```

- Use Docker volumes for locally durable database, queue, and artifact state.
- Run training, evaluation, agents, workers, Kafka, and inference here, with resource limits appropriate to the laptop.
- Use Kind or Minikube plus Helm to demonstrate Kubernetes manifests, configuration, probes, rollouts, and service networking without cloud cost.
- This is the source of truth for integration, resilience, load, and end-to-end testing of the complete platform.

## 2. Free public demo architecture

```text
Browser → Vercel static React app → Render FastAPI web service → Neon PostgreSQL
                                      └→ configured OAuth/OIDC provider
GitHub → Actions (quality gates) → Vercel / Render deployment
```

### Included scope

- A small authenticated REST vertical slice: identity, authorization, one or more bounded task workflows, audit records, and read/write PostgreSQL state.
- A static React application on Vercel Hobby, appropriate for personal/non-commercial usage and its documented resource limits.
- One stateless FastAPI web service on Render Free, accepting that it sleeps after inactivity and may restart.
- Neon Free PostgreSQL for low-volume persistent state.
- GitHub repository, pull-request checks, and deployment automation.
- WebSockets only as a progressive enhancement. The client must reconcile state by REST after reconnect/cold start and function without a continuous connection.

### Excluded scope

- Kafka, Redis, background workers, schedulers, persistent queues, and hosted model-inference services.
- Training jobs, GPU workloads, large artifact storage, production observability backends, multi-replica availability, and uptime/SLO commitments.
- Any workflow whose correctness depends on a process remaining alive after an HTTP response. Such workflow is local/full-production only.

### Operating constraints

Render Free web services spin down after 15 minutes without inbound traffic, can restart, have ephemeral filesystems, and do not support free worker services or multi-instance scaling. The demo therefore treats the API as stateless and stores durable state only in Neon. Vercel Hobby is for personal/non-commercial work and has usage limits. Neon Free has capacity/usage limits and a limited restore window. These plans must be rechecked before launch because providers change free-tier terms.

The API base URL, enabled capabilities, OIDC configuration, and observability exporters are environment configuration—not frontend code forks. Public-demo secrets are configured in Vercel/Render/GitHub settings. The demo never exposes database credentials to the browser.

## 3. Full production architecture

```text
CD → container registry → Kubernetes/Helm
                         ├→ API replicas and WebSocket-capable ingress
                         ├→ worker replicas and task queue
                         ├→ inference deployment with model artifacts
                         ├→ managed PostgreSQL and Redis
                         ├→ managed Kafka and object storage
                         └→ OpenTelemetry collectors, dashboards, alerts
Terraform → network, cluster prerequisites, managed services, identities, secrets integration
```

- Managed PostgreSQL, Redis, Kafka, and object storage provide durable state and backup/retention controls.
- API, worker, and inference scale independently; Kafka consumers and event outbox support reliable integration.
- Helm releases are promoted through development, staging, and production with controlled migrations and rollback procedures.
- OpenTelemetry, centralized logs, metrics, traces, alerts, vulnerability scans, least-privilege identities, and SLOs are mandatory.

## Provider references

- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby)
- [Render Free deployment limitations](https://render.com/docs/free)
- [Neon pricing and Free plan](https://neon.com/pricing)
