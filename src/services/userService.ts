import { api } from './api'

export const userService = {
  async getUsers(params?: { search?: string }) {
    const { data } = await api.get('/users', { params })
    return data
  },

  async getUser(id: string) {
    const { data } = await api.get(`/users/${id}`)
    return data
  },

  async updateUser(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/users/${id}`, payload)
    return data
  },

  async deactivateUser(id: string) {
    const { data } = await api.delete(`/users/${id}`)
    return data
  },

  async uploadAvatar(id: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post(`/users/${id}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async getUserStats(id: string) {
    const { data } = await api.get(`/users/${id}/stats`)
    return data
  },
}
