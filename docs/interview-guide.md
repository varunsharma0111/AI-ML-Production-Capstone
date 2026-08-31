# AuraML Technical Interview Preparation Guide

---

## Architecture & System Design Questions

### Q1: Why did you build AuraML as a modular monolith instead of microservices?
**Answer**:
> "Starting with a modular monolith provided strong module boundaries (identity, datasets, training, inference, audit) with clear in-process interfaces without introducing the network latency, operational overhead, and distributed transaction complexity of microservices. The background worker and ML inference engines are isolated processes so they can scale independently based on CPU/GPU demand."

### Q2: How does the asynchronous task architecture work, and how do you handle claim race conditions between worker replicas?
**Answer**:
> "API requests enqueue job IDs into a Redis task queue (`redis.asyncio`) and record the job state as `QUEUED` in PostgreSQL. Worker replicas pull job IDs from Redis and execute an atomic SQL transaction using `SELECT FOR UPDATE / SKIP LOCKED` to lock the job row and immediately update its state to `PROCESSING`. If a job is already claimed by another replica, the query skips it, completely preventing duplicate execution."

### Q3: How do you handle stuck or abandoned background jobs if a worker node crashes mid-execution?
**Answer**:
> "We implemented a 15-minute stuck-job recovery sweeper (`recover_stuck_jobs`). If a job remains in `PROCESSING` status for longer than 15 minutes, the worker checks its `attempt_count`. If `attempt_count < max_retries`, the job is automatically requeued back to `QUEUED`. Otherwise, it is marked `FAILED` with an error event, ensuring jobs never silently vanish."

---

## Security, RBAC & Storage Questions

### Q4: How is tenant workspace isolation enforced across database and storage layers?
**Answer**:
> "Workspace isolation is enforced at every layer. In the database, repository methods require a mandatory `workspace_id` parameter in all `WHERE` clauses. In object storage, object keys are prefixed as `workspaces/{workspace_id}/...`. Attempting to access resources from another workspace returns `HTTP 404 Not Found` to prevent cross-tenant ID enumeration."

### Q5: How do you guarantee that model weight artifacts stored in S3 have not been tampered with or corrupted?
**Answer**:
> "When a model is trained, `ArtifactStore` calculates a SHA-256 digest of the raw JSON payload before saving it to S3. This checksum is saved in the database record. When the model is loaded for inference serving, `ArtifactStore` re-computes the SHA-256 digest on read and compares it to the recorded hash. If there is a mismatch, the inference call fails immediately with `HTTP 400 Bad Request` (`artifact_corrupted`)."

### Q6: Why did you use RS256 for JWT token verification instead of HS256?
**Answer**:
> "RS256 uses asymmetric cryptography (public/private key pair). The identity provider signs tokens using its private key, while our API Gateway verifies tokens using public keys fetched from the OIDC `JWKS` endpoint. This allows the API to verify tokens securely without sharing a symmetric secret key across microservices."

---

## ML Engineering & Reliability Questions

### Q7: What are Quality Gates and why are they necessary before model promotion?
**Answer**:
> "Quality Gates act as automated governance checkpoints. Before a model version can be promoted from `draft` to `approved` or `production`, its evaluation metrics (accuracy, F1 score, precision, recall, latency) are evaluated against pre-defined workspace thresholds. This prevents substandard models from serving production traffic."

### Q8: How does the AI Platform Agent interact with the platform safely?
**Answer**:
> "The AI Agent is tool-augmented and strictly constrained. It can only execute explicit Python tools (e.g. `get_dataset_summary`, `evaluate_model`) that inherit the calling user's principal and RBAC permissions. All agent actions and tool invocations generate structured audit events."

---

## Failure Recovery & Observability Questions

### Q9: What happens if Redis is unavailable?
**Answer**:
> "If Redis is down, `RedisManager` falls back gracefully. The API continues to log jobs directly to PostgreSQL, where worker replicas fall back to `SKIP LOCKED` database queue polling. Sliding-window rate limiting falls back to an in-memory dictionary window."

### Q10: How are metrics and logs collected?
**Answer**:
> "The API uses `JsonFormatter` to produce structured JSON logs containing correlation fields (`request_id`, `job_id`, `workspace_id`). Sensitive keys (`token`, `password`, `secret`) are automatically redacted. Metrics are collected via `prometheus_client` and exposed at `/metrics`."
