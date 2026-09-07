# AI/ML Production Capstone — Comprehensive Interview & Technical Guide

This document is a complete technical guide designed to help explain the architecture, data models, engineering patterns, production bug fixes, and system design decisions of the **AI-ML-Production-Capstone** project during technical interviews.

---

## 1. Executive Summary & System Overview

**AI-ML-Production-Capstone** is an enterprise-grade, end-to-end machine learning platform and data operations system. It provides multi-tenant workspace isolation, asynchronous dataset processing, automated model training, model registry governance with automated quality gates, real-time inference serving, an AI-powered assistant orchestrator, and audit logging.

### High-Level Architecture Diagram
```
                     +-----------------------------------+
                     |    Vercel React Frontend (SPA)    |
                     +-----------------------------------+
                                       | HTTP / REST API
                                       v
                     +-----------------------------------+
                     |      FastAPI Backend (Render)     |
                     |  - REST Endpoints & RBAC Policy   |
                     |  - AI Assistant Orchestrator      |
                     +-----------------------------------+
                       /               |               \
                      /                |                \
                     v                 v                 v
+------------------------+  +-------------------+  +-------------------------+
| PostgreSQL / SQLite DB |  | Storage Service   |  | Asynchronous Worker     |
| (SQLAlchemy 2.0 Async) |  | (Local / S3)      |  | (Background Job Runner) |
+------------------------+  +-------------------+  +-------------------------+
```

---

## 2. Tech Stack & Infrastructure

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Vercel |
| **Backend API** | Python 3.11, FastAPI, Pydantic v2, Render |
| **Database & ORM** | PostgreSQL (Production), SQLite (Dev/Test), SQLAlchemy 2.0 (AsyncIO), Alembic |
| **Machine Learning** | Scikit-Learn, Pandas, NumPy, Joblib |
| **Job Queue & Async** | Custom Async Engine, SQLAlchemy Job Table with Idempotency Keys |
| **Testing & Quality** | Pytest, Pytest-Asyncio, Ruff (Linter & Formatter) |
| **CI/CD & Hosting** | GitHub Actions, Render (API/Worker), Vercel (Frontend) |

---

## 3. Data Models & Database Schemas

The database schema is organized around workspace multi-tenancy and MLOps entity tracking:

```
                      +-------------------+
                      |       Users       |
                      +-------------------+
                                |
                                v
                   +-------------------------+
                   |  WorkspaceMemberships   |
                   +-------------------------+
                                ^
                                | (role: owner/editor/viewer)
                                |
                      +-------------------+
                      |    Workspaces     |
                      +-------------------+
                       /    |       |    \
                      /     |       |     \
                     v      v       v      v
              +----------+ +------+ +-----+ +-------------+
              | Datasets | | Jobs | |Tasks| |Audit Events |
              +----------+ +------+ +-----+ +-------------+
                   |           |
                   v           v
           +--------------------------+
           |      ModelVersions       |
           +--------------------------+
                   |           |
                   v           v
        +------------------+ +-----------------+
        | ModelEvaluations | | InferenceLogs   |
        +------------------+ +-----------------+
```

### Key Entities & Purpose

1. **`User`**: OIDC subject mapping, email, and display name.
2. **`Workspace`**: Tenant boundary (`slug`, `name`). All resources belong to a workspace.
3. **`WorkspaceMembership`**: RBAC permissions mapping users to workspaces with roles (`owner`, `editor`, `viewer`).
4. **`Dataset`**: Uploaded file metadata (`original_filename`, `storage_path`, `file_size_bytes`, `mime_type`, `row_count`, `column_count`, `status`).
5. **`DatasetProfile`**: Exploratory data analysis metadata stored as JSON (`column_stats`, `missing_values`, `correlations`, `schema_summary`).
6. **`Job` & `JobAttempt`**: Asynchronous background job queue state with idempotency keys (`payload_json`, `status`, `max_retries`, `attempt_count`, `error_detail`).
7. **`ModelVersion`**: ML model artifact registry (`name`, `version_tag`, `artifact_path`, `status`: `draft`, `candidate`, `approved`, `rejected`, `staging`, `production`, `metrics_json`, `hyperparameters_json`).
8. **`ModelEvaluation`**: Automated quality gate evaluation result (`accuracy`, `f1_score`, `latency_ms`, `passed_gate`).
9. **`InferenceLog`**: Real-time prediction audit log capturing inputs, model predictions, and execution latency.
10. **`AuditEvent`**: Compliance and security tracking for every mutating platform operation (`action`, `resource_type`, `resource_id`, `request_id`, `actor_user_id`).
11. **`OutboxEvent`**: Reliability pattern to safely decouple state mutations from message publishing (`aggregate_type`, `event_type`, `payload_json`, `status`).

---

## 4. Key Software Engineering Patterns Implemented

### Pattern 1: Multi-Tenant RBAC & Policy Security
- **Concept**: Users cannot access or mutate resources outside their assigned workspace.
- **Implementation**: Decorator/policy check `require_permission(principal, workspace_id, Permission.WRITE)` verifies membership role before executing service logic.

### Pattern 2: Model Governance & Quality Gate Policy
- **Concept**: Models cannot serve real-time predictions without passing automated checks.
- **Rules**:
  - Minimum Accuracy: **>= 0.85**
  - Minimum F1 Score: **>= 0.80**
  - Maximum Latency: **<= 100 ms**
- **State Machine Transition**:
  - Model creation $\rightarrow$ `draft`
  - Training finished $\rightarrow$ `candidate`
  - Passed Quality Gate $\rightarrow$ `approved`
  - Failed Quality Gate $\rightarrow$ `rejected`
  - Deployment $\rightarrow$ `staging` / `production`
- **Enforcement**: `ControlledInferencePredictor` checks model status and raises `DomainError("Inference Blocked by Policy")` if status is `draft` or `rejected`.

### Pattern 3: Transactional Outbox Pattern
- **Concept**: Guarantees atomic writes between database changes and event notifications.
- **Implementation**: Outbox events are stored in the same database transaction as business mutations, avoiding double-write inconsistencies when external message brokers are down.

### Pattern 4: Safe Async Transaction Guards
- **Concept**: SQLAlchemy 2.0 `AsyncSession` throws `InvalidRequestError` if `async with session.begin()` is called while a transaction is already active.
- **Solution**: Implemented `_is_in_transaction(session)` helper. Services check active transaction state before initiating new transaction blocks.

### Pattern 5: Resilient Background Worker Execution Engine
- **Concept**: Prevents failed background tasks from becoming stuck in infinite retries.
- **Implementation**:
  - Uses `async with session.begin_nested():` savepoints for isolation.
  - Captures primitive attributes (`job_id = job.id`) before processing to avoid SQLAlchemy ORM expired object reload failures after transaction exit.
  - Formally writes `FAILED` status and `JobAttempt` records into DB on exception.

---

## 5. End-to-End MLOps Workflow & Data Flow

```
 1. Upload Dataset  ---> Saved to Storage Service & DB Dataset table
 2. Profile Dataset ---> Async Worker computes column stats, missing values & schema
 3. Model Training  ---> Async Worker executes Scikit-Learn training, saves joblib model
 4. Quality Gate    ---> Evaluates model against Accuracy (>=0.85), F1 (>=0.80), Latency (<=100ms)
 5. Promotion       ---> Model promoted from Approved to Staging / Production
 6. Inference       ---> API predicts incoming payload & logs latency into InferenceLog
```

---

## 6. Technical Interview Deep Dive: Bugs Encountered & Solutions

### Problem 1: Worker Stuck in Infinite Retry Loop
- **Symptom**: Background job failed (e.g. `Dataset not found`), but the job status remained `queued`, causing endless retries.
- **Root Cause**: In exception handling, `logger.exception("... %s", job.id)` attempted to access `job.id` after the session transaction closed. SQLAlchemy attempted a lazy reload on the closed session, throwing a 2nd exception (`InvalidRequestError: Can't operate on closed transaction`). This escaped uncaught and bypassed the code writing `job.status = 'failed'`.
- **Solution**:
  1. Captured `job_id = job.id` as a primitive string/UUID **before** starting the execution block.
  2. Wrapped execution in `async with session.begin_nested():` (savepoint).
  3. Ensured exception logging uses primitive `job_id` so lazy ORM queries never run on closed sessions.

### Problem 2: Internal Server Error (500) in AI Assistant Orchestration
- **Symptom**: Calling AI Assistant endpoint `/api/v1/agent/orchestrate` raised 500 `InvalidRequestError: A transaction is already begun on this Session`.
- **Root Cause**: FastAPI dependency injected an `AsyncSession` with an active transaction context, while `orchestrate` tried to execute `async with session.begin()`.
- **Solution**: Created `_is_in_transaction(session)` guard. The service checks `session.in_transaction()` before wrapping execution in a new transaction block. Added friendly markdown response formatting when models or datasets are not found.

---

## 7. Sample Interview Questions & Answers

### Q1: How do you handle multi-tenancy and data security in this architecture?
> *"Multi-tenancy is enforced at the database repository and service policy layer. Every entity (Datasets, Models, Tasks, Audit Logs) is scoped to a `workspace_id`. In incoming API requests, our `require_permission` policy middleware validates the user's role in `WorkspaceMembership` before allowing access. Queries are filtered strictly by `workspace_id`."*

### Q2: What happens if a background worker crashes mid-task?
> *"Jobs use idempotency keys and state tracking (`queued` -> `processing` -> `completed`/`failed`). Each execution runs within a savepoint (`begin_nested()`). If a task fails, `attempt_count` increments up to `max_retries`. If max retries are reached, the job is marked `failed` and a `JobAttempt` entry captures the stack trace."*

### Q3: How do you enforce model quality in production?
> *"We implement an automated Quality Gate in `ModelEvaluation`. Models cannot be deployed or served in real-time unless accuracy >= 0.85, F1 score >= 0.80, and latency <= 100ms. The `ControlledInferencePredictor` blocks inference requests for any model in `draft` or `rejected` states."*

### Q4: How do you manage database transaction boundaries with SQLAlchemy 2.0 AsyncIO?
> *"SQLAlchemy 2.0 AsyncSession prevents nested call to `session.begin()`. We created an async helper `_is_in_transaction` that inspects `session.in_transaction()`. If active, the service executes within the existing transaction; otherwise, it opens a fresh transaction block. This prevents 500 server errors from duplicate transaction initialization."*

---

## 8. Quick Reference API Table

| Endpoint | Method | Role / Permission | Purpose |
| :--- | :--- | :--- | :--- |
| `/api/v1/datasets/upload` | `POST` | `editor` / `owner` | Upload CSV dataset |
| `/api/v1/ml/models/train` | `POST` | `editor` / `owner` | Trigger async model training job |
| `/api/v1/ml/models/{id}/evaluate` | `POST` | `editor` / `owner` | Run automated Quality Gate evaluation |
| `/api/v1/ml/models/{id}/promote` | `POST` | `owner` | Promote model to Staging / Production |
| `/api/v1/ml/predict` | `POST` | `viewer`+ | Serve real-time model inference |
| `/api/v1/agent/orchestrate` | `POST` | `viewer`+ | AI Assistant natural language query orchestrator |
