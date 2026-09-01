"""Transactional AI agent service with RBAC, ML analytics, and audit."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.tools.definitions import REGISTERED_TOOLS
from agent.tools.sandbox import ToolSandbox
from agent.tools.security import AgentToolSecurityGuard
from app.api.schemas.agent import (
    AgentOrchestrateRequest,
    AgentOrchestrateResponse,
    ToolExecuteRequest,
)
from app.api.schemas.ml import PredictRequest
from app.core.errors import AuthorizationError, ResourceNotFoundError
from app.db.models.entities import AuditEvent
from app.db.repositories.datasets import DatasetRepository
from app.db.repositories.identity import IdentityRepository
from app.db.repositories.ml import ModelRepository
from app.domains.identity.policy import Permission, require_permission
from app.domains.identity.principal import Principal
from app.services.ml import MLService

TOOL_PERMISSION_MAP: dict[str, Permission] = {
    "calculator": Permission.TASK_READ,
    "workspace_summary": Permission.TASK_READ,
    "list_models": Permission.MODEL_READ,
    "list_datasets": Permission.DATASET_READ,
    "compare_models": Permission.MODEL_READ,
    "explain_metrics": Permission.MODEL_READ,
    "summarize_dataset": Permission.DATASET_READ,
    "run_prediction": Permission.MODEL_READ,
}


class AgentService:
    def __init__(
        self,
        identity_repository: IdentityRepository | None = None,
        model_repository: ModelRepository | None = None,
        dataset_repository: DatasetRepository | None = None,
        ml_service: MLService | None = None,
        sandbox: ToolSandbox | None = None,
        security_guard: AgentToolSecurityGuard | None = None,
    ) -> None:
        self._identity_repository = identity_repository or IdentityRepository()
        self._model_repository = model_repository or ModelRepository()
        self._dataset_repository = dataset_repository or DatasetRepository()
        self._ml_service = ml_service or MLService()
        self._sandbox = sandbox or ToolSandbox()
        self._security_guard = security_guard or AgentToolSecurityGuard()

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "required_permission": tool.required_permission,
            }
            for tool in REGISTERED_TOOLS.values()
        ]

    async def execute_tool(
        self,
        session: AsyncSession,
        principal: Principal,
        payload: ToolExecuteRequest,
        request_id: str = "unknown",
    ) -> tuple[dict[str, Any], float]:
        async with session.begin():
            user = await self._identity_repository.get_or_create_user(session, principal)
            membership = await self._identity_repository.get_membership(
                session, payload.workspace_id, user.id
            )
            if membership is None:
                raise AuthorizationError("You are not a member of this workspace.")

            # Validate input safety with security guard
            for arg_name, arg_val in payload.arguments.items():
                if isinstance(arg_val, str):
                    try:
                        self._security_guard.validate_input_string(arg_val, field_name=arg_name)
                    except Exception as sec_error:
                        session.add(
                            AuditEvent(
                                actor_user_id=user.id,
                                workspace_id=payload.workspace_id,
                                action="agent.tool_denied",
                                resource_type="agent_tool",
                                resource_id=user.id,
                                request_id=request_id,
                                metadata_json={
                                    "tool_name": payload.tool_name,
                                    "reason": f"Security Guard Rejection: {sec_error}",
                                },
                            )
                        )
                        raise sec_error

            # Enforce fine-grained RBAC permission check
            required_perm = TOOL_PERMISSION_MAP.get(payload.tool_name, Permission.MODEL_READ)
            try:
                require_permission(membership.role, required_perm)
            except AuthorizationError as rbac_error:
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="agent.tool_denied",
                        resource_type="agent_tool",
                        resource_id=user.id,
                        request_id=request_id,
                        metadata_json={
                            "tool_name": payload.tool_name,
                            "reason": (
                                f"RBAC Denied: role '{membership.role}'"
                                f" lacks '{required_perm.value}'"
                            ),
                        },
                    )
                )
                raise rbac_error

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="agent.tool_requested",
                    resource_type="agent_tool",
                    resource_id=user.id,
                    request_id=request_id,
                    metadata_json={"tool_name": payload.tool_name},
                )
            )

            # Build context dynamically from real DB repositories
            context: dict[str, Any] = {}

            if payload.tool_name == "list_models":
                models = await self._model_repository.list_model_versions_for_workspace(
                    session, payload.workspace_id
                )
                context["models"] = [
                    {
                        "id": m.id,
                        "name": m.name,
                        "version_tag": m.version_tag,
                        "status": m.status,
                        "metrics_json": m.metrics_json or {},
                    }
                    for m in models
                ]

            elif payload.tool_name == "list_datasets":
                datasets = await self._dataset_repository.list_datasets_for_workspace(
                    session, payload.workspace_id, offset=0, limit=50
                )
                context["datasets"] = [
                    {
                        "id": d.id,
                        "original_filename": d.original_filename,
                        "status": d.status,
                        "row_count": d.row_count,
                        "column_count": d.column_count,
                    }
                    for d in datasets
                ]

            elif payload.tool_name == "compare_models":
                models = await self._model_repository.list_model_versions_for_workspace(
                    session, payload.workspace_id
                )
                m1_name = str(payload.arguments.get("model_name_1", "")).lower()
                m2_name = str(payload.arguments.get("model_name_2", "")).lower()

                m1, m2 = None, None
                for m in models:
                    tag_or_name = f"{m.name} {m.version_tag}".lower()
                    if (m1_name in tag_or_name or str(m.id) == m1_name) and not m1:
                        m1 = m
                    elif (m2_name in tag_or_name or str(m.id) == m2_name) and not m2:
                        m2 = m

                if not m1 or not m2:
                    if len(models) >= 2 and (not m1 or not m2):
                        m1 = m1 or models[0]
                        m2 = m2 or models[1]
                    else:
                        raise ResourceNotFoundError("Could not find two model versions to compare.")

                context["model_1"] = {
                    "id": m1.id,
                    "name": m1.name,
                    "version_tag": m1.version_tag,
                    "status": m1.status,
                    "metrics_json": m1.metrics_json or {},
                }
                context["model_2"] = {
                    "id": m2.id,
                    "name": m2.name,
                    "version_tag": m2.version_tag,
                    "status": m2.status,
                    "metrics_json": m2.metrics_json or {},
                }

            elif payload.tool_name == "explain_metrics":
                models = await self._model_repository.list_model_versions_for_workspace(
                    session, payload.workspace_id
                )
                target = str(payload.arguments.get("model_id_or_name", "")).lower()
                matched = None
                for m in models:
                    if target in f"{m.name} {m.version_tag}".lower() or str(m.id) == target:
                        matched = m
                        break
                if not matched and models:
                    matched = models[0]
                if not matched:
                    raise ResourceNotFoundError("Requested model version was not found.")

                eval_record = await self._model_repository.get_latest_evaluation(
                    session, matched.id
                )

                context["model"] = {
                    "id": matched.id,
                    "name": matched.name,
                    "version_tag": matched.version_tag,
                    "status": matched.status,
                    "metrics_json": matched.metrics_json or {},
                }
                if eval_record:
                    context["evaluation"] = {
                        "accuracy": eval_record.accuracy,
                        "f1_score": eval_record.f1_score,
                        "passed_gate": eval_record.passed_gate,
                        "evaluation_metadata": eval_record.evaluation_metadata or {},
                    }

            elif payload.tool_name == "summarize_dataset":
                datasets = await self._dataset_repository.list_datasets_for_workspace(
                    session, payload.workspace_id, offset=0, limit=50
                )
                target = str(payload.arguments.get("dataset_id_or_name", "")).lower()
                matched_ds = None
                for d in datasets:
                    if target in d.original_filename.lower() or str(d.id) == target:
                        matched_ds = d
                        break
                if not matched_ds and datasets:
                    matched_ds = datasets[0]
                if not matched_ds:
                    raise ResourceNotFoundError("Requested dataset was not found.")

                profile = await self._dataset_repository.get_profile_by_dataset_id(
                    session, matched_ds.id
                )
                context["dataset"] = {
                    "id": matched_ds.id,
                    "original_filename": matched_ds.original_filename,
                    "status": matched_ds.status,
                    "row_count": matched_ds.row_count,
                    "column_count": matched_ds.column_count,
                }
                if profile:
                    context["profile"] = {
                        "row_count": profile.row_count,
                        "column_count": profile.column_count,
                        "columns_json": profile.columns_json or [],
                    }

            elif payload.tool_name == "run_prediction":
                models = await self._model_repository.list_model_versions_for_workspace(
                    session, payload.workspace_id
                )
                target = str(payload.arguments.get("model_id_or_name", "")).lower()
                matched = None
                for m in models:
                    if target in f"{m.name} {m.version_tag}".lower() or str(m.id) == target:
                        matched = m
                        break
                if not matched:
                    # Select first production/staging/approved model if available
                    for m in models:
                        if m.status in ["production", "staging", "approved"]:
                            matched = m
                            break
                if not matched and models:
                    matched = models[0]
                if not matched:
                    raise ResourceNotFoundError("No model version available for prediction.")

                features = payload.arguments.get(
                    "input_features", {"age": 35, "income": 50000, "tenure": 4}
                )
                predict_req = PredictRequest(
                    workspace_id=payload.workspace_id, input_features=features
                )

                # Execute MLService predict (eligibility, SHA-256, validation)
                pred_res, latency, _ = await self._ml_service.predict(
                    session, principal, matched.id, predict_req, request_id
                )
                context["prediction_result"] = pred_res
                context["latency_ms"] = latency

            result, duration_ms = self._sandbox.execute_tool(
                payload.tool_name, payload.arguments, context=context
            )

            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="agent.tool_completed",
                    resource_type="agent_tool",
                    resource_id=user.id,
                    request_id=request_id,
                    metadata_json={
                        "tool_name": payload.tool_name,
                        "duration_ms": duration_ms,
                    },
                )
            )

            return result, duration_ms

    async def orchestrate(
        self,
        session: AsyncSession,
        principal: Principal,
        payload: AgentOrchestrateRequest,
        request_id: str = "unknown",
    ) -> AgentOrchestrateResponse:
        user = await self._identity_repository.get_or_create_user(session, principal)

        # Log agent request audit event
        async with session.begin():
            session.add(
                AuditEvent(
                    actor_user_id=user.id,
                    workspace_id=payload.workspace_id,
                    action="agent.requested",
                    resource_type="agent_chat",
                    resource_id=user.id,
                    request_id=request_id,
                    metadata_json={"prompt_length": len(payload.message)},
                )
            )

        msg_lower = payload.message.lower()
        tools_used: list[str] = []
        tool_results: list[dict[str, Any]] = []
        answer = ""

        try:
            if "compare" in msg_lower:
                tool_name = "compare_models"
                m1_match = re.search(r"v\d+", msg_lower)
                args = {
                    "model_name_1": "v1.0.0" if not m1_match else m1_match.group(0),
                    "model_name_2": "v2.0.0",
                }
                res, duration = await self.execute_tool(
                    session,
                    principal,
                    ToolExecuteRequest(
                        workspace_id=payload.workspace_id, tool_name=tool_name, arguments=args
                    ),
                    request_id,
                )
                tools_used.append(tool_name)
                tool_results.append(
                    {"tool_name": tool_name, "result": res, "duration_ms": duration}
                )
                better = res.get("better_model", "v2.0.0")
                exp = res.get("explanation", "")
                m1_data = res.get("model_1", {})
                m2_data = res.get("model_2", {})
                m1_name = m1_data.get("name", "v1")
                m1_tag = m1_data.get("version_tag", "v1")
                m1_acc = float(m1_data.get("accuracy", 0.0)) * 100
                m1_f1 = float(m1_data.get("f1_score", 0.0)) * 100
                m1_st = m1_data.get("status")

                m2_name = m2_data.get("name", "v2")
                m2_tag = m2_data.get("version_tag", "v2")
                m2_acc = float(m2_data.get("accuracy", 0.0)) * 100
                m2_f1 = float(m2_data.get("f1_score", 0.0)) * 100
                m2_st = m2_data.get("status")

                answer = (
                    f"**Model Comparison Analysis**:\n\n"
                    f"Winner: Version **{better}** performs better!\n\n"
                    f"- **{m1_name} ({m1_tag})**: Accuracy = {m1_acc:.1f}%, "
                    f"F1 = {m1_f1:.1f}% (Status: {m1_st})\n"
                    f"- **{m2_name} ({m2_tag})**: Accuracy = {m2_acc:.1f}%, "
                    f"F1 = {m2_f1:.1f}% (Status: {m2_st})\n\n"
                    f"_{exp}_"
                )

            elif "explain" in msg_lower or "why" in msg_lower or "fail" in msg_lower:
                tool_name = "explain_metrics"
                args = {"model_id_or_name": "churn-model"}
                res, duration = await self.execute_tool(
                    session,
                    principal,
                    ToolExecuteRequest(
                        workspace_id=payload.workspace_id, tool_name=tool_name, arguments=args
                    ),
                    request_id,
                )
                tools_used.append(tool_name)
                tool_results.append(
                    {"tool_name": tool_name, "result": res, "duration_ms": duration}
                )
                decision = res.get("decision", "REJECTED")
                reasons = res.get("failure_reasons", [])
                reasons_str = (
                    "\n".join([f"- {r}" for r in reasons])
                    if isinstance(reasons, list) and reasons
                    else "- All evaluation criteria passed successfully."
                )
                m_name = res.get("model_name")
                v_tag = res.get("version_tag")
                act_acc = float(res.get("actual_accuracy", 0.0)) * 100
                req_acc = float(res.get("required_accuracy", 0.0)) * 100
                act_f1 = float(res.get("actual_f1_score", 0.0)) * 100
                req_f1 = float(res.get("required_f1_score", 0.0)) * 100
                answer = (
                    f"**Quality Gate Diagnostics for {m_name} ({v_tag})**:\n\n"
                    f"Final Decision: **{decision}**\n\n"
                    f"Metrics Breakdown:\n"
                    f"- Accuracy: {act_acc:.1f}% (Required: {req_acc:.1f}%)\n"
                    f"- F1 Score: {act_f1:.1f}% (Required: {req_f1:.1f}%)\n\n"
                    f"Evaluation Diagnostics:\n{reasons_str}"
                )

            elif "summarize" in msg_lower or "dataset" in msg_lower and "list" not in msg_lower:
                tool_name = "summarize_dataset"
                args = {"dataset_id_or_name": "churn"}
                res, duration = await self.execute_tool(
                    session,
                    principal,
                    ToolExecuteRequest(
                        workspace_id=payload.workspace_id, tool_name=tool_name, arguments=args
                    ),
                    request_id,
                )
                tools_used.append(tool_name)
                tool_results.append(
                    {"tool_name": tool_name, "result": res, "duration_ms": duration}
                )
                cols = res.get("columns", [])
                col_str = ", ".join([f"`{c['name']}` ({c['inferred_type']})" for c in cols[:6]])
                answer = (
                    f"**Dataset Overview: `{res.get('original_filename')}`**:\n\n"
                    f"- **Status**: `{res.get('status')}`\n"
                    f"- **Total Rows**: {res.get('row_count'):,}\n"
                    f"- **Total Columns**: {res.get('column_count')}\n"
                    f"- **Feature Schema**: {col_str}..."
                )

            elif "predict" in msg_lower or "churn for" in msg_lower:
                tool_name = "run_prediction"
                # Extract numeric features if available in prompt
                age_m = re.search(r"age\s*=?\s*(\d+)", msg_lower)
                inc_m = re.search(r"income\s*=?\s*(\d+)", msg_lower)
                ten_m = re.search(r"tenure\s*=?\s*(\d+)", msg_lower)

                features = {
                    "age": float(age_m.group(1)) if age_m else 35.0,
                    "income": float(inc_m.group(1)) if inc_m else 55000.0,
                    "tenure": float(ten_m.group(1)) if ten_m else 4.0,
                }
                args = {"model_id_or_name": "churn", "input_features": features}
                res, duration = await self.execute_tool(
                    session,
                    principal,
                    ToolExecuteRequest(
                        workspace_id=payload.workspace_id, tool_name=tool_name, arguments=args
                    ),
                    request_id,
                )
                tools_used.append(tool_name)
                tool_results.append(
                    {"tool_name": tool_name, "result": res, "duration_ms": duration}
                )
                answer = (
                    f"**Real-Time Inference Output**:\n\n"
                    f"- **Predicted Label**: `{res.get('prediction', 'unknown').upper()}`\n"
                    f"- **Confidence Score**: {res.get('confidence', 0) * 100:.1f}%\n"
                    f"- **Model Version**: `{res.get('model_version')}`\n"
                    f"- **Latency**: `{res.get('latency_ms', 0):.2f} ms`"
                )

            elif "datasets" in msg_lower:
                tool_name = "list_datasets"
                res, duration = await self.execute_tool(
                    session,
                    principal,
                    ToolExecuteRequest(
                        workspace_id=payload.workspace_id, tool_name=tool_name, arguments={}
                    ),
                    request_id,
                )
                tools_used.append(tool_name)
                tool_results.append(
                    {"tool_name": tool_name, "result": res, "duration_ms": duration}
                )
                ds_list = res.get("datasets", [])
                ds_lines = [
                    f"- `{d['filename']}` ({d['status']}, {d.get('row_count', 'N/A')} rows)"
                    for d in ds_list
                ]
                answer = f"**Workspace Datasets ({res.get('count', 0)})**:\n\n" + (
                    "\n".join(ds_lines) if ds_lines else "No datasets found in this workspace."
                )

            else:
                # Default list models / workspace summary response
                tool_name = "list_models"
                res, duration = await self.execute_tool(
                    session,
                    principal,
                    ToolExecuteRequest(
                        workspace_id=payload.workspace_id, tool_name=tool_name, arguments={}
                    ),
                    request_id,
                )
                tools_used.append(tool_name)
                tool_results.append(
                    {"tool_name": tool_name, "result": res, "duration_ms": duration}
                )
                m_list = res.get("models", [])
                m_lines = [
                    f"- **{m['name']}** (`{m['version_tag']}`) — Status: `{m['status']}`"
                    for m in m_list
                ]
                answer = f"**Workspace Models ({res.get('count', 0)})**:\n\n" + (
                    "\n".join(m_lines) if m_lines else "No models registered in this workspace yet."
                )

            # Audit agent completion
            async with session.begin():
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="agent.completed",
                        resource_type="agent_chat",
                        resource_id=user.id,
                        request_id=request_id,
                        metadata_json={"tools_used": tools_used},
                    )
                )

            return AgentOrchestrateResponse(
                answer=answer,
                tools_used=tools_used,
                tool_results=tool_results,
            )

        except Exception as error:
            async with session.begin():
                session.add(
                    AuditEvent(
                        actor_user_id=user.id,
                        workspace_id=payload.workspace_id,
                        action="agent.failed",
                        resource_type="agent_chat",
                        resource_id=user.id,
                        request_id=request_id,
                        metadata_json={"error": str(error)},
                    )
                )
            raise error
