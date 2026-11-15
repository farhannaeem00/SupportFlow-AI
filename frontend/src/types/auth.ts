
export interface AuthUser {
  id: string
  full_name: string
  email: string
  is_active: boolean
}

export interface AuthOrganization {
  id: string
  name: string
  slug: string
  public_key: string
  role: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  public_key: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
  organization: Organization | null
  organizations: AuthOrganization[]
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  full_name: string
  email: string
  password: string
  organization_name: string
}
