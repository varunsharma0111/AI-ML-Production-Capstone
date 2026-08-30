/**
 * TypeScript API contracts matching Phase 2 FastAPI endpoints and domain objects.
 */

export type TaskStatus = "open" | "completed";

export type WorkspaceRole = "owner" | "editor" | "viewer";

export type Permission = "workspace:read" | "task:create" | "task:read" | "task:update";

export interface User {
  id: string;
  subject: string;
  email: string | null;
  display_name: string | null;
}

export interface Workspace {
  id: string;
  slug: string;
  name: string;
  role: WorkspaceRole;
}

export interface Task {
  id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
}

export interface TaskUpdate {
  version: number;
  title?: string;
  description?: string;
  status?: TaskStatus;
}

export interface TaskListResponse {
  items: Task[];
  offset: number;
  limit: number;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  request_id: string;
}

export interface HealthCheckResponse {
  status: string;
}
