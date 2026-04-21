<template>
  <div>
    <v-menu v-model="menu" location="bottom end" offset-y>
      <template #activator="{ props }">
        <v-badge :content="messageStore.notifications.length" color="red" v-if="messageStore.notifications.length > 0"
          :max="99">
          <v-btn icon v-bind="props">
            <v-icon>mdi-bell</v-icon>
          </v-btn>
        </v-badge>
        <v-btn icon v-else v-bind="props">
          <v-icon>mdi-bell</v-icon>
        </v-btn>
      </template>

      <v-card width="400" max-height="500" class="overflow-y-auto">
        <v-card-title class="text-h6 font-weight-bold pa-4">通知中心</v-card-title>
        <v-divider />
        <v-list>
          <template v-if="messageStore.notifications.length > 0">
            <v-list-item v-for="(item, index) in messageStore.notifications" :key="index" density="comfortable"
              class="pa-3">
              <template #prepend>
                <v-icon color="primary" size="large" class="mr-3">mdi-information</v-icon>
              </template>
              <v-list-item-title class="text-body-1 font-weight-medium mb-1">{{ item.message }}</v-list-item-title>
              <!-- <v-list-item-subtitle class="text-caption text-grey">{{ formatTime(item.timestamp) }}</v-list-item-subtitle> -->
            </v-list-item>
          </template>
          <v-list-item v-else class="pa-4">
            <v-list-item-title class="text-grey text-center">暂无通知</v-list-item-title>
          </v-list-item>
        </v-list>

        
        <v-divider />
        <v-card-actions class="pa-3">
          <v-btn color="primary" variant="text" class="ms-auto" @click="clear">清空通知</v-btn>
        </v-card-actions>
      </v-card>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessageStore } from '@/stores/message'

const menu = ref(false)
const messageStore = useMessageStore()

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const clear = () => {
  messageStore.clearNotifications()
}
</script>

<style scoped>
.v-list-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.v-list-item:last-child {
  border-bottom: none;
}
</style>
