import os
import pytest
import ffmpeg
from app.core.video import transcode_video, extract_first_frame, get_video_metadata

# Use the specific video file provided by the user
REAL_VIDEO_PATH = "/home/tsw/workspace/keyan/videos/needle-videos/video9.mp4"
# Fallback to a local test file if the real one doesn't exist (e.g. in other envs)
TEST_VIDEO_PATH = REAL_VIDEO_PATH if os.path.exists(REAL_VIDEO_PATH) else "test_input.mp4"

TRANSCODED_VIDEO_PATH = "test_transcoded.mp4"
FRAME_PATH = "test_frame.png"

@pytest.fixture(scope="module")
def setup_video_file():
    """
    Setup the video file for testing.
    If the specific real file exists, use it.
    Otherwise, generate a dummy video file using ffmpeg.
    """
    created_dummy = False
    
    if os.path.exists(REAL_VIDEO_PATH):
        print(f"Using existing video file: {REAL_VIDEO_PATH}")
        yield REAL_VIDEO_PATH
    else:
        print(f"Real file not found, creating dummy video at: {TEST_VIDEO_PATH}")
        # Create a 1-second video with 30fps, 640x480 resolution
        try:
            (
                ffmpeg
                .input('testsrc=duration=1:size=640x480:rate=30', f='lavfi')
                .output(TEST_VIDEO_PATH, vcodec='libx264', pix_fmt='yuv420p')
                .overwrite_output()
                .run(quiet=True)
            )
            created_dummy = True
        except ffmpeg.Error as e:
            pytest.fail(f"Failed to create test video: {e.stderr.decode() if e.stderr else str(e)}")
        
        yield TEST_VIDEO_PATH
    
    # Cleanup
    # Only remove the input file if we created it
    if created_dummy and os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
        
    # Always remove output files
    for path in [TRANSCODED_VIDEO_PATH, FRAME_PATH]:
        if os.path.exists(path):
            os.remove(path)

def test_transcode_video(setup_video_file):
    print(f"Testing transcoding on: {setup_video_file}")
    transcode_video(setup_video_file, TRANSCODED_VIDEO_PATH)
    assert os.path.exists(TRANSCODED_VIDEO_PATH)
    
    # Verify the output is valid
    probe = ffmpeg.probe(TRANSCODED_VIDEO_PATH)
    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    assert video_stream is not None
    assert video_stream['codec_name'] == 'h264'
    # Check format container is mp4/mov
    assert 'mp4' in probe['format']['format_name']

def test_extract_first_frame(setup_video_file):
    print(f"Testing frame extraction on: {setup_video_file}")
    extract_first_frame(setup_video_file, FRAME_PATH)
    assert os.path.exists(FRAME_PATH)
    
    # Verify it's an image
    probe = ffmpeg.probe(FRAME_PATH)
    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    assert video_stream is not None
    assert video_stream['codec_name'] == 'png'

def test_get_video_metadata(setup_video_file):
    print(f"Testing metadata extraction on: {setup_video_file}")
    metadata = get_video_metadata(setup_video_file)
    
    print(f"Retrieved metadata: {metadata}")
    
    assert isinstance(metadata, dict)
    assert "duration" in metadata
    assert "size" in metadata
    assert "format" in metadata
    assert "fps" in metadata
    
    # Basic sanity checks instead of specific values since we are using a real file
    assert metadata["duration"] > 0
    assert metadata["size"] > 0
    # format_name usually contains 'mp4' for mp4 files
    assert 'mp4' in metadata["format"] or 'mov' in metadata["format"]

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        transcode_video("non_existent.mp4", "output.mp4")
