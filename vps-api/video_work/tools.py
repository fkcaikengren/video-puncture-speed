
import os
import tempfile
import shutil
import ffmpeg
import cv2
from typing import Any, List, Tuple


def save_frames2video(
    frames: List[Any],
    output_path: str,
    fps: int,
    size: Tuple[int, int],
) -> None:
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
