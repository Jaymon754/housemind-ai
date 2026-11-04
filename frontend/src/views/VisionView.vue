<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowUpRight,
  Bot,
  Check,
  CheckCircle2,
  CircleAlert,
  Copy,
  Eye,
  FileImage,
  ImagePlus,
  Lock,
  RotateCcw,
  ScanEye,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from 'lucide-vue-next'
import { api } from '@/api'
import type { UploadResult, VisionResult } from '@/types'
import { useAppStore } from '@/stores/app'
import { useAnalysisStore } from '@/stores/analysis'
import { useToastStore } from '@/stores/toast'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'

const app = useAppStore()
const store = useAnalysisStore()
const toast = useToastStore()
const router = useRouter()

const result = ref<VisionResult | null>(null)
const preview = ref('')
const fileMeta = ref<{ name: string; size: number; width: number; height: number; stripped: boolean } | null>(null)
const analyzing = ref(false)
const dragging = ref(false)
const error = ref('')
const isDemo = ref(false)
const copied = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const autoLoading = ref(false)

const modeLabel = computed(() => {
  if (!result.value) return 'READY'
  if (result.value.mode === 'remote-vision') return '远程多模态'
  if (result.value.mode === 'local-fallback') return '本地回退'
  return '本地信号分析'
})
const semanticUnavailable = computed(() => result.value?.semantic.room_type.includes('无法') ?? false)
const modeTone = computed(() => (result.value?.mode === 'remote-vision' ? 'badge-sage' : 'badge-gold'))

function brightnessLabel(value: number): string {
  if (value < 0.3) return '偏暗'
  if (value < 0.45) return '略暗'
  if (value < 0.65) return '中等'
  return '明亮'
}
function contrastLabel(value: number): string {
  if (value < 0.2) return '较平'
  if (value < 0.32) return '适中'
  return '层次强'
}
function saturationLabel(value: number): string {
  if (value < 0.2) return '低饱和'
  if (value < 0.38) return '自然'
  return '色彩浓'
}
function edgeLabel(value: number): string {
  if (value < 0.15) return '细节少'
  if (value < 0.4) return '适中'
  return '细节丰富'
}

const signals = computed(() => {
  if (!result.value) return []
  const f = result.value.features
  return [
    { label: '画面亮度', value: brightnessLabel(f.brightness), detail: `${Math.round(f.brightness * 100)} / 100`, width: f.brightness * 100, tone: 'gold' },
    { label: '明暗层次', value: contrastLabel(f.contrast), detail: `${Math.round(f.contrast * 100)} / 100`, width: Math.min(100, f.contrast * 220), tone: 'sage' },
    { label: '色彩饱和', value: saturationLabel(f.saturation), detail: `${Math.round(f.saturation * 100)} / 100`, width: Math.min(100, f.saturation * 180), tone: 'clay' },
    { label: '色温倾向', value: f.temperature, detail: `偏移 ${f.warmth >= 0 ? '+' : ''}${Math.round(f.warmth * 100)}`, width: Math.round(((f.warmth + 1) / 2) * 100), tone: 'gold' },
    { label: '细节密度', value: edgeLabel(f.edge_density), detail: `${Math.round(f.edge_density * 100)} / 100`, width: Math.min(100, f.edge_density * 100), tone: 'sage' },
  ]
})

function validate(file: File): string {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return '仅支持 JPG、PNG、WebP 图片'
  if (file.size > 8 * 1024 * 1024) return '图片大小不能超过 8 MB'
  return ''
}

async function processFile(file: File, demo = false) {
  const problem = validate(file)
  if (problem) {
    toast.push(problem, 'error')
    return
  }
  analyzing.value = true
  error.value = ''
  result.value = null
  isDemo.value = demo
  fileMeta.value = null
  try {
    const upload: UploadResult = await api.uploadImage(file)
    preview.value = upload.thumbnail_url
    fileMeta.value = {
      name: demo ? 'interior-demo.jpg' : upload.filename,
      size: upload.size_kb,
      width: upload.features.width,
      height: upload.features.height,
      stripped: upload.metadata_stripped,
    }
    const analysis = await api.analyzeImage(upload.image_id)
    result.value = analysis
    store.setVision(analysis)
    preview.value = analysis.image_url
    if (!demo) toast.push('图片分析完成。所有结论仅描述可见信号。', 'success')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '图片分析失败'
    toast.push(error.value, 'error')
  } finally {
    analyzing.value = false
  }
}

function chooseFile() {
  fileInput.value?.click()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) processFile(file)
}

function onDrop(event: DragEvent) {
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) processFile(file)
}

async function loadDemo(showToast = true) {
  autoLoading.value = true
  try {
    const response = await fetch('/demo/interior.jpg')
    if (!response.ok) throw new Error('示例图片不可用')
    const blob = await response.blob()
    const file = new File([blob], 'interior-demo.jpg', { type: 'image/jpeg' })
    await processFile(file, true)
    if (showToast) toast.push('已载入示例客厅照片', 'success')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '示例图片载入失败'
    if (showToast) toast.push(error.value, 'error')
  } finally {
    autoLoading.value = false
  }
}

function reset() {
  result.value = null
  preview.value = ''
  fileMeta.value = null
  error.value = ''
  isDemo.value = false
  store.setVision(null)
}

async function copySummary() {
  if (!result.value) return
  const r = result.value
  const text = `HouseMind 图像观察（${modeLabel.value}）\n` +
    `尺寸：${r.features.width}×${r.features.height}，${r.features.orientation}\n` +
    `亮度：${brightnessLabel(r.features.brightness)}，色温：${r.features.temperature}\n` +
    `观察：${r.features.observations.join('；')}\n` +
    `边界：${r.disclaimer}`
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1800)
    toast.push('观察摘要已复制', 'success')
  } catch {
    toast.push('浏览器未授予剪贴板权限', 'error')
  }
}

function askAgent() {
  if (!result.value) return
  router.push({ path: '/agent', query: { image: result.value.image_id } })
}

onMounted(async () => {
  await app.load()
  if (store.vision) {
    result.value = store.vision
    preview.value = store.vision.image_url
    fileMeta.value = {
      name: 'previous-upload.jpg',
      size: store.vision.size_kb ?? 0,
      width: store.vision.features.width,
      height: store.vision.features.height,
      stripped: true,
    }
    return
  }
  await loadDemo(false)
})
</script>

<template>
  <div class="page vision-page">
    <PageHeader
      eyebrow="MULTIMODAL VISION / 06"
      title="看见细节，也看见<em>边界</em>。"
      lede="读取亮度、色温、构图与细节密度，把照片变成可核对的观察线索。没有配置视觉大模型时，系统不会假装能识别房间或风格。"
    >
      <template #actions>
        <span class="badge" :class="result ? modeTone : 'badge-outline'"><ScanEye :size="11" /> {{ modeLabel }}</span>
        <button class="btn btn-ghost" @click="chooseFile"><ImagePlus :size="14" /> 上传照片</button>
        <button class="btn btn-primary" @click="loadDemo(true)"><Sparkles :size="14" /> 使用示例</button>
      </template>
    </PageHeader>

    <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" class="sr-only" @change="onFileChange" />

    <div v-if="error && !result" class="card">
      <EmptyState title="图片分析暂时不可用" :description="error">
        <button class="btn btn-ghost btn-small mt-16" @click="loadDemo(true)">重新载入示例</button>
      </EmptyState>
    </div>

    <template v-else>
      <div class="vision-layout">
        <section class="visual-column">
          <div
            class="image-stage"
            :class="{ dragging, empty: !preview, analyzing }"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop"
          >
            <template v-if="preview">
              <img :src="preview" alt="待分析的房屋照片" class="subject-image" />
              <div class="image-scan-grid" />
              <div v-if="analyzing" class="scan-line" />
              <div class="image-topline">
                <span class="image-badge"><Lock :size="10" /> {{ fileMeta?.stripped ? 'EXIF STRIPPED' : 'PROCESSED LOCALLY' }}</span>
                <span class="image-badge">{{ isDemo ? 'SAMPLE IMAGE' : 'UPLOADED' }}</span>
              </div>
              <div v-if="analyzing" class="analyzing-overlay">
                <div class="analyzing-card">
                  <span class="spinner light" />
                  <div><strong>正在提取可见信号</strong><small>亮度 · 色温 · 构图 · 细节密度</small></div>
                </div>
              </div>
              <div class="image-bottomline">
                <div>
                  <strong>{{ fileMeta?.width }} × {{ fileMeta?.height }}</strong>
                  <span>{{ fileMeta?.size ? `${Math.round(fileMeta.size)} KB` : '—' }}</span>
                </div>
                <span class="image-filename">{{ fileMeta?.name }}</span>
              </div>
            </template>
            <template v-else>
              <div class="dropzone-content">
                <div class="drop-orb"><UploadCloud :size="24" /></div>
                <h2>{{ autoLoading ? '正在载入示例照片' : '拖入一张房屋照片' }}</h2>
                <p>{{ autoLoading ? '准备本地图像分析…' : '或点击选择文件 · JPG / PNG / WebP · 最大 8 MB' }}</p>
                <button class="btn btn-primary btn-small" :disabled="autoLoading" @click="chooseFile">选择照片</button>
                <div class="privacy-chips">
                  <span><Lock :size="10" /> 去除 EXIF</span>
                  <span><ShieldCheck :size="10" /> 本地存储</span>
                  <span><Eye :size="10" /> 仅可见信号</span>
                </div>
              </div>
            </template>
            <span class="corner tl" /><span class="corner tr" /><span class="corner bl" /><span class="corner br" />
          </div>

          <div class="visual-actions">
            <button class="btn btn-ghost btn-small" @click="chooseFile"><ImagePlus :size="13" /> 更换照片</button>
            <button class="btn btn-ghost btn-small" :disabled="!result" @click="copySummary">
              <Check v-if="copied" :size="13" /><Copy v-else :size="13" /> {{ copied ? '已复制' : '复制摘要' }}
            </button>
            <button class="btn btn-ghost btn-small" :disabled="analyzing" @click="reset"><RotateCcw :size="13" /> 清空</button>
            <span v-if="isDemo" class="sample-note">当前为示例客厅照片，可替换为自己的房源图</span>
          </div>

          <div v-if="result" class="card signals-card">
            <div class="card-head">
              <div>
                <div class="card-label">VISIBLE SIGNALS</div>
                <h3 class="card-title">图像信号读数</h3>
                <p class="card-sub">这些是像素级统计，不是房屋质量评分。</p>
              </div>
              <span class="badge badge-outline">LOCAL</span>
            </div>
            <div class="signal-list">
              <div v-for="signal in signals" :key="signal.label" class="signal-row">
                <div class="signal-label"><span>{{ signal.label }}</span><strong>{{ signal.value }}</strong></div>
                <div class="signal-track"><span :class="signal.tone" :style="{ width: `${signal.width}%` }" /></div>
                <small>{{ signal.detail }}</small>
              </div>
            </div>
            <div class="palette-block">
              <div class="palette-label"><span>主色提取</span><small>按像素占比排序</small></div>
              <div class="palette">
                <div v-for="color in result.features.dominant_colors" :key="color.hex" class="swatch" :title="`${color.hex} · ${color.share_pct}%`">
                  <span :style="{ background: color.hex }" />
                  <small>{{ color.hex }}</small>
                  <em>{{ color.share_pct }}%</em>
                </div>
              </div>
            </div>
            <p class="signal-note">亮度与对比度会被拍摄曝光、后期滤镜和屏幕显示影响；不能据此判断实际采光或装修品质。</p>
          </div>
        </section>

        <section class="analysis-column">
          <div v-if="analyzing && !result" class="card analysis-loading">
            <div class="skeleton" style="height: 90px" />
            <div class="skeleton" style="height: 13px; width: 55%; margin-top: 20px" />
            <div class="skeleton" style="height: 10px; width: 91%; margin-top: 12px" />
            <div class="skeleton" style="height: 10px; width: 82%; margin-top: 7px" />
            <div class="skeleton" style="height: 10px; width: 64%; margin-top: 7px" />
            <div class="skeleton" style="height: 120px; margin-top: 20px" />
          </div>

          <template v-else-if="result">
            <div class="observation-panel">
              <div class="obs-top">
                <span class="obs-kicker">OBSERVATION / {{ result.mode.toUpperCase() }}</span>
                <span class="obs-mode">{{ modeLabel }}</span>
              </div>
              <div class="obs-title">
                <template v-if="semanticUnavailable">
                  语义识别<em>未启用</em>
                </template>
                <template v-else>
                  {{ result.semantic.room_type }}<em> · {{ result.semantic.style }}</em>
                </template>
              </div>
              <p class="obs-copy">
                {{ result.semantic.capability_note || '远程多模态模型返回了房间类型、风格与可见材质；仍不能替代现场检查。' }}
              </p>
              <div class="obs-tags">
                <span>房间类型 · {{ result.semantic.room_type }}</span>
                <span>风格 · {{ result.semantic.style }}</span>
                <span v-if="semanticUnavailable">语义能力 · 未启用</span>
                <span v-else>置信度 · {{ Math.round(result.semantic.confidence * 100) }}%</span>
              </div>
              <div class="obs-watermark">EYE</div>
            </div>

            <div class="card observation-list">
              <div class="card-head">
                <div>
                  <div class="card-label">WHAT THE PIXELS SAY</div>
                  <h3 class="card-title">可见观察</h3>
                </div>
              </div>
              <ul class="obs-list">
                <li v-for="item in result.semantic.observations" :key="item"><span class="obs-dot" />{{ item }}</li>
              </ul>
      </div>

            <div class="grid grid-2 strengths-grid">
              <div class="card strength-card">
                <div class="mini-label positive"><CheckCircle2 :size="12" /> 可继续核对的线索</div>
                <ul><li v-for="item in result.semantic.strengths" :key="item">{{ item }}</li></ul>
              </div>
              <div class="card concern-card">
                <div class="mini-label negative"><CircleAlert :size="12" /> 必须现场确认</div>
                <ul><li v-for="item in result.semantic.concerns" :key="item">{{ item }}</li></ul>
              </div>
            </div>

            <div class="card checklist-card">
              <div class="card-head">
                <div>
                  <div class="card-label">NEXT SITE VISIT</div>
                  <h3 class="card-title">下次看房，重点核对</h3>
                </div>
                <span class="badge badge-outline">人工</span>
              </div>
              <div class="checklist">
                <div v-for="(item, index) in result.semantic.questions_for_viewing" :key="item" class="check-item">
                  <span>{{ String(index + 1).padStart(2, '0') }}</span>
                  <p>{{ item }}</p>
                </div>
              </div>
            </div>

            <div class="boundary-card">
              <div class="boundary-head"><ShieldCheck :size="15" /> 能力边界 / CAPABILITY BOUNDARY</div>
              <div class="boundary-grid">
                <div>
                  <strong>可以做什么</strong>
                  <p>读取拍摄画面的亮度、色温、色彩构成与细节密度；提示采光、色差与需要现场复核的线索；在本地完成基础分析。</p>
                </div>
                <div>
                  <strong>不能做什么</strong>
                  <p>判断结构安全、渗漏、霉变、电路、面积、产权或真实装修质量；单张照片也不能替代持牌房屋检查。</p>
                </div>
              </div>
              <p class="boundary-disclaimer">{{ result.disclaimer }}</p>
            </div>

            <div class="vision-cta">
              <div>
                <div class="card-label">CONTINUE WITH AGENT</div>
                <h3>把这张图和预算放在一起问。</h3>
                <p>Agent 会调用图像、估值、市场与投资工具，给出带边界的综合分析。</p>
              </div>
              <button class="btn btn-light" @click="askAgent"><Bot :size="14" /> 在 Agent 中继续 <ArrowUpRight :size="13" /></button>
            </div>
          </template>

          <div v-else class="card">
            <EmptyState title="等待一张房屋照片" description="上传后，这里会显示可见信号、语义能力状态与现场核对清单。">
              <button class="btn btn-ghost btn-small mt-16" @click="loadDemo(true)">载入示例照片</button>
            </EmptyState>
          </div>
        </section>
      </div>

      <div class="vision-foot">
        <div><FileImage :size="13" /><span>支持 JPG / PNG / WebP，上传后统一转为 JPEG 并移除 EXIF。</span></div>
        <div><Lock :size="13" /><span>本地模式图片不离开服务器；配置远程视觉模型时仅发送必要图像数据。</span></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.vision-layout { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr); gap: 18px; align-items: start; }
.visual-column, .analysis-column { min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.image-stage { position: relative; background: var(--ink); border-radius: 10px; overflow: hidden; aspect-ratio: 4 / 3; display: flex; align-items: center; justify-content: center; border: 1px solid var(--ink); }
.image-stage.empty { background: #f8fafc; border: 1px dashed #b7c7d8; }
.image-stage.dragging { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(29,90,150,.12); }
.subject-image { width: 100%; height: 100%; object-fit: cover; display: block; filter: saturate(.94) contrast(.98); }
.image-scan-grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,.055) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.055) 1px, transparent 1px); background-size: 52px 52px; pointer-events: none; mix-blend-mode: screen; }
.scan-line { position: absolute; left: 0; right: 0; top: 0; height: 2px; background: linear-gradient(90deg, transparent, var(--gold-light), transparent); box-shadow: 0 0 18px rgba(119,168,212,.75); animation: scan 2.2s ease-in-out infinite; }
@keyframes scan { 0% { top: 0; opacity: 0; } 12% { opacity: 1; } 88% { opacity: 1; } 100% { top: 100%; opacity: 0; } }
.image-topline { position: absolute; top: 11px; left: 11px; right: 11px; display: flex; justify-content: space-between; gap: 8px; }
.image-badge { display: inline-flex; align-items: center; gap: 4px; background: rgba(11,27,22,.58); color: rgba(248,250,252,.8); backdrop-filter: blur(8px); border: 1px solid rgba(248,250,252,.13); border-radius: 6px; padding: 4px 6px; font-size: 6.5px; letter-spacing: .1em; }
.image-bottomline { position: absolute; left: 11px; right: 11px; bottom: 10px; display: flex; justify-content: space-between; align-items: flex-end; color: var(--paper); }
.image-bottomline div { display: flex; flex-direction: column; gap: 1px; }
.image-bottomline strong { font-family: var(--font-serif); font-size: 15px; font-weight: 650; text-shadow: 0 1px 4px rgba(0,0,0,.4); }
.image-bottomline span { font-size: 6.5px; color: rgba(248,250,252,.65); letter-spacing: .04em; }
.image-filename { max-width: 44%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.analyzing-overlay { position: absolute; inset: 0; background: rgba(11,27,22,.45); backdrop-filter: blur(2px); display: grid; place-items: center; }
.analyzing-card { display: flex; align-items: center; gap: 11px; border: 1px solid rgba(248,250,252,.2); background: rgba(11,27,22,.67); padding: 12px 17px; border-radius: 8px; color: var(--paper); }
.analyzing-card div { display: flex; flex-direction: column; gap: 2px; }
.analyzing-card strong { font-size: 10px; font-weight: 600; }
.analyzing-card small { font-size: 7px; color: rgba(248,250,252,.5); }
.dropzone-content { text-align: center; padding: 24px; display: flex; flex-direction: column; align-items: center; }
.drop-orb { width: 53px; height: 53px; border-radius: 50%; background: var(--ink); color: var(--gold-light); display: grid; place-items: center; margin-bottom: 14px; }
.dropzone-content h2 { font-family: var(--font-serif); font-size: 24px; font-weight: 650; letter-spacing: -.025em; }
.dropzone-content p { font-size: 9px; color: var(--muted); margin-top: 5px; }
.dropzone-content .btn { margin-top: 13px; }
.privacy-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin-top: 16px; }
.privacy-chips span { display: inline-flex; align-items: center; gap: 3px; font-size: 6.5px; color: var(--muted); border: 1px solid var(--line); padding: 3px 6px; border-radius: 99px; }
.corner { position: absolute; width: 13px; height: 13px; border-color: rgba(119,168,212,.5); pointer-events: none; }
.corner.tl { top: 7px; left: 7px; border-top: 1px solid; border-left: 1px solid; }
.corner.tr { top: 7px; right: 7px; border-top: 1px solid; border-right: 1px solid; }
.corner.bl { bottom: 7px; left: 7px; border-bottom: 1px solid; border-left: 1px solid; }
.corner.br { bottom: 7px; right: 7px; border-bottom: 1px solid; border-right: 1px solid; }
.visual-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sample-note { font-size: 7px; color: var(--muted-light); margin-left: auto; }

.signals-card { padding: 18px 19px; }
.signal-list { display: flex; flex-direction: column; gap: 10px; }
.signal-row { display: grid; grid-template-columns: 1fr 53px; align-items: center; gap: 4px 10px; }
.signal-label { grid-column: 1 / -1; display: flex; justify-content: space-between; font-size: 8.5px; }
.signal-label span { color: var(--muted); }
.signal-label strong { font-weight: 650; }
.signal-track { height: 4px; background: var(--paper-3); border-radius: 7px; overflow: hidden; }
.signal-track span { display: block; height: 100%; border-radius: 7px; }
.signal-track .gold { background: linear-gradient(90deg, #d7bd91, var(--gold)); }
.signal-track .sage { background: linear-gradient(90deg, #b4c7b8, var(--sage)); }
.signal-track .clay { background: linear-gradient(90deg, #d9b2a3, var(--clay)); }
.signal-row small { font-size: 7px; color: var(--muted-light); text-align: right; }
.palette-block { border-top: 1px solid var(--line-soft); margin-top: 15px; padding-top: 12px; }
.palette-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.palette-label span { font-size: 8.5px; font-weight: 650; }
.palette-label small { font-size: 7px; color: var(--muted-light); }
.palette { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; }
.swatch { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.swatch > span { display: block; height: 28px; border-radius: 6px; border: 1px solid rgba(15,23,42,.08); }
.swatch small { font-size: 6px; color: var(--muted); letter-spacing: .03em; }
.swatch em { font-style: normal; font-size: 6px; color: var(--muted-light); }
.signal-note { margin-top: 11px; padding-top: 9px; border-top: 1px solid var(--line-soft); font-size: 7px; line-height: 1.6; color: var(--muted-light); }

.observation-panel { background: var(--ink); color: var(--paper); border-radius: 10px; padding: 23px 24px; position: relative; overflow: hidden; }
.observation-panel::after { content: ''; position: absolute; right: -50px; top: -70px; width: 240px; height: 240px; border: 1px solid rgba(119,168,212,.13); border-radius: 50%; }
.obs-top { display: flex; justify-content: space-between; gap: 12px; position: relative; z-index: 1; }
.obs-kicker { font-size: 6.5px; letter-spacing: .16em; color: var(--gold-light); }
.obs-mode { font-size: 7px; color: rgba(248,250,252,.45); border: 1px solid rgba(248,250,252,.16); padding: 2px 6px; border-radius: 99px; }
.obs-title { font-family: var(--font-serif); font-size: clamp(26px, 2.4vw, 35px); font-weight: 650; letter-spacing: -.03em; line-height: 1.1; margin-top: 17px; position: relative; z-index: 1; }
.obs-title em { color: var(--gold-light); font-weight: 380; }
.obs-copy { margin-top: 10px; font-size: 8.5px; line-height: 1.7; color: rgba(248,250,252,.52); max-width: 460px; position: relative; z-index: 1; }
.obs-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 14px; position: relative; z-index: 1; }
.obs-tags span { font-size: 6.5px; color: rgba(248,250,252,.55); border: 1px solid rgba(248,250,252,.13); padding: 3px 6px; border-radius: 6px; }
.obs-watermark { position: absolute; right: 12px; bottom: -25px; font-family: var(--font-serif); font-size: 100px; color: rgba(248,250,252,.025); line-height: 1; }
.observation-list { padding: 17px 18px; }
.obs-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 7px; }
.obs-list li { display: flex; gap: 7px; align-items: flex-start; font-size: 9px; line-height: 1.6; color: var(--muted); }
.obs-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--gold); flex: 0 0 auto; margin-top: 6px; }
.strengths-grid { gap: 10px; }
.strength-card, .concern-card { padding: 14px; }
.mini-label { display: flex; align-items: center; gap: 4px; font-size: 8px; font-weight: 650; margin-bottom: 7px; }
.mini-label.positive { color: var(--positive); }
.mini-label.negative { color: var(--negative); }
.strength-card ul, .concern-card ul { margin: 0; padding-left: 14px; }
.strength-card li, .concern-card li { font-size: 8px; line-height: 1.65; color: var(--muted); margin-bottom: 3px; }
.checklist-card { padding: 17px 18px; }
.checklist { display: flex; flex-direction: column; }
.check-item { display: flex; gap: 9px; align-items: flex-start; padding: 7px 0; border-bottom: 1px solid var(--line-soft); }
.check-item:last-child { border-bottom: 0; }
.check-item span { font-family: var(--font-serif); font-size: 12px; color: var(--gold); line-height: 1.3; flex: 0 0 auto; }
.check-item p { font-size: 8.5px; line-height: 1.55; color: var(--muted); }
.boundary-card { border: 1px solid rgba(29,90,150,.28); background: rgba(29,90,150,.055); border-radius: 8px; padding: 16px; }
.boundary-head { display: flex; align-items: center; gap: 6px; font-size: 8px; letter-spacing: .08em; color: #82622f; font-weight: 650; }
.boundary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 11px; }
.boundary-grid > div + div { border-left: 1px solid rgba(29,90,150,.2); padding-left: 14px; }
.boundary-grid strong { font-size: 8.5px; font-weight: 650; }
.boundary-grid p { font-size: 7.5px; line-height: 1.65; color: var(--muted); margin-top: 3px; }
.boundary-disclaimer { margin-top: 11px; padding-top: 9px; border-top: 1px solid rgba(29,90,150,.17); font-size: 7px; line-height: 1.55; color: var(--muted); }
.vision-cta { display: flex; align-items: center; justify-content: space-between; gap: 17px; background: var(--ink); color: var(--paper); padding: 17px 18px; border-radius: 8px; }
.vision-cta .card-label { color: var(--gold-light); }
.vision-cta h3 { font-family: var(--font-serif); font-size: 17px; font-weight: 650; margin-top: 4px; }
.vision-cta p { font-size: 7.5px; line-height: 1.55; color: rgba(248,250,252,.45); margin-top: 3px; max-width: 340px; }
.vision-cta .btn { flex: 0 0 auto; }
.analysis-loading { padding: 22px; min-height: 420px; }
.vision-foot { display: flex; justify-content: space-between; gap: 20px; margin-top: 18px; padding: 12px 2px; border-top: 1px solid var(--line); }
.vision-foot div { display: flex; align-items: flex-start; gap: 5px; font-size: 7.5px; color: var(--muted); line-height: 1.6; }
.vision-foot svg { color: var(--sage); flex: 0 0 auto; margin-top: 1px; }

@media (max-width: 1080px) {
  .vision-layout { grid-template-columns: 1fr; }
  .image-stage { aspect-ratio: 16 / 10; }
}
@media (max-width: 640px) {
  .image-stage { aspect-ratio: 4 / 3; }
  .image-stage.empty { min-height: 330px; }
  .strengths-grid { grid-template-columns: 1fr; }
  .boundary-grid { grid-template-columns: 1fr; }
  .boundary-grid > div + div { border-left: 0; border-top: 1px solid rgba(29,90,150,.2); padding-left: 0; padding-top: 9px; }
  .vision-cta { flex-direction: column; align-items: flex-start; }
  .vision-foot { flex-direction: column; gap: 7px; }
  .swatch small { font-size: 5.5px; }
  .sample-note { width: 100%; margin-left: 0; }
}
</style>
