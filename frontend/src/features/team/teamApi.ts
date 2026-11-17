import api from "../../lib/api";
import type {
  CreateTeamMemberPayload,
  TeamActionResponse,
  TeamMember,
  UpdateTeamRolePayload,
} from "./types";

export const teamApi = {
  async getMembers(): Promise<TeamMember[]> {
    const response = await api.get<TeamMember[]>("/team/members");
    return response.data;
  },

  async createMember(
    payload: CreateTeamMemberPayload,
  ): Promise<TeamActionResponse> {
    const response = await api.post<TeamActionResponse>(
      "/team/members",
      payload,
    );
    return response.data;
  },

  async updateMemberRole(
    memberId: string,
    payload: UpdateTeamRolePayload,
  ): Promise<TeamActionResponse> {
    const response = await api.patch<TeamActionResponse>(
      `/team/members/${memberId}/role`,
      payload,
    );
    return response.data;
  },

  async removeMember(memberId: string): Promise<TeamActionResponse> {
    const response = await api.delete<TeamActionResponse>(
      `/team/members/${memberId}`,
    );
    return response.data;
  },
};