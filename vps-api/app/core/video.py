import os
import shutil
import ffmpeg
from typing import Dict, Any, Union
from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_target_format(probe: Dict[str, Any]) -> bool:
    video_stream = next(
        (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError("No video stream found")

    audio_stream = next(
        (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio"),
        None,
    )

    format_info = probe.get("format", {})
    format_name = str(format_info.get("format_name", ""))

    if "mp4" not in format_name:
        return False

    if video_stream.get("codec_name") != "h264":
        return False

    if video_stream.get("pix_fmt") != "yuv420p":
        return False

    if audio_stream is not None and audio_stream.get("codec_name") != "aac":
        return False

    return True


def _can_remux_to_mp4(probe: Dict[str, Any]) -> bool:
    video_stream = next(
        (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError("No video stream found")

    audio_stream = next(
        (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio"),
        None,
    )

    if video_stream.get("codec_name") != "h264":
        return False

    if video_stream.get("pix_fmt") != "yuv420p":
        return False

    if audio_stream is not None and audio_stream.get("codec_name") != "aac":
        return False

    return True

def transcode_video(input_path: str, output_path: str) -> None:
    """
    视频转码函数，将视频转换为 H.264 (视频) + AAC (音频) + MP4 (容器)。
    
    :param input_path: 输入视频文件的路径
    :param output_path: 输出视频文件的路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if os.path.abspath(input_path) == os.path.abspath(output_path) and os.path.exists(output_path):
        probe = ffmpeg.probe(input_path)
        if _is_target_format(probe):
            logger.info(f"Skip transcoding (already target format): {input_path}")
            return

    logger.info(f"Preparing video output: {input_path} -> {output_path}")
    try:
        probe = ffmpeg.probe(input_path)

        tmp_output_path = output_path
        needs_atomic_replace = os.path.abspath(input_path) == os.path.abspath(output_path)
        if needs_atomic_replace:
            base, ext = os.path.splitext(output_path)
            tmp_output_path = f"{base}.tmp{ext or '.mp4'}"

        if _is_target_format(probe):
            if os.path.abspath(input_path) != os.path.abspath(output_path):
                shutil.copy2(input_path, output_path)
            logger.info(f"Skip transcoding (already target format): {output_path}")
            return

        if _can_remux_to_mp4(probe):
            logger.info(f"Remuxing (no re-encode): {input_path} -> {tmp_output_path}")
            (
                ffmpeg.input(input_path)
                .output(
                    tmp_output_path,
                    c="copy",
                    movflags="faststart",
                    format="mp4",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            if needs_atomic_replace:
                os.replace(tmp_output_path, output_path)
            logger.info(f"Remux completed: {output_path}")
            return

        logger.info(f"Transcoding (re-encode): {input_path} -> {tmp_output_path}")
        (
            ffmpeg.input(input_path)
            .output(
                tmp_output_path,
                vcodec="libx264",
                acodec="aac",
                pix_fmt="yuv420p",
                crf=23,
                preset="medium",
                movflags="faststart",
                format="mp4",
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        if needs_atomic_replace:
            os.replace(tmp_output_path, output_path)
        logger.info(f"Transcoding completed: {output_path}")
    except ffmpeg.Error as e:
        error_message = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"Transcoding failed: {error_message}")
        raise RuntimeError(f"FFmpeg error: {error_message}") from e

def extract_first_frame(input_path: str, output_path: str) -> None:
    """
    获取视频首帧图片(png)。
    
    :param input_path: 输入视频文件的路径
    :param output_path: 输出图片文件的路径 (e.g., thumb.png)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info(f"Extracting first frame: {input_path} -> {output_path}")
    try:
        (
            ffmpeg
            .input(input_path, ss=0)
            .output(output_path, vframes=1, format='image2', vcodec='png')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logger.info(f"Frame extraction completed: {output_path}")
    except ffmpeg.Error as e:
        error_message = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"Frame extraction failed: {error_message}")
        raise RuntimeError(f"FFmpeg error: {error_message}") from e

def get_video_metadata(input_path: str) -> Dict[str, Union[str, float, int]]:
    """
    获取视频的元数据：时长，大小（字节），视频格式(mp4, mov等)，fps。
    
    :param input_path: 输入视频文件的路径
    :return: 包含元数据的字典
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info(f"Getting metadata for: {input_path}")
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        format_info = probe['format']

        if video_stream is None:
            raise ValueError("No video stream found")

        fps_str = video_stream.get('r_frame_rate', '0/0')
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            fps = num / den if den != 0 else 0.0
        else:
            fps = float(fps_str)

        duration_seconds = float(format_info.get('duration', 0) or 0)
        duration_ms = int(duration_seconds * 1000)
        fps_int = int(round(fps)) if fps > 0 else 1

        metadata = {
            "duration": duration_ms,
            "size": int(format_info.get('size', 0)),
            "fps": fps_int
        }
        logger.info(f"Metadata retrieved: {metadata}")
        return metadata

    except ffmpeg.Error as e:
        error_message = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"Probe failed: {error_message}")
        raise RuntimeError(f"FFmpeg probe error: {error_message}") from e
    except Exception as e:
        logger.error(f"Error parsing metadata: {str(e)}")
        raise e
