import { api } from './api'

export const projectService = {
  async getProjects(params?: { status?: string; stage?: string; search?: string }) {
    const { data } = await api.get('/projects', { params })
    return data
  },

  async getProject(id: string) {
    const { data } = await api.get(`/projects/${id}`)
    return data
  },

  async createProject(payload: Record<string, unknown>) {
    const { data } = await api.post('/projects', payload)
    return data
  },

  async updateProject(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/projects/${id}`, payload)
    return data
  },

  async deleteProject(id: string) {
    const { data } = await api.delete(`/projects/${id}`)
    return data
  },

  async addMember(projectId: string, userId: string, roleInProject?: string) {
    const { data } = await api.post(`/projects/${projectId}/members`, {
      user_id: userId,
      role_in_project: roleInProject,
    })
    return data
  },

  async removeMember(projectId: string, userId: string) {
    const { data } = await api.delete(`/projects/${projectId}/members/${userId}`)
    return data
  },

  async addSubObject(projectId: string, payload: Record<string, unknown>) {
    const { data } = await api.post(`/projects/${projectId}/objects`, payload)
    return data
  },

  async addSection(projectId: string, payload: Record<string, unknown>) {
    const { data } = await api.post(`/projects/${projectId}/sections`, payload)
    return data
  },

  async getProjectStats(id: string) {
    const { data } = await api.get(`/projects/${id}/stats`)
    return data
  },
}
