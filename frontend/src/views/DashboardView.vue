<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { EChartsOption } from 'echarts'
import { ArrowUpRight, Database, MapPin, RefreshCw, Sparkles } from 'lucide-vue-next'
import { api } from '@/api'
import type { DashboardData } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import ChartCanvas from '@/components/ChartCanvas.vue'
import MetricCard from '@/components/MetricCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { usd, num, pct } from '@/lib/format'
import { axisCommon, palette, tooltipCommon } from '@/lib/chartTheme'

const data = ref<DashboardData | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.dashboard()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '数据驾驶舱加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const overview = computed(() => data.value?.overview)
const pulse = computed(() => data.value?.market_pulse)

const priceBands = [
  { max: 350_000, color: '#1e3a5f', label: '<35万' },
  { max: 500_000, color: '#2c5f8f', label: '35–50万' },
  { max: 750_000, color: '#3f7fb8', label: '50–75万' },
  { max: 1_200_000, color: '#6fa4d1', label: '75–120万' },
  { max: Infinity, color: '#a9c9e6', label: '120万+' },
]

const mapOption = computed<EChartsOption>(() => {
  const points = data.value?.map_points ?? []
  const groups = priceBands.map((band, index) => {
    const min = index === 0 ? 0 : priceBands[index - 1].max
    return {
      name: band.label,
      type: 'scatter' as const,
      data: points.filter((p) => p.price >= min && p.price < band.max).map((p) => [p.lon, p.lat, p.price, p.area]),
      symbolSize: 3.2,
      itemStyle: { color: band.color, opacity: 0.76 },
      emphasis: { itemStyle: { opacity: 1, borderColor: '#ffffff', borderWidth: 1 } },
      large: true,
      largeThreshold: 300,
    }
  })
  return {
    backgroundColor: 'transparent',
    animationDuration: 700,
    grid: { left: 22, right: 22, top: 22, bottom: 28 },
    legend: {
      bottom: 2,
      left: 'center',
      icon: 'circle',
      itemWidth: 5,
      itemHeight: 5,
      itemGap: 15,
      textStyle: { color: 'rgba(248,250,252,.54)', fontSize: 8.5, fontFamily: 'Manrope Variable' },
    },
    tooltip: {
      ...tooltipCommon,
      trigger: 'item',
      formatter: (params: unknown) => {
        const item = params as { data: number[] }
        return `<div style="font-size:9px;letter-spacing:.12em;opacity:.55">KING COUNTY</div>
          <div style="font-family:Manrope Variable;font-size:18px;margin:3px 0">${usd(item.data[2])}</div>
          <div style="font-size:10px;opacity:.65">${num(item.data[3])} sqft · ${(item.data[2] / item.data[3]).toFixed(0)} USD/sqft</div>`
      },
    },
    xAxis: {
      type: 'value',
      min: -122.56,
      max: -121.05,
      show: false,
    },
    yAxis: {
      type: 'value',
      min: 47.05,
      max: 47.82,
      show: false,
    },
    series: groups,
  }
})

const histogramOption = computed<EChartsOption>(() => {
  const bins = data.value?.histogram ?? []
  return {
    animationDuration: 700,
    grid: { left: 38, right: 12, top: 18, bottom: 38 },
    tooltip: {
      ...tooltipCommon,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const item = (params as { name: string; value: number }[])[0]
        return `<div style="font-size:10px">${item.name}</div><div style="font-family:Manrope Variable;font-size:20px;margin-top:2px">${num(item.value)} <span style="font-size:10px;opacity:.6">套</span></div>`
      },
    },
    xAxis: {
      type: 'category',
      data: bins.map((b) => b.bin.replace('–', '–')),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, interval: 4, rotate: 0 },
      axisLine: { lineStyle: { color: 'rgba(15,23,42,.14)' } },
    },
    yAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, fontSize: 9 } },
    series: [
      {
        type: 'bar',
        data: bins.map((b) => b.count),
        barWidth: '72%',
        itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: palette.gold },
              { offset: 1, color: 'rgba(29,90,150,.18)' },
            ],
          },
        },
      },
    ],
  }
})

const trendOption = computed<EChartsOption>(() => {
  const trend = data.value?.trend ?? []
  return {
    animationDuration: 800,
    grid: { left: 42, right: 16, top: 30, bottom: 34 },
    tooltip: {
      ...tooltipCommon,
      trigger: 'axis',
      formatter: (params: unknown) => {
        const items = params as { seriesName: string; value: number; axisValue: string; color: string }[]
        return `<div style="font-size:9px;letter-spacing:.1em;opacity:.55">${items[0]?.axisValue}</div>` +
          items.map((i) => `<div style="display:flex;justify-content:space-between;gap:20px;margin-top:4px"><span><i style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${i.color};margin-right:6px"></i>${i.seriesName}</span><b>${i.seriesName === '成交样本' ? `${num(i.value)} 套` : usd(i.value)}</b></div>`).join('')
      },
    },
    legend: {
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 5,
      itemHeight: 5,
      textStyle: { color: '#64748b', fontSize: 9, fontFamily: 'Manrope Variable' },
    },
    xAxis: {
      type: 'category',
      data: trend.map((t) => t.label),
      boundaryGap: false,
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, interval: 1 },
    },
    yAxis: [
      { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${v / 1000}k` } },
      { type: 'value', ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `${v}` } },
    ],
    series: [
      {
        name: '成交样本',
        type: 'bar',
        yAxisIndex: 1,
        data: trend.map((t) => t.count),
        barWidth: '32%',
        itemStyle: { color: 'rgba(15,118,110,.16)', borderRadius: [2, 2, 0, 0] },
      },
      {
        name: '中位价',
        type: 'line',
        data: trend.map((t) => t.median_price),
        smooth: 0.28,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        lineStyle: { color: palette.ink, width: 1.8 },
        itemStyle: { color: palette.gold, borderColor: palette.paper, borderWidth: 2 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(29,90,150,.14)' },
              { offset: 1, color: 'rgba(29,90,150,0)' },
            ],
          },
        },
      },
    ],
  }
})

const areaOption = computed<EChartsOption>(() => {
  const bands = data.value?.area_price_bands ?? []
  return {
    animationDuration: 700,
    grid: { left: 42, right: 12, top: 22, bottom: 34 },
    tooltip: {
      ...tooltipCommon,
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = (params as { name: string; value: number }[])[0]
        return `<div style="font-size:10px">${item.name} sqft</div><div style="font-family:Manrope Variable;font-size:20px">$${item.value}/sqft</div><div style="font-size:9px;opacity:.55">中位成交单价</div>`
      },
    },
    xAxis: { type: 'category', data: bands.map((b) => b.band), ...axisCommon, axisLabel: { ...axisCommon.axisLabel, fontSize: 9 } },
    yAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `$${v}` } },
    series: [
      {
        type: 'bar',
        data: bands.map((b, i) => ({
          value: b.median_ppsf,
          itemStyle: { color: i >= 5 ? palette.clay : i >= 3 ? '#3f7fb8' : palette.sage, borderRadius: [2, 2, 0, 0] },
        })),
        barWidth: '54%',
        markLine: {
          symbol: 'none',
          label: { formatter: '区域中位', color: palette.muted, fontSize: 8, position: 'insideEndTop' },
          lineStyle: { color: 'rgba(15,23,42,.28)', type: 'dashed', width: 1 },
          data: [{ yAxis: overview.value?.median_ppsf ?? 0 }],
        },
      },
    ],
  }
})

const maxZipPrice = computed(() => Math.max(...(data.value?.top_zipcodes.map((z) => z.median_price) ?? [1])))
const maxRegionPrice = computed(() => Math.max(...(data.value?.regions.map((r) => r.median_price) ?? [1])))
</script>

<template>
  <div class="page dashboard-page">
    <PageHeader
      eyebrow="MARKET INTELLIGENCE / 01"
      title="读懂市场，<em>再决定。</em>"
      lede="从 21,418 条真实成交中提取价格结构、空间分布与市场脉搏。所有数字来自公开数据与可复现的训练流程，不用虚构指标装饰结论。"
    >
      <template #actions>
        <button class="btn btn-ghost" :disabled="loading" @click="load">
          <RefreshCw :size="14" :class="{ spinning: loading }" />
          刷新数据
        </button>
        <RouterLink to="/valuation" class="btn btn-primary">
          进入估值工作台
          <ArrowUpRight :size="14" />
        </RouterLink>
      </template>
    </PageHeader>

    <div v-if="error" class="card">
      <EmptyState title="驾驶舱暂时无法加载" :description="error">
        <button class="btn btn-ghost btn-small mt-16" @click="load">重新加载</button>
      </EmptyState>
    </div>

    <template v-else>
      <section class="kpi-strip">
        <div v-if="loading" v-for="i in 4" :key="i" class="skeleton kpi-skeleton" />
        <template v-else>
          <MetricCard
            label="样本成交"
            :value="num(overview?.total_sales)"
            unit="套"
            meta="2014.05 — 2015.05"
            note="去重后保留的真实住宅成交"
          />
          <MetricCard
            label="中位成交价"
            :value="usd(overview?.median_price)"
            meta="USD · 全样本"
            note="均值受豪宅拉动，参考中位数更稳健"
          />
          <MetricCard
            label="中位成交单价"
            :value="`$${num(overview?.median_ppsf)}`"
            unit="/sqft"
            meta="面积加权前的市场刻度"
            note="用于跨面积段比较的价格锚点"
          />
          <MetricCard
            label="覆盖邮编"
            :value="num(overview?.zipcodes)"
            unit="个"
            meta="金县子市场"
            note="70 个邮编进入模型与市场分析"
          />
        </template>
      </section>

      <section class="atlas-grid mt-24">
        <div class="atlas-panel">
          <div class="atlas-head">
            <div>
              <div class="atlas-kicker">PRICE ATLAS / KING COUNTY</div>
              <h2 class="atlas-title">价格不是均匀分布的。</h2>
              <p class="atlas-sub">每个点是一笔真实成交。颜色越浅，成交价越高；位置保留原始经纬度。</p>
            </div>
            <div class="atlas-legend">
              <span v-for="band in priceBands" :key="band.label" class="atlas-legend-item">
                <i :style="{ background: band.color }" />{{ band.label }}
              </span>
            </div>
          </div>
          <div class="atlas-canvas">
            <ChartCanvas :option="mapOption" height="394px" :loading="loading" aria-label="金县成交价格空间分布" />
            <div class="map-corner top-left">47.78°N<br />122.52°W</div>
            <div class="map-corner bottom-right">KING COUNTY<br />WASHINGTON</div>
          </div>
          <div class="atlas-foot">
            <div><span>空间极差</span><strong>{{ usd(maxRegionPrice - (data?.regions.at(-1)?.median_price ?? 0)) }}</strong><small>最高与最低区域中位价差</small></div>
            <div><span>滨水样本</span><strong>{{ pct(overview?.waterfront_share_pct, 2) }}</strong><small>稀缺属性，模型单独捕捉</small></div>
            <div><span>翻新样本</span><strong>{{ pct(overview?.renovated_share_pct, 1) }}</strong><small>翻新溢价为描述性统计</small></div>
          </div>
        </div>

        <aside class="side-stack">
          <div class="card pulse-card">
            <div class="card-head">
              <div>
                <div class="card-label">MARKET PULSE</div>
                <h3 class="card-title">市场脉搏</h3>
              </div>
              <span class="badge badge-sage"><span class="badge-dot" />样本期</span>
            </div>
            <div class="pulse-row" v-if="pulse">
              <div class="pulse-top"><span>滨水 vs 内陆中位价</span><strong class="positive">+{{ pct(pulse.waterfront_premium_pct) }}</strong></div>
              <div class="pulse-track"><span :style="{ width: `${Math.min(100, pulse.waterfront_premium_pct)}%` }" /></div>
              <div class="pulse-foot"><span>{{ usd(pulse.waterfront_median) }}</span><span>{{ usd(pulse.inland_median) }}</span></div>
            </div>
            <div class="pulse-row" v-if="pulse">
              <div class="pulse-top"><span>翻新 vs 未翻新</span><strong>+{{ pct(pulse.renovated_descriptive_gap_pct) }}</strong></div>
              <div class="pulse-track"><span class="gold-track" :style="{ width: `${Math.min(100, pulse.renovated_descriptive_gap_pct * 2.4)}%` }" /></div>
              <div class="pulse-foot"><span>{{ usd(pulse.renovated_median) }}</span><span>{{ usd(pulse.not_renovated_median) }}</span></div>
            </div>
            <div class="pulse-split" v-if="pulse">
              <div><span>样本峰值</span><strong>{{ pulse.peak_month }}</strong><small>{{ usd(pulse.peak_median) }}</small></div>
              <div><span>样本低点</span><strong>{{ pulse.trough_month }}</strong><small>{{ usd(pulse.trough_median) }}</small></div>
            </div>
            <p class="card-caption" v-if="pulse">{{ pulse.note }}</p>
          </div>

          <div class="card zip-card">
            <div class="card-head">
              <div>
                <div class="card-label">TOP SUBMARKETS</div>
                <h3 class="card-title">高价邮编</h3>
              </div>
              <RouterLink to="/research" class="icon-link" aria-label="查看研究实验室"><ArrowUpRight :size="15" /></RouterLink>
            </div>
            <div class="zip-list">
              <div v-for="(zip, index) in data?.top_zipcodes.slice(0, 6)" :key="zip.zipcode" class="zip-row">
                <span class="zip-rank">{{ String(index + 1).padStart(2, '0') }}</span>
                <div class="zip-main">
                  <div class="zip-head"><strong>{{ zip.zipcode }}</strong><span>{{ usd(zip.median_price) }}</span></div>
                  <div class="zip-track"><span :style="{ width: `${(zip.median_price / maxZipPrice) * 100}%` }" /></div>
                </div>
                <span class="zip-count">{{ zip.count }} 套</span>
              </div>
            </div>
          </div>
        </aside>
      </section>

      <section class="grid grid-12 mt-24">
        <div class="span-5 card">
          <div class="card-head">
            <div>
              <div class="card-label">DISTRIBUTION</div>
              <h3 class="card-title">价格分布</h3>
              <p class="card-sub">大部分成交集中在 30–75 万美元；长尾由豪宅构成。</p>
            </div>
            <span class="badge badge-outline">13 个月</span>
          </div>
          <ChartCanvas :option="histogramOption" height="238px" :loading="loading" aria-label="房价分布直方图" />
        </div>

        <div class="span-7 card">
          <div class="card-head">
            <div>
              <div class="card-label">TIME SERIES</div>
              <h3 class="card-title">成交量与中位价</h3>
              <p class="card-sub">柱形为月度成交量，折线为月中位价。样本期短，不作为未来预测。</p>
            </div>
            <span class="badge badge-gold">季节性</span>
          </div>
          <ChartCanvas :option="trendOption" height="238px" :loading="loading" aria-label="月度成交趋势" />
        </div>
      </section>

      <section class="grid grid-12 mt-24">
        <div class="span-7 card">
          <div class="card-head">
            <div>
              <div class="card-label">SUBMARKET LENS</div>
              <h3 class="card-title">区域价格结构</h3>
              <p class="card-sub">区域由经纬度规则划分，用于分析展示，并非官方行政边界。</p>
            </div>
            <RouterLink to="/valuation" class="section-link">在估值中使用 <ArrowUpRight :size="12" /></RouterLink>
          </div>
          <div class="region-table">
            <div class="region-row region-header">
              <span>子市场</span><span>中位价</span><span>单价 / sqft</span><span>样本</span>
            </div>
            <div v-for="region in data?.regions" :key="region.region" class="region-row">
              <div class="region-name">
                <span class="region-marker" />
                <div><strong>{{ region.region }}</strong><small>{{ pct(region.share_pct) }} 的市场样本</small></div>
              </div>
              <div class="region-price">
                <span>{{ usd(region.median_price) }}</span>
                <i><b :style="{ width: `${(region.median_price / maxRegionPrice) * 100}%` }" /></i>
              </div>
              <span class="region-ppsf">${{ num(region.median_ppsf) }}</span>
              <span class="region-count">{{ num(region.count) }}</span>
            </div>
          </div>
        </div>

        <div class="span-5 card">
          <div class="card-head">
            <div>
              <div class="card-label">SIZE & PRICE</div>
              <h3 class="card-title">面积段的单价曲线</h3>
              <p class="card-sub">房屋越大，单价通常越低；小面积段反而更贵。</p>
            </div>
          </div>
          <ChartCanvas :option="areaOption" height="244px" :loading="loading" aria-label="面积段与单价关系" />
          <div class="insight-strip">
            <Sparkles :size="14" />
            <p>面积从 1.2k 增至 5k sqft，中位单价下降约 {{ Math.round(((data?.area_price_bands[0]?.median_ppsf ?? 0) / (data?.area_price_bands.at(-1)?.median_ppsf ?? 1) - 1) * 100) }}%。估值时不要用全城平均单价直接乘面积。</p>
          </div>
        </div>
      </section>

      <section class="research-band mt-32">
        <div class="research-band-head">
          <div>
            <div class="eyebrow" style="color: var(--gold-light)">MODEL TRANSPARENCY / 07</div>
            <h2>模型不是黑箱，<em>数据也不该混着用。</em></h2>
            <p>三个公开数据集各自独立建模。金县用于主估值，UCI 做外部验证，California 做区域对照；不把一个数据集的指标伪装成另一个数据集的成绩。</p>
          </div>
          <RouterLink to="/research" class="btn btn-light">
            打开研究实验室
            <ArrowUpRight :size="15" />
          </RouterLink>
        </div>
        <div class="research-stats">
          <div class="research-stat">
            <span class="rs-label">BEST MODEL / KING COUNTY</span>
            <strong>XGBoost</strong>
            <small>MAE $59.5K · R² 0.9156</small>
          </div>
          <div class="research-stat">
            <span class="rs-label">BASELINE LIFT</span>
            <strong>{{ pct(40.2, 1) }}</strong>
            <small>相对 Ridge 的测试 MAE 降幅</small>
          </div>
          <div class="research-stat">
            <span class="rs-label">INTERVAL COVERAGE</span>
            <strong>81.5%</strong>
            <small>80% 参考区间的实测覆盖率</small>
          </div>
          <div class="research-stat dataset-stat">
            <Database :size="15" />
            <div><strong>3 个独立数据集</strong><small>King County · UCI · California</small></div>
          </div>
        </div>
        <div class="research-band-foot">
          <span><MapPin :size="12" /> 主模型覆盖：King County, WA</span>
          <span>历史成交 · 非当前市场价 · 非正式评估</span>
        </div>
      </section>

      <div class="data-quality">
        <div><span class="badge badge-outline"><Database :size="11" /> DATA HYGIENE</span></div>
        <p>原始 21,613 条 → 清洗后 {{ num(overview?.total_sales) }} 条；移除 177 个重复成交 ID 与结构性异常记录。缺失值在特征工程中显式处理，高价样本保留不截尾。</p>
        <RouterLink to="/research" class="section-link">查看清洗规则 <ArrowUpRight :size="12" /></RouterLink>
      </div>
    </template>
  </div>
</template>

<style scoped>
.kpi-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; border: 1px solid var(--line); background: #ffffff; border-radius: 10px; overflow: hidden; }
.kpi-strip > * { border: 0; border-right: 1px solid var(--line); border-radius: 0; background: transparent; }
.kpi-strip > *:last-child { border-right: 0; }
.kpi-skeleton { height: 137px; border-radius: 0; }
.spinning { animation: spin 0.9s linear infinite; }

.atlas-grid { display: grid; grid-template-columns: minmax(0, 1.72fr) minmax(300px, 0.78fr); gap: 16px; }
.atlas-panel { background: var(--ink); color: var(--paper); border-radius: 10px; padding: 24px 24px 0; overflow: hidden; position: relative; }
.atlas-panel::before { content: ''; position: absolute; right: 0; top: 0; width: 45%; height: 100%; background: radial-gradient(circle at 70% 20%, rgba(29,90,150,.12), transparent 60%); pointer-events: none; }
.atlas-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; position: relative; z-index: 2; }
.atlas-kicker { font-size: 8px; letter-spacing: .2em; color: var(--gold-light); }
.atlas-title { font-family: var(--font-serif);font-size: 27px; font-weight: 650; letter-spacing: -.025em; margin-top: 7px; }
.atlas-sub { font-size: 10.5px; line-height: 1.7; color: rgba(248,250,252,.46); margin-top: 6px; max-width: 420px; }
.atlas-legend { display: flex; flex-wrap: wrap; gap: 9px; max-width: 220px; justify-content: flex-end; }
.atlas-legend-item { display: inline-flex; align-items: center; gap: 4px; font-size: 8px; color: rgba(248,250,252,.52); }
.atlas-legend-item i { width: 5px; height: 5px; border-radius: 50%; }
.atlas-canvas { position: relative; margin: 12px -6px 0; }
.map-corner { position: absolute; font-size: 7px; letter-spacing: .16em; line-height: 1.7; color: rgba(248,250,252,.28); pointer-events: none; }
.map-corner.top-left { top: 9px; left: 8px; }
.map-corner.bottom-right { right: 8px; bottom: 12px; text-align: right; }
.atlas-foot { display: grid; grid-template-columns: repeat(3, 1fr); border-top: 1px solid rgba(248,250,252,.12); margin: 0 -24px; padding: 15px 24px; gap: 16px; }
.atlas-foot > div { display: flex; flex-direction: column; gap: 3px; }
.atlas-foot span { font-size: 7.5px; letter-spacing: .14em; color: rgba(248,250,252,.34); text-transform: uppercase; }
.atlas-foot strong { font-family: var(--font-serif); font-size: 20px; font-weight: 650; color: var(--paper); }
.atlas-foot small { font-size: 8.5px; color: rgba(248,250,252,.36); line-height: 1.5; }

.side-stack { display: flex; flex-direction: column; gap: 16px; }
.pulse-card { flex: 1; }
.pulse-row { margin-top: 15px; }
.pulse-top { display: flex; justify-content: space-between; font-size: 10px; margin-bottom: 6px; }
.pulse-top span { color: var(--muted); }
.pulse-top strong { font-weight: 700; }
.positive { color: var(--positive); }
.pulse-track { height: 3px; background: var(--paper-3); border-radius: 7px; overflow: hidden; }
.pulse-track span { display: block; height: 100%; background: var(--sage); border-radius: 7px; }
.pulse-track .gold-track { background: var(--gold); }
.pulse-foot { display: flex; justify-content: space-between; font-size: 8.5px; color: var(--muted-light); margin-top: 5px; }
.pulse-split { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); margin: 17px 0 12px; padding: 12px 0; }
.pulse-split > div { display: flex; flex-direction: column; gap: 3px; }
.pulse-split > div + div { border-left: 1px solid var(--line-soft); padding-left: 16px; }
.pulse-split span { font-size: 8px; letter-spacing: .1em; color: var(--muted); }
.pulse-split strong { font-family: var(--font-serif); font-size: 15px; font-weight: 650; }
.pulse-split small { font-size: 9px; color: var(--muted-light); }
.card-caption { font-size: 8.5px; line-height: 1.6; color: var(--muted-light); }
.zip-card { flex: 0 0 auto; }
.icon-link { color: var(--muted); display: inline-flex; }
.icon-link:hover { color: var(--gold); }
.zip-list { display: flex; flex-direction: column; gap: 10px; }
.zip-row { display: flex; align-items: center; gap: 9px; }
.zip-rank { font-size: 8px; color: var(--muted-light); width: 15px; font-variant-numeric: tabular-nums; }
.zip-main { flex: 1; min-width: 0; }
.zip-head { display: flex; justify-content: space-between; font-size: 9.5px; gap: 8px; }
.zip-head strong { font-weight: 650; letter-spacing: .04em; }
.zip-head span { color: var(--muted); font-variant-numeric: tabular-nums; }
.zip-track { height: 2px; background: var(--paper-3); margin-top: 5px; border-radius: 6px; overflow: hidden; }
.zip-track span { display: block; height: 100%; background: linear-gradient(90deg, var(--sage), var(--gold)); }
.zip-count { font-size: 8px; color: var(--muted-light); width: 28px; text-align: right; }

.region-table { font-size: 10.5px; }
.region-row { display: grid; grid-template-columns: 1.25fr 1.3fr .8fr .45fr; align-items: center; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--line-soft); }
.region-row:last-child { border-bottom: 0; }
.region-header { padding: 0 0 8px; font-size: 8px; letter-spacing: .12em; color: var(--muted); border-bottom: 1px solid var(--line); }
.region-name { display: flex; align-items: center; gap: 8px; }
.region-marker { width: 4px; height: 4px; border-radius: 50%; background: var(--gold); flex: 0 0 auto; }
.region-name div { display: flex; flex-direction: column; gap: 1px; }
.region-name strong { font-size: 10.5px; font-weight: 620; }
.region-name small { font-size: 8px; color: var(--muted-light); }
.region-price { display: flex; align-items: center; gap: 8px; }
.region-price > span { width: 61px; font-variant-numeric: tabular-nums; }
.region-price i { flex: 1; height: 3px; background: var(--paper-3); border-radius: 6px; overflow: hidden; }
.region-price b { display: block; height: 100%; background: var(--sage); border-radius: 6px; }
.region-ppsf, .region-count { font-variant-numeric: tabular-nums; color: var(--muted); }
.insight-strip { display: flex; gap: 9px; align-items: flex-start; border-top: 1px solid var(--line-soft); padding-top: 12px; margin-top: 8px; color: var(--gold); }
.insight-strip p { font-size: 9.5px; line-height: 1.65; color: var(--muted); }

.research-band { background: var(--ink); color: var(--paper); border-radius: 10px; padding: 30px; position: relative; overflow: hidden; }
.research-band::after { content: 'HM'; position: absolute; right: 20px; bottom: -58px; font-family: var(--font-serif); font-size: 210px; color: rgba(248,250,252,.025); line-height: 1; pointer-events: none; }
.research-band-head { display: flex; justify-content: space-between; gap: 30px; align-items: flex-start; position: relative; z-index: 1; }
.research-band h2 { font-family: var(--font-serif); font-size: clamp(28px, 2.6vw, 38px); font-weight: 650; letter-spacing: -.03em; margin-top: 11px; line-height: 1.14; }
.research-band h2 em { color: var(--gold-light); font-weight: 380; }
.research-band p { max-width: 690px; font-size: 11.5px; line-height: 1.8; color: rgba(248,250,252,.5); margin-top: 12px; }
.research-stats { display: grid; grid-template-columns: repeat(2, 1fr) 1.1fr; border-top: 1px solid rgba(248,250,252,.13); margin-top: 27px; padding-top: 20px; position: relative; z-index: 1; }
.research-stat { display: flex; flex-direction: column; gap: 4px; padding-right: 22px; }
.research-stat + .research-stat { border-left: 1px solid rgba(248,250,252,.13); padding-left: 22px; }
.rs-label { font-size: 7.5px; letter-spacing: .15em; color: rgba(248,250,252,.34); }
.research-stat strong { font-family: var(--font-serif); font-size: 26px; font-weight: 650; color: var(--paper); margin-top: 3px; }
.research-stat small { font-size: 8.5px; color: rgba(248,250,252,.38); }
.dataset-stat { flex-direction: row; align-items: center; gap: 10px; border-left: 1px solid rgba(248,250,252,.13); padding-left: 22px; color: var(--gold-light); }
.dataset-stat div { display: flex; flex-direction: column; gap: 3px; }
.dataset-stat strong { font-family: var(--font-sans); font-size: 11px; font-weight: 600; }
.dataset-stat small { font-size: 8px; }
.research-band-foot { display: flex; justify-content: space-between; margin-top: 24px; padding-top: 13px; border-top: 1px solid rgba(248,250,252,.1); font-size: 8px; letter-spacing: .08em; color: rgba(248,250,252,.33); position: relative; z-index: 1; }
.research-band-foot span { display: inline-flex; align-items: center; gap: 5px; }
.data-quality { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 18px; margin-top: 17px; padding: 14px 2px; border-bottom: 1px solid var(--line); }
.data-quality p { font-size: 9.5px; color: var(--muted); line-height: 1.65; }

@media (max-width: 1180px) {
  .atlas-grid { grid-template-columns: 1fr; }
  .side-stack { display: grid; grid-template-columns: 1fr 1fr; }
}
@media (max-width: 800px) {
  .kpi-strip { grid-template-columns: 1fr 1fr; }
  .kpi-strip > *:nth-child(2) { border-right: 0; }
  .kpi-strip > *:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
  .side-stack { grid-template-columns: 1fr; }
  .atlas-head { flex-direction: column; }
  .atlas-legend { justify-content: flex-start; max-width: none; }
  .atlas-foot { grid-template-columns: 1fr 1fr; }
  .research-band { padding: 22px; }
  .research-band-head { flex-direction: column; }
  .research-stats { grid-template-columns: 1fr 1fr; gap: 16px 0; }
  .dataset-stat { grid-column: 1 / -1; border-left: 0 !important; padding-left: 0 !important; border-top: 1px solid rgba(248,250,252,.13); padding-top: 13px; }
  .research-band-foot { flex-direction: column; gap: 6px; }
  .data-quality { grid-template-columns: 1fr; gap: 8px; }
}
@media (max-width: 520px) {
  .kpi-strip { grid-template-columns: 1fr; }
  .kpi-strip > * { border-right: 0 !important; border-bottom: 1px solid var(--line); }
  .kpi-strip > *:last-child { border-bottom: 0; }
  .atlas-panel { padding: 19px 17px 0; }
  .atlas-foot { margin: 0 -17px; padding: 13px 17px; grid-template-columns: 1fr; gap: 9px; }
  .atlas-foot > div { flex-direction: row; align-items: baseline; gap: 8px; }
  .atlas-foot strong { font-size: 16px; }
  .atlas-title { font-size: 23px; }
  .region-row { grid-template-columns: 1.1fr 1fr .65fr .35fr; gap: 7px; }
  .region-price i { display: none; }
}
</style>
