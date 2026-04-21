<template>
  <v-container fluid class="organization-profile-page">
    <!-- 页面标题 -->
    <v-row class="mb-6">
      <v-col>
        <h1 class="text-h4 font-weight-bold">组织信息</h1>
      </v-col>
    </v-row>

    <!-- 主要内容区域 -->
    <v-row>
      <!-- 左侧组织信息卡片 -->
      <v-col cols="12" md="4">
        <v-card class="organization-card" elevation="2">
          <v-card-text class="text-center pa-6">
            <v-avatar size="200" class="mb-6 organization-logo">
              <v-img :src="getImgUrl(organizationInfo.logo) || '/default-organization.png'" alt="组织Logo"></v-img>
            </v-avatar>
            <h2 class="text-h5 font-weight-bold mb-2">{{ organizationInfo.name }}</h2>
            <p class="text-body-1 text-grey mb-4">{{ organizationInfo.description }}</p>
            <v-divider class="mb-4"></v-divider>
            <div class="text-left">
              <div class="d-flex align-center mb-2">
                <v-icon color="primary" class="me-2">mdi-email</v-icon>
                <span class="text-body-1">{{ organizationInfo.email }}</span>
              </div>
              <div class="d-flex align-center mb-2">
                <v-icon color="primary" class="me-2">mdi-calendar</v-icon>
                <span class="text-body-1">创建时间：{{ formatTime(organizationInfo.created_at) }}</span>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧检测次数和充值卡片 -->
      <v-col cols="12" md="8">
        <v-card class="quota-card" elevation="2">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon color="primary" size="24" class="me-2">mdi-chart-bar</v-icon>
            <span class="text-h5">检测次数</span>
          </v-card-title>
          <v-card-text class="pa-6">
            <v-row>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="quota-item">
                  <v-card-text>
                    <div class="text-h6 mb-2">普通检测</div>
                    <div class="text-h4 font-weight-bold text-primary mb-2">
                      {{ organizationQuota?.remaining_non_llm_uses || 0 }}
                    </div>
                    <div class="text-body-2 text-grey">
                      基础配额：100次
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="quota-item">
                  <v-card-text>
                    <div class="text-h6 mb-2">LLM检测</div>
                    <div class="text-h4 font-weight-bold text-primary mb-2">
                      {{ organizationQuota?.remaining_llm_uses || 0 }}
                    </div>
                    <div class="text-body-2 text-grey">
                      基础配额：3次
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <v-divider class="my-6"></v-divider>

            <v-btn 
              color="primary" 
              block 
              size="large" 
              prepend-icon="mdi-credit-card" 
              @click="openRechargeDialog"
              :disabled="!canRecharge"
            >
              充值检测次数
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 充值对话框 -->
    <v-dialog v-model="rechargeDialog" max-width="600px">
      <v-card>
        <v-card-title class="text-h5 font-weight-bold">
          充值检测次数
        </v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <v-alert type="info" variant="tonal" class="mb-4">
                  <div class="text-body-1">
                    <div>当前剩余次数：</div>
                    <div>普通检测：{{ organizationQuota?.remaining_non_llm_uses || 0 }} 次</div>
                    <div>LLM检测：{{ organizationQuota?.remaining_llm_uses || 0 }} 次</div>
                  </div>
                </v-alert>
              </v-col>
              <v-col cols="12">
                <v-radio-group v-model="rechargeType" inline>
                  <v-radio label="普通检测" value="non-llm"></v-radio>
                  <v-radio label="LLM检测" value="llm"></v-radio>
                </v-radio-group>
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="rechargeAmount" label="充值金额（元）" type="number" min="100" step="100" :rules="[
                  v => v >= 100 || '最小充值金额为100元',
                  v => v % 100 === 0 || '充值金额必须是100的倍数'
                ]" variant="outlined"></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-alert type="info" variant="tonal">
                  <div class="text-body-1">
                    <div>充值说明：</div>
                    <div>每100元可兑换：</div>
                    <div v-if="rechargeType === 'non-llm'">- 100次普通检测</div>
                    <div v-else>- 3次LLM检测</div>
                  </div>
                </v-alert>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="rechargeDialog = false">
            取消
          </v-btn>
          <v-btn color="primary" @click="handleRecharge"
            :disabled="!rechargeAmount || rechargeAmount < 100 || rechargeAmount % 100 !== 0">
            确认充值
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useSnackbarStore } from '@/stores/snackbar'
import { useUserStore } from '@/stores/user'
import organization from '@/api/organization'
import userApi from '@/api/user'

const snackbar = useSnackbarStore()
const userStore = useUserStore()

// 组织信息
const organizationInfo = ref({
  id: 0,
  name: '',
  description: '',
  logo: '',
  email: '',
  created_at: ''
})

// 组织配额信息
const organizationQuota = ref<{
  remaining_non_llm_uses: number;
  remaining_llm_uses: number;
} | null>(null)

// 充值相关
const rechargeDialog = ref(false)
const rechargeType = ref<'non-llm' | 'llm'>('non-llm')
const rechargeAmount = ref(100)

// 计算是否可以充值
const canRecharge = computed(() => {
  if (!organizationQuota.value) return false
  return organizationQuota.value.remaining_non_llm_uses < 1000 && organizationQuota.value.remaining_llm_uses < 1000
})

const getImgUrl=(logo:any)=>{
  return import.meta.env.VITE_API_URL+logo
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

// 当前用户
const currentUser = ref<{
  email: string;
  admin_type?: string;
  organization?: number;
} | null>(null)

// 获取组织信息
const fetchOrganizationInfo = async () => {
  try {
    const res = await userApi.getUserInfo()
    currentUser.value = res.data
    const response = await organization.getOrgDetail({ organization_id: userStore.organization })
    organizationInfo.value = response.data
    // 获取组织配额信息
    await fetchOrganizationQuota()
  } catch (error) {
    snackbar.showMessage('获取组织信息失败', 'error')
  }
}

// 获取组织配额信息
const fetchOrganizationQuota = async () => {
  try {
    const response = await organization.getOrgUsage()
    organizationQuota.value = response.data
  } catch (error) {
    snackbar.showMessage('获取组织配额信息失败', 'error')
  }
}

// 打开充值对话框
const openRechargeDialog = () => {
  if (!canRecharge.value) {
    snackbar.showMessage('任意一种检测次数超过10000次时不能充值', 'warning')
    return
  }
  rechargeDialog.value = true
}

// 处理充值
const handleRecharge = async () => {
  try {
    // 计算充值后的次数
    const currentNonLLMUses = organizationQuota.value?.remaining_non_llm_uses || 0
    const currentLLMUses = organizationQuota.value?.remaining_llm_uses || 0
    const rechargeCount = rechargeType.value === 'non-llm' ? 
      Math.floor(rechargeAmount.value / 100) * 100 : // 普通检测：每100元100次
      Math.floor(rechargeAmount.value / 100) * 3     // LLM检测：每100元3次

    const newNonLLMUses = rechargeType.value === 'non-llm' ? 
      currentNonLLMUses + rechargeCount : 
      currentNonLLMUses
    const newLLMUses = rechargeType.value === 'llm' ? 
      currentLLMUses + rechargeCount : 
      currentLLMUses

    if (newNonLLMUses > 1000 || newLLMUses > 1000) {
      snackbar.showMessage('充值金额过多', 'warning')
      return
    }

    await organization.rechargeUses({
      amount: rechargeAmount.value,
      choice: rechargeType.value
    })

    // 充值成功
    rechargeDialog.value = false
    snackbar.showMessage('充值成功', 'success')
    // 刷新组织配额信息
    await fetchOrganizationQuota()
  } catch (error) {
    snackbar.showMessage('充值失败', 'error')
  }
}

onMounted(() => {
  fetchOrganizationInfo()
})
</script>

<style scoped>
.organization-profile-page {
  background-color: rgb(var(--v-theme-background));
  min-height: 100vh;
}

.organization-card {
  border-radius: 12px;
  height: 100%;
}

.quota-card {
  border-radius: 12px;
}

.organization-logo {
  border: 4px solid rgb(var(--v-theme-primary));
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.quota-item {
  border-radius: 8px;
  height: 100%;
  transition: transform 0.2s;
}

.quota-item:hover {
  transform: translateY(-2px);
}
</style>