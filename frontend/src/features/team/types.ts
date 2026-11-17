
export type TeamRole = "owner" | "agent";

export interface TeamMember {
  id: string;
  full_name: string;
  email: string;
  role: TeamRole;
  is_active: boolean;
}

export interface CreateTeamMemberPayload {
  full_name: string;
  email: string;
  password: string;
  role: TeamRole;
}

export interface UpdateTeamRolePayload {
  role: TeamRole;
}

export interface TeamActionResponse {
  message: string;
  member_id?: string;
}
