import React from "react";
import { Header } from "../components/layout/Header";
import { TaskList } from "../components/tasks/TaskList";
import { useWorkspace } from "../context/WorkspaceContext";

export const TasksPage: React.FC = () => {
  const { activeWorkspace } = useWorkspace();

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <div style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "1.5rem" }}>{activeWorkspace.name}</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Manage asynchronous jobs, workspace task lifecycle, and audit logs.
          </p>
        </div>
        <TaskList />
      </main>
    </div>
  );
};
