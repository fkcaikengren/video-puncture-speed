from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from video_work.tools import get_device
from video_work.models.menet_seg import MENetSeg


DEFAULT_MODEL_PATH = str(Path(__file__).resolve().parent / "menet.pth")


class Segment:
    _instance: "Segment | None" = None

    def __new__(cls, model_path: str = DEFAULT_MODEL_PATH) -> "Segment":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.device = get_device()
        self.model = MENetSeg(num_classes=2)
        self._load_weights(self.model, self.model_path, self.device)
        self.model.to(self.device)
        self.model.eval()

        self.input_size = (384, 384)
        self._norm_mean = torch.tensor([0.485, 0.456, 0.406], dtype=torch.float32).view(1, 3, 1, 1)
        self._norm_std = torch.tensor([0.229, 0.224, 0.225], dtype=torch.float32).view(1, 3, 1, 1)
        self.transform = transforms.Compose([transforms.Resize(self.input_size)])
        self._initialized = True

    @staticmethod
    def _load_weights(model: torch.nn.Module, weight_path: str, device: torch.device) -> None:
        checkpoint = torch.load(weight_path, map_location=device)
        if isinstance(checkpoint, dict):
            for key in ("state_dict", "model_state_dict", "model"):
                if key in checkpoint and isinstance(checkpoint[key], dict):
                    checkpoint = checkpoint[key]
                    break

        if not isinstance(checkpoint, dict):
            raise ValueError("Unsupported checkpoint format, expected a state_dict dict")

        state_dict: dict[str, torch.Tensor] = {}
        for k, v in checkpoint.items():
            if not isinstance(k, str):
                continue
            if k.startswith("module."):
                k = k[len("module.") :]
            state_dict[k] = v

        incompatible = model.load_state_dict(state_dict, strict=False)
        missing = getattr(incompatible, "missing_keys", None)
        unexpected = getattr(incompatible, "unexpected_keys", None)
        if missing is None or unexpected is None:
            missing, unexpected = incompatible

        if missing or unexpected:
            raise RuntimeError(
                f"Failed to load segmentation weights. missing={len(missing)}, unexpected={len(unexpected)}"
            )

    def predict_images(
        self,
        frame_tensors,
        mode: str = "slide",
        crop_size: int = 384,
        stride: tuple[int, int] = (224, 224),
        conf_thres: float = 0.5,
        min_area: int = 32,
        epsilon_ratio: float = 0.002,
    ) -> list[list[dict]]:
        """对多张图做分割推理并输出多边形结果。

        - 输入：frame_tensors 为 CHW、RGB、float(0~1) 的 torch.Tensor 列表
        - 模式：当前仅支持 mode='slide'，使用滑窗裁剪后批量推理并融合概率图
        - 参数：crop_size 默认为 384（32 的倍数且 >=224），stride 默认为 (224,224)
        - 输出：每张图对应一个 list[dict]，dict 结构为 {cls, conf, segments}
          - cls 固定为 1
          - conf 为该实例区域内概率均值（回退到 max）
          - segments 为像素坐标多边形点序列展开 [x1,y1,x2,y2,...]
        """
        if frame_tensors is None:
            raise ValueError("frame_tensors is None")
        if mode not in {"slide"}:
            raise ValueError(f"unsupported mode: {mode}")
        crop_h = int(crop_size)
        crop_w = int(crop_size)
        if crop_h <= 0 or crop_w <= 0:
            raise ValueError("crop_size must be positive")
        if crop_h % 32 != 0:
            raise ValueError("crop_size must be a multiple of 32")
        if crop_h < 224:
            raise ValueError("crop_size must be >= 224")
        stride_h, stride_w = int(stride[0]), int(stride[1])
        if stride_h <= 0 or stride_w <= 0:
            raise ValueError("stride must be positive")
        if stride_h > crop_h or stride_w > crop_w:
            raise ValueError("stride must be <= crop_size")

        if not frame_tensors:
            return []

        all_results: list[list[dict]] = []
        in_h, in_w = int(self.input_size[0]), int(self.input_size[1])

        weight_y = torch.hann_window(crop_h, periodic=False, dtype=torch.float32)
        weight_x = torch.hann_window(crop_w, periodic=False, dtype=torch.float32)
        weight_map = torch.outer(weight_y, weight_x).clamp_min(1e-3).cpu().numpy().astype(np.float32)

        def starts(full: int, crop: int, step: int) -> list[int]:
            if full <= crop:
                return [0]
            out = list(range(0, full - crop + 1, step))
            last = full - crop
            if out[-1] != last:
                out.append(last)
            return out

        for tensor in frame_tensors:
            if tensor is None:
                raise ValueError("tensor in frame_tensors is None")
            if tensor.ndim != 3 or tensor.shape[0] != 3:
                raise ValueError("each tensor must be CHW with 3 channels")

            orig_h = int(tensor.shape[1])
            orig_w = int(tensor.shape[2])
            if orig_h <= 0 or orig_w <= 0:
                all_results.append([])
                continue

            work_tensor = tensor.to(self.device, non_blocking=True).float()

            pad_h = max(0, crop_h - orig_h)
            pad_w = max(0, crop_w - orig_w)
            if pad_h or pad_w:
                work_tensor = F.pad(work_tensor.unsqueeze(0), (0, pad_w, 0, pad_h), mode="replicate").squeeze(0)

            work_h = int(work_tensor.shape[1])
            work_w = int(work_tensor.shape[2])
            y_starts = starts(work_h, crop_h, stride_h)
            x_starts = starts(work_w, crop_w, stride_w)

            crops: list[torch.Tensor] = []
            positions: list[tuple[int, int]] = []
            for y0 in y_starts:
                for x0 in x_starts:
                    crop = work_tensor[:, y0 : y0 + crop_h, x0 : x0 + crop_w]
                    crops.append(crop)
                    positions.append((y0, x0))

            if not crops:
                all_results.append([])
                continue

            batch_tensor = torch.stack(crops, dim=0)
            mean = self._norm_mean.to(batch_tensor.device, dtype=batch_tensor.dtype)
            std = self._norm_std.to(batch_tensor.device, dtype=batch_tensor.dtype)
            batch_tensor = (batch_tensor - mean) / std

            if (crop_h, crop_w) != (in_h, in_w):
                batch_tensor = F.interpolate(batch_tensor, size=(in_h, in_w), mode="bilinear", align_corners=False)

            with torch.no_grad():
                logits = self.model(batch_tensor)
                probs = torch.softmax(logits, dim=1)[:, 1]

            if probs.shape[-2:] != (crop_h, crop_w):
                probs = F.interpolate(probs.unsqueeze(1), size=(crop_h, crop_w), mode="bilinear", align_corners=False).squeeze(1)

            probs_np = probs.detach().float().cpu().numpy().astype(np.float32)
            prob_sum = np.zeros((work_h, work_w), dtype=np.float32)
            w_sum = np.zeros((work_h, work_w), dtype=np.float32)
            for idx, (y0, x0) in enumerate(positions):
                patch = probs_np[idx]
                prob_sum[y0 : y0 + crop_h, x0 : x0 + crop_w] += patch * weight_map
                w_sum[y0 : y0 + crop_h, x0 : x0 + crop_w] += weight_map

            w_sum = np.maximum(w_sum, 1e-6)
            prob_map = (prob_sum / w_sum)[:orig_h, :orig_w]

            bin_mask = (prob_map >= conf_thres).astype(np.uint8) * 255
            contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            image_results: list[dict] = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < float(min_area):
                    continue
                peri = cv2.arcLength(contour, True)
                epsilon = max(1.0, float(peri) * float(epsilon_ratio))
                approx = cv2.approxPolyDP(contour, epsilon, True)
                pts = approx.reshape(-1, 2)
                if pts.shape[0] < 3:
                    continue

                fill = np.zeros((orig_h, orig_w), dtype=np.uint8)
                cv2.drawContours(fill, [approx], -1, 1, thickness=-1)
                region = prob_map[fill.astype(bool)]
                conf = float(region.mean()) if region.size else float(prob_map.max())

                xs = np.clip(np.round(pts[:, 0]), 0, orig_w - 1).astype(np.int32)
                ys = np.clip(np.round(pts[:, 1]), 0, orig_h - 1).astype(np.int32)
                segment: list[int] = []
                for x, y in zip(xs.tolist(), ys.tolist()):
                    segment.extend([int(x), int(y)])

                image_results.append({"cls": 1, "conf": conf, "segments": segment})

            image_results.sort(key=lambda d: d["conf"], reverse=True)
            all_results.append(image_results)

        return all_results
