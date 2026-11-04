import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ValuationResult, VisionResult } from '@/types'

export const useAnalysisStore = defineStore('analysis', () => {
  const valuation = ref<ValuationResult | null>(null)
  const vision = ref<VisionResult | null>(null)
  const linkImageToAgent = ref(false)

  function setValuation(value: ValuationResult) {
    valuation.value = value
  }
  function setVision(value: VisionResult | null) {
    vision.value = value
  }
  return { valuation, vision, linkImageToAgent, setValuation, setVision }
})
