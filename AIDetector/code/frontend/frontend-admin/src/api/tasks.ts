import http from './request'

export interface AdminTaskQuery {
  page?: number
  page_size?: number
  status?: string
  task_type?: 'image' | 'paper' | 'review'
  keyword?: string
  organization?: string | number
  startTime?: string
  endTime?: string
}

export default {
  getTaskSummary(params?: { organization?: string | number }) {
    return http.get('/get-task-summary/', { params })
  },

  getAllTasks(params: AdminTaskQuery) {
    return http.get('/get_all_user_tasks/', { params })
  },

  getTaskDetail(taskId: number, params?: { organization?: string | number }) {
    return http.get(`/get_detection_task_status/${taskId}/`, { params })
  },

  downloadResourceFile(fileId: number | string) {
    return http.get(`/upload/${fileId}/download/`, { responseType: 'blob' })
  },

  downloadTaskReport(taskId: number | string) {
    return http.get(`/admin/tasks/${taskId}/report/`, { responseType: 'blob' })
  },

  deleteTask(taskId: number) {
    return http.delete(`/detection-task-delete/${taskId}/`)
  },
}
