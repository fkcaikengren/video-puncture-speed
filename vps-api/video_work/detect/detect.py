from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
from numpy.typing import NDArray
from ultralytics import YOLO
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MODEL_PATH = str(Path(__file__).resolve().parent / "yolo.pt")


class VideoMeta(BaseModel):
    width: int = Field(..., description="视频宽度（像素）")
    height: int = Field(..., description="视频高度（像素）")
    fps: int = Field(..., description="视频帧率（FPS）")
    codec: str = Field(..., description="视频编码格式（fourcc）")
    frame_count: int = Field(..., description="总帧数")

    model_config = ConfigDict(extra="forbid")

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class DetectResult(BaseModel):
    frames: List[NDArray[np.uint8]] = Field(..., description="原始视频帧列表（BGR 图像）")
    detect_norm_annotation: List[List[Dict[str, float]]] = Field(
        ..., description="每帧归一化检测框列表"
    )
    meta: VideoMeta = Field(
        ..., description="视频元信息（宽高、帧率、编码、帧数）"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class Detect:
    _instance: "Detect | None" = None

    def __new__(cls, model_path: str = DEFAULT_MODEL_PATH) -> "Detect":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.model_path = model_path
        self.model = YOLO(model_path)
        self._initialized = True


    @staticmethod
    def optimize_detect_norm_annotation(
        detect_norm_annotation: List[List[Dict[str, float]]],
        wnd_size: int = 60,
        step: int = 30,
        conf_threshhold=0.5,
        box_scale=2,
    ) -> List[List[Dict[str, float]]]:
        frame_count = len(detect_norm_annotation)
        if frame_count == 0:
            return detect_norm_annotation

        filtered: List[List[Dict[str, float]]] = []
        for frame_boxes in detect_norm_annotation:
            valid_boxes = [
                box
                for box in frame_boxes
                if float(box.get("conf", 0.0)) >= conf_threshhold
            ]
            filtered.append(valid_boxes)

        optimized: List[List[Dict[str, float]]] = [[] for _ in range(frame_count)]

        for wnd_start in range(0, frame_count, step):
            wnd_end = min(wnd_start + wnd_size, frame_count)

            centers_x: List[float] = []
            centers_y: List[float] = []
            widths: List[float] = []
            heights: List[float] = []
            wh_ratios: List[float] = []
            confs: List[float] = []

            for idx in range(wnd_start, wnd_end):
                frame_boxes = filtered[idx]
                if not frame_boxes:
                    continue

                best_box = max(
                    frame_boxes,
                    key=lambda b: float(b.get("conf", 0.0)),
                )

                x1 = float(best_box.get("x1", 0.0))
                y1 = float(best_box.get("y1", 0.0))
                x2 = float(best_box.get("x2", 0.0))
                y2 = float(best_box.get("y2", 0.0))
                conf = float(best_box.get("conf", 0.0))

                w = max(x2 - x1, 0.0)
                h = max(y2 - y1, 1e-6)
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                centers_x.append(cx)
                centers_y.append(cy)
                widths.append(w)
                heights.append(h)
                wh_ratios.append(w / h)
                confs.append(conf)

            if not centers_x:
                continue

            delegate_center_x = sum(centers_x) / len(centers_x)
            delegate_center_y = sum(centers_y) / len(centers_y)
            delegate_w = sum(widths) / len(widths)
            delegate_h = sum(heights) / len(heights)
            delegate_wh_ratio = sum(wh_ratios) / len(wh_ratios)
            delegate_conf = sum(confs) / len(confs) if confs else 0.0

            half_w = delegate_w / 2.0
            half_h = delegate_h / 2.0

            x1_d = delegate_center_x - half_w
            y1_d = delegate_center_y - half_h
            x2_d = delegate_center_x + half_w
            y2_d = delegate_center_y + half_h

            x1_d = max(0.0, min(1.0, x1_d))
            y1_d = max(0.0, min(1.0, y1_d))
            x2_d = max(0.0, min(1.0, x2_d))
            y2_d = max(0.0, min(1.0, y2_d))

            if x2_d <= x1_d:
                x2_d = min(1.0, x1_d + 1e-6)
            if y2_d <= y1_d:
                y2_d = min(1.0, y1_d + 1e-6)

            for idx in range(wnd_start, wnd_end):
                frame_boxes = filtered[idx]

                if not frame_boxes:
                    use_delegate = True
                    x1 = x1_d
                    y1 = y1_d
                    x2 = x2_d
                    y2 = y2_d
                    conf = delegate_conf
                else:
                    best_box = max(
                        frame_boxes,
                        key=lambda b: float(b.get("conf", 0.0)),
                    )

                    x1 = float(best_box.get("x1", 0.0))
                    y1 = float(best_box.get("y1", 0.0))
                    x2 = float(best_box.get("x2", 0.0))
                    y2 = float(best_box.get("y2", 0.0))
                    conf = float(best_box.get("conf", 0.0))

                    w = max(x2 - x1, 0.0)
                    h = max(y2 - y1, 1e-6)
                    wh_ratio = w / h
                    cx = (x1 + x2) / 2.0
                    cy = (y1 + y2) / 2.0

                    invalid_ratio = (
                        wh_ratio >= 2.0 * delegate_wh_ratio
                        or wh_ratio <= 0.5 * delegate_wh_ratio
                    )
                    invalid_center = (
                        cx < x1_d
                        or cx > x2_d
                        or cy < y1_d
                        or cy > y2_d
                    )

                    use_delegate = invalid_ratio or invalid_center

                if use_delegate:
                    new_box = {
                        "x1": x1_d,
                        "y1": y1_d,
                        "x2": x2_d,
                        "y2": y2_d,
                        "conf": delegate_conf,
                    }
                else:
                    new_box = {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "conf": conf,
                    }

                optimized[idx] = [new_box]

        # 对于任然存在的预测框空缺 从后取帧的预测框 作为填充. 如果后面帧都没有预测框，则从前取。
        for idx in range(frame_count):
            if optimized[idx]:
                continue

            fill_box: Dict[str, float] | None = None

            for j in range(idx + 1, frame_count):
                if optimized[j]:
                    fill_box = optimized[j][0]
                    break

            if fill_box is None:
                for j in range(idx - 1, -1, -1):
                    if optimized[j]:
                        fill_box = optimized[j][0]
                        break

            if fill_box is None:
                fill_box = {
                    "x1": 0.0,
                    "y1": 0.0,
                    "x2": 1.0,
                    "y2": 1.0,
                    "conf": 0.0,
                }

            optimized[idx] = [
                {
                    "x1": float(fill_box["x1"]),
                    "y1": float(fill_box["y1"]),
                    "x2": float(fill_box["x2"]),
                    "y2": float(fill_box["y2"]),
                    "conf": float(fill_box.get("conf", 0.0)),
                }
            ]

        for idx, frame_boxes in enumerate(optimized):
            if not frame_boxes:
                continue

            scaled_boxes: List[Dict[str, float]] = []
            for box in frame_boxes:
                x1 = float(box.get("x1", 0.0))
                y1 = float(box.get("y1", 0.0))
                x2 = float(box.get("x2", 0.0))
                y2 = float(box.get("y2", 0.0))

                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                w = (x2 - x1) * box_scale
                h = (y2 - y1) * box_scale

                side = max(w, h)
                half_side = side / 2.0

                x1_s = cx - half_side
                y1_s = cy - half_side
                x2_s = cx + half_side
                y2_s = cy + half_side

                x1_s = max(0.0, min(1.0, x1_s))
                y1_s = max(0.0, min(1.0, y1_s))
                x2_s = max(0.0, min(1.0, x2_s))
                y2_s = max(0.0, min(1.0, y2_s))

                if x2_s <= x1_s:
                    x2_s = min(1.0, x1_s + 1e-6)
                if y2_s <= y1_s:
                    y2_s = min(1.0, y1_s + 1e-6)

                scaled_box = {
                    "x1": x1_s,
                    "y1": y1_s,
                    "x2": x2_s,
                    "y2": y2_s,
                    "conf": float(box.get("conf", 0.0)),
                }
                scaled_boxes.append(scaled_box)

            optimized[idx] = scaled_boxes

        return optimized

    @staticmethod
    def crop_frames(
        frames: List[NDArray[np.uint8]],
        detect_norm_annotation: List[List[Dict[str, float]]],
        square: bool = True,
    ) -> List[List[NDArray[np.uint8]]]:
        """
        按归一化检测框裁剪视频帧，若 square 为 True 则裁剪为正方形，否则为矩形， 当裁剪超出图片边界会处理为黑色（0）。
        Args:
            frames (List[NDArray[np.uint8]]): 视频帧列表
            detect_norm_annotation (List[List[Dict[str, float]]]): 归一化检测框列表
            square (bool, optional): 是否裁剪为正方形. Defaults to True.

        Returns:
            List[List[NDArray[np.uint8]]]: 按检测框裁剪的帧片段列表
        """
        cropped_frames: List[List[NDArray[np.uint8]]] = []

        for frame, frame_annotations in zip(frames, detect_norm_annotation):
            height, width = frame.shape[:2]
            frame_crops: List[NDArray[np.uint8]] = []

            for ann in frame_annotations:
                x1_n = float(ann.get("x1", 0.0))
                y1_n = float(ann.get("y1", 0.0))
                x2_n = float(ann.get("x2", 1.0))
                y2_n = float(ann.get("y2", 1.0))

                x1_i = int(x1_n * width)
                y1_i = int(y1_n * height)
                x2_i = int(x2_n * width)
                y2_i = int(y2_n * height)

                x1_i = max(0, min(width, x1_i))
                y1_i = max(0, min(height, y1_i))
                x2_i = max(0, min(width, x2_i))
                y2_i = max(0, min(height, y2_i))

                if x2_i <= x1_i or y2_i <= y1_i:
                    continue

                if not square:
                    crop = frame[y1_i:y2_i, x1_i:x2_i]
                    frame_crops.append(crop)
                    continue

                w = x2_i - x1_i
                h = y2_i - y1_i
                side = int(max(w, h))
                if side <= 0:
                    continue
                if side % 2 != 0:
                    side += 1

                cx = (x1_i + x2_i) / 2.0
                cy = (y1_i + y2_i) / 2.0

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
                    continue

                dst_x1 = src_x1 - new_x1
                dst_y1 = src_y1 - new_y1
                dst_x2 = dst_x1 + (src_x2 - src_x1)
                dst_y2 = dst_y1 + (src_y2 - src_y1)

                if frame.ndim == 2:
                    crop: NDArray[np.uint8] = np.zeros(
                        (side, side), dtype=frame.dtype
                    )
                    crop[dst_y1:dst_y2, dst_x1:dst_x2] = frame[
                        src_y1:src_y2, src_x1:src_x2
                    ]
                else:
                    channels = frame.shape[2]
                    crop = np.zeros((side, side, channels), dtype=frame.dtype)
                    crop[dst_y1:dst_y2, dst_x1:dst_x2, :] = frame[
                        src_y1:src_y2, src_x1:src_x2, :
                    ]

                frame_crops.append(crop)

            cropped_frames.append(frame_crops)

        return cropped_frames

    def predict_images(
        self, 
        frames: List[NDArray[np.uint8]],
        frame_width: int,
        frame_height: int,
    ) -> List[List[Dict[str, float]]]:
        detect_norm_annotation: List[List[Dict[str, float]]] = []
        for frame in frames:
            results = self.model(frame, verbose=False)

            frame_annotations: List[Dict[str, float]] = []

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())

                    # x1_i, y1_i, x2_i, y2_i = int(x1), int(y1), int(x2), int(y2)
                    x1_n = x1 / frame_width
                    y1_n = y1 / frame_height
                    x2_n = x2 / frame_width
                    y2_n = y2 / frame_height

                    frame_annotations.append(
                        {
                            "x1": x1_n,
                            "y1": y1_n,
                            "x2": x2_n,
                            "y2": y2_n,
                            "conf": conf,
                        }
                    )

            detect_norm_annotation.append(frame_annotations)

            detect_norm_annotation.append(frame_annotations)

        return detect_norm_annotation
