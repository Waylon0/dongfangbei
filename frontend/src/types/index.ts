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
    label: '简化/过滤',
    keys: ['dp_epsilon', 'smooth_iterations', 'min_polygon_area'],
  },
]
