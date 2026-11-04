<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string
    unit?: string
    meta?: string
    note?: string
    tone?: 'default' | 'dark'
    accent?: string
  }>(),
  { unit: '', meta: '', note: '', tone: 'default', accent: '' },
)
</script>

<template>
  <div class="metric-card" :class="tone">
    <div class="metric-label">{{ label }}</div>
    <div class="metric-value" :style="accent ? { color: accent } : undefined">
      {{ value }}<span v-if="unit" class="unit">{{ unit }}</span>
    </div>
    <div v-if="meta" class="metric-meta">{{ meta }}</div>
    <div v-if="note" class="metric-note">{{ note }}</div>
    <slot />
  </div>
</template>

<style scoped>
.metric-card { padding: 18px 19px 17px; border: 1px solid var(--line); background: #fff; border-radius: 10px; position: relative; overflow: hidden; box-shadow: var(--shadow-sm); }
.metric-card::after { display: none; }
.metric-card.dark { background: var(--ink-deep); border-color: #1e3a50; color: #f8fafc; }
.metric-card.dark .metric-label, .metric-card.dark .metric-meta, .metric-card.dark .metric-note { color: rgba(248, 250, 252, 0.5); }
.metric-card.dark .metric-value { color: #f8fafc; }
</style>
