
import { useState } from "react";
import { X, MessageSquarePlus, LoaderCircle } from "lucide-react";
import type {
  Customer,
  ConversationPriority,
} from "./types";
import "./NewConversationModal.css";

interface NewConversationModalProps {
  customers: Customer[];
  onClose: () => void;
  onCreate: (data: {
    customer_id: string;
    subject: string;
    priority: ConversationPriority;
    initialMessage: string;
  }) => Promise<void>;
}

export default function NewConversationModal({
  customers,
  onClose,
  onCreate,
}: NewConversationModalProps) {
  const [customerId, setCustomerId] = useState("");
  const [subject, setSubject] = useState("");
  const [priority, setPriority] =
    useState<ConversationPriority>("normal");
  const [initialMessage, setInitialMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");

    if (!customerId) {
      setError("Please select a customer.");
      return;
    }

    if (!subject.trim()) {
      setError("Please enter a conversation subject.");
      return;
    }

    setSubmitting(true);

    try {
      await onCreate({
        customer_id: customerId,
        subject: subject.trim(),
        priority,
        initialMessage: initialMessage.trim(),
      });
      onClose();
    } catch {
      setError("Unable to create conversation. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="new-conversation-overlay" onClick={onClose}>
      <div
        className="new-conversation-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="new-conversation-header">
          <div className="new-conversation-title">
            <div className="new-conversation-icon">
              <MessageSquarePlus size={20} />
            </div>
            <div>
              <h2>New conversation</h2>
              <p>Start a conversation with a customer.</p>
            </div>
          </div>

          <button
            type="button"
            className="new-conversation-close"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </header>

        <form onSubmit={handleSubmit}>
          <div className="new-conversation-body">
            <label>
              Customer <span>*</span>
              <select
                value={customerId}
                onChange={(event) => setCustomerId(event.target.value)}
                required
              >
                <option value="">Select a customer</option>
                {customers
                  .filter((customer) => customer.is_active)
                  .map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.full_name} ({customer.email})
                    </option>
                  ))}
              </select>
            </label>

            <label>
              Subject <span>*</span>
              <input
                type="text"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                placeholder="e.g. Help with my recent order"
                maxLength={200}
                required
              />
            </label>

            <label>
              Priority
              <select
                value={priority}
                onChange={(event) =>
                  setPriority(event.target.value as ConversationPriority)
                }
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </label>

            <label>
              Initial message
              <textarea
                value={initialMessage}
                onChange={(event) => setInitialMessage(event.target.value)}
                placeholder="Write an optional first message..."
                rows={4}
                maxLength={10000}
              />
            </label>

            {customers.filter((customer) => customer.is_active).length === 0 && (
              <p className="new-conversation-error">
                No active customers found. Add a customer before creating a
                conversation.
              </p>
            )}

            {error && (
              <p className="new-conversation-error">{error}</p>
            )}
          </div>

          <footer className="new-conversation-footer">
            <button
              type="button"
              className="new-conversation-cancel"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="new-conversation-submit"
              disabled={
                submitting ||
                customers.filter((customer) => customer.is_active).length === 0
              }
            >
              {submitting ? (
                <>
                  <LoaderCircle size={16} className="sf-spin" />
                  Creating...
                </>
              ) : (
                "Create conversation"
              )}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
