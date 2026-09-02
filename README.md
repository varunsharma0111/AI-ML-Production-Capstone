# AuraML

## Local MLOps & Machine Learning Platform

---

## Project Overview

AuraML is a local machine-learning platform that provides a web interface for uploading datasets, profiling data, running background ML training jobs, evaluating models, promoting approved models, and generating predictions.

The platform simplifies the ML workflow by connecting dataset management, asynchronous processing, model training, evaluation, and prediction into one application.

---

## What Problem Does AuraML Solve?

Building a machine-learning model is more than writing a training script.

A typical workflow involves:

1. Uploading a dataset
2. Understanding the data
3. Checking data quality
4. Training a model
5. Evaluating the model
6. Deciding whether the model is good enough
7. Using the trained model for predictions

AuraML brings these steps into one application so the complete ML workflow can be demonstrated from dataset upload to prediction.

This makes the project understandable to recruiters and GitHub visitors.

---

## Example: Customer Churn Prediction

AuraML can be demonstrated using a customer churn dataset.

### What is Churn?

Churn means that a customer stopped using a company's service.

The `churn` column is the **target variable** that the model learns to predict.

- `churn = 0` → Customer did not churn
- `churn = 1` → Customer churned

The other columns provide information that the model can use to make the prediction.

Example:

| Customer | Age | Tenure | Contract | Late Payments | Churn |
|---|---:|---:|---|---:|---:|
| TEL0001 | 25 | 5 | Monthly | 3 | 1 |
| TEL0002 | 52 | 60 | Two-Year | 0 | 0 |
| TEL0003 | 31 | 12 | Monthly | 2 | 1 |

This is a **binary classification problem** because the model predicts one of two outcomes.

```text
Customer Data
      ↓
   ML Model
      ↓
Churn Prediction
      ↓
0 = Stayed
1 = Churned
```

This example demonstrates AuraML's complete workflow:

Upload → Profile → Train → Evaluate → Quality Gate → Promote → Predict

---

## ML Workflow

```text
CSV Dataset
     ↓
Upload Dataset
     ↓
Data Profiling
     ↓
Quality Checks
     ↓
Train ML Model
     ↓
Evaluate Model
     ↓
Quality Gate
     ↓
Promote Model
     ↓
Make Predictions
```

Each step is handled by AuraML instead of requiring separate scripts or tools.

---

## Local Architecture

```text
                    ┌──────────────────────┐
                    │     User / Browser    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    React Frontend    │
                    │   localhost:5173     │
                    └──────────┬───────────┘
                               │ HTTP
                               ▼
                    ┌──────────────────────┐
                    │   FastAPI Backend    │
                    │   localhost:8000     │
                    └───────┬───────┬──────┘
                            │       │
                    Dataset │       │ Job
                            │       │
                            ▼       ▼
                  ┌────────────┐  ┌────────────┐
                  │   Local    │  │   Redis    │
                  │  Storage   │  │   Queue    │
                  │./data/...  │  │ :6379      │
                  └─────┬──────┘  └─────┬──────┘
                        │                │
                        │                ▼
                        │       ┌────────────────┐
                        │       │ Background     │
                        └──────►│ Python Worker  │
                                └───────┬────────┘
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                       ┌────────────┐      ┌─────────────┐
                       │ PostgreSQL │      │ Scikit-learn│
                       │   :5432    │      │ ML Training │
                       └────────────┘      └──────┬──────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │    Model    │
                                           │   Artifact  │
                                           └──────┬──────┘
                                                  │
                                                  ▼
                                         ┌────────────────┐
                                         │ Prediction API │
                                         └───────┬────────┘
                                                 │
                                                 ▼
                                         ┌────────────────┐
                                         │ Prediction     │
                                         │ Result         │
                                         └────────────────┘
```

---

## Local Technology Stack

| Layer | Technology | Local Usage |
|---|---|---|
| Frontend | React, TypeScript, Vite | Web interface for datasets, jobs, models, and predictions |
| Backend | FastAPI, Uvicorn, Python, Pydantic | REST API, request validation, and application logic |
| Database | PostgreSQL, SQLAlchemy, Alembic, asyncpg | Stores datasets, jobs, models, metrics, and application records |
| Queue | Redis | Queues background profiling and training jobs |
| Worker | Python Worker | Processes queued jobs and performs ML/data operations |
| ML/Data | Scikit-learn, Python CSV processing | Dataset profiling, model training, and evaluation |
| File Storage | Local filesystem | Stores uploaded datasets and model artifacts |
| Testing | Pytest, HTTPX | Tests the running API and end-to-end workflow |

---

## Key Features

- **Dataset Management & Automated Profiling**: Streamlined CSV ingestion with file validation and background data profiling (row/column stats, missing values, summary stats).
- **Asynchronous Redis Worker Engine**: Decoupled background task queue for handling dataset profiling and model training jobs off the API main thread.
- **Local Storage Management**: Filesystem storage for uploaded CSV datasets and serialized model artifacts (`./data/uploads`).
- **Scikit-Learn ML Lifecycle**: Automated binary classification training, performance metric evaluation (accuracy, F1 score, recall, precision), and model artifact persistence.
- **ML Governance & Quality Gates**: Automated evaluation checks guarding model promotion from `draft` to `approved`.
- **Prediction API**: RESTful inference endpoints for serving real-time predictions using promoted model artifacts.
- **Web Interface**: Responsive React & TypeScript interface for datasets, job tracking, model evaluations, and single/batch predictions.

---

## Quickstart & Setup

### Prerequisites
- Python `3.11+`
- Node.js `20+` & `npm`
- PostgreSQL & Redis

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/varunsharma0111/AI-ML-Production-Capstone.git
cd AI-ML-Production-Capstone

# Install backend package in editable mode
pip install -e .[dev]

# Install frontend web dependencies
cd apps/web
npm install
cd ../..
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure local variables:
```env
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/capstone
REDIS_URL=redis://localhost:6379/0
STORAGE_BACKEND=local
STORAGE_PATH=./data/uploads
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start Local Development Services

**Terminal 1 — API Server:**
```bash
uvicorn apps.api.app.main:app --reload --port 8000
```

**Terminal 2 — Async Worker:**
```bash
python services/worker/main.py
```

**Terminal 3 — React Frontend:**
```bash
cd apps/web
npm run dev
```

---

## Testing

```bash
# Static Analysis & Formatting
ruff check .
ruff format --check .

# Strict Type Checking
mypy --explicit-package-bases apps/api services tests

# Unit & Integration Tests
pytest -v

# Frontend Production Build Verification
cd apps/web && npm run build
```

---

## Project Documentation

- [Architecture Guide](docs/architecture.md) — Architectural design, modules, and component interactions.
- [Security Guide](docs/security.md) — Security model, input sanitization, and data validation.
- [API Reference](docs/api.md) — Complete REST API endpoint documentation.
