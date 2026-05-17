<template>
  <v-container class="workspace-shell admin-home" fluid>
    <v-card class="page-hero mb-6">
      <v-card-text class="pa-7 pa-md-9">
        <div class="d-flex flex-column flex-md-row align-md-center justify-space-between ga-5">
          <div>
            <div class="section-eyebrow mb-2">管理端</div>
            <h1 class="hero-title mb-3">平台管理</h1>
            <p class="hero-copy mb-0">
              处理审核、查看运行状态、维护组织用户和检测模型。
            </p>
          </div>
          <v-btn color="primary" size="large" rounded="lg" prepend-icon="mdi-gavel" to="/reviews">
            进入人工审核
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col v-for="item in quickActions" :key="item.title" cols="12" sm="6" lg="4">
        <v-card class="quick-card h-100" :to="item.to">
          <v-card-text class="pa-6">
            <div class="d-flex align-start ga-4">
              <div class="quick-icon" :class="item.tone">
                <v-icon size="28">{{ item.icon }}</v-icon>
              </div>
              <div>
                <div class="text-h6 font-weight-bold mb-1">{{ item.title }}</div>
                <div class="text-body-2 subtle-text">{{ item.text }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
const quickActions = [
  {
    title: '统计分析',
    text: '查看任务趋势和组织活跃度。',
    icon: 'mdi-chart-bar',
    to: '/analytics',
    tone: 'tone-blue',
  },
  {
    title: '资源管理',
    text: '查看上传文件和检测资源。',
    icon: 'mdi-folder-multiple-outline',
    to: '/files',
    tone: 'tone-cyan',
  },
  {
    title: '用户管理',
    text: '维护账号、角色和权限。',
    icon: 'mdi-account-group-outline',
    to: '/users',
    tone: 'tone-amber',
  },
  {
    title: '人工审核',
    text: '审批申请并跟踪审核进度。',
    icon: 'mdi-gavel',
    to: '/reviews',
    tone: 'tone-rose',
  },
  {
    title: '模型配置',
    text: '配置对话模型和 FastDetect。',
    icon: 'mdi-robot-outline',
    to: '/llms',
    tone: 'tone-blue',
  },
  {
    title: '日志记录',
    text: '查看关键操作记录。',
    icon: 'mdi-clipboard-text-clock-outline',
    to: '/logs',
    tone: 'tone-cyan',
  },
]
</script>

<style scoped>
.quick-card {
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  cursor: pointer;
}

.quick-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 34px rgba(23, 32, 51, 0.1) !important;
}

.quick-icon {
  width: 50px;
  height: 50px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 12px;
}

.tone-blue {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
}

.tone-cyan {
  color: #0891b2;
  background: rgba(8, 145, 178, 0.1);
}

.tone-amber {
  color: #d97706;
  background: rgba(217, 119, 6, 0.12);
}

.tone-rose {
  color: #e11d48;
  background: rgba(225, 29, 72, 0.1);
}
</style>
