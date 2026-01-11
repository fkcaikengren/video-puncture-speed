import pytest
import uuid
from io import BytesIO
from unittest.mock import patch
from app.core.storage import MinioStorage
from app.core.config import settings

@pytest.fixture(scope="module")
def storage_service():
    """
    Fixture to provide a real MinioStorage instance.
    This will use the real settings and connection.
    """
    storage = MinioStorage()
    return storage

@pytest.fixture
def unique_filename():
    """Generate a unique filename for each test to avoid collisions."""
    return f"test_file_{uuid.uuid4()}.txt"

def test_storage_integration(storage_service, unique_filename):
    """
    Integration test for the full lifecycle:
    Upload -> Get URL -> Download -> Delete
    """
    # Prepare data
    content = b"Hello, MinIO Integration Test!"
    file_data = BytesIO(content)
    content_type = "text/plain"
    
    # 1. Test Upload
    uploaded_object_name = storage_service.upload_file(file_data, unique_filename, content_type)
    assert uploaded_object_name == unique_filename
    
    # Verify file exists in Minio (using the client directly for verification)
    # Note: stat_object raises exception if object does not exist
    stat = storage_service.client.stat_object(settings.MINIO_BUCKET_NAME, unique_filename)
    assert stat.size == len(content)

    # 2. Test Get URL
    url = storage_service.get_url(unique_filename)
    assert isinstance(url, str)
    assert settings.MINIO_ENDPOINT in url or "localhost" in url or "127.0.0.1" in url
    assert unique_filename in url

    # 3. Test Download
    response = storage_service.download_file(unique_filename)
    try:
        downloaded_content = response.read()
        assert downloaded_content == content
    finally:
        response.close()
        
    # 4. Test Delete
    storage_service.delete_file(unique_filename)
    
    # Verify file is gone
    with pytest.raises(Exception): # Minio raises generic S3Error or similar
        storage_service.client.stat_object(settings.MINIO_BUCKET_NAME, unique_filename)

def test_init_creates_bucket(storage_service):
    """Verify that the bucket is actually created upon initialization."""
    # This is implicitly tested by the fixture setup, but we can double check
    assert storage_service.client.bucket_exists(settings.MINIO_BUCKET_NAME) is True

# def test_init_creates_new_bucket():
#     """Test that a new bucket is created if it doesn't exist."""
#     new_bucket_name = f"test-bucket-{uuid.uuid4()}"
    
#     # Patch the settings used in app.core.storage
#     with patch("app.core.storage.settings.MINIO_BUCKET_NAME", new_bucket_name):
#         storage = MinioStorage()
        
#         try:
#             # Verify bucket was created
#             assert storage.client.bucket_exists(new_bucket_name) is True
#         finally:
#             # Cleanup: delete the bucket
#             try:
#                 storage.client.remove_bucket(new_bucket_name)
#             except Exception:
#                 pass
