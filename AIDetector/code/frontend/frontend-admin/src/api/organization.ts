import http from './request'

export default {
  // 获取组织信息
  getOrgDetail(data: any) {
    return http.get(`/organization/${data.organization_id}/`)
  },

  // 上传组织Logo
  uploadLogo(data: FormData) {
    return http.post('/organization/upload_logo/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  createOrganization(data: any) {
    return http.post('organizations/create-directly/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 获取组织列表
  getOrgList(params: any) {
    return http.get('/organizations/', { params })
  },

  // 获取待审核组织列表
  getPendingOrgList(params: any) {
    return http.get('/organization/applications/get_pending/', { params })
  },

  // 删除组织
  deleteOrg(data: { organization_id: number }) {
    return http.delete(`/organization/${data.organization_id}/delete/`)
  },

  // 审核通过组织
  approveOrg(data: { organization_id: number }) {
    return http.post(`/organization/${data.organization_id}/approve/`)
  },

  // 拒绝组织申请
  rejectOrg(data: { organization_id: number }) {
    return http.post(`/organization/${data.organization_id}/reject/`)
  },

  // 获取组织使用次数
  getOrgUsage() {
    return http.get('/organization/usage/')
  },

  // 充值使用次数
  rechargeUses(data: { amount: number; choice: 'non-llm' | 'llm' }) {
    return http.post('/organization/recharge-uses/', data)
  },

  // 获取待审核组织详情
  getPendingApplicationDetail(app_id: number) {
    return http.get(`/organization/applications/${app_id}/`)
  }
} 