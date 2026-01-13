import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.stats import median_abs_deviation
from numpy.typing import NDArray
from typing import Sequence
import cv2


"""

"""

__all__ = [
    "get_coord_min_rect_len",
    "calc_length_diff",
    "calc_speed"
]





def get_coord_min_rect_len(seg_coords: Sequence[int] | NDArray[np.integer] | NDArray[np.floating],):
    """计算多边形坐标的最小外接矩形的长度，这里指的较大的边"""
    arr = np.asarray(seg_coords, dtype=np.float32)
    if arr.size < 6:
        return 0.0
    if arr.ndim == 1:
        if int(arr.size) % 2 != 0:
            return 0.0
        pts = arr.reshape(-1, 2)
    elif arr.ndim == 2 and arr.shape[1] == 2:
        pts = arr
    else:
        return 0.0

    if pts.shape[0] < 3:
        return 0.0

    try:
        cv_pts = pts.reshape((-1, 1, 2)).astype(np.float32)
        (_, (w, h), _) = cv2.minAreaRect(cv_pts)
        return float(max(w, h))
    except Exception:
        xs = pts[:, 0]
        ys = pts[:, 1]
        w = float(xs.max() - xs.min())
        h = float(ys.max() - ys.min())
        return float(max(w, h))



def detect_outliers_mad(data, threshold=2.0):
        """
        使用 Modified Z-score 检测异常点
        """
        median = np.median(data)
        mad = median_abs_deviation(data)
        
        # 防止除以0
        if mad == 0:
            return np.zeros_like(data, dtype=bool)
        
        # 计算 Modified Z-score
        modified_z_score = 0.6745 * (data - median) / mad
        return np.abs(modified_z_score) > threshold



def fix_to_monotonic_decreasing(lens):
        """
            从峰值开始修正为单调减的序列，
            并且对峰值做了离群点和均值优化
            
            （原地修改list）
        """

        if not lens:
            return lens, 0
            

        arr = np.asarray(lens, dtype=np.float64)
        try:
            peak_idx = int(np.nanargmax(arr))
        except ValueError:
            peak_idx = 0

        left = max(0, peak_idx - 4)
        right = min(len(lens) - 1, peak_idx + 4)
        xs = np.arange(left, right + 1, dtype=np.float64)
        ys = np.asarray(lens[left : right + 1], dtype=np.float64)
        finite_mask = np.isfinite(ys)
        if finite_mask.any():
            xs_f = xs[finite_mask]
            ys_f = ys[finite_mask]
            if xs_f.size >= 3:
                x0 = xs_f - xs_f.mean()
                A = np.column_stack([x0, np.ones_like(x0)])
                (m, b), *_ = np.linalg.lstsq(A, ys_f, rcond=None)
                residuals = ys_f - (m * x0 + b)
                outlier_mask = detect_outliers_mad(residuals)
                inlier_mask = ~outlier_mask

                if np.count_nonzero(inlier_mask) < 3:
                    order = np.argsort(np.abs(residuals))
                    inlier_mask = np.zeros_like(residuals, dtype=bool)
                    inlier_mask[order[: min(3, ys_f.size)]] = True

                peak_avg = float(np.mean(ys_f[inlier_mask]))
            else:
                peak_avg = float(np.mean(ys_f))
            lens[0] = peak_avg

        for i in range(1, len(lens)):
            if lens[i] > lens[i - 1]:
                lens[i] = lens[i - 1]
        
        
        

        return lens, peak_idx



def calc_length_diff(length_list, swin=6, step=2):
    '''
        计算长度列表的长度差列表
    '''
        
    def _average_within(nums, index, r=2):
        # 计算前后 r 个数的范围，考虑到列表边界
        start = max(0, index - r)
        end = min(len(nums), index + r + 1)
        
        # 提取范围内的子列表并计算平均值
        values = nums[start:end]
        
        # 计算并返回平均值
        if values:
            return sum(values) / len(values)
        else:
            return None  # 如果范围内没有元素，返回 None
        
    lengths_diff = []
    indexes = []
    n = len(length_list)
    for i in range(0, n - swin + 1, step):
        start = _average_within(length_list, i, r=2)
        end = _average_within(length_list, i + swin - 1, r=2) 
        diff = start - end
        lengths_diff.append(diff)
        indexes.append(i)


    return lengths_diff, indexes




def calc_speed(
    lengths : list[float], 
    start_end: (int, int), 
    fps=30, 
    swin=8,  # 计算瞬时速度区间窗口
    step=2, # 窗口步长
    init_shaft_len = 20, # 针梗的实际长度，单位为毫米
    init_speed_sample_points: int = 5,
):
    """
        基于视频帧针梗长度，计算穿刺速度
    """



    def gaussian_smoothing(lens, sigma=3):
        """高斯平滑"""
        return gaussian_filter1d(lens, sigma=sigma).tolist()

    
    start_idx, end_idx = start_end
    
    
    
    needle_lengths = gaussian_smoothing(lengths) #对长度平滑
    start_length = needle_lengths[start_idx]
    end_length = needle_lengths[end_idx]
    if start_length<=0:
        start_length = 0.000001 #避免除以0
    
    # 计算比例因子
    r = (init_shaft_len/start_length)


    # -------------- 计算1/10长度变化 START -----------------
    # move_threshold = 2
    # insert_threshold = move_threshold/init_shaft_len
    # start_speed = 0.0
    # for i,nlength in enumerate(needle_lengths):
    #     if (start_length - nlength)/start_length >= insert_threshold:
    #         length_diff = (start_length - nlength) * r
    #         time_diff = (i - start_idx) / fps
    #         start_speed = length_diff / time_diff if time_diff != 0 else 0.0
    #         break
    

    # -------------- 计算平均速度 START -----------------
    # 计算长度差值
    length_diff = max(0.0, (start_length - end_length) * r)
    # 计算时间差（秒）
    time_diff = (end_idx - start_idx) / fps
    # 计算平均速度（长度单位/秒）
    avg_speed = length_diff / time_diff if time_diff != 0 else 0.0
    # -------------- 计算平均速度 END -----------------


    # -------------- 计算瞬时速度 START -----------------
    needle_lengths_diff, needle_lengths_index = calc_length_diff(needle_lengths, swin=swin, step=step)
    swin_time_diff = swin/fps
    instantaneous_speeds = [ (max(0.0, len_diff)*r)/swin_time_diff for len_diff in needle_lengths_diff]
    # -------------- 计算瞬时速度 END -----------------


    # -------------- 计算初始速度 START -----------------
    '''
        计算若干个速度点的“加速度”。
        - sum =  instantaneous_speeds[0]
        - sum += instantaneous_speeds[1], 然后判断“加速度”[0] ,若大于2 则停止 sum自增，否则继续加。
        - ...
        - 最终算平均速度。
    '''
    if not instantaneous_speeds:
        init_speed = 0.0
    else:
        sample_points_count = max(1, int(init_speed_sample_points))
        first_pos = next((i for i, x in enumerate(instantaneous_speeds) if x >= 0.6), None)
        if first_pos is None:
            first_pos = 0

        if len(instantaneous_speeds) >= sample_points_count:
            first_pos = min(max(0, first_pos), len(instantaneous_speeds) - sample_points_count)
            speed_points = instantaneous_speeds[first_pos : first_pos + sample_points_count]
        else:
            first_pos = min(max(0, first_pos), len(instantaneous_speeds) - 1)
            speed_points = instantaneous_speeds[first_pos:]

        time_step = (step/fps)
        accelerations = [(speed_points[i + 1] - speed_points[i]) /time_step for i in range(len(speed_points) - 1)]

        speed_sum = speed_points[0]
        speed_count = 1
        for i, a in enumerate(accelerations):
            speed_sum += speed_points[i + 1]
            speed_count += 1
            if a > 10: # 根据实际视频总结出来 10 是一个合理的阈值 (可根据 初始速度定义 进行调整)
                break

        init_speed = speed_sum / speed_count
    # -------------- 计算初始速度 END -----------------

    return init_speed, avg_speed, instantaneous_speeds
