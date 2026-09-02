# AuraML

## Local MLOps & Machine Learning Platform

AuraML is a local machine-learning platform that brings the core ML workflow into one application — from dataset upload and data profiling to model training, evaluation, quality checks, model promotion, and prediction.

---

## Local Architecture

```text
                    ┌──────────────────────┐
                    │     User / Browser   │
                    └──────────┬───────────┘
                               │
                               │ HTTP
                               ▼
                    ┌──────────────────────┐
                    │    React Frontend    │
                    │   localhost:5173     │
                    └──────────┬───────────┘
                               │
                               │ HTTP API
                               ▼
                    ┌──────────────────────┐
                    │   FastAPI Backend    │
                    │   localhost:8000     │
                    └───────┬───────┬──────┘
                            │       │
                     Dataset│       │Job
                            │       │
                            ▼       ▼
                  ┌────────────┐  ┌────────────┐
                  │   Local    │  │   Redis    │
                  │  Storage   │  │   Queue    │
                  │ ./data/    │  │   :6379    │
                  └─────┬──────┘  └─────┬──────┘
                        │                │
                        │                │ Job
                        │                ▼
                        │       ┌────────────────┐
                        └──────►│ Python Worker  │
                                │ Background ML  │
                                └───────┬────────┘
                                        │
                              ┌─────────┴─────────┐
                              │                   │
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

### Architecture in Simple Terms

```text
User
 ↓
React Frontend
 ↓
FastAPI Backend
 ├──→ Local File Storage
 └──→ Redis Queue
          ↓
     Python Worker
       ├──→ PostgreSQL
       └──→ Scikit-learn
                ↓
           Model Artifact
                ↓
          Prediction API
                ↓
        Prediction Result
```

AuraML uses a background Python worker for longer-running profiling and training jobs instead of making the FastAPI request perform the entire ML operation.

---

## Project Overview

AuraML provides a web interface for:

- Uploading datasets
- Profiling datasets
- Checking data quality
- Running background ML training jobs
- Evaluating models
- Applying quality gates
- Promoting approved models
- Generating predictions

The platform connects dataset management, asynchronous processing, model training, evaluation, and prediction into one local application.

---

## ML Workflow

```text
CSV Dataset
     ↓
Dataset Upload
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

### Background Job Flow

Profiling and model training are processed asynchronously:

```text
User Request
     ↓
FastAPI Backend
     ↓
Create Job
     ↓
Redis Queue
     ↓
Python Worker
     ↓
Process Job
     ↓
Store Result
```

This separates normal API requests from longer-running ML operations.

---

## Example: Customer Churn Prediction

AuraML can be demonstrated using a customer churn dataset.

### What is Churn?

Churn means that a customer stopped using a company's service.

The `churn` column is the **target variable** — the value the machine-learning model learns to predict.

- `churn = 0` → Customer did not churn
- `churn = 1` → Customer churned

The remaining columns provide information that the model can use to make its prediction.

### Example Dataset

| Customer | Age | Tenure | Contract | Late Payments | Churn |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TEL0001 | 25 | 5 | Monthly | 3 | 1 |
| TEL0002 | 52 | 60 | Two-Year | 0 | 0 |
| TEL0003 | 31 | 12 | Monthly | 2 | 1 |

This is a binary classification problem because the model predicts one of two outcomes.

```text
Customer Information
        ↓
    ML Model
        ↓
  Churn Prediction
        ↓
   ┌───────────────┐
   │ 0 → Stayed    │
   │ 1 → Churned   │
   └───────────────┘
```

The model learns patterns from existing customer data and uses those patterns to predict the churn outcome for new data.

---

## Local Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React, TypeScript, Vite | Web interface for datasets, jobs, models, and predictions |
| **Backend** | FastAPI, Uvicorn, Python, Pydantic | REST API, validation, and application logic |
| **Database** | PostgreSQL, SQLAlchemy, Alembic, asyncpg | Stores datasets, jobs, models, metrics, and application records |
| **Queue** | Redis | Queues background profiling and training jobs |
| **Worker** | Python Worker | Processes background jobs and ML/data operations |
| **ML/Data** | Scikit-learn, Python CSV processing | Data profiling, model training, and evaluation |
| **File Storage** | Local filesystem | Stores uploaded datasets and model artifacts |
| **Testing** | Pytest, HTTPX | API, integration, and end-to-end testing |

---

## Key Features

### Dataset Management & Profiling
- CSV dataset upload
- Automatic schema inference
- Data type detection
- Missing-value analysis
- Summary statistics
- Dataset health information
- Local dataset storage

### Asynchronous ML Processing
- Redis-backed job queue
- Background Python worker
- Dataset profiling jobs
- Model training jobs
- Job status tracking

### Model Training & Evaluation
- Scikit-learn model training
- Binary classification workflow
- Model performance evaluation
  - Accuracy
  - Precision
  - Recall
  - F1 score
- Model artifact persistence

### Model Quality & Promotion
- Automated quality checks
- Quality gate evaluation
- Model approval workflow
- Promotion of models that meet defined requirements

### Prediction
- Prediction API
- Promoted model inference
- Single prediction workflow
- Batch prediction workflow

### Web Interface
- React and TypeScript frontend
- Dataset management interface
- Job tracking
- Model evaluation interface
- Prediction interface
- Responsive UI

---

## Project Structure

```text
AuraML/
│
├── apps/
│   ├── api/                 # FastAPI backend
│   └── web/                 # React frontend
│
├── services/
│   └── worker/              # Background Python worker
│
├── database/
│   └── migrations/          # Alembic database migrations
│
├── data/
│   └── uploads/             # Local datasets and model artifacts
│
└── tests/                   # Automated tests
```

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm
- PostgreSQL
- Redis

### 1. Clone the Repository
```bash
git clone https://github.com/varunsharma0111/AI-ML-Production-Capstone.git
cd AI-ML-Production-Capstone
```

### 2. Install Backend Dependencies
```bash
pip install -e .[dev]
```

### 3. Install Frontend Dependencies
```bash
cd apps/web
npm install
cd ../..
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and configure the local environment:

```env
APP_ENV=local

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/capstone

REDIS_URL=redis://localhost:6379/0

STORAGE_BACKEND=local
STORAGE_PATH=./data/uploads

CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Start Local Services

Open three terminals.

**Terminal 1 — FastAPI Backend**
```bash
uvicorn apps.api.app.main:app --reload --port 8000
```

**Terminal 2 — Background Worker**
```bash
python services/worker/main.py
```

**Terminal 3 — React Frontend**
```bash
cd apps/web
npm run dev
```

---

## Testing

Run these checks from the project root.

### Code Quality
```bash
ruff check .
ruff format --check .
```

### Type Checking
```bash
mypy --explicit-package-bases apps/api services tests
```

### Automated Tests
```bash
pytest -v
```

### Frontend Production Build
```bash
cd apps/web
npm run build
```

---

## Documentation

- [Architecture Guide](docs/architecture.md) — System architecture, modules, and component interactions.
- [Security Guide](docs/security.md) — Security model, input validation, and data protection.
- [API Reference](docs/api.md) — REST API endpoint documentation.

---

## Project Summary

AuraML demonstrates how a machine-learning workflow can be organized into a complete local platform rather than a collection of individual scripts.

The project connects:

`React → FastAPI → Redis → Python Worker → PostgreSQL → Scikit-learn`

to provide a complete workflow:

`Dataset Upload → Profiling → Training → Evaluation → Quality Gate → Model Promotion → Prediction`

Everything described in this README refers to the local AuraML implementation.
