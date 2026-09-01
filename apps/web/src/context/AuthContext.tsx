import React, { createContext, useContext, useEffect, useState } from "react";
import { request } from "../services/apiClient";
import { User } from "../types/api";

interface AuthContextType {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: () => void;
  loginWithDevToken: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = "capstone_access_token";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const isDevToken = (t: string): boolean =>
    t.startsWith("dev_") || t === "dev_token_sample" || t.includes("dev_token");

  const DEV_USER: User = {
    id: "00000000-0000-0000-0000-000000000001",
    subject: "dev-user-123",
    email: "dev.user@example.com",
    display_name: "Dev Demo User",
  };

  const fetchCurrentUser = async (authToken: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const currentUser = await request<User>("/api/v1/me", { token: authToken });
      setUser(currentUser);
    } catch (err: unknown) {
      console.error("Failed to authenticate principal via /me:", err);
      // Fallback for dev demonstration if API is unreachable
      if (isDevToken(authToken)) {
        setUser(DEV_USER);
      } else {
        setError("Session expired or token invalid.");
        logout();
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const loginWithDevToken = async (devToken: string) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, devToken);
    setToken(devToken);
    await fetchCurrentUser(devToken);
  };

  const login = () => {
    // In production, triggers OIDC Authorization Code + PKCE redirect.
    // For local dev demonstration, prompts for a JWT or uses a default test token.
    const sampleToken = prompt(
      "Enter OIDC JWT Bearer Token (or press OK for default dev token):",
      "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.dev_token_sample"
    );
    if (sampleToken) {
      loginWithDevToken(sampleToken);
    }
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setError(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token && !!user,
        isLoading,
        error,
        login,
        loginWithDevToken,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
