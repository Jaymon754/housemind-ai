<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; lede?: string; index?: string }>()
</script>

<template>
  <header class="page-head">
    <div class="page-head-copy">
      <div class="eyebrow">{{ eyebrow }} <span v-if="index" class="head-index">{{ index }}</span></div>
      <!-- Titles are static, authored strings; inline <em> is intentional. -->
      <h1 class="display-title" v-html="title" />
      <p v-if="lede" class="page-lede">{{ lede }}</p>
    </div>
    <div class="page-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.head-index { color: var(--muted-light); border-left: 1px solid var(--line); padding-left: 8px; margin-left: 2px; }
</style>
