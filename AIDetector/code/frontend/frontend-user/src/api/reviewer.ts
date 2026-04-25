import http from './request'

export default {
  submitReview(manual_review_id: number, data: any, requestType: 'image' | 'resource' = 'image') {
    return http.post(`/post_review/${manual_review_id}/`, {
      ...data,
      request_type: requestType,
    })
  },
  getReviewerTasks(params: any) {
    return http.get('/get_reviewer_tasks/', { params })
  },
  getReviewRequest(params: any) {
    return http.get('/get_publisher_review_tasks/', { params })
  },

  getReviewTaskDetail(data: { manual_review_id: number | string; request_type?: 'image' | 'resource' }) {
    return http.get(`/get_review_request_detail/${data.manual_review_id}/`, {
      params: { request_type: data.request_type || 'image' },
    })
  },

  getMaskImage(data: any) {
    return http.get(`/results_image/${data.img_id}/`)
  },

  getTaskCount() {
    return http.get('/reviewer/tasks/')
  },

  getRecentActivities() {
    return http.get('/reviewer/activity_logs/')
  },

  getDetectionResult(data: any) {
    return http.get(`tasks_image/${data.img_id}/report/`)
  }

}