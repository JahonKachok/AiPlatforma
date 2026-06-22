import { api, BASE_UPLOAD_URL } from './api'

export const documentService = {
  async getDocuments(params?: {
    project_id?: string
    status?: string
    doc_type?: string
    search?: string
  }) {
    const { data } = await api.get('/documents', { params })
    return data
  },

  async getDocument(id: string) {
    const { data } = await api.get(`/documents/${id}`)
    return data
  },

  async uploadDocument(formData: FormData) {
    const { data } = await api.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async updateDocument(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/documents/${id}`, payload)
    return data
  },

  async deleteDocument(id: string) {
    const { data } = await api.delete(`/documents/${id}`)
    return data
  },

  async uploadVersion(documentId: string, file: File, notes?: string) {
    const formData = new FormData()
    formData.append('file', file)
    if (notes) formData.append('notes', notes)
    const { data } = await api.post(`/documents/${documentId}/versions`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async getVersions(documentId: string) {
    const { data } = await api.get(`/documents/${documentId}/versions`)
    return data
  },

  getDownloadUrl(documentId: string) {
    const token = localStorage.getItem('access_token')
    return `${BASE_UPLOAD_URL}/api/documents/${documentId}/download?token=${token}`
  },

  async getAudit(documentId: string) {
    const { data } = await api.get(`/documents/${documentId}/audit`)
    return data
  },

  async bulkDownload(docIds: string[], zipName: string = 'documents') {
    const params = new URLSearchParams()
    docIds.forEach(id => params.append('doc_ids', id))
    params.append('zip_name', zipName)

    window.location.href = `${BASE_UPLOAD_URL}/api/documents/bulk-download?${params.toString()}&token=${localStorage.getItem('access_token')}`
  },

  async approveDocument(id: string, payload: Record<string, unknown>) {
    const { data } = await api.put(`/documents/${id}`, payload)
    return data
  },
}
