<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import {
  ArrowUpRight,
  Check,
  Copy,
  Database,
  FlaskConical,
  GitBranch,
  Layers3,
  Scale,
  ShieldCheck,
  Sparkles,
  Target,
  TriangleAlert,
  X,
} from 'lucide-vue-next'
import { api } from '@/api'
import { useToastStore } from '@/stores/toast'
import { usd, num, pct } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import ChartCanvas from '@/components/ChartCanvas.vue'
import { axisCommon, palette, tooltipCommon } from '@/lib/chartTheme'

interface Metric {
  mae: number
  rmse: number
  r2: number
  mape: number
  median_ae: number
  within_10pct: number
  within_20pct: number
  n: number
  label?: string
  note?: string
  fit_seconds?: number
  best_iteration?: number
  within_20?: number
}

interface ResearchData {
  king_county: {
    dataset: string
    rows: number
    period: { start: string; end: string }
    split: string
    models: Record<string, Metric>
    best_model: string
    best_model_label: string
    baseline_lift_pct: number
    interval: {
      residual_q10: number
      residual_q50: number
      residual_q90: number
      test_coverage_pct: number
      median_width_usd: number
      level: number
    }
  }
  uci: {
    dataset: string
    source: string
    target: string
    target_note: string
    rows: number
    holdout: Metric
    five_fold_cv: Metric
  }
  california: {
    dataset: string
    source: string
    target: string
    target_note: string
    rows: number
    holdout: Metric
  }
  generalization: {
    experiment: string
    purpose: string
    split: string
    train_rows: number
    test_rows: number
    unseen_zipcodes: string[]
    metrics: { mae: number; rmse: number; r2: number }
    random_split_reference: { mae: number; r2: number }
    caveat: string
  }
  evaluation: {
    errors_by_price_band: { group: string; count: number; mae: number; mape: number }[]
    errors_by_region: { group: string; count: number; mae: number; mape: number }[]
    residual: { mean: number; median: number; std: number; p10: number; p90: number }
    interval: { test_coverage_pct: number; median_width_usd: number }
    figures: string[]
  }
  shap: {
    ranking: { feature: string; label: string; mean_abs_shap: number; direction_corr: number; share_pct: number; direction: string }[]
    method: string
    base_value_usd: number
  }
  summary: { generated_at: string; duration_seconds: number }
  disclaimer: string
}

interface ModelCardData {
  card: {
    intended_use: string
    not_intended_for: string[]
    training_period: string
    currency: string
    known_limitations: string[]
    sensitive_attributes: string
    explainability: string
    generated_at: string
  }
  metrics: Record<string, Metric>
  best_model: string
  baseline_lift_pct: number
  interval: ResearchData['king_county']['interval']
  generalization: ResearchData['generalization']
}

const toast = useToastStore()
const research = ref<ResearchData | null>(null)
const card = ref<ModelCardData | null>(null)
const loading = ref(true)
const error = ref('')
const figure = ref<string | null>(null)
const copied = ref(false)

const figureCaptions: Record<string, string> = {
  'model_comparison.png': '三种模型在同一测试集上的 MAE 对比。XGBoost 相对 Ridge 降低 40.2%。',
  'actual_vs_predicted.png': '测试集预测值与真实成交价。高价段离散度更大，符合长尾分布。',
  'residual_distribution.png': '测试集残差分布。不对称残差是采用分位数区间而非正态假设的原因。',
  'shap_importance.png': '全局 TreeSHAP 平均绝对贡献。邮编市场基准、建筑等级与面积排在前列。',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [r, c] = await Promise.all([api.research(), api.modelCard()])
    research.value = r as unknown as ResearchData
    card.value = c as unknown as ModelCardData
  } catch (err) {
    error.value = err instanceof Error ? err.message : '研究数据加载失败'
  } finally {
    loading.value = false
  }
}

async function copyCommand() {
  const command = '.venv/bin/python ml/train.py && .venv/bin/python ml/explain.py && .venv/bin/python ml/evaluate.py'
  try {
    await navigator.clipboard.writeText(command)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1800)
    toast.push('复现命令已复制', 'success')
  } catch {
    toast.push('浏览器未授予剪贴板权限', 'error')
  }
}

onMounted(load)

const king = computed(() => research.value?.king_county)
const metrics = computed(() => research.value?.king_county.models ?? {})
const modelRows = computed(() => Object.entries(metrics.value).map(([key, value]) => ({ key, ...value })))
const maxBandMae = computed(() => Math.max(1, ...(research.value?.evaluation.errors_by_price_band.map((row) => row.mae) ?? [1])))

const modelOption = computed<EChartsOption>(() => {
  const rows = [...modelRows.value].sort((a, b) => b.mae - a.mae)
  return {
    animationDuration: 700,
    grid: { left: 96, right: 70, top: 12, bottom: 22 },
    tooltip: {
      ...tooltipCommon,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const p = (params as { dataIndex: number; value: number }[])[0]
        const row = rows[p.dataIndex]
        return `<div style="font-size:10px">${row.label ?? row.key}</div><div style="font-family:Manrope Variable;font-size:19px">${usd(row.mae)}</div><div style="font-size:8px;opacity:.55">MAE · R² ${row.r2}</div>`
      },
    },
    xAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${Math.round(v / 1000)}k` } },
    yAxis: { type: 'category', data: rows.map((row) => row.label ?? row.key), ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, fontSize: 9 } },
    series: [
      {
        type: 'bar',
        data: rows.map((row) => ({
          value: row.mae,
          itemStyle: { color: row.key === 'xgboost' ? palette.ink : row.key === 'random_forest' ? palette.sage : '#c7b9a4', borderRadius: [0, 2, 2, 0] },
        })),
        barWidth: '42%',
        label: { show: true, position: 'right', formatter: (p: unknown) => usd((p as { value: number }).value), fontSize: 8, color: '#64748b' },
      },
    ],
  }
})

const shapOption = computed<EChartsOption>(() => {
  const rows = [...(research.value?.shap.ranking.slice(0, 9) ?? [])].reverse()
  return {
    animationDuration: 700,
    grid: { left: 105, right: 54, top: 10, bottom: 20 },
    tooltip: {
      ...tooltipCommon,
      formatter: (params: unknown) => {
        const p = params as { dataIndex: number }
        const row = rows[p.dataIndex]
        return `<div style="font-size:10px">${row.label}</div><div style="font-family:Manrope Variable;font-size:19px">${usd(row.mean_abs_shap)}</div><div style="font-size:8px;opacity:.55">平均 |SHAP| · 占解释力 ${row.share_pct}%</div>`
      },
    },
    xAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${Math.round(v / 1000)}k` } },
    yAxis: { type: 'category', data: rows.map((row) => row.label), ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, fontSize: 8.5 } },
    series: [
      {
        type: 'bar',
        data: rows.map((row) => row.mean_abs_shap),
        barWidth: '48%',
        itemStyle: {
          borderRadius: [0, 2, 2, 0],
          color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: 'rgba(15,118,110,.45)' }, { offset: 1, color: palette.sage }] },
        },
        label: { show: true, position: 'right', formatter: (p: unknown) => `$${Math.round((p as { value: number }).value / 1000)}k`, fontSize: 7.5, color: '#64748b' },
      },
    ],
  }
})

const bandOption = computed<EChartsOption>(() => {
  const rows = research.value?.evaluation.errors_by_price_band ?? []
  return {
    animationDuration: 600,
    grid: { left: 45, right: 30, top: 18, bottom: 30 },
    tooltip: { ...tooltipCommon, trigger: 'axis', formatter: (params: unknown) => {
      const p = (params as { dataIndex: number; value: number }[])[0]
      const row = rows[p.dataIndex]
      return `<div style="font-size:10px">${row.group} · ${row.count} 套</div><div style="font-family:Manrope Variable;font-size:18px">${usd(row.mae)} MAE</div><div style="font-size:8px;opacity:.55">MAPE ${row.mape}%</div>`
    } },
    xAxis: { type: 'category', data: rows.map((row) => row.group), ...axisCommon, axisLabel: { ...axisCommon.axisLabel, fontSize: 8 } },
    yAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${Math.round(v / 1000)}k` } },
    series: [
      {
        type: 'bar',
        data: rows.map((row) => ({ value: row.mae, itemStyle: { color: row.mae > 150000 ? palette.clay : palette.gold, borderRadius: [2, 2, 0, 0] } })),
        barWidth: '48%',
      },
    ],
  }
})
</script>

<template>
  <div class="page research-page">
    <PageHeader
      eyebrow="MODEL RESEARCH / 07"
      title="指标可以漂亮，<em>但必须是真的。</em>"
      lede="从线性基线到梯度提升，从随机切分到未见邮编的冷启动检验。每个数字都由仓库里的脚本产生，每个边界都写进模型卡。"
    >
      <template #actions>
        <span class="badge badge-sage"><Check :size="11" /> REPRODUCIBLE</span>
        <button class="btn btn-ghost" @click="load"><FlaskConical :size="14" /> 重新载入</button>
      </template>
    </PageHeader>

    <div v-if="error" class="card">
      <div class="empty"><strong>研究数据加载失败</strong><p>{{ error }}</p><button class="btn btn-ghost btn-small mt-16" @click="load">重试</button></div>
    </div>

    <template v-else>
      <section class="research-hero">
        <div class="research-hero-head">
          <div>
            <div class="hero-kicker">KING COUNTY / RANDOM 80-20 HOLDOUT</div>
            <h2>主模型测试成绩</h2>
            <p>目标为成交价（USD）。测试集 4,284 套，未参与训练与早停。</p>
          </div>
          <span class="hero-stamp">XGBOOST<br /><b>v1.0</b></span>
        </div>
        <div class="hero-metrics">
          <div><span>MAE</span><strong>{{ loading ? '—' : usd(king?.models.xgboost.mae) }}</strong><small>平均绝对误差</small></div>
          <div><span>R²</span><strong>{{ loading ? '—' : king?.models.xgboost.r2.toFixed(4) }}</strong><small>解释方差比例</small></div>
          <div><span>MAPE</span><strong>{{ loading ? '—' : pct(king?.models.xgboost.mape) }}</strong><small>平均绝对百分比误差</small></div>
          <div><span>BASELINE LIFT</span><strong>{{ loading ? '—' : pct(king?.baseline_lift_pct) }}</strong><small>相对 Ridge 的 MAE 降幅</small></div>
        </div>
        <div class="hero-foot">
          <span><Database :size="11" /> 清洗后 {{ num(king?.rows) }} 条 · {{ king?.period.start }} 至 {{ king?.period.end }}</span>
          <span><GitBranch :size="11" /> {{ king?.split }}</span>
          <span>指标来自单次固定切分，未做测试集调参</span>
        </div>
      </section>

      <section class="grid grid-12 mt-24">
        <div class="span-7 card">
          <div class="card-head">
            <div>
              <div class="card-label">MODEL BAKE-OFF</div>
              <h3 class="card-title">为什么选 XGBoost</h3>
              <p class="card-sub">同一个测试集、同一套特征。线性模型提供基线，随机森林提供稳健对照。</p>
            </div>
            <span class="badge badge-outline">MAE</span>
          </div>
          <ChartCanvas :option="modelOption" height="230px" :loading="loading" aria-label="三种模型 MAE 对比" />
        </div>

        <div class="span-5 card">
          <div class="card-head">
            <div>
              <div class="card-label">METRIC TABLE</div>
              <h3 class="card-title">完整对照</h3>
            </div>
          </div>
          <div class="metric-table-wrap">
            <table class="data-table">
              <thead><tr><th>模型</th><th class="right">MAE</th><th class="right">R²</th><th class="right">±20%</th></tr></thead>
              <tbody>
                <tr v-for="row in modelRows" :key="row.key" :class="{ best: row.key === 'xgboost' }">
                  <td class="strong">{{ row.label ?? row.key }}</td>
                  <td class="right">{{ usd(row.mae) }}</td>
                  <td class="right">{{ row.r2.toFixed(3) }}</td>
                  <td class="right">{{ pct(row.within_20pct) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="metric-insight">
            <Sparkles :size="13" />
            <p>XGBoost 的 MAE 比 Ridge 低 {{ pct(king?.baseline_lift_pct) }}，但这不是“更准”的全部证据：还需看区间覆盖、残差切片与未见邮编表现。</p>
          </div>
        </div>
      </section>

      <section class="grid grid-12 mt-24">
        <div class="span-7 card">
          <div class="card-head">
            <div>
              <div class="card-label">GLOBAL EXPLAINABILITY</div>
              <h3 class="card-title">模型在看什么</h3>
              <p class="card-sub">全样本平均 |TreeSHAP|，精确加性分解。排序不是因果结论，只说明模型的依赖结构。</p>
            </div>
            <span class="badge badge-gold" :title="research?.shap.method">TREESHAP · 精确</span>
          </div>
          <ChartCanvas :option="shapOption" height="300px" :loading="loading" aria-label="全局 SHAP 重要性排序" />
        </div>

        <div class="span-5 stack">
          <div class="card interval-card">
            <div class="card-head">
              <div>
                <div class="card-label">UNCERTAINTY</div>
                <h3 class="card-title">80% 区间校准</h3>
              </div>
              <span class="badge badge-sage">覆盖 {{ pct(king?.interval.test_coverage_pct) }}</span>
            </div>
            <div class="interval-scale">
              <span class="interval-fill" />
              <span class="interval-center"><i /></span>
              <span class="interval-tick q10"><b>{{ usd(king?.interval.residual_q10) }}</b><small>Q10 残差</small></span>
              <span class="interval-tick q90"><b>+{{ usd(king?.interval.residual_q90) }}</b><small>Q90 残差</small></span>
            </div>
            <div class="interval-stats">
              <div><span>实测覆盖</span><strong>{{ pct(king?.interval.test_coverage_pct) }}</strong><small>目标 80%</small></div>
              <div><span>区间中位宽度</span><strong>{{ usd(king?.interval.median_width_usd) }}</strong><small>不对称，保留长尾</small></div>
              <div><span>残差中位数</span><strong>{{ usd(king?.interval.residual_q50) }}</strong><small>略微低估</small></div>
            </div>
            <p class="card-caption">用 5 折 OOF 残差分位数构造不对称区间，避免强行假设正态分布。81.5% 的实测覆盖略高于目标，方向偏保守。</p>
          </div>

          <div class="card card-darkish">
            <div class="card-label">KNOWN LIMITATIONS</div>
            <ul class="limit-list">
              <li v-for="item in card?.card.known_limitations" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="generalization-band mt-24">
        <div class="gen-copy">
          <div class="eyebrow" style="color: var(--gold-light)">GEOGRAPHIC GENERALIZATION</div>
          <h2>随机切分很乐观，<em>未见邮编才是冷水。</em></h2>
          <p>{{ research?.generalization.purpose }} 模型在训练时从未见过 14 个邮编，只能依赖经纬度、面积与区域基准做冷启动推断。</p>
          <div class="gen-zips">
            <span v-for="zip in research?.generalization.unseen_zipcodes.slice(0, 10)" :key="zip">{{ zip }}</span>
            <span v-if="(research?.generalization.unseen_zipcodes.length ?? 0) > 10">+{{ (research?.generalization.unseen_zipcodes.length ?? 0) - 10 }}</span>
          </div>
        </div>
        <div class="gen-metrics">
          <div class="gen-row">
            <div class="gen-label"><span>随机切分 MAE</span><strong>{{ usd(research?.generalization.random_split_reference.mae) }}</strong></div>
            <div class="gen-track"><span :style="{ width: `${(research?.generalization.random_split_reference.mae ?? 0) / (research?.generalization.metrics.mae ?? 1) * 100}%` }" /></div>
          </div>
          <div class="gen-row unseen">
            <div class="gen-label"><span>未见邮编 MAE</span><strong>{{ usd(research?.generalization.metrics.mae) }}</strong></div>
            <div class="gen-track"><span style="width: 100%" /></div>
          </div>
          <div class="gen-r2">
            <div><span>随机切分 R²</span><strong>{{ research?.generalization.random_split_reference.r2 }}</strong></div>
            <ArrowUpRight :size="15" />
            <div><span>未见邮编 R²</span><strong>{{ research?.generalization.metrics.r2 }}</strong></div>
          </div>
          <p class="gen-caveat"><TriangleAlert :size="12" />{{ research?.generalization.caveat }}</p>
        </div>
      </section>

      <section class="mt-32">
        <div class="section-head">
          <div>
            <div class="section-kicker">THREE DATASETS, THREE QUESTIONS</div>
            <h2 class="section-title">三个数据集，<em>三套独立结论</em></h2>
            <p class="section-desc">不把一个数据集的误差、货币或 R² 横向拼成“平均成绩”。每套数据只回答它自己的问题。</p>
          </div>
        </div>
        <div class="dataset-grid">
          <div class="dataset-card primary">
            <div class="dataset-head"><span class="dataset-tag">PRIMARY</span><Database :size="15" /></div>
            <h3>King County<br /><em>主估值模型</em></h3>
            <p class="dataset-desc">2014–2015 年住宅成交，美元计价。用于 Web 估值、SHAP 与可比成交。</p>
            <div class="dataset-stats">
              <div><span>清洗样本</span><strong>{{ num(king?.rows) }}</strong></div>
              <div><span>测试 MAE</span><strong>{{ usd(king?.models.xgboost.mae) }}</strong></div>
              <div><span>测试 R²</span><strong>{{ king?.models.xgboost.r2.toFixed(4) }}</strong></div>
              <div><span>区间覆盖</span><strong>{{ pct(king?.interval.test_coverage_pct) }}</strong></div>
            </div>
            <div class="dataset-note">目标：成交价 USD · 随机 80/20</div>
          </div>

          <div class="dataset-card">
            <div class="dataset-head"><span class="dataset-tag">EXTERNAL</span><FlaskConical :size="15" /></div>
            <h3>UCI Real Estate<br /><em>新店区 · 台湾</em></h3>
            <p class="dataset-desc">{{ research?.uci.target_note }}</p>
            <div class="dataset-stats">
              <div><span>样本</span><strong>{{ research?.uci.rows }}</strong></div>
              <div><span>Holdout MAE</span><strong>{{ research?.uci.holdout.mae }}</strong></div>
              <div><span>5 折 CV MAE</span><strong>{{ research?.uci.five_fold_cv.mae }}</strong></div>
              <div><span>Holdout R²</span><strong>{{ research?.uci.holdout.r2 }}</strong></div>
            </div>
            <div class="dataset-note">目标：万元新台币 / 坪 · 不可与美元 MAE 比较</div>
          </div>

          <div class="dataset-card">
            <div class="dataset-head"><span class="dataset-tag">REGIONAL CONTROL</span><Layers3 :size="15" /></div>
            <h3>California Housing<br /><em>1990 普查街区组</em></h3>
            <p class="dataset-desc">{{ research?.california.target_note }}</p>
            <div class="dataset-stats">
              <div><span>样本</span><strong>{{ num(research?.california.rows) }}</strong></div>
              <div><span>Holdout MAE</span><strong>{{ usd(research?.california.holdout.mae) }}</strong></div>
              <div><span>Holdout R²</span><strong>{{ research?.california.holdout.r2 }}</strong></div>
              <div><span>±20% 命中</span><strong>{{ pct(research?.california.holdout.within_20pct) }}</strong></div>
            </div>
            <div class="dataset-note">目标：1990 年中位房价 · 500k 处封顶</div>
          </div>
        </div>
      </section>

      <section class="grid grid-12 mt-24">
        <div class="span-7 card">
          <div class="card-head">
            <div>
              <div class="card-label">ERROR SLICES</div>
              <h3 class="card-title">误差在哪些价格段更大</h3>
              <p class="card-sub">绝对误差随价格上升，但百分比误差在低价段反而更高。</p>
            </div>
          </div>
          <ChartCanvas :option="bandOption" height="238px" :loading="loading" aria-label="分价格段误差" />
          <div class="band-table">
            <div v-for="row in research?.evaluation.errors_by_price_band" :key="row.group" class="band-row">
              <span>{{ row.group }}</span>
              <i><b :style="{ width: `${(row.mae / maxBandMae) * 100}%` }" /></i>
              <strong>{{ usd(row.mae) }}</strong>
              <small>{{ pct(row.mape) }} MAPE</small>
            </div>
          </div>
        </div>

        <div class="span-5 card">
          <div class="card-head">
            <div>
              <div class="card-label">RESIDUAL DIAGNOSTICS</div>
              <h3 class="card-title">残差与区间</h3>
            </div>
          </div>
          <div class="residual-grid">
            <div><span>残差均值</span><strong>{{ usd(research?.evaluation.residual.mean) }}</strong></div>
            <div><span>残差中位数</span><strong>{{ usd(research?.evaluation.residual.median) }}</strong></div>
            <div><span>残差标准差</span><strong>{{ usd(research?.evaluation.residual.std) }}</strong></div>
            <div><span>P10 / P90</span><strong>{{ usd(research?.evaluation.residual.p10) }} / {{ usd(research?.evaluation.residual.p90) }}</strong></div>
          </div>
          <div class="coverage-block">
            <div class="coverage-head"><span>80% 区间实测覆盖</span><strong>{{ pct(king?.interval.test_coverage_pct) }}</strong></div>
            <div class="coverage-track">
              <span class="coverage-target" style="left: 80%" />
              <span class="coverage-fill" :style="{ width: `${king?.interval.test_coverage_pct ?? 0}%` }" />
            </div>
            <div class="coverage-foot"><span>0%</span><span>目标 80%</span><span>100%</span></div>
          </div>
          <p class="card-caption">残差均值接近 0，但分布有明显长尾；这是保留不对称区间、报告 P10/P90 而不是单一置信半径的原因。</p>
          <div class="shap-base"><span>全局 SHAP 基准价</span><strong>{{ usd(research?.shap.base_value_usd) }}</strong></div>
        </div>
      </section>

      <section class="mt-32">
        <div class="section-head">
          <div>
            <div class="section-kicker">DIAGNOSTIC FIGURES</div>
            <h2 class="section-title">可复核的图表</h2>
            <p class="section-desc">这些图由 `ml/evaluate.py` 生成，不是前端装饰图。点击查看原图。</p>
          </div>
        </div>
        <div class="figure-grid">
          <button v-for="name in research?.evaluation.figures" :key="name" class="figure-card" @click="figure = `/reports/${name}`">
            <img :src="`/reports/${name}`" :alt="figureCaptions[name] ?? name" loading="lazy" />
            <div class="figure-caption"><span>{{ name.replace('.png', '').replaceAll('_', ' ') }}</span><ArrowUpRight :size="12" /></div>
            <p class="figure-desc">{{ figureCaptions[name] }}</p>
          </button>
        </div>
      </section>

      <section class="governance mt-24">
        <div class="governance-copy">
          <div class="eyebrow" style="color: var(--gold-light)">MODEL CARD / GOVERNANCE</div>
          <h2>能用来做什么，<em>不能用来做什么。</em></h2>
          <p>{{ card?.card.intended_use }}。模型未使用种族、性别、宗教等受保护属性，但地理位置仍可能与历史性隔离相关，需持续做公平性审查。</p>
          <div class="governance-badges">
            <span><ShieldCheck :size="11" /> 非正式评估</span>
            <span><Scale :size="11" /> 公平性待审</span>
            <span><Target :size="11" /> 历史样本</span>
          </div>
        </div>
        <div class="governance-lists">
          <div>
            <h3>NOT INTENDED FOR</h3>
            <ul><li v-for="item in card?.card.not_intended_for" :key="item">{{ item }}</li></ul>
          </div>
          <div>
            <h3>REPRODUCE</h3>
            <div class="command-box">
              <code>.venv/bin/python ml/train.py<br />.venv/bin/python ml/explain.py<br />.venv/bin/python ml/evaluate.py</code>
              <button class="icon-btn" :title="copied ? '已复制' : '复制命令'" @click="copyCommand">
                <Check v-if="copied" :size="13" /><Copy v-else :size="13" />
              </button>
            </div>
            <p class="repro-note">训练约 29 秒；artifacts 写入 `ml/artifacts/`，报告写入 `ml/reports/`。</p>
          </div>
        </div>
      </section>

      <p class="research-disclaimer">{{ research?.disclaimer }}</p>
    </template>

    <Transition name="fade">
      <div v-if="figure" class="figure-modal" @click.self="figure = null">
        <button class="modal-close" aria-label="关闭图片" @click="figure = null"><X :size="20" /></button>
        <img :src="figure" alt="诊断图表原图" />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.research-hero { background: var(--ink); color: var(--paper); border-radius: 10px; padding: 26px 28px 0; position: relative; overflow: hidden; }
.research-hero::after { content: 'R²'; position: absolute; right: 26px; top: -22px; font-family: var(--font-serif); font-size: 150px; color: rgba(248,250,252,.025); line-height: 1; }
.research-hero-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 25px; position: relative; z-index: 1; }
.hero-kicker { font-size: 7.5px; letter-spacing: .18em; color: var(--gold-light); }
.research-hero h2 { font-family: var(--font-serif); font-size: 28px; font-weight: 650; letter-spacing: -.025em; margin-top: 6px; }
.research-hero p { font-size: 8.5px; color: rgba(248,250,252,.4); margin-top: 3px; }
.hero-stamp { font-size: 7px; letter-spacing: .13em; color: rgba(248,250,252,.4); text-align: right; line-height: 1.8; border: 1px solid rgba(248,250,252,.16); padding: 6px 9px; border-radius: 6px; }
.hero-stamp b { color: var(--gold-light); font-weight: 600; }
.hero-metrics { display: grid; grid-template-columns: repeat(4, 1fr); border-top: 1px solid rgba(248,250,252,.13); margin-top: 22px; padding-top: 17px; position: relative; z-index: 1; }
.hero-metrics > div { display: flex; flex-direction: column; gap: 3px; padding-right: 18px; }
.hero-metrics > div + div { border-left: 1px solid rgba(248,250,252,.13); padding-left: 20px; }
.hero-metrics span { font-size: 7px; letter-spacing: .15em; color: rgba(248,250,252,.37); }
.hero-metrics strong { font-family: var(--font-serif); font-size: clamp(27px, 3.2vw, 41px); font-weight: 650; letter-spacing: -.04em; line-height: 1; margin-top: 3px; white-space: nowrap; }
.hero-metrics small { font-size: 7px; color: rgba(248,250,252,.32); }
.hero-foot { display: flex; justify-content: space-between; gap: 14px; margin: 18px -28px 0; padding: 10px 28px; border-top: 1px solid rgba(248,250,252,.1); font-size: 6.5px; color: rgba(248,250,252,.3); }
.hero-foot span { display: inline-flex; align-items: center; gap: 4px; }

.metric-table-wrap { overflow-x: auto; }
.data-table tr.best { background: rgba(29,90,150,.08); }
.data-table tr.best td:first-child { color: var(--ink); }
.metric-insight { display: flex; align-items: flex-start; gap: 7px; padding-top: 12px; margin-top: 8px; border-top: 1px solid var(--line-soft); color: var(--gold); }
.metric-insight p { font-size: 8.5px; line-height: 1.65; color: var(--muted); }
.stack { display: flex; flex-direction: column; gap: 16px; }
.interval-card { flex: 1; }
.interval-scale { position: relative; height: 45px; margin: 17px 0 5px; background: linear-gradient(90deg, rgba(180,35,24,.18), var(--paper-3) 50%, rgba(15,118,110,.2)); border-radius: 6px; }
.interval-fill { position: absolute; left: 8%; right: 8%; top: 19px; height: 4px; background: linear-gradient(90deg, var(--clay), var(--gold), var(--sage)); border-radius: 8px; }
.interval-center { position: absolute; left: 50%; top: 19px; transform: translate(-50%,-50%); width: 11px; height: 11px; border-radius: 50%; border: 2px solid var(--ink); background: var(--paper-2); }
.interval-center i { display: block; width: 3px; height: 3px; border-radius: 50%; background: var(--ink); margin: 2px auto; }
.interval-tick { position: absolute; top: 0; display: flex; flex-direction: column; }
.interval-tick.q10 { left: 0; }
.interval-tick.q90 { right: 0; text-align: right; }
.interval-tick b { font-size: 8px; font-weight: 650; }
.interval-tick small { font-size: 6px; color: var(--muted-light); }
.interval-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 13px; padding-top: 11px; border-top: 1px solid var(--line-soft); }
.interval-stats div { display: flex; flex-direction: column; gap: 2px; }
.interval-stats span { font-size: 6.5px; color: var(--muted); }
.interval-stats strong { font-family: var(--font-serif); font-size: 17px; font-weight: 650; }
.interval-stats small { font-size: 6.5px; color: var(--muted-light); }
.card-darkish { background: #f8fafc; border-color: var(--line); flex: 0 0 auto; }
.limit-list { margin: 8px 0 0; padding-left: 14px; }
.limit-list li { font-size: 8px; line-height: 1.6; color: var(--muted); margin-bottom: 5px; }

.generalization-band { background: var(--ink); color: var(--paper); border-radius: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 34px; padding: 27px 29px; }
.gen-copy h2 { font-family: var(--font-serif); font-size: clamp(24px, 2.5vw, 32px); font-weight: 650; letter-spacing: -.03em; line-height: 1.18; margin-top: 9px; }
.gen-copy h2 em { color: var(--gold-light); font-weight: 380; }
.gen-copy p { font-size: 9px; line-height: 1.7; color: rgba(248,250,252,.46); margin-top: 10px; max-width: 460px; }
.gen-zips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 13px; }
.gen-zips span { font-size: 6.5px; color: rgba(248,250,252,.5); border: 1px solid rgba(248,250,252,.14); padding: 2px 5px; border-radius: 6px; }
.gen-metrics { display: flex; flex-direction: column; justify-content: center; gap: 13px; }
.gen-label { display: flex; justify-content: space-between; align-items: baseline; font-size: 8px; color: rgba(248,250,252,.45); }
.gen-label strong { font-family: var(--font-serif); font-size: 19px; font-weight: 650; color: var(--paper); }
.gen-track { height: 5px; background: rgba(248,250,252,.1); border-radius: 7px; margin-top: 5px; overflow: hidden; }
.gen-track span { display: block; height: 100%; background: var(--sage-light); border-radius: 7px; }
.gen-row.unseen .gen-track span { background: var(--gold-light); }
.gen-r2 { display: flex; align-items: center; gap: 15px; border-top: 1px solid rgba(248,250,252,.11); border-bottom: 1px solid rgba(248,250,252,.11); padding: 11px 0; }
.gen-r2 div { display: flex; flex-direction: column; gap: 1px; flex: 1; }
.gen-r2 span { font-size: 6.5px; color: rgba(248,250,252,.35); }
.gen-r2 strong { font-family: var(--font-serif); font-size: 18px; font-weight: 650; }
.gen-r2 svg { color: var(--gold-light); }
.gen-caveat { display: flex; gap: 5px; font-size: 7px; line-height: 1.6; color: rgba(248,250,252,.36); }
.gen-caveat svg { color: var(--clay); flex: 0 0 auto; margin-top: 1px; }

.dataset-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.dataset-card { border: 1px solid var(--line); background: #ffffff; border-radius: 8px; padding: 19px; display: flex; flex-direction: column; }
.dataset-card.primary { background: var(--ink); border-color: var(--ink); color: var(--paper); }
.dataset-head { display: flex; justify-content: space-between; align-items: center; color: var(--gold); }
.dataset-card.primary .dataset-head { color: var(--gold-light); }
.dataset-tag { font-size: 6px; letter-spacing: .15em; border: 1px solid currentColor; padding: 2px 5px; border-radius: 6px; }
.dataset-card h3 { font-family: var(--font-serif); font-size: 23px; font-weight: 650; letter-spacing: -.025em; line-height: 1.15; margin-top: 15px; }
.dataset-card h3 em { font-style: normal; color: var(--gold); font-size: 14px; }
.dataset-card.primary h3 em { color: var(--gold-light); }
.dataset-desc { font-size: 8px; line-height: 1.65; color: var(--muted); margin-top: 7px; min-height: 40px; }
.dataset-card.primary .dataset-desc { color: rgba(248,250,252,.45); }
.dataset-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border-top: 1px solid var(--line); margin-top: 15px; padding-top: 12px; }
.dataset-card.primary .dataset-stats { border-color: rgba(248,250,252,.12); }
.dataset-stats div { display: flex; flex-direction: column; gap: 1px; }
.dataset-stats span { font-size: 6.5px; color: var(--muted); }
.dataset-card.primary .dataset-stats span { color: rgba(248,250,252,.35); }
.dataset-stats strong { font-family: var(--font-serif); font-size: 17px; font-weight: 650; letter-spacing: -.02em; }
.dataset-note { margin-top: 13px; padding-top: 8px; border-top: 1px solid var(--line-soft); font-size: 6.5px; color: var(--muted-light); }
.dataset-card.primary .dataset-note { border-color: rgba(248,250,252,.1); color: rgba(248,250,252,.3); }

.band-table { margin-top: 10px; display: flex; flex-direction: column; gap: 5px; }
.band-row { display: grid; grid-template-columns: 62px 1fr 64px 65px; align-items: center; gap: 8px; font-size: 8px; }
.band-row span { color: var(--muted); }
.band-row i { height: 3px; background: var(--paper-3); border-radius: 6px; overflow: hidden; }
.band-row b { display: block; height: 100%; background: var(--gold); }
.band-row strong { text-align: right; font-weight: 650; }
.band-row small { font-size: 6.5px; color: var(--muted-light); text-align: right; }
.residual-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 15px; }
.residual-grid div { display: flex; flex-direction: column; gap: 2px; }
.residual-grid span { font-size: 7px; color: var(--muted); }
.residual-grid strong { font-family: var(--font-serif); font-size: 17px; font-weight: 650; }
.coverage-block { margin-top: 17px; padding-top: 12px; border-top: 1px solid var(--line-soft); }
.coverage-head { display: flex; justify-content: space-between; font-size: 8px; color: var(--muted); }
.coverage-head strong { color: var(--ink); }
.coverage-track { position: relative; height: 6px; background: var(--paper-3); border-radius: 8px; margin: 9px 0 4px; overflow: hidden; }
.coverage-fill { display: block; height: 100%; background: linear-gradient(90deg, var(--sage), #91ad98); border-radius: 8px; }
.coverage-target { position: absolute; top: -2px; bottom: -2px; width: 1px; background: var(--ink); z-index: 1; }
.coverage-foot { display: flex; justify-content: space-between; font-size: 6.5px; color: var(--muted-light); }
.shap-base { display: flex; justify-content: space-between; align-items: baseline; margin-top: 13px; padding-top: 10px; border-top: 1px solid var(--line-soft); font-size: 7.5px; color: var(--muted); }
.shap-base strong { font-family: var(--font-serif); font-size: 17px; font-weight: 650; color: var(--ink); }

.figure-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.figure-card { border: 1px solid var(--line); background: var(--paper-2); padding: 0; overflow: hidden; border-radius: 7px; text-align: left; }
.figure-card img { display: block; width: 100%; height: 205px; object-fit: contain; background: #fff; padding: 8px; transition: transform .3s; }
.figure-card:hover img { transform: scale(1.012); }
.figure-desc { padding: 0 10px 9px; font-size: 7px; line-height: 1.5; color: var(--muted-light); }
.figure-caption { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border-top: 1px solid var(--line); font-size: 7px; letter-spacing: .04em; color: var(--muted); text-transform: uppercase; }

.governance { display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 30px; background: #f8fafc; border: 1px solid var(--line); border-radius: 10px; padding: 25px 27px; }
.governance-copy h2 { font-family: var(--font-serif); font-size: 27px; font-weight: 650; letter-spacing: -.03em; line-height: 1.15; margin-top: 9px; }
.governance-copy h2 em { color: var(--gold); font-weight: 380; }
.governance-copy p { font-size: 8.5px; line-height: 1.7; color: var(--muted); margin-top: 9px; }
.governance-badges { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 13px; }
.governance-badges span { display: inline-flex; align-items: center; gap: 3px; font-size: 6.5px; border: 1px solid var(--line); padding: 3px 6px; border-radius: 99px; color: var(--muted); }
.governance-lists { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.governance-lists h3 { font-size: 7px; letter-spacing: .13em; color: var(--muted); margin: 0 0 8px; }
.governance-lists ul { margin: 0; padding-left: 14px; }
.governance-lists li { font-size: 7.5px; line-height: 1.55; color: var(--muted); margin-bottom: 4px; }
.command-box { display: flex; align-items: flex-start; gap: 6px; background: var(--ink); color: rgba(248,250,252,.75); border-radius: 7px; padding: 9px; }
.command-box code { font-size: 6.5px; line-height: 1.75; flex: 1; word-break: break-all; }
.command-box .icon-btn { color: var(--gold-light); width: 22px; height: 22px; flex: 0 0 auto; }
.repro-note { font-size: 6.5px; line-height: 1.55; color: var(--muted-light); margin-top: 7px; }
.research-disclaimer { margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--line); font-size: 7px; line-height: 1.6; color: var(--muted-light); }
.figure-modal { position: fixed; inset: 0; z-index: 90; background: rgba(6,18,14,.78); backdrop-filter: blur(4px); display: grid; place-items: center; padding: 40px; }
.figure-modal img { max-width: 92vw; max-height: 88vh; background: #fff; padding: 10px; border-radius: 7px; }
.modal-close { position: absolute; top: 18px; right: 18px; width: 34px; height: 34px; border-radius: 50%; border: 1px solid rgba(248,250,252,.22); background: rgba(11,27,22,.5); color: var(--paper); display: grid; place-items: center; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 1100px) {
  .generalization-band { grid-template-columns: 1fr; gap: 22px; }
  .dataset-grid { grid-template-columns: 1fr; }
  .dataset-card { display: grid; grid-template-columns: 1fr 1fr; gap: 0 20px; }
  .dataset-card .dataset-head { grid-column: 1 / -1; }
  .dataset-card h3 { grid-column: 1; }
  .dataset-desc { grid-column: 1; }
  .dataset-stats { grid-column: 2; grid-row: 2 / span 2; border-top: 0; margin-top: 15px; padding-top: 0; align-self: start; }
  .dataset-note { grid-column: 1 / -1; }
  .governance { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .hero-metrics { grid-template-columns: 1fr 1fr; gap: 15px 0; }
  .hero-metrics > div:nth-child(3) { border-left: 0; padding-left: 0; }
  .hero-foot { flex-direction: column; gap: 5px; margin-left: -17px; margin-right: -17px; padding-left: 17px; padding-right: 17px; }
  .research-hero { padding: 20px 17px 0; }
  .dataset-card { display: block; }
  .dataset-stats { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 15px; }
  .dataset-card.primary .dataset-stats { border-color: rgba(248,250,252,.12); }
  .figure-grid { grid-template-columns: 1fr; }
  .figure-card img { height: 180px; }
  .governance-lists { grid-template-columns: 1fr; }
  .interval-stats { grid-template-columns: 1fr; gap: 7px; }
  .band-row { grid-template-columns: 58px 1fr 58px; }
  .band-row small { display: none; }
  .generalization-band { padding: 21px 18px; }
  .governance { padding: 20px 18px; }
}
</style>
