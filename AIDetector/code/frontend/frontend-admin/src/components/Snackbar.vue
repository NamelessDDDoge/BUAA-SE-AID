<!-- components/GlobalSnackbar.vue -->
<template>
  <div v-if="show" class="snackbar" :class="typeClass">
    <div class="snackbar-content">
      <span class="snackbar-message">{{ message }}</span>
      <v-btn
        icon="mdi-close"
        variant="text"
        size="small"
        class="snackbar-close"
        @click="store.hide()"
      ></v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useSnackbarStore } from '@/stores/snackbar';

const store = useSnackbarStore();

const typeClass = computed(() => `snackbar--${store.type}`);
const show = computed(() => store.show);
const message = computed(() => store.message);
</script>

<style scoped>
.snackbar {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  color: white;
  min-width: 300px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: slideIn 0.3s ease-out;
  z-index: 9999;
}

.snackbar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.snackbar-message {
  flex: 1;
  font-size: 0.875rem;
  line-height: 1.5;
}

.snackbar-close {
  color: white !important;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.snackbar-close:hover {
  opacity: 1;
}

.snackbar--success { 
  background-color: #4CAF50;
  border-left: 4px solid #388E3C;
}

.snackbar--error { 
  background-color: #f44336;
  border-left: 4px solid #d32f2f;
}

.snackbar--warning { 
  background-color: #ff9800;
  border-left: 4px solid #f57c00;
}

.snackbar--info { 
  background-color: #2196F3;
  border-left: 4px solid #1976D2;
}

@keyframes slideIn {
  from {
    bottom: -100px;
    opacity: 0;
    transform: translate(-50%, 20px);
  }
  to {
    bottom: 20px;
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
</style>