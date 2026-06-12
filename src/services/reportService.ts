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

  async getEmployeesReport() {
    const { data } = await api.get('/reports/employees')
    return data
  },

  async downloadExport(kind: 'projects' | 'tasks' | 'finance' | 'employees') {
    const response = await api.get(`/reports/export/${kind}`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${kind}_report.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  },
}
