<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { useAppStore } from '@/stores/app'

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    height?: string
    loading?: boolean
    ariaLabel?: string
  }>(),
  { height: '240px', loading: false, ariaLabel: '数据图表' },
)

const container = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
let observer: ResizeObserver | null = null
const app = useAppStore()

const render = () => {
  if (!chart.value) return
  chart.value.setOption(props.option, { notMerge: true, lazyUpdate: true })
}

onMounted(() => {
  if (!container.value) return
  chart.value = echarts.init(container.value, undefined, { renderer: 'canvas' })
  render()
  observer = new ResizeObserver(() => chart.value?.resize())
  observer.observe(container.value)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  observer?.disconnect()
  chart.value?.dispose()
  chart.value = null
})

watch(
  () => app.meta,
  () => window.setTimeout(render, 30),
)
</script>

<template>
  <div class="chart-shell" :style="{ height }" :aria-label="ariaLabel" role="img">
    <div ref="container" class="chart-inner" />
    <div v-if="loading" class="chart-loading"><span class="spinner" /></div>
  </div>
</template>

<style scoped>
.chart-shell { position: relative; width: 100%; }
.chart-inner { width: 100%; height: 100%; }
.chart-loading { position: absolute; inset: 0; display: grid; place-items: center; background: rgba(251, 248, 241, 0.65); backdrop-filter: blur(2px); }
</style>
