import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
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
        background: "radial-gradient(circle at top right, hsl(222, 40%, 15%), var(--bg-dark))",
      }}
    >
      <div
        className="glass-panel animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "460px",
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
              width: "48px",
              height: "48px",
              margin: "0 auto 1rem auto",
              borderRadius: "var(--radius-md)",
              background: "linear-gradient(135deg, var(--accent-blue), var(--accent-purple))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "#fff",
              boxShadow: "0 4px 14px rgba(59, 130, 246, 0.4)",
            }}
          >
            AI
          </div>
          <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>
            AI/ML Production Capstone
          </h1>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Authenticate with OIDC PKCE to access workspace-scoped tasks, agent orchestrations, and audit logs.
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "0.75rem",
              fontSize: "0.875rem",
              color: "var(--status-danger)",
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {error}
          </div>
        )}

        <Button variant="primary" onClick={login} style={{ width: "100%", padding: "0.75rem" }}>
          Sign In with OIDC Identity Provider
        </Button>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.25rem", marginTop: "0.5rem" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.75rem" }}>
            Local First / Development Quick Auth
          </span>
          <form onSubmit={handleDevLogin} style={{ display: "flex", gap: "0.5rem" }}>
            <Input
              placeholder="Paste Bearer JWT Token..."
              value={devTokenInput}
              onChange={(e) => setDevTokenInput(e.target.value)}
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
