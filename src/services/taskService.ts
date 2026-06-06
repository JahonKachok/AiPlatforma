import { api } from './api'

export const taskService = {
  async getTasks(params?: {
    project_id?: string
    assignee_id?: string
    status?: string
    priority?: string
    search?: string
  }) {
    const { data } = await api.get('/tasks', { params })
    return data
  },

  async getTask(id: string) {
    const { data } = await api.get(`/tasks/${id}`)
    return data
  },

  async createTask(payload: Record<string, unknown>) {
    const { data } = await api.post('/tasks', payload)
    return data
  },

  async updateTask(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/tasks/${id}`, payload)
    return data
  },

  async deleteTask(id: string) {
    const { data } = await api.delete(`/tasks/${id}`)
    return data
  },

  async addComment(taskId: string, content: string) {
    const { data } = await api.post(`/tasks/${taskId}/comments`, { content })
    return data
  },

  async updateComment(taskId: string, commentId: string, content: string) {
    const { data } = await api.put(`/tasks/${taskId}/comments/${commentId}`, { content })
    return data
  },

  async deleteComment(taskId: string, commentId: string) {
    const { data } = await api.delete(`/tasks/${taskId}/comments/${commentId}`)
    return data
  },

  async uploadAttachment(taskId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post(`/tasks/${taskId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async deleteAttachment(taskId: string, attachmentId: string) {
    const { data } = await api.delete(`/tasks/${taskId}/attachments/${attachmentId}`)
    return data
  },

  async getOverdueTasks() {
    const { data } = await api.get('/tasks/overdue')
    return data
  },

  async getCalendarTasks(start: string, end: string) {
    const { data } = await api.get('/tasks/calendar', { params: { start, end } })
    return data
  },
}
