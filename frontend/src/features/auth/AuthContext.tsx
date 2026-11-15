
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import axios from 'axios'
import api, {
  AUTH_TOKEN_KEY,
  ORGANIZATION_ID_KEY,
  ORGANIZATIONS_KEY,
  clearAuthStorage,
} from '../../lib/api'
import type {
  AuthOrganization,
  AuthResponse,
  AuthUser,
  LoginPayload,
  Organization,
  RegisterPayload,
} from '../../types/auth'

interface AuthContextValue {
  user: AuthUser | null
  organization: Organization | null
  organizations: AuthOrganization[]
  isAuthenticated: boolean
  isLoading: boolean
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
  selectOrganization: (organizationId: string) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function saveAuthSession(data: AuthResponse) {
  localStorage.setItem(AUTH_TOKEN_KEY, data.access_token)
  localStorage.setItem(
    ORGANIZATIONS_KEY,
    JSON.stringify(data.organizations),
  )

  const selectedOrganization =
    data.organization ??
    data.organizations[0] ??
    null

  if (selectedOrganization) {
    localStorage.setItem(
      ORGANIZATION_ID_KEY,
      selectedOrganization.id,
    )
  } else {
    localStorage.removeItem(ORGANIZATION_ID_KEY)
  }
}

function readStoredOrganizations(): AuthOrganization[] {
  try {
    const stored = localStorage.getItem(ORGANIZATIONS_KEY)
    return stored ? JSON.parse(stored) as AuthOrganization[] : []
  } catch {
    return []
  }
}

function getStoredOrganization(
  organizations: AuthOrganization[],
): Organization | null {
  const selectedId = localStorage.getItem(ORGANIZATION_ID_KEY)

  const selected = organizations.find(
    (item) => item.id === selectedId,
  )

  if (!selected) return null

  return {
    id: selected.id,
    name: selected.name,
    slug: selected.slug,
    public_key: selected.public_key,
  }
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail

    if (typeof detail === 'string') return detail

    if (Array.isArray(detail)) {
      return detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join(', ')
    }

    return error.response?.data?.message ||
      error.message ||
      'Something went wrong. Please try again.'
  }

  return 'Something went wrong. Please try again.'
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [organization, setOrganization] =
    useState<Organization | null>(null)
  const [organizations, setOrganizations] =
    useState<AuthOrganization[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const applySession = useCallback((data: AuthResponse) => {
    saveAuthSession(data)
    setUser(data.user)
    setOrganizations(data.organizations)

    const selected = data.organization ??
      data.organizations[0] ??
      null

    setOrganization(
      selected
        ? {
            id: selected.id,
            name: selected.name,
            slug: selected.slug,
            public_key: selected.public_key,
          }
        : null,
    )
  }, [])

  useEffect(() => {
    let active = true

    async function restoreSession() {
      const token = localStorage.getItem(AUTH_TOKEN_KEY)

      if (!token) {
        setIsLoading(false)
        return
      }

      try {
        const response = await api.get<AuthUser>('/auth/me')

        if (!active) return

        const storedOrganizations = readStoredOrganizations()

        setUser(response.data)
        setOrganizations(storedOrganizations)
        setOrganization(
          getStoredOrganization(storedOrganizations),
        )
      } catch {
        if (!active) return

        clearAuthStorage()
        setUser(null)
        setOrganization(null)
        setOrganizations([])
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void restoreSession()

    return () => {
      active = false
    }
  }, [])

  const login = useCallback(
    async (payload: LoginPayload) => {
      try {
        const response = await api.post<AuthResponse>(
          '/auth/login',
          payload,
        )
        applySession(response.data)
      } catch (error) {
        throw new Error(getErrorMessage(error))
      }
    },
    [applySession],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      try {
        const response = await api.post<AuthResponse>(
          '/auth/register',
          payload,
        )
        applySession(response.data)
      } catch (error) {
        throw new Error(getErrorMessage(error))
      }
    },
    [applySession],
  )

  const logout = useCallback(() => {
    clearAuthStorage()
    setUser(null)
    setOrganization(null)
    setOrganizations([])
  }, [])

  const selectOrganization = useCallback(
    (organizationId: string) => {
      const selected = organizations.find(
        (item) => item.id === organizationId,
      )

      if (!selected) {
        throw new Error('You do not belong to this organization.')
      }

      localStorage.setItem(
        ORGANIZATION_ID_KEY,
        selected.id,
      )

      setOrganization({
        id: selected.id,
        name: selected.name,
        slug: selected.slug,
        public_key: selected.public_key,
      })
    },
    [organizations],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      organization,
      organizations,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      selectOrganization,
    }),
    [
      user,
      organization,
      organizations,
      isLoading,
      login,
      register,
      logout,
      selectOrganization,
    ],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}
