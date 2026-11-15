
import {
  ArrowDownLeft,
  Bot,
  UserRound,
  Headset,
  LoaderCircle,
  Mail,
} from "lucide-react";
import ReplyComposer from "./ReplyComposer";
import type {
  Conversation,
  ConversationPriority,
  ConversationStatus,
  Message,
  TeamMember,
} from "./types";

interface Props {
  conversation: Conversation | null;
  messages: Message[];
  messagesLoading: boolean;
  teamMembers: TeamMember[];
  sending: boolean;
  updating: boolean;
  onSendMessage: (content: string) => Promise<void>;
  onStatusChange: (status: ConversationStatus) => Promise<void>;
  onPriorityChange: (priority: ConversationPriority) => Promise<void>;
  onAssignmentChange: (memberId: string) => Promise<void>;
}

const formatMessageTime = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

export default function ConversationDetails({
  conversation,
  messages,
  messagesLoading,
  teamMembers,
  sending,
  updating,
  onSendMessage,
  onStatusChange,
  onPriorityChange,
  onAssignmentChange,
}: Props) {
  if (!conversation) {
    return (
      <main className="conversation-details-panel conversation-no-selection">
        <div className="no-selection-icon">
          <Mail size={30} />
        </div>
        <h2>Select a conversation</h2>
        <p>Choose a conversation from your inbox to view its messages.</p>
      </main>
    );
  }

  const customer = conversation.customer;

  return (
    <main className="conversation-details-panel">
      <header className="conversation-detail-header">
        <div className="conversation-customer-heading">
          <div className="conversation-avatar detail-avatar">
            {customer?.full_name
              ?.split(" ")
              .slice(0, 2)
              .map((part) => part[0])
              .join("")
              .toUpperCase() ?? "CU"}
          </div>

          <div>
            <h2>{customer?.full_name ?? "Unknown customer"}</h2>
            <span>
              {customer?.email ?? "Customer details unavailable"}
            </span>
          </div>
        </div>

        <div className="conversation-channel">
          <span className="channel-dot" />
          {conversation.channel.replaceAll("_", " ")}
        </div>
      </header>

      <div className="conversation-subject">
        <div>
          <span>SUBJECT</span>
          <h3>{conversation.subject || "No subject"}</h3>
        </div>
        <span className="conversation-id">
          #{conversation.id.slice(0, 8)}
        </span>
      </div>

      <div className="conversation-management">
        <label>
          <span>Status</span>
          <select
            value={conversation.status}
            disabled={updating}
            onChange={(event) =>
              void onStatusChange(event.target.value as ConversationStatus)
            }
          >
            <option value="open">Open</option>
            <option value="pending">Pending</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </label>

        <label>
          <span>Priority</span>
          <select
            value={conversation.priority}
            disabled={updating}
            onChange={(event) =>
              void onPriorityChange(event.target.value as ConversationPriority)
            }
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>

        <label className="assignment-control">
          <span>Assigned to</span>
          <select
            value={conversation.assigned_to_id ?? ""}
            disabled={updating}
            onChange={(event) => void onAssignmentChange(event.target.value)}
          >
            <option value="">Unassigned</option>
            {teamMembers
              .filter((member) => member.is_active)
              .map((member) => (
                <option key={member.id} value={member.id}>
                  {member.full_name} ({member.role})
                </option>
              ))}
          </select>
        </label>
      </div>

      <section className="conversation-message-area">
        <div className="message-date-divider">
          <span>MESSAGE HISTORY</span>
        </div>

        {messagesLoading ? (
          <div className="messages-loading">
            <LoaderCircle size={22} className="sf-spin" />
            Loading messages...
          </div>
        ) : messages.length === 0 ? (
          <div className="messages-empty">
            <MessageSquareIcon />
            <strong>No messages yet</strong>
            <span>Send a reply to start the conversation.</span>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => {
              const isCustomer = message.sender_type === "customer";
              const isAI = message.sender_type === "ai";

              return (
                <article
                  key={message.id}
                  className={`message-row ${
                    isCustomer ? "message-customer" : "message-agent"
                  }`}
                >
                  <div className="message-avatar">
                    {isCustomer ? (
                      <UserRound size={16} />
                    ) : isAI ? (
                      <Bot size={16} />
                    ) : (
                      <Headset size={16} />
                    )}
                  </div>

                  <div className="message-content">
                    <div className="message-meta">
                      <strong>
                        {isCustomer ? "Customer" : isAI ? "AI Assistant" : "Team"}
                      </strong>
                      <time>{formatMessageTime(message.created_at)}</time>
                    </div>

                    <div className="message-bubble">{message.content}</div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <ReplyComposer
        disabled={sending || conversation.status === "closed"}
        sending={sending}
        onSend={onSendMessage}
      />
    </main>
  );
}

function MessageSquareIcon() {
  return <ArrowDownLeft size={25} />;
}
