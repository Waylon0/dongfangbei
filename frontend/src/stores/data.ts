import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PipelineResult } from '@/types'
import { runPipeline, generateData, uploadFile } from '@/api/pipeline'
import { useParamsStore } from './params'
import { ElMessage } from 'element-plus'

export const useDataStore = defineStore('data', () => {
  const rawData = ref<number[][] | null>(null)
  const dataShape = ref<[number, number]>([0, 0])
  const result = ref<PipelineResult | null>(null)
  const running = ref(false)

  const hasData = computed(() => rawData.value !== null && rawData.value.length > 0)
  const hasResult = computed(() => result.value !== null)

  async function generate(rows = 300, cols = 400, nFaults = 5, noiseLevel = 0.03, seed = 42) {
    running.value = true
    try {
      const res = await generateData(rows, cols, nFaults, noiseLevel, seed)
      rawData.value = res.data
      dataShape.value = res.shape
      ElMessage.success(`数据已生成 ${res.shape[0]} x ${res.shape[1]}`)
    } catch (e: any) {
      ElMessage.error(`生成失败: ${e.message}`)
    } finally {
      running.value = false
    }
  }

  async function upload(file: File) {
    running.value = true
    try {
      const res = await uploadFile(file)
      rawData.value = res.data
      dataShape.value = res.shape
      result.value = null
      ElMessage.success(`已加载 ${file.name} — ${res.shape[0]} x ${res.shape[1]}`)
    } catch (e: any) {
      ElMessage.error(`上传失败: ${e.message}`)
    } finally {
      running.value = false
    }
  }

  async function execute() {
    if (!rawData.value) {
      ElMessage.warning('请先生成或加载数据')
      return
    }
    running.value = true
    try {
      const params = useParamsStore().state
      const res = await runPipeline(rawData.value, params)
      result.value = res
      ElMessage.success(`追踪完成，耗时 ${res.elapsed}s，共 ${res.filtered.length} 个多边形`)
    } catch (e: any) {
      ElMessage.error(`追踪失败: ${e.message}`)
    } finally {
      running.value = false
    }
  }

  function clearResult() {
    result.value = null
  }

  function clearAll() {
    rawData.value = null
    dataShape.value = [0, 0]
    result.value = null
  }

  return {
    rawData, dataShape, result, running,
    hasData, hasResult,
    generate, upload, execute, clearResult, clearAll,
  }
})
