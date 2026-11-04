<script setup lang="ts">
import { computed } from 'vue'
import {
  BookOpen,
  Building2,
  Calculator,
  CheckCircle2,
  ChevronDown,
  GitBranch,
  MapPin,
  ScanEye,
  TriangleAlert,
  Wrench,
} from 'lucide-vue-next'
import type { AgentToolCall } from '@/types'

const props = defineProps<{ calls: AgentToolCall[] }>()

const icons: Record<string, unknown> = {
  predict_house_price: Building2,
  explain_house_price: GitBranch,
  analyze_market: MapPin,
  calculate_investment: Calculator,
  search_property_knowledge: BookOpen,
  analyze_house_image: ScanEye,
}
const totalLatency = computed(() => props.calls.reduce((sum, call) => sum + (call.latency_ms ?? 0), 0))
const running = computed(() => props.calls.some((call) => call.status === 'running'))
const doneCount = computed(() => props.calls.filter((call) => call.status === 'done').length)

function iconFor(name: string) {
  return icons[name] ?? Wrench
}
function pretty(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}
function argSummary(args: Record<string, unknown>): string {
  return Object.entries(args)
    .slice(0, 4)
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join('/') : String(value)}`)
    .join(' · ')
}
</script>

<template>
  <div class="tool-trace">
    <div class="trace-head">
      <span class="trace-orb" :class="{ active: running }"><Wrench :size="11" /></span>
      <span class="trace-title">工具调用轨迹</span>
      <span class="trace-count">{{ doneCount }}/{{ calls.length }}</span>
      <span v-if="running" class="trace-live"><i />执行中</span>
      <span v-else class="trace-latency">{{ totalLatency }} ms</span>
    </div>
    <div class="trace-list">
      <details v-for="call in calls" :key="call.id" class="trace-item" :class="call.status">
        <summary>
          <span class="tool-icon"><component :is="iconFor(call.name)" :size="14" /></span>
          <span class="tool-copy">
            <span class="tool-name">{{ call.label }}</span>
            <span class="tool-summary">{{ call.status === 'running' ? '正在执行…' : call.summary || call.error || call.reason }}</span>
          </span>
          <span class="tool-state">
            <span v-if="call.status === 'running'" class="spinner" />
            <CheckCircle2 v-else-if="call.status === 'done'" :size="13" class="ok" />
            <TriangleAlert v-else :size="13" class="err" />
            <small v-if="call.latency_ms">{{ call.latency_ms }}ms</small>
            <ChevronDown :size="12" class="chev" />
          </span>
        </summary>
        <div class="trace-detail">
          <div class="detail-block">
            <span class="detail-label">调用原因</span>
            <p>{{ call.reason }}</p>
          </div>
          <div class="detail-block">
            <span class="detail-label">参数</span>
            <code>{{ argSummary(call.arguments) }}</code>
          </div>
          <details class="raw-details">
            <summary>查看原始返回</summary>
            <pre>{{ pretty(call.data ?? call.error ?? {}) }}</pre>
          </details>
        </div>
      </details>
    </div>
  </div>
</template>

<style scoped>
.tool-trace { border: 1px solid var(--line); background: rgba(234,226,212,.28); border-radius: 4px; margin: 11px 0 13px; overflow: hidden; }
.trace-head { display: flex; align-items: center; gap: 7px; padding: 8px 11px; border-bottom: 1px solid var(--line-soft); }
.trace-orb { width: 19px; height: 19px; border-radius: 50%; background: var(--ink); color: var(--gold-light); display: grid; place-items: center; }
.trace-orb.active { animation: pulse-orb 1.6s ease infinite; }
@keyframes pulse-orb { 0%,100% { box-shadow: 0 0 0 0 rgba(176,138,82,.3); } 50% { box-shadow: 0 0 0 5px rgba(176,138,82,0); } }
.trace-title { font-size: 8.5px; font-weight: 650; letter-spacing: .08em; }
.trace-count { font-size: 7.5px; color: var(--muted); border: 1px solid var(--line); border-radius: 99px; padding: 1px 5px; }
.trace-live { margin-left: auto; display: inline-flex; align-items: center; gap: 4px; font-size: 7.5px; color: var(--gold); }
.trace-live i { width: 4px; height: 4px; border-radius: 50%; background: var(--gold); animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: .25; } }
.trace-latency { margin-left: auto; font-size: 7.5px; color: var(--muted-light); }
.trace-list { padding: 3px 7px 6px; }
.trace-item { border-bottom: 1px solid var(--line-soft); }
.trace-item:last-child { border-bottom: 0; }
.trace-item > summary { display: flex; align-items: center; gap: 8px; padding: 7px 4px; cursor: pointer; list-style: none; }
.trace-item > summary::-webkit-details-marker { display: none; }
.tool-icon { width: 23px; height: 23px; border: 1px solid var(--line); border-radius: 3px; display: grid; place-items: center; color: var(--ink-soft); flex: 0 0 auto; background: rgba(251,248,241,.6); }
.tool-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 1px; }
.tool-name { font-size: 8.5px; font-weight: 650; }
.tool-summary { font-size: 7.5px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 520px; }
.tool-state { display: flex; align-items: center; gap: 5px; flex: 0 0 auto; }
.tool-state small { font-size: 7px; color: var(--muted-light); }
.tool-state .ok { color: var(--positive); }
.tool-state .err { color: var(--negative); }
.chev { color: var(--muted-light); transition: transform .2s; }
.trace-item[open] .chev { transform: rotate(180deg); }
.trace-detail { padding: 0 4px 10px 35px; display: flex; flex-direction: column; gap: 8px; }
.detail-block { display: flex; flex-direction: column; gap: 2px; }
.detail-label { font-size: 6.5px; letter-spacing: .12em; color: var(--muted-light); }
.detail-block p { font-size: 8px; line-height: 1.55; color: var(--muted); }
.detail-block code { font-size: 7.5px; line-height: 1.55; color: var(--ink-soft); word-break: break-all; background: rgba(16,35,29,.04); padding: 4px 6px; border-radius: 2px; }
.raw-details summary { font-size: 7.5px; color: var(--muted); cursor: pointer; }
.raw-details pre { max-height: 190px; overflow: auto; background: var(--ink); color: rgba(244,239,229,.8); padding: 9px; font-size: 7px; line-height: 1.55; border-radius: 3px; margin-top: 5px; }
</style>
