import { api } from './api'

export const telegramService = {
  async createTelegramLink(userId: string) {
    const { data } = await api.post(`/users/${userId}/telegram/link`)
    return data
  },

  async removeTelegramLink(userId: string) {
    const { data } = await api.post(`/users/${userId}/telegram/unlink`)
    return data
  },

  async getTelegramInfo() {
    const { data } = await api.get('/telegram/info')
    return data
  },

  async sendMessage(message: string, parseMode: string = 'HTML') {
    const { data } = await api.post('/telegram/send-message', {
      message,
      parse_mode: parseMode,
    })
    return data
  },

  async sendNotification(title: string, description: string, notificationType: string = 'info') {
    const { data } = await api.post('/telegram/send-notification', {
      title,
      description,
      notification_type: notificationType,
    })
    return data
  },
}
