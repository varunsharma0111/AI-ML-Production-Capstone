import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ModelVersion, ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconCheckCircle, IconGitCompare, IconRefreshCw } from "../ui/Icons";
import { Skeleton } from "../ui/Skeleton";

export const ModelComparisonView: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const [modelAId, setModelAId] = useState<string>("");
  const [modelBId, setModelBId] = useState<string>("");

  const fetchModels = async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const res = await request<ModelVersion[]>(`/api/v1/models?workspace_id=${activeWorkspace.id}`, { token });
      setModels(res);
      if (res.length >= 2) {
        setModelAId(res[0].id);
        setModelBId(res[1].id);
      } else if (res.length === 1) {
        setModelAId(res[0].id);
      }
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Models Fetch Error",
          status: 400,
          detail: err.message || "Failed to load models for comparison.",
          code: "models_load_failed",
          request_id: "unknown",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, [activeWorkspace.id]);

  const modelA = models.find((m) => m.id === modelAId);
  const modelB = models.find((m) => m.id === modelBId);

  const getMetric = (m: ModelVersion | undefined, key: string): string => {
    if (!m || !m.metrics_json) return "N/A";
    const val = m.metrics_json[key];
    if (typeof val === "number") {
      return (val * 100).toFixed(1) + "%";
    }
    return val ?? "N/A";
  };

  const getRawMetric = (m: ModelVersion | undefined, key: string): number => {
    if (!m || !m.metrics_json) return 0;
    return Number(m.metrics_json[key] || 0);
  };

  const f1A = getRawMetric(modelA, "f1_score");
  const f1B = getRawMetric(modelB, "f1_score");
  const betterModel = f1A > f1B ? modelA : f1B > f1A ? modelB : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Model Version Comparison</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Side-by-side performance evaluation, classification metrics, and training duration comparison.
          </p>
        </div>
        <Button variant="outline" size="sm" icon={<IconRefreshCw size={14} />} onClick={fetchModels} isLoading={isLoading}>
          Refresh Models
        </Button>
      </div>

      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      {isLoading ? (
        <div className="aura-card" style={{ padding: "2rem" }}>
          <Skeleton height="100px" className="mb-2" />
          <Skeleton height="200px" />
        </div>
      ) : models.length < 2 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconGitCompare size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>Insufficient Models for Comparison</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            You need at least 2 trained model versions in this workspace to run side-by-side comparative diagnostics.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Winner Banner */}
          {betterModel && (
            <div
              style={{
                backgroundColor: "var(--status-success-bg)",
                border: "1px solid var(--status-success-border)",
                borderRadius: "var(--radius-md)",
                padding: "1rem 1.25rem",
                display: "flex",
                alignItems: "center",
                gap: "1rem",
              }}
            >
              <IconCheckCircle size={24} color="var(--status-success)" />
              <div>
                <div style={{ fontWeight: 700, color: "var(--status-success)", fontSize: "0.9375rem" }}>
                  Recommended Champion: {betterModel.name} ({betterModel.version_tag})
                </div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "0.15rem" }}>
                  Outperforms candidate with an F1 score of {getMetric(betterModel, "f1_score")} and accuracy of {getMetric(betterModel, "accuracy")}.
                </div>
              </div>
            </div>
          )}

          {/* Model Selectors */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div className="aura-card" style={{ padding: "1.25rem" }}>
              <div className="aura-form-group">
                <label className="aura-label">Select Model Version A</label>
                <select
                  value={modelAId}
                  onChange={(e) => setModelAId(e.target.value)}
                  className="aura-select"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.version_tag}) — {m.status.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="aura-card" style={{ padding: "1.25rem" }}>
              <div className="aura-form-group">
                <label className="aura-label">Select Model Version B</label>
                <select
                  value={modelBId}
                  onChange={(e) => setModelBId(e.target.value)}
                  className="aura-select"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.version_tag}) — {m.status.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Comparative Metrics Table */}
          <div className="aura-table-container">
            <table className="aura-table">
              <thead>
                <tr>
                  <th style={{ width: "30%" }}>Metric / Parameter</th>
                  <th style={{ width: "35%" }}>
                    Model A: {modelA ? `${modelA.name} (${modelA.version_tag})` : "-"}
                  </th>
                  <th style={{ width: "35%" }}>
                    Model B: {modelB ? `${modelB.name} (${modelB.version_tag})` : "-"}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 600 }}>Lifecycle Status</td>
                  <td>
                    {modelA ? <Badge variant={modelA.status}>{modelA.status.toUpperCase()}</Badge> : "N/A"}
                  </td>
                  <td>
                    {modelB ? <Badge variant={modelB.status}>{modelB.status.toUpperCase()}</Badge> : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>F1 Score</td>
                  <td style={{ fontWeight: 700, color: f1A > f1B ? "var(--status-success)" : "var(--text-primary)" }}>
                    {getMetric(modelA, "f1_score")}
                  </td>
                  <td style={{ fontWeight: 700, color: f1B > f1A ? "var(--status-success)" : "var(--text-primary)" }}>
                    {getMetric(modelB, "f1_score")}
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Accuracy</td>
                  <td>{getMetric(modelA, "accuracy")}</td>
                  <td>{getMetric(modelB, "accuracy")}</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Precision</td>
                  <td>{getMetric(modelA, "precision")}</td>
                  <td>{getMetric(modelB, "precision")}</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Recall</td>
                  <td>{getMetric(modelA, "recall")}</td>
                  <td>{getMetric(modelB, "recall")}</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Training Duration</td>
                  <td>{modelA?.metrics_json?.training_duration_ms ? `${modelA.metrics_json.training_duration_ms} ms` : "N/A"}</td>
                  <td>{modelB?.metrics_json?.training_duration_ms ? `${modelB.metrics_json.training_duration_ms} ms` : "N/A"}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
