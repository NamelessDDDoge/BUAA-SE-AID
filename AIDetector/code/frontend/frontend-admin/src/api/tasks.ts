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
}
