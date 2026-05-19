<template>
  <div ref="chartRef" class="fault-map" @contextmenu.prevent></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  heatmap?: number[][]
  contours?: number[][][]
  filtered?: number[][][]
  skeleton?: number[][]
  junctions?: [number, number][]
  layer?: 'heatmap' | 'binary' | 'polygons'
  height?: string
}>(), {
  layer: 'heatmap',
  height: '100%',
})

const emit = defineEmits<{ clickPolygon: [index: number] }>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

/** 降采样 2D 数组，限制最大采样点数防止 ECharts 渲染卡顿 */
function downsample(data: number[][], maxRows = 200, maxCols = 200): number[][] {
  const h = data.length
  const w = data[0]?.length || 0
  if (h <= maxRows && w <= maxCols) return data

  const rowStep = Math.max(1, Math.ceil(h / maxRows))
  const colStep = Math.max(1, Math.ceil(w / maxCols))
  const result: number[][] = []
  for (let r = 0; r < h; r += rowStep) {
    const row: number[] = []
    for (let c = 0; c < w; c += colStep) {
      row.push(data[r][c])
    }
    result.push(row)
  }
  return result
}

/** 降采样骨架二值图，只提取非零点 */
function extractPoints(binary: number[][], maxPts = 50000): [number, number][] {
  const h = binary.length
  const w = binary[0]?.length || 0
  const step = Math.max(1, Math.ceil(Math.sqrt((h * w) / maxPts)))
  const pts: [number, number][] = []
  for (let r = 0; r < h; r += step) {
    for (let c = 0; c < w; c += step) {
      if (binary[r][c]) pts.push([c, r])
    }
  }
  // 如果 step > 1，也检查非采样点避免丢失骨架
  if (step > 1) {
    return pts
  }
  return pts
}

function buildOption(): echarts.EChartsOption {
  const series: any[] = []

  if ((props.layer === 'heatmap' || props.layer === 'binary') && props.heatmap) {
    const sampled = downsample(props.heatmap)
    const h = sampled.length
    const w = sampled[0]?.length || 0
    const heatData: [number, number, number][] = []
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        heatData.push([c, r, sampled[r][c]])
      }
    }
    series.push({
      type: 'heatmap',
      data: heatData,
      label: { show: false },
      emphasis: { disabled: true },
      itemStyle: { borderWidth: 0 },
    })
  }

  if (props.filtered && props.filtered.length > 0) {
    const colors = [
      '#2563EB', '#EF4444', '#22C55E', '#F59E0B', '#8B5CF6',
      '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16',
    ]
    props.filtered.forEach((poly, idx) => {
      // 对大多边形也降采样顶点
      const step = Math.max(1, Math.floor(poly.length / 500))
      const coords = poly
        .filter((_: number[], i: number) => i % step === 0)
        .map(([r, c]: number[]) => [c, r])
      series.push({
        type: 'line',
        data: coords,
        silent: false,
        polyline: false,
        lineStyle: { color: colors[idx % colors.length], width: 2 },
        z: 10,
        name: `polygon_${idx}`,
      })
    })
  }

  if (props.skeleton) {
    const skelPts = extractPoints(props.skeleton)
    if (skelPts.length > 0) {
      series.push({
        type: 'scatter',
        data: skelPts,
        symbolSize: 2,
        itemStyle: { color: '#94A3B8' },
        z: 5,
      })
    }
  }

  if (props.junctions && props.junctions.length > 0) {
    series.push({
      type: 'scatter',
      data: props.junctions.map(([r, c]: [number, number]) => [c, r]),
      symbolSize: 8,
      itemStyle: { color: '#EF4444', borderColor: '#fff', borderWidth: 1 },
      z: 15,
    })
  }

  const sampled = props.heatmap ? downsample(props.heatmap) : null
  const h = sampled?.length || 0
  const w = sampled?.[0]?.length || 0

  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'value', min: 0, max: w, show: false },
    yAxis: { type: 'value', min: h, max: 0, show: false },
    visualMap: props.layer === 'binary'
      ? { min: 0, max: 1, inRange: { color: ['#0F172A', '#F8FAFC'] }, show: false }
      : { min: 0, max: 1, inRange: { color: ['#0F172A', '#2563EB', '#60A5FA', '#BFDBFE', '#F8FAFC'] }, show: false },
    series,
    animation: false,
  }
}

function renderChart() {
  if (!chart || !chartRef.value) return
  chart.setOption(buildOption(), true)
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()

  chart.on('click', (params: any) => {
    if (params.seriesName?.startsWith('polygon_')) {
      const idx = parseInt(params.seriesName.replace('polygon_', ''))
      emit('clickPolygon', idx)
    }
  })
}

function handleResize() { chart?.resize() }

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})

// 浅监听 — 只比较引用，不递归遍历数组
watch(
  () => [props.layer, props.heatmap, props.filtered, props.skeleton, props.junctions],
  () => renderChart(),
)
</script>

<style scoped>
.fault-map {
  width: 100%;
  height: v-bind(height);
  min-height: 300px;
}
</style>
