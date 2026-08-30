import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, id, className = "", ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem", width: "100%" }}>
        {label && (
          <label
            htmlFor={inputId}
            style={{
              fontSize: "0.875rem",
              fontWeight: 500,
              color: "var(--text-secondary)",
            }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={className}
          style={{
            width: "100%",
            padding: "0.625rem 0.875rem",
            fontSize: "0.875rem",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
            border: `1px solid ${error ? "var(--status-danger)" : "var(--border-subtle)"}`,
            borderRadius: "var(--radius-sm)",
            outline: "none",
            transition: "border-color var(--transition-fast)",
          }}
          {...props}
        />
        {error && (
          <span style={{ fontSize: "0.75rem", color: "var(--status-danger)" }}>{error}</span>
        )}
        {helperText && !error && (
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{helperText}</span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
