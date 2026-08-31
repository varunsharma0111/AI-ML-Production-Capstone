import React from "react";

export type BadgeVariant =
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral"
  | "purple"
  | "ready"
  | "completed"
  | "profiling"
  | "uploaded"
  | "failed"
  | "queued"
  | "processing"
  | "cancelled"
  | "owner"
  | "editor"
  | "viewer"
  | "candidate"
  | "approved"
  | "staging"
  | "production"
  | "rejected";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant | string;
  icon?: React.ReactNode;
  className?: string;
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "neutral",
  icon,
  className = "",
  size = "md",
}) => {
  let variantClass = "aura-badge-neutral";

  const v = variant.toString().toLowerCase();

  if (["success", "ready", "completed", "approved", "production", "online"].includes(v)) {
    variantClass = "aura-badge-success";
  } else if (["warning", "profiling", "queued", "staging"].includes(v)) {
    variantClass = "aura-badge-warning";
  } else if (["danger", "failed", "cancelled", "rejected", "offline"].includes(v)) {
    variantClass = "aura-badge-danger";
  } else if (["info", "processing", "uploaded", "candidate"].includes(v)) {
    variantClass = "aura-badge-info";
  } else if (["purple", "owner", "editor"].includes(v)) {
    variantClass = "aura-badge-purple";
  }

  const paddingClass = size === "sm" ? "0.15rem 0.4rem" : "0.2rem 0.55rem";
  const fontSizeClass = size === "sm" ? "0.625rem" : "0.6875rem";

  return (
    <span
      className={`aura-badge ${variantClass} ${className}`}
      style={{ padding: paddingClass, fontSize: fontSizeClass }}
    >
      {icon && <span style={{ display: "inline-flex", alignItems: "center" }}>{icon}</span>}
      {children}
    </span>
  );
};
