from pathlib import Path

import torch

from video_work.segment.segment import Segment


def test_segment_predict_images_smoke():
    project_root = Path(__file__).resolve().parents[2]
    model_path = project_root / "video_work" / "segment" / "menet.pth"
    segmenter = Segment(model_path=str(model_path))

    imgs = [torch.rand(3, 240, 320)]
    results = segmenter.predict_images(imgs)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], list)
    for det in results[0]:
        assert set(det.keys()) == {"cls", "conf", "segments"}
        assert isinstance(det["cls"], int)
        assert isinstance(det["conf"], float)
        assert isinstance(det["segments"], list)
