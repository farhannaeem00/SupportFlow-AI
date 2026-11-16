
import {
  AlertCircle,
  File,
  FileText,
  LoaderCircle,
  Trash2,
} from "lucide-react";
import type { KnowledgeDocument } from "./knowledgeBaseApi";

interface DocumentListProps {
  documents: KnowledgeDocument[];
  loading: boolean;
  onDelete: (document: KnowledgeDocument) => void;
  canManage: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "Unknown date";

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getStatus(status: string) {
  const normalized = status.toLowerCase();

  if (["completed", "processed", "ready", "success"].includes(normalized)) {
    return { label: "Processed", className: "success" };
  }

  if (["failed", "error"].includes(normalized)) {
    return { label: "Failed", className: "failed" };
  }

  if (["pending", "processing", "queued"].includes(normalized)) {
    return { label: normalized === "pending" ? "Pending" : "Processing", className: "processing" };
  }

  return { label: status.replaceAll("_", " "), className: "unknown" };
}

export default function DocumentList({
  documents,
  loading,
  onDelete,
  canManage,
}: DocumentListProps) {
  if (loading) {
    return (
      <div className="kb-loading">
        <LoaderCircle size={20} className="kb-spinner" />
        <span>Loading documents...</span>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="kb-document-empty">
        <File size={23} />
        <strong>No documents uploaded</strong>
        <span>Upload your first document to this knowledge base.</span>
      </div>
    );
  }

  return (
    <div className="kb-document-list">
      {documents.map((document) => {
        const status = getStatus(document.status);

        return (
          <div className="kb-document-row" key={document.id}>
            <div className="kb-document-icon">
              <FileText size={20} />
            </div>

            <div className="kb-document-info">
              <strong title={document.original_filename}>
                {document.original_filename}
              </strong>
              <span>
                {formatFileSize(document.file_size)}
                <span className="kb-dot">·</span>
                {formatDate(document.created_at)}
              </span>

              {document.error_message && (
                <span className="kb-document-error">
                  <AlertCircle size={13} />
                  {document.error_message}
                </span>
              )}
            </div>

            <div className="kb-document-meta">
              <span className={`kb-document-status ${status.className}`}>
                {status.className === "processing" && (
                  <LoaderCircle size={12} className="kb-spinner" />
                )}
                {status.label}
              </span>
              <small>
                {document.chunk_count}{" "}
                {document.chunk_count === 1 ? "chunk" : "chunks"}
              </small>
            </div>

            {canManage && (
              <button
                type="button"
                className="kb-icon-button kb-delete-document"
                title="Delete document"
                aria-label={`Delete ${document.original_filename}`}
                onClick={() => onDelete(document)}
              >
                <Trash2 size={17} />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
