# Vue 3 前端重构设计文档

## 背景

断层多边形自动追踪系统当前使用 Streamlit 前端，Python 流水线逻辑完整，但前端受限于 Streamlit 框架能力，视觉效果和交互自由度不足。目标是用 Vue 3 重写前端，FastAPI 封装后端，做到 Linear/Notion 级别的现代工具质感。

## 技术选型

| 项 | 选择 | 理由 |
|---|------|------|
| 前端框架 | Vue 3 + Vite | 用户熟悉，生态成熟 |
| UI 组件库 | Element Plus | 中文资料最全，主题可定制 |
| 图表库 | ECharts | 热力图/轮廓叠加原生支持，交互强 |
| 后端 | FastAPI | Python 流水线直接复用 |
| 通信 | REST API | 流水线 2-3s，一次请求返回全部结果 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| 路由 | Vue Router 4 | 3 页面 SPA |

## 项目结构

```
东方杯/
├── backend/
│   ├── main.py              # FastAPI + CORS
│   ├── api/
│   │   └── pipeline.py      # POST /api/pipeline
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── views/            # 3 页面
│   │   │   ├── PipelineView.vue
│   │   │   ├── ExploreView.vue
│   │   │   └── CompareView.vue
│   │   ├── components/       # 共享组件
│   │   │   ├── AppSidebar.vue
│   │   │   ├── StepProgress.vue
│   │   │   ├── ParamPanel.vue
│   │   │   ├── FaultMap.vue
│   │   │   └── PolyDetail.vue
│   │   ├── stores/           # Pinia
│   │   │   ├── data.ts
│   │   │   └── params.ts
│   │   ├── api/              # axios
│   │   │   └── pipeline.ts
│   │   └── router/
│   │       └── index.ts
│   ├── package.json
│   └── vite.config.ts
├── src/                      # 现有流水线，不动
├── config.py                 # 现有配置，不动
└── data/
```

## 路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向 → `/pipeline` | |
| `/pipeline` | 分步流水线 | 答辩核心页，7 步逐步展示 |
| `/explore` | 交互探索 | 全屏地图，点击多边形看详情 |
| `/compare` | 对比分析 | 双参数集并排对比 |

## API

**POST /api/pipeline**

请求：
```json
{
  "data": [[...], [...]],  // 属性数据 2D 数组
  "params": {
    "gaussian_sigma": 1.5,
    "otsu_scale": 1.0,
    ...
  }
}
```

响应：
```json
{
  "binary": [[...]],
  "binary_before_morph": [[...]],
  "data_smoothed": [[...]],
  "skeleton": [[...]],
  "junctions": [[...]],
  "contours": [[...]],
  "filtered": [[...]],
  "areas": [...],
  "elapsed": 2.345
}
```

**POST /api/generate** — 生成合成测试数据

## 全局侧边栏（240px 固定）

- 标题 "断层多边形追踪" + 英文副标题 + 蓝色装饰线
- 数据源区域：合成数据（行/列/断层数/噪声/种子 + 生成按钮）或上传文件（.npy/.npz/.dat）
- 数据状态指示：已加载时显示绿色状态点 + 尺寸
- 算法参数：5 组折叠面板（预处理/分割/提取/追踪/简化过滤），一次只展开一组
- 参数组控件：slider / number input / toggle，与现有 Config 参数完全对应
- "重置默认"按钮
- 蓝色主按钮"运行追踪"（未加载数据时 disabled）
- "下载 GeoJSON"按钮（有结果后才显示）

## 页面 1：分步流水线

- 顶部 7 步水平进度条：完成=蓝色实心，当前=深蓝高亮，未完成=灰色
- 中间 ECharts 大图表区域，占页面主体（70% 高度）
- 图表下方蓝色左边框说明卡片，显示当前步骤标题 + 描述
- 底部控制栏：上一步 / 下一步 / 自动播放 toggle / 跳转下拉 / AI 语音按钮
- 键盘左右箭头支持切换步骤
- 7 步各自展示内容：
  1. 原始数据 → 热力图
  2. 预处理 → 平滑数据 + 二值化对比
  3. 形态学 → 处理前后对比
  4. 轮廓提取 → 热力图叠加轮廓线
  5. 交叉点 → 骨架图 + 红色交叉点
  6. 最终结果 → 原始数据叠加简化多边形
  7. 总览 → 6 小图网格 + 面积直方图 + 统计数字

## 页面 2：交互探索

- 全屏 ECharts 地图（热力图 + 多边形叠加图层）
- 支持滚轮缩放、拖拽平移、点击多边形
- 顶部图层切换按钮（热力图 / 二值图 / 纯多边形）
- 点击多边形 → 右侧滑出 el-drawer，显示面积、顶点数、顶点坐标表
- 底部状态栏：多边形数量、面积范围、筛选状态

## 页面 3：对比分析

- 上方左右两列参数面板，各自独立折叠
- 各自"运行 A"/"运行 B"按钮
- 中间 ECharts 并排对比图
- 下方 el-table 差异统计表格（数量 / 最小面积 / 最大面积 / 平均面积 / 中位数 / 耗时）

## 色彩系统

- 主背景: #FAFBFC
- 侧边栏: #F1F4F8
- 主蓝色: #2563EB → hover #1D4ED8
- 文字主色: #1E293B
- 文字次要: #64748B
- 边框: #E5E7EB
- 成功绿: #22C55E
- 卡片阴影: 0 1px 3px rgba(0,0,0,0.05)
- 卡片悬浮: 0 4px 12px rgba(0,0,0,0.08)

## 分步数据流

1. 用户上传/生成数据 → Pinia data store
2. 调节参数 → Pinia params store
3. 点击"运行追踪" → api/pipeline.ts POST → 后端跑 run_pipeline_with_steps()
4. 响应存入 Pinia → 各页面响应式渲染 ECharts
