<template>
  <v-container>
    <!-- 标题 -->
    <v-row class="mb-6">
      <v-col>
        <h1 class="text-h4 font-weight-bold">用户管理</h1>
      </v-col>
    </v-row>

    <!-- 搜索和筛选区域 -->
    <v-row class="mb-4 align-center">
      <v-col cols="12" sm="8" md="6">
        <v-text-field v-model="searchQuery" label="搜索用户名" append-inner-icon="mdi-magnify" clearable density="compact"
          hide-details class="search-input" @keyup.enter="handleSearch" @click:append-inner="handleSearch"
          @click:clear="handleSearch" placeholder="请输入用户名"></v-text-field>
      </v-col>
      <v-col v-if="currentUser?.admin_type === 'software_admin'" cols="12" sm="4" md="3">
        <v-text-field v-model="organizationQuery" label="搜索组织" append-inner-icon="mdi-magnify" clearable
          density="compact" hide-details class="search-input" @keyup.enter="handleSearch"
          @click:append-inner="handleSearch" @click:clear="handleSearch" placeholder="请输入组织名称"></v-text-field>
      </v-col>
      <!-- spacer 自动填充空位 -->
      <v-spacer></v-spacer>

      <!-- 筛选按钮，始终靠右 -->
      <v-col cols="auto">
        <v-btn color="primary" class="text-none mr-2" prepend-icon="mdi-filter-variant"
          @click="showFilterDialog = true">
          筛选
        </v-btn>
        <!-- <v-btn v-if="currentUser && currentUser.email === 'admin@mail.com'" color="success" class="text-none"
          prepend-icon="mdi-account-plus" @click="showCreateAdminDialog = true">
          创建管理员
        </v-btn> -->
        <v-btn v-if="currentUser?.admin_type === 'organization_admin'" color="primary" class="text-none ml-2"
          prepend-icon="mdi-account-plus" @click="handleAddExpert">
          添加组织内用户
        </v-btn>
      </v-col>
    </v-row>

    <v-card class="elevation-2">
      <v-data-table :headers="headers" :items="users" class="elevation-0" :items-per-page="pageSize" hover
        :width="'100%'" :loading="loading" hide-default-footer>
        <template v-slot:top>
          <div class="d-flex align-center pa-4">
            <div class="text-caption text-medium-emphasis">
              共 {{ totalUsers }} 条记录
            </div>
          </div>
        </template>
        <template v-slot:item.avatar="{ item }">
          <v-avatar size="40">
            <v-img :src="item.avatar || 'https://randomuser.me/api/portraits/lego/1.jpg'" :alt="item.username"></v-img>
          </v-avatar>
        </template>

        <template v-slot:item.email="{ item }">
          <span>{{ item.email }}</span>
        </template>

        <template v-slot:item.role="{ item }">
          <v-chip v-if="item.email === ROOT_ADMIN_EMAIL" color="purple" size="small" class="role-chip">
            软件管理员
          </v-chip>
          <v-chip v-else-if="item.role === 'admin'" :color="item.admin_type === 'software_admin' ? 'error' : 'warning'"
            size="small" class="role-chip">
            {{ item.admin_type === 'software_admin' ? '软件管理员' : '组织管理员' }}
          </v-chip>
          <v-chip v-else :color="getRoleColor(item.role)" size="small" class="role-chip">
            {{ getRoleName(item.role) }}
          </v-chip>
        </template>

        <template v-slot:item.permission="{ item }">
          <div class="d-flex flex-column align-center">
            <v-chip v-if="item.role === 'admin' || item.email === ROOT_ADMIN_EMAIL" size="x-small" color="error"
              class="mb-1">
              管理员权限
            </v-chip>
            <template v-else>
              <div class="d-flex flex-wrap justify-center gap-2">
                <div class="d-flex align-center">
                  <v-icon :color="getPermissionBit(item.permission, 3) ? 'info' : 'error'" size="small" class="mr-1">
                    {{ getPermissionBit(item.permission, 3) ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                  <span class="text-caption">上传图像</span>
                </div>
                <div class="d-flex align-center">
                  <v-icon :color="getPermissionBit(item.permission, 2) ? 'success' : 'error'" size="small" class="mr-1">
                    {{ getPermissionBit(item.permission, 2) ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                  <span class="text-caption">提交AI检测</span>
                </div>
                <div class="d-flex align-center">
                  <v-icon :color="getPermissionBit(item.permission, 1) ? 'warning' : 'error'" size="small" class="mr-1">
                    {{ getPermissionBit(item.permission, 1) ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                  <span class="text-caption">发布人工审核</span>
                </div>
                <div class="d-flex align-center">
                  <v-icon :color="getPermissionBit(item.permission, 0) ? 'primary' : 'error'" size="small" class="mr-1">
                    {{ getPermissionBit(item.permission, 0) ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                  <span class="text-caption">提交人工审核</span>
                </div>
              </div>
            </template>
          </div>
        </template>

        <template v-slot:item.organization="{ item }">
          <span>{{ item.organization }}</span>
        </template>

        <template v-slot:item.registerTime="{ item }">
          {{ formatTime(item.registerTime) }}
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn icon variant="text" size="small" color="info" class="mr-2" @click="openUserDetailsDialog(item)">
            <v-icon>mdi-eye</v-icon>
          </v-btn>
          <v-btn icon variant="text" size="small" color="primary" class="mr-2" @click="openPermissionDialog(item)">
            <v-icon>mdi-key-variant</v-icon>
          </v-btn>
          <v-btn icon variant="text" size="small" color="error" @click="openDeleteDialog(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>

      <div class="d-flex align-center justify-center pa-4">
        <div class="d-flex align-center">
          <span class="text-caption mr-2">每页显示</span>
          <v-select v-model="pageSize" :items="[5, 10, 20, 50, 100]" density="compact" variant="outlined" hide-details
            style="width: 100px" @update:model-value="handlePageSizeChange"></v-select>
          <span class="text-caption ml-2">条</span>
        </div>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" class="ml-4"
          @update:model-value="handlePageChange"></v-pagination>
      </div>
    </v-card>

    <!-- 权限设置对话框 -->
    <v-dialog v-model="showPermissionDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">修改权限</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <!-- 出版社权限 -->
            <template v-if="selectedUser?.role === 'publisher'">
              <v-switch v-model="editingPermissions.uploadImage" label="上传图像权限" color="info" hide-details></v-switch>
              <v-switch v-model="editingPermissions.submitAI" label="提交AI检测权限" color="success" hide-details></v-switch>
              <v-switch v-model="editingPermissions.publishReview" label="发布人工审核权限" color="warning"
                hide-details></v-switch>
            </template>
            <!-- 审稿人权限 -->
            <template v-else-if="selectedUser?.role === 'reviewer'">
              <v-switch v-model="editingPermissions.submitReview" label="提交人工审核权限" color="primary"
                hide-details></v-switch>
            </template>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showPermissionDialog = false">取消</v-btn>
          <v-btn color="primary" @click="updatePermissions">确认</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">确认删除</v-card-title>
        <v-card-text>
          确定要删除用户 "{{ selectedUser?.username }}" 吗？此操作不可撤销。
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" @click="deleteUser">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 筛选对话框 -->
    <v-dialog v-model="showFilterDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <v-select v-model="filters.role" :items="roleOptions" label="角色" clearable hide-details></v-select>

            <div class="d-flex flex-column gap-2">
              <div class="text-subtitle-2">权限筛选</div>
              <v-switch v-model="filters.enablePermissionFilter" label="启用权限筛选" color="info" hide-details></v-switch>
              <template v-if="filters.enablePermissionFilter">
                <v-switch v-model="filters.permissions.uploadImage" label="上传图像权限" color="info" hide-details></v-switch>
                <v-switch v-model="filters.permissions.submitAI" label="提交AI检测权限" color="success"
                  hide-details></v-switch>
                <v-switch v-model="filters.permissions.publishReview" label="发布人工审核权限" color="warning"
                  hide-details></v-switch>
                <v-switch v-model="filters.permissions.submitReview" label="提交人工审核权限" color="primary"
                  hide-details></v-switch>
              </template>
            </div>

            <v-select v-model="filters.timeRange" :items="timeRangeOptions" label="快速选择时间范围" clearable hide-details
              @update:model-value="handleTimeRangeChange"></v-select>

            <div class="d-flex align-center gap-4">
              <v-text-field v-model="filters.startDate" label="开始时间" type="datetime-local" hide-details
                density="compact" :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"></v-text-field>
              <v-text-field v-model="filters.endDate" label="结束时间" type="datetime-local" hide-details density="compact"
                :error-messages="timeError" @update:model-value="handleCustomTimeChange"></v-text-field>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="resetFilters">重置</v-btn>
          <v-btn color="primary" @click="applyFilters">应用</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 创建管理员对话框 -->
    <v-dialog v-if="currentUser && currentUser.email === 'admin@mail.com'" v-model="showCreateAdminDialog"
      max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">创建管理员</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <v-text-field v-model="newAdmin.username" label="用户名" :rules="[v => !!v || '用户名不能为空']"
              required></v-text-field>
            <v-text-field v-model="newAdmin.email" label="邮箱"
              :rules="[v => !!v || '邮箱不能为空', v => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址']" required></v-text-field>
            <v-text-field v-model="newAdmin.password" label="密码" type="password"
              :rules="[v => !!v || '密码不能为空', v => v.length >= 6 || '密码长度不能少于6位']" required></v-text-field>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showCreateAdminDialog = false">取消</v-btn>
          <v-btn color="success" @click="createAdmin" :loading="creatingAdmin">创建</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 用户详情对话框 -->
    <v-dialog v-model="showUserDetailsDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">用户详情</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <div class="d-flex justify-center">
              <v-avatar size="120">
                <v-img :src="selectedUserDetails?.avatar || 'https://randomuser.me/api/portraits/lego/1.jpg'"
                  :alt="selectedUserDetails?.username"></v-img>
              </v-avatar>
            </div>
            <v-divider></v-divider>
            <div class="d-flex flex-column gap-2">
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-account</v-icon>
                <span class="text-subtitle-1">用户名：</span>
                <span class="text-body-1 ml-2">{{ selectedUserDetails?.username }}</span>
              </div>
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-email</v-icon>
                <span class="text-subtitle-1">邮箱：</span>
                <span class="text-body-1 ml-2">{{ selectedUserDetails?.email }}</span>
              </div>
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-account-cog</v-icon>
                <span class="text-subtitle-1">角色：</span>
                <v-chip :color="getRoleColor(selectedUserDetails?.role || '')" size="small" class="ml-2">
                  {{ getRoleName(selectedUserDetails?.role || '') }}
                </v-chip>
              </div>
              <div v-if="selectedUserDetails?.role === 'admin'" class="d-flex align-center">
                <v-icon class="mr-2">mdi-shield-account</v-icon>
                <span class="text-subtitle-1">管理员类型：</span>
                <v-chip :color="selectedUserDetails?.admin_type === 'software_admin' ? 'error' : 'warning'" size="small"
                  class="ml-2">
                  {{ selectedUserDetails?.admin_type === 'software_admin' ? '软件管理员' : '组织管理员' }}
                </v-chip>
              </div>
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-text</v-icon>
                <span class="text-subtitle-1">简介：</span>
                <span class="text-body-1 ml-2">{{ selectedUserDetails?.profile || '暂无简介' }}</span>
              </div>
              <div v-if="selectedUserDetails?.organization_name" class="d-flex align-center">
                <v-icon class="mr-2">mdi-office-building</v-icon>
                <span class="text-subtitle-1">所属组织：</span>
                <span class="text-body-1 ml-2">{{ selectedUserDetails.organization_name }}</span>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showUserDetailsDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 邀请码对话框 -->
    <v-dialog v-model="showInviteCodeDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">邀请码</v-card-title>
        <v-card-text>
          <v-tabs v-model="activeInviteTab" color="primary">
            <v-tab value="publisher">编辑邀请码</v-tab>
            <v-tab value="reviewer">专家邀请码</v-tab>
          </v-tabs>
          <v-window v-model="activeInviteTab">
            <v-window-item value="publisher">
              <div class="d-flex flex-column align-center gap-4 mt-4">
                <v-icon color="success" size="64" class="mb-2">mdi-account-edit</v-icon>
                <div class="text-h5 font-weight-bold">{{ publisherInviteCode }}</div>
                <div class="text-body-2 text-medium-emphasis text-center">
                  请将此邀请码发送给需要注册的编辑，编辑可以使用此邀请码完成注册。
                </div>
              </div>
            </v-window-item>
            <v-window-item value="reviewer">
              <div class="d-flex flex-column align-center gap-4 mt-4">
                <v-icon color="primary" size="64" class="mb-2">mdi-account-tie</v-icon>
                <div class="text-h5 font-weight-bold">{{ reviewerInviteCode }}</div>
                <div class="text-body-2 text-medium-emphasis text-center">
                  请将此邀请码发送给需要注册的专家，专家可以使用此邀请码完成注册。
                </div>
              </div>
            </v-window-item>
          </v-window>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <!-- <v-btn color="primary" @click="copyInviteCode">
            <v-icon start>mdi-content-copy</v-icon>
            复制邀请码
          </v-btn> -->
          <v-btn color="grey" variant="text" @click="showInviteCodeDialog = false">
            关闭
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import userApi from '@/api/user'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

interface User {
  id: number
  avatar: string
  username: string
  email: string
  role: string
  permission: string
  registerTime: number
  lastLoginTime: number
  admin_type?: string
  organization?: string
}

const headers = computed(() => {
  const baseHeaders = [
    { title: '头像', key: 'avatar', align: 'center', sortable: false, width: '80px' },
    { title: '用户名', key: 'username', align: 'start', width: '120px' },
    { title: '邮箱', key: 'email', align: 'start', width: '180px' },
    { title: '角色', key: 'role', align: 'center', width: '100px' },
    { title: '权限', key: 'permission', align: 'center', sortable: false, width: '200px' },
    { title: '注册时间', key: 'registerTime', align: 'center', width: '160px' },
    { title: '操作', key: 'actions', align: 'center', sortable: false, width: '120px' },
  ]

  if (currentUser.value?.admin_type === 'software_admin') {
    baseHeaders.splice(5, 0, { title: '组织', key: 'organization', align: 'center', width: '120px' })
  }

  return baseHeaders
}) as any

// 分页相关
const users = ref<User[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalUsers = ref(0)
const totalPages = ref(1)

// 权限编辑相关
const showPermissionDialog = ref(false)
const selectedUser = ref<User | null>(null)
const editingPermissions = ref({
  uploadImage: false,
  submitAI: false,
  publishReview: false,
  submitReview: false
})

// 删除对话框相关
const showDeleteDialog = ref(false)

// 搜索相关
const searchQuery = ref('')
const organizationQuery = ref('')
const selectedHeader = ref<typeof headers[0] | null>(null)

// 可搜索的列
const searchableHeaders = computed(() => {
  return headers.value.filter((header: { key: string }) =>
    header.key !== 'avatar' &&
    header.key !== 'permission' &&
    header.key !== 'actions'
  )
})

const selectHeader = (header: typeof headers[0]) => {
  selectedHeader.value = header
  searchQuery.value = ''
  organizationQuery.value = ''
}

const handleSearch = () => {
  currentPage.value = 1
  pageSize.value = 10
  fetchUsers(1, 10)
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const openPermissionDialog = (user: User) => {
  selectedUser.value = user
  // 只有非管理员和非根管理员才能修改权限
  if (user.role !== 'admin' && user.email !== ROOT_ADMIN_EMAIL) {
    editingPermissions.value = {
      uploadImage: getPermissionBit(user.permission, 3),
      submitAI: getPermissionBit(user.permission, 2),
      publishReview: getPermissionBit(user.permission, 1),
      submitReview: getPermissionBit(user.permission, 0)
    }
    showPermissionDialog.value = true
  } else {
    snackbar.showMessage('不能修改管理员权限', 'warning')
  }
}

const updatePermissions = async () => {
  if (selectedUser.value && selectedUser.value.role !== 'admin' && selectedUser.value.email !== ROOT_ADMIN_EMAIL) {
    try {
      // 计算权限值（4位二进制）
      const permissionValue =
        (editingPermissions.value.uploadImage ? 8 : 0) +  // 第3位：上传图像
        (editingPermissions.value.submitAI ? 4 : 0) +     // 第2位：提交AI检测
        (editingPermissions.value.publishReview ? 2 : 0) + // 第1位：发布人工审核
        (editingPermissions.value.submitReview ? 1 : 0)    // 第0位：提交人工审核

      // 转换为4位二进制字符串
      const permissionBinary = permissionValue.toString(2).padStart(4, '0')
      await userApi.updateUserPermission(selectedUser.value.id, permissionBinary)

      // 更新本地数据
      const userToUpdate = users.value.find(u => u.id === selectedUser.value!.id)
      if (userToUpdate) {
        userToUpdate.permission = permissionBinary  // 使用二进制字符串
      }

      snackbar.showMessage('权限更新成功', 'success')
    } catch (error) {
      console.error('更新权限失败:', error)
      snackbar.showMessage('更新权限失败', 'error')
    }
  }
  showPermissionDialog.value = false
}

const openDeleteDialog = (user: User) => {
  // 根管理员不能被删除
  if (user.email === ROOT_ADMIN_EMAIL) {
    snackbar.showMessage('不能删除软件管理员', 'warning')
    return
  }
  if (currentUser.value?.admin_type === 'organization_admin') {
    if (user.admin_type === 'organization_admin') {
      snackbar.showMessage('不能删除自己', 'warning')
      return
    }
  }
  selectedUser.value = user
  showDeleteDialog.value = true
}

const deleteUser = async () => {
  if (selectedUser.value) {
    try {
      await userApi.deleteUser(selectedUser.value.id)
      users.value = users.value.filter(u => u.id !== selectedUser.value!.id)
      snackbar.showMessage('用户删除成功', 'success')
    } catch (error) {
      console.error('删除用户失败:', error)
      snackbar.showMessage('删除用户失败', 'error')
    }
  }
  currentPage.value = 1
  pageSize.value = 10
  fetchUsers(currentPage.value, pageSize.value)
  showDeleteDialog.value = false
}

// 筛选相关
const showFilterDialog = ref(false)
const filters = ref<{
  role: string | null
  permissions: {
    uploadImage: boolean | null
    submitAI: boolean | null
    publishReview: boolean | null
    submitReview: boolean | null
  }
  timeRange: string | null
  startDate: string | null
  endDate: string | null
  enablePermissionFilter: boolean
}>({
  role: null,
  permissions: {
    uploadImage: null,
    submitAI: null,
    publishReview: null,
    submitReview: null
  },
  timeRange: null,
  startDate: null,
  endDate: null,
  enablePermissionFilter: false
})

const roleOptions = [
  { title: '编辑', value: 'publisher' },
  { title: '专家', value: 'reviewer' },
  { title: '管理员', value: 'admin' }
]

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' }
]

// 保存原始数据用于重置
const originalUsers = ref<User[]>([])

// 初始化时保存原始数据
const initOriginalUsers = () => {
  originalUsers.value = [...users.value]
}

// 重置筛选条件
const resetFilters = () => {
  filters.value = {
    role: null,
    permissions: {
      uploadImage: null,
      submitAI: null,
      publishReview: null,
      submitReview: null
    },
    timeRange: null,
    startDate: null,
    endDate: null,
    enablePermissionFilter: false
  }
  // searchQuery.value = ''
  // organizationQuery.value = ''
  timeError.value = ''
  currentPage.value = 1
  pageSize.value = 10
  fetchUsers(1, 10)
  showFilterDialog.value = false
}

// 应用筛选条件
const applyFilters = () => {
  // 如果有时间错误，不执行筛选
  if (timeError.value) {
    return
  }

  // 计算权限值
  let permissionValue = 0
  if (filters.value.permissions.uploadImage !== null) {
    permissionValue |= (filters.value.permissions.uploadImage ? 8 : 0)
  }
  if (filters.value.permissions.submitAI !== null) {
    permissionValue |= (filters.value.permissions.submitAI ? 4 : 0)
  }
  if (filters.value.permissions.publishReview !== null) {
    permissionValue |= (filters.value.permissions.publishReview ? 2 : 0)
  }
  if (filters.value.permissions.submitReview !== null) {
    permissionValue |= (filters.value.permissions.submitReview ? 1 : 0)
  }

  currentPage.value = 1
  pageSize.value = 10
  fetchUsers(1, 10)
  showFilterDialog.value = false
}

// 在 script 部分添加时间验证相关的代码
const timeError = ref('')

// 处理快速选择时间范围变化
const handleTimeRangeChange = (value: string | null) => {
  if (value) {
    // 如果选择了快速时间范围，清空自定义时间
    filters.value.startDate = null
    filters.value.endDate = null
    timeError.value = ''
  }
}

// 处理自定义时间变化
const handleCustomTimeChange = () => {
  // 如果输入了自定义时间，清空快速选择
  filters.value.timeRange = null

  // 验证时间
  if (!filters.value.startDate || !filters.value.endDate) {
    timeError.value = '开始时间和结束时间不能为空'
    return
  }

  const startTime = new Date(filters.value.startDate).getTime()
  const endTime = new Date(filters.value.endDate).getTime()

  if (startTime >= endTime) {
    timeError.value = '开始时间必须早于结束时间'
  } else {
    timeError.value = ''
  }
}


const getRoleColor = (role: string) => {
  switch (role) {
    case 'publisher':
      return 'success'
    case 'reviewer':
      return 'primary'
    case 'admin':
      return 'error'
    default:
      return 'grey'
  }
}

const getRoleName = (role: string) => {
  switch (role) {
    case 'publisher':
      return '编辑'
    case 'reviewer':
      return '专家'
    case 'admin':
      return '管理员'
    default:
      return role
  }
}

const getPermissionBit = (permission: string | null, bit: number) => {
  if (permission === null) return false
  // 将二进制字符串转换为数字，然后进行位运算
  const permissionNum = parseInt(permission, 2)
  return ((permissionNum >> bit) & 1) === 1
}

// 创建管理员相关
const showCreateAdminDialog = ref(false)
const creatingAdmin = ref(false)
const newAdmin = ref({
  username: '',
  email: '',
  password: '',
  role: 'admin'
})

// 从后端获取用户数据
const fetchUsers = async (page: number, pageSize: number) => {
  loading.value = true
  try {
    // 计算权限筛选值（4 位二进制）
    let permissionFilter = ''
    if (filters.value.enablePermissionFilter) {
      const { uploadImage, submitAI, publishReview, submitReview } = filters.value.permissions
      if (uploadImage !== null || submitAI !== null || publishReview !== null || submitReview !== null) {
        let value = 0
        if (uploadImage !== null) { value |= (uploadImage ? 8 : 0) }
        if (submitAI !== null) { value |= (submitAI ? 4 : 0) }
        if (publishReview !== null) { value |= (publishReview ? 2 : 0) }
        if (submitReview !== null) { value |= (submitReview ? 1 : 0) }
        permissionFilter = value.toString(2).padStart(4, '0')
      }
    }

    // 计算时间筛选
    let startTimeFilter: string | undefined
    let endTimeFilter: string | undefined
    if (filters.value.timeRange) {
      const now = Date.now()
      const ranges: Record<string, number> = {
        '1d': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
        '90d': 90 * 24 * 60 * 60 * 1000,
        '365d': 365 * 24 * 60 * 60 * 1000
      }
      const rangeMs = ranges[filters.value.timeRange as keyof typeof ranges]
      startTimeFilter = formatDateFilter(now - rangeMs)
      endTimeFilter = formatDateFilter(now)
    } else if (filters.value.startDate && filters.value.endDate) {
      startTimeFilter = formatDateFilter(new Date(filters.value.startDate).getTime())
      endTimeFilter = formatDateFilter(new Date(filters.value.endDate).getTime())
    }

    const params = {
      page,
      page_size: pageSize,
      query: searchQuery.value || '',
      role: filters.value.role || '',
      permission: permissionFilter || '',
      startTime: startTimeFilter,
      endTime: endTimeFilter,
      organization: currentUser.value?.admin_type === 'software_admin' ? organizationQuery.value : ''
    }
    const response = await userApi.getUsers(params)
    const { users: userList, current_page, total_pages, total_users } = response.data

    // 转换后端数据格式为前端格式
    users.value = userList.map((user: any) => ({
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      permission: user.permission,
      registerTime: new Date(user.date_joined).getTime(),
      avatar: import.meta.env.VITE_API_URL + user.avatar || '',
      admin_type: user.admin_type,
      organization: user.organization
    }))

    currentPage.value = current_page
    totalPages.value = total_pages
    totalUsers.value = total_users

    // 保存原始数据用于筛选
    originalUsers.value = [...users.value]
  } catch (error) {
    console.error('获取用户数据失败:', error)
    snackbar.showMessage('获取用户数据失败', 'error')
  } finally {
    loading.value = false
  }
}

// 创建管理员
const createAdmin = async () => {
  if (!newAdmin.value.username || !newAdmin.value.email || !newAdmin.value.password) {
    snackbar.showMessage('请填写完整信息', 'error')
    return
  }

  creatingAdmin.value = true
  try {
    const response = await userApi.createAdmin(newAdmin.value)
    snackbar.showMessage('管理员创建成功', 'success')
    showCreateAdminDialog.value = false
    // 刷新用户列表
    fetchUsers(currentPage.value, pageSize.value)
    // 重置表单
    newAdmin.value = {
      username: '',
      email: '',
      password: '',
      role: 'admin'
    }
  } catch (error) {
    console.error('创建管理员失败:', error)
    snackbar.showMessage('创建管理员失败', 'error')
  } finally {
    creatingAdmin.value = false
  }
}

// 处理页码变化
const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchUsers(page, pageSize.value)
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1 // 重置到第一页
  fetchUsers(1, size)
}

// 当前用户
const currentUser = ref<{
  email: string;
  admin_type?: string;
  organization?: number;
} | null>(null)

// 初始化
onMounted(async () => {
  try {
    const res = await userApi.getUserInfo()
    currentUser.value = res.data
  } catch (error) {
    console.error('获取当前用户信息失败:', error)
  }
  fetchUsers(currentPage.value, pageSize.value)
})

const ROOT_ADMIN_EMAIL = 'admin@mail.com'

// 时间格式化，用于筛选条件
const formatDateFilter = (timestamp: number) => {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

// 用户详情相关
const showUserDetailsDialog = ref(false)
const selectedUserDetails = ref<{
  username: string
  email: string
  role: string
  profile: string
  avatar: string
  admin_type: string
  organization: string
  organization_name: string
} | null>(null)

// 打开用户详情对话框
const openUserDetailsDialog = async (user: User) => {
  // // 检查权限
  // if (user.role === 'admin' && currentUser.value?.email !== ROOT_ADMIN_EMAIL) {
  //   snackbar.showMessage('只有软件管理员才能查看管理员信息', 'warning')
  //   return
  // }

  try {
    let response;
    if (user.role === 'admin') {
      response = await userApi.getAdminDetail(user.id);
    } else {
      response = await userApi.getOtherUserInfo(user.id);
    }

    selectedUserDetails.value = {
      ...response.data,
      avatar: import.meta.env.VITE_API_URL + response.data.avatar,
    }
    showUserDetailsDialog.value = true
  } catch (error) {
    console.error('获取用户详情失败:', error)
    snackbar.showMessage('获取用户详情失败', 'error')
  }
}

// 邀请码相关
const showInviteCodeDialog = ref(false)
const activeInviteTab = ref('publisher')
const publisherInviteCode = ref('')
const reviewerInviteCode = ref('')

// 获取邀请码
const getInviteCode = async () => {
  try {
    const response = await userApi.getInviteCode({
      organization_id: currentUser.value?.organization,
    })
    if (activeInviteTab.value === 'publisher') {
      publisherInviteCode.value = response.data[0].code
    } else {
      reviewerInviteCode.value = response.data[1].code
    }
  } catch (error) {
    console.error('获取邀请码失败:', error)
    snackbar.showMessage('获取邀请码失败', 'error')
  }
}

// 复制邀请码
const copyInviteCode = () => {
  const codeToCopy = activeInviteTab.value === 'publisher' ? publisherInviteCode.value : reviewerInviteCode.value
  navigator.clipboard.writeText(codeToCopy).then(() => {
    snackbar.showMessage('邀请码已复制到剪贴板', 'success')
  }).catch(() => {
    snackbar.showMessage('复制失败，请手动复制', 'error')
  })
}

// 监听标签页切换
watch(activeInviteTab, (newValue) => {
  if (showInviteCodeDialog.value) {
    getInviteCode()
  }
})

// 修改按钮点击事件
const handleAddExpert = () => {
  showInviteCodeDialog.value = true
  activeInviteTab.value = 'reviewer'
  getInviteCode()
}
</script>

<style scoped>
.v-card {
  border-radius: 12px;
  overflow: hidden;
}

.role-chip {
  font-size: 12px;
  padding: 0 12px;
  font-weight: 500;
}

.v-btn.v-btn--size-small {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
}

.v-btn--icon.v-btn--size-small .v-icon {
  font-size: 18px;
}

:deep(.v-data-table) {
  border-radius: 12px;
  width: 100%;
  table-layout: fixed;
}

:deep(.v-data-table-header) {
  background-color: rgb(var(--v-theme-surface-variant));
}

:deep(.v-data-table-header th) {
  font-weight: 600;
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
  white-space: nowrap;
  padding: 12px 8px;
  text-align: center;
}

:deep(.v-data-table__tr td) {
  white-space: nowrap;
  padding: 12px 8px;
  text-align: center;
}

:deep(.v-data-table__tr td:first-child) {
  text-align: center;
}

:deep(.v-data-table__tr td:nth-child(2)),
:deep(.v-data-table__tr td:nth-child(3)) {
  text-align: left;
}

:deep(.v-data-table__tr:hover) {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

:deep(.v-chip) {
  font-weight: 500;
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
</style>
