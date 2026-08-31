import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, icon, id, className = "", style, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="aura-form-group" style={{ width: "100%" }}>
        {label && (
          <label htmlFor={inputId} className="aura-label">
            {label}
          </label>
        )}
        <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
          {icon && (
            <div
              style={{
                position: "absolute",
                left: "0.75rem",
                color: "var(--text-muted)",
                display: "flex",
                alignItems: "center",
                pointerEvents: "none",
              }}
            >
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={`aura-input ${className}`}
            style={{
              paddingLeft: icon ? "2.25rem" : "0.875rem",
              borderColor: error ? "var(--status-danger)" : undefined,
              ...style,
            }}
            {...props}
          />
        </div>
        {error && (
          <span style={{ fontSize: "0.75rem", color: "var(--status-danger)", fontWeight: 500 }}>
            {error}
          </span>
        )}
        {helperText && !error && (
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{helperText}</span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
