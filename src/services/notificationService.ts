import { api } from './api'

export const notificationService = {
  async getNotifications() {
    const { data } = await api.get('/notifications')
    return data
  },

  async getUnreadCount() {
    const { data } = await api.get('/notifications/unread-count')
    return data.count as number
  },

  async markRead(id: string) {
    const { data } = await api.put(`/notifications/${id}/read`)
    return data
  },

  async markAllRead() {
    const { data } = await api.put('/notifications/read-all')
    return data
  },

  async deleteNotification(id: string) {
    const { data } = await api.delete(`/notifications/${id}`)
    return data
  },
}
