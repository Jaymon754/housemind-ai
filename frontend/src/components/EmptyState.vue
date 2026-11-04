<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
defineProps<{ title: string; description?: string }>()
</script>

<template>
  <div class="empty">
    <div class="empty-icon"><Inbox :size="19" /></div>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <slot />
  </div>
</template>
