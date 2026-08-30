import React from "react";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  maxLength?: number;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, id, maxLength, value, className = "", ...props }, ref) => {
    const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
    const currentLength = typeof value === "string" ? value.length : 0;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem", width: "100%" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {label && (
            <label
              htmlFor={textareaId}
              style={{
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "var(--text-secondary)",
              }}
            >
              {label}
            </label>
          )}
          {maxLength && (
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {currentLength} / {maxLength}
            </span>
          )}
        </div>
        <textarea
          ref={ref}
          id={textareaId}
          value={value}
          maxLength={maxLength}
          className={className}
          style={{
            width: "100%",
            minHeight: "100px",
            padding: "0.625rem 0.875rem",
            fontSize: "0.875rem",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
            border: `1px solid ${error ? "var(--status-danger)" : "var(--border-subtle)"}`,
            borderRadius: "var(--radius-sm)",
            outline: "none",
            resize: "vertical",
            fontFamily: "inherit",
          }}
          {...props}
        />
        {error && (
          <span style={{ fontSize: "0.75rem", color: "var(--status-danger)" }}>{error}</span>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
