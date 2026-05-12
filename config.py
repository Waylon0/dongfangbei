"""可调参数配置"""


class Config:
    # --- 预处理 ---
    gaussian_sigma: float = 1.5       # 高斯滤波σ
    use_clahe: bool = False           # CLAHE对比度增强
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8

    # --- 二值化 ---
    otsu_scale: float = 1.0           # Otsu阈值缩放（>1更保守，<1更敏感）

    # --- 形态学处理 ---
    closing_radius: int = 5           # 闭运算半径（填充小孔洞）
    opening_radius: int = 2           # 开运算半径（去除噪点）

    # --- 断层分离 ---
    min_component_area: int = 100     # 最小连通域面积（像素）
    separate_intersections: bool = True  # 是否在交叉处分离不同断层

    # --- 轮廓提取 ---
    contour_smooth_sigma: float = 2.0 # 轮廓平滑σ

    # --- 多边形过滤 ---
    min_polygon_area: float = 50      # 最小多边形面积（像素）

    # --- 多边形简化 ---
    dp_epsilon: float = 3.0           # Douglas-Peucker简化容差
    smooth_iterations: int = 2        # Chaikin平滑迭代次数

    # --- 多尺度 ---
    scales: list = [1.0, 2.0]         # 多尺度σ列表（单尺度用 []）
    dedup_overlap_threshold: float = 0.5  # 去重重合度（IoU）

    # --- 导出 ---
    output_format: str = 'geojson'    # geojson / txt
