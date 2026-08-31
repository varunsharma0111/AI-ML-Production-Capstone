/**
 * TypeScript API contracts matching Phase 2, Milestone 1, 2, 3, 4, and 5 endpoints and domain objects.
 */

export type TaskStatus = "open" | "completed";

export type WorkspaceRole = "owner" | "editor" | "viewer";

export type Permission =
  | "workspace:read"
  | "task:create"
  | "task:read"
  | "task:update"
  | "dataset:create"
  | "dataset:read"
  | "model:evaluate"
  | "model:promote"
  | "model:read";

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

export interface TaskListResponse {
  items: Task[];
  offset: number;
  limit: number;
}

export type JobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";
export type JobType = "sample_ml_ingestion" | "data_export" | "model_evaluation" | "dataset_profiling" | "model_training";

export interface Job {
  id: string;
  workspace_id: string;
  created_by_user_id: string;
  idempotency_key: string | null;
  job_type: JobType;
  payload_json: Record<string, any>;
  status: JobStatus;
  result_json: Record<string, any> | null;
  error_detail: string | null;
  max_retries: number;
  attempt_count: number;
  version: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TrainingJobCreatePayload {
  workspace_id: string;
  dataset_id: string;
  target_column: string;
  model_name: string;
  model_type: string;
  hyperparameters?: Record<string, any>;
}

export interface ModelTrainingResult {
  model_version_id: string;
  version_tag: string;
  artifact_path: string;
  metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    training_duration_ms: number;
    train_samples: number;
    test_samples: number;
    target_column: string;
    target_classes: string[];
  };
  model_name: string;
  model_type: string;
  target_column: string;
}

export interface ModelVersion {
  id: string;
  name: string;
  version_tag: string;
  description: string | null;
  artifact_path: string;
  status: string;
  workspace_id?: string | null;
  dataset_id?: string | null;
  job_id?: string | null;
  metrics_json?: Record<string, any>;
  hyperparameters_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface QualityGateResponse {
  model_id: string;
  workspace_id?: string | null;
  status: string;
  passed_gate: boolean;
  accuracy: number;
  f1_score: number;
  accuracy_threshold: number;
  f1_threshold: number;
  failure_reasons: string[];
  evaluated_at: string;
}

export interface PredictRequestPayload {
  workspace_id: string;
  input_features: Record<string, any>;
}

export interface PredictResponsePayload {
  model_id: string;
  model_version: string;
  prediction: string;
  confidence: number;
  latency_ms: number;
}

export interface AgentOrchestrateRequestPayload {
  workspace_id: string;
  message: string;
}

export interface AgentToolResultItem {
  tool_name: string;
  result: Record<string, any>;
  duration_ms: number;
}

export interface AgentOrchestrateResponsePayload {
  answer: string;
  tools_used: string[];
  tool_results: AgentToolResultItem[];
}

export type DatasetStatus = "uploaded" | "profiling" | "ready" | "failed";

export interface Dataset {
  id: string;
  workspace_id: string;
  created_by_user_id: string;
  original_filename: string;
  storage_path: string;
  file_size_bytes: number;
  mime_type: string;
  format: string;
  status: DatasetStatus;
  row_count: number | null;
  column_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetUploadResponse {
  dataset: Dataset;
  job_id: string | null;
}

export interface DatasetListResponse {
  items: Dataset[];
  offset: number;
  limit: number;
}

export interface TopValueItem {
  value: string;
  count: number;
}

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  missing_count: number;
  missing_percentage: number;
  unique_count: number;
  min_value?: number | null;
  max_value?: number | null;
  mean_value?: number | null;
  top_values?: TopValueItem[] | null;
}

export interface DatasetProfile {
  id: string;
  dataset_id: string;
  row_count: number;
  column_count: number;
  columns_json: ColumnProfile[];
  created_at: string;
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
