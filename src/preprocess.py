"""数据加载与预处理"""

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import exposure
from .utils import normalize


def load_attribute_data(filepath: str) -> np.ndarray:
    """加载沿层属性数据。支持 .npy / .npz 格式。

    输入数据预期为2D numpy数组，形状 (rows, cols)，
    每个像素值代表该位置的断层响应强度。
    """
    if filepath.endswith('.npz'):
        data = np.load(filepath)
        key = list(data.keys())[0]
        return data[key].astype(np.float64)
    else:
        return np.load(filepath).astype(np.float64)


def preprocess(data: np.ndarray, sigma: float = 1.0,
               use_clahe: bool = False,
               clahe_clip_limit: float = 2.0,
               clahe_grid_size: int = 8,
               otsu_scale: float = 1.0) -> np.ndarray:
    """预处理流水线：
    1. 归一化
    2. CLAHE对比度增强（可选）
    3. 高斯滤波去噪
    4. Otsu自适应二值化

    返回二值图像 (0/1)。
    """
    data = normalize(data)

    # 可选 CLAHE 对比度增强
    if use_clahe:
        img_uint8 = (data * 255).astype(np.uint8)
        data = exposure.equalize_adapthist(
            img_uint8,
            kernel_size=(clahe_grid_size, clahe_grid_size),
            clip_limit=clahe_clip_limit,
        )

    # 高斯滤波去噪
    smoothed = gaussian_filter(data, sigma=sigma)

    # Otsu 自适应二值化
    from skimage.filters import threshold_otsu
    thresh = threshold_otsu(smoothed) * otsu_scale
    binary = (smoothed >= thresh).astype(np.uint8)

    return binary
