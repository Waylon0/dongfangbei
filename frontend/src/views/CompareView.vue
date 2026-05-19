<template>
  <div class="compare-view">
    <div class="compare-header">
      <div class="compare-title">对比分析</div>
      <p class="compare-desc">两组参数独立运行，对比追踪结果差异</p>
    </div>

    <div class="dual-params">
      <div class="param-col">
        <h4>参数集 A</h4>
        <ParamPanelB @run="runA" :loading="loadingA" label="运行 A" />
      </div>
      <div class="param-col">
        <h4>参数集 B</h4>
        <ParamPanelB @run="runB" :loading="loadingB" label="运行 B" />
      </div>
    </div>

    <div class="compare-charts" v-if="resultA || resultB">
      <div class="chart-col">
        <span class="chart-label">结果 A</span>
        <FaultMap
          v-if="resultA"
          :heatmap="dataStore.rawData!"
          :filtered="resultA.filtered"
          layer="heatmap"
          height="100%"
        />
        <div v-else class="chart-placeholder">未运行</div>
      </div>
      <div class="chart-col">
        <span class="chart-label">结果 B</span>
        <FaultMap
          v-if="resultB"
          :heatmap="dataStore.rawData!"
          :filtered="resultB.filtered"
          layer="heatmap"
          height="100%"
        />
        <div v-else class="chart-placeholder">未运行</div>
      </div>
    </div>

    <div v-if="resultA || resultB" class="stats-table-wrap">
      <el-table :data="compareTableData" size="small" border stripe style="width:100%">
        <el-table-column prop="metric" label="指标" width="140" />
        <el-table-column prop="a" label="参数集 A" />
        <el-table-column prop="b" label="参数集 B" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDataStore } from '@/stores/data'
import type { PipelineResult, PipelineParams } from '@/types'
import { runPipeline } from '@/api/pipeline'
import FaultMap from '@/components/FaultMap.vue'
import ParamPanelB from '@/components/ParamPanelB.vue'
import { ElMessage } from 'element-plus'

const dataStore = useDataStore()

const resultA = ref<PipelineResult | null>(null)
const resultB = ref<PipelineResult | null>(null)
const loadingA = ref(false)
const loadingB = ref(false)

async function runA(params: PipelineParams) {
  if (!dataStore.rawData) { ElMessage.warning('请先生成数据'); return }
  loadingA.value = true
  try {
    resultA.value = await runPipeline(dataStore.rawData, params)
    ElMessage.success(`A 完成，${resultA.value.filtered.length} 个多边形`)
  } catch (e: any) {
    ElMessage.error(`A 失败: ${e.message}`)
  } finally { loadingA.value = false }
}

async function runB(params: PipelineParams) {
  if (!dataStore.rawData) { ElMessage.warning('请先生成数据'); return }
  loadingB.value = true
  try {
    resultB.value = await runPipeline(dataStore.rawData, params)
    ElMessage.success(`B 完成，${resultB.value.filtered.length} 个多边形`)
  } catch (e: any) {
    ElMessage.error(`B 失败: ${e.message}`)
  } finally { loadingB.value = false }
}

const compareTableData = computed(() => {
  const rows: any[] = []
  const ra = resultA.value, rb = resultB.value

  const stats = (r: PipelineResult | null) => {
    if (!r || r.areas.length === 0) return { count: 0, min: '-', max: '-', mean: '-', median: '-', elapsed: '-' }
    const a = [...r.areas].sort((x, y) => x - y)
    return {
      count: r.filtered.length,
      min: Math.min(...a).toFixed(0),
      max: Math.max(...a).toFixed(0),
      mean: (a.reduce((s, v) => s + v, 0) / a.length).toFixed(0),
      median: a[Math.floor(a.length / 2)].toFixed(0),
      elapsed: r.elapsed.toFixed(2) + 's',
    }
  }

  const sa = stats(ra), sb = stats(rb)
  const metrics = ['count', 'min', 'max', 'mean', 'median', 'elapsed']
  const labels: Record<string, string> = {
    count: '多边形数量', min: '最小面积 (px²)', max: '最大面积 (px²)',
    mean: '平均面积 (px²)', median: '中位数面积 (px²)', elapsed: '耗时',
  }

  for (const m of metrics) {
    rows.push({ metric: labels[m], a: String(sa[m as keyof typeof sa]), b: String(sb[m as keyof typeof sb]) })
  }
  return rows
})
</script>

<style scoped>
.compare-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  padding: 16px;
}

.compare-header { margin-bottom: 12px; }
.compare-title { font-size: 20px; font-weight: 700; color: #1E293B; }
.compare-desc { font-size: 13px; color: #64748B; margin: 2px 0 0; }

.dual-params { display: flex; gap: 16px; margin-bottom: 12px; }
.param-col { flex: 1; padding: 12px; background: #fff; border: 1px solid #E5E7EB; border-radius: 8px; }
.param-col h4 { font-size: 14px; font-weight: 600; color: #1E293B; margin: 0 0 8px; }

.compare-charts { flex: 1; display: flex; gap: 16px; min-height: 0; margin-bottom: 12px; }
.chart-col { flex: 1; display: flex; flex-direction: column; border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }
.chart-label { padding: 6px 12px; font-size: 13px; font-weight: 600; color: #475569; background: #FAFBFC; border-bottom: 1px solid #E5E7EB; }
.chart-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; color: #94A3B8; }

.stats-table-wrap { max-height: 240px; overflow-y: auto; }
</style>
