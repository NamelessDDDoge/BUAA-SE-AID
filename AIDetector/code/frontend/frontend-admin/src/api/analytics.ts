import http from './request'

export default {
  // 获取图像标签统计
  getImgTag: (params: { startTime?: string; endTime?: string }) => {
    return http.get('/dashboard/img_tag/', { params })
  },
  getTopPublishers: () => {
    return http.get('/dashboard/top_publishers/')
  },
  getTopOrganizations: () => {
    return http.get('/dashboard/top_organizations/')
  },
  getDailyTaskCount: () => {
    return http.get('/dashboard/daily_task_count/')
  },
  getDailyReviewRequestCount: () => {
    return http.get('/dashboard/daily_review_request_count/')
  },
  getDailyCompletedManualReviewCount: () => {
    return http.get('/dashboard/daily_completed_manual_review_count/')
  },
  getDailyActiveUsers: () => {
    return http.get('/dashboard/daily_active_users/')
  },
  getDailyActiveOrganizations: () => {
    return http.get('/dashboard/daily_active_organizations/')
  },
  getDetectionMethodStats: () => {
    return http.get('/dashboard/get_sub_method_distribution_by_tag/')
  }
}