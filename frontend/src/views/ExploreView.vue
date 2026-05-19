<template>
  <div class="explore-view">
    <div class="layer-bar">
      <el-radio-group v-model="layer" size="small">
        <el-radio-button value="heatmap">热力图</el-radio-button>
        <el-radio-button value="binary">二值图</el-radio-button>
        <el-radio-button value="polygons">纯多边形</el-radio-button>
      </el-radio-group>
    </div>

    <div class="map-container">
      <template v-if="dataStore.hasResult">
        <FaultMap
          :heatmap="layer === 'polygons' ? undefined : (layer === 'binary' ? dataStore.result!.binary : dataStore.rawData!)"
          :filtered="dataStore.result!.filtered"
          :layer="layer === 'polygons' ? 'binary' : layer"
          height="100%"
          @click-polygon="handleClickPolygon"
        />
      </template>
      <div v-else class="empty-state">
        <el-empty description="请先在侧边栏运行追踪流水线" :image-size="100" />
      </div>
    </div>

    <div class="status-bar">
      <span>多边形: <strong>{{ polygonCount }}</strong></span>
      <span v-if="areaRange">面积范围: <strong>{{ areaRange.min }} - {{ areaRange.max }}</strong> px²</span>
      <span>中位数: <strong>{{ areaMedian }}</strong> px²</span>
    </div>

    <PolyDetail
      :visible="drawerVisible"
      :polygon="selectedPolygon"
      :area="selectedArea"
      @close="drawerVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDataStore } from '@/stores/data'
import FaultMap from '@/components/FaultMap.vue'
import PolyDetail from '@/components/PolyDetail.vue'
import { polygonArea } from '@/utils/geometry'

const dataStore = useDataStore()
const layer = ref<'heatmap' | 'binary' | 'polygons'>('heatmap')
const drawerVisible = ref(false)
const selectedIndex = ref(-1)

const polygonCount = computed(() => dataStore.result?.filtered?.length ?? 0)

const selectedPolygon = computed(() => {
  if (selectedIndex.value < 0 || !dataStore.result) return null
  return dataStore.result.filtered[selectedIndex.value] ?? null
})

const selectedArea = computed(() => {
  const poly = selectedPolygon.value
  if (!poly) return 0
  return polygonArea(poly)
})

const areaRange = computed(() => {
  const areas = dataStore.result?.areas
  if (!areas || areas.length === 0) return null
  return {
    min: Math.min(...areas).toFixed(0),
    max: Math.max(...areas).toFixed(0),
  }
})

const areaMedian = computed(() => {
  const areas = dataStore.result?.areas
  if (!areas || areas.length === 0) return '-'
  const sorted = [...areas].sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)].toFixed(0)
})

function handleClickPolygon(idx: number) {
  selectedIndex.value = idx
  drawerVisible.value = true
}
</script>

<style scoped>
.explore-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.layer-bar {
  display: flex;
  justify-content: center;
  padding: 8px;
  background: #FAFBFC;
  border-bottom: 1px solid #E5E7EB;
}

.map-container {
  flex: 1;
  min-height: 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.status-bar {
  display: flex;
  gap: 24px;
  padding: 6px 16px;
  font-size: 12px;
  color: #64748B;
  background: #FAFBFC;
  border-top: 1px solid #E5E7EB;
}

.status-bar strong {
  color: #1E293B;
}
</style>
