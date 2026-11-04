<script setup lang="ts">
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-vue-next'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toast-stack" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="item in toast.items" :key="item.id" class="toast" :class="item.tone">
        <CheckCircle2 v-if="item.tone === 'success'" :size="16" />
        <TriangleAlert v-else-if="item.tone === 'error'" :size="16" />
        <Info v-else :size="16" />
        <span>{{ item.message }}</span>
        <button aria-label="关闭提示" @click="toast.dismiss(item.id)"><X :size="13" /></button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-stack { position: fixed; right: 24px; bottom: 24px; z-index: 90; display: flex; flex-direction: column; gap: 8px; }
.toast { display: flex; align-items: center; gap: 9px; min-width: 240px; max-width: 380px; background: var(--ink-deep); color: #f8fafc; padding: 11px 13px; font-size: 11.5px; border-radius: 8px; box-shadow: 0 16px 40px rgba(15,23,42,.22); }
.toast.success svg { color: #a9c8a9; }
.toast.error svg { color: #e0a28f; }
.toast.info svg { color: var(--gold-light); }
.toast span { flex: 1; }
.toast button { background: none; border: 0; color: rgba(248,250,252,.55); cursor: pointer; padding: 2px; }
.toast-enter-active, .toast-leave-active { transition: all .24s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
