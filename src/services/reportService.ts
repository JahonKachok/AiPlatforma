import { api } from './api'

export const reportService = {
  async getDashboardStats() {
    const { data } = await api.get('/reports/dashboard')
    return data
  },

  async getProjectsAnalytics() {
    const { data } = await api.get('/reports/projects')
    return data
  },

  async getTasksAnalytics() {
    const { data } = await api.get('/reports/tasks')
    return data
  },

  async getFinanceAnalytics() {
    const { data } = await api.get('/reports/finance')
    return data
  },

  async getUserPerformance(userId: string) {
    const { data } = await api.get(`/reports/users/${userId}/performance`)
    return data
  },
}
