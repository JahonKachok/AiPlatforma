import { api } from './api'

export interface BackupInfo {
  filename: string
  size: number
  created_at: string
}

export const adminService = {
  async createBackup(): Promise<{ message: string; filename: string; size: number }> {
    const { data } = await api.post('/admin/backup')
    return data
  },

  async getBackups(): Promise<BackupInfo[]> {
    const { data } = await api.get('/admin/backups')
    return data
  },

  async downloadBackup(filename: string) {
    const response = await api.get(`/admin/backups/${filename}`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },

  async getAuditLogs(params?: { entity_type?: string; entity_id?: string; user_id?: string }) {
    const { data } = await api.get('/admin/audit-logs', { params })
    return data
  },
}
