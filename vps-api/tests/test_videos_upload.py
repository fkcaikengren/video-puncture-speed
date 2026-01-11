from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_upload_video_success():
    # Mock dependencies
    with patch("app.api.videos.service.transcode_video") as mock_transcode, \
         patch("app.api.videos.service.storage") as mock_storage, \
         patch("app.api.videos.service.TempfileManager.create_temp_file") as mock_temp_file:

        # Setup mocks
        # create_temp_file is a context manager, so we need to mock __enter__
        mock_temp_path = "/tmp/mock_file"
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_temp_path
        mock_temp_file.return_value = mock_ctx
        
        mock_storage.upload_file.return_value = "videos/mock_object.mp4"

        # Create a dummy file for upload
        file_content = b"fake video content"
        files = {"file": ("test_video.mov", file_content, "video/quicktime")}

        response = client.post("/video/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["original_filename"] == "test_video.mov"
        assert "filename" in data
        assert data["message"] == "Video uploaded and processed successfully"

        # Verify calls
        # 1. Check if transcode was called
        mock_transcode.assert_called_once()
        args, _ = mock_transcode.call_args
        assert args[0] == mock_temp_path  # input path
        assert args[1] == mock_temp_path  # output path (since we mocked create_temp_file to return same path)

        # 2. Check if upload was called
        mock_storage.upload_file.assert_called_once()
        args, kwargs = mock_storage.upload_file.call_args
        assert kwargs["file_path"] == mock_temp_path
        assert kwargs["content_type"] == "video/mp4"
        assert kwargs["object_name"].startswith("videos/")
        assert kwargs["object_name"].endswith(".mp4")

def test_upload_video_transcode_fail():
    with patch("app.api.videos.service.transcode_video") as mock_transcode, \
         patch("app.api.videos.service.TempfileManager.create_temp_file") as mock_temp_file:

        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = "/tmp/fail_file"
        mock_temp_file.return_value = mock_ctx
        
        mock_transcode.side_effect = RuntimeError("Transcode error")

        files = {"file": ("fail.mov", b"content", "video/quicktime")}
        response = client.post("/video/upload", files=files)
        
        assert response.status_code == 500
        assert "Transcoding failed" in response.json()["detail"]
