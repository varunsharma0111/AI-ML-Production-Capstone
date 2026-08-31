import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  IconLogOut,
  IconMenu,
  IconMoon,
  IconSun,
  IconUser,
  IconZap,
} from "../ui/Icons";
import { HealthIndicator } from "./HealthIndicator";

interface HeaderProps {
  onNavigateHome?: () => void;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onNavigateHome, onToggleMobileMenu }) => {
  const { user, logout } = useAuth();
  const { activeWorkspace, availableWorkspaces, setActiveWorkspace } = useWorkspace();

  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = localStorage.getItem("auraml_theme");
    return saved === "light" ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("auraml_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <header className="aura-header" role="banner">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.75rem 1.5rem",
          gap: "1rem",
        }}
      >
        {/* Brand logo & Mobile menu toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {onToggleMobileMenu && (
            <button
              onClick={onToggleMobileMenu}
              aria-label="Toggle Navigation Menu"
              style={{
                background: "transparent",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                padding: "0.4rem",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <IconMenu size={18} />
            </button>
          )}

          <div
            onClick={onNavigateHome}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                onNavigateHome?.();
              }
            }}
            title="Navigate to Overview"
            style={{ display: "flex", alignItems: "center", gap: "0.75rem", cursor: "pointer" }}
          >
            <div
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "var(--radius-sm)",
                background: "linear-gradient(135deg, #2563EB, #7C3AED)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                boxShadow: "0 2px 8px rgba(37, 99, 235, 0.35)",
              }}
            >
              <IconZap size={18} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <h1 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
                  AuraML
                </h1>
                <span
                  style={{
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--accent-blue)",
                    backgroundColor: "var(--accent-blue-light)",
                    padding: "0.1rem 0.4rem",
                    borderRadius: "var(--radius-xs)",
                    border: "1px solid rgba(59, 130, 246, 0.3)",
                  }}
                >
                  Enterprise
                </span>
              </div>
              <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", display: "block", marginTop: "-1px" }}>
                AI/ML Production Platform
              </span>
            </div>
          </div>
        </div>

        {/* Workspace selector & System Telemetry */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <HealthIndicator />

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <label htmlFor="header-workspace-select" style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
              Workspace:
            </label>
            <select
              id="header-workspace-select"
              value={activeWorkspace.id}
              onChange={(e) => {
                const ws = availableWorkspaces.find((w) => w.id === e.target.value);
                if (ws) setActiveWorkspace(ws);
              }}
              className="aura-select"
              style={{
                padding: "0.35rem 0.65rem",
                fontSize: "0.8125rem",
                width: "auto",
                fontWeight: 500,
              }}
            >
              {availableWorkspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name}
                </option>
              ))}
            </select>
          </div>

          <Badge variant={activeWorkspace.role} size="sm">
            Role: {activeWorkspace.role}
          </Badge>

          {/* Dark / Light Theme Toggle */}
          <button
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
            aria-label="Toggle Theme Mode"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
              padding: "0.4rem 0.65rem",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.8125rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            {theme === "dark" ? <IconSun size={15} color="#F59E0B" /> : <IconMoon size={15} color="#8B5CF6" />}
            <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>
              {theme === "dark" ? "Light" : "Dark"}
            </span>
          </button>
        </div>

        {/* User profile & Logout */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-secondary)",
              }}
            >
              <IconUser size={16} />
            </div>
            <div style={{ textAlign: "right", display: "none" }} className="desktop-user-info">
              <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.2 }}>
                {user?.display_name || "Authenticated User"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                {user?.email || user?.subject}
              </div>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            icon={<IconLogOut size={15} />}
            aria-label="Sign out of platform"
          >
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
};
