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
.metric-card { padding: 19px 20px 18px; border: 1px solid var(--line); background: rgba(251, 248, 241, 0.66); border-radius: 5px; position: relative; overflow: hidden; }
.metric-card::after { content: ''; position: absolute; right: -24px; top: -24px; width: 70px; height: 70px; border: 1px solid rgba(176, 138, 82, 0.16); border-radius: 50%; }
.metric-card.dark { background: var(--ink); border-color: var(--ink); color: var(--paper); }
.metric-card.dark .metric-label, .metric-card.dark .metric-meta, .metric-card.dark .metric-note { color: rgba(244, 239, 229, 0.5); }
.metric-card.dark .metric-value { color: var(--paper); }
</style>
