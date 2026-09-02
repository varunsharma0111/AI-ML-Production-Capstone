import React from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { WorkspaceProvider } from "./context/WorkspaceContext";
import { CallbackPage } from "./pages/CallbackPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { AppLayout } from "./components/layout/AppLayout";

const MainRouter: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const path = window.location.pathname;

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-secondary)",
          background: "var(--bg-dark)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div className="spinner" style={{ width: "28px", height: "28px", margin: "0 auto 1rem" }} />
          <span>Loading platform authentication context...</span>
        </div>
      </div>
    );
  }

  if (path === "/callback") {
    return <CallbackPage />;
  }

  // Temporarily commented out sign-in check for website testing
  // if (!isAuthenticated) {
  //   return <LoginPage />;
  // }

  if (path === "/" || path.startsWith("/workspaces") || path.startsWith("/tasks")) {
    return (
      <WorkspaceProvider>
        <ToastProvider>
          <AppLayout />
        </ToastProvider>
      </WorkspaceProvider>
    );
  }

  return <NotFoundPage />;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainRouter />
    </AuthProvider>
  );
};
