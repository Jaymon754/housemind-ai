import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToastItem {
  id: number
  message: string
  tone: 'success' | 'error' | 'info'
}

export const useToastStore = defineStore('toast', () => {
  const items = ref<ToastItem[]>([])
  let sequence = 0

  function push(message: string, tone: ToastItem['tone'] = 'info') {
    const id = ++sequence
    items.value.push({ id, message, tone })
    window.setTimeout(() => dismiss(id), 3800)
  }
  function dismiss(id: number) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  return { items, push, dismiss }
})
