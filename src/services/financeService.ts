import { api } from './api'

export const financeService = {
  async getRecords(params?: { project_id?: string; type?: string; status?: string }) {
    const { data } = await api.get('/finance/records', { params })
    return data
  },

  async createRecord(payload: Record<string, unknown>) {
    const { data } = await api.post('/finance/records', payload)
    return data
  },

  async updateRecord(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/finance/records/${id}`, payload)
    return data
  },

  async deleteRecord(id: string) {
    const { data } = await api.delete(`/finance/records/${id}`)
    return data
  },

  async getContracts(params?: { project_id?: string }) {
    const { data } = await api.get('/finance/contracts', { params })
    return data
  },

  async createContract(payload: Record<string, unknown>) {
    const { data } = await api.post('/finance/contracts', payload)
    return data
  },

  async updateContract(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/finance/contracts/${id}`, payload)
    return data
  },

  async getEmployeeContracts(params?: { project_id?: string; user_id?: string }) {
    const { data } = await api.get('/finance/employee-contracts', { params })
    return data
  },

  async createEmployeeContract(payload: Record<string, unknown>) {
    const { data } = await api.post('/finance/employee-contracts', payload)
    return data
  },

  async updateEmployeeContract(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/finance/employee-contracts/${id}`, payload)
    return data
  },

  async getStats() {
    const { data } = await api.get('/finance/stats')
    return data
  },

  async getProjectSummary(projectId: string) {
    const { data } = await api.get(`/finance/project/${projectId}/summary`)
    return data
  },
}
