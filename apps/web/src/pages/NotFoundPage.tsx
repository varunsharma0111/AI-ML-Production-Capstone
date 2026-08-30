import React from "react";
import { Button } from "../components/ui/Button";

export const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "1rem",
        textAlign: "center",
      }}
    >
      <h1 style={{ fontSize: "4rem", color: "var(--accent-purple)" }}>404</h1>
      <h2>Page Not Found</h2>
      <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", maxWidth: "400px" }}>
        The requested workspace route or page does not exist.
      </p>
      <Button variant="primary" onClick={() => (window.location.href = "/")}>
        Return to Dashboard
      </Button>
    </div>
  );
};
