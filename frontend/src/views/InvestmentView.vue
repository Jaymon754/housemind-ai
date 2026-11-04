<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import {
  ArrowRight,
  Calculator,
  ChevronDown,
  CircleDollarSign,
  Info,
  Landmark,
  Printer,
  RefreshCcw,
  Save,
  Scale,
  Sparkles,
  TriangleAlert,
  Wallet,
} from 'lucide-vue-next'
import { api } from '@/api'
import type { InvestmentInputs, InvestmentResult, ScenarioResponse } from '@/types'
import { useAppStore } from '@/stores/app'
import { useAnalysisStore } from '@/stores/analysis'
import { useToastStore } from '@/stores/toast'
import { usd, pct, signedUsd } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import ChartCanvas from '@/components/ChartCanvas.vue'
import { axisCommon, palette, tooltipCommon } from '@/lib/chartTheme'

const app = useAppStore()
const analysisStore = useAnalysisStore()
const toast = useToastStore()

interface Preset {
  label: string
  zipcode: string
  region: string
  purchase_price: number
  monthly_rent: number
  down_payment_pct: number
  interest_rate: number
  note: string
}

const defaults: InvestmentInputs = {
  purchase_price: 685000,
  down_payment_pct: 25,
  interest_rate: 6.5,
  loan_term_years: 30,
  monthly_rent: 3100,
  vacancy_rate_pct: 5,
  property_tax_rate_pct: 1.0,
  insurance_annual: 1800,
  hoa_monthly: 0,
  maintenance_pct: 1.0,
  closing_cost_pct: 2.5,
  rent_growth_pct: 3.0,
  appreciation_pct: 3.0,
  holding_years: 5,
}

const form = reactive<InvestmentInputs>({ ...defaults })
const result = ref<InvestmentResult | null>(null)
const scenarios = ref<ScenarioResponse | null>(null)
const presets = ref<Preset[]>([])
const calculating = ref(false)
const saving = ref(false)
const error = ref('')
const showAdvanced = ref(false)
const hasAutoRun = ref(false)

const normalized = computed<InvestmentInputs>(() => ({
  ...form,
  purchase_price: Number(form.purchase_price) || 0,
  monthly_rent: Number(form.monthly_rent) || 0,
}))

function applyPreset(preset: Preset) {
  form.purchase_price = preset.purchase_price
  form.monthly_rent = preset.monthly_rent
  form.down_payment_pct = preset.down_payment_pct
  form.interest_rate = preset.interest_rate
  calculate(true)
}

async function calculate(scroll = false) {
  if (form.purchase_price < 50000) {
    error.value = '房价需不低于 50,000 美元'
    toast.push(error.value, 'error')
    return
  }
  if (form.monthly_rent < 0) {
    error.value = '月租金不能为负'
    toast.push(error.value, 'error')
    return
  }
  error.value = ''
  calculating.value = true
  try {
    const [base, scenario] = await Promise.all([
      api.investment({ ...normalized.value }),
      api.scenarios({ base: { ...normalized.value }, rent_change_pct: 0, interest_rate_delta: 0, price_change_pct: 0 }),
      new Promise((resolve) => window.setTimeout(resolve, 620)),
    ])
    result.value = base
    scenarios.value = scenario
    if (scroll) window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '投资测算失败，请检查输入'
    toast.push(error.value, 'error')
  } finally {
    calculating.value = false
  }
}

async function saveReport() {
  if (!result.value) return
  saving.value = true
  try {
    await api.saveReport({
      kind: 'investment',
      title: `投资测算 · ${usd(result.value.inputs.purchase_price)} · 月现金流 ${usd(result.value.summary.monthly_cash_flow)}`,
      payload: result.value as unknown as Record<string, unknown>,
    })
    toast.push('投资测算已保存', 'success')
  } catch (err) {
    toast.push(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function loadPresets() {
  try {
    const data = await api.presets()
    presets.value = data.presets as unknown as Preset[]
    if (data.defaults) {
      Object.assign(form, data.defaults)
    }
    if (presets.value.length) {
      const first = presets.value[0]
      form.purchase_price = first.purchase_price
      form.monthly_rent = first.monthly_rent
      form.down_payment_pct = first.down_payment_pct
      form.interest_rate = first.interest_rate
    }
  } catch {
    /* defaults already usable */
  }
}

function useValuation() {
  const value = analysisStore.valuation?.estimate.value
  if (!value) {
    toast.push('请先在智能估值中生成一套房源', 'info')
    return
  }
  form.purchase_price = value
  form.monthly_rent = Math.round((value * 0.0052) / 50) * 50
  toast.push('已带入估值结果与 0.52% 月租假设', 'success')
  calculate()
}

function resetForm() {
  Object.assign(form, defaults)
  if (presets.value[0]) {
    const first = presets.value[0]
    form.purchase_price = first.purchase_price
    form.monthly_rent = first.monthly_rent
    form.down_payment_pct = first.down_payment_pct
    form.interest_rate = first.interest_rate
  }
  calculate(true)
}

function printReport() {
  window.print()
}

onMounted(async () => {
  await app.load()
  await loadPresets()
  if (!hasAutoRun.value) {
    hasAutoRun.value = true
    await calculate()
  }
})

const summary = computed(() => result.value?.summary)
const returns = computed(() => result.value?.returns)
const monthly = computed(() => result.value?.monthly)
const verdict = computed(() => result.value?.verdict)

const kpis = computed(() => {
  if (!result.value) return []
  return [
    {
      label: '月度净现金流',
      value: signedUsd(result.value.summary.monthly_cash_flow),
      meta: result.value.summary.monthly_cash_flow >= 0 ? '每月为正' : '每月需补贴',
      tone: result.value.summary.monthly_cash_flow >= 0 ? 'positive' : 'negative',
    },
    {
      label: 'Cap Rate',
      value: pct(result.value.returns.cap_rate_pct),
      meta: 'NOI / 购买价',
      tone: result.value.returns.cap_rate_pct >= 4 ? 'positive' : 'neutral',
    },
    {
      label: '现金回报率',
      value: pct(result.value.returns.cash_on_cash_pct),
      meta: '年现金流 / 自有资金',
      tone: result.value.returns.cash_on_cash_pct >= 0 ? 'positive' : 'negative',
    },
    {
      label: 'DSCR',
      value: result.value.returns.dscr === null ? '全现金' : `${result.value.returns.dscr.toFixed(2)}×`,
      meta: (result.value.returns.dscr ?? 99) >= 1.25 ? '高于 1.25 缓冲线' : '低于 1.25 缓冲线',
      tone: (result.value.returns.dscr ?? 99) >= 1.25 ? 'positive' : 'negative',
    },
    {
      label: `${result.value.returns.holding_years} 年 IRR`,
      value: result.value.returns.irr_pct === null ? '—' : pct(result.value.returns.irr_pct),
      meta: '含期末出售与 6% 交易成本',
      tone: (result.value.returns.irr_pct ?? 0) >= 0 ? 'positive' : 'negative',
    },
  ]
})

const cashRows = computed(() => {
  if (!monthly.value) return []
  const rows = [
    { label: '租金收入', value: monthly.value.gross_rent, kind: 'income' },
    { label: '空置损失', value: -monthly.value.vacancy_loss, kind: 'expense' },
    { label: '房产税', value: -monthly.value.property_tax, kind: 'expense' },
    { label: '保险', value: -monthly.value.insurance, kind: 'expense' },
    { label: 'HOA', value: -monthly.value.hoa, kind: 'expense' },
    { label: '维护准备金', value: -monthly.value.maintenance, kind: 'expense' },
    { label: '月供', value: -monthly.value.mortgage, kind: 'debt' },
  ]
  return rows.filter((row) => row.value !== 0)
})
const maxCash = computed(() => Math.max(1, ...cashRows.value.map((row) => Math.abs(row.value))))

const cashFlowOption = computed<EChartsOption>(() => {
  const schedule = result.value?.schedule ?? []
  return {
    animationDuration: 800,
    grid: { left: 44, right: 48, top: 28, bottom: 30 },
    tooltip: {
      ...tooltipCommon,
      trigger: 'axis',
      formatter: (params: unknown) => {
        const items = params as { seriesName: string; value: number; axisValue: string; color: string }[]
        return `<div style="font-size:9px;letter-spacing:.1em;opacity:.55">YEAR ${items[0]?.axisValue}</div>` +
          items.map((i) => `<div style="display:flex;justify-content:space-between;gap:18px;margin-top:3px"><span><i style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${i.color};margin-right:6px"></i>${i.seriesName}</span><b>${usd(i.value)}</b></div>`).join('')
      },
    },
    legend: { top: 0, right: 0, icon: 'circle', itemWidth: 5, itemHeight: 5, textStyle: { color: '#737a72', fontSize: 8.5 } },
    xAxis: { type: 'category', data: schedule.map((s) => `Y${s.year}`), ...axisCommon, axisLabel: { ...axisCommon.axisLabel, fontSize: 8.5 } },
    yAxis: [
      { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${Math.round(v / 1000)}k` } },
      { type: 'value', ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${Math.round(v / 1000)}k` } },
    ],
    series: [
      {
        name: '年度现金流',
        type: 'bar',
        data: schedule.map((s) => ({
          value: s.cash_flow,
          itemStyle: { color: s.cash_flow >= 0 ? palette.sage : palette.clay, borderRadius: [2, 2, 0, 0] },
        })),
        barWidth: '38%',
      },
      {
        name: '贷款余额',
        type: 'line',
        yAxisIndex: 1,
        data: schedule.map((s) => s.loan_balance),
        smooth: 0.2,
        showSymbol: false,
        lineStyle: { color: palette.ink, width: 1.5 },
        areaStyle: { color: 'rgba(16,35,29,.04)' },
      },
      {
        name: '累计现金流',
        type: 'line',
        data: schedule.map((s) => s.cumulative_cash_flow),
        smooth: 0.2,
        showSymbol: false,
        lineStyle: { color: palette.gold, width: 1.4, type: 'dashed' },
      },
    ],
  }
})

const sensitivityOption = computed<EChartsOption>(() => {
  const data = result.value?.sensitivity ?? []
  const rents = [...new Set(data.map((d) => d.rent))].sort((a, b) => a - b)
  const rates = [...new Set(data.map((d) => d.rate))].sort((a, b) => a - b)
  const values = data.map((d) => [rents.indexOf(d.rent), rates.indexOf(d.rate), d.monthly_cash_flow])
  const bound = Math.max(1, ...data.map((d) => Math.abs(d.monthly_cash_flow)))
  return {
    animationDuration: 600,
    grid: { left: 48, right: 16, top: 12, bottom: 46 },
    tooltip: {
      ...tooltipCommon,
      formatter: (params: unknown) => {
        const p = params as { value: number[] }
        return `<div style="font-size:9px;opacity:.55">月租 ${usd(rents[p.value[0]])} · 利率 ${rates[p.value[1]].toFixed(2)}%</div><div style="font-family:Fraunces Variable;font-size:20px;margin-top:2px">${signedUsd(p.value[2])}<span style="font-size:9px;opacity:.55"> / 月</span></div>`
      },
    },
    xAxis: {
      type: 'category',
      data: rents.map((r) => `$${Math.round(r / 100) / 10}k`),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, fontSize: 8 },
      name: '月租金',
      nameLocation: 'middle',
      nameGap: 27,
      nameTextStyle: { color: '#737a72', fontSize: 8 },
    },
    yAxis: {
      type: 'category',
      data: rates.map((r) => `${r.toFixed(2)}%`),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, fontSize: 8 },
      name: '利率',
      nameLocation: 'middle',
      nameGap: 36,
      nameTextStyle: { color: '#737a72', fontSize: 8 },
    },
    visualMap: {
      show: false,
      min: -bound,
      max: bound,
      inRange: { color: ['#b46b52', '#e4c9ba', '#f4efe5', '#b9cbbd', '#6f8a76'] },
    },
    series: [
      {
        type: 'heatmap',
        data: values,
        label: { show: true, fontSize: 7, color: 'rgba(16,35,29,.75)', formatter: (p: unknown) => { const v = (p as { value: number[] }).value[2]; return `${v >= 0 ? '+' : ''}${Math.round(v / 10) / 100}k` } },
        itemStyle: { borderColor: '#fbf8f1', borderWidth: 2, borderRadius: 2 },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(16,35,29,.2)' } },
      },
    ],
  }
})

const scenarioCards = computed(() => {
  if (!scenarios.value) return []
  return [
    { key: 'pessimistic', label: '压力情景', data: scenarios.value.pessimistic, tone: 'negative' },
    { key: 'base', label: '基准情景', data: scenarios.value.base, tone: 'base' },
    { key: 'optimistic', label: '乐观情景', data: scenarios.value.optimistic, tone: 'positive' },
  ]
})

const maxScenarioIrr = computed(() => Math.max(1, ...scenarioCards.value.map((c) => Math.abs(c.data.returns.irr_pct ?? 0))))
</script>

<template>
  <div class="page investment-page">
    <PageHeader
      eyebrow="INVESTMENT UNDERWRITING / 03"
      title="把租金，拆成<em>可验证的现金流</em>。"
      lede="月供、空置、税费、维护、DSCR 与退出假设全部摊开计算。没有“稳赚”的结论，只有不同情景下的数字与边界。"
    >
      <template #actions>
        <button class="btn btn-ghost" :disabled="!analysisStore.valuation" @click="useValuation">
          <Calculator :size="14" />
          带入估值
        </button>
        <button class="btn btn-primary" :disabled="!result" @click="printReport">
          <Printer :size="14" />
          打印 / PDF
        </button>
      </template>
    </PageHeader>

    <div v-if="presets.length" class="preset-bar no-print">
      <span class="preset-label">快速开始</span>
      <button v-for="preset in presets" :key="preset.zipcode" class="preset-chip" @click="applyPreset(preset)">
        <span>{{ preset.label }}</span>
        <small>{{ usd(preset.purchase_price) }} · {{ usd(preset.monthly_rent) }}/月</small>
      </button>
      <span class="preset-note">示例假设来自邮编中位价与 0.52% 月租，可修改</span>
    </div>

    <div class="investment-layout">
      <aside class="form-panel card no-print">
        <div class="form-head">
          <div>
            <div class="card-label">DEAL ASSUMPTIONS</div>
            <h2 class="card-title">交易假设</h2>
          </div>
          <button class="icon-btn" title="恢复默认" @click="resetForm"><RefreshCcw :size="15" /></button>
        </div>

        <div class="form-grid">
          <div class="field full">
            <label class="field-label">购买价格 <span class="hint">USD</span></label>
            <div class="input-suffix">
              <input v-model.number="form.purchase_price" class="input" type="number" min="50000" step="5000" />
              <span class="suffix">USD</span>
            </div>
          </div>
          <div class="field full">
            <label class="field-label">月租金 <span class="hint">毛租金</span></label>
            <div class="input-suffix">
              <input v-model.number="form.monthly_rent" class="input" type="number" min="0" step="50" />
              <span class="suffix">/ MO</span>
            </div>
          </div>
        </div>

        <div class="slider-field">
          <div class="range-row"><span class="field-label">首付比例</span><span class="range-value">{{ form.down_payment_pct }}%</span></div>
          <input v-model.number="form.down_payment_pct" type="range" min="0" max="100" step="1" :style="{ '--fill': `${form.down_payment_pct}%` }" />
          <div class="range-row"><span>0%</span><span>首付 {{ usd(form.purchase_price * form.down_payment_pct / 100) }}</span><span>100%</span></div>
        </div>

        <div class="form-grid">
          <div class="field">
            <label class="field-label">贷款利率 <span class="hint">%</span></label>
            <input v-model.number="form.interest_rate" class="input" type="number" min="0" max="20" step="0.125" />
          </div>
          <div class="field">
            <label class="field-label">贷款年限</label>
            <select v-model.number="form.loan_term_years" class="select">
              <option :value="15">15 年</option>
              <option :value="20">20 年</option>
              <option :value="30">30 年</option>
            </select>
          </div>
          <div class="field">
            <label class="field-label">空置率 <span class="hint">%</span></label>
            <input v-model.number="form.vacancy_rate_pct" class="input" type="number" min="0" max="50" step="0.5" />
          </div>
          <div class="field">
            <label class="field-label">房产税率 <span class="hint">% / 年</span></label>
            <input v-model.number="form.property_tax_rate_pct" class="input" type="number" min="0" max="10" step="0.05" />
          </div>
          <div class="field">
            <label class="field-label">保险 <span class="hint">USD / 年</span></label>
            <input v-model.number="form.insurance_annual" class="input" type="number" min="0" step="50" />
          </div>
          <div class="field">
            <label class="field-label">HOA <span class="hint">USD / 月</span></label>
            <input v-model.number="form.hoa_monthly" class="input" type="number" min="0" step="10" />
          </div>
          <div class="field">
            <label class="field-label">维护准备金 <span class="hint">% 房价 / 年</span></label>
            <input v-model.number="form.maintenance_pct" class="input" type="number" min="0" max="10" step="0.1" />
          </div>
          <div class="field">
            <label class="field-label">持有年限 <span class="hint">年</span></label>
            <input v-model.number="form.holding_years" class="input" type="number" min="1" max="30" />
          </div>
        </div>

        <button class="advanced-toggle" type="button" @click="showAdvanced = !showAdvanced">
          <Scale :size="14" />
          增长与退出假设
          <ChevronDown :size="14" :class="{ rotated: showAdvanced }" />
        </button>

        <Transition name="expand">
          <div v-if="showAdvanced" class="advanced-fields">
            <div class="form-grid">
              <div class="field">
                <label class="field-label">租金年增长 <span class="hint">%</span></label>
                <input v-model.number="form.rent_growth_pct" class="input" type="number" min="-10" max="20" step="0.25" />
              </div>
              <div class="field">
                <label class="field-label">房价年增值 <span class="hint">%</span></label>
                <input v-model.number="form.appreciation_pct" class="input" type="number" min="-20" max="30" step="0.25" />
              </div>
              <div class="field full">
                <label class="field-label">交易成本 <span class="hint">% 房价</span></label>
                <input v-model.number="form.closing_cost_pct" class="input" type="number" min="0" max="10" step="0.1" />
              </div>
            </div>
            <p class="advanced-note">出售成本固定按成交价 6% 估算，未计个人所得税、资本利得税与 1031 置换。</p>
          </div>
        </Transition>

        <button class="btn btn-primary btn-block calculate-btn" :disabled="calculating" @click="calculate(true)">
          <span v-if="calculating" class="spinner light" />
          <Sparkles v-else :size="15" />
          {{ calculating ? '正在测算' : '重新测算' }}
          <ArrowRight v-if="!calculating" :size="15" />
        </button>
        <p v-if="error" class="form-error"><TriangleAlert :size="12" /> {{ error }}</p>
        <p class="form-disclaimer">所有参数均可在结果中追溯。本工具不构成投资、税务或贷款建议。</p>
      </aside>

      <section class="result-column">
        <div v-if="calculating && !result" class="card result-loading">
          <div class="loading-orbit"><span class="orbit-ring" /><span class="orbit-core"><Wallet :size="21" /></span></div>
          <div class="loading-title">正在拆解每一笔现金流</div>
          <div class="skeleton" style="width: 60%; height: 50px; margin-top: 20px" />
          <div class="skeleton" style="width: 42%; height: 10px; margin-top: 12px" />
        </div>

        <template v-else-if="result && summary && returns && monthly">
          <div class="result-toolbar">
            <div>
              <span class="result-live"><span class="live-dot" /> UNDERWRITING OUTPUT</span>
              <span class="result-time">{{ result.verdict.label }} · 持有 {{ returns.holding_years }} 年</span>
            </div>
            <button class="link-arrow" :disabled="saving" @click="saveReport">
              <Save :size="13" />{{ saving ? '保存中' : '保存测算' }}
            </button>
          </div>

          <div class="verdict-panel" :class="verdict?.tone">
            <div class="verdict-left">
              <div class="verdict-kicker">BASE CASE / MONTHLY CASH FLOW</div>
              <div class="verdict-number" :class="summary.monthly_cash_flow >= 0 ? 'positive' : 'negative'">
                {{ signedUsd(summary.monthly_cash_flow) }}<span>/ 月</span>
              </div>
              <div class="verdict-label">{{ verdict?.label }}</div>
            </div>
            <div class="verdict-right">
              <p>{{ verdict?.note }}</p>
              <div class="verdict-facts">
                <div><span>自有资金投入</span><strong>{{ usd(summary.total_cash_invested) }}</strong></div>
                <div><span>盈亏平衡入住率</span><strong>{{ pct(returns.break_even_occupancy_pct) }}</strong></div>
                <div><span>退出时净回款</span><strong>{{ usd(returns.net_sale_proceeds) }}</strong></div>
              </div>
            </div>
            <div class="verdict-watermark">IRR</div>
          </div>

          <div class="kpi-grid">
            <div v-for="kpi in kpis" :key="kpi.label" class="kpi-item">
              <span class="kpi-label">{{ kpi.label }}</span>
              <strong :class="kpi.tone">{{ kpi.value }}</strong>
              <small>{{ kpi.meta }}</small>
            </div>
          </div>

          <div class="grid grid-12 mt-16">
            <div class="span-6 card">
              <div class="card-head">
                <div>
                  <div class="card-label">MONTHLY WATERFALL</div>
                  <h3 class="card-title">每月钱去了哪里</h3>
                  <p class="card-sub">从毛租金到净现金流，逐项扣除。</p>
                </div>
                <span class="badge badge-outline">USD / 月</span>
              </div>
              <div class="cash-waterfall">
                <div v-for="row in cashRows" :key="row.label" class="cash-row">
                  <span class="cash-label">{{ row.label }}</span>
                  <div class="cash-track">
                    <span
                      class="cash-bar"
                      :class="row.kind"
                      :style="{ width: `${(Math.abs(row.value) / maxCash) * 100}%` }"
                    />
                  </div>
                  <span class="cash-value" :class="row.value >= 0 ? 'positive' : 'negative'">{{ signedUsd(row.value) }}</span>
                </div>
                <div class="cash-total">
                  <span>净现金流</span>
                  <strong :class="monthly.net_cash_flow >= 0 ? 'positive' : 'negative'">{{ signedUsd(monthly.net_cash_flow) }}</strong>
                  <small>年化 {{ signedUsd(monthly.net_cash_flow * 12) }}</small>
                </div>
              </div>
            </div>

            <div class="span-6 card exit-card">
              <div class="card-head">
                <div>
                  <div class="card-label">HOLD & EXIT</div>
                  <h3 class="card-title">{{ returns.holding_years }} 年持有回报</h3>
                  <p class="card-sub">含累计现金流、还本与出售净回款。</p>
                </div>
                <span class="badge" :class="(returns.irr_pct ?? 0) >= 0 ? 'badge-sage' : 'badge-clay'">IRR {{ returns.irr_pct === null ? '—' : pct(returns.irr_pct) }}</span>
              </div>
              <div class="exit-grid">
                <div><span>初始自有资金</span><strong>{{ usd(summary.total_cash_invested) }}</strong></div>
                <div><span>{{ returns.holding_years }} 年后售价</span><strong>{{ usd(returns.sale_price) }}</strong></div>
                <div><span>出售净回款</span><strong>{{ usd(returns.net_sale_proceeds) }}</strong></div>
                <div><span>累计总利润</span><strong :class="returns.total_profit >= 0 ? 'positive' : 'negative'">{{ signedUsd(returns.total_profit) }}</strong></div>
                <div><span>总 ROI</span><strong :class="returns.total_roi_pct >= 0 ? 'positive' : 'negative'">{{ pct(returns.total_roi_pct) }}</strong></div>
                <div><span>权益倍数</span><strong>{{ returns.equity_multiple.toFixed(2) }}×</strong></div>
              </div>
              <div class="exit-bar">
                <span class="exit-bar-label">总利润 / 初始资金</span>
                <div class="exit-bar-track">
                  <span :style="{ width: `${Math.min(100, Math.abs(returns.total_roi_pct))}%` }" :class="returns.total_roi_pct >= 0 ? 'positive-fill' : 'negative-fill'" />
                </div>
                <strong>{{ pct(returns.total_roi_pct) }}</strong>
              </div>
              <div class="exit-note">
                <Info :size="12" />
                年化 ROI {{ returns.annualized_roi_pct === null ? '—' : pct(returns.annualized_roi_pct) }}；回本周期 {{ returns.payback_years === null ? '未回本' : `${returns.payback_years} 年` }}。
              </div>
            </div>
          </div>

          <div class="grid grid-12 mt-16">
            <div class="span-7 card">
              <div class="card-head">
                <div>
                  <div class="card-label">HOLDING PERIOD</div>
                  <h3 class="card-title">现金流、贷款余额与累计回收</h3>
                  <p class="card-sub">租金按输入增长率增长，运营费用按 2.5% 年增长。</p>
                </div>
              </div>
              <ChartCanvas :option="cashFlowOption" height="260px" aria-label="持有期现金流与贷款余额" />
            </div>
            <div class="span-5 card">
              <div class="card-head">
                <div>
                  <div class="card-label">SENSITIVITY / 5 × 5</div>
                  <h3 class="card-title">租金 × 利率</h3>
                  <p class="card-sub">格内为月净现金流，绿色更安全。</p>
                </div>
              </div>
              <ChartCanvas :option="sensitivityOption" height="260px" aria-label="租金与利率敏感性热力图" />
            </div>
          </div>

          <div class="card scenarios-card mt-16">
            <div class="card-head">
              <div>
                <div class="card-label">SCENARIO ANALYSIS</div>
                <h3 class="card-title">三种情景，不只看基准</h3>
                <p class="card-sub">压力情景上调空置率与利率、下调租金与增值；乐观情景反之。</p>
              </div>
              <span class="badge badge-gold">确定性规则</span>
            </div>
            <div class="scenario-grid">
              <div v-for="card in scenarioCards" :key="card.key" class="scenario-card" :class="[card.tone, { active: card.key === 'base' }]">
                <div class="scenario-head">
                  <span>{{ card.label }}</span>
                  <span v-if="card.key === 'base'" class="badge badge-ink">当前</span>
                </div>
                <div class="scenario-cf" :class="card.data.summary.monthly_cash_flow >= 0 ? 'positive' : 'negative'">
                  {{ signedUsd(card.data.summary.monthly_cash_flow) }}<small>/ 月</small>
                </div>
                <div class="scenario-stats">
                  <div><span>IRR</span><strong>{{ card.data.returns.irr_pct === null ? '—' : pct(card.data.returns.irr_pct) }}</strong></div>
                  <div><span>CoC</span><strong>{{ pct(card.data.returns.cash_on_cash_pct) }}</strong></div>
                  <div><span>DSCR</span><strong>{{ card.data.returns.dscr === null ? '—' : card.data.returns.dscr.toFixed(2) }}</strong></div>
                </div>
                <div class="scenario-bar">
                  <span :style="{ width: `${(Math.abs(card.data.returns.irr_pct ?? 0) / maxScenarioIrr) * 100}%` }" />
                </div>
                <small class="scenario-note">{{ scenarios?.scenario_definitions[card.key] }}</small>
              </div>
            </div>
          </div>

          <div v-if="result.warnings.length" class="warnings mt-16">
            <div class="warnings-head"><TriangleAlert :size="15" /> 风险提示</div>
            <ul><li v-for="warning in result.warnings" :key="warning">{{ warning }}</li></ul>
          </div>

          <div class="assumptions mt-16">
            <div class="assumptions-title"><CircleDollarSign :size="14" /> 计算假设</div>
            <div class="assumption-grid">
              <p v-for="item in result.assumptions" :key="item">{{ item }}</p>
            </div>
            <p class="disclaimer">{{ result.disclaimer }}</p>
          </div>
        </template>

        <div v-else class="card">
          <div class="empty">
            <div class="empty-icon"><Landmark :size="20" /></div>
            <strong>填写交易假设</strong>
            <p>系统会计算 NOI、DSCR、现金流、IRR 与敏感性，不替你做投资决定。</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.preset-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; overflow-x: auto; padding-bottom: 2px; }
.preset-label { font-size: 8px; letter-spacing: .15em; color: var(--muted); flex: 0 0 auto; margin-right: 3px; }
.preset-chip { flex: 0 0 auto; border: 1px solid var(--line); background: rgba(251,248,241,.6); border-radius: 3px; padding: 6px 10px; display: flex; flex-direction: column; gap: 1px; text-align: left; transition: border-color .2s, background .2s; }
.preset-chip:hover { border-color: var(--gold); background: var(--paper-2); }
.preset-chip span { font-size: 9px; font-weight: 600; }
.preset-chip small { font-size: 7.5px; color: var(--muted); }
.preset-note { font-size: 7.5px; color: var(--muted-light); margin-left: auto; flex: 0 0 auto; }

.investment-layout { display: grid; grid-template-columns: 342px minmax(0, 1fr); gap: 20px; align-items: start; }
.form-panel { position: sticky; top: 93px; padding: 21px; }
.form-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 17px; }
.slider-field { padding: 15px 0 13px; border-top: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); margin: 15px 0; }
.slider-field input[type=range] { margin: 4px 0; }
.slider-field .range-row { font-size: 8px; color: var(--muted-light); }
.advanced-toggle { width: 100%; display: flex; align-items: center; gap: 7px; background: transparent; border: 0; border-top: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); padding: 12px 1px; margin: 16px 0 4px; font-size: 10px; font-weight: 600; color: var(--ink-soft); }
.advanced-toggle svg:last-child { margin-left: auto; transition: transform .2s; }
.rotated { transform: rotate(180deg); }
.advanced-fields { overflow: hidden; }
.advanced-fields .form-grid { padding-top: 12px; }
.advanced-note { font-size: 8px; line-height: 1.6; color: var(--muted); padding-top: 9px; }
.expand-enter-active, .expand-leave-active { transition: opacity .2s, max-height .3s; max-height: 300px; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.calculate-btn { margin-top: 16px; height: 43px; }
.form-error { display: flex; gap: 5px; align-items: flex-start; font-size: 9px; color: var(--negative); margin-top: 8px; }
.form-disclaimer { font-size: 7.5px; line-height: 1.6; text-align: center; color: var(--muted-light); margin-top: 9px; }

.result-column { min-width: 0; }
.result-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 8px; letter-spacing: .1em; }
.result-live { color: var(--muted); display: inline-flex; align-items: center; gap: 6px; }
.live-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--positive); box-shadow: 0 0 0 3px rgba(77,127,98,.1); }
.result-time { margin-left: 12px; color: var(--muted-light); letter-spacing: 0; }
.verdict-panel { background: var(--ink); color: var(--paper); border-radius: 5px; display: grid; grid-template-columns: 1fr 1.1fr; gap: 30px; padding: 25px 29px; position: relative; overflow: hidden; }
.verdict-panel::before { content: ''; position: absolute; right: -50px; top: -80px; width: 260px; height: 260px; border: 1px solid rgba(216,188,140,.12); border-radius: 50%; }
.verdict-left { border-right: 1px solid rgba(244,239,229,.13); padding-right: 28px; }
.verdict-kicker { font-size: 7.5px; letter-spacing: .18em; color: var(--gold-light); }
.verdict-number { font-family: var(--font-serif); font-size: clamp(39px, 4vw, 55px); font-weight: 430; letter-spacing: -.045em; line-height: 1; margin-top: 10px; white-space: nowrap; }
.verdict-number span { font-family: var(--font-sans); font-size: 10px; font-weight: 500; letter-spacing: 0; color: rgba(244,239,229,.4); margin-left: 5px; }
.verdict-number.positive { color: #b9d0bd; }
.verdict-number.negative { color: #dfa58f; }
.verdict-label { font-size: 9px; color: rgba(244,239,229,.55); margin-top: 5px; letter-spacing: .05em; }
.verdict-right { position: relative; z-index: 1; display: flex; flex-direction: column; justify-content: center; }
.verdict-right > p { font-size: 9.5px; line-height: 1.7; color: rgba(244,239,229,.53); max-width: 390px; }
.verdict-facts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 15px; padding-top: 12px; border-top: 1px solid rgba(244,239,229,.11); }
.verdict-facts div { display: flex; flex-direction: column; gap: 2px; }
.verdict-facts span { font-size: 7px; color: rgba(244,239,229,.34); }
.verdict-facts strong { font-family: var(--font-serif); font-size: 15px; font-weight: 450; color: var(--paper); }
.verdict-watermark { position: absolute; right: 17px; bottom: -25px; font-family: var(--font-serif); font-size: 90px; color: rgba(244,239,229,.025); }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); border: 1px solid var(--line); background: rgba(251,248,241,.6); margin-top: 10px; border-radius: 4px; overflow: hidden; }
.kpi-item { padding: 14px 14px 13px; border-right: 1px solid var(--line); display: flex; flex-direction: column; gap: 3px; }
.kpi-item:last-child { border-right: 0; }
.kpi-label { font-size: 7.5px; letter-spacing: .1em; color: var(--muted); }
.kpi-item strong { font-family: var(--font-serif); font-size: 22px; font-weight: 480; letter-spacing: -.02em; margin-top: 3px; white-space: nowrap; }
.kpi-item small { font-size: 7.5px; color: var(--muted-light); }
.positive { color: var(--positive); }
.negative { color: var(--negative); }
.neutral { color: var(--ink); }

.cash-waterfall { display: flex; flex-direction: column; gap: 7px; }
.cash-row { display: grid; grid-template-columns: 78px 1fr 63px; align-items: center; gap: 9px; }
.cash-label { font-size: 9px; color: var(--muted); }
.cash-track { height: 9px; background: rgba(16,35,29,.035); border-radius: 1px; }
.cash-bar { display: block; height: 100%; border-radius: 1px; }
.cash-bar.income { background: linear-gradient(90deg, #87a58d, var(--sage)); }
.cash-bar.expense { background: linear-gradient(90deg, #d7ac9c, var(--clay)); }
.cash-bar.debt { background: linear-gradient(90deg, #b9a58b, #8f7658); }
.cash-value { font-size: 9px; font-weight: 650; text-align: right; font-variant-numeric: tabular-nums; }
.cash-total { display: grid; grid-template-columns: 1fr auto; align-items: baseline; border-top: 1px solid var(--line); margin-top: 7px; padding-top: 11px; }
.cash-total span { font-size: 10px; font-weight: 650; }
.cash-total strong { font-family: var(--font-serif); font-size: 25px; font-weight: 480; }
.cash-total small { grid-column: 1 / -1; font-size: 8px; color: var(--muted-light); margin-top: 1px; }

.exit-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px 18px; }
.exit-grid div { display: flex; flex-direction: column; gap: 2px; }
.exit-grid span { font-size: 7.5px; color: var(--muted); }
.exit-grid strong { font-family: var(--font-serif); font-size: 17px; font-weight: 480; }
.exit-bar { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; margin-top: 15px; padding-top: 12px; border-top: 1px solid var(--line-soft); }
.exit-bar-label { font-size: 7.5px; color: var(--muted); }
.exit-bar-track { height: 4px; background: var(--paper-3); border-radius: 3px; overflow: hidden; }
.exit-bar-track span { display: block; height: 100%; border-radius: 3px; }
.positive-fill { background: var(--sage); }
.negative-fill { background: var(--clay); }
.exit-bar strong { font-size: 9px; }
.exit-note { display: flex; align-items: center; gap: 5px; font-size: 8px; color: var(--muted); margin-top: 9px; }

.scenarios-card { padding-bottom: 18px; }
.scenario-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.scenario-card { border: 1px solid var(--line); padding: 13px; border-radius: 3px; background: rgba(251,248,241,.5); }
.scenario-card.active { border-color: var(--ink); background: rgba(234,226,212,.3); }
.scenario-head { display: flex; justify-content: space-between; align-items: center; font-size: 9px; font-weight: 650; }
.scenario-cf { font-family: var(--font-serif); font-size: 26px; font-weight: 470; letter-spacing: -.03em; margin: 8px 0 9px; white-space: nowrap; }
.scenario-cf small { font-family: var(--font-sans); font-size: 8px; font-weight: 500; color: var(--muted-light); }
.scenario-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.scenario-stats div { display: flex; flex-direction: column; gap: 1px; }
.scenario-stats span { font-size: 7px; color: var(--muted); }
.scenario-stats strong { font-size: 10px; font-weight: 650; }
.scenario-bar { height: 2px; background: var(--paper-3); margin: 9px 0 7px; overflow: hidden; }
.scenario-bar span { display: block; height: 100%; background: var(--gold); }
.scenario-note { display: block; font-size: 7px; line-height: 1.5; color: var(--muted-light); }

.warnings { border: 1px solid rgba(180,107,82,.24); background: rgba(180,107,82,.055); padding: 14px 16px; border-radius: 4px; }
.warnings-head { display: flex; align-items: center; gap: 7px; font-size: 10px; font-weight: 650; color: #8e4e39; }
.warnings ul { margin: 7px 0 0; padding-left: 17px; }
.warnings li { font-size: 9px; line-height: 1.65; color: #7e5b4e; }
.assumptions { padding: 16px; border: 1px solid var(--line); border-radius: 4px; background: rgba(234,226,212,.22); }
.assumptions-title { display: flex; align-items: center; gap: 6px; font-size: 9.5px; font-weight: 650; }
.assumptions-title svg { color: var(--sage); }
.assumption-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 9px 18px; margin-top: 10px; }
.assumption-grid p { font-size: 8.5px; line-height: 1.6; color: var(--muted); padding-left: 9px; border-left: 1px solid var(--line); }
.disclaimer { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--line); font-size: 8px; color: var(--muted-light); }
.result-loading { min-height: 420px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.loading-orbit { position: relative; width: 82px; height: 82px; display: grid; place-items: center; margin-bottom: 18px; }
.orbit-ring { position: absolute; inset: 0; border: 1px solid var(--line); border-top-color: var(--gold); border-radius: 50%; animation: spin 1.4s linear infinite; }
.orbit-core { width: 48px; height: 48px; border-radius: 50%; background: var(--ink); color: var(--gold-light); display: grid; place-items: center; }
.loading-title { font-family: var(--font-serif); font-size: 20px; }

@media (max-width: 1180px) {
  .investment-layout { grid-template-columns: 310px minmax(0, 1fr); }
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .kpi-item:nth-child(3) { border-right: 0; }
  .kpi-item:nth-child(-n+3) { border-bottom: 1px solid var(--line); }
  .verdict-panel { grid-template-columns: 1fr; gap: 17px; }
  .verdict-left { border-right: 0; border-bottom: 1px solid rgba(244,239,229,.13); padding: 0 0 15px; }
}
@media (max-width: 980px) {
  .investment-layout { grid-template-columns: 1fr; }
  .form-panel { position: static; }
  .scenario-grid { grid-template-columns: 1fr; }
  .assumption-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .kpi-grid { grid-template-columns: 1fr 1fr; }
  .kpi-item:nth-child(2n) { border-right: 0; }
  .kpi-item { border-bottom: 1px solid var(--line); }
  .kpi-item:nth-child(3) { border-right: 1px solid var(--line); }
  .verdict-number { font-size: 38px; }
  .verdict-facts { grid-template-columns: 1fr; gap: 7px; }
  .preset-note { display: none; }
  .cash-row { grid-template-columns: 66px 1fr 58px; }
}
</style>
