import cv2
from typing import Any, Dict, List
from ultralytics import YOLO


class Detect:
    _instance: "Detect | None" = None

    def __new__(cls, model_path: str) -> "Detect":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: str) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.model_path = model_path
        self.model = YOLO(model_path)
        self._initialized = True

    @staticmethod
    def draw_box(
        frame: Any,
        annotations: List[Dict[str, float]],
    ) -> Any:
        height, width = frame.shape[:2]
        scale = height / 720.0 if height > 0 else 1.0
        thickness = max(1, int(round(2 * scale)))
        font_scale = 0.6 * scale
        text_offset = int(round(10 * scale))
        for ann in annotations:
            x1_n = ann["x1"]
            y1_n = ann["y1"]
            x2_n = ann["x2"]
            y2_n = ann["y2"]
            conf = ann.get("conf", 0.0)

            x1 = int(x1_n * width)
            y1 = int(y1_n * height)
            x2 = int(x2_n * width)
            y2 = int(y2_n * height)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                thickness,
            )

            text = f"{conf*100:.1f}%"
            cv2.putText(
                frame,
                text,
                (x1, y1 - text_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (0, 255, 0),
                thickness,
            )

        return frame

    @staticmethod
    def optimize_detect_norm_annotation(
        detect_norm_annotation: List[List[Dict[str, float]]],
        wnd_size: int = 60,
        step: int = 30,
        conf_threshhold = 0.5,
        box_scale = 2
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

    def predict_video(self, video_path: str) -> Dict[str, Any]:
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

        frames: List[Any] = []
        detect_norm_annotation: List[List[Dict[str, float]]] = []
        crop_frames: List[List[Any]] = []

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frames.append(frame.copy())

                results = self.model(frame)

                frame_annotations: List[Dict[str, float]] = []
                frame_crops: List[Any] = []

                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())

                        x1_i, y1_i, x2_i, y2_i = int(x1), int(y1), int(x2), int(y2)
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

                        crop = frame[y1_i:y2_i, x1_i:x2_i]
                        frame_crops.append(crop)

                detect_norm_annotation.append(frame_annotations)
                crop_frames.append(frame_crops)
        finally:
            cap.release()
            cv2.destroyAllWindows()

        meta: Dict[str, Any] = {
            "width": frame_width,
            "height": frame_height,
            "fps": fps,
            "codec": fourcc,
            "frame_count": len(frames),
        }

        return {
            "frames": frames,
            "detect_norm_annotation": detect_norm_annotation,
            "crop_frames": crop_frames,
            "meta": meta,
        }
