
import axios from 'axios'

const widgetApi = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

export interface WidgetConfig {
  organization_name: string
}

export interface WidgetSession {
  session_token: string
  expires_at: string
}

export interface WidgetMessage {
  id: string
  sender_type: string
  content: string
  message_type: string
  created_at: string
}

export interface WidgetConversation {
  id: string
  subject: string
  status: string
  created_at: string
  messages: WidgetMessage[]
}

export interface CreateWidgetConversation {
  full_name: string
  email?: string
  subject: string
  message: string
}

function sessionHeaders(sessionToken: string) {
  return {
    'X-Widget-Session': sessionToken,
  }
}

export const widgetApiService = {
  async getConfig(publicKey: string) {
    const response = await widgetApi.get<WidgetConfig>(
      `/widget/${encodeURIComponent(publicKey)}`
    )
    return response.data
  },

  async createSession(publicKey: string) {
    const response = await widgetApi.post<WidgetSession>(
      `/widget/${encodeURIComponent(publicKey)}/sessions`
    )
    return response.data
  },

  async createConversation(
    publicKey: string,
    sessionToken: string,
    payload: CreateWidgetConversation
  ) {
    const response = await widgetApi.post<WidgetConversation>(
      `/widget/${encodeURIComponent(publicKey)}/conversations`,
      payload,
      { headers: sessionHeaders(sessionToken) }
    )
    return response.data
  },

  async sendMessage(
    publicKey: string,
    sessionToken: string,
    message: string
  ) {
    const response = await widgetApi.post<WidgetMessage>(
      `/widget/${encodeURIComponent(publicKey)}/messages`,
      { message },
      { headers: sessionHeaders(sessionToken) }
    )
    return response.data
  },

  async getConversation(
    publicKey: string,
    sessionToken: string
  ) {
    const response = await widgetApi.get<WidgetConversation>(
      `/widget/${encodeURIComponent(publicKey)}/conversation`,
      { headers: sessionHeaders(sessionToken) }
    )
    return response.data
  },
}
