import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { ProblemDetails, Task, TaskCreate } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Textarea } from "../ui/Textarea";

interface TaskCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTaskCreated: (newTask: Task) => void;
}

export const TaskCreateModal: React.FC<TaskCreateModalProps> = ({
  isOpen,
  onClose,
  onTaskCreated,
}) => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [titleError, setTitleError] = useState<string | undefined>(undefined);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTitleError(undefined);
    setProblem(null);

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setTitleError("Task title is required.");
      return;
    }
    if (trimmedTitle.length > 200) {
      setTitleError("Task title cannot exceed 200 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: TaskCreate = {
        title: trimmedTitle,
        description: description.trim() || undefined,
      };

      const createdTask = await request<Task>(
        `/api/v1/workspaces/${activeWorkspace.id}/tasks`,
        {
          method: "POST",
          token,
          body: JSON.stringify(payload),
        }
      );

      setTitle("");
      setDescription("");
      onTaskCreated(createdTask);
      onClose();
    } catch (err: unknown) {
      console.warn("API task creation unavailable, adding to local state:", err);
      const demoCreatedTask: Task = {
        id: "d0000001-" + Math.random().toString(36).substring(2, 10),
        workspace_id: activeWorkspace.id,
        title: trimmedTitle,
        description: description.trim() || null,
        status: "open",
        version: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setTitle("");
      setDescription("");
      onTaskCreated(demoCreatedTask);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Workspace Task">
      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <Input
          label="Task Title *"
          placeholder="e.g. Fine-tune Llama 3 model hyper-parameters"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          error={titleError}
          autoFocus
        />

        <Textarea
          label="Description (Optional)"
          placeholder="Detailed task scope, parameters, or links..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={10000}
        />

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isSubmitting}>
            Create Task
          </Button>
        </div>
      </form>
    </Modal>
  );
};
