import { api } from './api'

export const organizationService = {
  // Departments
  async getDepartments() {
    const { data } = await api.get('/organization/departments')
    return data
  },

  async getDepartment(id: string) {
    const { data } = await api.get(`/organization/departments/${id}`)
    return data
  },

  async createDepartment(payload: Record<string, unknown>) {
    const { data } = await api.post('/organization/departments', payload)
    return data
  },

  async updateDepartment(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/organization/departments/${id}`, payload)
    return data
  },

  async deleteDepartment(id: string) {
    const { data } = await api.delete(`/organization/departments/${id}`)
    return data
  },

  // Organizational Units
  async getUnits(departmentId?: string) {
    const { data } = await api.get('/organization/units', {
      params: { department_id: departmentId }
    })
    return data
  },

  async getUnit(id: string) {
    const { data } = await api.get(`/organization/units/${id}`)
    return data
  },

  async createUnit(payload: Record<string, unknown>) {
    const { data } = await api.post('/organization/units', payload)
    return data
  },

  async updateUnit(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/organization/units/${id}`, payload)
    return data
  },

  // Department Members
  async getMembers(unitId?: string, userId?: string) {
    const { data } = await api.get('/organization/members', {
      params: { unit_id: unitId, user_id: userId }
    })
    return data
  },

  async addMember(payload: Record<string, unknown>) {
    const { data } = await api.post('/organization/members', payload)
    return data
  },

  async updateMember(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/organization/members/${id}`, payload)
    return data
  },

  async removeMember(id: string) {
    const { data } = await api.delete(`/organization/members/${id}`)
    return data
  },

  // Reporting Chain
  async getReportingChain(userId: string) {
    const { data } = await api.get(`/organization/reporting-chain/${userId}`)
    return data
  },

  async getDirectReports(managerId: string) {
    const { data } = await api.get(`/organization/direct-reports/${managerId}`)
    return data
  },

  async createReportingRelationship(payload: Record<string, unknown>) {
    const { data } = await api.post('/organization/reporting-relationships', payload)
    return data
  },

  async deleteReportingRelationship(id: string) {
    const { data } = await api.delete(`/organization/reporting-relationships/${id}`)
    return data
  },
}
