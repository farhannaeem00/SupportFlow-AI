
import { BookOpen, FileText, MoreVertical, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import type { KnowledgeBase } from "./knowledgeBaseApi";

interface KnowledgeBaseListProps {
  items: KnowledgeBase[];
  selectedId: string | null;
  onSelect: (item: KnowledgeBase) => void;
  onEdit: (item: KnowledgeBase) => void;
  onDelete: (item: KnowledgeBase) => void;
  canManage: boolean;
}

export default function KnowledgeBaseList({
  items,
  selectedId,
  onSelect,
  onEdit,
  onDelete,
  canManage,
}: KnowledgeBaseListProps) {
  const [menuId, setMenuId] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className="kb-empty-state">
        <div className="kb-empty-icon">
          <BookOpen size={25} />
        </div>
        <h3>No knowledge bases yet</h3>
        <p>Create a knowledge base to start organizing your AI resources.</p>
      </div>
    );
  }

  return (
    <div className="kb-list">
      {items.map((item) => (
        <div
          key={item.id}
          className={`kb-list-item ${selectedId === item.id ? "selected" : ""}`}
        >
          <button
            type="button"
            className="kb-list-select"
            onClick={() => {
              setMenuId(null);
              onSelect(item);
            }}
          >
            <div className="kb-list-icon">
              <BookOpen size={20} />
            </div>

            <div className="kb-list-content">
              <strong>{item.name}</strong>
              <span>
                <FileText size={13} />
                {item.document_count}{" "}
                {item.document_count === 1 ? "document" : "documents"}
              </span>
              {item.description && (
                <p>{item.description}</p>
              )}
            </div>

            <span
              className={`kb-status ${item.is_active ? "active" : "inactive"}`}
            >
              {item.is_active ? "Active" : "Inactive"}
            </span>
          </button>

          {canManage && (
            <div className="kb-item-menu">
              <button
                type="button"
                className="kb-icon-button"
                aria-label={`Actions for ${item.name}`}
                onClick={() =>
                  setMenuId(menuId === item.id ? null : item.id)
                }
              >
                <MoreVertical size={18} />
              </button>

              {menuId === item.id && (
                <div className="kb-dropdown">
                  <button
                    type="button"
                    onClick={() => {
                      setMenuId(null);
                      onEdit(item);
                    }}
                  >
                    <Pencil size={15} />
                    Edit
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => {
                      setMenuId(null);
                      onDelete(item);
                    }}
                  >
                    <Trash2 size={15} />
                    Delete
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
