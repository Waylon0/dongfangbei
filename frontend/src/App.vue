<template>
  <div class="app-shell">
    <AppSidebar />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
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
</style>
