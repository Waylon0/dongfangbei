"""数据加载与预处理"""

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import exposure
from .utils import normalize


def _load_dat(filepath: str) -> np.ndarray:
    """解析 GeoEast 导出的 ASCII .dat 格式属性网格文件。

    格式：空格分隔，首行为 # 注释头，后续每行：
    Line  CMP  X  Y  Value
    根据 Line 和 CMP 的唯一个数构建规则网格，Value 填充到对应位置。
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # 跳过注释头
    rows_data = []
    for line in lines:
        if line.startswith('#'):
            continue
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        rows_data.append((int(parts[0]), int(parts[1]), float(parts[4])))

    # 确定网格维度
    lines_vals = sorted(set(r[0] for r in rows_data))
    cmps_vals = sorted(set(r[1] for r in rows_data))
    line_to_idx = {v: i for i, v in enumerate(lines_vals)}
    cmp_to_idx = {v: i for i, v in enumerate(cmps_vals)}

    data = np.zeros((len(lines_vals), len(cmps_vals)), dtype=np.float64)
    for line, cmp, val in rows_data:
        data[line_to_idx[line], cmp_to_idx[cmp]] = val

    return data


def load_attribute_data(filepath: str) -> np.ndarray:
    """加载沿层属性数据。支持 .npy / .npz / .dat 格式。

    输入数据预期为2D numpy数组，形状 (rows, cols)，
    每个像素值代表该位置的断层响应强度。
    """
    if filepath.endswith('.dat'):
        return _load_dat(filepath)
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
