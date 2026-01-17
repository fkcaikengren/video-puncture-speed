from typing import Callable, Optional
from pydantic import BaseModel
from video_work.detect.detect import Detect
from video_work.classify.classify import Classify
from video_work.segment.segment import Segment
from video_work.paint import (
    draw_box_on_frame, 
    overlay_crop_mask_on_frame, 
    square_crop_with_origin
)
from video_work.tools import (
    save_frames2video,
    get_device,
    frames2tensors,
    make_group_square_annotations,
    get_coord_mask,
    extract_video_frames,
    get_detect_box_sacle
)
from video_work.speed import (
    get_coord_min_rect_len,
    fix_to_monotonic_decreasing, 
    calc_speed
)


class AnalysisOutput(BaseModel):
    init_speed: float
    avg_speed: float
    instantaneous_speeds: list[float]
    instantaneous_speed_indexes: list[int]
    predict_start: int
    predict_end: int


def analyse_video(
    video_path: str, 
    temp_save_path: str,
    status_callback: Optional[Callable[[dict], None]] = None
) -> AnalysisOutput:
    
    # 初始化模型
    detector = Detect()
    classifier = Classify()
    segmenter = Segment()
    if status_callback:
        try:
            status_callback({"status": "PROCESSING"})
        except Exception:
            pass
    
    # 提取视频帧
    video = extract_video_frames(video_path)
    frames = video["frames"]
    meta = video["meta"]
    fps = int(meta["fps"])
    if fps >= 60:
        wnd_size = 150
        step = 60
    else:
        wnd_size = 90
        step = 30
    # 预测检测框
    detect_norm_annotation = detector.predict_images(frames, int(meta["width"]), int(meta["height"]))
    # 优化检测框（扩大为正方形）
    annotations_per_frame = Detect.optimize_detect_norm_annotation(
        detect_norm_annotation,
        wnd_size=wnd_size, 
        step=step,
        box_scale = get_detect_box_sacle(int(meta["width"]), int(meta["height"]))
    )
    group_size = 30
    group_square_annotations = make_group_square_annotations(
        annotations_per_frame,
        group_size=group_size,
        image_size=(int(meta["width"]), int(meta["height"])),
    )

    # 裁剪图片（用于后续分类和分割）
    crop_items: list[tuple[int, object, int, int]] = []
    crop_frames = []
    for frame_idx, (frame, frame_anns) in enumerate(zip(frames, group_square_annotations)):
        for ann in frame_anns:
            out = square_crop_with_origin(frame, ann)
            if out is None:
                continue
            crop, origin_x, origin_y = out
            crop_items.append((frame_idx, crop, origin_x, origin_y))
            crop_frames.append(crop)

    if not crop_frames:
        raise RuntimeError("no crop_frames generated")
    frame_tensors = frames2tensors(crop_frames, get_device())
    # 预测分类
    preds, probs = classifier.predict_images(frame_tensors)
    # 识别到“刺入帧”
    insert_frame_index = Classify.find_first_inserted_frame(
        class_list=preds,
        prob_list=probs,
    )
    # print(f"insert_frame_index: {insert_frame_index}")
    insert_frame_index = insert_frame_index - 4 if insert_frame_index >= 4 else 0
    # print(f"insert_frame_index 调整后: {insert_frame_index}")
    
    # 预测分割
    seg_results = segmenter.predict_images(frame_tensors, conf_thres=0.5)

    # 计算分割长度
    origin_lens: list[float] = [0.0 for _ in range(len(frames))]

    for (frame_idx, _crop, _origin_x, _origin_y), seg in zip(crop_items, seg_results):
        max_len = 0.0
        for det in seg:
            segments = det.get("segments")
            if not segments:
                continue
            max_len = max(max_len, get_coord_min_rect_len(segments))
        origin_lens[int(frame_idx)] = max(origin_lens[int(frame_idx)], max_len)

    # 优化长度（从insert_frame_index开始取帧，并做单调递减处理）
    lens, peak_idx = fix_to_monotonic_decreasing(origin_lens[insert_frame_index:])
    floor_idx = peak_idx
    predict_start = insert_frame_index 

    # 寻找floor_idx
    start_len = float(lens[0]) if lens else 0.0
    threshold_len = start_len / 2.0   # 长度剩余1/2时 作为结束点
    predict_end = predict_start + 1
    if start_len > 0:
        for i in range( 1,  + len(lens)):
            end_len = float(lens[i])
            if end_len <= threshold_len:
                floor_idx = i
                predict_end = predict_start + i
                break
    # TODO: 计算速度的窗口改为 前端可配置
    # 计算速度 
    speed_swin=60 if meta["fps"] >= 60 else 30
    speed_step=30 if meta["fps"] >= 60 else 15
    init_speed, avg_speed, instantaneous_speeds = calc_speed(
        lens,
        (0, int(floor_idx)),
        fps=meta["fps"],
        swin=speed_swin, 
        step=speed_step,
        init_speed_sample_points = 5
    )

    instantaneous_speed_indexes = [
        int(predict_start + i * speed_step + speed_swin // 2)
        for i in range(len(instantaneous_speeds))
    ]

    # 保存分析视频（包含检测框和分割掩码）
    frames_with_boxes = []
    for frame, anns in zip(frames, annotations_per_frame):
        drawn = draw_box_on_frame(frame, anns)
        frames_with_boxes.append(drawn)

    frames_with_masks = [f.copy() for f in frames_with_boxes]
    for (frame_idx, crop, origin_x, origin_y), seg in zip(crop_items, seg_results):
        for det in seg:
            segments = det.get("segments")
            if not segments:
                continue
            mask_crop = get_coord_mask(crop.shape, segments, color=(255, 255, 0))
            overlay_crop_mask_on_frame(
                frames_with_masks[frame_idx],
                mask_crop,
                origin_x=origin_x,
                origin_y=origin_y,
                alpha=0.35,
            )


    # 保存视频到临时目录
    save_frames2video(
        frames = frames_with_masks,
        output_path = temp_save_path ,
        fps = int(meta["fps"]),
        size = (int(meta["width"]), int(meta["height"])),
    )


    out = AnalysisOutput(
        init_speed=float(init_speed),
        avg_speed=float(avg_speed),
        instantaneous_speeds=[float(v) for v in instantaneous_speeds],
        instantaneous_speed_indexes=instantaneous_speed_indexes,
        predict_start=int(predict_start),
        predict_end=int(predict_end),
    )
    if status_callback:
        try:
            status_callback({"status": "COMPLETED"})
        except Exception:
            pass
    return out
    
