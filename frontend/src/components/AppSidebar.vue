<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="title">断层多边形追踪</h1>
      <p class="subtitle">Fault Polygon Auto-Tracking</p>
      <div class="accent-line"></div>
    </div>

    <div class="section">
      <h3 class="section-title">数据源</h3>
      <div class="data-source">
        <div class="gen-row">
          <span class="label">行</span>
          <el-input-number v-model="genRows" :min="50" :max="1000" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">列</span>
          <el-input-number v-model="genCols" :min="50" :max="1000" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">断层数</span>
          <el-input-number v-model="genFaults" :min="1" :max="20" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">噪声</span>
          <el-input-number v-model="genNoise" :min="0" :max="0.2" :step="0.01" :precision="2" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">种子</span>
          <el-input-number v-model="genSeed" :min="0" :max="9999" size="small" controls-position="right" />
        </div>
        <el-button type="primary" @click="handleGenerate" :loading="dataStore.running" style="width:100%">
          生成合成数据
        </el-button>
      </div>
      <el-divider style="margin:12px 0"><span style="color:#94a3b8;font-size:12px">或</span></el-divider>
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        accept=".npy,.npz,.dat"
        style="width:100%"
      >
        <el-button style="width:100%">上传文件 (.npy/.npz/.dat)</el-button>
      </el-upload>
      <div v-if="dataStore.hasData" class="data-status">
        <span class="status-dot"></span>
        已加载 {{ dataStore.dataShape[0] }} x {{ dataStore.dataShape[1] }}
      </div>
    </div>

    <div class="section params-section">
      <h3 class="section-title">算法参数</h3>
      <ParamPanel />
      <el-button @click="paramsStore.reset()" style="width:100%;margin-top:8px">重置默认</el-button>
    </div>

    <div class="sidebar-footer">
      <el-button
        type="primary"
        size="large"
        @click="dataStore.execute()"
        :loading="dataStore.running"
        :disabled="!dataStore.hasData"
        style="width:100%"
      >
        {{ dataStore.running ? '运行中...' : '运行追踪' }}
      </el-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDataStore } from '@/stores/data'
import { useParamsStore } from '@/stores/params'
import ParamPanel from './ParamPanel.vue'

const dataStore = useDataStore()
const paramsStore = useParamsStore()

const genRows = ref(300)
const genCols = ref(400)
const genFaults = ref(5)
const genNoise = ref(0.03)
const genSeed = ref(42)

function handleGenerate() {
  dataStore.generate(genRows.value, genCols.value, genFaults.value, genNoise.value, genSeed.value)
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  background: #F1F4F8;
  border-right: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 20px 16px 12px;
}

.title {
  font-size: 18px;
  font-weight: 700;
  color: #1E293B;
  margin: 0;
  line-height: 1.3;
}

.subtitle {
  font-size: 11px;
  color: #64748B;
  margin: 2px 0 0;
  letter-spacing: 0.5px;
}

.accent-line {
  width: 32px;
  height: 3px;
  background: #2563EB;
  border-radius: 2px;
  margin-top: 10px;
}

.section {
  padding: 8px 16px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px;
}

.data-source {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gen-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.gen-row .label {
  font-size: 13px;
  color: #475569;
  min-width: 44px;
}

.gen-row :deep(.el-input-number) {
  width: 130px;
}

.data-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #22C55E;
  margin-top: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #22C55E;
  border-radius: 50%;
}

.params-section {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #E5E7EB;
}
</style>
