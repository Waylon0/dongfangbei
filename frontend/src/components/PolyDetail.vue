<template>
  <el-drawer
    :model-value="visible"
    @update:model-value="$emit('close')"
    title="多边形详情"
    size="360px"
    direction="rtl"
  >
    <template v-if="polygon">
      <div class="detail-section">
        <div class="stat-row">
          <span class="stat-label">顶点数</span>
          <span class="stat-value">{{ polygon.length }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">面积 (px²)</span>
          <span class="stat-value">{{ area.toFixed(1) }}</span>
        </div>
      </div>
      <el-divider />
      <h4 class="table-title">顶点坐标</h4>
      <el-table :data="tableData" size="small" max-height="320" stripe>
        <el-table-column prop="idx" label="#" width="48" />
        <el-table-column prop="row" label="Row" />
        <el-table-column prop="col" label="Col" />
      </el-table>
    </template>
    <template v-else>
      <el-empty description="点击地图上的多边形查看详情" />
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  visible: boolean
  polygon: number[][] | null
  area: number
}>()

defineEmits<{ close: [] }>()

const tableData = computed(() => {
  if (!props.polygon) return []
  return props.polygon.map(([row, col], idx) => ({
    idx,
    row: row.toFixed(1),
    col: col.toFixed(1),
  }))
})
</script>

<style scoped>
.detail-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #F8FAFC;
  border-radius: 6px;
}

.stat-label {
  font-size: 13px;
  color: #64748B;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

.table-title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 8px;
}
</style>
