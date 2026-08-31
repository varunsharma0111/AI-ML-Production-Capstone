import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  IconActivity,
  IconBox,
  IconCheckCircle,
  IconCpu,
  IconDatabase,
  IconRefreshCw,
  IconShieldCheck,
  IconZap,
} from "../ui/Icons";
import { Skeleton } from "../ui/Skeleton";

interface SystemMetricsSummary {
  total_datasets: number;
  ready_datasets: number;
  profiling_datasets: number;
  failed_datasets: number;

  total_training_jobs: number;
  queued_jobs: number;
  processing_jobs: number;
  completed_jobs: number;
  failed_jobs: number;

  total_models: number;
  production_models: number;
  staging_models: number;
  approved_models: number;
  rejected_models: number;

  total_predictions: number;
  average_latency_ms: number;
}

interface OperationsDashboardData {
  system_status: string;
  api_status: string;
  database_status: string;
  metrics: SystemMetricsSummary;
}

export const OperationsDashboard: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const [data, setData] = useState<OperationsDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const fetchTelemetry = async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const res = await request<OperationsDashboardData>(
        `/api/v1/workspaces/${activeWorkspace.id}/operations/dashboard`,
        { token }
      );
      setData(res);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Telemetry Load Error",
          status: 400,
          detail: err.message || "Failed to load live platform operations telemetry.",
          code: "operations_load_failed",
          request_id: "unknown",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, [activeWorkspace.id]);

  const m = data?.metrics;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Platform Banner Header */}
      <div className="aura-card" style={{ padding: "1.5rem", background: "linear-gradient(135deg, var(--bg-card), var(--bg-surface))" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
              <IconActivity size={20} color="var(--accent-blue)" />
              <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Platform Operations & Live Telemetry</h2>
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: 0 }}>
              Operational health dashboard for workspace <strong>{activeWorkspace.name}</strong>. Monitor automated dataset profiling, model experiment runs, quality gates, and inference latencies.
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexShrink: 0 }}>
            <Badge variant="success" icon={<IconCheckCircle size={13} />}>
              PostgreSQL & API Healthy
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchTelemetry}
              isLoading={isLoading}
              icon={<IconRefreshCw size={14} />}
            >
              Refresh Telemetry
            </Button>
          </div>
        </div>
      </div>

      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      {/* Primary Telemetry Stat Cards */}
      {isLoading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
          <Skeleton height="140px" borderRadius="var(--radius-md)" />
          <Skeleton height="140px" borderRadius="var(--radius-md)" />
          <Skeleton height="140px" borderRadius="var(--radius-md)" />
          <Skeleton height="140px" borderRadius="var(--radius-md)" />
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
          {/* Datasets Metric */}
          <div className="aura-card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Datasets Ingestion
              </span>
              <div style={{ width: "32px", height: "32px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--accent-blue-light)", color: "var(--accent-blue)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <IconDatabase size={17} />
              </div>
            </div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
              {m?.total_datasets || 0}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
              <Badge variant="success" size="sm">Ready: {m?.ready_datasets || 0}</Badge>
              <Badge variant="warning" size="sm">Profiling: {m?.profiling_datasets || 0}</Badge>
              {m?.failed_datasets ? <Badge variant="danger" size="sm">Failed: {m.failed_datasets}</Badge> : null}
            </div>
          </div>

          {/* Model Training Metric */}
          <div className="aura-card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Training Jobs
              </span>
              <div style={{ width: "32px", height: "32px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--accent-purple-light)", color: "var(--accent-purple)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <IconCpu size={17} />
              </div>
            </div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
              {m?.total_training_jobs || 0}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
              <Badge variant="success" size="sm">Completed: {m?.completed_jobs || 0}</Badge>
              <Badge variant="warning" size="sm">Queued: {m?.queued_jobs || 0}</Badge>
              {m?.failed_jobs ? <Badge variant="danger" size="sm">Failed: {m.failed_jobs}</Badge> : null}
            </div>
          </div>

          {/* Model Registry Metric */}
          <div className="aura-card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Model Registry
              </span>
              <div style={{ width: "32px", height: "32px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--accent-teal-light)", color: "var(--accent-teal)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <IconBox size={17} />
              </div>
            </div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
              {m?.total_models || 0}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
              <Badge variant="purple" size="sm">Prod: {m?.production_models || 0}</Badge>
              <Badge variant="info" size="sm">Staging: {m?.staging_models || 0}</Badge>
              <Badge variant="success" size="sm">Approved: {m?.approved_models || 0}</Badge>
            </div>
          </div>

          {/* Real-Time Controlled Inference */}
          <div className="aura-card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Inference Volume
              </span>
              <div style={{ width: "32px", height: "32px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--status-success-bg)", color: "var(--status-success)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <IconZap size={17} />
              </div>
            </div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
              {m?.total_predictions || 0}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.75rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Avg Latency: <strong style={{ color: "var(--accent-blue)" }}>{m?.average_latency_ms || 0} ms</strong></span>
              <Badge variant="neutral" size="sm">Enforced</Badge>
            </div>
          </div>
        </div>
      )}

      {/* Lower Section: Actionable Insights & Status Grids */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1.25rem" }}>
        {/* Quality & Governance Panel */}
        <div className="aura-card">
          <div className="aura-card-header">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <IconShieldCheck size={18} color="var(--status-success)" />
              <h3 style={{ fontSize: "0.9375rem", margin: 0 }}>Governance & Quality Gate Integrity</h3>
            </div>
            <Badge variant="success" size="sm">Active Policy</Badge>
          </div>
          <div className="aura-card-body" style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8125rem", padding: "0.625rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ color: "var(--text-secondary)" }}>Min Accuracy Threshold</span>
              <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>90.0%</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8125rem", padding: "0.625rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ color: "var(--text-secondary)" }}>Min F1-Score Threshold</span>
              <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>85.0%</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8125rem", padding: "0.625rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ color: "var(--text-secondary)" }}>RBAC Promotion Gate</span>
              <strong style={{ color: "var(--accent-purple)" }}>Role: Owner/Editor Only</strong>
            </div>
          </div>
        </div>

        {/* Operational Checklist */}
        <div className="aura-card">
          <div className="aura-card-header">
            <h3 style={{ fontSize: "0.9375rem", margin: 0 }}>Platform Quick Actions</h3>
          </div>
          <div className="aura-card-body" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <a
              href="#datasets"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.75rem 1rem",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface)",
                textDecoration: "none",
                color: "var(--text-primary)",
                fontWeight: 500,
                fontSize: "0.8125rem",
                transition: "all var(--transition-fast)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                <IconDatabase size={16} color="var(--accent-blue)" />
                <span>Upload & Profile New CSV Dataset</span>
              </div>
              <span style={{ color: "var(--accent-blue)", fontSize: "0.75rem" }}>Launch →</span>
            </a>

            <a
              href="#training"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.75rem 1rem",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface)",
                textDecoration: "none",
                color: "var(--text-primary)",
                fontWeight: 500,
                fontSize: "0.8125rem",
                transition: "all var(--transition-fast)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                <IconCpu size={16} color="var(--accent-purple)" />
                <span>Trigger New Model Experiment</span>
              </div>
              <span style={{ color: "var(--accent-purple)", fontSize: "0.75rem" }}>Configure →</span>
            </a>

            <a
              href="#sandbox"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.75rem 1rem",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface)",
                textDecoration: "none",
                color: "var(--text-primary)",
                fontWeight: 500,
                fontSize: "0.8125rem",
                transition: "all var(--transition-fast)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                <IconZap size={16} color="var(--status-success)" />
                <span>Execute Real-Time Model Inference</span>
              </div>
              <span style={{ color: "var(--status-success)", fontSize: "0.75rem" }}>Open Sandbox →</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
