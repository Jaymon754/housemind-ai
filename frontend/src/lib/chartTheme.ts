export const palette = {
  ink: '#0f172a',
  inkSoft: '#334155',
  paper: '#ffffff',
  gold: '#1d5a96',
  goldLight: '#77a8d4',
  sage: '#0f766e',
  sageLight: '#99f6e4',
  clay: '#b42318',
  line: 'rgba(15,23,42,0.12)',
  muted: '#64748b',
}

export const axisCommon = {
  axisLine: { lineStyle: { color: 'rgba(15,23,42,0.14)' } },
  axisTick: { show: false },
  axisLabel: { color: '#64748b', fontSize: 10.5, fontFamily: 'Manrope Variable, PingFang SC, sans-serif' },
  splitLine: { lineStyle: { color: 'rgba(15,23,42,0.06)', type: 'dashed' as const } },
}

export const tooltipCommon = {
  backgroundColor: '#0f172a',
  borderWidth: 0,
  padding: [10, 13],
  textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Manrope Variable, PingFang SC, sans-serif' },
  extraCssText: 'border-radius:8px;box-shadow:0 12px 30px rgba(15,23,42,.22);',
}
