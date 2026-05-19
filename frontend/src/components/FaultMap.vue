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


function buildOption(): echarts.EChartsOption {
  const series: any[] = []

  if ((props.layer === 'heatmap' || props.layer === 'binary') && props.heatmap) {
    const data = props.heatmap
    const h = data.length
    const w = data[0]?.length || 0
    const heatData: [number, number, number][] = []
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        heatData.push([c, r, data[r][c]])
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
      const coords = poly.map(([r, c]: number[]) => [c, r])
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
    const skel: number[][] = props.skeleton
    const h = skel.length
    const w = skel[0]?.length || 0
    const skelData: [number, number][] = []
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        if (skel[r][c]) skelData.push([c, r])
      }
    }
    if (skelData.length > 0) {
      series.push({
        type: 'scatter',
        data: skelData,
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

  const h = props.heatmap?.length || 0
  const w = props.heatmap?.[0]?.length || 0
  const xCats = Array.from({ length: w }, (_, i) => i)
  const yCats = Array.from({ length: h }, (_, i) => i)

  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'category', data: xCats, show: false, boundaryGap: true },
    yAxis: { type: 'category', data: yCats, show: false, boundaryGap: true, inverse: true },
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
