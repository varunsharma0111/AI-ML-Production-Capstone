import React from "react";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { WorkspaceProvider } from "./context/WorkspaceContext";
import { CallbackPage } from "./pages/CallbackPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { AppLayout } from "./components/layout/AppLayout";

const MainRouter: React.FC = () => {
  const path = window.location.pathname;

  if (path === "/callback") {
    return <CallbackPage />;
  }

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
