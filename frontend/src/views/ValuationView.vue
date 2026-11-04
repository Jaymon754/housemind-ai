<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Building2,
  CheckCircle2,
  ChevronDown,
  Info,
  Layers3,
  Printer,
  RefreshCcw,
  Save,
  Sparkles,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
} from 'lucide-vue-next'
import { api } from '@/api'
import type { ValuationResult, Contribution } from '@/types'
import { useAppStore } from '@/stores/app'
import { useAnalysisStore } from '@/stores/analysis'
import { useToastStore } from '@/stores/toast'
import { num, usd, pct, signedUsd } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import ZipSelect from '@/components/ZipSelect.vue'

const app = useAppStore()
const store = useAnalysisStore()
const toast = useToastStore()

interface FormState {
  zipcode: string
  sqft_living: number
  sqft_lot: number
  bedrooms: number
  bathrooms: number
  floors: number
  condition: number
  grade: number
  yr_built: number
  yr_renovated: number
  waterfront: boolean
  view: number
  sqft_basement: number
  asking_price: number
}

const defaults: FormState = {
  zipcode: '98115',
  sqft_living: 1840,
  sqft_lot: 6000,
  bedrooms: 3,
  bathrooms: 2,
  floors: 1,
  condition: 3,
  grade: 7,
  yr_built: 1962,
  yr_renovated: 0,
  waterfront: false,
  view: 0,
  sqft_basement: 0,
  asking_price: 599000,
}

const form = reactive<FormState>({ ...defaults })
const result = ref<ValuationResult | null>(null)
const analyzing = ref(false)
const error = ref('')
const showAdvanced = ref(false)
const expandShap = ref(false)
const saving = ref(false)
const resultRef = ref<HTMLElement | null>(null)
const hasAutoRun = ref(false)

const zipOptions = computed(() => app.meta?.zipcodes ?? [])
const selectedZip = computed(() => zipOptions.value.find((z) => z.zipcode === form.zipcode))

function hydrate(input: Record<string, unknown>) {
  form.zipcode = String(input.zipcode ?? defaults.zipcode)
  form.sqft_living = Number(input.sqft_living ?? defaults.sqft_living)
  form.sqft_lot = Number(input.sqft_lot ?? defaults.sqft_lot)
  form.bedrooms = Number(input.bedrooms ?? defaults.bedrooms)
  form.bathrooms = Number(input.bathrooms ?? defaults.bathrooms)
  form.floors = Number(input.floors ?? defaults.floors)
  form.condition = Number(input.condition ?? defaults.condition)
  form.grade = Number(input.grade ?? defaults.grade)
  form.yr_built = Number(input.yr_built ?? defaults.yr_built)
  form.yr_renovated = Number(input.yr_renovated ?? 0)
  form.waterfront = Number(input.waterfront ?? 0) === 1
  form.view = Number(input.view ?? 0)
  form.sqft_basement = Number(input.sqft_basement ?? 0)
  form.asking_price = Number(input.asking_price ?? 0)
}

function validate(): string {
  if (!/^\d{5}$/.test(form.zipcode)) return '请选择有效的 5 位邮编'
  if (form.sqft_living < 300 || form.sqft_living > 12000) return '室内面积需在 300–12,000 sqft 之间'
  if (form.sqft_lot < 500) return '土地面积过小，请检查输入'
  if (form.bedrooms < 1 || form.bedrooms > 10) return '卧室数量需在 1–10 之间'
  if (form.bathrooms < 0.5 || form.bathrooms > 8) return '卫浴数量需在 0.5–8 之间'
  if (form.yr_built < 1900 || form.yr_built > 2015) return '建造年份需在 1900–2015 之间'
  if (form.yr_renovated && form.yr_renovated < form.yr_built) return '翻新年份不能早于建造年份'
  if (form.asking_price && form.asking_price < 10000) return '挂牌价过低，请检查输入'
  return ''
}

function payload() {
  return {
    ...form,
    waterfront: form.waterfront ? 1 : 0,
    asking_price: form.asking_price > 0 ? form.asking_price : null,
  }
}

async function analyze(scroll = false) {
  error.value = validate()
  if (error.value) {
    toast.push(error.value, 'error')
    return
  }
  analyzing.value = true
  try {
    const [response] = await Promise.all([
      api.valuation(payload()),
      new Promise((resolve) => window.setTimeout(resolve, 760)),
    ])
    result.value = response
    store.setValuation(response)
    if (scroll) {
      window.setTimeout(() => resultRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '估值失败，请稍后重试'
    toast.push(error.value, 'error')
  } finally {
    analyzing.value = false
  }
}

async function saveReport() {
  if (!result.value) return
  saving.value = true
  try {
    await api.saveReport({
      kind: 'valuation',
      title: `估值报告 · ${form.zipcode} · ${usd(result.value.estimate.value)}`,
      payload: result.value as unknown as Record<string, unknown>,
    })
    toast.push('估值报告已保存，可在打印视图中导出 PDF', 'success')
  } catch (err) {
    toast.push(err instanceof Error ? err.message : '报告保存失败', 'error')
  } finally {
    saving.value = false
  }
}

function resetForm() {
  Object.assign(form, defaults)
  analyze(true)
}

function stepBeds(delta: number) {
  form.bedrooms = Math.min(10, Math.max(1, form.bedrooms + delta))
}
function stepBaths(delta: number) {
  form.bathrooms = Math.min(8, Math.max(0.5, Math.round((form.bathrooms + delta) * 2) / 2))
}

onMounted(async () => {
  await app.load()
  if (store.valuation) {
    result.value = store.valuation
    hydrate(store.valuation.input as Record<string, unknown>)
    hasAutoRun.value = true
  }
  if (!hasAutoRun.value) {
    hasAutoRun.value = true
    await analyze()
  }
})

const estimate = computed(() => result.value?.estimate)
const assessment = computed(() => result.value?.assessment)
const confidence = computed(() => result.value?.confidence)
const market = computed(() => result.value?.market)
const contributions = computed(() => result.value?.explanation.contributions ?? [])
const hiddenCount = computed(() => Math.max(0, contributions.value.length - 9))
const otherContribution = computed(() =>
  contributions.value.slice(9).reduce((sum, item) => sum + item.amount, 0),
)
const shapRows = computed<Contribution[]>(() => {
  if (expandShap.value) return contributions.value
  const rows = contributions.value.slice(0, 9)
  if (hiddenCount.value > 0) {
    return [
      ...rows,
      {
        feature: 'other',
        label: `其余 ${hiddenCount.value} 项合计`,
        value: null,
        value_display: '合并显示',
        amount: otherContribution.value,
        direction: otherContribution.value >= 0 ? 'positive' : 'negative',
        share_pct: 0,
      },
    ]
  }
  return rows
})
const maxAbs = computed(() => Math.max(1, ...shapRows.value.map((row) => Math.abs(row.amount))))
const confidenceDash = computed(() => 2 * Math.PI * 46 * ((confidence.value?.score ?? 0) / 100))

const rangePosition = computed(() => {
  if (!estimate.value) return 50
  const { value, range_low, range_high } = estimate.value
  return Math.min(97, Math.max(3, ((value - range_low) / Math.max(1, range_high - range_low)) * 100))
})
const askingPosition = computed(() => {
  if (!assessment.value || !estimate.value) return null
  const { range_low, range_high } = estimate.value
  return Math.min(99, Math.max(1, ((assessment.value.asking_price - range_low) / Math.max(1, range_high - range_low)) * 100))
})
const intervalWidthPct = computed(() => {
  if (!estimate.value) return 0
  return ((estimate.value.range_high - estimate.value.range_low) / estimate.value.value) * 100
})
const toneClass = computed(() => {
  const tone = assessment.value?.tone
  return tone ? `tone-${tone}` : 'tone-none'
})

function printReport() {
  window.print()
}
</script>

<template>
  <div class="page valuation-page">
    <PageHeader
      eyebrow="VALUATION STUDIO / 02"
      title="价格，是一个<em>区间</em>，不是一个数字。"
      lede="XGBoost 给出点估计，5 折袋外残差校准 80% 参考区间，TreeSHAP 拆解每一项特征。输入真实房源参数，得到可核对、可质疑的估值。"
    >
      <template #actions>
        <button class="btn btn-ghost" :disabled="!result || saving" @click="saveReport">
          <Save :size="14" />
          {{ saving ? '保存中' : '保存报告' }}
        </button>
        <button class="btn btn-primary" :disabled="!result" @click="printReport">
          <Printer :size="14" />
          打印 / PDF
        </button>
      </template>
    </PageHeader>

    <div class="valuation-layout">
      <aside class="form-panel card no-print">
        <div class="form-head">
          <div>
            <div class="card-label">SUBJECT PROPERTY</div>
            <h2 class="card-title">房源参数</h2>
          </div>
          <button class="icon-btn" title="重置为示例房源" @click="resetForm"><RefreshCcw :size="15" /></button>
        </div>

        <div class="form-grid">
          <div class="field full">
            <label class="field-label">邮编 <span class="hint">King County</span></label>
            <ZipSelect v-model="form.zipcode" :options="zipOptions" />
            <div v-if="selectedZip" class="zip-hint">
              区域中位价 {{ usd(selectedZip.median_price) }} · {{ selectedZip.count }} 套样本
            </div>
          </div>

          <div class="field full">
            <label class="field-label">室内面积 <span class="hint">sqft</span></label>
            <div class="input-suffix">
              <input v-model.number="form.sqft_living" class="input" type="number" min="300" max="12000" step="10" />
              <span class="suffix">SQFT</span>
            </div>
          </div>

          <div class="field">
            <label class="field-label">卧室</label>
            <div class="stepper">
              <button type="button" aria-label="减少卧室" @click="stepBeds(-1)">−</button>
              <span>{{ form.bedrooms }}</span>
              <button type="button" aria-label="增加卧室" @click="stepBeds(1)">+</button>
            </div>
          </div>

          <div class="field">
            <label class="field-label">卫浴</label>
            <div class="stepper">
              <button type="button" aria-label="减少卫浴" @click="stepBaths(-0.5)">−</button>
              <span>{{ form.bathrooms }}</span>
              <button type="button" aria-label="增加卫浴" @click="stepBaths(0.5)">+</button>
            </div>
          </div>

          <div class="field">
            <label class="field-label">土地面积 <span class="hint">sqft</span></label>
            <input v-model.number="form.sqft_lot" class="input" type="number" min="500" step="100" />
          </div>

          <div class="field">
            <label class="field-label">建造年份</label>
            <input v-model.number="form.yr_built" class="input" type="number" min="1900" max="2015" />
          </div>

          <div class="field full">
            <label class="field-label">房屋状况 <span class="hint">1 差 · 5 优</span></label>
            <div class="condition-pills">
              <button
                v-for="level in 5"
                :key="level"
                type="button"
                :class="{ active: form.condition === level }"
                @click="form.condition = level"
              >
                <span>{{ level }}</span>
                <small>{{ ['差', '一般', '平均', '良好', '优秀'][level - 1] }}</small>
              </button>
            </div>
          </div>

          <div class="field full">
            <label class="field-label">建筑等级 <span class="range-value">{{ form.grade }} 级</span></label>
            <input
              v-model.number="form.grade"
              type="range"
              min="1"
              max="13"
              step="1"
              :style="{ '--fill': `${((form.grade - 1) / 12) * 100}%` }"
            />
            <div class="range-row"><span>1 · 简易</span><span>7 · 平均</span><span>13 · 定制</span></div>
          </div>
        </div>

        <button class="advanced-toggle" type="button" @click="showAdvanced = !showAdvanced">
          <Layers3 :size="14" />
          更多房屋特征
          <ChevronDown :size="14" :class="{ rotated: showAdvanced }" />
        </button>

        <Transition name="expand">
          <div v-if="showAdvanced" class="advanced-fields">
            <div class="form-grid">
              <div class="field">
                <label class="field-label">楼层</label>
                <select v-model.number="form.floors" class="select">
                  <option :value="1">1 层</option>
                  <option :value="1.5">1.5 层</option>
                  <option :value="2">2 层</option>
                  <option :value="2.5">2.5 层</option>
                  <option :value="3">3 层</option>
                </select>
              </div>
              <div class="field">
                <label class="field-label">景观等级</label>
                <select v-model.number="form.view" class="select">
                  <option :value="0">无景观</option>
                  <option :value="1">一般</option>
                  <option :value="2">较好</option>
                  <option :value="3">优质</option>
                  <option :value="4">顶级</option>
                </select>
              </div>
              <div class="field">
                <label class="field-label">翻新年份 <span class="hint">0 = 未翻新</span></label>
                <input v-model.number="form.yr_renovated" class="input" type="number" min="0" max="2015" />
              </div>
              <div class="field">
                <label class="field-label">地下室面积 <span class="hint">sqft</span></label>
                <input v-model.number="form.sqft_basement" class="input" type="number" min="0" step="50" />
              </div>
            </div>
            <div class="switch-row">
              <div class="switch-copy">
                <strong>滨水物业</strong>
                <small>样本稀少，估值不确定性会上升</small>
              </div>
              <button class="switch" :class="{ on: form.waterfront }" type="button" role="switch" :aria-checked="form.waterfront" @click="form.waterfront = !form.waterfront" />
            </div>
          </div>
        </Transition>

        <div class="asking-box">
          <div class="asking-head">
            <label class="field-label" for="asking">挂牌价 <span class="hint">选填</span></label>
            <Info :size="12" />
          </div>
          <div class="input-suffix">
            <input id="asking" v-model.number="form.asking_price" class="input" type="number" min="0" step="1000" placeholder="留空则跳过议价判断" />
            <span class="suffix">USD</span>
          </div>
          <p>填写后，系统会判断挂牌价是否落在模型 80% 参考区间内。</p>
        </div>

        <button class="btn btn-primary btn-block analyze-btn" :disabled="analyzing" @click="analyze(true)">
          <span v-if="analyzing" class="spinner light" />
          <Sparkles v-else :size="15" />
          {{ analyzing ? '正在推演' : result ? '重新估值' : '开始估值' }}
          <ArrowRight v-if="!analyzing" :size="15" />
        </button>
        <p v-if="error" class="form-error"><TriangleAlert :size="12" /> {{ error }}</p>
        <p class="form-disclaimer">结果为历史样本下的统计估计，不构成正式评估或投资建议。</p>
      </aside>

      <section ref="resultRef" class="result-column">
        <div v-if="analyzing && !result" class="result-loading card">
          <div class="loading-orbit">
            <span class="orbit-ring" />
            <span class="orbit-core"><Building2 :size="22" /></span>
          </div>
          <div class="loading-title">模型正在读取这套房子的特征</div>
          <div class="loading-steps">
            <span class="active">匹配邻里市场</span>
            <span>运行 XGBoost</span>
            <span>计算 TreeSHAP</span>
          </div>
          <div class="skeleton" style="width: 62%; height: 58px; margin-top: 22px" />
          <div class="skeleton" style="width: 44%; height: 12px; margin-top: 12px" />
        </div>

        <template v-else-if="result && estimate">
          <div class="result-toolbar">
            <div>
              <span class="result-live"><span class="live-dot" /> MODEL OUTPUT</span>
              <span class="result-time">生成于 {{ new Date(estimate.generated_at).toLocaleString('zh-CN') }}</span>
            </div>
            <RouterLink to="/investment" class="link-arrow">用这个价格测算投资 <ArrowUpRight :size="13" /></RouterLink>
          </div>

          <div class="estimate-hero">
            <div class="hero-main">
              <div class="hero-kicker">ESTIMATED SALE PRICE · 80% INTERVAL</div>
              <div class="estimate-number">
                <span class="estimate-currency">$</span>{{ num(estimate.value) }}
              </div>
              <div class="estimate-sub">
                <span>{{ usd(estimate.range_low) }} — {{ usd(estimate.range_high) }}</span>
                <span class="estimate-dot" />
                <span>${{ num(estimate.price_per_sqft) }} / sqft</span>
                <span class="estimate-dot" />
                <span>{{ form.bedrooms }} bd · {{ form.bathrooms }} ba · {{ num(form.sqft_living) }} sqft</span>
              </div>

              <div class="range-visual">
                <div class="range-labels">
                  <span>P10 {{ usd(estimate.range_low) }}</span>
                  <span>点估计</span>
                  <span>P90 {{ usd(estimate.range_high) }}</span>
                </div>
                <div class="range-track">
                  <span class="range-fill" />
                  <span class="range-point" :style="{ left: `${rangePosition}%` }"><i /></span>
                  <span v-if="askingPosition !== null" class="asking-marker" :style="{ left: `${askingPosition}%` }">
                    <b>挂牌</b>
                  </span>
                </div>
                <div class="range-foot">
                  <span>区间宽度约为点估计的 {{ pct(intervalWidthPct) }}</span>
                  <span>5 折 OOF 残差分位校准</span>
                </div>
              </div>
            </div>

            <div class="hero-side">
              <div class="confidence-ring">
                <svg viewBox="0 0 112 112" width="112" height="112">
                  <circle cx="56" cy="56" r="46" fill="none" stroke="rgba(244,239,229,.12)" stroke-width="2" />
                  <circle
                    cx="56" cy="56" r="46" fill="none" stroke="var(--gold-light)" stroke-width="2.4"
                    stroke-linecap="round" :stroke-dasharray="`${confidenceDash} 999`"
                    transform="rotate(-90 56 56)"
                  />
                </svg>
                <div class="confidence-center">
                  <strong>{{ confidence?.score }}</strong>
                  <span>CONFIDENCE</span>
                </div>
              </div>
              <div class="confidence-label">{{ confidence?.label }}置信度</div>
              <ul class="confidence-basis">
                <li v-for="basis in confidence?.basis" :key="basis">{{ basis }}</li>
              </ul>
            </div>
            <div class="hero-watermark">HM</div>
          </div>

          <div v-if="assessment" class="assessment-bar" :class="toneClass">
            <div class="assessment-icon">
              <BadgeCheck v-if="assessment.tone === 'fair'" :size="19" />
              <TrendingUp v-else-if="assessment.tone === 'underpriced'" :size="19" />
              <TrendingDown v-else :size="19" />
            </div>
            <div class="assessment-copy">
              <div class="assessment-title">{{ assessment.verdict }}</div>
              <p>{{ assessment.message }}</p>
            </div>
            <div class="assessment-number">
              <span>挂牌价 {{ usd(assessment.asking_price) }}</span>
              <strong>{{ assessment.difference >= 0 ? '+' : '−' }}{{ usd(Math.abs(assessment.difference)) }}</strong>
              <small>{{ assessment.difference_pct >= 0 ? '+' : '' }}{{ pct(assessment.difference_pct) }} vs 模型</small>
            </div>
          </div>
          <div v-else class="assessment-bar tone-none">
            <div class="assessment-icon"><Info :size="19" /></div>
            <div class="assessment-copy">
              <div class="assessment-title">想知道挂牌价是否合理？</div>
              <p>在左侧填写挂牌价，系统会判断它是否落在模型 80% 参考区间内，并给出议价方向。</p>
            </div>
          </div>

          <div class="grid grid-12 mt-16">
            <div class="span-7 card shap-card">
              <div class="card-head">
                <div>
                  <div class="card-label">TREE SHAP / LOCAL EXPLANATION</div>
                  <h3 class="card-title">这个价格由什么构成？</h3>
                  <p class="card-sub">从模型基准价出发，每一项特征把价格推向更高或更低。</p>
                </div>
                <span class="badge badge-outline">精确 Shapley</span>
              </div>

              <div class="shap-summary">
                <div><span>基准价</span><strong>{{ usd(result.explanation.base_value) }}</strong></div>
                <ArrowRight :size="15" />
                <div><span>最终估值</span><strong class="gold">{{ usd(result.explanation.prediction) }}</strong></div>
                <div class="shap-net" :class="result.explanation.prediction - result.explanation.base_value >= 0 ? 'positive' : 'negative'">
                  {{ signedUsd(result.explanation.prediction - result.explanation.base_value) }}
                </div>
              </div>

              <div class="shap-chart">
                <div class="shap-axis"><span>− 拉低</span><span>0</span><span>推高 +</span></div>
                <div v-for="row in shapRows" :key="row.feature" class="shap-row" :title="`${row.label} ${row.value_display}`">
                  <div class="shap-label">
                    <strong>{{ row.label }}</strong>
                    <small>{{ row.value_display }}</small>
                  </div>
                  <div class="shap-bar-area">
                    <span class="shap-zero" />
                    <span
                      class="shap-bar"
                      :class="row.amount >= 0 ? 'pos' : 'neg'"
                      :style="row.amount >= 0
                        ? { left: '50%', width: `${(Math.abs(row.amount) / maxAbs) * 48}%` }
                        : { right: '50%', width: `${(Math.abs(row.amount) / maxAbs) * 48}%` }"
                    />
                  </div>
                  <div class="shap-amount" :class="row.amount >= 0 ? 'positive' : 'negative'">{{ signedUsd(row.amount) }}</div>
                </div>
              </div>
              <button class="shap-toggle" type="button" @click="expandShap = !expandShap">
                {{ expandShap ? '收起特征清单' : `展开全部 ${contributions.length} 项特征` }}
                <ChevronDown :size="12" :class="{ rotated: expandShap }" />
              </button>
              <p class="shap-note">{{ result.explanation.narrative }}</p>
            </div>

            <div class="span-5 stack">
              <div class="card market-mini">
                <div class="card-head">
                  <div>
                    <div class="card-label">NEIGHBOURHOOD CONTEXT</div>
                    <h3 class="card-title">{{ market?.zipcode }} · {{ market?.region }}</h3>
                  </div>
                  <span class="badge badge-outline">{{ market?.sales_count }} 套样本</span>
                </div>
                <div class="market-numbers">
                  <div><span>邮编中位价</span><strong>{{ usd(market?.median_price) }}</strong></div>
                  <div><span>中位单价</span><strong>${{ num(market?.median_ppsf) }}</strong></div>
                  <div><span>样本期趋势</span><strong :class="(market?.trend_pct_sample_period ?? 0) >= 0 ? 'positive' : 'negative'">{{ (market?.trend_pct_sample_period ?? 0) >= 0 ? '+' : '' }}{{ pct(market?.trend_pct_sample_period) }}</strong></div>
                </div>
                <div class="percentile">
                  <div class="percentile-head"><span>预测单价在邮编内的分位</span><strong>{{ pct(market?.ppsf_percentile) }}</strong></div>
                  <div class="percentile-track">
                    <span class="percentile-fill" :style="{ width: `${market?.ppsf_percentile ?? 0}%` }" />
                    <span class="percentile-marker" :style="{ left: `${market?.ppsf_percentile ?? 0}%` }" />
                  </div>
                  <div class="percentile-foot"><span>低价</span><span>中位</span><span>高价</span></div>
                </div>
                <p class="card-caption">{{ market?.trend_note }}</p>
              </div>

              <div class="card whatif-card">
                <div class="card-head">
                  <div>
                    <div class="card-label">COUNTERFACTUAL</div>
                    <h3 class="card-title">如果改变一个条件</h3>
                  </div>
                </div>
                <div class="whatif-list">
                  <div v-for="item in result.explanation.what_if" :key="item.label" class="whatif-row">
                    <span>{{ item.label }}</span>
                    <strong :class="item.delta >= 0 ? 'positive' : 'negative'">{{ signedUsd(item.delta) }}</strong>
                    <small>{{ item.delta_pct >= 0 ? '+' : '' }}{{ pct(item.delta_pct) }}</small>
                  </div>
                </div>
                <p class="card-caption">反事实由同一模型即时重算，仅改变一个变量，不代表真实改造收益。</p>
              </div>
            </div>
          </div>

          <div class="card comps-card mt-16">
            <div class="card-head">
              <div>
                <div class="card-label">COMPARABLE SALES</div>
                <h3 class="card-title">最相似的真实成交</h3>
                <p class="card-sub">按面积、房型、等级、距离与邮编综合匹配，展示 6 套样本。</p>
              </div>
              <span class="badge badge-gold">非自动估价师意见</span>
            </div>
            <div class="comps-table-wrap">
              <table class="data-table comps-table">
                <thead>
                  <tr><th>成交价</th><th>面积 / 房型</th><th>单价</th><th>等级</th><th>距离</th><th>成交时间</th><th>相似度</th></tr>
                </thead>
                <tbody>
                  <tr v-for="comp in result.comparables" :key="`${comp.sold_at}-${comp.price}-${comp.sqft_living}`">
                    <td class="strong">{{ usd(comp.price) }}</td>
                    <td>{{ num(comp.sqft_living) }} sqft · {{ comp.bedrooms }}b/{{ comp.bathrooms }}ba</td>
                    <td>${{ num(comp.price_per_sqft) }}</td>
                    <td>{{ comp.grade }}</td>
                    <td>{{ comp.distance_miles }} mi</td>
                    <td>{{ comp.sold_at }}</td>
                    <td><span class="similarity"><i><b :style="{ width: `${comp.similarity}%` }" /></i>{{ comp.similarity }}%</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="result.warnings.length" class="warnings mt-16">
            <div class="warnings-head"><TriangleAlert :size="15" /> 需要特别留意</div>
            <ul><li v-for="warning in result.warnings" :key="warning">{{ warning }}</li></ul>
          </div>

          <div class="assumptions mt-16">
            <div class="assumptions-title"><CheckCircle2 :size="14" /> 模型假设与边界</div>
            <div class="assumption-grid">
              <p v-for="item in result.assumptions" :key="item">{{ item }}</p>
            </div>
            <div class="model-stamp">
              <span>{{ result.model.name }} v{{ result.model.version }}</span>
              <span>MAE {{ usd(result.model.mae) }}</span>
              <span>R² {{ result.model.r2.toFixed(4) }}</span>
              <span>训练于 {{ result.model.trained_at.slice(0, 10) }}</span>
              <span>{{ result.model.test_rows.toLocaleString() }} 条测试样本</span>
            </div>
          </div>
        </template>

        <div v-else class="card">
          <div class="empty">
            <div class="empty-icon"><Building2 :size="20" /></div>
            <strong>填写左侧房源参数</strong>
            <p>模型会返回价格区间、置信度、SHAP 归因、可比成交与议价判断。</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.valuation-layout { display: grid; grid-template-columns: 342px minmax(0, 1fr); gap: 20px; align-items: start; }
.form-panel { position: sticky; top: 93px; padding: 21px; }
.form-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }
.form-head .icon-btn { color: var(--muted); }
.zip-hint { font-size: 8.5px; color: var(--muted); margin-top: -1px; }
.condition-pills { display: grid; grid-template-columns: repeat(5, 1fr); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
.condition-pills button { background: rgba(251,248,241,.6); border-right: 1px solid var(--line); padding: 7px 2px 6px; display: flex; flex-direction: column; align-items: center; gap: 1px; transition: background .18s, color .18s; }
.condition-pills button:last-child { border-right: 0; }
.condition-pills button span { font-family: var(--font-serif); font-size: 15px; line-height: 1; color: var(--muted); }
.condition-pills button small { font-size: 7.5px; color: var(--muted-light); }
.condition-pills button:hover { background: rgba(176,138,82,.07); }
.condition-pills button.active { background: var(--ink); }
.condition-pills button.active span, .condition-pills button.active small { color: var(--paper); }
.advanced-toggle { width: 100%; display: flex; align-items: center; gap: 7px; background: transparent; border: 0; border-top: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); padding: 12px 1px; margin: 17px 0 4px; font-size: 10px; font-weight: 600; color: var(--ink-soft); }
.advanced-toggle svg:last-child { margin-left: auto; transition: transform .2s; }
.rotated { transform: rotate(180deg); }
.advanced-fields { overflow: hidden; }
.advanced-fields .form-grid { padding-top: 11px; }
.expand-enter-active, .expand-leave-active { transition: opacity .2s, max-height .3s; max-height: 300px; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.asking-box { margin-top: 17px; padding: 12px; background: rgba(234,226,212,.38); border: 1px solid var(--line); border-radius: 3px; }
.asking-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; color: var(--muted); }
.asking-box .field-label { color: var(--ink-soft); }
.asking-box p { margin-top: 6px; font-size: 8px; line-height: 1.55; color: var(--muted); }
.analyze-btn { margin-top: 16px; height: 43px; }
.form-error { display: flex; gap: 5px; align-items: flex-start; font-size: 9px; line-height: 1.5; color: var(--negative); margin-top: 8px; }
.form-disclaimer { font-size: 7.5px; line-height: 1.6; text-align: center; color: var(--muted-light); margin-top: 9px; }

.result-column { min-width: 0; scroll-margin-top: 90px; }
.result-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 8px; letter-spacing: .1em; }
.result-live { color: var(--muted); display: inline-flex; align-items: center; gap: 6px; }
.live-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--positive); box-shadow: 0 0 0 3px rgba(77,127,98,.1); }
.result-time { margin-left: 12px; color: var(--muted-light); letter-spacing: 0; }
.estimate-hero { position: relative; background: var(--ink); color: var(--paper); border-radius: 5px; padding: 30px 30px 23px; display: grid; grid-template-columns: 1fr 166px; gap: 26px; overflow: hidden; }
.estimate-hero::before { content: ''; position: absolute; left: -10%; bottom: -45%; width: 70%; height: 110%; background: radial-gradient(ellipse, rgba(176,138,82,.13), transparent 65%); pointer-events: none; }
.hero-main { position: relative; z-index: 1; min-width: 0; }
.hero-kicker { font-size: 8px; letter-spacing: .2em; color: var(--gold-light); }
.estimate-number { font-family: var(--font-serif); font-size: clamp(52px, 5.4vw, 78px); font-weight: 430; letter-spacing: -.055em; line-height: 1; margin-top: 15px; white-space: nowrap; font-variant-numeric: tabular-nums; }
.estimate-currency { font-size: .48em; font-weight: 380; vertical-align: .3em; margin-right: 4px; color: var(--gold-light); }
.estimate-sub { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 10px; color: rgba(244,239,229,.56); margin-top: 12px; }
.estimate-dot { width: 2px; height: 2px; background: rgba(244,239,229,.3); border-radius: 50%; }
.range-visual { margin-top: 31px; }
.range-labels { display: flex; justify-content: space-between; font-size: 8px; color: rgba(244,239,229,.45); letter-spacing: .03em; }
.range-labels span:nth-child(2) { color: var(--gold-light); }
.range-track { position: relative; height: 2px; background: rgba(244,239,229,.15); margin: 13px 0 9px; }
.range-fill { position: absolute; left: 0; right: 0; top: 0; height: 100%; background: linear-gradient(90deg, rgba(216,188,140,.18), rgba(216,188,140,.55), rgba(216,188,140,.18)); }
.range-point { position: absolute; top: 50%; transform: translate(-50%,-50%); width: 13px; height: 13px; border-radius: 50%; border: 1px solid var(--gold-light); background: var(--ink); display: grid; place-items: center; }
.range-point i { width: 4px; height: 4px; border-radius: 50%; background: var(--gold-light); }
.asking-marker { position: absolute; top: -7px; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; }
.asking-marker::after { content: ''; width: 1px; height: 15px; background: rgba(244,239,229,.55); }
.asking-marker b { font-size: 7px; background: var(--paper); color: var(--ink); padding: 1px 4px; border-radius: 1px; letter-spacing: .08em; margin-bottom: 2px; white-space: nowrap; }
.range-foot { display: flex; justify-content: space-between; font-size: 7.5px; color: rgba(244,239,229,.32); }
.hero-side { border-left: 1px solid rgba(244,239,229,.13); padding-left: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; z-index: 1; }
.confidence-ring { position: relative; width: 112px; height: 112px; }
.confidence-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.confidence-center strong { font-family: var(--font-serif); font-size: 30px; font-weight: 450; line-height: 1; }
.confidence-center span { font-size: 6px; letter-spacing: .16em; color: rgba(244,239,229,.38); margin-top: 3px; }
.confidence-label { font-size: 9px; color: var(--paper); margin-top: 7px; letter-spacing: .08em; }
.confidence-basis { list-style: none; padding: 0; margin: 9px 0 0; display: flex; flex-direction: column; gap: 4px; width: 100%; }
.confidence-basis li { font-size: 7.5px; line-height: 1.45; color: rgba(244,239,229,.4); padding-left: 8px; position: relative; }
.confidence-basis li::before { content: '·'; position: absolute; left: 0; color: var(--gold); }
.hero-watermark { position: absolute; right: 15px; bottom: -49px; font-family: var(--font-serif); font-size: 150px; color: rgba(244,239,229,.02); line-height: 1; pointer-events: none; }

.assessment-bar { display: flex; align-items: center; gap: 13px; margin-top: 10px; padding: 14px 17px; border: 1px solid var(--line); background: rgba(251,248,241,.75); border-radius: 4px; }
.assessment-icon { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; flex: 0 0 auto; }
.assessment-bar.tone-fair .assessment-icon { background: rgba(77,127,98,.1); color: var(--positive); }
.assessment-bar.tone-overpriced .assessment-icon { background: rgba(180,107,82,.1); color: var(--negative); }
.assessment-bar.tone-underpriced .assessment-icon { background: rgba(176,138,82,.12); color: var(--gold); }
.assessment-bar.tone-none .assessment-icon { background: rgba(16,35,29,.05); color: var(--muted); }
.assessment-copy { flex: 1; min-width: 0; }
.assessment-title { font-size: 11.5px; font-weight: 680; }
.assessment-copy p { font-size: 9px; line-height: 1.55; color: var(--muted); margin-top: 2px; }
.assessment-number { display: flex; flex-direction: column; align-items: flex-end; flex: 0 0 auto; padding-left: 15px; border-left: 1px solid var(--line); }
.assessment-number span { font-size: 8px; color: var(--muted); }
.assessment-number strong { font-family: var(--font-serif); font-size: 19px; font-weight: 480; line-height: 1.1; }
.assessment-number small { font-size: 8px; color: var(--muted); }

.stack { display: flex; flex-direction: column; gap: 16px; }
.shap-summary { display: flex; align-items: center; gap: 15px; padding: 11px 13px; background: rgba(234,226,212,.35); border: 1px solid var(--line-soft); border-radius: 3px; margin-bottom: 14px; }
.shap-summary > div:not(.shap-net) { display: flex; flex-direction: column; gap: 1px; }
.shap-summary span { font-size: 7.5px; letter-spacing: .08em; color: var(--muted); }
.shap-summary strong { font-family: var(--font-serif); font-size: 18px; font-weight: 500; }
.shap-summary > svg { color: var(--muted-light); }
.shap-net { margin-left: auto; font-size: 10px; font-weight: 700; }
.shap-chart { display: flex; flex-direction: column; gap: 2px; }
.shap-axis { display: flex; justify-content: space-between; font-size: 7px; letter-spacing: .08em; color: var(--muted-light); padding: 0 0 5px; margin-left: 132px; margin-right: 68px; }
.shap-row { display: grid; grid-template-columns: 126px 1fr 62px; gap: 10px; align-items: center; padding: 5px 0; border-bottom: 1px solid rgba(16,35,29,.045); }
.shap-row:last-child { border-bottom: 0; }
.shap-label { display: flex; flex-direction: column; min-width: 0; }
.shap-label strong { font-size: 9.5px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shap-label small { font-size: 7.5px; color: var(--muted-light); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shap-bar-area { position: relative; height: 9px; background: rgba(16,35,29,.035); }
.shap-zero { position: absolute; left: 50%; top: -2px; bottom: -2px; width: 1px; background: rgba(16,35,29,.16); }
.shap-bar { position: absolute; top: 1px; height: 7px; border-radius: 1px; min-width: 2px; }
.shap-bar.pos { background: linear-gradient(90deg, var(--sage), #8fab96); }
.shap-bar.neg { background: linear-gradient(90deg, #d1a08e, var(--clay)); }
.shap-amount { font-size: 8.5px; font-weight: 650; text-align: right; font-variant-numeric: tabular-nums; }
.shap-toggle { display: inline-flex; align-items: center; gap: 4px; border: 0; background: none; padding: 8px 0 0; font-size: 8.5px; color: var(--muted); }
.shap-toggle:hover { color: var(--gold); }
.shap-note { margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--line-soft); font-size: 8.5px; line-height: 1.65; color: var(--muted); }
.market-numbers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; margin-bottom: 15px; }
.market-numbers > div { display: flex; flex-direction: column; gap: 3px; }
.market-numbers span { font-size: 7.5px; color: var(--muted); }
.market-numbers strong { font-family: var(--font-serif); font-size: 17px; font-weight: 500; }
.percentile { padding: 11px 0 8px; border-top: 1px solid var(--line-soft); }
.percentile-head { display: flex; justify-content: space-between; font-size: 8.5px; color: var(--muted); }
.percentile-head strong { color: var(--ink); }
.percentile-track { position: relative; height: 4px; background: linear-gradient(90deg, var(--paper-3), var(--gold-pale), var(--gold)); border-radius: 4px; margin: 8px 0 4px; }
.percentile-marker { position: absolute; top: 50%; width: 9px; height: 9px; border: 2px solid var(--ink); background: var(--paper-2); border-radius: 50%; transform: translate(-50%,-50%); }
.percentile-foot { display: flex; justify-content: space-between; font-size: 7px; color: var(--muted-light); }
.whatif-list { display: flex; flex-direction: column; gap: 0; }
.whatif-row { display: grid; grid-template-columns: 1fr auto 44px; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--line-soft); font-size: 9px; }
.whatif-row:last-child { border-bottom: 0; }
.whatif-row span { color: var(--muted); }
.whatif-row strong { font-size: 9.5px; font-variant-numeric: tabular-nums; }
.whatif-row small { font-size: 8px; color: var(--muted-light); text-align: right; }

.comps-table-wrap { overflow-x: auto; }
.comps-table { min-width: 640px; }
.similarity { display: flex; align-items: center; gap: 6px; font-size: 8.5px; color: var(--muted); }
.similarity i { display: block; height: 3px; width: 32px; background: var(--paper-3); border-radius: 3px; position: relative; overflow: hidden; }
.similarity i b { display: block; height: 100%; background: var(--sage); border-radius: 3px; }
.warnings { border: 1px solid rgba(180,107,82,.24); background: rgba(180,107,82,.055); padding: 14px 16px; border-radius: 4px; }
.warnings-head { display: flex; align-items: center; gap: 7px; font-size: 10px; font-weight: 650; color: #8e4e39; }
.warnings ul { margin: 7px 0 0; padding-left: 17px; }
.warnings li { font-size: 9px; line-height: 1.65; color: #7e5b4e; }
.assumptions { padding: 16px; border: 1px solid var(--line); border-radius: 4px; background: rgba(234,226,212,.22); }
.assumptions-title { display: flex; align-items: center; gap: 6px; font-size: 9.5px; font-weight: 650; }
.assumptions-title svg { color: var(--sage); }
.assumption-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 10px; }
.assumption-grid p { font-size: 8.5px; line-height: 1.65; color: var(--muted); padding-left: 9px; border-left: 1px solid var(--line); }
.model-stamp { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 13px; padding-top: 10px; border-top: 1px solid var(--line); font-size: 7.5px; letter-spacing: .05em; color: var(--muted-light); }

.result-loading { min-height: 430px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px; }
.loading-orbit { position: relative; width: 82px; height: 82px; display: grid; place-items: center; margin-bottom: 20px; }
.orbit-ring { position: absolute; inset: 0; border: 1px solid var(--line); border-top-color: var(--gold); border-radius: 50%; animation: spin 1.4s linear infinite; }
.orbit-core { width: 48px; height: 48px; border-radius: 50%; background: var(--ink); color: var(--gold-light); display: grid; place-items: center; }
.loading-title { font-family: var(--font-serif); font-size: 20px; }
.loading-steps { display: flex; gap: 17px; margin-top: 13px; font-size: 8.5px; color: var(--muted-light); }
.loading-steps span { position: relative; padding-left: 9px; }
.loading-steps span::before { content: ''; position: absolute; left: 0; top: 50%; width: 4px; height: 4px; border-radius: 50%; background: var(--line); transform: translateY(-50%); }
.loading-steps span.active { color: var(--ink); }
.loading-steps span.active::before { background: var(--gold); }

@media (max-width: 1180px) {
  .valuation-layout { grid-template-columns: 310px minmax(0, 1fr); }
  .estimate-hero { grid-template-columns: 1fr; }
  .hero-side { border-left: 0; border-top: 1px solid rgba(244,239,229,.13); padding: 17px 0 0; flex-direction: row; flex-wrap: wrap; gap: 14px; justify-content: flex-start; }
  .confidence-basis { width: auto; flex: 1; min-width: 150px; }
}
@media (max-width: 980px) {
  .valuation-layout { grid-template-columns: 1fr; }
  .form-panel { position: static; }
  .assumption-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .estimate-hero { padding: 22px 18px 18px; }
  .estimate-number { font-size: 47px; }
  .result-toolbar { flex-direction: column; align-items: flex-start; gap: 6px; }
  .assessment-bar { flex-wrap: wrap; }
  .assessment-number { border-left: 0; padding-left: 49px; align-items: flex-start; width: 100%; }
  .shap-row { grid-template-columns: 92px 1fr 55px; gap: 6px; }
  .shap-axis { margin-left: 98px; margin-right: 61px; }
  .shap-label strong { font-size: 8.5px; }
  .market-numbers strong { font-size: 15px; }
}
</style>
