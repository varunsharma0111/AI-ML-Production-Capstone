import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconRefreshCw, IconSearch, IconShield } from "../ui/Icons";
import { Skeleton } from "../ui/Skeleton";

interface AuditEventItem {
  id: string;
  actor_user_id: string;
  workspace_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  request_id: string;
  metadata_json: Record<string, any>;
  occurred_at: string;
}

export const AuditLogViewer: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");

  const fetchAuditLogs = async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const res = await request<AuditEventItem[]>(
        `/api/v1/workspaces/${activeWorkspace.id}/audit-logs`,
        { token }
      );
      setEvents(res);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Audit Log Fetch Error",
          status: 400,
          detail: err.message || "Failed to load workspace security audit logs.",
          code: "audit_logs_load_failed",
          request_id: "unknown",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [activeWorkspace.id]);

  const filteredEvents = events.filter((evt) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      evt.action.toLowerCase().includes(term) ||
      evt.resource_type.toLowerCase().includes(term) ||
      evt.request_id.toLowerCase().includes(term)
    );
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Security Audit Event Log</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Tamper-evident audit trail of all workspace actions, evaluations, promotions, inferences, and tool executions.
          </p>
        </div>
        <Button variant="outline" size="sm" icon={<IconRefreshCw size={14} />} onClick={fetchAuditLogs} isLoading={isLoading}>
          Refresh Trail
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
          placeholder="Filter audit events by action (e.g. model.promoted, dataset.uploaded) or request ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="aura-input"
          style={{ paddingLeft: "2.35rem" }}
        />
      </div>

      {isLoading ? (
        <div className="aura-card" style={{ padding: "2rem" }}>
          <Skeleton height="30px" className="mb-2" />
          <Skeleton height="50px" className="mb-2" />
          <Skeleton height="50px" />
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconShield size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>No Audit Events Recorded</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            Audit events automatically log when actions occur within this workspace.
          </p>
        </div>
      ) : (
        <div className="aura-table-container">
          <table className="aura-table">
            <thead>
              <tr>
                <th>Occurred At</th>
                <th>Action Event</th>
                <th>Resource Target</th>
                <th>Correlation ID</th>
                <th>Metadata Payload</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((evt) => (
                <tr key={evt.id}>
                  <td style={{ color: "var(--text-secondary)", fontSize: "0.78125rem" }}>
                    {new Date(evt.occurred_at).toLocaleString()}
                  </td>
                  <td>
                    <Badge variant="purple" size="sm">
                      {evt.action}
                    </Badge>
                  </td>
                  <td style={{ fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                    {evt.resource_type} ({evt.resource_id.slice(0, 8)}...)
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78125rem", color: "var(--text-muted)" }}>
                    {evt.request_id.slice(0, 8)}...
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    {JSON.stringify(evt.metadata_json)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
