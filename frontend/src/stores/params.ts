import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'
import { DEFAULT_PARAMS, type PipelineParams } from '@/types'

export const useParamsStore = defineStore('params', () => {
  const state = reactive<PipelineParams>({ ...DEFAULT_PARAMS })

  function reset() {
    Object.assign(state, DEFAULT_PARAMS)
  }

  function setParam<K extends keyof PipelineParams>(key: K, value: PipelineParams[K]) {
    state[key] = value
  }

  return { ...toRefs(state), state, reset, setParam }
})
