export const palette = {
  ink: '#10231d',
  inkSoft: '#294038',
  paper: '#fbf8f1',
  gold: '#b08a52',
  goldLight: '#d8bc8c',
  sage: '#6f8a76',
  sageLight: '#a6b9a9',
  clay: '#b46b52',
  line: 'rgba(16,35,29,0.12)',
  muted: '#737a72',
}

export const axisCommon = {
  axisLine: { lineStyle: { color: 'rgba(16,35,29,0.16)' } },
  axisTick: { show: false },
  axisLabel: { color: '#737a72', fontSize: 11, fontFamily: 'Manrope, PingFang SC, sans-serif' },
  splitLine: { lineStyle: { color: 'rgba(16,35,29,0.07)', type: 'dashed' as const } },
}

export const tooltipCommon = {
  backgroundColor: '#10231d',
  borderWidth: 0,
  padding: [10, 13],
  textStyle: { color: '#f8f2e7', fontSize: 12, fontFamily: 'Manrope, PingFang SC, sans-serif' },
  extraCssText: 'border-radius:6px;box-shadow:0 12px 30px rgba(10,25,20,.22);',
}
