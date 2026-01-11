from pathlib import Path
from detect.detect import Detect
from tools import save_frames2video


if __name__ == "__main__":
    def test_detect() -> None:
        project_root = Path(__file__).resolve().parents[1]
        model_path = project_root / "video_work" / "detect" / "yolo.pt"
        video_path = project_root / "tests" / "data" / "video1.mp4"
        output_dir = project_root / "tests" / "data"

        detector = Detect(str(model_path))
        result = detector.predict_video(str(video_path))

        frames = result["frames"]
        fps = int(result["meta"]["fps"])
        print(f'fps: {fps}')
        if fps >= 60:
            wnd_size = 150
            step = 60
        else:
            wnd_size = 90
            step = 30

        annotations_per_frame = Detect.optimize_detect_norm_annotation(
            result["detect_norm_annotation"], wnd_size=wnd_size, step=step
        )
        frames_with_boxes = []
        for frame, anns in zip(frames, annotations_per_frame):
            drawn = Detect.draw_box(frame, anns)
            frames_with_boxes.append(drawn)

        save_frames2video(
            frames=frames_with_boxes,
            output_path=str(output_dir / f"{video_path.stem}_detected.mp4"),
            fps=int(result["meta"]["fps"]),
            size=(int(result["meta"]["width"]), int(result["meta"]["height"])),
        )

    test_detect()
