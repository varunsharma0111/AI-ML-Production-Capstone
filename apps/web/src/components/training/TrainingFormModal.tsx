import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { Dataset, DatasetListResponse, DatasetProfile, Job, ProblemDetails, TrainingJobCreatePayload } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { IconLayers, IconPlay } from "../ui/Icons";
import { Modal } from "../ui/Modal";

interface TrainingFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onJobSubmitted: () => void;
}

export const TrainingFormModal: React.FC<TrainingFormModalProps> = ({
  isOpen,
  onClose,
  onJobSubmitted,
}) => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);

  const [modelName, setModelName] = useState<string>("");
  const [modelType, setModelType] = useState<string>("random_forest");
  const [targetColumn, setTargetColumn] = useState<string>("");
  const [nEstimators, setNEstimators] = useState<number>(100);
  const [maxDepth, setMaxDepth] = useState<number>(5);
  const [randomState, setRandomState] = useState<number>(42);

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isLoadingDatasets, setIsLoadingDatasets] = useState<boolean>(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchDatasets();
      setProblem(null);
    }
  }, [isOpen, activeWorkspace.id]);

  const fetchDatasets = async () => {
    setIsLoadingDatasets(true);
    try {
      const data = await request<DatasetListResponse>(
        `/api/v1/datasets?workspace_id=${activeWorkspace.id}&offset=0&limit=50`,
        { token }
      );
      const readyDatasets = data.items.filter((d) => d.status === "ready");
      setDatasets(readyDatasets);
      if (readyDatasets.length > 0) {
        setSelectedDatasetId(readyDatasets[0].id);
        fetchColumns(readyDatasets[0].id);
      } else {
        setSelectedDatasetId("");
        setAvailableColumns([]);
      }
    } catch {
      // Ignore initial fetch errors
    } finally {
      setIsLoadingDatasets(false);
    }
  };

  const fetchColumns = async (datasetId: string) => {
    try {
      const profile = await request<DatasetProfile>(
        `/api/v1/datasets/${datasetId}/profile?workspace_id=${activeWorkspace.id}`,
        { token }
      );
      const colNames = profile.columns_json.map((c) => c.name);
      setAvailableColumns(colNames);
      if (colNames.length > 0) {
        setTargetColumn(colNames[colNames.length - 1]);
      }
    } catch {
      setAvailableColumns([]);
    }
  };

  const handleDatasetChange = (datasetId: string) => {
    setSelectedDatasetId(datasetId);
    fetchColumns(datasetId);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDatasetId || !targetColumn || !modelName) return;

    setIsSubmitting(true);
    setProblem(null);

    const payload: TrainingJobCreatePayload = {
      workspace_id: activeWorkspace.id,
      dataset_id: selectedDatasetId,
      target_column: targetColumn,
      model_name: modelName.trim(),
      model_type: modelType,
      hyperparameters: {
        n_estimators: nEstimators,
        max_depth: maxDepth,
        random_state: randomState,
      },
    };

    try {
      await request<Job>("/api/v1/jobs/train", {
        method: "POST",
        token,
        body: payload,
      });

      onJobSubmitted();
      onClose();
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Submission Failed",
          status: 500,
          detail: err.message || "Failed to submit model training job.",
          code: "submit_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Dispatch Model Training Experiment"
      subtitle="Configure dataset targets, classifier hyperparameter grids, and dispatch async background job."
      maxWidth="680px"
    >
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

        {/* Model Identifier */}
        <div className="aura-form-group">
          <label className="aura-label">Model Identifier / Experiment Tag</label>
          <input
            type="text"
            required
            placeholder="e.g. churn-predictor-v1"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            className="aura-input"
          />
        </div>

        {/* Dataset Selection */}
        <div className="aura-form-group">
          <label className="aura-label">Training Dataset Source (Ready Status Only)</label>
          {isLoadingDatasets ? (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", padding: "0.5rem 0" }}>
              Loading available dataset inventory...
            </div>
          ) : datasets.length === 0 ? (
            <div style={{ fontSize: "0.8125rem", color: "var(--status-warning)", padding: "0.5rem 0" }}>
              No ready datasets found in this workspace. Upload and profile a CSV dataset first.
            </div>
          ) : (
            <select
              value={selectedDatasetId}
              onChange={(e) => handleDatasetChange(e.target.value)}
              className="aura-select"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_filename} ({d.row_count?.toLocaleString()} rows, {d.column_count} cols)
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Target Column */}
        <div className="aura-form-group">
          <label className="aura-label">Target Column (Label Variable)</label>
          {availableColumns.length === 0 ? (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No dataset columns loaded</div>
          ) : (
            <select
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              className="aura-select"
            >
              {availableColumns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Model Algorithm */}
        <div className="aura-form-group">
          <label className="aura-label">Model Classifier Architecture</label>
          <select
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
            className="aura-select"
          >
            <option value="random_forest">RandomForestClassifier (Ensemble Trees)</option>
            <option value="decision_tree">DecisionTreeClassifier (Single Tree)</option>
            <option value="logistic_regression">LogisticRegression (Linear Decision Boundary)</option>
          </select>
        </div>

        {/* Hyperparameter Settings Panel */}
        <div style={{ padding: "1rem", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <IconLayers size={16} color="var(--accent-purple)" />
            <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
              Hyperparameters Configuration
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
            <div className="aura-form-group">
              <label className="aura-label" style={{ fontSize: "0.71875rem" }}>n_estimators</label>
              <input
                type="number"
                min={10}
                max={500}
                value={nEstimators}
                onChange={(e) => setNEstimators(Number(e.target.value))}
                className="aura-input"
                style={{ fontSize: "0.8125rem" }}
              />
            </div>
            <div className="aura-form-group">
              <label className="aura-label" style={{ fontSize: "0.71875rem" }}>max_depth</label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="aura-input"
                style={{ fontSize: "0.8125rem" }}
              />
            </div>
            <div className="aura-form-group">
              <label className="aura-label" style={{ fontSize: "0.71875rem" }}>random_state</label>
              <input
                type="number"
                value={randomState}
                onChange={(e) => setRandomState(Number(e.target.value))}
                className="aura-input"
                style={{ fontSize: "0.8125rem" }}
              />
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
          <Button variant="ghost" type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="submit"
            icon={<IconPlay size={15} />}
            disabled={!selectedDatasetId || !targetColumn || !modelName || isSubmitting}
            isLoading={isSubmitting}
          >
            {isSubmitting ? "Dispatching..." : "Dispatch Training Job"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
