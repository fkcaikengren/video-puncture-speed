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
        font_scale = 0.8 * scale
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
    ) -> List[List[Dict[str, float]]]:
        pass

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
