
from typing import Dict, Tuple
import math
import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt

def square_crop_with_origin(
    frame: NDArray[np.uint8],
    ann: Dict[str, float],
) -> Tuple[NDArray[np.uint8], int, int] | None:
    height, width = frame.shape[:2]

    x1_n = float(ann.get("x1", 0.0))
    y1_n = float(ann.get("y1", 0.0))
    x2_n = float(ann.get("x2", 1.0))
    y2_n = float(ann.get("y2", 1.0))

    x1_f = x1_n * width
    y1_f = y1_n * height
    x2_f = x2_n * width
    y2_f = y2_n * height

    x1_i = int(round(x1_f))
    y1_i = int(round(y1_f))
    x2_i = int(round(x2_f))
    y2_i = int(round(y2_f))

    x1_i = max(0, min(width, x1_i))
    y1_i = max(0, min(height, y1_i))
    x2_i = max(0, min(width, x2_i))
    y2_i = max(0, min(height, y2_i))

    if x2_i <= x1_i or y2_i <= y1_i:
        return None

    w_f = float(x2_f - x1_f)
    h_f = float(y2_f - y1_f)
    side_override = ann.get("square_side_px")
    if side_override is None:
        side = int(round(max(w_f, h_f)))
    else:
        side = int(round(float(side_override)))

    min_side = 32 * 6
    max_side = 32 * 20
    step = 32
    target = max(float(side), float(min_side))
    side = int(math.ceil(target / float(step)) * step)
    side = int(max(min_side, min(max_side, side)))
    if side <= 0:
        return None

    cx = (x1_f + x2_f) / 2.0
    cy = (y1_f + y2_f) / 2.0

    half_side = side / 2.0
    new_x1 = int(round(cx - half_side))
    new_y1 = int(round(cy - half_side))
    new_x2 = new_x1 + side
    new_y2 = new_y1 + side

    src_x1 = max(0, min(width, new_x1))
    src_y1 = max(0, min(height, new_y1))
    src_x2 = max(0, min(width, new_x2))
    src_y2 = max(0, min(height, new_y2))

    if src_x2 <= src_x1 or src_y2 <= src_y1:
        return None

    dst_x1 = src_x1 - new_x1
    dst_y1 = src_y1 - new_y1
    dst_x2 = dst_x1 + (src_x2 - src_x1)
    dst_y2 = dst_y1 + (src_y2 - src_y1)

    if frame.ndim == 2:
        crop: NDArray[np.uint8] = np.zeros((side, side), dtype=frame.dtype)
        crop[dst_y1:dst_y2, dst_x1:dst_x2] = frame[src_y1:src_y2, src_x1:src_x2]
    else:
        channels = int(frame.shape[2])
        crop = np.zeros((side, side, channels), dtype=frame.dtype)
        crop[dst_y1:dst_y2, dst_x1:dst_x2, :] = frame[
            src_y1:src_y2, src_x1:src_x2, :
        ]

    return crop, int(new_x1), int(new_y1)


def overlay_crop_mask_on_frame(
    frame: NDArray[np.uint8],
    crop_mask: NDArray[np.uint8],
    origin_x: int,
    origin_y: int,
    alpha: float = 0.35,
) -> NDArray[np.uint8]:
    if crop_mask.ndim != 3 or frame.ndim != 3:
        raise ValueError("frame and crop_mask must be HWC images")
    if frame.shape[2] != crop_mask.shape[2]:
        raise ValueError("frame and crop_mask must have same channels")

    fh, fw = frame.shape[:2]
    ch, cw = crop_mask.shape[:2]

    x1_full = max(int(origin_x), 0)
    y1_full = max(int(origin_y), 0)
    x2_full = min(int(origin_x + cw), fw)
    y2_full = min(int(origin_y + ch), fh)

    if x2_full <= x1_full or y2_full <= y1_full:
        return frame

    x1_crop = x1_full - int(origin_x)
    y1_crop = y1_full - int(origin_y)
    x2_crop = x1_crop + (x2_full - x1_full)
    y2_crop = y1_crop + (y2_full - y1_full)

    roi = frame[y1_full:y2_full, x1_full:x2_full]
    mask_roi = crop_mask[y1_crop:y2_crop, x1_crop:x2_crop]
    mask_idx = np.any(mask_roi != 0, axis=2)
    if not mask_idx.any():
        return frame

    roi_f = roi.astype(np.float32)
    mask_f = mask_roi.astype(np.float32)
    roi_f[mask_idx] = roi_f[mask_idx] * (1.0 - float(alpha)) + mask_f[mask_idx] * float(
        alpha
    )
    roi[:] = np.clip(roi_f, 0, 255).astype(np.uint8)

    return frame




def save_speeds_graph(y_speeds, x_datas, graph_output_path='', title=''):
    """
        保存速度折线图
    """
    plt.plot(x_datas, y_speeds, marker='.', linestyle='-', color='b', label='Line')

    # 添加标题和标签
    plt.title('speed-time, '+ title)
    plt.ylabel('speed')
    plt.xlabel('frame index')
    

    # 显示图例
    plt.legend()

    # 保存图像到指定的outpath
    plt.savefig(graph_output_path)
    plt.close()
