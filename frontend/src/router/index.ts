import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/pipeline',
    },
    {
      path: '/pipeline',
      name: 'pipeline',
      component: () => import('@/views/PipelineView.vue'),
    },
    {
      path: '/explore',
      name: 'explore',
      component: () => import('@/views/ExploreView.vue'),
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('@/views/CompareView.vue'),
    },
  ],
})

export default router
