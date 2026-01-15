
import os
import tempfile
import shutil
import ffmpeg
import cv2
import numpy as np
import math
import torch
from numpy.typing import NDArray
from torch import Tensor
from typing import Dict, List, Literal, Sequence, Tuple, TypedDict


class VideoFramesMeta(TypedDict):
    width: int
    height: int
    fps: int
    codec: str
    frame_count: int


class VideoFramesResult(TypedDict):
    frames: List[NDArray[np.uint8]]
    meta: VideoFramesMeta


VideoResolutionLevel = Literal["720", "1080", "2k", "4k"]


def get_video_resolution_level(width: int, height: int) -> VideoResolutionLevel:
    longest_side = max(int(width), int(height))
    if longest_side < 1920:
        return "720"
    if longest_side < 2560:
        return "1080"
    if longest_side < 3840:
        return "2k"
    return "4k"


def get_detect_box_sacle(width: int, height: int):
    level = get_video_resolution_level(width, height)
    match level:
        case "720":
            return 2.5
        case "1080":
            return 2.3
        case "2k":
            return 2.1
        case "4k":
            return 2




def extract_video_frames(video_path: str) -> VideoFramesResult:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc = (
        chr(fourcc_int & 0xFF)
        + chr((fourcc_int >> 8) & 0xFF)
        + chr((fourcc_int >> 16) & 0xFF)
        + chr((fourcc_int >> 24) & 0xFF)
    )

    frames: List[NDArray[np.uint8]] = []
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame.copy())
    finally:
        cap.release()
        cv2.destroyAllWindows()

    meta: VideoFramesMeta = {
        "width": frame_width,
        "height": frame_height,
        "fps": fps,
        "codec": fourcc,
        "frame_count": len(frames),
    }
    return {"frames": frames, "meta": meta}

def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def frames2tensors(
    frames: List[NDArray[np.uint8]],
    device: torch.device,
) -> List[Tensor]:
    """
        将视频帧列表转为归一化的 CHW torch.Tensor 列表
    """
    tensors: List[Tensor] = []
    for frame in frames:
        if frame is None:
            raise ValueError("frame in frames is None")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_contiguous = np.ascontiguousarray(rgb)
        tensor = torch.from_numpy(rgb_contiguous).permute(2, 0, 1)
        tensor = tensor.to(device).float() / 255.0
        tensors.append(tensor)
    return tensors


def make_group_square_annotations(
    annotations: List[List[Dict[str, float]]],
    group_size: int,
    image_size: Tuple[int, int],
) -> List[List[Dict[str, float]]]:
    """
        将预测框按“顺序分组”，每组取该组内最大的边长，然后把组内每个框调整为同尺寸正方形框：
        - 分组顺序：按 annotations 的遍历顺序（先帧后框）扁平化后，每 group_size 个为一组
        - 正方形边长：先取组内最大像素边长，再向上取整到 [224, 640] 范围内的 32 倍数
        - 每个框保持中心点不变（若越界则平移回 [0,1] 范围内）
    """
    if group_size <= 0:
        raise ValueError("group_size must be positive")

    width, height = int(image_size[0]), int(image_size[1])
    if width <= 0 or height <= 0:
        raise ValueError("image_size must be positive (width, height)")

    flat: List[Tuple[int, Dict[str, float]]] = []
    for frame_idx, frame_boxes in enumerate(annotations):
        for ann in frame_boxes:
            flat.append((frame_idx, ann))

    if not flat:
        return annotations

    min_side = 32 * 7
    max_side = 32 * 20
    step = 32

    def quantize_side_px(side_px: float) -> int:
        target = max(float(side_px), float(min_side))
        quantized = int(math.ceil(target / float(step)) * step)
        return int(max(min_side, min(max_side, quantized)))

    group_side_px_list: List[int] = []
    current_max_px = 0.0
    current_count = 0
    for _, ann in flat:
        w_n = float(ann["x2"] - ann["x1"])
        h_n = float(ann["y2"] - ann["y1"])
        w_px = w_n * float(width)
        h_px = h_n * float(height)
        current_max_px = max(current_max_px, max(w_px, h_px))
        current_count += 1
        if current_count >= group_size:
            group_side_px_list.append(quantize_side_px(current_max_px))
            current_max_px = 0.0
            current_count = 0
    if current_count > 0:
        group_side_px_list.append(quantize_side_px(current_max_px))

    out: List[List[Dict[str, float]]] = [[] for _ in range(len(annotations))]
    for flat_idx, (frame_idx, ann) in enumerate(flat):
        group_idx = flat_idx // group_size
        side_px = int(group_side_px_list[group_idx]) if group_idx < len(group_side_px_list) else 0
        if side_px <= 0:
            continue

        max_side_x = float(side_px) / float(width)
        max_side_y = float(side_px) / float(height)
        half_x = max_side_x / 2.0
        half_y = max_side_y / 2.0

        x1 = float(ann["x1"])
        y1 = float(ann["y1"])
        x2 = float(ann["x2"])
        y2 = float(ann["y2"])

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        new_x1 = cx - half_x
        new_x2 = cx + half_x
        if new_x1 < 0.0:
            shift = -new_x1
            new_x1 += shift
            new_x2 += shift
        if new_x2 > 1.0:
            shift = new_x2 - 1.0
            new_x1 -= shift
            new_x2 -= shift

        new_y1 = cy - half_y
        new_y2 = cy + half_y
        if new_y1 < 0.0:
            shift = -new_y1
            new_y1 += shift
            new_y2 += shift
        if new_y2 > 1.0:
            shift = new_y2 - 1.0
            new_y1 -= shift
            new_y2 -= shift

        new_x1 = float(max(0.0, min(1.0, new_x1)))
        new_y1 = float(max(0.0, min(1.0, new_y1)))
        new_x2 = float(max(0.0, min(1.0, new_x2)))
        new_y2 = float(max(0.0, min(1.0, new_y2)))

        if new_x2 <= new_x1 or new_y2 <= new_y1:
            continue

        new_ann = dict(ann)
        new_ann["x1"] = new_x1
        new_ann["y1"] = new_y1
        new_ann["x2"] = new_x2
        new_ann["y2"] = new_y2
        new_ann["square_side_px"] = float(side_px) # 正方形边长
        out[frame_idx].append(new_ann)

    return out

def save_frames2video(
    frames: List[NDArray[np.uint8]],
    output_path: str,
    fps: int,
    size: Tuple[int, int],
) -> None:
    """
        保存视频帧到视频文件
    """
    if not frames:
        raise ValueError("frames is empty")

    width, height = size
    tmp_dir = tempfile.mkdtemp(prefix="detect_frames_")

    try:
        for idx, frame in enumerate(frames):
            resized = cv2.resize(frame, (width, height))
            frame_path = os.path.join(tmp_dir, f"frame_{idx:06d}.png")
            ok = cv2.imwrite(frame_path, resized)
            if not ok:
                raise RuntimeError(f"Failed to write frame {idx} to disk")

        input_pattern = os.path.join(tmp_dir, "frame_%06d.png")
        (
            ffmpeg.input(input_pattern, framerate=fps)
            .output(
                output_path,
                vcodec="libx264",
                pix_fmt="yuv420p",
                movflags="faststart",
                format="mp4",
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        error_message = e.stderr.decode() if e.stderr else str(e)
        raise RuntimeError(f"Error during ffmpeg processing: {error_message}") from e
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)







def get_coord_mask(
    image_shape: tuple[int, int] | tuple[int, int, int] | NDArray[np.uint8],
    seg_coords: Sequence[int] | NDArray[np.integer] | NDArray[np.floating],
    color: tuple[int, int, int] = (255, 255, 0),
) -> NDArray[np.uint8]:
    """根据多边形坐标绘制掩码"""
    shape = getattr(image_shape, "shape", image_shape)
    if shape is None or len(shape) < 2:
        raise ValueError(f"invalid image_shape: {shape}")

    height, width = int(shape[0]), int(shape[1])
    channels = int(shape[2]) if len(shape) >= 3 else 1

    if channels <= 1:
        mask: NDArray[np.uint8] = np.zeros((height, width), dtype=np.uint8)
    else:
        mask = np.zeros((height, width, channels), dtype=np.uint8)

    arr = np.asarray(seg_coords, dtype=np.float32)
    if arr.size < 6:
        return mask
    if arr.ndim == 1 and int(arr.size) % 2 != 0:
        return mask

    pts = arr.reshape(-1, 2)
    xs = np.clip(np.round(pts[:, 0]), 0, width - 1).astype(np.int32)
    ys = np.clip(np.round(pts[:, 1]), 0, height - 1).astype(np.int32)
    cv_pts = np.stack([xs, ys], axis=1).reshape((-1, 1, 2))

    if channels <= 1:
        cv2.fillPoly(mask, [cv_pts], 255)
    else:
        fill_color = tuple(int(c) for c in color[:channels])
        cv2.fillPoly(mask, [cv_pts], fill_color)

    return mask
