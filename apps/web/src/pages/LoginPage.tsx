import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { IconCpu, IconKey, IconLock } from "../components/ui/Icons";
import { Input } from "../components/ui/Input";

export const LoginPage: React.FC = () => {
  const { login, loginWithDevToken, error } = useAuth();
  const [devTokenInput, setDevTokenInput] = useState("");

  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (devTokenInput.trim()) {
      await loginWithDevToken(devTokenInput.trim());
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
        backgroundColor: "var(--bg-dark)",
        backgroundImage: "radial-gradient(ellipse at 50% 0%, var(--accent-purple-light), transparent 70%)",
      }}
    >
      <div
        className="aura-card animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "440px",
          padding: "2.5rem 2rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.5rem",
          textAlign: "center",
        }}
      >
        <div>
          <div
            style={{
              width: "52px",
              height: "52px",
              margin: "0 auto 1.25rem auto",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--accent-purple)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ffffff",
              boxShadow: "0 6px 20px rgba(139, 92, 246, 0.35)",
            }}
          >
            <IconCpu size={28} />
          </div>

          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, margin: "0 0 0.5rem 0", letterSpacing: "-0.02em" }}>
            AuraML Enterprise Platform
          </h1>
          <p style={{ fontSize: "0.84375rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
            Authenticate via OIDC identity provider to access workspace telemetry, model registries, and autonomous AI agents.
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "0.75rem 1rem",
              fontSize: "0.8125rem",
              color: "var(--status-danger)",
              backgroundColor: "var(--status-danger-bg)",
              border: "1px solid var(--status-danger-border)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {error}
          </div>
        )}

        <Button
          variant="primary"
          onClick={login}
          icon={<IconLock size={16} />}
          style={{ width: "100%", padding: "0.75rem" }}
        >
          Sign In via OIDC Identity Provider
        </Button>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.25rem", marginTop: "0.5rem" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.75rem", fontWeight: 600 }}>
            Developer Fast-Track Access
          </span>
          <form onSubmit={handleDevLogin} style={{ display: "flex", gap: "0.5rem" }}>
            <Input
              placeholder="Paste Bearer JWT Token..."
              value={devTokenInput}
              onChange={(e) => setDevTokenInput(e.target.value)}
              icon={<IconKey size={15} />}
            />
            <Button type="submit" variant="secondary">
              Login
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};
