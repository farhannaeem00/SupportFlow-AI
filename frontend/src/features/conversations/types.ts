
export type ConversationStatus = "open" | "pending" | "resolved" | "closed";
export type ConversationPriority = "low" | "normal" | "high" | "urgent";

export interface Customer {
  id: string;
  organization_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  company: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TeamMember {
  id: string;
  full_name: string;
  email: string;
  role: "owner" | "agent";
  is_active: boolean;
}

export interface Conversation {
  id: string;
  organization_id: string;
  customer_id: string;
  assigned_to_id: string | null;
  subject: string;
  status: ConversationStatus;
  priority: ConversationPriority;
  channel: string;
  created_at: string;
  updated_at: string;
  customer?: Customer;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: string;
  sender_user_id: string | null;
  sender_customer_id: string | null;
  content: string;
  message_type: string;
  created_at: string;
}
