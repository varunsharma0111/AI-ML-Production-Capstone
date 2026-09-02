import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { request, setUnauthorizedHandler } from "../services/apiClient";
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

const DEFAULT_DEV_USER: User = {
  id: "dev-user-123",
  subject: "dev-user-123",
  email: "dev.user@example.com",
  display_name: "Dev Demo User",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  workspaces: [],
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_STORAGE_KEY) || "dev_token_sample"
  );
  const [user, setUser] = useState<User | null>(DEFAULT_DEV_USER);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      // Temporarily disabled auto-logout for local website testing
      console.warn("Unauthorized API call caught; keeping test session active.");
    });
    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  const fetchCurrentUser = async (authToken: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const currentUser = await request<User>("/api/v1/me", { token: authToken });
      setUser(currentUser);
    } catch (err: unknown) {
      console.warn("Authentication via /me failed, using dev fallback user for UI testing:", err);
      setUser(DEFAULT_DEV_USER);
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
    // Production OIDC Token login prompt
    const tokenInput = prompt("Enter your OIDC Access Token:");
    if (tokenInput && tokenInput.trim()) {
      loginWithDevToken(tokenInput.trim());
    }
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
