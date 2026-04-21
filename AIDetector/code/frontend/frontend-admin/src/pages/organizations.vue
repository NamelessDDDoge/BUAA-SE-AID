<template>
  <v-container fluid class="organizations-page">
    <!-- 标题和操作按钮 -->
    <v-row class="mb-6">
      <v-col>
        <h1 class="text-h4 font-weight-bold">组织管理</h1>
      </v-col>
    </v-row>

    <!-- 搜索和筛选区域 -->
    <v-row class="mb-4 align-center">
      <v-col cols="12" sm="8" md="6">
        <v-text-field v-model="searchQuery" label="搜索组织名称" append-inner-icon="mdi-magnify" clearable density="compact"
          hide-details class="search-input" @keyup.enter="handleSearch" @click:append-inner="handleSearch"
          @click:clear="handleSearch" placeholder="请输入组织名称"></v-text-field>
      </v-col>
      <v-col cols="12" sm="4" md="auto" class="d-flex justify-end">
        <v-btn color="secondary" size="large" prepend-icon="mdi-plus" @click="showCreateOrgDialog = true"
          class="create-btn">
          创建组织
        </v-btn>
      </v-col>
    </v-row>

    <!-- 组织列表 -->
    <v-row>
      <v-col cols="12">
        <v-card class="list-card" elevation="2">
          <v-tabs v-model="activeTab" color="primary" class="tabs-header" height="60">
            <v-tab value="existing" class="text-h6">
              现有组织
            </v-tab>
            <v-tab value="pending" class="text-h6">
              待审核组织
            </v-tab>
          </v-tabs>

          <v-card-text class="pa-6">
            <v-window v-model="activeTab">
              <!-- 现有组织列表 -->
              <v-window-item value="existing">
                <v-data-table :headers="headers" :items="organizations" :loading="loading"
                  class="elevation-1 rounded-lg" hover :items-per-page="pageSize" hide-default-footer>
                  <template v-slot:top>
                    <div class="d-flex align-center pa-4">
                      <div class="text-caption text-medium-emphasis">
                        共 {{ totalOrganizations }} 条记录
                      </div>
                    </div>
                  </template>

                  <template v-slot:item.logo="{ item }">
                    <v-avatar size="40">
                      <v-img :src="getImgUrl(item.logo)" :alt="item.name"></v-img>
                    </v-avatar>
                  </template>

                  <template v-slot:item.actions="{ item }">
                    <v-btn icon="mdi-eye" size="small" color="info" class="me-2 action-btn" variant="tonal"
                      @click="showDetails(item)"></v-btn>
                    <v-btn icon="mdi-delete" size="small" color="error" class="action-btn" variant="tonal"
                      @click="showDeleteConfirm(item)"></v-btn>
                  </template>
                </v-data-table>

                <div class="d-flex align-center justify-center pa-4">
                  <div class="d-flex align-center">
                    <span class="text-caption mr-2">每页显示</span>
                    <v-select v-model="pageSize" :items="[5, 10, 20, 50, 100]" density="compact" variant="outlined"
                      hide-details style="width: 100px" @update:model-value="handleItemsPerPageChange"></v-select>
                    <span class="text-caption ml-2">条</span>
                  </div>
                  <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" class="ml-4"
                    @update:model-value="handlePageChange"></v-pagination>
                </div>
              </v-window-item>

              <!-- 待审核组织列表 -->
              <v-window-item value="pending">
                <v-data-table :headers="pendingHeaders" :items="pendingOrganizations" :loading="loading"
                  class="elevation-1 rounded-lg" hover :items-per-page="pageSize" hide-default-footer>
                  <template v-slot:top>
                    <div class="d-flex align-center pa-4">
                      <div class="text-caption text-medium-emphasis">
                        共 {{ totalPendingOrganizations }} 条记录
                      </div>
                    </div>
                  </template>

                  <template v-slot:item.actions="{ item }">
                    <v-btn icon="mdi-eye" size="small" color="info" class="me-2 action-btn" variant="tonal"
                      @click="showDetails(item)"></v-btn>
                    <v-btn color="success" size="small" class="me-2 action-btn" variant="tonal"
                      @click="approveOrganization(item.id)">
                      通过
                    </v-btn>
                    <v-btn color="error" size="small" class="action-btn" variant="tonal"
                      @click="rejectOrganization(item.id)">
                      拒绝
                    </v-btn>
                  </template>
                </v-data-table>

                <div class="d-flex align-center justify-center pa-4">
                  <div class="d-flex align-center">
                    <span class="text-caption mr-2">每页显示</span>
                    <v-select v-model="pageSize" :items="[5, 10, 20, 50, 100]" density="compact" variant="outlined"
                      hide-details style="width: 100px" @update:model-value="handleItemsPerPageChange"></v-select>
                    <span class="text-caption ml-2">条</span>
                  </div>
                  <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" class="ml-4"
                    @update:model-value="handlePageChange"></v-pagination>
                </div>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 组织详情对话框 -->
    <v-dialog v-model="detailsDialog" max-width="800px" transition="dialog-bottom-transition">
      <v-card class="dialog-card" v-if="selectedItem">
        <v-card-title class="d-flex justify-space-between align-center pa-4">
          <div class="d-flex align-center">
            <v-icon size="24" color="primary" class="me-2">mdi-eye</v-icon>
            <span class="text-h5">组织详情</span>
          </div>
          <v-btn icon @click="detailsDialog = false" variant="tonal">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-6">
          <v-container>
            <v-row>
              <v-col cols="12" class="d-flex justify-center">
                <v-avatar size="200" class="mb-6 organization-logo">
                  <v-img :src="getImgUrl(selectedItem.logo)" alt="组织Logo"></v-img>
                </v-avatar>
              </v-col>
              <v-col cols="12">
                <v-list class="rounded-lg pa-4 bg-grey-lighten-4">
                  <v-list-item class="mb-2">
                    <template v-slot:prepend>
                      <v-icon color="primary" size="24">mdi-office-building</v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-1 font-weight-bold">组织名称</v-list-item-title>
                    <v-list-item-subtitle class="text-body-1 mt-1">{{ selectedItem.name }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-divider class="my-2"></v-divider>

                  <v-list-item class="mb-2">
                    <template v-slot:prepend>
                      <v-icon color="primary" size="24">mdi-text-box</v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-1 font-weight-bold">组织描述</v-list-item-title>
                    <v-list-item-subtitle class="text-body-1 mt-1">{{ selectedItem.description || '暂无描述'
                    }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-divider class="my-2"></v-divider>

                  <v-list-item class="mb-2">
                    <template v-slot:prepend>
                      <v-icon color="primary" size="24">mdi-text-box</v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-1 font-weight-bold">管理员邮箱</v-list-item-title>
                    <v-list-item-subtitle class="text-body-1 mt-1">{{ selectedItem.email
                    }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-divider class="my-2"></v-divider>

                  <v-list-item class="mb-2">
                    <template v-slot:prepend>
                      <v-icon color="primary" size="24">mdi-calendar</v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-1 font-weight-bold">注册时间</v-list-item-title>
                    <v-list-item-subtitle class="text-body-1 mt-1">{{ formatTime(selectedItem.created_at)
                    }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-divider class="my-2" v-if="selectedItem.user_count"></v-divider>

                  <v-list-item class="mb-2" v-if="selectedItem.user_count">
                    <template v-slot:prepend>
                      <v-icon color="primary" size="24">mdi-account-group</v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-1 font-weight-bold">用户数量</v-list-item-title>
                    <v-list-item-subtitle class="text-body-1 mt-1">{{ selectedItem.user_count }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-divider class="my-2" v-if="selectedItem.image_count"></v-divider>

                  <v-list-item class="mb-2" v-if="selectedItem.image_count">
                    <template v-slot:prepend>
                      <v-icon color="primary" size="24">mdi-image-multiple</v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-1 font-weight-bold">图像数量</v-list-item-title>
                    <v-list-item-subtitle class="text-body-1 mt-1">{{ selectedItem.image_count }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>

              <v-col cols="12" v-if="selectedItem.proof_materials">
                <v-card class="mt-6 documents-card" elevation="2">
                  <v-card-title class="d-flex align-center pa-4">
                    <v-icon color="primary" size="24" class="me-2">mdi-file-document</v-icon>
                    <span class="text-h6">证明材料</span>
                  </v-card-title>
                  <v-card-text class="pa-4">
                    <v-btn color="primary" prepend-icon="mdi-download"
                      @click="downloadProofMaterials(selectedItem.proof_materials)">
                      下载证明材料
                    </v-btn>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- 创建组织对话框 -->
    <v-dialog v-model="showCreateOrgDialog" max-width="700" persistent>
      <v-card class="create-org-dialog">
        <v-card-title class="d-flex align-center pa-6">
          <v-icon size="32" color="primary" class="mr-3">mdi-office-building</v-icon>
          <span class="text-h5">创建组织</span>
        </v-card-title>

        <v-card-text class="pa-6">
          <v-form ref="orgForm" @submit.prevent="handleCreateOrg">
            <!-- 组织信息部分 -->
            <div class="form-section mb-8">
              <div class="section-header d-flex align-center mb-4">
                <v-icon color="primary" class="mr-2">mdi-domain</v-icon>
                <span class="text-h6">组织信息</span>
              </div>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.name" label="组织名称" variant="outlined" density="comfortable"
                    :rules="orgRules.name" prepend-inner-icon="mdi-tag"></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.adminUsername" label="管理员用户名" variant="outlined"
                    density="comfortable" :rules="orgRules.adminUsername"
                    prepend-inner-icon="mdi-account"></v-text-field>
                </v-col>
              </v-row>

              <v-textarea v-model="orgFormData.description" label="组织描述" variant="outlined" density="comfortable"
                :rules="orgRules.description" rows="3" prepend-inner-icon="mdi-text-box"></v-textarea>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.adminEmail" label="管理员邮箱" variant="outlined" density="comfortable"
                    :rules="orgRules.adminEmail" prepend-inner-icon="mdi-email"></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.adminPassword" label="管理员密码" type="password" variant="outlined"
                    density="comfortable" :rules="orgRules.adminPassword" prepend-inner-icon="mdi-lock"></v-text-field>
                </v-col>
              </v-row>

              <v-text-field v-model="orgFormData.adminConfirmPassword" label="确认管理员密码" type="password"
                variant="outlined" density="comfortable" :rules="orgRules.adminConfirmPassword"
                prepend-inner-icon="mdi-lock-check"></v-text-field>
            </div>

            <!-- 文件上传部分 -->
            <div class="form-section">
              <div class="section-header d-flex align-center mb-4">
                <v-icon color="primary" class="mr-2">mdi-file-upload</v-icon>
                <span class="text-h6">文件上传</span>
              </div>

              <v-row>
                <v-col cols="12" md="6">
                  <div class="upload-section pa-4 rounded-lg">
                    <div class="text-subtitle-2 mb-2">组织Logo</div>
                    <v-file-input v-model="orgFormData.logo" accept="image/*" label="上传Logo" variant="outlined"
                      density="comfortable" prepend-icon="mdi-camera" :rules="orgRules.logo" @change="handleLogoChange"
                      class="mb-2"></v-file-input>
                    <v-img v-if="orgFormData.logoPreview" :src="orgFormData.logoPreview" max-height="150"
                      class="rounded-lg" contain></v-img>
                  </div>
                </v-col>

                <v-col cols="12" md="6">
                  <div class="upload-section pa-4 rounded-lg">
                    <div class="text-subtitle-2 mb-2">证明材料</div>
                    <v-file-input v-model="orgFormData.certificate" accept=".pdf,.jpg,.jpeg,.png" label="上传证明材料"
                      variant="outlined" density="comfortable" prepend-icon="mdi-file-document"
                      :rules="orgRules.certificate"></v-file-input>
                  </div>
                </v-col>
              </v-row>
            </div>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-6">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeCreateOrgDialog" class="mr-2">
            取消
          </v-btn>
          <v-btn color="primary" variant="elevated" @click="handleCreateOrg" :loading="creatingOrg"
            :disabled="!isOrgFormValid">
            <v-icon start>mdi-check</v-icon>
            创建组织
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400px" transition="dialog-bottom-transition">
      <v-card class="dialog-card">
        <v-card-title class="d-flex justify-space-between align-center pa-4">
          <div class="d-flex align-center">
            <v-icon size="24" color="error" class="me-2">mdi-alert</v-icon>
            <span class="text-h5">确认删除</span>
          </div>
          <v-btn icon @click="showDeleteDialog = false" variant="tonal">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-6">
          <p class="text-body-1">
            确定要删除组织 "{{ selectedItem?.name }}" 吗？此操作不可撤销。
          </p>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn color="grey-darken-1" variant="tonal" @click="showDeleteDialog = false">
            取消
          </v-btn>
          <v-btn color="error" variant="tonal" @click="confirmDelete" :loading="loading">
            确认删除
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useSnackbarStore } from '@/stores/snackbar'
import organization from '@/api/organization'
import type { DataTableHeader } from 'vuetify'
import { useUserStore } from '@/stores/user'

const snackbar = useSnackbarStore()

// 表格头部配置
const headers = computed<DataTableHeader[]>(() => [
  { title: 'Logo', key: 'logo', align: 'center', sortable: false, width: '80px' },
  { title: '组织名称', key: 'name', align: 'start', width: '120px' },
  { title: '用户数量', key: 'user_count', align: 'center', width: '100px' },
  { title: '图像数量', key: 'image_count', align: 'center', width: '100px' },
  { title: '操作', key: 'actions', align: 'center', sortable: false, width: '120px' }
] as const)

const pendingHeaders = computed<DataTableHeader[]>(() => [
  { title: '组织名称', key: 'name', align: 'start', width: '120px' },
  { title: '管理员名', key: 'admin_username', align: 'start', width: '120px' },
  { title: '管理员邮箱', key: 'admin_email', align: 'start', width: '180px' },
  { title: '提交时间', key: 'submitted_at', align: 'center', width: '160px' },
  { title: '操作', key: 'actions', align: 'center', sortable: false, width: '180px' }
] as const)

// 类型定义
interface Organization {
  id: number
  name: string
  description: string
  logo?: string
  proof_materials?: string
  email:string
  created_at:string
  user_count: number
  image_count: number
}

interface PendingOrganization {
  id: number
  name: string
  email: string
  admin_username: string
  admin_email: string
  submitted_at: string
}

// 状态变量
const activeTab = ref('existing')
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalOrganizations = ref(0)
const totalPendingOrganizations = ref(0)
const totalPages = ref(1)
const showDeleteDialog = ref(false)
const detailsDialog = ref(false)
const selectedItem = ref<Organization | null>(null)
const organizations = ref<Organization[]>([])
const pendingOrganizations = ref<PendingOrganization[]>([])
const admin_type = ref<string>('')
const showCreateOrgDialog = ref(false)
const creatingOrg = ref(false)

const orgFormData = ref({
  name: '',
  description: '',
  logo: null as File | null,
  logoPreview: '',
  certificate: null as File | null,
  adminUsername: '',
  adminEmail: '',
  adminPassword: '',
  adminConfirmPassword: ''
})

const orgRules = {
  name: [
    (v: string) => !!v || '组织名称不能为空',
    (v: string) => v.length >= 2 || '组织名称至少2个字符'
  ],
  description: [
    (v: string) => !!v || '组织描述不能为空',
    (v: string) => v.length >= 10 || '组织描述至少10个字符'
  ],
  logo: [
    (v: File | null) => !!v || '请上传组织Logo',
    (v: File | null) => !v || v.size <= 5 * 1024 * 1024 || 'Logo大小不能超过5MB'
  ],
  certificate: [
    (v: File | null) => !!v || '请上传证明材料',
    (v: File | null) => !v || v.size <= 10 * 1024 * 1024 || '文件大小不能超过10MB'
  ],
  email: [
    (v: string) => !!v || '组织邮箱不能为空',
    (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
  ],
  adminUsername: [
    (v: string) => !!v || '管理员用户名不能为空',
    (v: string) => v.length >= 2 || '用户名至少2个字符'
  ],
  adminEmail: [
    (v: string) => !!v || '管理员邮箱不能为空',
    (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
  ],
  adminPassword: [
    (v: string) => !!v || '管理员密码不能为空',
    (v: string) => v.length >= 6 || '密码至少6个字符'
  ],
  adminConfirmPassword: [
    (v: string) => !!v || '请确认管理员密码',
    (v: string) => v === orgFormData.value.adminPassword || '两次输入的密码不一致'
  ]
}

const formatTime = (data: string) => {
  const timestamp = new Date(data).getTime()
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}


const getImgUrl = (logo: any) => {
  return import.meta.env.VITE_API_URL + logo
}

// 获取组织列表
const fetchOrganizations = async () => {
  try {
    loading.value = true
    const response = await organization.getOrgList({
      page: currentPage.value,
      page_size: pageSize.value,
      query: searchQuery.value
    })
    organizations.value = response.data.organizations
    totalOrganizations.value = response.data.total_organizations
    totalPages.value = response.data.total_pages
    currentPage.value = response.data.current_page
  } catch (error) {
    snackbar.showMessage('获取组织列表失败', 'error')
  } finally {
    loading.value = false
  }
}

// 获取待审核组织列表
const fetchPendingOrganizations = async () => {
  try {
    loading.value = true
    const response = await organization.getPendingOrgList({
      page: currentPage.value,
      page_size: pageSize.value,
      query: searchQuery.value
    })
    pendingOrganizations.value = response.data.applications
    totalPendingOrganizations.value = response.data.total_count
    totalPages.value = response.data.total_pages
    currentPage.value = response.data.current_page
  } catch (error) {
    snackbar.showMessage('获取待审核组织列表失败', 'error')
  } finally {
    loading.value = false
  }
}

// 显示组织详情
const showDetails = async (item: Organization | PendingOrganization) => {
  try {
    if ('user_count' in item) {
      // 现有组织
      const response = await organization.getOrgDetail({ organization_id: item.id })
      selectedItem.value = response.data
    } else {
      // 待审核组织，调用新接口获取详情
      const response = await organization.getPendingApplicationDetail(item.id)
        selectedItem.value = 
        {
          ...response.data,
          created_at:response.data.submitted_at,
        }
    }
    detailsDialog.value = true
  } catch (error) {
    snackbar.showMessage('获取组织详情失败', 'error')
  }
}

// 删除组织
const deleteOrganization = async (id: number) => {
  try {
    await organization.deleteOrg({ organization_id: id })
    snackbar.showMessage('删除成功', 'success')
    await fetchOrganizations()
  } catch (error) {
    snackbar.showMessage('删除失败', 'error')
  }
}

// 审核通过组织
const approveOrganization = async (id: number) => {
  try {
    await organization.approveOrg({ organization_id: id })
    snackbar.showMessage('审核通过成功', 'success')
    await fetchPendingOrganizations()
  } catch (error) {
    snackbar.showMessage('审核通过失败', 'error')
  }
}

// 拒绝组织申请
const rejectOrganization = async (id: number) => {
  try {
    await organization.rejectOrg({ organization_id: id })
    snackbar.showMessage('已拒绝申请', 'success')
    await fetchPendingOrganizations()
  } catch (error) {
    snackbar.showMessage('操作失败', 'error')
  }
}

// 处理Logo预览
const handleLogoChange = (file: File | null) => {
  if (file && file instanceof File) {
    try {
      const reader = new FileReader()
      reader.onload = (e) => {
        if (e.target?.result) {
          orgFormData.value.logoPreview = e.target.result as string
        }
      }
      reader.onerror = () => {
        console.error('读取文件失败')
        orgFormData.value.logoPreview = ''
        snackbar.showMessage('读取文件失败，请重试', 'error')
      }
      reader.readAsDataURL(file)
    } catch (error) {
      console.error('处理文件时出错:', error)
      orgFormData.value.logoPreview = ''
      snackbar.showMessage('处理文件时出错，请重试', 'error')
    }
  } else {
    orgFormData.value.logoPreview = ''
  }
}

// 组织表单验证
const isOrgFormValid = computed(() => {
  // 检查所有必填字段是否都已填写
  const hasName = orgFormData.value.name && orgFormData.value.name.length >= 2
  const hasDescription = orgFormData.value.description && orgFormData.value.description.length >= 10
  const hasLogo = orgFormData.value.logo !== null
  const hasCertificate = orgFormData.value.certificate !== null
  const hasAdminUsername = orgFormData.value.adminUsername && orgFormData.value.adminUsername.length >= 2
  const hasAdminEmail = orgFormData.value.adminEmail && /.+@.+\..+/.test(orgFormData.value.adminEmail)
  const hasAdminPassword = orgFormData.value.adminPassword && orgFormData.value.adminPassword.length >= 6
  const hasAdminConfirmPassword = orgFormData.value.adminConfirmPassword === orgFormData.value.adminPassword

  // 所有字段都必须填写且符合验证规则
  return hasName && hasDescription && hasLogo && hasCertificate &&
    hasAdminUsername && hasAdminEmail && hasAdminPassword && hasAdminConfirmPassword
})

//创建组织
const handleCreateOrg = async () => {
  if (!isOrgFormValid.value) return

  try {
    creatingOrg.value = true
    const formData = new FormData()
    formData.append('org_name', orgFormData.value.name)
    formData.append('description', orgFormData.value.description)
    if (orgFormData.value.logo) {
      formData.append('logo', orgFormData.value.logo)
    }
    if (orgFormData.value.certificate) {
      formData.append('proof_materials', orgFormData.value.certificate)
    }
    formData.append('email', orgFormData.value.adminEmail)
    formData.append('admin_username', orgFormData.value.adminUsername)
    formData.append('admin_email', orgFormData.value.adminEmail)
    formData.append('admin_password', orgFormData.value.adminPassword)

    await organization.createOrganization(formData)

    snackbar.showMessage('组织创建成功', 'success')
    closeCreateOrgDialog()
  } catch (error: any) {
    console.error('创建组织失败:', error)
    const errorMsg = error.response?.data?.message || '创建组织失败'
    snackbar.showMessage(errorMsg, 'error')
  } finally {
    creatingOrg.value = false
  }
}


// 关闭创建组织对话框
const closeCreateOrgDialog = () => {
  showCreateOrgDialog.value = false
  // 重置表单
  setTimeout(() => {
    orgFormData.value = {
      name: '',
      description: '',
      logo: null,
      logoPreview: '',
      certificate: null,
      adminUsername: '',
      adminEmail: '',
      adminPassword: '',
      adminConfirmPassword: ''
    }
  }, 300)
}



// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  if (activeTab.value === 'existing') {
    fetchOrganizations()
  } else {
    fetchPendingOrganizations()
  }
}

// 分页处理
const handlePageChange = (page: number) => {
  currentPage.value = page
  if (activeTab.value === 'existing') {
    fetchOrganizations()
  } else {
    fetchPendingOrganizations()
  }
}

const handleItemsPerPageChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  if (activeTab.value === 'existing') {
    fetchOrganizations()
  } else {
    fetchPendingOrganizations()
  }
}

// 监听标签页切换
watch(activeTab, (newValue) => {
  currentPage.value = 1
  if (newValue === 'existing') {
    fetchOrganizations()
  } else {
    fetchPendingOrganizations()
  }
})

// 确认删除
const confirmDelete = async () => {
  if (selectedItem.value) {
    try {
      await deleteOrganization(selectedItem.value.id)
      showDeleteDialog.value = false
    } catch (error) {
      snackbar.showMessage('删除失败', 'error')
    }
  }
}

// 显示删除确认对话框
const showDeleteConfirm = (item: Organization) => {
  selectedItem.value = item
  showDeleteDialog.value = true
}

// 监听搜索查询变化
watch(searchQuery, () => {
  currentPage.value = 1
  if (activeTab.value === 'existing') {
    fetchOrganizations()
  } else {
    fetchPendingOrganizations()
  }
})

// 下载证明材料
const downloadProofMaterials = (url: string) => {
  if (!url) return
  const link = document.createElement('a')
  link.href = getImgUrl(url)
  link.download = '证明材料'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const fetchAdmin = () => {
  const userStore = useUserStore()
  admin_type.value = userStore.admin_type
}

// 初始化
onMounted(() => {
  fetchOrganizations()
  fetchAdmin()
})
</script>

<style scoped>
.organizations-page {
  background-color: rgb(var(--v-theme-background));
  min-height: 100vh;
}

.list-card {
  border-radius: 12px;
  overflow: hidden;
}

.tabs-header {
  background-color: rgb(var(--v-theme-surface));
}

.action-btn {
  transition: transform 0.2s;
}

.action-btn:hover {
  transform: scale(1.1);
}

.dialog-card {
  border-radius: 12px;
}

.organization-logo {
  border: 4px solid rgb(var(--v-theme-primary));
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.documents-card {
  border-radius: 12px;
}

:deep(.v-data-table) {
  border-radius: 8px;
}

:deep(.v-data-table-header) {
  background-color: rgb(var(--v-theme-surface-variant));
}

:deep(.v-data-table-row) {
  transition: background-color 0.2s;
}

:deep(.v-data-table-row:hover) {
  background-color: rgb(var(--v-theme-surface-variant));
}

:deep(.v-tab) {
  text-transform: none;
  letter-spacing: normal;
}

:deep(.v-btn) {
  text-transform: none;
  letter-spacing: normal;
}

.search-input {
  width: 100%;
}

:deep(.v-text-field .v-field__input) {
  min-height: 40px;
}

:deep(.v-btn--variant-outlined) {
  border-color: rgb(var(--v-theme-outline));
}

:deep(.v-select .v-field__input) {
  min-height: 40px;
}

:deep(.v-select .v-field__append-inner) {
  padding-top: 0;
}

.create-btn {
  min-width: 140px;
  white-space: nowrap;
}
</style>