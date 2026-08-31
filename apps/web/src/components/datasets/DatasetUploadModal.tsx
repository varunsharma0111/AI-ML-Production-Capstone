import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { DatasetUploadResponse, ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { IconFileText, IconUpload, IconX } from "../ui/Icons";
import { Modal } from "../ui/Modal";

interface DatasetUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: () => void;
}

export const DatasetUploadModal: React.FC<DatasetUploadModalProps> = ({
  isOpen,
  onClose,
  onUploaded,
}) => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith(".csv")) {
        setProblem({
          type: "about:blank",
          title: "Invalid File Format",
          status: 400,
          detail: "Only CSV files (.csv) are supported for automated schema profiling and ML training.",
          code: "validation_failed",
          request_id: "client_val",
        });
        return;
      }
      setSelectedFile(file);
      setProblem(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (!file.name.toLowerCase().endsWith(".csv")) {
        setProblem({
          type: "about:blank",
          title: "Invalid File Format",
          status: 400,
          detail: "Only CSV files (.csv) are supported for automated schema profiling and ML training.",
          code: "validation_failed",
          request_id: "client_val",
        });
        return;
      }
      setSelectedFile(file);
      setProblem(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setProblem(null);

    const formData = new FormData();
    formData.append("workspace_id", activeWorkspace.id);
    formData.append("file", selectedFile);

    try {
      await request<DatasetUploadResponse>("/api/v1/datasets/upload", {
        method: "POST",
        token,
        body: formData,
      });

      setSelectedFile(null);
      onUploaded();
      onClose();
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Dataset Ingestion Failed",
          status: 500,
          detail: err.message || "Failed to upload dataset to the platform.",
          code: "upload_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Ingest New Dataset"
      subtitle="Upload a tabular CSV dataset for automated schema profiling, data health analysis, and model training."
    >
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {problem && <Alert problem={problem} onClose={() => setProblem(null)} />}

        {/* Dropzone Container */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          style={{
            border: isDragOver
              ? "2px dashed var(--accent-blue)"
              : "2px dashed var(--border-medium)",
            borderRadius: "var(--radius-md)",
            padding: "2.25rem 1.5rem",
            textAlign: "center",
            backgroundColor: isDragOver ? "var(--accent-blue-light)" : "var(--bg-surface)",
            cursor: "pointer",
            transition: "all var(--transition-fast)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
          }}
          onClick={() => document.getElementById("file-upload-input")?.click()}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              backgroundColor: "var(--bg-card)",
              color: "var(--accent-blue)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <IconUpload size={22} />
          </div>
          <div>
            <span style={{ fontWeight: 600, color: "var(--accent-blue)" }}>Click to browse</span> or drag and drop CSV file
          </div>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Supported format: Standard tabular CSV (.csv) up to 50MB
          </span>
          <input
            id="file-upload-input"
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
        </div>

        {selectedFile && (
          <div
            style={{
              padding: "0.875rem 1rem",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-medium)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <IconFileText size={20} color="var(--accent-blue)" />
              <div>
                <div style={{ fontSize: "0.84375rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  {selectedFile.name}
                </div>
                <div style={{ fontSize: "0.71875rem", color: "var(--text-muted)" }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB • CSV Document
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                padding: "0.25rem",
              }}
            >
              <IconX size={16} />
            </button>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
          <Button variant="ghost" type="button" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={!selectedFile || isUploading} isLoading={isUploading}>
            {isUploading ? "Uploading & Profiling..." : "Upload & Run Profiler"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
