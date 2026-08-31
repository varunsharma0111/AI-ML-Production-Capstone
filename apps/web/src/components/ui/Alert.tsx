import React from "react";
import { ProblemDetails } from "../../types/api";
import { IconAlertTriangle, IconCheckCircle, IconInfo, IconX, IconXCircle } from "./Icons";

interface AlertProps {
  variant?: "danger" | "warning" | "info" | "success";
  title?: string;
  problem?: ProblemDetails | null;
  message?: string;
  onRetry?: () => void;
  onClose?: () => void;
}

export const Alert: React.FC<AlertProps> = ({
  variant = "danger",
  title,
  problem,
  message,
  onRetry,
  onClose,
}) => {
  const displayTitle = title || (problem ? `${problem.title} (${problem.code})` : "System Notification");
  const displayDetail = message || problem?.detail || "";

  let bgVar = "var(--status-danger-bg)";
  let borderVar = "var(--status-danger-border)";
  let textVar = "var(--status-danger)";
  let IconComponent = IconXCircle;

  if (variant === "warning") {
    bgVar = "var(--status-warning-bg)";
    borderVar = "var(--status-warning-border)";
    textVar = "var(--status-warning)";
    IconComponent = IconAlertTriangle;
  } else if (variant === "success") {
    bgVar = "var(--status-success-bg)";
    borderVar = "var(--status-success-border)";
    textVar = "var(--status-success)";
    IconComponent = IconCheckCircle;
  } else if (variant === "info") {
    bgVar = "var(--status-info-bg)";
    borderVar = "var(--status-info-border)";
    textVar = "var(--status-info)";
    IconComponent = IconInfo;
  }

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        gap: "0.75rem",
        padding: "0.875rem 1rem",
        backgroundColor: bgVar,
        border: `1px solid ${borderVar}`,
        borderRadius: "var(--radius-sm)",
        color: "var(--text-primary)",
        marginBottom: "1rem",
      }}
    >
      <div style={{ color: textVar, marginTop: "0.1rem" }}>
        <IconComponent size={18} />
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong style={{ fontSize: "0.84375rem", fontWeight: 600, color: textVar }}>{displayTitle}</strong>
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Dismiss alert"
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                padding: 0,
                display: "flex",
                alignItems: "center",
              }}
            >
              <IconX size={16} />
            </button>
          )}
        </div>
        {displayDetail && <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", margin: 0 }}>{displayDetail}</p>}
        {problem?.request_id && (
          <small style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            Request ID: {problem.request_id}
          </small>
        )}
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              alignSelf: "flex-start",
              marginTop: "0.25rem",
              background: "none",
              border: "none",
              color: textVar,
              fontSize: "0.75rem",
              fontWeight: 600,
              textDecoration: "underline",
              cursor: "pointer",
            }}
          >
            Retry Request
          </button>
        )}
      </div>
    </div>
  );
};
