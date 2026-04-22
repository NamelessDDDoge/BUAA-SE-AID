<template>
  <div class="d-flex flex-wrap ga-2">
    <v-chip
      v-for="option in options"
      :key="option.value"
      :color="modelValue === option.value ? option.color : undefined"
      :variant="modelValue === option.value ? 'flat' : 'outlined'"
      class="cursor-pointer"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
      <span v-if="typeof option.count === 'number'" class="ml-2">{{ option.count }}</span>
    </v-chip>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  options: Array<{ label: string; value: string; color?: string; count?: number }>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()
</script>
