
import axios from 'axios'

export const AUTH_TOKEN_KEY = 'supportflow_token'
export const ORGANIZATION_ID_KEY = 'supportflow_organization_id'
export const ORGANIZATIONS_KEY = 'supportflow_organizations'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY)
  const organizationId = localStorage.getItem(ORGANIZATION_ID_KEY)

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  if (organizationId) {
    config.headers['X-Organization-ID'] = organizationId
  }

  return config
})

export function clearAuthStorage() {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(ORGANIZATION_ID_KEY)
  localStorage.removeItem(ORGANIZATIONS_KEY)
}

export default api
