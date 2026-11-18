export interface AISettings {
  ai_enabled: boolean;
  suggestions_enabled: boolean;
  confidence_threshold: number;
  escalation_priority_level: number;
  max_context_messages: number;
}

export type UpdateAISettingsPayload = Partial<AISettings>;