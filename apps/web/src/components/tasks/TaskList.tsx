import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { ApiError, request } from "../../services/apiClient";
import { ProblemDetails, Task, TaskListResponse, TaskStatus } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Skeleton } from "../ui/Skeleton";
import { TaskCard } from "./TaskCard";
import { TaskCreateModal } from "./TaskCreateModal";
import { TaskEditModal } from "./TaskEditModal";

export const TaskList: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace, hasPermission } = useWorkspace();
  const canCreate = hasPermission("task:create");

  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const [filterStatus, setFilterStatus] = useState<"all" | TaskStatus>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const data = await request<TaskListResponse>(
        `/api/v1/workspaces/${activeWorkspace.id}/tasks?offset=0&limit=50`,
        { token }
      );
      setTasks(data.items);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Error",
          status: 500,
          detail: "Failed to load workspace tasks.",
          code: "fetch_error",
          request_id: "client",
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace.id, token]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleToggleStatus = async (task: Task) => {
    try {
      const nextStatus: TaskStatus = task.status === "open" ? "completed" : "open";
      const updatedTask = await request<Task>(
        `/api/v1/workspaces/${activeWorkspace.id}/tasks/${task.id}`,
        {
          method: "PATCH",
          token,
          body: JSON.stringify({
            version: task.version,
            status: nextStatus,
          }),
        }
      );
      setTasks((prev) => prev.map((t) => (t.id === updatedTask.id ? updatedTask : t)));
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setProblem(err.problem);
      }
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const matchesStatus = filterStatus === "all" || t.status === filterStatus;
    const matchesSearch =
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Action & Filter Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.25rem",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, minWidth: "260px" }}>
          <Input
            placeholder="Search tasks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {/* Status Filter Pills */}
          <div
            style={{
              display: "flex",
              backgroundColor: "var(--bg-surface)",
              padding: "0.25rem",
              borderRadius: "var(--radius-sm)",
              gap: "0.25rem",
            }}
          >
            {(["all", "open", "completed"] as const).map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                style={{
                  background: filterStatus === status ? "var(--bg-card)" : "transparent",
                  color: filterStatus === status ? "var(--text-primary)" : "var(--text-secondary)",
                  border: "none",
                  padding: "0.375rem 0.75rem",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  textTransform: "capitalize",
                  transition: "all var(--transition-fast)",
                }}
              >
                {status}
              </button>
            ))}
          </div>

          {canCreate ? (
            <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
              + New Task
            </Button>
          ) : (
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
              (Read-Only Viewer Role)
            </span>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {problem && <Alert problem={problem} onRetry={fetchTasks} onClose={() => setProblem(null)} />}

      {/* Loading Skeletons */}
      {isLoading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem" }}>
          <Skeleton height="140px" />
          <Skeleton height="140px" />
          <Skeleton height="140px" />
        </div>
      ) : filteredTasks.length === 0 ? (
        /* Empty State */
        <div
          className="glass-panel"
          style={{
            padding: "3rem 1.5rem",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <div style={{ fontSize: "2.5rem" }}>📋</div>
          <h3>No tasks found</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", maxWidth: "400px" }}>
            {searchQuery
              ? `No tasks match "${searchQuery}". Try adjusting your filters.`
              : "This workspace has no tasks assigned yet."}
          </p>
          {canCreate && !searchQuery && (
            <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
              Create First Task
            </Button>
          )}
        </div>
      ) : (
        /* Task Cards Grid */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem" }}>
          {filteredTasks.map((t) => (
            <TaskCard
              key={t.id}
              task={t}
              onEdit={(taskToEdit) => setEditingTask(taskToEdit)}
              onToggleStatus={handleToggleStatus}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <TaskCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onTaskCreated={(newTask) => setTasks((prev) => [newTask, ...prev])}
      />

      {/* Edit Modal */}
      <TaskEditModal
        task={editingTask}
        isOpen={!!editingTask}
        onClose={() => setEditingTask(null)}
        onTaskUpdated={(updatedTask) =>
          setTasks((prev) => prev.map((t) => (t.id === updatedTask.id ? updatedTask : t)))
        }
      />
    </div>
  );
};
