
import api from "../../lib/api";
import type {
  Conversation,
  ConversationPriority,
  ConversationStatus,
  Customer,
  Message,
  TeamMember,
} from "./types";

export const conversationApi = {
  async getConversations(): Promise<Conversation[]> {
    const { data } = await api.get("/conversations");
    return data;
  },

  async getCustomers(): Promise<Customer[]> {
    const { data } = await api.get("/customers", {
      params: { skip: 0, limit: 100 },
    });
    return data;
  },

  async getTeamMembers(): Promise<TeamMember[]> {
    const { data } = await api.get("/team/members");
    return data;
  },

  async getMessages(conversationId: string): Promise<Message[]> {
    const { data } = await api.get(
      `/conversations/${conversationId}/messages`,
    );
    return data;
  },

  async sendMessage(conversationId: string, content: string): Promise<Message> {
    const { data } = await api.post(
      `/conversations/${conversationId}/messages`,
      { content },
    );
    return data;
  },

  async updateStatus(
    conversationId: string,
    status: ConversationStatus,
  ): Promise<Conversation> {
    const { data } = await api.patch(
      `/conversations/${conversationId}/status`,
      { status },
    );
    return data;
  },

  async updatePriority(
    conversationId: string,
    priority: ConversationPriority,
  ): Promise<Conversation> {
    const { data } = await api.patch(
      `/conversations/${conversationId}/priority`,
      { priority },
    );
    return data;
  },

  async updateAssignment(
    conversationId: string,
    assigned_to_id: string | null,
  ): Promise<Conversation> {
    const { data } = await api.patch(
      `/conversations/${conversationId}/assignment`,
      { assigned_to_id },
    );
    return data;
  },
  async createConversation(data: {
  customer_id: string;
  subject: string;
  priority: ConversationPriority;
}): Promise<Conversation> {
  const { data: response } = await api.post("/conversations", data);
  return response;
},
};
