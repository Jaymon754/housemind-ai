<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, ChevronsUpDown, MapPin, Search } from 'lucide-vue-next'
import type { ZipOption } from '@/types'
import { usd } from '@/lib/format'

const props = defineProps<{ modelValue: string; options: ZipOption[]; placeholder?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const root = ref<HTMLDivElement | null>(null)
const open = ref(false)
const query = ref('')
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = q
    ? props.options.filter((o) => o.zipcode.includes(q) || o.region.toLowerCase().includes(q))
    : props.options
  return list.slice(0, 80)
})
const selected = computed(() => props.options.find((o) => o.zipcode === props.modelValue))

function choose(zip: string) {
  emit('update:modelValue', zip)
  open.value = false
  query.value = ''
}
function onFocus() {
  open.value = true
  query.value = ''
}
function onInput(event: Event) {
  open.value = true
  query.value = (event.target as HTMLInputElement).value
}
function onDocClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('mousedown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="root" class="zip-select">
    <div class="zip-input-wrap" :class="{ open }">
      <MapPin :size="14" class="zip-icon" />
      <input
        :value="open ? query : modelValue"
        :placeholder="placeholder ?? '搜索邮编或区域'"
        inputmode="numeric"
        autocomplete="off"
        aria-label="选择邮编"
        @focus="onFocus"
        @input="onInput"
        @keydown.esc="open = false"
      />
      <span v-if="!open && selected" class="zip-region">{{ selected.region }}</span>
      <ChevronsUpDown :size="12" class="zip-chevron" />
    </div>
    <Transition name="drop">
      <div v-if="open" class="zip-dropdown">
        <div class="zip-drop-head">
          <Search :size="11" />
          <span>{{ filtered.length }} 个邮编 · 仅限 King County 训练样本</span>
        </div>
        <button
          v-for="item in filtered"
          :key="item.zipcode"
          type="button"
          class="zip-option"
          :class="{ selected: item.zipcode === modelValue }"
          @click="choose(item.zipcode)"
        >
          <span class="zip-option-code">{{ item.zipcode }}</span>
          <span class="zip-option-region">{{ item.region }}</span>
          <span class="zip-option-price">{{ usd(item.median_price) }}</span>
          <Check v-if="item.zipcode === modelValue" :size="12" class="zip-check" />
        </button>
        <div v-if="!filtered.length" class="zip-none">没有匹配邮编，请检查输入。</div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.zip-select { position: relative; }
.zip-input-wrap { display: flex; align-items: center; height: 39px; border: 1px solid var(--line); background: #ffffff; border-radius: 7px; padding: 0 10px; gap: 7px; transition: border-color .2s, box-shadow .2s; }
.zip-input-wrap.open, .zip-input-wrap:focus-within { border-color: var(--gold); background: var(--paper-2); box-shadow: 0 0 0 3px rgba(29,90,150,.09); }
.zip-icon { color: var(--gold); flex: 0 0 auto; }
.zip-input-wrap input { border: 0; outline: 0; background: transparent; flex: 1; min-width: 0; font-size: 12px; letter-spacing: .04em; }
.zip-region { font-size: 8.5px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 68px; }
.zip-chevron { color: var(--muted); flex: 0 0 auto; }
.zip-dropdown { position: absolute; z-index: 50; top: calc(100% + 5px); left: 0; right: 0; background: var(--paper-2); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 18px 45px rgba(15,23,42,.16); max-height: 270px; overflow-y: auto; padding: 4px; }
.zip-drop-head { position: sticky; top: 0; z-index: 1; display: flex; align-items: center; gap: 6px; padding: 7px 8px; font-size: 8px; color: var(--muted); background: #ffffff; border-bottom: 1px solid var(--line-soft); }
.zip-option { width: 100%; display: grid; grid-template-columns: 48px 1fr auto 12px; align-items: center; gap: 8px; border: 0; background: transparent; padding: 8px; border-radius: 7px; text-align: left; }
.zip-option:hover, .zip-option.selected { background: rgba(29,90,150,.09); }
.zip-option-code { font-size: 10.5px; font-weight: 650; letter-spacing: .04em; }
.zip-option-region { font-size: 9px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.zip-option-price { font-size: 9px; color: var(--muted); font-variant-numeric: tabular-nums; }
.zip-check { color: var(--gold); }
.zip-none { padding: 18px; text-align: center; font-size: 10px; color: var(--muted); }
.drop-enter-active, .drop-leave-active { transition: opacity .15s, transform .15s; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
