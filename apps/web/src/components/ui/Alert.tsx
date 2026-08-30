import React from "react";
import { ProblemDetails } from "../../types/api";

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
  const displayTitle = title || (problem ? `${problem.title} (${problem.code})` : "Notice");
  const displayDetail = message || problem?.detail || "";

  let bgColor = "rgba(239, 68, 68, 0.12)";
  let borderColor = "rgba(239, 68, 68, 0.3)";
  let textColor = "var(--status-danger)";

  if (variant === "warning") {
    bgColor = "rgba(245, 158, 11, 0.12)";
    borderColor = "rgba(245, 158, 11, 0.3)";
    textColor = "var(--status-warning)";
  } else if (variant === "success") {
    bgColor = "rgba(34, 197, 94, 0.12)";
    borderColor = "rgba(34, 197, 94, 0.3)";
    textColor = "var(--status-success)";
  } else if (variant === "info") {
    bgColor = "rgba(59, 130, 246, 0.12)";
    borderColor = "rgba(59, 130, 246, 0.3)";
    textColor = "var(--accent-blue)";
  }

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        padding: "1rem",
        backgroundColor: bgColor,
        border: `1px solid ${borderColor}`,
        borderRadius: "var(--radius-sm)",
        color: "var(--text-primary)",
        marginBottom: "1rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: "0.875rem", color: textColor }}>{displayTitle}</strong>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        )}
      </div>
      {displayDetail && <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>{displayDetail}</p>}
      {problem?.request_id && (
        <small style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
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
            color: textColor,
            fontSize: "0.75rem",
            fontWeight: 600,
            textDecoration: "underline",
            cursor: "pointer",
          }}
        >
          Try Again
        </button>
      )}
    </div>
  );
};
