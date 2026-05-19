<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="title">断层多边形追踪</h1>
      <p class="subtitle">Fault Polygon Auto-Tracking</p>
      <div class="accent-line"></div>
    </div>

    <nav class="nav-links">
      <router-link to="/pipeline" class="nav-item" active-class="nav-item--active">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
        </span>
        分步流水线
      </router-link>
      <router-link to="/explore" class="nav-item" active-class="nav-item--active">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </span>
        交互探索
      </router-link>
      <router-link to="/compare" class="nav-item" active-class="nav-item--active">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        </span>
        结果对比
      </router-link>
    </nav>

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
        :on-change="handleFileChange"
        style="width:100%"
      >
        <el-button :loading="dataStore.running" style="width:100%">
          {{ dataStore.running ? '加载中...' : '上传文件 (.npy/.npz/.dat)' }}
        </el-button>
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
import { ElMessage } from 'element-plus'
import { useDataStore } from '@/stores/data'
import { useParamsStore } from '@/stores/params'
import ParamPanel from './ParamPanel.vue'
import type { UploadFile, UploadRawFile } from 'element-plus'

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

function handleFileChange(file: UploadFile) {
  const raw = file.raw as UploadRawFile
  if (!raw) return
  const ext = '.' + raw.name.split('.').pop()?.toLowerCase()
  if (!['.dat', '.npy', '.npz'].includes(ext)) {
    ElMessage.error(`不支持的文件格式 ${ext}`)
    return
  }
  dataStore.upload(raw)
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

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 12px;
  margin-bottom: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: #475569;
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.15s;
}

.nav-item:hover {
  background: #E2E8F0;
  color: #1E293B;
}

.nav-item--active {
  background: #DBEAFE;
  color: #2563EB;
  font-weight: 600;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #E5E7EB;
}
</style>
