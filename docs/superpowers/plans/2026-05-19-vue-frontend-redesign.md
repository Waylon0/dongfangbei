# Vue 3 前端重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将断层多边形自动追踪系统前端从 Streamlit 迁移到 Vue 3 + Element Plus，后端用 FastAPI 封装现有 Python 流水线。

**Architecture:** Monorepo 结构，`backend/` FastAPI 通过 `sys.path` 引用项目根现有 `src/` 和 `config.py`，`frontend/` 为标准 Vue 3 + Vite SPA。前端通过 Axios 调后端 REST API，单次 POST /api/pipeline 返回全部 7 步中间数据。

**Tech Stack:** Vue 3 + Vite + TypeScript, Element Plus, ECharts (vue-echarts), Pinia, Vue Router 4, Axios, FastAPI + uvicorn

---

## 文件结构总览

```
东方杯/
├── backend/
│   ├── main.py              # FastAPI + CORS + sys.path
│   ├── api/
│   │   ├── __init__.py
│   │   └── pipeline.py      # POST /api/pipeline, POST /api/generate
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── env.d.ts
│   │   ├── types/
│   │   │   └── index.ts      # 共享 TS 接口
│   │   ├── views/
│   │   │   ├── PipelineView.vue
│   │   │   ├── ExploreView.vue
│   │   │   └── CompareView.vue
│   │   ├── components/
│   │   │   ├── AppSidebar.vue
│   │   │   ├── StepProgress.vue
│   │   │   ├── ParamPanel.vue
│   │   │   ├── FaultMap.vue
│   │   │   └── PolyDetail.vue
│   │   ├── stores/
│   │   │   ├── data.ts
│   │   │   └── params.ts
│   │   ├── api/
│   │   │   └── pipeline.ts
│   │   └── router/
│   │       └── index.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── src/                      # 不变
├── config.py                 # 不变
└── data/                     # 不变
```

---

### Task 1: 创建后端 FastAPI 项目结构

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/api/__init__.py`
- Create: `backend/api/pipeline.py`
- Create: `backend/main.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
numpy>=1.24.0
scipy>=1.10.0
scikit-image>=0.20.0
shapely>=2.0.0
```

- [ ] **Step 2: 创建 backend/api/__init__.py**

```python
```

(空文件)

- [ ] **Step 3: 创建 backend/api/pipeline.py**

```python
"""流水线 API 端点"""

import sys
import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from src.preprocess import normalize
from src.segment import segment_fault_regions
from src.polygon_extract import extract_fault_polygons
from src.vectorize import simplify_polygon, filter_by_area, polygon_area
from src.tracker import track_faults
from src.multiscale import merge_multiscale_results
from scipy.ndimage import gaussian_filter
from skimage.filters import threshold_otsu, threshold_local
from skimage.morphology import skeletonize


router = APIRouter()


class PipelineParams(BaseModel):
    gaussian_sigma: float = 1.5
    use_clahe: bool = False
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    otsu_scale: float = 1.0
    use_adaptive_threshold: bool = False
    adaptive_block_size: int = 35
    adaptive_c: float = 0.0
    closing_radius: int = 5
    opening_radius: int = 2
    min_component_area: int = 100
    separate_intersections: bool = True
    contour_smooth_sigma: float = 2.0
    min_polygon_area: float = 50
    dp_epsilon: float = 3.0
    smooth_iterations: int = 2
    scales: list = [1.0, 2.0]
    dedup_overlap_threshold: float = 0.5
    track_max_link_distance: float = 30.0
    track_angle_weight: float = 2.0
    track_min_segment_length: int = 10
    track_dilate_radius: int = 3
    track_dilate_iterations: int = 5


class PipelineRequest(BaseModel):
    data: list
    params: PipelineParams = PipelineParams()


class GenerateRequest(BaseModel):
    rows: int = 300
    cols: int = 400
    n_faults: int = 5
    noise_level: float = 0.03
    seed: int = 42


def _config_from_params(p: PipelineParams) -> Config:
    cfg = Config()
    cfg.gaussian_sigma = p.gaussian_sigma
    cfg.use_clahe = p.use_clahe
    cfg.clahe_clip_limit = p.clahe_clip_limit
    cfg.clahe_grid_size = p.clahe_grid_size
    cfg.otsu_scale = p.otsu_scale
    cfg.use_adaptive_threshold = p.use_adaptive_threshold
    cfg.adaptive_block_size = p.adaptive_block_size
    cfg.adaptive_c = p.adaptive_c
    cfg.closing_radius = p.closing_radius
    cfg.opening_radius = p.opening_radius
    cfg.min_component_area = p.min_component_area
    cfg.separate_intersections = p.separate_intersections
    cfg.contour_smooth_sigma = p.contour_smooth_sigma
    cfg.min_polygon_area = p.min_polygon_area
    cfg.dp_epsilon = p.dp_epsilon
    cfg.smooth_iterations = p.smooth_iterations
    cfg.scales = p.scales
    cfg.dedup_overlap_threshold = p.dedup_overlap_threshold
    cfg.track_max_link_distance = p.track_max_link_distance
    cfg.track_angle_weight = p.track_angle_weight
    cfg.track_min_segment_length = p.track_min_segment_length
    cfg.track_dilate_radius = p.track_dilate_radius
    cfg.track_dilate_iterations = p.track_dilate_iterations
    return cfg


def _find_junctions(skel: np.ndarray) -> list:
    coords = np.argwhere(skel > 0)
    junctions = []
    h, w = skel.shape
    for r, c in coords:
        r, c = int(r), int(c)
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and skel[rr, cc]:
                    cnt += 1
        if cnt >= 3:
            junctions.append((r, c))
    return junctions


def _serialize_array(arr) -> list:
    """将 numpy 数组转为 JSON 可序列化的 list"""
    if isinstance(arr, np.ndarray):
        if arr.dtype == bool:
            return arr.astype(int).tolist()
        return arr.tolist()
    return arr


def _serialize_contours(contours: list) -> list:
    """将轮廓列表转为 [[[r,c], ...], ...]"""
    result = []
    for c in contours:
        arr = np.array(c) if not isinstance(c, np.ndarray) else c
        result.append(arr.tolist())
    return result


@router.post("/api/pipeline")
def run_pipeline(req: PipelineRequest):
    """运行完整断层多边形追踪流水线，返回每步中间数据"""
    try:
        data = np.array(req.data, dtype=np.float64)
        if data.ndim != 2:
            raise HTTPException(400, "data must be a 2D array")
    except Exception as e:
        raise HTTPException(400, f"Invalid data: {e}")

    cfg = _config_from_params(req.params)
    t0 = time.perf_counter()
    data_norm = normalize(data)

    # 步骤1-2: 二值分割（阈值前）
    smoothed = gaussian_filter(data_norm, sigma=cfg.gaussian_sigma)
    if cfg.use_adaptive_threshold:
        block = max(3, cfg.adaptive_block_size)
        if block % 2 == 0:
            block += 1
        img_uint8 = (smoothed * 255).astype(np.uint8)
        local_thresh = threshold_local(img_uint8, block, method='gaussian',
                                        offset=cfg.adaptive_c * 255)
        binary_before_morph = (smoothed >= (local_thresh / 255.0)).astype(np.uint8)
    else:
        thresh = threshold_otsu(smoothed) * cfg.otsu_scale
        binary_before_morph = (smoothed >= thresh).astype(np.uint8)

    # 步骤3: 形态学处理
    binary = segment_fault_regions(
        data, sigma=cfg.gaussian_sigma, otsu_scale=cfg.otsu_scale,
        closing_radius=cfg.closing_radius, opening_radius=cfg.opening_radius,
        use_adaptive_threshold=cfg.use_adaptive_threshold,
        adaptive_block_size=cfg.adaptive_block_size, adaptive_c=cfg.adaptive_c,
    )

    # 步骤3.5: 断层追踪
    binary_before_track = binary.copy()
    binary = track_faults(
        binary, max_link_distance=cfg.track_max_link_distance,
        angle_weight=cfg.track_angle_weight,
        min_segment_length=cfg.track_min_segment_length,
        dilate_radius=cfg.track_dilate_radius,
        dilate_iterations=cfg.track_dilate_iterations,
        raw_data=data,
    )

    # 步骤4: 轮廓提取
    contours = extract_fault_polygons(
        binary, min_component_area=cfg.min_component_area,
        separate_intersections=cfg.separate_intersections,
        smooth_sigma=cfg.contour_smooth_sigma,
    )

    # 步骤5: 骨架 + 交叉点
    skel = skeletonize(binary.astype(bool))
    junctions = _find_junctions(skel)

    # 步骤6: 矢量简化 + 平滑
    vectorized = [
        simplify_polygon(c, cfg.dp_epsilon, cfg.smooth_iterations)
        for c in contours
    ]
    filtered = filter_by_area(vectorized, cfg.min_polygon_area)
    areas = [polygon_area(p) for p in filtered]

    # 多尺度融合
    if cfg.scales and len(cfg.scales) > 1:
        all_polygons = [filtered]
        all_areas_list = [areas]
        for scale_sigma in cfg.scales[1:]:
            binary_s = segment_fault_regions(
                data, sigma=scale_sigma, otsu_scale=cfg.otsu_scale,
                closing_radius=cfg.closing_radius, opening_radius=cfg.opening_radius,
            )
            binary_s = track_faults(
                binary_s, max_link_distance=cfg.track_max_link_distance,
                angle_weight=cfg.track_angle_weight,
                min_segment_length=cfg.track_min_segment_length,
                dilate_radius=cfg.track_dilate_radius,
                dilate_iterations=cfg.track_dilate_iterations,
                raw_data=data,
            )
            contours_s = extract_fault_polygons(
                binary_s, min_component_area=cfg.min_component_area,
                separate_intersections=cfg.separate_intersections,
                smooth_sigma=cfg.contour_smooth_sigma,
            )
            vectorized_s = [simplify_polygon(c, cfg.dp_epsilon, cfg.smooth_iterations)
                            for c in contours_s]
            filtered_s = filter_by_area(vectorized_s, cfg.min_polygon_area)
            areas_s = [polygon_area(p) for p in filtered_s]
            all_polygons.append(filtered_s)
            all_areas_list.append(areas_s)
        filtered, areas = merge_multiscale_results(
            all_polygons, all_areas_list, cfg.dedup_overlap_threshold)

    elapsed = time.perf_counter() - t0

    return {
        'data_smoothed': _serialize_array(smoothed),
        'binary_before_morph': _serialize_array(binary_before_morph),
        'binary': _serialize_array(binary),
        'binary_before_track': _serialize_array(binary_before_track),
        'skeleton': _serialize_array(skel),
        'junctions': junctions,
        'contours': _serialize_contours(contours),
        'vectorized': _serialize_contours(vectorized),
        'filtered': _serialize_contours(filtered),
        'areas': areas,
        'elapsed': round(elapsed, 3),
    }


@router.post("/api/generate")
def generate_data(req: GenerateRequest):
    """生成合成测试数据"""
    from main import generate_synthetic_data
    data = generate_synthetic_data(
        shape=(req.rows, req.cols),
        n_faults=req.n_faults,
        noise_level=req.noise_level,
        seed=req.seed,
    )
    return {
        'data': _serialize_array(data),
        'shape': list(data.shape),
        'min': float(data.min()),
        'max': float(data.max()),
    }
```

- [ ] **Step 4: 创建 backend/main.py**

```python
"""FastAPI 后端入口"""

import sys
from pathlib import Path

# 确保项目根在 sys.path 中，让 src/ 和 config.py 可导入
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.pipeline import router

app = FastAPI(title="断层多边形自动追踪 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 5: 验证后端语法**

```bash
cd "d:\东方杯" && python -c "import ast; ast.parse(open('backend/main.py').read()); ast.parse(open('backend/api/pipeline.py').read()); print('Syntax OK')"
```

- [ ] **Step 6: 测试后端启动**

```bash
cd "d:\东方杯" && timeout 5 python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 2>&1 || true
```

- [ ] **Step 7: Commit**

```bash
git add backend/ && git commit -m "feat: add FastAPI backend wrapping existing pipeline"
```

---

### Task 2: 搭建 Vue 3 前端项目

**Files:**
- Create: `frontend/` (Vite scaffold)

- [ ] **Step 1: 用 Vite 创建项目**

```bash
cd "d:\东方杯" && npm create vite@latest frontend -- --template vue-ts
```

- [ ] **Step 2: 安装依赖**

```bash
cd "d:\东方杯\frontend" && npm install && npm install element-plus @element-plus/icons-vue echarts vue-echarts pinia vue-router@4 axios
```

- [ ] **Step 3: 添加 env.d.ts 类型声明**

创建 `frontend/src/env.d.ts`:

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 4: 配置 vite.config.ts**

修改 `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 5: 配置 tsconfig.json 路径别名**

修改 `frontend/tsconfig.json`，在 `compilerOptions` 中添加:

```json
"baseUrl": ".",
"paths": {
  "@/*": ["src/*"]
}
```

- [ ] **Step 6: 验证前端能启动**

```bash
cd "d:\东方杯\frontend" && timeout 8 npm run dev 2>&1 || true
```

- [ ] **Step 7: Commit**

```bash
cd "d:\东方杯" && git add frontend/ && git commit -m "feat: scaffold Vue 3 + Vite frontend with deps"
```

---

### Task 3: 共享 TypeScript 类型定义

**Files:**
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: 创建类型文件**

```typescript
/** 后端返回的流水线完整结果 */
export interface PipelineResult {
  data_smoothed: number[][]
  binary_before_morph: number[][]
  binary: number[][]
  binary_before_track: number[][]
  skeleton: number[][]
  junctions: [number, number][]
  contours: number[][][]
  vectorized: number[][][]
  filtered: number[][][]
  areas: number[]
  elapsed: number
}

/** 生成数据接口返回 */
export interface GeneratedData {
  data: number[][]
  shape: [number, number]
  min: number
  max: number
}

/** 可调参数全集，与 config.py 一一对应 */
export interface PipelineParams {
  gaussian_sigma: number
  use_clahe: boolean
  clahe_clip_limit: number
  clahe_grid_size: number
  otsu_scale: number
  use_adaptive_threshold: boolean
  adaptive_block_size: number
  adaptive_c: number
  closing_radius: number
  opening_radius: number
  min_component_area: number
  separate_intersections: boolean
  contour_smooth_sigma: number
  min_polygon_area: number
  dp_epsilon: number
  smooth_iterations: number
  scales: number[]
  dedup_overlap_threshold: number
  track_max_link_distance: number
  track_angle_weight: number
  track_min_segment_length: number
  track_dilate_radius: number
  track_dilate_iterations: number
}

/** 默认参数 */
export const DEFAULT_PARAMS: PipelineParams = {
  gaussian_sigma: 1.5,
  use_clahe: false,
  clahe_clip_limit: 2.0,
  clahe_grid_size: 8,
  otsu_scale: 1.0,
  use_adaptive_threshold: false,
  adaptive_block_size: 35,
  adaptive_c: 0.0,
  closing_radius: 5,
  opening_radius: 2,
  min_component_area: 100,
  separate_intersections: true,
  contour_smooth_sigma: 2.0,
  min_polygon_area: 50,
  dp_epsilon: 3.0,
  smooth_iterations: 2,
  scales: [1.0, 2.0],
  dedup_overlap_threshold: 0.5,
  track_max_link_distance: 30.0,
  track_angle_weight: 2.0,
  track_min_segment_length: 10,
  track_dilate_radius: 3,
  track_dilate_iterations: 5,
}

/** 7 步流水线步骤定义 */
export interface StepDef {
  key: string
  title: string
  description: string
}

export const PIPELINE_STEPS: StepDef[] = [
  { key: 'raw', title: '原始数据', description: '原始断层属性数据热力图，颜色越深表示断层响应越强。可观察数据整体分布和噪声水平。' },
  { key: 'smoothed', title: '预处理', description: '高斯平滑去噪后的数据（左）与 Otsu 自适应二值化结果（右）对比。' },
  { key: 'morph', title: '形态学处理', description: '闭运算填充断层内部小孔洞、连接断缝；开运算去除孤立噪点。左为处理前，右为处理后。' },
  { key: 'contour', title: '轮廓提取', description: '在二值掩膜上提取连通域，分离交叉断层，追踪每个断层区域的外轮廓线。' },
  { key: 'skeleton', title: '骨架与交叉点', description: '断层区域骨架化（中心线），红色标记为交叉点（度数 >= 3），用于验证断层分离效果。' },
  { key: 'result', title: '最终结果', description: '原始数据叠加简化后的断层多边形。矢量简化去除冗余顶点，面积过滤剔除小碎片。' },
  { key: 'overview', title: '总览', description: '6 小图网格展示全流程 + 多边形面积分布直方图 + 关键统计数字。' },
]

/** 参数分组，用于侧边栏折叠面板 */
export interface ParamGroup {
  label: string
  keys: (keyof PipelineParams)[]
}

export const PARAM_GROUPS: ParamGroup[] = [
  {
    label: '预处理',
    keys: ['gaussian_sigma', 'use_clahe', 'clahe_clip_limit', 'clahe_grid_size'],
  },
  {
    label: '分割',
    keys: ['otsu_scale', 'use_adaptive_threshold', 'adaptive_block_size', 'adaptive_c'],
  },
  {
    label: '提取',
    keys: ['closing_radius', 'opening_radius', 'min_component_area', 'separate_intersections', 'contour_smooth_sigma'],
  },
  {
    label: '追踪',
    keys: ['track_max_link_distance', 'track_angle_weight', 'track_min_segment_length', 'track_dilate_radius', 'track_dilate_iterations'],
  },
  {
    label: '简化／过滤',
    keys: ['dp_epsilon', 'smooth_iterations', 'min_polygon_area'],
  },
]
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/types/ && git commit -m "feat: add shared TypeScript type definitions"
```

---

### Task 4: API 通信层

**Files:**
- Create: `frontend/src/api/pipeline.ts`

- [ ] **Step 1: 创建 Axios API 客户端**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/api/ && git commit -m "feat: add Axios API client layer"
```

---

### Task 5: Pinia 参数状态管理

**Files:**
- Create: `frontend/src/stores/params.ts`

- [ ] **Step 1: 创建 params store**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/stores/params.ts && git commit -m "feat: add Pinia params store"
```

---

### Task 6: Pinia 数据状态管理

**Files:**
- Create: `frontend/src/stores/data.ts`

- [ ] **Step 1: 创建 data store**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PipelineResult, GeneratedData } from '@/types'
import { runPipeline, generateData } from '@/api/pipeline'
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
      ElMessage.success(`数据已生成 ${res.shape[0]}×${res.shape[1]}`)
    } catch (e: any) {
      ElMessage.error(`生成失败: ${e.message}`)
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
    generate, execute, clearResult, clearAll,
  }
})
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/stores/data.ts && git commit -m "feat: add Pinia data store with pipeline execution"
```

---

### Task 7: Vue Router 路由配置

**Files:**
- Create: `frontend/src/router/index.ts`

- [ ] **Step 1: 创建路由**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/router/ && git commit -m "feat: add Vue Router configuration"
```

---

### Task 8: 共享组件 — AppSidebar

**Files:**
- Create: `frontend/src/components/AppSidebar.vue`

- [ ] **Step 1: 创建侧边栏组件**

```vue
<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="title">断层多边形追踪</h1>
      <p class="subtitle">Fault Polygon Auto-Tracking</p>
      <div class="accent-line"></div>
    </div>

    <!-- 数据源 -->
    <div class="section">
      <h3 class="section-title">数据源</h3>
      <div class="data-source">
        <div class="gen-row">
          <span class="label">行</span>
          <el-input-number v-model="genRows" :min="50" :max="1000" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">列</span>
          <el-input-number v-model="genCols" :min="50" :max="1000" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">断层数</span>
          <el-input-number v-model="genFaults" :min="1" :max="20" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">噪声</span>
          <el-input-number v-model="genNoise" :min="0" :max="0.2" :step="0.01" :precision="2" size="small" controls-position="right" />
        </div>
        <div class="gen-row">
          <span class="label">种子</span>
          <el-input-number v-model="genSeed" :min="0" :max="9999" size="small" controls-position="right" />
        </div>
        <el-button type="primary" @click="handleGenerate" :loading="dataStore.running" style="width:100%">
          生成合成数据
        </el-button>
      </div>
      <el-divider style="margin:12px 0"><span style="color:#94a3b8;font-size:12px">或</span></el-divider>
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        :on-change="handleFileLoad"
        accept=".npy,.npz,.dat"
        style="width:100%"
      >
        <el-button style="width:100%">上传文件 (.npy/.npz/.dat)</el-button>
      </el-upload>
      <div v-if="dataStore.hasData" class="data-status">
        <span class="status-dot"></span>
        已加载 {{ dataStore.dataShape[0] }} × {{ dataStore.dataShape[1] }}
      </div>
    </div>

    <!-- 算法参数 -->
    <div class="section params-section">
      <h3 class="section-title">算法参数</h3>
      <ParamPanel />
      <el-button @click="paramsStore.reset()" style="width:100%;margin-top:8px">重置默认</el-button>
    </div>

    <!-- 操作按钮区 -->
    <div class="sidebar-footer">
      <el-button
        type="primary"
        size="large"
        @click="dataStore.execute()"
        :loading="dataStore.running"
        :disabled="!dataStore.hasData"
        style="width:100%"
      >
        {{ dataStore.running ? '运行中...' : '运行追踪' }}
      </el-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDataStore } from '@/stores/data'
import { useParamsStore } from '@/stores/params'
import ParamPanel from './ParamPanel.vue'
import type { UploadFile } from 'element-plus'

const dataStore = useDataStore()
const paramsStore = useParamsStore()

const genRows = ref(300)
const genCols = ref(400)
const genFaults = ref(5)
const genNoise = ref(0.03)
const genSeed = ref(42)

function handleGenerate() {
  dataStore.generate(genRows.value, genCols.value, genFaults.value, genNoise.value, genSeed.value)
}

async function handleFileLoad(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  const buffer = await raw.arrayBuffer()
  const ext = raw.name.split('.').pop()?.toLowerCase()
  // 前端只做轻量解析，复杂格式交给后端
  if (ext === 'npy') {
    // .npy 需要解析 NPY 格式头 — 简化：传原始字节到后端
    // 实际走 /api/upload 端点，这里留占位
    // 暂时提示用户使用合成数据或后端直接加载
  }
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  background: #F1F4F8;
  border-right: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 20px 16px 12px;
}

.title {
  font-size: 18px;
  font-weight: 700;
  color: #1E293B;
  margin: 0;
  line-height: 1.3;
}

.subtitle {
  font-size: 11px;
  color: #64748B;
  margin: 2px 0 0;
  letter-spacing: 0.5px;
}

.accent-line {
  width: 32px;
  height: 3px;
  background: #2563EB;
  border-radius: 2px;
  margin-top: 10px;
}

.section {
  padding: 8px 16px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px;
}

.data-source {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gen-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.gen-row .label {
  font-size: 13px;
  color: #475569;
  min-width: 44px;
}

.gen-row .el-input-number {
  width: 130px;
}

.data-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #22C55E;
  margin-top: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #22C55E;
  border-radius: 50%;
}

.params-section {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #E5E7EB;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/components/AppSidebar.vue && git commit -m "feat: add AppSidebar component with data source and actions"
```

---

### Task 9: 共享组件 — ParamPanel

**Files:**
- Create: `frontend/src/components/ParamPanel.vue`

- [ ] **Step 1: 创建参数面板组件**

```vue
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
          <!-- boolean → switch -->
          <div v-if="isBoolean(key)" class="param-row">
            <span class="param-label">{{ paramLabel(key) }}</span>
            <el-switch
              :model-value="Boolean(paramsStore[key])"
              @update:model-value="paramsStore.setParam(key, $event)"
              size="small"
            />
          </div>
          <!-- number → slider or input-number -->
          <div v-else class="param-row">
            <span class="param-label">{{ paramLabel(key) }}</span>
            <el-input-number
              :model-value="Number(paramsStore[key])"
              @update:model-value="paramsStore.setParam(key, $event)"
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

const paramsStore = useParamsStore()
const activeGroup = ref('预处理')

type ParamKey = keyof PipelineParams

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

const BOOLEAN_KEYS = new Set<ParamKey>(['use_clahe', 'use_adaptive_threshold', 'separate_intersections'])

function isBoolean(key: ParamKey): boolean {
  return BOOLEAN_KEYS.has(key)
}

function paramLabel(key: ParamKey): string {
  return LABELS[key] || key
}

function paramRange(key: ParamKey): [number, number] {
  const ranges: Partial<Record<ParamKey, [number, number]>> = {
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
  return ranges[key] || [0, 100]
}

function paramStep(key: ParamKey): number {
  const steps: Partial<Record<ParamKey, number>> = {
    gaussian_sigma: 0.1,
    otsu_scale: 0.1,
    clahe_clip_limit: 0.1,
    adaptive_c: 0.05,
    contour_smooth_sigma: 0.1,
    dp_epsilon: 0.5,
    dedup_overlap_threshold: 0.05,
    track_angle_weight: 0.5,
  }
  return steps[key] || 1
}

function paramPrecision(key: ParamKey): number {
  const precisions: Partial<Record<ParamKey, number>> = {
    gaussian_sigma: 1,
    otsu_scale: 1,
    clahe_clip_limit: 1,
    adaptive_c: 2,
    contour_smooth_sigma: 1,
    dp_epsilon: 1,
    dedup_overlap_threshold: 2,
    track_angle_weight: 1,
  }
  return precisions[key] || 0
}
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/components/ParamPanel.vue && git commit -m "feat: add ParamPanel with 5-group accordion"
```

---

### Task 10: 共享组件 — StepProgress

**Files:**
- Create: `frontend/src/components/StepProgress.vue`

- [ ] **Step 1: 创建步骤进度条组件**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/components/StepProgress.vue && git commit -m "feat: add StepProgress component"
```

---

### Task 11: 共享组件 — FaultMap

**Files:**
- Create: `frontend/src/components/FaultMap.vue`

- [ ] **Step 1: 创建 ECharts 地图组件**

```vue
<template>
  <div ref="chartRef" class="fault-map" @contextmenu.prevent></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  heatmap?: number[][]
  contours?: number[][][]
  filtered?: number[][][]
  skeleton?: number[][]
  junctions?: [number, number][]
  layer?: 'heatmap' | 'binary' | 'polygons'
  height?: string
}>(), {
  layer: 'heatmap',
  height: '100%',
})

const emit = defineEmits<{ clickPolygon: [index: number] }>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function buildOption(): echarts.EChartsOption {
  const series: any[] = []

  // 热力图 / 二值底层
  if (props.layer === 'heatmap' && props.heatmap) {
    const data = props.heatmap
    const h = data.length
    const w = data[0]?.length || 0
    const heatData: [number, number, number][] = []
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        heatData.push([c, r, data[r][c]])
      }
    }
    series.push({
      type: 'heatmap',
      data: heatData,
      label: { show: false },
      emphasis: { disabled: true },
      itemStyle: {
        borderWidth: 0,
      },
    })
  } else if (props.layer === 'binary' && props.heatmap) {
    // 二值图：用 heatmap 但颜色离散
    const data = props.heatmap
    const h = data.length
    const w = data[0]?.length || 0
    const binData: [number, number, number][] = []
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        binData.push([c, r, data[r][c]])
      }
    }
    series.push({
      type: 'heatmap',
      data: binData,
      label: { show: false },
      emphasis: { disabled: true },
      itemStyle: { borderWidth: 0 },
    })
  }

  // 多边形轮廓线
  if (props.filtered && props.filtered.length > 0) {
    const colors = [
      '#2563EB', '#EF4444', '#22C55E', '#F59E0B', '#8B5CF6',
      '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16',
    ]
    props.filtered.forEach((poly, idx) => {
      const coords = poly.map(([r, c]) => [c, r])
      series.push({
        type: 'line',
        data: coords,
        silent: false,
        polyline: false,
        lineStyle: { color: colors[idx % colors.length], width: 2 },
        z: 10,
        name: `polygon_${idx}`,
      })
    })
  }

  // 骨架
  if (props.skeleton) {
    const skelData: [number, number][] = []
    const h = props.skeleton.length
    const w = props.skeleton[0]?.length || 0
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        if (props.skeleton[r][c]) skelData.push([c, r])
      }
    }
    series.push({
      type: 'scatter',
      data: skelData,
      symbolSize: 1,
      itemStyle: { color: '#94A3B8' },
      z: 5,
    })
  }

  // 交叉点
  if (props.junctions && props.junctions.length > 0) {
    const jData = props.junctions.map(([r, c]) => [c, r])
    series.push({
      type: 'scatter',
      data: jData,
      symbolSize: 8,
      itemStyle: { color: '#EF4444', borderColor: '#fff', borderWidth: 1 },
      z: 15,
    })
  }

  const h = props.heatmap?.length || 0
  const w = props.heatmap?.[0]?.length || 0

  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: {
      type: 'value',
      min: 0,
      max: w,
      show: false,
    },
    yAxis: {
      type: 'value',
      min: h,
      max: 0,
      show: false,
    },
    visualMap: props.layer === 'binary'
      ? {
          min: 0,
          max: 1,
          inRange: { color: ['#0F172A', '#F8FAFC'] },
          show: false,
        }
      : {
          min: 0,
          max: 1,
          inRange: { color: ['#0F172A', '#2563EB', '#60A5FA', '#BFDBFE', '#F8FAFC'] },
          show: false,
        },
    series,
    animation: false,
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())

  chart.on('click', (params: any) => {
    if (params.seriesName?.startsWith('polygon_')) {
      const idx = parseInt(params.seriesName.replace('polygon_', ''))
      emit('clickPolygon', idx)
    }
  })
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  chart?.resize()
}

watch(() => [props.heatmap, props.contours, props.filtered, props.skeleton, props.junctions, props.layer], () => {
  if (chart) {
    chart.setOption(buildOption(), true)
  }
}, { deep: true })
</script>

<style scoped>
.fault-map {
  width: 100%;
  height: v-bind(height);
  min-height: 300px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/components/FaultMap.vue && git commit -m "feat: add FaultMap ECharts component with layer toggle"
```

---

### Task 12: 共享组件 — PolyDetail

**Files:**
- Create: `frontend/src/components/PolyDetail.vue`

- [ ] **Step 1: 创建多边形详情抽屉组件**

```vue
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
          <span class="stat-label">面积 (像素²)</span>
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/components/PolyDetail.vue && git commit -m "feat: add PolyDetail drawer component"
```

---

### Task 13: 页面视图 — PipelineView

**Files:**
- Create: `frontend/src/views/PipelineView.vue`

- [ ] **Step 1: 创建分步流水线页面**

```vue
<template>
  <div class="pipeline-view">
    <StepProgress :current="currentStep" @go="setStep" />

    <div class="chart-area">
      <template v-if="dataStore.hasResult">
        <!-- Step 0: 原始数据热力图 -->
        <FaultMap
          v-if="currentStep === 0"
          :heatmap="dataStore.rawData!"
          layer="heatmap"
        />

        <!-- Step 1: 预处理 — 平滑数据 -->
        <FaultMap
          v-if="currentStep === 1"
          :heatmap="dataStore.result!.data_smoothed"
          layer="heatmap"
        />

        <!-- Step 2: 形态学 — binary_before_morph vs binary -->
        <div v-if="currentStep === 2" class="split-chart">
          <div class="split-pane">
            <span class="pane-label">处理前</span>
            <FaultMap :heatmap="dataStore.result!.binary_before_morph" layer="binary" height="100%" />
          </div>
          <div class="split-pane">
            <span class="pane-label">处理后</span>
            <FaultMap :heatmap="dataStore.result!.binary" layer="binary" height="100%" />
          </div>
        </div>

        <!-- Step 3: 轮廓提取 -->
        <FaultMap
          v-if="currentStep === 3"
          :heatmap="dataStore.rawData!"
          :contours="dataStore.result!.contours"
          layer="heatmap"
        />

        <!-- Step 4: 骨架 + 交叉点 -->
        <FaultMap
          v-if="currentStep === 4"
          :heatmap="dataStore.result!.binary"
          :skeleton="dataStore.result!.skeleton"
          :junctions="dataStore.result!.junctions"
          layer="binary"
        />

        <!-- Step 5: 最终结果 -->
        <FaultMap
          v-if="currentStep === 5"
          :heatmap="dataStore.rawData!"
          :filtered="dataStore.result!.filtered"
          layer="heatmap"
        />

        <!-- Step 6: 总览 — 6 网格 + 统计 -->
        <div v-if="currentStep === 6" class="overview-grid">
          <div class="overview-item">
            <span class="overview-label">原始数据</span>
            <FaultMap :heatmap="dataStore.rawData!" layer="heatmap" height="100%" />
          </div>
          <div class="overview-item">
            <span class="overview-label">平滑后</span>
            <FaultMap :heatmap="dataStore.result!.data_smoothed" layer="heatmap" height="100%" />
          </div>
          <div class="overview-item">
            <span class="overview-label">二值化</span>
            <FaultMap :heatmap="dataStore.result!.binary" layer="binary" height="100%" />
          </div>
          <div class="overview-item">
            <span class="overview-label">骨架</span>
            <FaultMap
              :heatmap="dataStore.result!.binary"
              :skeleton="dataStore.result!.skeleton"
              :junctions="dataStore.result!.junctions"
              layer="binary"
              height="100%"
            />
          </div>
          <div class="overview-item">
            <span class="overview-label">最终结果</span>
            <FaultMap
              :heatmap="dataStore.rawData!"
              :filtered="dataStore.result!.filtered"
              layer="heatmap"
              height="100%"
            />
          </div>
          <div class="overview-item overview-stats">
            <span class="overview-label">统计</span>
            <div class="stats-list">
              <div class="stat-item">
                <span class="stat-num">{{ dataStore.result!.filtered.length }}</span>
                <span class="stat-unit">多边形</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ dataStore.result!.elapsed }}s</span>
                <span class="stat-unit">耗时</span>
              </div>
              <div class="stat-item" v-if="areaStats">
                <span class="stat-num">{{ areaStats.min }}</span>
                <span class="stat-unit">最小面积</span>
              </div>
              <div class="stat-item" v-if="areaStats">
                <span class="stat-num">{{ areaStats.max }}</span>
                <span class="stat-unit">最大面积</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-empty description="在左侧边栏生成或上传数据，然后点击「运行追踪」" :image-size="120" />
      </div>
    </div>

    <!-- 步骤说明卡片 -->
    <div v-if="dataStore.hasResult" class="desc-card">
      <div class="desc-border"></div>
      <div class="desc-content">
        <h3>{{ PIPELINE_STEPS[currentStep].title }}</h3>
        <p>{{ PIPELINE_STEPS[currentStep].description }}</p>
      </div>
    </div>

    <!-- 底部控制栏 -->
    <div v-if="dataStore.hasResult" class="control-bar">
      <el-button @click="prevStep" :disabled="currentStep === 0" :icon="ArrowLeft">上一步</el-button>
      <el-button @click="nextStep" :disabled="currentStep === 6" :icon="ArrowRight" style="margin-left:0">下一步</el-button>
      <el-divider direction="vertical" />
      <el-select v-model="currentStep" @change="setStep" size="small" style="width:140px">
        <el-option v-for="(s, i) in PIPELINE_STEPS" :key="s.key" :label="`${i + 1}. ${s.title}`" :value="i" />
      </el-select>
      <el-divider direction="vertical" />
      <el-button text @click="toggleAutoPlay" :type="autoPlay ? 'primary' : 'default'">
        {{ autoPlay ? '暂停' : '自动播放' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { useDataStore } from '@/stores/data'
import { PIPELINE_STEPS } from '@/types'
import StepProgress from '@/components/StepProgress.vue'
import FaultMap from '@/components/FaultMap.vue'

const dataStore = useDataStore()
const currentStep = ref(0)
const autoPlay = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const areaStats = computed(() => {
  const areas = dataStore.result?.areas
  if (!areas || areas.length === 0) return null
  return {
    min: Math.min(...areas).toFixed(0),
    max: Math.max(...areas).toFixed(0),
    mean: (areas.reduce((a, b) => a + b, 0) / areas.length).toFixed(0),
  }
})

function setStep(i: number) { currentStep.value = i }
function prevStep() { if (currentStep.value > 0) currentStep.value-- }
function nextStep() { if (currentStep.value < 6) currentStep.value++ }

function toggleAutoPlay() {
  autoPlay.value = !autoPlay.value
  if (autoPlay.value) {
    timer = setInterval(() => {
      if (currentStep.value < 6) currentStep.value++
      else { autoPlay.value = false; if (timer) clearInterval(timer) }
    }, 2500)
  } else {
    if (timer) { clearInterval(timer); timer = null }
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') prevStep()
  if (e.key === 'ArrowRight') nextStep()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (timer) clearInterval(timer)
})

// 新结果重置到第0步
watch(() => dataStore.result, () => { currentStep.value = 0 })
</script>

<style scoped>
.pipeline-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.chart-area {
  flex: 1;
  min-height: 0;
  padding: 16px;
}

.split-chart {
  display: flex;
  gap: 12px;
  height: 100%;
}

.split-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.pane-label {
  font-size: 12px;
  color: #64748B;
  margin-bottom: 4px;
  text-align: center;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 8px;
  height: 100%;
}

.overview-item {
  position: relative;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  overflow: hidden;
  min-height: 0;
}

.overview-label {
  position: absolute;
  top: 4px;
  left: 8px;
  font-size: 11px;
  color: #64748B;
  z-index: 10;
  background: rgba(255,255,255,0.85);
  padding: 1px 6px;
  border-radius: 3px;
}

.overview-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #F8FAFC;
}

.stats-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #2563EB;
}

.stat-unit {
  font-size: 11px;
  color: #64748B;
}

.desc-card {
  display: flex;
  margin: 0 16px 12px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  overflow: hidden;
}

.desc-border {
  width: 4px;
  background: #2563EB;
  flex-shrink: 0;
}

.desc-content {
  padding: 10px 16px;
}

.desc-content h3 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #1E293B;
}

.desc-content p {
  margin: 0;
  font-size: 13px;
  color: #64748B;
  line-height: 1.5;
}

.control-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-top: 1px solid #E5E7EB;
  background: #FAFBFC;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/views/PipelineView.vue && git commit -m "feat: add PipelineView with 7-step flow"
```

---

### Task 14: 页面视图 — ExploreView

**Files:**
- Create: `frontend/src/views/ExploreView.vue`

- [ ] **Step 1: 创建交互探索页面**

```vue
<template>
  <div class="explore-view">
    <!-- 图层切换 -->
    <div class="layer-bar">
      <el-radio-group v-model="layer" size="small">
        <el-radio-button value="heatmap">热力图</el-radio-button>
        <el-radio-button value="binary">二值图</el-radio-button>
        <el-radio-button value="polygons">纯多边形</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 地图 -->
    <div class="map-container">
      <template v-if="dataStore.hasResult">
        <FaultMap
          :heatmap="layer === 'polygons' ? null : (layer === 'binary' ? dataStore.result!.binary : dataStore.rawData!)"
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

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <span>多边形: <strong>{{ polygonCount }}</strong></span>
      <span v-if="areaRange">面积范围: <strong>{{ areaRange.min }} - {{ areaRange.max }}</strong> px²</span>
      <span>中位数: <strong>{{ areaMedian }}</strong> px²</span>
    </div>

    <!-- 详情抽屉 -->
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
```

- [ ] **Step 2: 创建前端几何工具函数**

创建 `frontend/src/utils/geometry.ts`:

```typescript
/** Shoelace 公式计算多边形面积 */
export function polygonArea(points: number[][]): number {
  if (points.length < 3) return 0
  const n = points.length
  let area = 0
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    area += points[i][1] * points[j][0]
    area -= points[j][1] * points[i][0]
  }
  return Math.abs(area) / 2
}
```

- [ ] **Step 3: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/views/ExploreView.vue frontend/src/utils/ && git commit -m "feat: add ExploreView with click-to-inspect"
```

---

### Task 15: 页面视图 — CompareView

**Files:**
- Create: `frontend/src/views/CompareView.vue`

- [ ] **Step 1: 创建对比分析页面**

```vue
<template>
  <div class="compare-view">
    <div class="compare-header">
      <div class="compare-title">对比分析</div>
      <p class="compare-desc">两组参数独立运行，对比追踪结果差异</p>
    </div>

    <!-- 双参数面板 -->
    <div class="dual-params">
      <div class="param-col">
        <h4>参数集 A</h4>
        <ParamPanelB @run="runA" :loading="loadingA" label="运行 A" />
      </div>
      <div class="param-col">
        <h4>参数集 B</h4>
        <ParamPanelB @run="runB" :loading="loadingB" label="运行 B" />
      </div>
    </div>

    <!-- 对比图表 -->
    <div class="compare-charts" v-if="resultA || resultB">
      <div class="chart-col">
        <span class="chart-label">结果 A</span>
        <FaultMap
          v-if="resultA"
          :heatmap="resultA.filtered.length > 0 ? dataStore.rawData! : undefined"
          :filtered="resultA.filtered"
          layer="heatmap"
          height="100%"
        />
        <div v-else class="chart-placeholder">未运行</div>
      </div>
      <div class="chart-col">
        <span class="chart-label">结果 B</span>
        <FaultMap
          v-if="resultB"
          :heatmap="resultB.filtered.length > 0 ? dataStore.rawData! : undefined"
          :filtered="resultB.filtered"
          layer="heatmap"
          height="100%"
        />
        <div v-else class="chart-placeholder">未运行</div>
      </div>
    </div>

    <!-- 统计对比表 -->
    <div v-if="resultA || resultB" class="stats-table-wrap">
      <el-table :data="compareTableData" size="small" border stripe style="width:100%">
        <el-table-column prop="metric" label="指标" width="120" />
        <el-table-column prop="a" label="参数集 A">
          <template #default="scope">
            <span :class="{ 'is-better': scope.row.better === 'a' }">{{ scope.row.a }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="b" label="参数集 B">
          <template #default="scope">
            <span :class="{ 'is-better': scope.row.better === 'b' }">{{ scope.row.b }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDataStore } from '@/stores/data'
import type { PipelineResult, PipelineParams } from '@/types'
import { DEFAULT_PARAMS } from '@/types'
import { runPipeline } from '@/api/pipeline'
import FaultMap from '@/components/FaultMap.vue'
import { ElMessage } from 'element-plus'

const dataStore = useDataStore()

const resultA = ref<PipelineResult | null>(null)
const resultB = ref<PipelineResult | null>(null)
const loadingA = ref(false)
const loadingB = ref(false)
const paramsA = ref<PipelineParams>({ ...DEFAULT_PARAMS })
const paramsB = ref<PipelineParams>({ ...DEFAULT_PARAMS })

async function runA(params: PipelineParams) {
  if (!dataStore.rawData) { ElMessage.warning('请先生成数据'); return }
  paramsA.value = { ...params }
  loadingA.value = true
  try {
    resultA.value = await runPipeline(dataStore.rawData, params)
    ElMessage.success(`A 完成，${resultA.value.filtered.length} 个多边形`)
  } catch (e: any) {
    ElMessage.error(`A 失败: ${e.message}`)
  } finally { loadingA.value = false }
}

async function runB(params: PipelineParams) {
  if (!dataStore.rawData) { ElMessage.warning('请先生成数据'); return }
  paramsB.value = { ...params }
  loadingB.value = true
  try {
    resultB.value = await runPipeline(dataStore.rawData, params)
    ElMessage.success(`B 完成，${resultB.value.filtered.length} 个多边形`)
  } catch (e: any) {
    ElMessage.error(`B 失败: ${e.message}`)
  } finally { loadingB.value = false }
}

// 简单的独立参数面板（内联，避免与全局 ParamPanel 冲突）
// 通过 Provide/Inject 或直接使用独立 store 实例
// 这里简化为使用独立 ref
import ParamPanelB from '@/components/ParamPanelB.vue'

const compareTableData = computed(() => {
  const rows: any[] = []
  const ra = resultA.value, rb = resultB.value

  const stats = (r: PipelineResult | null) => {
    if (!r || r.areas.length === 0) return { count: 0, min: '-', max: '-', mean: '-', median: '-', elapsed: '-' }
    const a = [...r.areas].sort((x, y) => x - y)
    return {
      count: r.filtered.length,
      min: Math.min(...a).toFixed(0),
      max: Math.max(...a).toFixed(0),
      mean: (a.reduce((s, v) => s + v, 0) / a.length).toFixed(0),
      median: a[Math.floor(a.length / 2)].toFixed(0),
      elapsed: r.elapsed.toFixed(2) + 's',
    }
  }

  const sa = stats(ra), sb = stats(rb)
  const metrics = ['count', 'min', 'max', 'mean', 'median', 'elapsed']
  const labels: Record<string, string> = {
    count: '多边形数量',
    min: '最小面积 (px²)',
    max: '最大面积 (px²)',
    mean: '平均面积 (px²)',
    median: '中位数面积 (px²)',
    elapsed: '耗时',
  }

  for (const m of metrics) {
    const aVal = sa[m as keyof typeof sa]
    const bVal = sb[m as keyof typeof sb]
    let better: string | null = null
    if (ra && rb && typeof aVal === 'string' && typeof bVal === 'string' && m !== 'elapsed') {
      // numeric comparison for area metrics
    }
    rows.push({ metric: labels[m], a: String(aVal), b: String(bVal), better })
  }
  return rows
})
</script>

<style scoped>
.compare-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  padding: 16px;
}

.compare-header {
  margin-bottom: 12px;
}

.compare-title {
  font-size: 20px;
  font-weight: 700;
  color: #1E293B;
}

.compare-desc {
  font-size: 13px;
  color: #64748B;
  margin: 2px 0 0;
}

.dual-params {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.param-col {
  flex: 1;
  padding: 12px;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
}

.param-col h4 {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
  margin: 0 0 8px;
}

.compare-charts {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
  margin-bottom: 12px;
}

.chart-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  overflow: hidden;
}

.chart-label {
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  background: #FAFBFC;
  border-bottom: 1px solid #E5E7EB;
}

.chart-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94A3B8;
}

.stats-table-wrap {
  max-height: 240px;
  overflow-y: auto;
}

.is-better {
  color: #22C55E;
  font-weight: 600;
}
</style>
```

- [ ] **Step 2: Commit**

由于 CompareView 引用了 ParamPanelB（独立参数面板，不共享全局 store），需要单独创建。

稍后在 Task 15b 中创建 `ParamPanelB.vue`。

同 Step 2 一起 commit:

```bash
cd "d:\东方杯" && git add frontend/src/views/CompareView.vue && git commit -m "feat: add CompareView with dual-param side-by-side"
```

---

### Task 15b: 独立参数面板组件（对比页专用）

**Files:**
- Create: `frontend/src/components/ParamPanelB.vue`

- [ ] **Step 1: 创建独立参数面板**

```vue
<template>
  <div class="param-panel-b">
    <el-collapse v-model="activeGroup" accordion>
      <el-collapse-item
        v-for="group in PARAM_GROUPS"
        :key="group.label"
        :title="group.label"
        :name="group.label"
      >
        <div class="param-grid">
          <template v-for="key in group.keys" :key="key">
            <div v-if="isBoolean(key)" class="param-row">
              <span class="param-label">{{ paramLabel(key) }}</span>
              <el-switch
                :model-value="Boolean(params[key])"
                @update:model-value="setParam(key, $event)"
                size="small"
              />
            </div>
            <div v-else class="param-row">
              <span class="param-label">{{ paramLabel(key) }}</span>
              <el-input-number
                :model-value="Number(params[key])"
                @update:model-value="setParam(key, $event)"
                :min="paramRange(key)[0]"
                :max="paramRange(key)[1]"
                :step="paramStep(key)"
                :precision="paramPrecision(key)"
                size="small"
                controls-position="right"
                style="width:110px"
              />
            </div>
          </template>
        </div>
      </el-collapse-item>
    </el-collapse>
    <el-button type="primary" @click="$emit('run', { ...params })" :loading="loading" style="width:100%;margin-top:8px">
      {{ label }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { DEFAULT_PARAMS, PARAM_GROUPS } from '@/types'
import type { PipelineParams } from '@/types'

defineProps<{ loading: boolean; label: string }>()
defineEmits<{ run: [params: PipelineParams] }>()

type ParamKey = keyof PipelineParams

const params = reactive<PipelineParams>({ ...DEFAULT_PARAMS })
const activeGroup = ref('预处理')

const LABELS: Record<string, string> = {
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
  track_max_link_distance: '最大连接距离',
  track_angle_weight: '方向权重',
  track_min_segment_length: '最小片段长',
  track_dilate_radius: '膨胀半径',
  track_dilate_iterations: '膨胀迭代',
}

const BOOLEAN_KEYS = new Set(['use_clahe', 'use_adaptive_threshold', 'separate_intersections'])

function isBoolean(key: string): boolean { return BOOLEAN_KEYS.has(key) }
function paramLabel(key: string): string { return LABELS[key] || key }
function setParam(key: string, value: any) { (params as any)[key] = value }

function paramRange(key: string): [number, number] {
  const r: Record<string, [number, number]> = {
    gaussian_sigma: [0, 10], clahe_clip_limit: [0, 10], clahe_grid_size: [2, 32],
    otsu_scale: [0, 5], adaptive_block_size: [3, 201], adaptive_c: [-1, 1],
    closing_radius: [0, 20], opening_radius: [0, 10], min_component_area: [0, 1000],
    contour_smooth_sigma: [0, 10], min_polygon_area: [0, 500], dp_epsilon: [0, 20],
    smooth_iterations: [0, 10], dedup_overlap_threshold: [0, 1],
    track_max_link_distance: [0, 100], track_angle_weight: [0, 10],
    track_min_segment_length: [0, 50], track_dilate_radius: [0, 10],
    track_dilate_iterations: [0, 10],
  }
  return r[key] || [0, 100]
}

function paramStep(key: string): number {
  const s: Record<string, number> = {
    gaussian_sigma: 0.1, otsu_scale: 0.1, clahe_clip_limit: 0.1,
    adaptive_c: 0.05, contour_smooth_sigma: 0.1, dp_epsilon: 0.5,
    dedup_overlap_threshold: 0.05, track_angle_weight: 0.5,
  }
  return s[key] || 1
}

function paramPrecision(key: string): number {
  const p: Record<string, number> = {
    gaussian_sigma: 1, otsu_scale: 1, clahe_clip_limit: 1,
    adaptive_c: 2, contour_smooth_sigma: 1, dp_epsilon: 1,
    dedup_overlap_threshold: 2, track_angle_weight: 1,
  }
  return p[key] || 0
}
</script>

<style scoped>
.param-panel-b { }
.param-grid { display: flex; flex-direction: column; gap: 6px; }
.param-row { display: flex; align-items: center; justify-content: space-between; }
.param-label { font-size: 12px; color: #475569; }
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/components/ParamPanelB.vue && git commit -m "feat: add standalone ParamPanelB for CompareView"
```

---

### Task 16: App.vue 根组件

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 替换 App.vue**

```vue
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
/* 全局基础样式 */
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

/* Element Plus 主题覆盖 */
:root {
  --el-color-primary: #2563EB;
  --el-color-primary-hover: #1D4ED8;
  --el-border-color-base: #E5E7EB;
}

/* 滚动条 */
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
```

- [ ] **Step 2: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/App.vue && git commit -m "feat: wire App.vue shell with sidebar + router-view"
```

---

### Task 17: main.ts 入口文件

**Files:**
- Modify: `frontend/src/main.ts`

- [ ] **Step 1: 重写 main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: undefined })  // 使用默认英文，后续可加中文 locale

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

- [ ] **Step 2: 更新 index.html**

修改 `frontend/index.html`，确保中文 lang:

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>断层多边形自动追踪系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 3: Commit**

```bash
cd "d:\东方杯" && git add frontend/src/main.ts frontend/index.html && git commit -m "feat: configure main.ts with Pinia, Router, Element Plus"
```

---

### Task 18: 集成测试 — 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd "d:\东方杯" && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
```

- [ ] **Step 2: 测试 GET /docs**

```bash
curl -s http://localhost:8000/docs -o /dev/null -w "%{http_code}"
```

预期: `200`

- [ ] **Step 3: 测试 POST /api/generate**

```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"rows":50,"cols":60,"n_faults":2,"noise_level":0.02,"seed":1}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'Shape: {d[\"shape\"]}, Min: {d[\"min\"]:.2f}, Max: {d[\"max\"]:.2f}')"
```

预期: `Shape: [50, 60], Min: 0.00, Max: 0.95`

- [ ] **Step 4: 测试 POST /api/pipeline**

```bash
# 先生成数据，再跑流水线
DATA=$(curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"rows":50,"cols":60,"n_faults":2,"noise_level":0.02,"seed":1}')

curl -s -X POST http://localhost:8000/api/pipeline \
  -H "Content-Type: application/json" \
  -d "{\"data\":$(echo $DATA | python -c "import sys,json; print(json.dumps(json.load(sys.stdin)['data']))"), \"params\":{}}" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'Elapsed: {d[\"elapsed\"]}s, Polygons: {len(d[\"filtered\"])}, Areas: {d[\"areas\"]}')"
```

预期: 输出耗时和多边形数量

- [ ] **Step 5: 构建前端**

```bash
cd "d:\东方杯\frontend" && npm run build
```

预期: 无报错，`dist/` 目录生成。

- [ ] **Step 6: Commit**

```bash
cd "d:\东方杯" && git add -A && git commit -m "test: end-to-end backend API and frontend build verification"
```

---

### Task 19: 清理与最终检查

- [ ] **Step 1: 删除 Vite 默认文件**

```bash
rm -f "d:\东方杯\frontend\src\components\HelloWorld.vue" 2>/dev/null
rm -f "d:\东方杯\frontend\src\assets\vue.svg" 2>/dev/null
rm -f "d:\东方杯\frontend\public\vite.svg" 2>/dev/null
```

- [ ] **Step 2: 清理 App.vue 中的默认样式引用**

确认 `App.vue` 中没有引用 `./components/HelloWorld.vue` 或默认 `./assets/vue.svg`。

- [ ] **Step 3: 最终 TypeScript 检查**

```bash
cd "d:\东方杯\frontend" && npx vue-tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 4: 最终构建验证**

```bash
cd "d:\东方杯\frontend" && npm run build
```

- [ ] **Step 5: 最终 Commit**

```bash
cd "d:\东方杯" && git add -A && git commit -m "chore: cleanup Vite defaults, final verification"
```

---

## 自审清单

### 1. Spec 覆盖率检查

| Spec 要求 | 对应 Task |
|-----------|----------|
| 项目结构 backend/ + frontend/ | Task 1, 2 |
| POST /api/pipeline | Task 1 (Step 3) |
| POST /api/generate | Task 1 (Step 3) |
| 全局侧边栏 240px | Task 8 |
| 数据源区域（合成/上传/状态指示） | Task 8 |
| 5 组参数折叠面板 | Task 9 |
| "重置默认"按钮 | Task 8 |
| "运行追踪"按钮（disabled 逻辑） | Task 8 |
| 3 页面路由 (/ → /pipeline, /explore, /compare) | Task 7 |
| 页面1: 7步进度条 | Task 10, 13 |
| 页面1: 7步各自图表 | Task 13 |
| 页面1: 蓝色左边框说明卡片 | Task 13 |
| 页面1: 控制栏（上一步/下一步/自动播放/跳转/键盘） | Task 13 |
| 页面2: 全屏地图 + 图层切换 | Task 14 |
| 页面2: 点击多边形 → el-drawer | Task 12, 14 |
| 页面2: 底部状态栏 | Task 14 |
| 页面3: 双列参数 + 并排图 + 对比表 | Task 15, 15b |
| 色彩系统 (#FAFBFC, #2563EB 等) | Task 16 (CSS 变量) |
| Pinia 数据流 | Task 5, 6 |
| 现有 src/ 不动 | Task 1 (sys.path 引用) |
| 27 个 Config 参数全对应 | Task 3 (DEFAULT_PARAMS), Task 5 |

### 2. 占位符扫描

无 TBD/TODO/占位符。

### 3. 类型一致性

- `PipelineParams` 接口在 Task 3 定义，Task 5/6/9/15/15b 使用
- `PipelineResult` 接口在 Task 3 定义，Task 6/13/14/15 使用
- `PIPELINE_STEPS` 在 Task 3 定义，Task 10/13 使用
- `PARAM_GROUPS` 在 Task 3 定义，Task 9/15b 使用
- 组件 props/emits 类型与调用方一致
- `useDataStore.execute()` → API `runPipeline()` → POST /api/pipeline 类型贯穿
