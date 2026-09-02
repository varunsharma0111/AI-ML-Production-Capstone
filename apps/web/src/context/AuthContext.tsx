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

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_STORAGE_KEY)
  );
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
      setError("Session expired or authentication failed.");
    });
    return () => {
      setUnauthorizedHandler(null);
    };
  }, [logout]);

  const fetchCurrentUser = async (authToken: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const currentUser = await request<User>("/api/v1/me", { token: authToken });
      setUser(currentUser);
    } catch (err: unknown) {
      console.warn("Authentication via /me failed:", err);
      setError("Session expired or token invalid.");
      logout();
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
