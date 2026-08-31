import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ProblemDetails, Task, TaskListResponse, TaskStatus } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { IconFilter, IconListTodo, IconPlus, IconSearch } from "../ui/Icons";
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

  const DEMO_TASKS: Task[] = [
    {
      id: "d0000001-0001-0001-0001-000000000001",
      workspace_id: activeWorkspace.id,
      title: "Train sentiment analysis model v2",
      description: "Fine-tune BERT classifier on updated customer feedback dataset with automated preprocessing.",
      status: "open",
      version: 1,
      created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      updated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    },
    {
      id: "d0000001-0001-0001-0001-000000000002",
      workspace_id: activeWorkspace.id,
      title: "Deploy quality gate policy for fraud detection",
      description: "Enforce minimum accuracy threshold of 0.95 and F1 score of 0.89 before production promotion.",
      status: "completed",
      version: 2,
      created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
      updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
    },
    {
      id: "d0000001-0001-0001-0001-000000000003",
      workspace_id: activeWorkspace.id,
      title: "Audit agent tool execution logs",
      description: "Review sandboxed agent tool calls for compliance and execution integrity.",
      status: "open",
      version: 1,
      created_at: new Date(Date.now() - 3600000 * 6).toISOString(),
      updated_at: new Date(Date.now() - 3600000 * 6).toISOString(),
    },
  ];

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const data = await request<TaskListResponse>(
        `/api/v1/workspaces/${activeWorkspace.id}/tasks?offset=0&limit=50`,
        { token }
      );
      setTasks(data.items);
    } catch {
      setTasks(DEMO_TASKS);
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
    } catch {
      const nextStatus: TaskStatus = task.status === "open" ? "completed" : "open";
      setTasks((prev) =>
        prev.map((t) =>
          t.id === task.id
            ? { ...t, status: nextStatus, version: t.version + 1, updated_at: new Date().toISOString() }
            : t
        )
      );
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
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Operational Tasks & Workflows</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Track background operations, manual quality reviews, and MLOps maintenance checklists.
          </p>
        </div>
        {canCreate && (
          <Button variant="primary" icon={<IconPlus size={16} />} onClick={() => setIsCreateModalOpen(true)}>
            New Task
          </Button>
        )}
      </div>

      {problem && <Alert problem={problem} onRetry={fetchTasks} onClose={() => setProblem(null)} />}

      {/* Filter & Search Bar */}
      <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center" }}>
          <div style={{ position: "absolute", left: "0.875rem", color: "var(--text-muted)", pointerEvents: "none" }}>
            <IconSearch size={16} />
          </div>
          <input
            type="text"
            placeholder="Search tasks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="aura-input"
            style={{ paddingLeft: "2.35rem" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <IconFilter size={16} color="var(--text-muted)" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as any)}
            className="aura-select"
            style={{ width: "auto" }}
          >
            <option value="all">All Tasks</option>
            <option value="open">Open</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem" }}>
          <Skeleton height="140px" />
          <Skeleton height="140px" />
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconListTodo size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>No Tasks Found</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            {searchQuery ? `No tasks match search query "${searchQuery}".` : "No tasks assigned to this workspace."}
          </p>
        </div>
      ) : (
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

      <TaskCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onTaskCreated={(newTask) => setTasks((prev) => [newTask, ...prev])}
      />

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
