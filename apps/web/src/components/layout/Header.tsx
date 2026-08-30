import React from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { HealthIndicator } from "./HealthIndicator";

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const { activeWorkspace, availableWorkspaces, setActiveWorkspace } = useWorkspace();

  return (
    <header
      className="glass-panel"
      style={{
        borderRadius: 0,
        borderLeft: "none",
        borderRight: "none",
        borderTop: "none",
        padding: "0.875rem 1.5rem",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      <div
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        {/* Brand & Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "var(--radius-sm)",
              background: "linear-gradient(135deg, var(--accent-blue), var(--accent-purple))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              color: "#fff",
              fontSize: "1.125rem",
            }}
          >
            AI
          </div>
          <div>
            <h1 style={{ fontSize: "1.125rem", fontWeight: 700, lineHeight: 1.2 }}>
              AI/ML Production Platform
            </h1>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Phase 3 — Secure Modular Monolith
            </span>
          </div>
        </div>

        {/* Workspace Selector & Health Status */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <HealthIndicator />

          <select
            value={activeWorkspace.id}
            onChange={(e) => {
              const ws = availableWorkspaces.find((w) => w.id === e.target.value);
              if (ws) setActiveWorkspace(ws);
            }}
            style={{
              padding: "0.45rem 0.75rem",
              fontSize: "0.875rem",
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              outline: "none",
              cursor: "pointer",
            }}
          >
            {availableWorkspaces.map((ws) => (
              <option key={ws.id} value={ws.id}>
                {ws.name}
              </option>
            ))}
          </select>

          <Badge variant={activeWorkspace.role}>Role: {activeWorkspace.role}</Badge>
        </div>

        {/* User Info & Logout */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.875rem" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.875rem", fontWeight: 600 }}>
              {user?.display_name || "Authenticated User"}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {user?.email || user?.subject}
            </div>
          </div>
          <Button variant="ghost" onClick={logout}>
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
};
