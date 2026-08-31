# AuraML REST & WebSocket API Documentation

---

## 1. System & Health Endpoints

### Liveness Probe
- **GET** `/health/live`
- **Response**: `200 OK` `{"status": "ok"}`

### Readiness Probe
- **GET** `/health/ready`
- **Response**: `200 OK` `{"status": "ok", "dependencies": {"database": "healthy", "redis": "healthy", "storage": "healthy"}}`

### Prometheus Metrics
- **GET** `/metrics`
- **Response**: `200 OK` (Prometheus text exposition format)

---

## 2. Dataset Ingestion API

### Upload CSV Dataset
- **POST** `/api/v1/datasets/upload`
- **Form Data**:
  - `workspace_id` (UUID)
  - `file` (Multipart CSV file)
- **Response**: `201 Created`

### List Datasets
- **GET** `/api/v1/datasets?workspace_id={ws_id}&offset=0&limit=20`
- **Response**: `200 OK`

---

## 3. ML Model Management & Controlled Inference API

### Register & Train Model
- **POST** `/api/v1/models`
- **Body**:
  ```json
  {
    "workspace_id": "...",
    "dataset_id": "...",
    "model_name": "churn_classifier",
    "target_column": "target",
    "model_type": "random_forest",
    "hyperparameters": {"n_estimators": 100}
  }
  ```
- **Response**: `201 Created`

### Promote Model Version
- **POST** `/api/v1/models/{model_id}/promote`
- **Body**: `{"target_status": "staging"}`
- **Response**: `200 OK`

### Controlled Model Inference
- **POST** `/api/v1/models/{model_id}/predict`
- **Body**:
  ```json
  {
    "workspace_id": "...",
    "input_features": {"f1": 0.5, "f2": 1.2}
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "model_id": "...",
    "model_version": "v1.1.0",
    "prediction": "positive",
    "confidence": 0.8921,
    "latency_ms": 1.45
  }
  ```

---

## 4. WebSockets API

### Job Status Stream
- **WebSocket** `/ws/jobs?workspace_id={ws_id}&token={jwt_token}`
- **Events Received**: Real-time status JSON objects (`job_status`, `dataset_profiling`, `model_training`).
