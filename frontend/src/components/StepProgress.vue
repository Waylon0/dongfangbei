<template>
  <div class="step-progress">
    <div class="step-track">
      <div
        v-for="(step, idx) in PIPELINE_STEPS"
        :key="step.key"
        class="step-item"
        :class="{
          'is-done': idx < current,
          'is-current': idx === current,
        }"
        @click="$emit('go', idx)"
      >
        <div class="step-dot">{{ idx + 1 }}</div>
        <span class="step-label">{{ step.title }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PIPELINE_STEPS } from '@/types'

defineProps<{ current: number }>()
defineEmits<{ go: [index: number] }>()
</script>

<style scoped>
.step-progress {
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
}

.step-track {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.step-track::before {
  content: '';
  position: absolute;
  top: 14px;
  left: 0;
  right: 0;
  height: 2px;
  background: #E5E7EB;
  z-index: 0;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  z-index: 1;
  position: relative;
}

.step-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #E5E7EB;
  color: #94A3B8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.step-label {
  font-size: 11px;
  color: #94A3B8;
  white-space: nowrap;
}

.step-item.is-done .step-dot {
  background: #2563EB;
  color: #fff;
}

.step-item.is-done .step-label {
  color: #2563EB;
}

.step-item.is-current .step-dot {
  background: #1D4ED8;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2);
}

.step-item.is-current .step-label {
  color: #1D4ED8;
  font-weight: 600;
}
</style>
