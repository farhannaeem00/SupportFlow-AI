import api from "../../lib/api";
import type { AISettings, UpdateAISettingsPayload } from "./types";

export const aiSettingsApi = {
  async getSettings(): Promise<AISettings> {
    const response = await api.get<AISettings>("/ai-settings");
    return response.data;
  },

  async updateSettings(
    payload: UpdateAISettingsPayload,
  ): Promise<AISettings> {
    const response = await api.patch<AISettings>(
      "/ai-settings",
      payload,
    );

    return response.data;
  },
};