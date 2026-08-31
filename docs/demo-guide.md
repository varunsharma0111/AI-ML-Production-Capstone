# AuraML Live Presentation & Demo Guide

---

## Overview

This guide provides a structured 5-to-10 minute presentation script and walkthrough for demonstrating AuraML to recruiters, interviewers, and technical stakeholders.

---

## 5–10 Minute Walkthrough Script

### Step 1: Platform Vision & Architecture Overview (1 Minute)
- **Script**: "AuraML is a cloud-native enterprise AI/ML lifecycle platform. It enables engineering and data science teams to securely manage datasets, execute asynchronous background model training, evaluate model quality through automated governance gates, serve controlled predictions, and audit system operations in real time."
- **Key Points**: Show `README.md` Mermaid diagrams (Overall Architecture, ML Lifecycle, Security).

### Step 2: Dataset Upload & Automated Async Profiling (1.5 Minutes)
- **Action**: Navigate to **Datasets** $\rightarrow$ Click **Upload Dataset** $\rightarrow$ Select `churn_dataset.csv`.
- **Script**: "When a user uploads a dataset, the API Gateway validates MIME types, checks file size boundaries, sanitizes the filename against path traversal attacks, and stores the file in S3. The API then enqueues a profiling job into a Redis task queue. The background worker picks up the job out-of-process and computes column summary statistics."

### Step 3: Asynchronous Model Training & S3 Storage (2 Minutes)
- **Action**: Navigate to **Model Training** $\rightarrow$ Click **Train New Model** $\rightarrow$ Select `churn_dataset.csv`, target column `churn`, algorithm `random_forest`.
- **Script**: "Model training is executed completely asynchronously out of the request path. The worker claims the job atomically using PostgreSQL `SELECT FOR UPDATE / SKIP LOCKED` queries to prevent duplicate worker execution. Once trained, the model weights JSON artifact is stored in S3 and its SHA-256 digest is computed and saved."

### Step 4: Quality Gate Governance & Environment Promotion (2 Minutes)
- **Action**: Open **Model Registry** $\rightarrow$ View `churn_classifier` `v1.0.0` $\rightarrow$ Evaluate Quality Gate.
- **Script**: "Before any model can serve predictions, it must pass automated Quality Gates checking accuracy, F1 score, and latency metrics. Once approved, the model is promoted from `draft` to `approved`, `staging`, and `production`."

### Step 5: Controlled Inference Sandbox & Prediction History (1.5 Minutes)
- **Action**: Open **Inference Sandbox** $\rightarrow$ Submit feature values `{"f1": 0.45, "f2": 1.2}` $\rightarrow$ View prediction output.
- **Script**: "The inference endpoint re-verifies the model's SHA-256 digest on every call to guarantee artifact integrity. Unapproved models are strictly blocked from serving predictions. Latency and confidence metrics are logged to the PostgreSQL `inference_logs` table."

### Step 6: AI Platform Agent & Operations Telemetry (2 Minutes)
- **Action**: Open **AI Assistant** $\rightarrow$ Ask: *"Inspect dataset churn_dataset.csv and summarize top models"* $\rightarrow$ Open **Audit Logs** and **Operations Dashboard**.
- **Script**: "AuraML includes a tool-augmented AI agent constrained by user RBAC permissions. Finally, all operations emit structured JSON logs and Prometheus metrics visible on the Operations Dashboard."
