import http from './request'

export default {
  getReviewers(params: { publisher_id: string | number }) {
    return http.get(`publishers/${params.publisher_id}/reviewers/`)
  },

  getPublisherReviewTasks(params: {
    page?: number
    page_size?: number
    status?: string
    startTime?: string
    endTime?: string
  }) {
    return http.get('/get_publisher_review_tasks/', { params })
  },

  getReviewRequestDetail(params: { review_request_id: string | number }) {
    return http.get(`/get_request_detail/${params.review_request_id}/`)
  },

  getImageReviewAll(params: { review_request_id: string | number; img_id: string | number }) {
    return http.get(`/get_img_review_all/?review_request_id=${params.review_request_id}&img_id=${params.img_id}`)
  },

  getImageReviewDetail(params: {
    review_request_id: string | number
    img_id: string | number
    reviewer_id: string | number
  }) {
    return http.get(`/get_image_review/?review_request_id=${params.review_request_id}&img_id=${params.img_id}&reviewer_id=${params.reviewer_id}`)
  },

  getDetectionId(params: { img_id: string | number }) {
    return http.get(`/tasks_image/${params.img_id}/getdr/`)
  },

  downloadReviewReport(params: { review_request_id: string | number }) {
    return http.get(`/manual-review/${params.review_request_id}/report/`, {
      responseType: 'blob',
    })
  },
}
