<script setup lang="ts">
withDefaults(defineProps<{ size?: number; light?: boolean }>(), { size: 34, light: false })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 40 40" fill="none" aria-hidden="true" class="logo-mark">
    <rect x="1" y="1" width="38" height="38" rx="9" :fill="light ? '#ffffff' : '#0f2a43'" />
    <path d="M9.5 21.5 20 12l10.5 9.5" :stroke="light ? '#0f2a43' : '#9ec5e6'" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M13 20.5V29h14v-8.5" :stroke="light ? '#0f2a43' : '#f8fafc'" stroke-width="1.8" stroke-linejoin="round" />
    <path d="M18 29v-5.5h4V29" :stroke="light ? '#0f2a43' : '#9ec5e6'" stroke-width="1.5" />
  </svg>
</template>

<style scoped>
.logo-mark { display: block; flex: 0 0 auto; }
</style>
