<template>
    <v-row align="center" justify="center">
      <v-col cols="12" class="text-center">
        <div class="text-h1 font-weight-bold mb-4">
          404
        </div>
        <div class="text-h4 mb-8">
          你来到了没有知识的荒原
        </div>
        <div class="text-body-1 mb-8">
          {{ countdown }}秒后自动返回首页
        </div>
        <v-btn
          color="primary"
          size="large"
          prepend-icon="mdi-home"
          @click="goToHome"
        >
          返回首页
        </v-btn>
      </v-col>
    </v-row>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted, onUnmounted } from 'vue'

const router = useRouter()
const countdown = ref(5)
let timer: number | null = null

const goToHome = () => {
  if (timer) {
    clearInterval(timer)
  }
  router.push('/')
}

onMounted(() => {
  timer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (timer) {
        clearInterval(timer)
      }
      router.push('/')
    }
  }, 1000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.text-h1 {
  font-size: 8rem;
  line-height: 1;
  color: #2c3e50;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
}

.text-h4 {
  color: #34495e;
  font-weight: 300;
}

.v-img {
  border-radius: 12px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.v-img:hover {
  transform: scale(1.05);
}

.v-btn {
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0.5px;
}
</style> 