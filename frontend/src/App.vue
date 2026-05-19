<template>
  <div class="app-shell" @dragenter.prevent="onDragEnter" @dragover.prevent>
    <AppSidebar />
    <main class="main-content">
      <router-view />
    </main>

    <!-- 全局拖拽覆盖层 -->
    <Teleport to="body">
      <transition name="drop-fade">
        <div
          v-if="dragging"
          class="drop-overlay"
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
        >
          <div class="drop-zone">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p class="drop-title">释放文件以加载数据</p>
            <p class="drop-hint">支持 .dat / .npy / .npz 格式</p>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppSidebar from '@/components/AppSidebar.vue'
import { useDataStore } from '@/stores/data'

const dataStore = useDataStore()

const dragging = ref(false)
let dragCounter = 0

const ALLOWED = ['.dat', '.npy', '.npz']

function hasAllowedFile(e: DragEvent): boolean {
  return e.dataTransfer?.types.includes('Files') ?? false
}

function onDragEnter(e: DragEvent) {
  if (!hasAllowedFile(e)) return
  dragCounter++
  dragging.value = true
}

function onDragLeave(e: DragEvent) {
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    dragging.value = false
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  dragCounter = 0
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return

  const file = files[0]
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!ALLOWED.includes(ext)) {
    ElMessage.error(`不支持的文件格式 ${ext}，请上传 .dat / .npy / .npz`)
    return
  }

  dataStore.upload(file)
}
</script>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial,
    sans-serif;
  font-size: 14px;
  color: #1E293B;
  background: #FAFBFC;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

:root {
  --el-color-primary: #2563EB;
  --el-color-primary-hover: #1D4ED8;
  --el-border-color-base: #E5E7EB;
}

::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-thumb {
  background: #CBD5E1;
  border-radius: 2px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

/* 拖拽覆盖层 */
.drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(37, 99, 235, 0.08);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-zone {
  background: #FFFFFF;
  border: 2px dashed #2563EB;
  border-radius: 16px;
  padding: 48px 64px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(37, 99, 235, 0.15);
  pointer-events: none;
}

.drop-title {
  font-size: 18px;
  font-weight: 600;
  color: #1E293B;
  margin: 16px 0 4px;
}

.drop-hint {
  font-size: 13px;
  color: #64748B;
  margin: 0;
}

.drop-fade-enter-active,
.drop-fade-leave-active {
  transition: opacity 0.2s;
}

.drop-fade-enter-from,
.drop-fade-leave-to {
  opacity: 0;
}
</style>
