import { api } from './api'

export interface RegisterData {
  email: string
  password: string
  full_name: string
  role: string
  department?: string
  phone?: string
}

export const authService = {
  async login(email: string, password: string, totp_code?: string) {
    const { data } = await api.post('/auth/login', { email, password, totp_code })
    return data
  },

  async register(payload: RegisterData) {
    const { data } = await api.post('/auth/register', payload)
    return data
  },

  async logout(refresh_token: string) {
    await api.post('/auth/logout', { refresh_token })
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  async getMe() {
    const { data } = await api.get('/auth/me')
    return data
  },

  async setup2FA() {
    const { data } = await api.post('/auth/2fa/setup')
    return data
  },

  async verify2FA(code: string) {
    const { data } = await api.post('/auth/2fa/verify', { code })
    return data
  },

  async disable2FA(code: string) {
    const { data } = await api.post('/auth/2fa/disable', { code })
    return data
  },

  async getLoginJournal() {
    const { data } = await api.get('/auth/login-journal')
    return data
  },
}
