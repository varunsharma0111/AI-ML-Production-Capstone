import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { Dataset, DatasetListResponse, ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  IconDatabase,
  IconFileText,
  IconFilter,
  IconPlus,
  IconSearch,
  IconTrash2,
} from "../ui/Icons";
import { Skeleton } from "../ui/Skeleton";
import { DatasetDetailsModal } from "./DatasetDetailsModal";
import { DatasetUploadModal } from "./DatasetUploadModal";

export const DatasetList: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace, hasPermission } = useWorkspace();
  const { addToast } = useToast();

  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);

  const fetchDatasets = useCallback(async () => {
    setIsLoading(true);
    setProblem(null);
    try {
      const data = await request<DatasetListResponse>(
        `/api/v1/datasets?workspace_id=${activeWorkspace.id}&offset=0&limit=50`,
        { token }
      );
      setDatasets(data.items);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Failed to Fetch Datasets",
          status: 500,
          detail: "Could not load dataset inventory for the current workspace.",
          code: "fetch_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace.id, token]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleDeleteDataset = async (e: React.MouseEvent, datasetId: string, filename: string) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to permanently delete dataset '${filename}'?`)) {
      return;
    }

    try {
      await request(`/api/v1/datasets/${datasetId}?workspace_id=${activeWorkspace.id}`, {
        method: "DELETE",
        token,
      });
      addToast("success", "Dataset Deleted", `Dataset '${filename}' was removed permanently.`);
      fetchDatasets();
    } catch (err: any) {
      addToast("error", "Delete Failed", err.message || "Failed to delete dataset.");
    }
  };

  const canCreate = hasPermission("dataset:create");

  const filteredDatasets = datasets.filter((ds) => {
    const matchesSearch = ds.original_filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || ds.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Dataset Repository & Ingestion</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.84375rem", margin: "0.25rem 0 0" }}>
            Upload, profile, search, inspect schemas, and manage CSV datasets for machine learning workflows.
          </p>
        </div>
        {canCreate && (
          <Button variant="primary" icon={<IconPlus size={16} />} onClick={() => setIsUploadOpen(true)}>
            Ingest Dataset
          </Button>
        )}
      </div>

      {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

      {/* Filter & Search Bar */}
      <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center" }}>
          <div style={{ position: "absolute", left: "0.875rem", color: "var(--text-muted)", pointerEvents: "none" }}>
            <IconSearch size={16} />
          </div>
          <input
            type="text"
            placeholder="Search datasets by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="aura-input"
            style={{ paddingLeft: "2.35rem" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <IconFilter size={16} color="var(--text-muted)" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="aura-select"
            style={{ width: "auto" }}
          >
            <option value="all">All Statuses</option>
            <option value="ready">Ready</option>
            <option value="profiling">Profiling</option>
            <option value="uploaded">Uploaded</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Dataset Inventory Table */}
      {isLoading ? (
        <div className="aura-card" style={{ padding: "2rem" }}>
          <Skeleton height="30px" className="mb-2" />
          <Skeleton height="50px" className="mb-2" />
          <Skeleton height="50px" className="mb-2" />
          <Skeleton height="50px" />
        </div>
      ) : filteredDatasets.length === 0 ? (
        <div className="aura-empty-state">
          <div className="aura-empty-icon">
            <IconDatabase size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", margin: 0 }}>No Datasets Available</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "420px", fontSize: "0.84375rem", margin: 0 }}>
            {datasets.length === 0
              ? "Upload a tabular CSV dataset to trigger background profiling, data health analysis, and feature schema generation."
              : "No datasets match your search parameters."}
          </p>
          {canCreate && (
            <Button variant="primary" icon={<IconPlus size={16} />} onClick={() => setIsUploadOpen(true)}>
              Ingest First Dataset
            </Button>
          )}
        </div>
      ) : (
        <div className="aura-table-container">
          <table className="aura-table">
            <thead>
              <tr>
                <th>Dataset Name</th>
                <th>Status</th>
                <th>File Size</th>
                <th>Rows</th>
                <th>Columns</th>
                <th>Uploaded Date</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDatasets.map((dataset) => (
                <tr
                  key={dataset.id}
                  onClick={() => setSelectedDataset(dataset)}
                  style={{ cursor: "pointer" }}
                >
                  <td style={{ fontWeight: 600 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                      <IconFileText size={16} color="var(--accent-blue)" />
                      <span>{dataset.original_filename}</span>
                    </div>
                  </td>
                  <td>
                    <Badge variant={dataset.status}>{dataset.status}</Badge>
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78125rem" }}>
                    {(dataset.file_size_bytes / 1024).toFixed(1)} KB
                  </td>
                  <td style={{ fontWeight: 500 }}>
                    {dataset.row_count !== null ? dataset.row_count.toLocaleString() : "—"}
                  </td>
                  <td style={{ fontWeight: 500 }}>
                    {dataset.column_count !== null ? dataset.column_count : "—"}
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.78125rem" }}>
                    {new Date(dataset.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedDataset(dataset);
                        }}
                      >
                        Inspect
                      </Button>
                      {canCreate && (
                        <Button
                          variant="danger"
                          size="sm"
                          icon={<IconTrash2 size={14} />}
                          onClick={(e) => handleDeleteDataset(e, dataset.id, dataset.original_filename)}
                          aria-label="Delete dataset"
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DatasetUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploaded={fetchDatasets}
      />

      <DatasetDetailsModal
        dataset={selectedDataset}
        isOpen={!!selectedDataset}
        onClose={() => setSelectedDataset(null)}
      />
    </div>
  );
};
