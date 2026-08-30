import React from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { WorkspaceProvider } from "./context/WorkspaceContext";
import { CallbackPage } from "./pages/CallbackPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { TasksPage } from "./pages/TasksPage";

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
        }}
      >
        Loading application context...
      </div>
    );
  }

  if (path === "/callback") {
    return <CallbackPage />;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (path === "/" || path.startsWith("/workspaces")) {
    return (
      <WorkspaceProvider>
        <TasksPage />
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
