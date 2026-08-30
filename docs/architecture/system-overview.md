# System Overview

## Problem statement

AI-enabled applications often fail to make model use reliable, observable, secure, and governable. This capstone will build a platform that turns a user-submitted AI task into a traceable, permission-checked workflow with versioned model results and real-time status updates.

## Goals

- Deliver a secure web experience for authenticated users to create, run, inspect, and manage AI tasks.
- Demonstrate a maintainable FastAPI modular monolith with separately scalable worker and inference workloads.
- Support repeatable ML training, evaluation, versioning, and controlled promotion to inference.
- Make asynchronous work observable, retryable, and visible through WebSockets.
- Operate locally with Docker Compose first, then deploy the same workloads through Kubernetes, Helm, Terraform, and CI/CD.

## Non-goals

- Building a generic autonomous-agent framework or unrestricted code-execution environment.
- Starting with microservices, multi-region availability, or a self-managed data platform.
- Using MongoDB, Kafka, Kubernetes, or Terraform before their concrete workload and deployment stages require them.
- Training foundation models or handling unbounded public data ingestion.

## Major components and responsibilities

| Component | Responsibility |
|---|---|
| React web app | User workflows, client-side session handling, REST calls, WebSocket status display. |
| FastAPI application | REST/WebSocket boundary, authentication, authorization, domain rules, audit records, and transactions. |
| PostgreSQL | Authoritative users, roles, tasks, job state, agent approvals, audit trail, model registry metadata. |
| Redis | Cache-aside reads, rate-limit counters, idempotency/short-lived coordination, and task-queue broker/result support. |
| Worker | Executes bounded asynchronous jobs, retries safely, emits lifecycle events, and invokes inference. |
| Inference service | Loads an approved model version, validates inputs, runs predictions, records model metadata. |
| Kafka | Durable domain-event stream for job lifecycle, audit/analytics consumers, and replayable integration events. |
| ML lifecycle | Training, offline evaluation, experiment tracking, artifact storage, and promotion decisions. |
| Agent/tool layer | Plans constrained tool calls, checks permissions and policy, requires approval where needed, audits every call. |

## Data flow

The API persists authoritative state in PostgreSQL. It uses Redis only for rebuildable or short-lived state. A committed domain change is recorded with an outbox row in the same database transaction; a publisher relays that row to Kafka. Consumers remain idempotent. Large datasets and model artifacts are stored outside Git in an object-storage-compatible location, while PostgreSQL stores pointers and version metadata.

## Request flow

1. The web app obtains an OIDC-authenticated session and sends an access token to the API.
2. FastAPI validates token claims, resolves roles and permissions, validates the request, and starts a trace.
3. The relevant domain module reads or writes PostgreSQL, optionally using a cache-aside Redis lookup for safe read models.
4. Commands requiring long-running work create a job and outbox event transactionally, then return `202 Accepted` with a job identifier.
5. The client receives job updates through an authenticated WebSocket channel or fetches job state through REST.

## AI/ML flow

Offline pipelines curate data, train candidate models, and run reproducible evaluation for quality, safety, latency, and cost. Evaluation results and artifact references are recorded in a model registry. An authorized approver promotes a version to a deployment stage. The inference service serves only approved versions, logs model/version metadata, and sends non-sensitive telemetry for monitoring and later evaluation.

## Asynchronous processing flow

A durable job record is created before queueing. A worker claims the job, records attempts and progress, calls the inference or approved tool endpoint, and marks the job terminally succeeded, failed, or cancelled. Retries use exponential backoff and idempotency keys; failed jobs go to a reviewable dead-letter path. Job-state changes are published as domain events and WebSocket notifications.

## Real-time communication flow

The browser opens a token-authenticated WebSocket to FastAPI. Each connection is associated with a user and permitted workspace/task scope. The API subscribes only to authorized job notifications, fan-outs updates from the event consumer, and supports reconnect plus REST state reconciliation. WebSockets are notifications, not the source of truth.

## Deployment profiles

The architecture has three profiles with the same domain contracts but different operational scopes:

| Profile | Purpose | Included components | Explicitly excluded or constrained |
|---|---|---|---|
| Local development | Complete engineering and demonstration environment. | Docker Compose: web, API, PostgreSQL, Redis, worker, inference, Kafka, and local object storage; Kind or Minikube for Kubernetes demonstrations. | Not publicly exposed or highly available. |
| Free public demo | A small, safe, portfolio-accessible vertical slice. | Vercel static React client, one Render FastAPI web service, Neon PostgreSQL, GitHub repository/actions, and a free-compatible OIDC provider. | No persistent worker, Kafka, Redis dependency, Kubernetes, or heavyweight hosted inference. WebSockets are best-effort; REST polling/reconciliation is required. |
| Full production | Scalable, durable operation. | Containers, managed PostgreSQL/Redis/Kafka/object storage, worker and inference deployments, Kubernetes/Helm, Terraform, CI/CD, full telemetry. | Requires paid infrastructure and defined SLOs. |

The free demo is not labelled production. It may cold-start, restart, and have constrained resource and usage limits. Durable work and model training/inference are demonstrated locally or in the full-production profile rather than forced onto unsuitable free services.
