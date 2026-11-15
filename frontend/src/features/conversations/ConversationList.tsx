
import type { Conversation, ConversationStatus } from "./types";
import { Search, MessageSquare } from "lucide-react";
interface Props {
  conversations: Conversation[];
  selectedId: string | null;
  search: string;
  statusFilter: string;
  onSearchChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onSelect: (id: string) => void;
}

const filters = [
  { label: "All", value: "all" },
  { label: "Open", value: "open" },
  { label: "Pending", value: "pending" },
  { label: "Resolved", value: "resolved" },
  { label: "Closed", value: "closed" },
];

const formatTime = (value: string) =>
  new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

const statusLabel: Record<ConversationStatus, string> = {
  open: "Open",
  pending: "Pending",
  resolved: "Resolved",
  closed: "Closed",
};

export default function ConversationList({
  conversations,
  selectedId,
  search,
  statusFilter,
  onSearchChange,
  onStatusFilterChange,
  onSelect,
}: Props) {
  return (
    <aside className="conversation-list-panel">
      <div className="conversation-list-header">
        <div>
          <h2>Inbox</h2>
          <span>{conversations.length} conversations</span>
        </div>
        <MessageSquare size={19} />
      </div>

      <div className="conversation-search">
        <Search size={17} />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search conversations..."
          aria-label="Search conversations"
        />
      </div>

      <div className="conversation-filters">
        {filters.map((filter) => (
          <button
            key={filter.value}
            className={statusFilter === filter.value ? "active" : ""}
            onClick={() => onStatusFilterChange(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="conversation-items">
        {conversations.length === 0 ? (
          <div className="conversation-list-empty">
            <MessageSquare size={25} />
            <strong>No conversations found</strong>
            <span>Try another search or status filter.</span>
          </div>
        ) : (
          conversations.map((conversation) => {
            const customer = conversation.customer;
            const initials = customer?.full_name
              ? customer.full_name
                  .split(" ")
                  .slice(0, 2)
                  .map((part) => part[0])
                  .join("")
                  .toUpperCase()
              : "CU";

            return (
              <button
                key={conversation.id}
                className={`conversation-item ${
                  selectedId === conversation.id ? "selected" : ""
                }`}
                onClick={() => onSelect(conversation.id)}
              >
                <div className="conversation-avatar">{initials}</div>

                <div className="conversation-item-content">
                  <div className="conversation-item-top">
                    <strong>{customer?.full_name ?? "Unknown customer"}</strong>
                    <time>{formatTime(conversation.updated_at)}</time>
                  </div>

                  <div className="conversation-item-subject">
                    {conversation.subject || "No subject"}
                  </div>

                  <div className="conversation-item-bottom">
                    <span
                      className={`status-pill status-${conversation.status}`}
                    >
                      {statusLabel[conversation.status]}
                    </span>

                    <span className="priority-indicator">
                      <span
                        className={`priority-dot priority-${conversation.priority}`}
                      />
                      {conversation.priority}
                    </span>
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}
