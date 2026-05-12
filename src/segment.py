"""断层区域分割模块

从断层属性数据中提取断层区域掩膜：
1. 阈值二值化 → 断层/非断层
2. 形态学闭运算 → 填充小孔洞、连接断缝
3. 形态学开运算 → 去除噪点
"""

import numpy as np
from scipy.ndimage import gaussian_filter, binary_closing, binary_opening
from skimage.filters import threshold_otsu
from skimage.morphology import disk
from .utils import normalize


def segment_fault_regions(data: np.ndarray,
                           sigma: float = 1.5,
                           otsu_scale: float = 1.0,
                           closing_radius: int = 5,
                           opening_radius: int = 2) -> np.ndarray:
    """从属性数据中分割出断层区域。

    参数：
        data: 归一化后的属性数据 (2D)
        sigma: 高斯滤波σ
        otsu_scale: Otsu阈值缩放因子
        closing_radius: 形态学闭运算半径
        opening_radius: 形态学开运算半径

    返回：
        二值掩膜 (0/1)，1 表示断层区域
    """
    data = normalize(data)

    # 高斯滤波去噪
    smoothed = gaussian_filter(data, sigma=sigma)

    # Otsu 阈值二值化
    thresh = threshold_otsu(smoothed) * otsu_scale
    binary = smoothed >= thresh

    # 形态学闭运算 — 填充断层区域内部小孔洞，连接断缝
    if closing_radius > 0:
        se_close = disk(closing_radius)
        binary = binary_closing(binary, structure=se_close, iterations=1)

    # 形态学开运算 — 去除孤立噪点
    if opening_radius > 0:
        se_open = disk(opening_radius)
        binary = binary_opening(binary, structure=se_open, iterations=1)

    return binary.astype(np.uint8)
