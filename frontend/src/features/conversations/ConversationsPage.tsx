
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Inbox, LoaderCircle, MessageSquare,Plus } from "lucide-react";
import { conversationApi } from "./conversationApi";
import ConversationList from "./ConversationList";
import ConversationDetails from "./ConversationDetails";
import type {
  Conversation,
  ConversationPriority,
  ConversationStatus,
  Customer,
  Message,
  TeamMember,
} from "./types";
import "./Conversations.css";
import NewConversationModal from "./NewConversationModal";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [loading, setLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [error, setError] = useState("");

  const [showNewConversation, setShowNewConversation] = useState(false);

  const [sending, setSending] = useState(false);
  const [updating, setUpdating] = useState(false);

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [conversationData, customerData, teamData] = await Promise.all([
        conversationApi.getConversations(),
        conversationApi.getCustomers(),
        conversationApi.getTeamMembers(),
      ]);

      setConversations(conversationData);
      setCustomers(customerData);
      setTeamMembers(teamData);

      setSelectedId((current) => {
        if (current && conversationData.some((item) => item.id === current)) {
          return current;
        }

        return conversationData[0]?.id ?? null;
      });
    } catch {
      setError("Unable to load your conversations. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  const customerMap = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer])),
    [customers],
  );

  const selectedConversation = conversations.find(
    (conversation) => conversation.id === selectedId,
  );

  const enrichedConversations = useMemo(
    () =>
      conversations.map((conversation) => ({
        ...conversation,
        customer: customerMap.get(conversation.customer_id),
      })),
    [conversations, customerMap],
  );

  const filteredConversations = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return enrichedConversations.filter((conversation) => {
      const matchesStatus =
        statusFilter === "all" || conversation.status === statusFilter;

      const customer = conversation.customer;
      const matchesSearch =
        !normalizedSearch ||
        conversation.subject.toLowerCase().includes(normalizedSearch) ||
        customer?.full_name.toLowerCase().includes(normalizedSearch) ||
        customer?.email.toLowerCase().includes(normalizedSearch);

      return matchesStatus && matchesSearch;
    });
  }, [enrichedConversations, search, statusFilter]);

  useEffect(() => {
    if (!selectedId) {
      setMessages([]);
      return;
    }

    let active = true;

    async function loadMessages() {
      setMessagesLoading(true);

      try {
        const data = await conversationApi.getMessages(selectedId!);
        if (active) setMessages(data);
      } catch {
        if (active) setMessages([]);
      } finally {
        if (active) setMessagesLoading(false);
      }
    }

    void loadMessages();

    return () => {
      active = false;
    };
  }, [selectedId]);

  const updateConversationInState = (updated: Conversation) => {
    setConversations((current) =>
      current.map((item) =>
        item.id === updated.id ? { ...item, ...updated } : item,
      ),
    );
  };

  const handleSendMessage = async (content: string) => {
    if (!selectedId) return;

    setSending(true);

    try {
      const message = await conversationApi.sendMessage(selectedId, content);
      setMessages((current) => [...current, message]);
      await loadWorkspace();
    } finally {
      setSending(false);
    }
  };

  const handleStatusChange = async (status: ConversationStatus) => {
    if (!selectedId) return;

    setUpdating(true);

    try {
      const updated = await conversationApi.updateStatus(selectedId, status);
      updateConversationInState(updated);
    } finally {
      setUpdating(false);
    }
  };

  const handlePriorityChange = async (priority: ConversationPriority) => {
    if (!selectedId) return;

    setUpdating(true);

    try {
      const updated = await conversationApi.updatePriority(selectedId, priority);
      updateConversationInState(updated);
    } finally {
      setUpdating(false);
    }
  };

  const handleAssignmentChange = async (memberId: string) => {
    if (!selectedId) return;

    setUpdating(true);

    try {
      const updated = await conversationApi.updateAssignment(
        selectedId,
        memberId || null,
      );
      updateConversationInState(updated);
    } finally {
      setUpdating(false);
    }
  };

  const selectedWithCustomer = selectedConversation
    ? {
        ...selectedConversation,
        customer: customerMap.get(selectedConversation.customer_id),
      }
    : null;

const handleCreateConversation = async (data: {
  customer_id: string;
  subject: string;
  priority: ConversationPriority;
  initialMessage: string;
}) => {
  const created = await conversationApi.createConversation({
    customer_id: data.customer_id,
    subject: data.subject,
    priority: data.priority,
  });

  // Refresh the Inbox and select the newly created conversation.
  const [conversationData, customerData, teamData] = await Promise.all([
    conversationApi.getConversations(),
    conversationApi.getCustomers(),
    conversationApi.getTeamMembers(),
  ]);

  setConversations(conversationData);
  setCustomers(customerData);
  setTeamMembers(teamData);
  setSelectedId(created.id);

  // Send the optional initial message after successful creation.
  if (data.initialMessage) {
    const message = await conversationApi.sendMessage(
      created.id,
      data.initialMessage,
    );
    setMessages([message]);
  } else {
    setMessages([]);
  }
};

  if (loading) {
    return (
      <div className="conversations-loading">
        <LoaderCircle size={28} className="sf-spin" />
        <span>Loading conversations...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="conversations-error">
        <AlertCircle size={24} />
        <p>{error}</p>
        <button onClick={() => void loadWorkspace()}>Try again</button>
      </div>
    );
  }

  return (
    <section className="conversations-page">
      <header className="conversations-heading">
        <div>
          <div className="conversations-eyebrow">
            <Inbox size={14} />
            CUSTOMER SUPPORT
          </div>
          <h1>Conversations</h1>
          <p>Manage customer messages and keep every conversation moving.</p>
        </div>

        <div className="conversations-heading-actions">
  <div className="conversation-count">
    <MessageSquare size={16} />
    <span>{conversations.length} total</span>
  </div>

  <button
    className="new-conversation-button"
    onClick={() => setShowNewConversation(true)}
  >
    <Plus size={17} />
    New conversation
  </button>
</div>

        
      </header>

      <div className="conversations-workspace">
        <ConversationList
          conversations={filteredConversations}
          selectedId={selectedId}
          search={search}
          statusFilter={statusFilter}
          onSearchChange={setSearch}
          onStatusFilterChange={setStatusFilter}
          onSelect={setSelectedId}
        />

        <ConversationDetails
          conversation={selectedWithCustomer ?? null}
          messages={messages}
          messagesLoading={messagesLoading}
          teamMembers={teamMembers}
          sending={sending}
          updating={updating}
          onSendMessage={handleSendMessage}
          onStatusChange={handleStatusChange}
          onPriorityChange={handlePriorityChange}
          onAssignmentChange={handleAssignmentChange}
        />
      </div>

      {showNewConversation && (
  <NewConversationModal
    customers={customers}
    onClose={() => setShowNewConversation(false)}
    onCreate={handleCreateConversation}
  />
)}
    </section>
  );
}
