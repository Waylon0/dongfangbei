<template>
  <el-collapse v-model="activeGroup" accordion>
    <el-collapse-item
      v-for="group in PARAM_GROUPS"
      :key="group.label"
      :title="group.label"
      :name="group.label"
    >
      <div class="param-grid">
        <template v-for="key in group.keys" :key="key">
          <div v-if="BOOLEAN_KEYS.has(key)" class="param-row">
            <span class="param-label">{{ LABELS[key] }}</span>
            <el-switch
              :model-value="Boolean(paramsStore[key])"
              @update:model-value="paramsStore.setParam(key, $event)"
              size="small"
            />
          </div>
          <div v-else class="param-row">
            <span class="param-label">{{ LABELS[key] }}</span>
            <el-input-number
              :model-value="Number(paramsStore[key])"
              @update:model-value="val => paramsStore.setParam(key, val)"
              :min="paramRange(key)[0]"
              :max="paramRange(key)[1]"
              :step="paramStep(key)"
              :precision="paramPrecision(key)"
              size="small"
              controls-position="right"
              style="width:120px"
            />
          </div>
        </template>
      </div>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useParamsStore } from '@/stores/params'
import { PARAM_GROUPS, type PipelineParams } from '@/types'

type ParamKey = keyof PipelineParams

const paramsStore = useParamsStore()
const activeGroup = ref('预处理')

const LABELS: Record<ParamKey, string> = {
  gaussian_sigma: '高斯滤波 σ',
  use_clahe: 'CLAHE 增强',
  clahe_clip_limit: 'CLAHE 限幅',
  clahe_grid_size: 'CLAHE 网格',
  otsu_scale: 'Otsu 缩放',
  use_adaptive_threshold: '自适应阈值',
  adaptive_block_size: '自适应窗口',
  adaptive_c: '偏移常数',
  closing_radius: '闭运算半径',
  opening_radius: '开运算半径',
  min_component_area: '最小连通域',
  separate_intersections: '交叉分离',
  contour_smooth_sigma: '轮廓平滑 σ',
  min_polygon_area: '最小面积',
  dp_epsilon: 'DP 简化容差',
  smooth_iterations: '平滑迭代',
  scales: '多尺度 σ',
  dedup_overlap_threshold: '去重 IoU',
  track_max_link_distance: '最大连接距离',
  track_angle_weight: '方向权重',
  track_min_segment_length: '最小片段长',
  track_dilate_radius: '膨胀半径',
  track_dilate_iterations: '膨胀迭代',
}

const BOOLEAN_KEYS: Set<ParamKey> = new Set(['use_clahe', 'use_adaptive_threshold', 'separate_intersections'])

const RANGES: Partial<Record<ParamKey, [number, number]>> = {
  gaussian_sigma: [0, 10],
  clahe_clip_limit: [0, 10],
  clahe_grid_size: [2, 32],
  otsu_scale: [0, 5],
  adaptive_block_size: [3, 201],
  adaptive_c: [-1, 1],
  closing_radius: [0, 20],
  opening_radius: [0, 10],
  min_component_area: [0, 1000],
  contour_smooth_sigma: [0, 10],
  min_polygon_area: [0, 500],
  dp_epsilon: [0, 20],
  smooth_iterations: [0, 10],
  dedup_overlap_threshold: [0, 1],
  track_max_link_distance: [0, 100],
  track_angle_weight: [0, 10],
  track_min_segment_length: [0, 50],
  track_dilate_radius: [0, 10],
  track_dilate_iterations: [0, 10],
}

const STEPS: Partial<Record<ParamKey, number>> = {
  gaussian_sigma: 0.1,
  otsu_scale: 0.1,
  clahe_clip_limit: 0.1,
  adaptive_c: 0.05,
  contour_smooth_sigma: 0.1,
  dp_epsilon: 0.5,
  dedup_overlap_threshold: 0.05,
  track_angle_weight: 0.5,
}

const PRECISIONS: Partial<Record<ParamKey, number>> = {
  gaussian_sigma: 1,
  otsu_scale: 1,
  clahe_clip_limit: 1,
  adaptive_c: 2,
  contour_smooth_sigma: 1,
  dp_epsilon: 1,
  dedup_overlap_threshold: 2,
  track_angle_weight: 1,
}

function paramRange(key: ParamKey): [number, number] { return RANGES[key] || [0, 100] }
function paramStep(key: ParamKey): number { return STEPS[key] || 1 }
function paramPrecision(key: ParamKey): number { return PRECISIONS[key] || 0 }
</script>

<style scoped>
.param-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.param-label {
  font-size: 12px;
  color: #475569;
}
</style>
