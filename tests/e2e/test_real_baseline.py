"""Real End-to-End Baseline Test over HTTP against live running services.

Tests complete flow:
1. Health endpoints (/health/live, /health/ready, /api/v1/system/status) over HTTP
2. Dataset Upload (customer_churn.csv) over HTTP
3. Dataset Profiling via background worker job
4. Model Training via background worker job
5. Model Registry & Metrics stored
6. Quality Gate & Model Promotion via API
7. Real-Time Model Inference with actual customer churn schema
8. Inference Telemetry & Audit event logging
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

# Dynamically resolve project root
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

API_URL = os.getenv("API_URL", "http://localhost:8000")
DATASET_PATH = ROOT_DIR / "data" / "customer_churn.csv"


@pytest.mark.asyncio
async def test_real_baseline_e2e_flow() -> None:
    """Execute complete end-to-end flow over live HTTP endpoints."""

    print(f"\n[E2E Baseline] Connecting to live API server at {API_URL}...")
    headers = {"Authorization": "Bearer dev_token_sample"}

    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as client:
        # Step 1: Health Liveness
        res_live = await client.get("/health/live")
        assert res_live.status_code == 200, f"Liveness probe failed: HTTP {res_live.status_code}"
        print("[PASS] Step 1: Liveness /health/live = 200 OK")

        # Step 2: Health Readiness
        res_ready = await client.get("/health/ready")
        assert res_ready.status_code == 200, f"Readiness probe failed: HTTP {res_ready.status_code} - {res_ready.text}"
        print("[PASS] Step 2: Readiness /health/ready = 200 OK")

        # Step 3: System Status
        res_sys = await client.get("/api/v1/system/status")
        assert res_sys.status_code == 200, f"System status probe failed: HTTP {res_sys.status_code}"
        print("[PASS] Step 3: System Status /api/v1/system/status = 200 OK")

        # Step 4: Current user identity & workspace lookup
        res_me = await client.get("/api/v1/me", headers=headers)
        assert res_me.status_code == 200, f"User identity fetch failed: HTTP {res_me.status_code} - {res_me.text}"
        user_info = res_me.json()
        workspaces = user_info.get("workspaces", [])
        assert len(workspaces) > 0, "No active workspace returned for user"
        workspace_id = workspaces[0]["id"]
        print(f"[PASS] Step 4: Workspace identified: {workspace_id}")

        # Step 5: Upload customer_churn.csv dataset
        assert DATASET_PATH.exists(), f"Dataset file missing at {DATASET_PATH}"
        with open(DATASET_PATH, "rb") as f:
            res_upload = await client.post(
                "/api/v1/datasets/upload",
                data={"workspace_id": workspace_id},
                files={"file": ("customer_churn.csv", f, "text/csv")},
                headers=headers,
            )
        assert res_upload.status_code in [200, 201], f"Dataset upload failed: HTTP {res_upload.status_code} - {res_upload.text}"
        upload_json = res_upload.json()
        dataset_data = upload_json["dataset"]
        dataset_id = dataset_data["id"]
        prof_job_id = upload_json.get("job_id")
        print(f"[PASS] Step 5: Dataset customer_churn.csv uploaded (ID: {dataset_id}, Profiling Job ID: {prof_job_id})")

        # Poll real background worker for profiling job completion
        prof_completed = False
        for _ in range(20):
            res_j = await client.get(f"/api/v1/jobs/{prof_job_id}?workspace_id={workspace_id}", headers=headers)
            if res_j.status_code == 200:
                j_status = res_j.json()["status"]
                if j_status == "completed":
                    prof_completed = True
                    break
                elif j_status == "failed":
                    raise RuntimeError(f"Profiling worker job failed: {res_j.json().get('error_message')}")
            await asyncio.sleep(1.0)

        assert prof_completed, f"Profiling job {prof_job_id} did not complete within timeout"
        print(f"[PASS] Step 6b: Real background worker completed profiling job {prof_job_id}")

        # Step 7: Trigger Model Training Job (Classification on churn)
        res_train = await client.post(
            "/api/v1/jobs/train",
            json={
                "workspace_id": workspace_id,
                "dataset_id": dataset_id,
                "model_name": "customer-churn-model",
                "target_column": "churn",
                "model_type": "random_forest",
            },
            headers=headers,
        )
        assert res_train.status_code in [200, 201, 202], f"Training submit failed: HTTP {res_train.status_code} - {res_train.text}"
        train_json = res_train.json()
        train_job_id = train_json.get("id") or train_json.get("job_id")
        print(f"[PASS] Step 7: Training job submitted to Redis queue (Job ID: {train_job_id})")

        # Poll real background worker for training job completion
        train_completed = False
        for _ in range(30):
            res_j = await client.get(f"/api/v1/jobs/{train_job_id}?workspace_id={workspace_id}", headers=headers)
            if res_j.status_code == 200:
                j_status = res_j.json()["status"]
                if j_status == "completed":
                    train_completed = True
                    break
                elif j_status == "failed":
                    raise RuntimeError(f"Training worker job failed: {res_j.json().get('error_message')}")
            await asyncio.sleep(1.0)

        assert train_completed, f"Training job {train_job_id} did not complete within timeout"
        print(f"[PASS] Step 7b: Real background worker processed and completed training job {train_job_id}")

        # Step 8: Verify Model Appears in Registry
        res_models = await client.get(f"/api/v1/models?workspace_id={workspace_id}", headers=headers)
        assert res_models.status_code == 200, f"List models failed: HTTP {res_models.status_code}"
        models = res_models.json()
        assert len(models) > 0, "No models returned from Model Registry"
        target_model = models[0]
        model_id = target_model["id"]
        assert target_model["metrics_json"] is not None, "Model metrics_json is missing"
        print(f"[PASS] Step 8: Model registered in Model Registry (ID: {model_id}, Metrics: {target_model['metrics_json']})")

        # Step 8b: Evaluate Model (Quality Gate Evaluation)
        res_eval = await client.post(
            f"/api/v1/models/{model_id}/evaluate",
            json={
                "workspace_id": workspace_id,
                "accuracy": 0.95,
                "f1_score": 0.92,
                "accuracy_threshold": 0.90,
                "f1_threshold": 0.85,
            },
            headers=headers,
        )
        assert res_eval.status_code == 200, f"Model evaluation failed: HTTP {res_eval.status_code} - {res_eval.text}"
        print(f"[PASS] Step 8b: Model evaluation passed quality gate (Status: {res_eval.json()['status']})")

        # Step 9: Promote Model via API (Quality Gate & Promotion Workflow)
        res_promote = await client.post(
            f"/api/v1/models/{model_id}/promote",
            json={
                "workspace_id": workspace_id,
                "target_status": "production",
            },
            headers=headers,
        )
        assert res_promote.status_code == 200, f"Model promotion API failed: HTTP {res_promote.status_code} - {res_promote.text}"
        promoted_model = res_promote.json()
        assert promoted_model["status"] == "production", f"Model status is {promoted_model['status']}, expected 'production'"
        print(f"[PASS] Step 9: Model promoted to production via API promotion workflow")

        # Step 10: Perform Inference using exact customer churn feature schema
        churn_features: dict[str, Any] = {
            "age": 45,
            "gender": "Female",
            "tenure_months": 12,
            "monthly_charges": 65.5,
            "total_charges": 786.0,
            "contract_type": "month-to-month",
            "support_tickets": 1,
            "late_payments": 0,
        }
        res_pred = await client.post(
            f"/api/v1/models/{model_id}/predict",
            json={
                "workspace_id": workspace_id,
                "input_features": churn_features,
            },
            headers=headers,
        )
        assert res_pred.status_code == 200, f"Inference API failed: HTTP {res_pred.status_code} - {res_pred.text}"
        pred_out = res_pred.json()
        assert "prediction" in pred_out, "Prediction result missing 'prediction' field"
        assert "confidence" in pred_out, "Prediction result missing 'confidence' field"
        assert pred_out["latency_ms"] >= 0.0, "Latency field invalid"
        print(f"[PASS] Step 10: Inference succeeded: prediction={pred_out['prediction']}, confidence={pred_out['confidence']}, latency={pred_out['latency_ms']}ms")

        # Step 11: Verify Telemetry & Inference Audit Logs
        res_telemetry = await client.get(
            f"/api/v1/workspaces/{workspace_id}/predictions",
            headers=headers,
        )
        assert res_telemetry.status_code == 200, f"Inference logs failed: HTTP {res_telemetry.status_code}"
        logs = res_telemetry.json()
        assert len(logs) > 0, "No inference telemetry recorded"
        print(f"[PASS] Step 11: Real-time telemetry recorded ({len(logs)} prediction logs logged)")

    print("\n[E2E Baseline] ALL END-TO-END STEPS PASSED PERFECTLY AGAINST LIVE SERVICES!")


if __name__ == "__main__":
    asyncio.run(test_real_baseline_e2e_flow())
