import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ModelVersion, PredictResponsePayload, ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconAlertTriangle, IconPlay, IconZap } from "../ui/Icons";

interface InferenceSandboxProps {
  initialModelId?: string;
}

export const InferenceSandbox: React.FC<InferenceSandboxProps> = ({ initialModelId }) => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [models, setModels] = useState<ModelVersion[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>(initialModelId || "");
  const [featureInputs, setFeatureInputs] = useState<Record<string, string>>({});

  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [predictionResult, setPredictionResult] = useState<PredictResponsePayload | null>(null);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  useEffect(() => {
    fetchModels();
  }, [activeWorkspace.id]);

  const fetchModels = async () => {
    try {
      const data = await request<ModelVersion[]>(
        `/api/v1/models?workspace_id=${activeWorkspace.id}`,
        { token }
      );
      setModels(data);

      if (data.length > 0) {
        const initial = initialModelId && data.some((m) => m.id === initialModelId)
          ? initialModelId
          : data[0].id;
        setSelectedModelId(initial);
      }
    } catch (err: any) {
      if (err.problem) setProblem(err.problem);
    }
  };

  const selectedModel = models.find((m) => m.id === selectedModelId) || null;
  const metrics = selectedModel?.metrics_json || {};

  const featureNames: string[] = metrics.target_column
    ? ["age", "income", "tenure"]
    : ["feature_1", "feature_2"];

  useEffect(() => {
    if (selectedModel) {
      const initialFeatures: Record<string, string> = {};
      featureNames.forEach((fn) => {
        initialFeatures[fn] = "35";
      });
      setFeatureInputs(initialFeatures);
      setPredictionResult(null);
      setProblem(null);
    }
  }, [selectedModelId]);

  const isEligible =
    selectedModel && ["approved", "staging", "production"].includes(selectedModel.status);

  const handleInputChange = (fieldName: string, value: string) => {
    setFeatureInputs((prev) => ({ ...prev, [fieldName]: value }));
  };

  const handleRunPrediction = async () => {
    if (!selectedModel) return;
    setIsRunning(true);
    setProblem(null);
    setPredictionResult(null);

    const parsedFeatures: Record<string, number> = {};
    for (const [key, val] of Object.entries(featureInputs)) {
      parsedFeatures[key] = parseFloat(val) || 0.0;
    }

    try {
      const res = await request<PredictResponsePayload>(
        `/api/v1/models/${selectedModel.id}/predict`,
        {
          method: "POST",
          token,
          body: {
            workspace_id: activeWorkspace.id,
            input_features: parsedFeatures,
          },
        }
      );
      setPredictionResult(res);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Inference Error",
          status: 400,
          detail: err.message || "Failed to execute model prediction.",
          code: "predict_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Real-Time Inference Sandbox</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
          Execute real-time model predictions using registered models that have satisfied quality gate criteria.
        </p>
      </div>

      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "1.5rem" }}>
        {/* Model Selector & Inputs Card */}
        <div className="aura-card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="aura-form-group">
            <label className="aura-label">Target Model Version</label>
            <select
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(e.target.value)}
              className="aura-select"
            >
              {models.length === 0 ? (
                <option value="">No models available</option>
              ) : (
                models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.version_tag}) — [{m.status.toUpperCase()}]
                  </option>
                ))
              )}
            </select>
          </div>

          {selectedModel && (
            <div style={{ padding: "0.875rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>{selectedModel.name}</span>
                <Badge variant={isEligible ? "success" : "danger"}>
                  {selectedModel.status.toUpperCase()}
                </Badge>
              </div>
              <div style={{ fontSize: "0.71875rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginTop: "0.35rem" }}>
                Path: {selectedModel.artifact_path}
              </div>
            </div>
          )}

          {/* Blocked Model UX Banner */}
          {selectedModel && !isEligible && (
            <div
              style={{
                padding: "1rem",
                backgroundColor: "var(--status-danger-bg)",
                border: "1px solid var(--status-danger-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--status-danger)",
                fontSize: "0.84375rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                <IconAlertTriangle size={16} />
                <span>Inference Blocked by Policy</span>
              </div>
              <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                Model state standard is candidate/rejected (`{selectedModel.status}`). Audit and promote this model to Staging/Production in the Model Registry before invoking real-time endpoints.
              </p>
            </div>
          )}

          {/* Input Features Form */}
          {selectedModel && isEligible && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Feature Vector Inputs
              </span>

              {featureNames.map((fName) => (
                <div key={fName} className="aura-form-group">
                  <label className="aura-label" style={{ fontSize: "0.75rem" }}>
                    {fName} (Numeric Feature)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={featureInputs[fName] || ""}
                    onChange={(e) => handleInputChange(fName, e.target.value)}
                    className="aura-input"
                  />
                </div>
              ))}

              <Button
                variant="primary"
                onClick={handleRunPrediction}
                isLoading={isRunning}
                icon={<IconZap size={16} />}
                style={{ marginTop: "0.5rem" }}
              >
                {isRunning ? "Executing Inference..." : "Execute Real-Time Prediction"}
              </Button>
            </div>
          )}
        </div>

        {/* Prediction Results Display Card */}
        <div className="aura-card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0 }}>Inference Execution Output</h3>

          {!predictionResult ? (
            <div className="aura-empty-state" style={{ padding: "2.5rem 1rem", border: "none" }}>
              <div className="aura-empty-icon">
                <IconPlay size={22} />
              </div>
              <h4 style={{ fontSize: "1rem", margin: 0 }}>Awaiting Inference Trigger</h4>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", maxWidth: "320px", margin: 0 }}>
                Configure numeric feature parameters and click "Execute Real-Time Prediction" to view class output and confidence score.
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              {/* Primary Output Callout */}
              <div
                style={{
                  padding: "1.5rem",
                  backgroundColor: "var(--bg-surface)",
                  borderRadius: "var(--radius-md)",
                  border: "2px solid var(--accent-blue)",
                  textAlign: "center",
                }}
              >
                <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.06em" }}>
                  Predicted Class Label
                </span>
                <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--accent-blue)", margin: "0.25rem 0" }}>
                  {predictionResult.prediction.toUpperCase()}
                </div>
                <Badge variant="info" size="sm">
                  Model Version: {predictionResult.model_version}
                </Badge>
              </div>

              {/* Confidence & Latency */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
                  <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                    Confidence Score
                  </span>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--status-success)", marginTop: "0.25rem" }}>
                    {(predictionResult.confidence * 100).toFixed(1)}%
                  </div>
                  <div style={{ height: "6px", width: "100%", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-full)", marginTop: "0.5rem", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${predictionResult.confidence * 100}%`, backgroundColor: "var(--status-success)" }} />
                  </div>
                </div>

                <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
                  <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                    Serving Latency
                  </span>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "0.25rem" }}>
                    {predictionResult.latency_ms.toFixed(2)} ms
                  </div>
                  <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", marginTop: "0.35rem", display: "block" }}>
                    Enforced SHA-256 Engine
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
