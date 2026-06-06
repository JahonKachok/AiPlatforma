import { api } from './api'

export const requestService = {
  async getRequests(params?: { project_id?: string; status?: string }) {
    const { data } = await api.get('/requests', { params })
    return data
  },

  async getRequest(id: string) {
    const { data } = await api.get(`/requests/${id}`)
    return data
  },

  async createRequest(payload: Record<string, unknown>) {
    const { data } = await api.post('/requests', payload)
    return data
  },

  async updateRequest(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/requests/${id}`, payload)
    return data
  },

  async deleteRequest(id: string) {
    const { data } = await api.delete(`/requests/${id}`)
    return data
  },

  async addComment(requestId: string, content: string) {
    const { data } = await api.post(`/requests/${requestId}/comments`, { content })
    return data
  },
}
