<template>
  <div class="d-flex flex-column ga-4">
    <v-alert type="info" variant="tonal">
      Paper results are rendered through the shared resource detail flow, but this wrapper keeps the page task-type aware.
    </v-alert>
    <ResourceDetectionDetailStep :task="task" :reviewer-options="reviewerOptions" @download="emit('download')" @request-review="emit('request-review', $event)" />
  </div>
</template>

<script setup lang="ts">
import ResourceDetectionDetailStep from '@/components/steps/ResourceDetectionDetailStep.vue'

defineProps<{
  task: any
  reviewerOptions: Array<{ id: number; username: string; avatar?: string | null }>
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[] }): void
}>()
</script>
