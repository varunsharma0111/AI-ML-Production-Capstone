import React from "react";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  maxLength?: number;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, id, maxLength, value, className = "", style, ...props }, ref) => {
    const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
    const currentLength = typeof value === "string" ? value.length : 0;

    return (
      <div className="aura-form-group" style={{ width: "100%" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {label && (
            <label htmlFor={textareaId} className="aura-label">
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
          className={`aura-textarea ${className}`}
          style={{
            minHeight: "100px",
            borderColor: error ? "var(--status-danger)" : undefined,
            ...style,
          }}
          {...props}
        />
        {error && (
          <span style={{ fontSize: "0.75rem", color: "var(--status-danger)", fontWeight: 500 }}>
            {error}
          </span>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
