import axios from 'axios'
import type { PipelineParams, PipelineResult, GeneratedData } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

/** 运行追踪流水线 */
export async function runPipeline(
  data: number[][],
  params: PipelineParams
): Promise<PipelineResult> {
  const res = await api.post<PipelineResult>('/pipeline', { data, params })
  return res.data
}

/** 生成合成测试数据 */
export async function generateData(
  rows = 300,
  cols = 400,
  nFaults = 5,
  noiseLevel = 0.03,
  seed = 42
): Promise<GeneratedData> {
  const res = await api.post<GeneratedData>('/generate', {
    rows,
    cols,
    n_faults: nFaults,
    noise_level: noiseLevel,
    seed,
  })
  return res.data
}
