<template>
  <v-container class="workspace-shell user-home" fluid>
    <v-card class="page-hero mb-6">
      <v-card-text class="pa-7 pa-md-9">
        <div class="d-flex flex-column flex-md-row align-md-center justify-space-between ga-5">
          <div>
            <div class="section-eyebrow mb-2">{{ hero.eyebrow }}</div>
            <h1 class="hero-title mb-3">{{ hero.title }}</h1>
            <p class="hero-copy mb-0">{{ hero.text }}</p>
          </div>
          <v-btn color="primary" size="large" rounded="lg" :prepend-icon="hero.actionIcon" :to="hero.actionTo">
            {{ hero.actionText }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col v-for="item in homeCards" :key="item.title" cols="12" :md="homeCards.length === 2 ? 6 : 4">
        <v-card class="home-card h-100" :to="item.to">
          <v-card-text class="pa-6">
            <div class="home-icon mb-4" :class="item.tone">
              <v-icon size="28">{{ item.icon }}</v-icon>
            </div>
            <div class="text-h6 font-weight-bold mb-2">{{ item.title }}</div>
            <div class="text-body-2 subtle-text">{{ item.text }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const publisherCards = [
  {
    title: '学术图像',
    text: '上传图片、PDF 或 ZIP，选择需要检测的图像。',
    icon: 'mdi-image-search-outline',
    tone: 'tone-green',
    to: '/upload',
  },
  {
    title: '论文全文',
    text: '上传论文文档，预览文本后提交检测。',
    icon: 'mdi-file-document-edit-outline',
    tone: 'tone-blue',
    to: '/upload',
  },
  {
    title: 'Review 检测',
    text: '上传原论文和 Review，检查评审内容。',
    icon: 'mdi-comment-text-multiple-outline',
    tone: 'tone-orange',
    to: '/upload',
  },
]

const reviewerCards = [
  {
    title: '待审任务',
    text: '查看分配给你的人工审核任务。',
    icon: 'mdi-clipboard-text-search-outline',
    tone: 'tone-blue',
    to: '/review',
  },
  {
    title: '个人信息',
    text: '维护头像、联系方式和个人简介。',
    icon: 'mdi-account-circle-outline',
    tone: 'tone-orange',
    to: '/profile',
  },
]

const hero = computed(() => {
  if (userStore.role === 'reviewer') {
    return {
      eyebrow: '审稿工作台',
      title: '查看审阅任务',
      text: '这里仅展示审稿相关入口。检测上传和发布审核由出版社用户完成。',
      actionText: '进入审阅',
      actionIcon: 'mdi-book-open-page-variant',
      actionTo: '/review',
    }
  }

  return {
    eyebrow: '检测工作台',
    title: '开始一次检测',
    text: '上传图像、论文或 Review，确认内容后提交检测并查看报告。',
    actionText: '上传任务',
    actionIcon: 'mdi-cloud-upload-outline',
    actionTo: '/upload',
  }
})

const homeCards = computed(() => {
  return userStore.role === 'reviewer' ? reviewerCards : publisherCards
})
</script>

<style scoped>
.home-card {
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  cursor: pointer;
}

.home-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 34px rgba(21, 34, 56, 0.1) !important;
}

.home-icon {
  width: 50px;
  height: 50px;
  display: grid;
  place-items: center;
  border-radius: 12px;
}

.tone-green {
  color: #0f9f7a;
  background: rgba(15, 159, 122, 0.12);
}

.tone-blue {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
}

.tone-orange {
  color: #ea7a1a;
  background: rgba(234, 122, 26, 0.12);
}
</style>
