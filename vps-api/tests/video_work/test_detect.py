from pathlib import Path
from video_work.detect.detect import predict_video, save_frames2video


def test_predict_video_and_save_frames2video(tmp_path):
    tests_dir = Path(__file__).resolve().parents[1]
    project_root = Path(__file__).resolve().parents[2]

    model_path = project_root / "video_work" / "detect" / "yolo.pt"
    video_path = tests_dir / "data" / "video1.mp4"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = predict_video(str(model_path), str(video_path))

    frames = result["frames"]
    meta = result["meta"]
    output_video_path = output_dir / f"{video_path.stem}_detected.mp4"

    save_frames2video(
        frames=frames,
        output_path=str(output_video_path),
        fps=int(meta["fps"]),
        size=(int(meta["width"]), int(meta["height"])),
    )

    assert output_video_path.exists()
    assert output_video_path.is_file()
    assert output_video_path.stat().st_size > 0
