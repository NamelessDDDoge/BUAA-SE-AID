import { defineStore } from "pinia"

export const useMessageStore = defineStore('message', {
  state: () => ({
    notifications: [] as Array<{ type: string; message: string }>
  }),

  actions: {
    addNotification(notification: { type: string; message: string }) {
      this.notifications.unshift(notification)
    },
    clearNotifications() {
      this.notifications = []
    }
  }
})