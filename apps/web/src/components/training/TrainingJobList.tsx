import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { Job, JobListResponse } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  IconCheckCircle,
  IconCpu,
  IconPlus,
  IconRefreshCw,
  IconXCircle,
} from "../ui/Icons";
import { Skeleton } from "../ui/Skeleton";

interface TrainingJobListProps {
  onOpenTrainModal: () => void;
  refreshTrigger: number;
}

export const TrainingJobList: React.FC<TrainingJobListProps> = ({
  onOpenTrainModal,
  refreshTrigger,
}) => {
  const { token } = useAuth();
  const { activeWorkspace, hasPermission } = useWorkspace();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const canCreateJob = hasPermission("task:create");

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, [activeWorkspace.id, refreshTrigger]);

  const fetchJobs = async () => {
    try {
      const data = await request<JobListResponse>(
        `/api/v1/workspaces/${activeWorkspace.id}/jobs?offset=0&limit=50`,
        { token }
      );
      const trainingJobs = data.items.filter((j) => j.job_type === "model_training");
      setJobs(trainingJobs);
      setError(null);
    } catch {
      setError("Failed to fetch model training background jobs.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Model Training Experiments</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Track asynchronous background model training, evaluation metrics, artifact locations, and quality gates.
          </p>
        </div>
        {canCreateJob && (
          <Button variant="primary" icon={<IconPlus size={16} />} onClick={onOpenTrainModal}>
            Train New Model
          </Button>
        )}
      </div>

      {error && (
        <Alert
          problem={{
            type: "about:blank",
            title: "Job Telemetry Error",
            status: 500,
            detail: error,
            code: "fetch_error",
            request_id: "unknown",
          }}
          onClose={() => setError(null)}
        />
      )}

      {isLoading ? (
        <div className="aura-card" style={{ padding: "2rem" }}>
          <Skeleton height="100px" className="mb-2" />
          <Skeleton height="100px" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconCpu size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>No Training Jobs Executed</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            Select an ingested CSV dataset to launch an asynchronous classifier training job and compute validation metrics.
          </p>
          {canCreateJob && (
            <Button variant="primary" icon={<IconPlus size={16} />} onClick={onOpenTrainModal}>
              Start First Model Training Job
            </Button>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {jobs.map((job) => {
            const res = job.result_json || {};
            const metrics = res.metrics || {};
            const payload = job.payload_json || {};

            return (
              <div key={job.id} className="aura-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                      <h4 style={{ fontSize: "1rem", fontWeight: 700, margin: 0 }}>
                        {payload.model_name || "Model Training Job"}
                      </h4>
                      <Badge variant={job.status}>{job.status}</Badge>
                      {res.version_tag && <Badge variant="purple">{res.version_tag}</Badge>}
                    </div>

                    <div
                      style={{
                        fontSize: "0.78125rem",
                        color: "var(--text-muted)",
                        marginTop: "0.35rem",
                        display: "flex",
                        gap: "1.25rem",
                        flexWrap: "wrap",
                      }}
                    >
                      <span>Algorithm: <strong style={{ color: "var(--text-secondary)" }}>{payload.model_type || "random_forest"}</strong></span>
                      <span>Target Column: <strong style={{ color: "var(--text-secondary)" }}>{payload.target_column || "N/A"}</strong></span>
                      <span>Dispatched: <strong style={{ color: "var(--text-secondary)" }}>{new Date(job.created_at).toLocaleTimeString()}</strong></span>
                    </div>
                  </div>

                  {job.status === "completed" && res.model_version_id && (
                    <Badge variant="success" icon={<IconCheckCircle size={13} />}>
                      Registered in Registry
                    </Badge>
                  )}
                </div>

                {/* Error Detail Container */}
                {job.status === "failed" && job.error_detail && (
                  <div
                    style={{
                      marginTop: "0.875rem",
                      padding: "0.75rem 1rem",
                      backgroundColor: "var(--status-danger-bg)",
                      border: "1px solid var(--status-danger-border)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "0.8125rem",
                      color: "var(--status-danger)",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                    }}
                  >
                    <IconXCircle size={16} />
                    <span><strong>Execution Failure:</strong> {job.error_detail}</span>
                  </div>
                )}

                {/* Completed Metrics Grid */}
                {job.status === "completed" && metrics.accuracy !== undefined && (
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
                      <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--status-success)" }}>
                        {(metrics.accuracy * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                        Precision
                      </span>
                      <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {(metrics.precision * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                        Recall
                      </span>
                      <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {(metrics.recall * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                        F1 Score
                      </span>
                      <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--accent-blue)" }}>
                        {(metrics.f1_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                        Execution Time
                      </span>
                      <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {metrics.training_duration_ms} ms
                      </span>
                    </div>
                  </div>
                )}

                {res.artifact_path && (
                  <div
                    style={{
                      marginTop: "0.75rem",
                      fontSize: "0.71875rem",
                      color: "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                      backgroundColor: "var(--bg-surface)",
                      padding: "0.35rem 0.65rem",
                      borderRadius: "var(--radius-xs)",
                      wordBreak: "break-all",
                    }}
                  >
                    Artifact Location: {res.artifact_path}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
