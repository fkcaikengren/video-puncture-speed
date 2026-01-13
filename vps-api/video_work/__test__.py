from pathlib import Path
from video_work.detect.detect import Detect
from video_work.classify.classify import Classify
from video_work.segment.segment import Segment
from video_work.paint import overlay_crop_mask_on_frame, square_crop_with_origin, save_speeds_graph
from video_work.tools import (
    save_frames2video,
    frames2tensors,
    make_group_square_annotations,
    get_coord_mask,
)
from video_work.speed import get_coord_min_rect_len,fix_to_monotonic_decreasing, calc_speed

# 不导出任何变量和函数
__all__ = []


project_root = Path(__file__).resolve().parents[1]
video_path_dir = Path('/home/tsw/workspace/keyan/videos/needle-videos/').resolve()
video_path = video_path_dir / 'video16.mp4'
output_dir = project_root / "video_work" / "test_output"

def test_detect() -> None:

    detector = Detect()
    result = detector.predict_video(str(video_path))

    frames = result.frames
    fps = int(result.meta.fps)
    print(f"fps: {fps}")
    if fps >= 60:
        wnd_size = 150
        step = 60
    else:
        wnd_size = 90
        step = 30

    annotations_per_frame = Detect.optimize_detect_norm_annotation(
        result.detect_norm_annotation, wnd_size=wnd_size, step=step
    )
    frames_with_boxes = []
    for frame, anns in zip(frames, annotations_per_frame):
        drawn = Detect.draw_box(frame, anns)
        frames_with_boxes.append(drawn)

    save_frames2video(
        frames=frames_with_boxes,
        output_path=str(output_dir / f"{video_path.stem}_detected.mp4"),
        fps=int(result.meta.fps),
        size=(int(result.meta.width), int(result.meta.height)),
    )

def test_classify() -> None:
    
    detector = Detect()
    classifier = Classify()
    result = detector.predict_video(str(video_path))
    annotations_per_frame = Detect.optimize_detect_norm_annotation(
        result.detect_norm_annotation
    )
    nested_crop_frames = Detect.crop_frames(result.frames, annotations_per_frame)
    crop_frames = [
        crop for frame_crops in nested_crop_frames for crop in frame_crops
    ]

    frame_tensors = frames2tensors(crop_frames, classifier.device)
    preds, probs = classifier.predict_images(frame_tensors)

    insert_frame_index = Classify.find_first_inserted_frame(
        class_list=preds, 
        prob_list=probs
    )
    for pred, prob, frame in zip(preds, probs, crop_frames):
        print((pred, prob, frame.shape))
    print(f"insert_frame_index: {insert_frame_index}") 

def test_segment() -> None:
    
    detector = Detect()
    segmenter = Segment()
    
    result = detector.predict_video(str(video_path))
    # 扩大2倍，正方形 预测框
    annotations_per_frame = Detect.optimize_detect_norm_annotation(
        result.detect_norm_annotation
    )
    group_size = 30
    same_size_annotations = make_group_square_annotations(
        annotations_per_frame,
        group_size=group_size,
        image_size=(int(result.meta.width), int(result.meta.height)),
    )

    max_frames = min(400, len(result.frames)) # 指最大处理400帧
    frames = result.frames[:max_frames]
    anns = same_size_annotations[:max_frames]

    crop_items: list[tuple[int, object, int, int]] = []
    crop_frames = []
    for frame_idx, (frame, frame_anns) in enumerate(zip(frames, anns)):
        for ann in frame_anns:
            out = square_crop_with_origin(frame, ann)
            if out is None:
                continue
            crop, origin_x, origin_y = out
            crop_items.append((frame_idx, crop, origin_x, origin_y))
            crop_frames.append(crop)

    if not crop_frames:
        raise RuntimeError("no crop_frames generated")

    test_crop_frames = crop_frames[100:130]
    for i, crop in enumerate(test_crop_frames):
        print(f"crop_frame {100+i} size: {crop.shape}")
    print("...")

    frame_tensors = frames2tensors(crop_frames, segmenter.device)
    seg_results = segmenter.predict_images(frame_tensors)

    print(
        f"frame_tensors.length:seg_results.length => {len(seg_results)} : {len(frame_tensors)}"
    )

    frames_with_masks = [f.copy() for f in frames]
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

    save_frames2video(
        frames=frames_with_masks,
        output_path=str(output_dir / f"{video_path.stem}_segmented.mp4"),
        fps=int(result.meta.fps),
        size=(int(result.meta.width), int(result.meta.height)),
    )
    
def test_speed() -> None:
    detector = Detect()
    classifier = Classify()
    segmenter = Segment()
    
    result = detector.predict_video(str(video_path))
    frames = result.frames
    # 扩大2倍，正方形 预测框
    annotations_per_frame = Detect.optimize_detect_norm_annotation(
        result.detect_norm_annotation
    )

    group_size = 30
    group_square_annotations = make_group_square_annotations(
        annotations_per_frame,
        group_size=group_size,
        image_size=(int(result.meta.width), int(result.meta.height)),
    )

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

    cls_tensors = frames2tensors(crop_frames, classifier.device)
    preds, probs = classifier.predict_images(cls_tensors)
    insert_frame_index = Classify.find_first_inserted_frame(
        class_list=preds,
        prob_list=probs,
    )
    print(f"insert_frame_index: {insert_frame_index}")
    insert_frame_index = insert_frame_index - 4 if insert_frame_index >= 4 else 0
    print(f"insert_frame_index 调整后: {insert_frame_index}")
    
    seg_tensors = frames2tensors(crop_frames, segmenter.device)
    seg_results = segmenter.predict_images(seg_tensors, conf_thres=0.5)

    origin_lens: list[float] = [0.0 for _ in range(len(frames))]
    for (frame_idx, _crop, _origin_x, _origin_y), seg in zip(crop_items, seg_results):
        max_len = 0.0
        for det in seg:
            segments = det.get("segments")
            if not segments:
                continue
            max_len = max(max_len, get_coord_min_rect_len(segments))
        origin_lens[int(frame_idx)] = max(origin_lens[int(frame_idx)], max_len)

    # 从insert_frame_index取帧，并做单调递减处理
    lens, peak_idx = fix_to_monotonic_decreasing(origin_lens[insert_frame_index:])
    floor_idx = peak_idx
    predict_start = insert_frame_index 
    # 寻找predict_end

    start_len = float(lens[0]) if lens else 0.0
    threshold_len = start_len / 4.0

    predict_end = predict_start + 1
    if start_len > 0:
        for i in range( 1,  + len(lens)):
            end_len = float(lens[i])
            if end_len <= threshold_len:
                floor_idx = i
                predict_end = predict_start + i
                break

    speed_swin=8
    speed_step=2
    init_speed, avg_speed, instantaneous_speeds = calc_speed(
        lens,
        (0, int(floor_idx)),
        fps=result.meta.fps,
        swin=speed_swin, 
        step=speed_step,
        init_speed_sample_points = 10
    )
    print(f"start_speed: {init_speed:.2f} mm/s")
    print(f"avg_speed: {avg_speed:.2f} mm/s")
    print(f"instantaneous_speeds: {instantaneous_speeds[:10]}")


    speed_frame_indexes = [
        int(predict_start + i * speed_step + speed_swin // 2)
        for i in range(len(instantaneous_speeds))
    ]
    save_speeds_graph(
        instantaneous_speeds,
        speed_frame_indexes,
        graph_output_path=str(output_dir / f"{video_path.stem}_speeds.png"),
        title=str( f"{video_path.stem}_speeds.png"),
    )
    print(f"speeds graph saved to {output_dir / f'{video_path.stem}_speeds.png'}")
    

if __name__ == "__main__":
    
    # test_detect()
    # test_classify()
    # test_segment()

    test_speed()
