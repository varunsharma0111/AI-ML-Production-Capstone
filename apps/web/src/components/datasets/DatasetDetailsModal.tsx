import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { Dataset, DatasetProfile, ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { IconDatabase, IconFileText } from "../ui/Icons";
import { Modal } from "../ui/Modal";

interface DatasetDetailsModalProps {
  dataset: Dataset | null;
  isOpen: boolean;
  onClose: () => void;
}

export const DatasetDetailsModal: React.FC<DatasetDetailsModalProps> = ({
  dataset,
  isOpen,
  onClose,
}) => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [activeTab, setActiveTab] = useState<"overview" | "schema" | "missing" | "stats">("overview");
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  useEffect(() => {
    if (isOpen && dataset) {
      setActiveTab("overview");
      setProfile(null);
      setProblem(null);
      if (dataset.status === "ready") {
        fetchProfile(dataset.id);
      }
    }
  }, [isOpen, dataset]);

  const fetchProfile = async (datasetId: string) => {
    setIsLoading(true);
    setProblem(null);
    try {
      const data = await request<DatasetProfile>(
        `/api/v1/datasets/${datasetId}/profile?workspace_id=${activeWorkspace.id}`,
        { token }
      );
      setProfile(data);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Profile Fetch Failed",
          status: 500,
          detail: "Could not retrieve automated dataset profiling results.",
          code: "fetch_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!dataset) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Dataset Profile: ${dataset.original_filename}`}
      subtitle="Automated schema inference, data health checks, missing value breakdown, and summary statistics."
      maxWidth="780px"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

        {/* Tab Navigation */}
        <div
          style={{
            display: "flex",
            gap: "0.5rem",
            borderBottom: "1px solid var(--border-subtle)",
            paddingBottom: "0.5rem",
          }}
        >
          {(["overview", "schema", "missing", "stats"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                background: activeTab === tab ? "var(--bg-surface)" : "transparent",
                color: activeTab === tab ? "var(--accent-blue)" : "var(--text-secondary)",
                border: activeTab === tab ? "1px solid var(--border-active)" : "1px solid transparent",
                borderRadius: "var(--radius-sm)",
                padding: "0.4rem 0.875rem",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: "pointer",
                textTransform: "capitalize",
                transition: "all var(--transition-fast)",
              }}
            >
              {tab === "overview" && "Metadata & Overview"}
              {tab === "schema" && "Inferred Schema"}
              {tab === "missing" && "Null Analysis"}
              {tab === "stats" && "Summary Statistics"}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
            <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                Status
              </span>
              <div style={{ marginTop: "0.35rem" }}>
                <Badge variant={dataset.status}>{dataset.status}</Badge>
              </div>
            </div>
            <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                File Size
              </span>
              <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {(dataset.file_size_bytes / 1024).toFixed(1)} KB
              </span>
            </div>
            <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                Row Count
              </span>
              <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {dataset.row_count !== null ? dataset.row_count.toLocaleString() : "Processing..."}
              </span>
            </div>
            <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                Column Count
              </span>
              <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {dataset.column_count !== null ? dataset.column_count : "Processing..."}
              </span>
            </div>
            <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)", gridColumn: "span 2" }}>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                Storage System Path
              </span>
              <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--text-secondary)", wordBreak: "break-all" }}>
                {dataset.storage_path}
              </span>
            </div>
          </div>
        )}

        {isLoading && (
          <div style={{ padding: "2.5rem", textAlign: "center", color: "var(--text-muted)" }}>
            <span className="spinner" style={{ width: "20px", height: "20px", margin: "0 auto 0.75rem" }} />
            <div>Fetching live profiling schema from background job engine...</div>
          </div>
        )}

        {/* Schema Tab */}
        {!isLoading && profile && activeTab === "schema" && (
          <div className="aura-table-container">
            <table className="aura-table">
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Inferred Type</th>
                  <th>Missing Count</th>
                  <th>Missing %</th>
                  <th>Unique Values</th>
                </tr>
              </thead>
              <tbody>
                {profile.columns_json.map((col) => (
                  <tr key={col.name}>
                    <td style={{ fontWeight: 600 }}>{col.name}</td>
                    <td>
                      <Badge variant="purple" size="sm">
                        {col.inferred_type}
                      </Badge>
                    </td>
                    <td>{col.missing_count}</td>
                    <td>
                      <Badge variant={col.missing_percentage > 10 ? "danger" : col.missing_percentage > 0 ? "warning" : "success"} size="sm">
                        {col.missing_percentage}%
                      </Badge>
                    </td>
                    <td>{col.unique_count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Missing Values Tab */}
        {!isLoading && profile && activeTab === "missing" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            {profile.columns_json.map((col) => (
              <div key={col.name} style={{ backgroundColor: "var(--bg-surface)", padding: "0.875rem", borderRadius: "var(--radius-sm)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: "0.35rem" }}>
                  <span style={{ fontWeight: 600 }}>{col.name}</span>
                  <span style={{ color: col.missing_percentage > 0 ? "var(--status-warning)" : "var(--status-success)", fontWeight: 500 }}>
                    {col.missing_count} nulls ({col.missing_percentage}%)
                  </span>
                </div>
                <div
                  style={{
                    height: "6px",
                    width: "100%",
                    backgroundColor: "var(--bg-card)",
                    borderRadius: "var(--radius-full)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${col.missing_percentage}%`,
                      backgroundColor: col.missing_percentage > 20 ? "var(--status-danger)" : "var(--status-warning)",
                      transition: "width var(--transition-normal)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary Stats Tab */}
        {!isLoading && profile && activeTab === "stats" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            {profile.columns_json.map((col) => (
              <div
                key={col.name}
                style={{
                  padding: "1rem",
                  backgroundColor: "var(--bg-surface)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>{col.name}</span>
                  <Badge variant="info" size="sm">{col.inferred_type}</Badge>
                </div>

                {col.min_value !== undefined && col.min_value !== null ? (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", fontSize: "0.8125rem" }}>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "0.5rem", borderRadius: "var(--radius-xs)" }}>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>MIN</span>
                      <strong style={{ fontFamily: "var(--font-mono)" }}>{col.min_value}</strong>
                    </div>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "0.5rem", borderRadius: "var(--radius-xs)" }}>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>MAX</span>
                      <strong style={{ fontFamily: "var(--font-mono)" }}>{col.max_value}</strong>
                    </div>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "0.5rem", borderRadius: "var(--radius-xs)" }}>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>MEAN</span>
                      <strong style={{ fontFamily: "var(--font-mono)" }}>{col.mean_value}</strong>
                    </div>
                  </div>
                ) : col.top_values && col.top_values.length > 0 ? (
                  <div>
                    <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", marginBottom: "0.35rem" }}>
                      Top Frequency Values:
                    </span>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                      {col.top_values.map((item, idx) => (
                        <span
                          key={idx}
                          style={{
                            fontSize: "0.71875rem",
                            padding: "0.2rem 0.5rem",
                            borderRadius: "var(--radius-xs)",
                            backgroundColor: "var(--bg-card)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          "{item.value}": <strong style={{ color: "var(--accent-blue)" }}>{item.count}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>No numerical distribution available</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
};
