<template>
  <div class="pipeline-view">
    <StepProgress :current="currentStep" @go="setStep" />

    <div class="chart-area">
      <template v-if="dataStore.hasResult">
        <!-- Step 0: 原始数据热力图 -->
        <FaultMap
          v-if="currentStep === 0"
          :heatmap="dataStore.rawData!"
          layer="heatmap"
        />

        <!-- Step 1: 预处理 — 平滑数据 -->
        <FaultMap
          v-if="currentStep === 1"
          :heatmap="dataStore.result!.data_smoothed"
          layer="heatmap"
        />

        <!-- Step 2: 形态学 — 前后对比 -->
        <div v-if="currentStep === 2" class="split-chart">
          <div class="split-pane">
            <span class="pane-label">处理前</span>
            <FaultMap :heatmap="dataStore.result!.binary_before_morph" layer="binary" height="100%" />
          </div>
          <div class="split-pane">
            <span class="pane-label">处理后</span>
            <FaultMap :heatmap="dataStore.result!.binary" layer="binary" height="100%" />
          </div>
        </div>

        <!-- Step 3: 轮廓提取 -->
        <FaultMap
          v-if="currentStep === 3"
          :heatmap="dataStore.rawData!"
          :contours="dataStore.result!.contours"
          layer="heatmap"
        />

        <!-- Step 4: 骨架 + 交叉点 -->
        <FaultMap
          v-if="currentStep === 4"
          :heatmap="dataStore.result!.binary"
          :skeleton="dataStore.result!.skeleton"
          :junctions="dataStore.result!.junctions"
          layer="binary"
        />

        <!-- Step 5: 最终结果 -->
        <FaultMap
          v-if="currentStep === 5"
          :heatmap="dataStore.rawData!"
          :filtered="dataStore.result!.filtered"
          layer="heatmap"
        />

        <!-- Step 6: 总览 -->
        <div v-if="currentStep === 6" class="overview-grid">
          <div class="overview-item">
            <span class="overview-label">原始数据</span>
            <FaultMap :heatmap="dataStore.rawData!" layer="heatmap" height="100%" />
          </div>
          <div class="overview-item">
            <span class="overview-label">平滑后</span>
            <FaultMap :heatmap="dataStore.result!.data_smoothed" layer="heatmap" height="100%" />
          </div>
          <div class="overview-item">
            <span class="overview-label">二值化</span>
            <FaultMap :heatmap="dataStore.result!.binary" layer="binary" height="100%" />
          </div>
          <div class="overview-item">
            <span class="overview-label">骨架</span>
            <FaultMap
              :heatmap="dataStore.result!.binary"
              :skeleton="dataStore.result!.skeleton"
              :junctions="dataStore.result!.junctions"
              layer="binary"
              height="100%"
            />
          </div>
          <div class="overview-item">
            <span class="overview-label">最终结果</span>
            <FaultMap
              :heatmap="dataStore.rawData!"
              :filtered="dataStore.result!.filtered"
              layer="heatmap"
              height="100%"
            />
          </div>
          <div class="overview-item overview-stats">
            <span class="overview-label">统计</span>
            <div class="stats-list">
              <div class="stat-item">
                <span class="stat-num">{{ dataStore.result!.filtered.length }}</span>
                <span class="stat-unit">多边形</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ dataStore.result!.elapsed }}s</span>
                <span class="stat-unit">耗时</span>
              </div>
              <div class="stat-item" v-if="areaStats">
                <span class="stat-num">{{ areaStats.min }}</span>
                <span class="stat-unit">最小面积</span>
              </div>
              <div class="stat-item" v-if="areaStats">
                <span class="stat-num">{{ areaStats.max }}</span>
                <span class="stat-unit">最大面积</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else class="empty-state">
        <el-empty description="在左侧边栏生成或上传数据，然后点击「运行追踪」" :image-size="120" />
      </div>
    </div>

    <!-- 步骤说明卡片 -->
    <div v-if="dataStore.hasResult" class="desc-card">
      <div class="desc-border"></div>
      <div class="desc-content">
        <h3>{{ PIPELINE_STEPS[currentStep].title }}</h3>
        <p>{{ PIPELINE_STEPS[currentStep].description }}</p>
      </div>
    </div>

    <!-- 底部控制栏 -->
    <div v-if="dataStore.hasResult" class="control-bar">
      <el-button @click="prevStep" :disabled="currentStep === 0">上一步</el-button>
      <el-button @click="nextStep" :disabled="currentStep === 6" style="margin-left:0">下一步</el-button>
      <el-divider direction="vertical" />
      <el-select v-model="currentStep" @change="setStep" size="small" style="width:140px">
        <el-option v-for="(s, i) in PIPELINE_STEPS" :key="s.key" :label="`${i + 1}. ${s.title}`" :value="i" />
      </el-select>
      <el-divider direction="vertical" />
      <el-button text @click="toggleAutoPlay" :type="autoPlay ? 'primary' : 'default'">
        {{ autoPlay ? '暂停' : '自动播放' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useDataStore } from '@/stores/data'
import { PIPELINE_STEPS } from '@/types'
import StepProgress from '@/components/StepProgress.vue'
import FaultMap from '@/components/FaultMap.vue'

const dataStore = useDataStore()
const currentStep = ref(0)
const autoPlay = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const areaStats = computed(() => {
  const areas = dataStore.result?.areas
  if (!areas || areas.length === 0) return null
  return {
    min: Math.min(...areas).toFixed(0),
    max: Math.max(...areas).toFixed(0),
    mean: (areas.reduce((a, b) => a + b, 0) / areas.length).toFixed(0),
  }
})

function setStep(i: number) { currentStep.value = i }
function prevStep() { if (currentStep.value > 0) currentStep.value-- }
function nextStep() { if (currentStep.value < 6) currentStep.value++ }

function toggleAutoPlay() {
  autoPlay.value = !autoPlay.value
  if (autoPlay.value) {
    timer = setInterval(() => {
      if (currentStep.value < 6) currentStep.value++
      else { autoPlay.value = false; if (timer) clearInterval(timer) }
    }, 2500)
  } else {
    if (timer) { clearInterval(timer); timer = null }
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') prevStep()
  if (e.key === 'ArrowRight') nextStep()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (timer) clearInterval(timer)
})

watch(() => dataStore.result, () => { currentStep.value = 0 })
</script>

<style scoped>
.pipeline-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.chart-area {
  flex: 1;
  min-height: 0;
  padding: 16px;
}

.split-chart {
  display: flex;
  gap: 12px;
  height: 100%;
}

.split-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.pane-label {
  font-size: 12px;
  color: #64748B;
  margin-bottom: 4px;
  text-align: center;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 8px;
  height: 100%;
}

.overview-item {
  position: relative;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  overflow: hidden;
  min-height: 0;
}

.overview-label {
  position: absolute;
  top: 4px;
  left: 8px;
  font-size: 11px;
  color: #64748B;
  z-index: 10;
  background: rgba(255,255,255,0.85);
  padding: 1px 6px;
  border-radius: 3px;
}

.overview-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #F8FAFC;
}

.stats-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #2563EB;
}

.stat-unit {
  font-size: 11px;
  color: #64748B;
}

.desc-card {
  display: flex;
  margin: 0 16px 12px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  overflow: hidden;
}

.desc-border {
  width: 4px;
  background: #2563EB;
  flex-shrink: 0;
}

.desc-content {
  padding: 10px 16px;
}

.desc-content h3 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #1E293B;
}

.desc-content p {
  margin: 0;
  font-size: 13px;
  color: #64748B;
  line-height: 1.5;
}

.control-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-top: 1px solid #E5E7EB;
  background: #FAFBFC;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
