
import { useEffect, useState, type FormEvent } from "react";
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeBaseUpdate,
} from "./knowledgeBaseApi";

interface KnowledgeBaseFormProps {
  knowledgeBase?: KnowledgeBase | null;
  onSubmit: (data: KnowledgeBaseCreate | KnowledgeBaseUpdate) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export default function KnowledgeBaseForm({
  knowledgeBase,
  onSubmit,
  onCancel,
  loading = false,
}: KnowledgeBaseFormProps) {
  const [name, setName] = useState(knowledgeBase?.name ?? "");
  const [description, setDescription] = useState(
    knowledgeBase?.description ?? "",
  );
  const [isActive, setIsActive] = useState(
    knowledgeBase?.is_active ?? true,
  );
  const [error, setError] = useState("");

  useEffect(() => {
    setName(knowledgeBase?.name ?? "");
    setDescription(knowledgeBase?.description ?? "");
    setIsActive(knowledgeBase?.is_active ?? true);
    setError("");
  }, [knowledgeBase]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedName = name.trim();

    if (trimmedName.length < 2) {
      setError("Name must contain at least 2 characters.");
      return;
    }

    if (trimmedName.length > 150) {
      setError("Name cannot exceed 150 characters.");
      return;
    }

    if (description.length > 2000) {
      setError("Description cannot exceed 2000 characters.");
      return;
    }

    setError("");

    const data = knowledgeBase
      ? {
          name: trimmedName,
          description: description.trim() || null,
          is_active: isActive,
        }
      : {
          name: trimmedName,
          description: description.trim() || null,
        };

    try {
      await onSubmit(data);
    } catch {
      setError("Unable to save the knowledge base. Please try again.");
    }
  }

  return (
    <form className="kb-form" onSubmit={handleSubmit}>
      <div className="kb-form-header">
        <div>
          <span className="kb-eyebrow">
            {knowledgeBase ? "EDIT RESOURCE" : "NEW RESOURCE"}
          </span>
          <h3>{knowledgeBase ? "Edit knowledge base" : "Create knowledge base"}</h3>
          <p>Organize the information your AI assistant can use.</p>
        </div>
      </div>

      <label className="kb-field">
        <span>Knowledge base name</span>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. Product documentation"
          maxLength={150}
          required
          autoFocus
        />
      </label>

      <label className="kb-field">
        <span>Description <small>(optional)</small></span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Describe the information stored in this knowledge base..."
          rows={4}
          maxLength={2000}
        />
        <small className="kb-character-count">
          {description.length}/2000
        </small>
      </label>

      {knowledgeBase && (
        <label className="kb-toggle">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(event) => setIsActive(event.target.checked)}
          />
          <span>
            <strong>Active knowledge base</strong>
            <small>Allow this knowledge base to remain active.</small>
          </span>
        </label>
      )}

      {error && <div className="kb-inline-error">{error}</div>}

      <div className="kb-form-actions">
        <button
          type="button"
          className="kb-button kb-button-secondary"
          onClick={onCancel}
          disabled={loading}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="kb-button kb-button-primary"
          disabled={loading}
        >
          {loading
            ? "Saving..."
            : knowledgeBase
              ? "Save changes"
              : "Create knowledge base"}
        </button>
      </div>
    </form>
  );
}
