import http from './request'

export default {
  getUnRead() {
    return http.get('/notification/notify/')
  },

  setReadAll() {
    return http.post('/notification/set_as_read/')
  },

  setSingleRead(data: any) {
    return http.post(`/notification/set_as_read/${data.notification_id}/`)
  },

  getAllNotifications() {
    return http.get('/notification/get/')
  }
}