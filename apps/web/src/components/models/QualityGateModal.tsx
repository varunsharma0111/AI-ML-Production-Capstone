import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ModelVersion, ProblemDetails, QualityGateResponse } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconCheckCircle, IconShieldCheck, IconXCircle } from "../ui/Icons";
import { Modal } from "../ui/Modal";

interface QualityGateModalProps {
  isOpen: boolean;
  model: ModelVersion | null;
  qualityGate: QualityGateResponse | null;
  onClose: () => void;
  onEvaluated: () => void;
}

export const QualityGateModal: React.FC<QualityGateModalProps> = ({
  isOpen,
  model,
  qualityGate,
  onClose,
  onEvaluated,
}) => {
  const { token } = useAuth();
  const { activeWorkspace, hasPermission } = useWorkspace();

  const [accuracyThresh, setAccuracyThresh] = useState<number>(0.9);
  const [f1Thresh, setF1Thresh] = useState<number>(0.85);

  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  if (!model) return null;

  const canEvaluate = hasPermission("model:evaluate");
  const metrics = model.metrics_json || {};

  const acc = qualityGate ? qualityGate.accuracy : Number(metrics.accuracy || 0);
  const f1 = qualityGate ? qualityGate.f1_score : Number(metrics.f1_score || 0);

  const targetAccThresh = qualityGate ? qualityGate.accuracy_threshold : accuracyThresh;
  const targetF1Thresh = qualityGate ? qualityGate.f1_threshold : f1Thresh;

  const passedAcc = acc >= targetAccThresh;
  const passedF1 = f1 >= targetF1Thresh;
  const passedGate = qualityGate ? qualityGate.passed_gate : passedAcc && passedF1;

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setProblem(null);
    try {
      await request<ModelVersion>(`/api/v1/models/${model.id}/evaluate`, {
        method: "POST",
        token,
        body: {
          workspace_id: activeWorkspace.id,
          accuracy: acc,
          f1_score: f1,
          accuracy_threshold: accuracyThresh,
          f1_threshold: f1Thresh,
        },
      });
      onEvaluated();
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Evaluation Failure",
          status: 500,
          detail: err.message || "Failed to execute quality gate evaluation.",
          code: "eval_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Quality Gate Audit: ${model.name}`}
      subtitle="Evaluates classification performance against workspace policy constraints for staging/production readiness."
      maxWidth="640px"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

        {/* Quality Gate Status Card */}
        <div
          style={{
            padding: "1.25rem",
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-md)",
            border: `2px solid ${
              passedGate ? "var(--status-success)" : "var(--status-danger)"
            }`,
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <IconShieldCheck size={20} color={passedGate ? "var(--status-success)" : "var(--status-danger)"} />
              <span style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Policy Verification Status
              </span>
            </div>
            <Badge variant={passedGate ? "success" : "danger"}>
              {passedGate ? "APPROVED & PASSED" : "REJECTED BY POLICY"}
            </Badge>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.875rem" }}>
            {/* Accuracy Score */}
            <div style={{ padding: "0.875rem", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                Accuracy / Threshold
              </span>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: "0.25rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>{(acc * 100).toFixed(1)}% / {(targetAccThresh * 100).toFixed(1)}%</span>
                {passedAcc ? <IconCheckCircle size={18} color="var(--status-success)" /> : <IconXCircle size={18} color="var(--status-danger)" />}
              </div>
            </div>

            {/* F1 Score */}
            <div style={{ padding: "0.875rem", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                F1 Score / Threshold
              </span>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: "0.25rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>{(f1 * 100).toFixed(1)}% / {(targetF1Thresh * 100).toFixed(1)}%</span>
                {passedF1 ? <IconCheckCircle size={18} color="var(--status-success)" /> : <IconXCircle size={18} color="var(--status-danger)" />}
              </div>
            </div>
          </div>

          {qualityGate?.failure_reasons && qualityGate.failure_reasons.length > 0 && (
            <div
              style={{
                padding: "0.75rem",
                backgroundColor: "var(--status-danger-bg)",
                border: "1px solid var(--status-danger-border)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8125rem",
                color: "var(--status-danger)",
              }}
            >
              <strong>Rejection Reasons:</strong>
              <ul style={{ margin: "0.25rem 0 0 1.25rem", padding: 0 }}>
                {qualityGate.failure_reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Configurable Threshold Inputs */}
        {canEvaluate && (
          <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
            <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: "0.75rem" }}>
              Configure Custom Gate Thresholds
            </span>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.875rem" }}>
              <div className="aura-form-group">
                <label className="aura-label" style={{ fontSize: "0.71875rem" }}>Min Accuracy Threshold</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  max="1.0"
                  value={accuracyThresh}
                  onChange={(e) => setAccuracyThresh(Number(e.target.value))}
                  className="aura-input"
                />
              </div>
              <div className="aura-form-group">
                <label className="aura-label" style={{ fontSize: "0.71875rem" }}>Min F1-Score Threshold</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  max="1.0"
                  value={f1Thresh}
                  onChange={(e) => setF1Thresh(Number(e.target.value))}
                  className="aura-input"
                />
              </div>
            </div>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          {canEvaluate && (
            <Button
              variant="primary"
              onClick={handleEvaluate}
              isLoading={isEvaluating}
              icon={<IconShieldCheck size={16} />}
            >
              {isEvaluating ? "Evaluating..." : "Run Quality Gate Audit"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};
