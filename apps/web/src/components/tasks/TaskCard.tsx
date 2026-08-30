import React from "react";
import { useWorkspace } from "../../context/WorkspaceContext";
import { Task } from "../../types/api";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface TaskCardProps {
  task: Task;
  onEdit: (task: Task) => void;
  onToggleStatus: (task: Task) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({ task, onEdit, onToggleStatus }) => {
  const { hasPermission } = useWorkspace();
  const canUpdate = hasPermission("task:update");

  const formattedDate = new Date(task.updated_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <article
      className="glass-panel"
      style={{
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: "1rem",
        transition: "border-color var(--transition-fast), transform var(--transition-fast)",
      }}
    >
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem", marginBottom: "0.5rem" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {task.title}
          </h3>
          <Badge variant={task.status}>{task.status}</Badge>
        </div>

        {task.description && (
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "0.75rem", whiteSpace: "pre-wrap" }}>
            {task.description}
          </p>
        )}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          paddingTop: "0.75rem",
          borderTop: "1px solid var(--border-subtle)",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
        }}
      >
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <span>v{task.version}</span>
          <span>•</span>
          <span>Updated {formattedDate}</span>
        </div>

        {canUpdate && (
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <Button
              variant="ghost"
              style={{ padding: "0.25rem 0.625rem", fontSize: "0.75rem" }}
              onClick={() => onToggleStatus(task)}
            >
              {task.status === "open" ? "Mark Complete" : "Reopen"}
            </Button>
            <Button
              variant="secondary"
              style={{ padding: "0.25rem 0.625rem", fontSize: "0.75rem" }}
              onClick={() => onEdit(task)}
            >
              Edit
            </Button>
          </div>
        )}
      </div>
    </article>
  );
};
