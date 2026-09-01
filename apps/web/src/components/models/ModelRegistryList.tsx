import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ModelVersion, ProblemDetails, QualityGateResponse } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  IconBox,
  IconCheckCircle,
  IconShieldCheck,
  IconZap,
} from "../ui/Icons";
import { Skeleton } from "../ui/Skeleton";
import { QualityGateModal } from "./QualityGateModal";

interface ModelRegistryListProps {
  onRunInference?: (modelId: string) => void;
}

export const ModelRegistryList: React.FC<ModelRegistryListProps> = ({ onRunInference }) => {
  const { token } = useAuth();
  const { activeWorkspace, hasPermission } = useWorkspace();

  const [models, setModels] = useState<ModelVersion[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const [selectedModel, setSelectedModel] = useState<ModelVersion | null>(null);
  const [qualityGate, setQualityGate] = useState<QualityGateResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const canPromote = hasPermission("model:promote");
  const isOwner = activeWorkspace.role === "owner";

  useEffect(() => {
    fetchModels();
  }, [activeWorkspace.id]);

  const fetchModels = async () => {
    if (!activeWorkspace?.id) return;
    setIsLoading(true);
    try {
      const data = await request<ModelVersion[]>(
        `/api/v1/models?workspace_id=${activeWorkspace.id}`,
        { token }
      );
      setModels(data);
      setProblem(null);
    } catch (err: any) {
      if (err.problem) setProblem(err.problem);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenQualityGate = async (model: ModelVersion) => {
    setSelectedModel(model);
    try {
      const qg = await request<QualityGateResponse>(
        `/api/v1/models/${model.id}/quality-gate?workspace_id=${activeWorkspace.id}`,
        { token }
      );
      setQualityGate(qg);
    } catch {
      setQualityGate(null);
    }
    setIsModalOpen(true);
  };

  const handlePromote = async (modelId: string, targetStatus: "staging" | "production") => {
    setProblem(null);
    try {
      await request<ModelVersion>(`/api/v1/models/${modelId}/promote`, {
        method: "POST",
        token,
        body: {
          workspace_id: activeWorkspace.id,
          target_status: targetStatus,
        },
      });
      fetchModels();
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Promotion Rejected",
          status: 400,
          detail: err.message || "Model promotion failed quality or RBAC validation.",
          code: "promotion_error",
          request_id: "unknown",
        });
      }
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Model Registry & Governance Gate</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Track versioned machine learning artifacts, enforce automated quality policies, and control staging / production promotions.
          </p>
        </div>
      </div>

      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      {isLoading ? (
        <div className="aura-card" style={{ padding: "2rem" }}>
          <Skeleton height="120px" className="mb-2" />
          <Skeleton height="120px" />
        </div>
      ) : models.length === 0 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconBox size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>No Models Registered</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            Dispatch a training job from the Model Training section to automatically register a candidate model version.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {models.map((model) => {
            const metrics = model.metrics_json || {};

            const isApproved = model.status === "approved";
            const isStaging = model.status === "staging";
            const isProduction = model.status === "production";
            const isEligibleForInference = isApproved || isStaging || isProduction;

            return (
              <div key={model.id} className="aura-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                      <h4 style={{ fontSize: "1.125rem", fontWeight: 700, margin: 0 }}>
                        {model.name}
                      </h4>
                      <Badge variant="purple" size="sm">{model.version_tag}</Badge>
                      <Badge variant={model.status}>{model.status.toUpperCase()}</Badge>
                    </div>

                    <div style={{ fontSize: "0.78125rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>
                      Dataset ID: <span style={{ fontFamily: "var(--font-mono)" }}>{model.dataset_id || "N/A"}</span> • Job ID: <span style={{ fontFamily: "var(--font-mono)" }}>{model.job_id || "N/A"}</span>
                    </div>
                  </div>

                  {/* Actions Header */}
                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    {isEligibleForInference && onRunInference && (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={<IconZap size={14} />}
                        onClick={() => onRunInference(model.id)}
                      >
                        Run Inference
                      </Button>
                    )}

                    <Button
                      variant="ghost"
                      size="sm"
                      icon={<IconShieldCheck size={14} />}
                      onClick={() => handleOpenQualityGate(model)}
                    >
                      Quality Gate
                    </Button>

                    {canPromote && isApproved && (
                      <Button
                        variant="primary"
                        size="sm"
                        icon={<IconZap size={14} />}
                        onClick={() => handlePromote(model.id, "staging")}
                      >
                        Promote Staging
                      </Button>
                    )}

                    {canPromote && (isApproved || isStaging) && isOwner && (
                      <Button
                        variant="primary"
                        size="sm"
                        icon={<IconCheckCircle size={14} />}
                        style={{ backgroundColor: "var(--status-success)" }}
                        onClick={() => handlePromote(model.id, "production")}
                      >
                        Promote Production
                      </Button>
                    )}
                  </div>
                </div>

                {/* Metrics Row */}
                <div
                  style={{
                    marginTop: "1rem",
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                    gap: "0.75rem",
                    backgroundColor: "var(--bg-surface)",
                    padding: "0.875rem 1rem",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                      Accuracy
                    </span>
                    <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      {metrics.accuracy !== undefined ? `${(Number(metrics.accuracy) * 100).toFixed(1)}%` : "N/A"}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                      Precision
                    </span>
                    <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      {metrics.precision !== undefined ? `${(Number(metrics.precision) * 100).toFixed(1)}%` : "N/A"}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                      Recall
                    </span>
                    <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      {metrics.recall !== undefined ? `${(Number(metrics.recall) * 100).toFixed(1)}%` : "N/A"}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                      F1 Score
                    </span>
                    <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--accent-blue)" }}>
                      {metrics.f1_score !== undefined ? `${(Number(metrics.f1_score) * 100).toFixed(1)}%` : "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <QualityGateModal
        isOpen={isModalOpen}
        model={selectedModel}
        qualityGate={qualityGate}
        onClose={() => setIsModalOpen(false)}
        onEvaluated={() => {
          setIsModalOpen(false);
          fetchModels();
        }}
      />
    </div>
  );
};
