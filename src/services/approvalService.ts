import { api } from './api'

export const approvalService = {
  async getApprovals() {
    const { data } = await api.get('/approvals')
    return data
  },

  async getPendingApprovals() {
    const { data } = await api.get('/approvals/pending')
    return data
  },

  async createApprovalWorkflow(
    documentId: string,
    stages: Array<{ stage_order: number; stage_name: string; reviewer_id: string }>
  ) {
    const { data } = await api.post(`/approvals/${documentId}/stages`, stages)
    return data
  },

  async reviewStage(stageId: string, payload: { status: string; comment?: string }) {
    const { data } = await api.put(`/approvals/stages/${stageId}`, payload)
    return data
  },
}
