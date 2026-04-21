import http from './request'

export default {
  sendBroadcast(data: any){
    return http.post('/notification/broadcast/', data)
  }
}