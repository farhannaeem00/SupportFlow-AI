
import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  FileText,
  LoaderCircle,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import KnowledgeBaseForm from "./KnowledgeBaseForm";
import KnowledgeBaseList from "./KnowledgeBaseList";
import DocumentList from "./DocumentList";
import DocumentUpload from "./DocumentUpload";
import {
  knowledgeBaseApi,
  type KnowledgeBase,
  type KnowledgeBaseCreate,
  type KnowledgeBaseUpdate,
  type KnowledgeDocument,
} from "./knowledgeBaseApi";
import "./KnowledgeBase.css";

type FormMode = "create" | "edit" | null;

function getErrorMessage(error: unknown, fallback: string): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response = (error as {
      response?: { data?: { detail?: unknown } };
    }).response;

    const detail = response?.data?.detail;

    if (typeof detail === "string") return detail;
  }

  return fallback;
}

export default function KnowledgeBasePage() {
  const { organization, organizations } = useAuth()

const currentMembership = organizations.find(
  (item) => item.id === organization?.id,
)

const role = currentMembership?.role?.toLowerCase()
const canManage = role === "owner" || role === "admin"

  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selected, setSelected] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);

  const [loading, setLoading] = useState(true);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState("");
  const [notice, setNotice] = useState("");

  const [formMode, setFormMode] = useState<FormMode>(null);
  const [editing, setEditing] = useState<KnowledgeBase | null>(null);

  const loadKnowledgeBases = useCallback(async () => {
    setLoading(true);
    setPageError("");

    try {
      const items = await knowledgeBaseApi.list({ skip: 0, limit: 100 });
      setKnowledgeBases(items);

      setSelected((current) => {
        if (!current) return null;
        return items.find((item) => item.id === current.id) ?? null;
      });
    } catch (error) {
      setPageError(
        getErrorMessage(error, "Unable to load knowledge bases."),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDocuments = useCallback(async (knowledgeBaseId: string) => {
    setDocumentsLoading(true);

    try {
      const items = await knowledgeBaseApi.listDocuments(knowledgeBaseId, {
        skip: 0,
        limit: 100,
      });
      setDocuments(items);
    } catch (error) {
      setPageError(
        getErrorMessage(error, "Unable to load documents."),
      );
      setDocuments([]);
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadKnowledgeBases();
  }, [loadKnowledgeBases]);

  useEffect(() => {
    if (selected) {
      void loadDocuments(selected.id);
    } else {
      setDocuments([]);
    }
  }, [selected?.id, loadDocuments]);

  async function handleCreateOrUpdate(
    data: KnowledgeBaseCreate | KnowledgeBaseUpdate,
  ) {
    setSaving(true);
    setPageError("");

    try {
      if (formMode === "edit" && editing) {
        const updated = await knowledgeBaseApi.update(editing.id, data);
        setKnowledgeBases((current) =>
          current.map((item) => item.id === updated.id ? updated : item),
        );
        setSelected(updated);
        setNotice("Knowledge base updated successfully.");
      } else {
        const created = await knowledgeBaseApi.create(
          data as KnowledgeBaseCreate,
        );
        setKnowledgeBases((current) => [created, ...current]);
        setSelected(created);
        setNotice("Knowledge base created successfully.");
      }

      setFormMode(null);
      setEditing(null);
    } catch (error) {
      setPageError(
        getErrorMessage(error, "Unable to save the knowledge base."),
      );
      throw error;
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteKnowledgeBase(item: KnowledgeBase) {
    const confirmed = window.confirm(
      `Delete "${item.name}"? This action cannot be undone.`,
    );

    if (!confirmed) return;

    setPageError("");
    setNotice("");

    try {
      await knowledgeBaseApi.delete(item.id);

      setKnowledgeBases((current) =>
        current.filter((base) => base.id !== item.id),
      );

      if (selected?.id === item.id) {
        setSelected(null);
      }

      setNotice("Knowledge base deleted successfully.");
    } catch (error) {
      setPageError(
        getErrorMessage(error, "Unable to delete the knowledge base."),
      );
    }
  }

  async function handleUpload(file: File) {
    if (!selected) return;

    setPageError("");
    setNotice("");

    try {
      await knowledgeBaseApi.uploadDocument(selected.id, file);
      await Promise.all([
        loadDocuments(selected.id),
        loadKnowledgeBases(),
      ]);
      setNotice("Document uploaded. Processing may take a moment.");
    } catch (error) {
      setPageError(
        getErrorMessage(error, "Unable to upload the document."),
      );
      throw error;
    }
  }

  async function handleDeleteDocument(document: KnowledgeDocument) {
    if (!selected) return;

    const confirmed = window.confirm(
      `Delete "${document.original_filename}"?`,
    );

    if (!confirmed) return;

    setPageError("");
    setNotice("");

    try {
      await knowledgeBaseApi.deleteDocument(selected.id, document.id);

      setDocuments((current) =>
        current.filter((item) => item.id !== document.id),
      );

      setKnowledgeBases((current) =>
        current.map((item) =>
          item.id === selected.id
            ? {
                ...item,
                document_count: Math.max(0, item.document_count - 1),
              }
            : item,
        ),
      );

      setSelected((current) =>
        current?.id === selected.id
          ? {
              ...current,
              document_count: Math.max(0, current.document_count - 1),
            }
          : current,
      );

      setNotice("Document deleted successfully.");
    } catch (error) {
      setPageError(
        getErrorMessage(error, "Unable to delete the document."),
      );
    }
  }

  function openCreateForm() {
    setEditing(null);
    setFormMode("create");
    setPageError("");
    setNotice("");
  }

  function openEditForm(item: KnowledgeBase) {
    setEditing(item);
    setFormMode("edit");
    setPageError("");
    setNotice("");
  }

  return (
    <div className="knowledge-base-page">
      <header className="kb-page-header">
        <div>
          <span className="kb-eyebrow">AI KNOWLEDGE MANAGEMENT</span>
          <h1>Knowledge Base</h1>
          <p>
            Manage the documents and information that power your AI support
            assistant.
          </p>
        </div>

        <div className="kb-header-actions">
          <button
            type="button"
            className="kb-button kb-button-secondary"
            onClick={() => void loadKnowledgeBases()}
            disabled={loading}
          >
            <RefreshCw size={16} />
            Refresh
          </button>

          {canManage && (
            <button
              type="button"
              className="kb-button kb-button-primary"
              onClick={openCreateForm}
            >
              <Plus size={17} />
              New knowledge base
            </button>
          )}
        </div>
      </header>

      {pageError && (
        <div className="kb-alert kb-alert-error">
          <AlertCircle size={17} />
          <span>{pageError}</span>
          <button type="button" onClick={() => setPageError("")}>
            Dismiss
          </button>
        </div>
      )}

      {notice && (
        <div className="kb-alert kb-alert-success">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>
            Dismiss
          </button>
        </div>
      )}

      {formMode && (
        <section className="kb-form-panel">
          <KnowledgeBaseForm
            knowledgeBase={formMode === "edit" ? editing : null}
            onSubmit={handleCreateOrUpdate}
            onCancel={() => {
              setFormMode(null);
              setEditing(null);
            }}
            loading={saving}
          />
        </section>
      )}

      <div className="kb-overview">
        <div className="kb-stat-card">
          <div className="kb-stat-icon purple">
            <BookOpen size={20} />
          </div>
          <div>
            <span>Knowledge bases</span>
            <strong>{knowledgeBases.length}</strong>
          </div>
        </div>

        <div className="kb-stat-card">
          <div className="kb-stat-icon blue">
            <FileText size={20} />
          </div>
          <div>
            <span>Total documents</span>
            <strong>
              {knowledgeBases.reduce(
                (total, item) => total + item.document_count,
                0,
              )}
            </strong>
          </div>
        </div>

        <div className="kb-stat-card">
          <div className="kb-stat-icon green">
            <BookOpen size={20} />
          </div>
          <div>
            <span>Active bases</span>
            <strong>
              {knowledgeBases.filter((item) => item.is_active).length}
            </strong>
          </div>
        </div>
      </div>

      <div className="kb-workspace">
        <section className="kb-panel kb-sidebar-panel">
          <div className="kb-panel-heading">
            <div>
              <h2>Your knowledge bases</h2>
              <p>Select a knowledge base to manage its documents.</p>
            </div>
            <span className="kb-count">{knowledgeBases.length}</span>
          </div>

          {loading ? (
            <div className="kb-loading">
              <LoaderCircle size={20} className="kb-spinner" />
              <span>Loading knowledge bases...</span>
            </div>
          ) : (
            <KnowledgeBaseList
              items={knowledgeBases}
              selectedId={selected?.id ?? null}
              onSelect={(item) => {
                setSelected(item);
                setPageError("");
                setNotice("");
              }}
              onEdit={openEditForm}
              onDelete={(item) => void handleDeleteKnowledgeBase(item)}
              canManage={canManage}
            />
          )}
        </section>

        <section className="kb-panel kb-details-panel">
          {selected ? (
            <>
              <div className="kb-panel-heading kb-details-heading">
                <div>
                  <span className="kb-eyebrow">SELECTED KNOWLEDGE BASE</span>
                  <h2>{selected.name}</h2>
                  <p>
                    {selected.description || "No description provided."}
                  </p>
                </div>
                <span
                  className={`kb-status ${selected.is_active ? "active" : "inactive"}`}
                >
                  {selected.is_active ? "Active" : "Inactive"}
                </span>
              </div>

              <div className="kb-section-heading">
                <div>
                  <h3>Documents</h3>
                  <p>Files stored in this knowledge base.</p>
                </div>
                <span className="kb-count">{documents.length}</span>
              </div>

              {canManage && (
                <DocumentUpload
                  onUpload={handleUpload}
                  disabled={!selected.is_active}
                />
              )}

              {!selected.is_active && canManage && (
                <p className="kb-muted-notice">
                  This knowledge base is inactive. Activate it to upload
                  documents.
                </p>
              )}

              <DocumentList
                documents={documents}
                loading={documentsLoading}
                onDelete={(document) => void handleDeleteDocument(document)}
                canManage={canManage}
              />
            </>
          ) : (
            <div className="kb-select-prompt">
              <div className="kb-empty-icon">
                <BookOpen size={28} />
              </div>
              <h2>Select a knowledge base</h2>
              <p>
                Choose a knowledge base from the left to view and manage its
                documents.
              </p>
              {knowledgeBases.length === 0 && canManage && (
                <button
                  type="button"
                  className="kb-button kb-button-primary"
                  onClick={openCreateForm}
                >
                  <Plus size={17} />
                  Create your first knowledge base
                </button>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
