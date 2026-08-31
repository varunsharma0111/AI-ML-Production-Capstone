# AuraML Architecture Guide

---

## 1. System Overview

AuraML is designed as a modular monolith API with decoupled asynchronous worker processes and pluggable cloud storage engines.

```
+-------------------------------------------------------------------------+
|                              React 18 SPA                               |
|                     (Vite, TypeScript, TailwindCSS)                     |
+------------------------------------+------------------------------------+
                                     |
                       HTTPS REST / WebSocket JSON
                                     |
                                     v
+-------------------------------------------------------------------------+
|                           FastAPI Monolith                              |
|                                                                         |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Identity & RBAC   |  | Dataset Service   |  | ML Governance Engine|  |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Async Job Service |  | Inference Engine  |  | AI Agent Module     |  |
|  +-------------------+  +-------------------+  +---------------------+  |
+-------------------+-------------------+-------------------+-------------+
                    |                   |                   |
                    v                   v                   v
            +---------------+   +---------------+   +---------------+
            | PostgreSQL DB |   |  Redis Broker |   | S3 Storage    |
            | (Transactional|   | (Queue, Cache,|   | (Datasets &   |
            |   Entities)   |   |   PubSub)     |   |   Artifacts)  |
            +---------------+   +-------+-------+   +---------------+
                                        |
                                        v
                        +-------------------------------+
                        |      Async Worker Process     |
                        | (Dataset Profiling & Training)|
                        +-------------------------------+
```

---

## 2. Component Design & Responsibilities

### 2.1 API Gateway (`apps/api/app/main.py`)
- Handles identity verification (`JwtVerifier`), rate limiting (`RateLimitMiddleware`), security headers, structured JSON logging (`JsonFormatter`), and domain exception handling.
- Exposes REST endpoints (`/api/v1/...`) and real-time WebSocket job notifications (`/ws/jobs`).

### 2.2 Async Worker Process (`services/worker/`)
- Executes asynchronous long-running tasks out-of-process.
- Claims jobs atomically using SQL transactions (`SELECT FOR UPDATE / SKIP LOCKED`), eliminating claim race conditions across multiple worker replicas.
- Automatically recovers stuck jobs (`recover_stuck_jobs`) after a 15-minute timeout window.

### 2.3 Object Storage Layer (`apps/api/app/core/storage/`)
- Provides unified `StorageBackend` abstraction for local filesystem and cloud S3 storage (AWS S3, MinIO, Cloudflare R2).
- Enforces path-traversal safeguards and tenant workspace isolation (`workspaces/{workspace_id}/...`).

### 2.4 ML Lifecycle Engine (`ml/` & `services/ml_inference/`)
- Handles automated CSV dataset profiling, scikit-learn model training, evaluation metrics calculation (Accuracy, F1, Precision, Recall, Latency), and controlled inference prediction with mandatory SHA-256 artifact verification.

### 2.5 AI Agent Module (`apps/api/app/api/routers/agent.py`)
- Tool-augmented AI assistant providing workspace data analysis, model comparison, and automated promotion recommendation using permission-checked tools.
