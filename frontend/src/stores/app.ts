import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import type { Health, Meta } from '@/types'

export const useAppStore = defineStore('app', () => {
  const meta = ref<Meta | null>(null)
  const health = ref<Health | null>(null)
  const loading = ref(false)
  const error = ref('')
  let loaded = false

  async function load(force = false) {
    if (loaded && !force) return
    loading.value = true
    error.value = ''
    try {
      const [m, h] = await Promise.all([api.meta(), api.health()])
      meta.value = m
      health.value = h
      loaded = true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '无法连接分析服务'
    } finally {
      loading.value = false
    }
  }

  return { meta, health, loading, error, load }
})
