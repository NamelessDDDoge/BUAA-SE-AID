import http from './request'

export interface DetectionTaskQuery {
  page?: number
  page_size?: number
  status?: string
  task_type?: 'image' | 'paper' | 'review'
  keyword?: string
  startTime?: string
  endTime?: string
}

export default {
  listUserTasks(params: DetectionTaskQuery) {
    return http.get('/user-tasks/', { params })
  },

  submitDetection(data: any) {
    return http.post('/detection/submit/', data)
  },

  getTaskResults(taskId: string | number) {
    return http.get(`/tasks/${taskId}/results/`)
  },

  getFakeResults(params: { task_id: string | number; include_image?: number }) {
    return http.get(`/tasks/${params.task_id}/fake_results/?include_image=${params.include_image ?? 0}`)
  },

  getNormalResults(params: { task_id: string | number; include_image?: number }) {
    return http.get(`/tasks/${params.task_id}/normal_results/?include_image=${params.include_image ?? 0}`)
  },

  getSingleImageResult(resultId: string | number) {
    return http.get(`/results/${resultId}/`)
  },

  getTaskDetail(taskId: string | number) {
    return http.get(`/detection-task/${taskId}/status/`)
  },

  downloadTaskReport(taskId: string | number) {
    return http.get(`/tasks/${taskId}/report/`, {
      responseType: 'blob',
    })
  },

  deleteTask(taskId: string | number) {
    return http.delete(`/detection-task-delete/${taskId}/`)
  },

  clearHistory() {
    return http.delete('/detection-history/clear/')
  },
}
