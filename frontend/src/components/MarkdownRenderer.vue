<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const props = defineProps<{ content: string }>()
const md = new MarkdownIt({ html: false, linkify: true, breaks: true, typographer: true })
const html = computed(() =>
  DOMPurify.sanitize(md.render(props.content), {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel'],
  }),
)
</script>

<template>
  <div class="markdown" v-html="html" />
</template>

<style scoped>
.markdown { font-size: 12.5px; line-height: 1.85; color: var(--ink-soft); overflow-wrap: anywhere; }
.markdown :deep(h1), .markdown :deep(h2), .markdown :deep(h3) { font-family: var(--font-serif); font-weight: 540; letter-spacing: -0.02em; color: var(--ink); margin: 1.35em 0 0.5em; line-height: 1.25; }
.markdown :deep(h1) { font-size: 22px; }
.markdown :deep(h2) { font-size: 17px; }
.markdown :deep(h3) { font-size: 14px; }
.markdown :deep(p) { margin: 0.55em 0; }
.markdown :deep(strong) { font-weight: 700; color: var(--ink); }
.markdown :deep(ul), .markdown :deep(ol) { padding-left: 1.3em; margin: 0.6em 0; }
.markdown :deep(li) { margin: 0.3em 0; }
.markdown :deep(blockquote) { margin: 0.9em 0; padding: 8px 13px; border-left: 2px solid var(--gold); background: rgba(176, 138, 82, 0.06); color: var(--muted); }
.markdown :deep(blockquote p) { margin: 0; }
.markdown :deep(code) { background: rgba(16, 35, 29, 0.06); padding: 1px 5px; border-radius: 2px; font-size: 0.88em; }
.markdown :deep(pre) { background: var(--ink); color: var(--paper); padding: 13px; border-radius: 3px; overflow-x: auto; }
.markdown :deep(pre code) { background: none; padding: 0; color: inherit; }
.markdown :deep(a) { color: #82622f; text-decoration: underline; text-underline-offset: 2px; }
.markdown :deep(hr) { border: 0; border-top: 1px solid var(--line); margin: 1.2em 0; }
.markdown :deep(table) { width: 100%; border-collapse: collapse; font-size: 11px; margin: 0.8em 0; }
.markdown :deep(th), .markdown :deep(td) { border-bottom: 1px solid var(--line); padding: 7px 8px; text-align: left; }
</style>
