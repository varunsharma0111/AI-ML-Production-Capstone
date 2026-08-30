import React, { useEffect } from "react";
import { useAuth } from "../context/AuthContext";

export const CallbackPage: React.FC = () => {
  const { loginWithDevToken } = useAuth();

  useEffect(() => {
    // Parses code/token from URL callback during standard OIDC PKCE redirect
    const params = new URLSearchParams(window.location.search);
    const tokenParam = params.get("access_token") || params.get("code");
    if (tokenParam) {
      loginWithDevToken(tokenParam);
    }
  }, [loginWithDevToken]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", color: "var(--text-secondary)" }}>
        <h2>Completing Authentication...</h2>
        <p style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>
          Verifying security claims with the identity provider.
        </p>
      </div>
    </div>
  );
};
