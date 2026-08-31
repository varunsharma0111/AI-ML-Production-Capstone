import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconHistory, IconRefreshCw, IconSearch } from "../ui/Icons";
import { Modal } from "../ui/Modal";
import { Skeleton } from "../ui/Skeleton";

interface PredictionLogItem {
  id: string;
  model_version_id: string;
  workspace_id: string;
  input_features: Record<string, any>;
  prediction: {
    prediction: string;
    confidence?: number;
    [key: string]: any;
  };
  latency_ms: number;
  created_at: string;
}

export const PredictionHistory: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const [logs, setLogs] = useState<PredictionLogItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedLog, setSelectedLog] = useState<PredictionLogItem | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const res = await request<PredictionLogItem[]>(
        `/api/v1/workspaces/${activeWorkspace.id}/predictions`,
        { token }
      );
      setLogs(res);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Telemetry Load Error",
          status: 400,
          detail: err.message || "Failed to load prediction telemetry history.",
          code: "predictions_load_failed",
          request_id: "unknown",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [activeWorkspace.id]);

  const filteredLogs = logs.filter((item) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const predStr = String(item.prediction?.prediction || "").toLowerCase();
    const featStr = JSON.stringify(item.input_features).toLowerCase();
    return predStr.includes(term) || featStr.includes(term) || item.id.includes(term);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Prediction History Telemetry</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Audit log of real-time classification prediction payloads served by model inference endpoints.
          </p>
        </div>
        <Button variant="outline" size="sm" icon={<IconRefreshCw size={14} />} onClick={fetchLogs} isLoading={isLoading}>
          Refresh History
        </Button>
      </div>

      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      {/* Filter Input */}
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <div style={{ position: "absolute", left: "0.875rem", color: "var(--text-muted)", pointerEvents: "none" }}>
          <IconSearch size={16} />
        </div>
        <input
          type="text"
          placeholder="Filter predictions by class label, features, or ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="aura-input"
          style={{ paddingLeft: "2.35rem" }}
        />
      </div>

      {/* Prediction History Table */}
      {isLoading ? (
        <div className="aura-card" style={{ padding: "2rem" }}>
          <Skeleton height="30px" className="mb-2" />
          <Skeleton height="50px" className="mb-2" />
          <Skeleton height="50px" />
        </div>
      ) : filteredLogs.length === 0 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconHistory size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>No Prediction Telemetry Logs</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            Execute predictions using the Inference Sandbox to populate the audit log.
          </p>
        </div>
      ) : (
        <div className="aura-table-container">
          <table className="aura-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Model ID</th>
                <th>Predicted Class</th>
                <th>Confidence</th>
                <th>Serving Latency</th>
                <th style={{ textAlign: "right" }}>Inspection</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => {
                const conf = log.prediction?.confidence
                  ? (log.prediction.confidence * 100).toFixed(1) + "%"
                  : "N/A";
                const pred = log.prediction?.prediction ?? "Unknown";

                return (
                  <tr key={log.id}>
                    <td style={{ color: "var(--text-secondary)", fontSize: "0.78125rem" }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78125rem" }}>
                      {log.model_version_id.slice(0, 8)}...
                    </td>
                    <td>
                      <Badge variant="info">{String(pred)}</Badge>
                    </td>
                    <td style={{ fontWeight: 600, color: "var(--status-success)" }}>{conf}</td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78125rem" }}>
                      {log.latency_ms.toFixed(2)} ms
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setSelectedLog(log)}
                      >
                        Inspect Features
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Feature Payload Inspection Modal */}
      <Modal
        isOpen={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        title="Prediction Feature Payload Inspection"
        subtitle="Raw feature vector and model confidence breakdown."
      >
        {selectedLog && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                padding: "1rem",
                borderRadius: "var(--radius-sm)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8125rem",
                maxHeight: "300px",
                overflowY: "auto",
                whiteSpace: "pre-wrap",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {JSON.stringify(selectedLog.input_features, null, 2)}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Button variant="secondary" onClick={() => setSelectedLog(null)}>
                Close Inspection
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
