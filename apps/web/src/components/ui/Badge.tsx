import React from "react";
import { TaskStatus, WorkspaceRole } from "../../types/api";

interface BadgeProps {
  children: React.ReactNode;
  variant?: TaskStatus | WorkspaceRole | "online" | "offline" | "neutral";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = "neutral", className = "" }) => {
  let badgeClass = "badge";

  if (variant === "open") badgeClass += " badge-open";
  else if (variant === "completed") badgeClass += " badge-completed";
  else if (variant === "owner" || variant === "editor" || variant === "viewer")
    badgeClass += " badge-role";
  else if (variant === "online")
    badgeClass += " badge-completed";
  else if (variant === "offline")
    badgeClass += " badge-open";

  return <span className={`${badgeClass} ${className}`}>{children}</span>;
};
