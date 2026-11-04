<script setup lang="ts">
withDefaults(defineProps<{ size?: number; light?: boolean }>(), { size: 34, light: false })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 40 40" fill="none" aria-hidden="true" class="logo-mark">
    <rect x="1" y="1" width="38" height="38" rx="10" :fill="light ? '#f4efe5' : '#10231d'" />
    <path d="M9.5 21.5 20 12l10.5 9.5" :stroke="light ? '#10231d' : '#d8bc8c'" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M13 20.5V29h14v-8.5" :stroke="light ? '#10231d' : '#f4efe5'" stroke-width="1.8" stroke-linejoin="round" />
    <path d="M18 29v-5.5h4V29" :stroke="light ? '#10231d' : '#d8bc8c'" stroke-width="1.5" />
  </svg>
</template>

<style scoped>
.logo-mark { display: block; flex: 0 0 auto; }
</style>
