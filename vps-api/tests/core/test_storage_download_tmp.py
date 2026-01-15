from pathlib import Path
from io import BytesIO
import pytest
from app.core.storage import MinioStorage


class _RespStub:
    def __init__(self, data: bytes, chunk_size: int = 1024):
        self._bio = BytesIO(data)
        self._chunk_size = chunk_size
        self._closed = False

    def stream(self, chunk_size: int):
        while True:
            chunk = self._bio.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def read(self):
        return self._bio.getvalue()

    def close(self):
        self._closed = True

    def release_conn(self):
        pass


def test_download_tmp_context_manager(monkeypatch, tmp_path):
    storage = MinioStorage.__new__(MinioStorage)
    content = b"hello world"
    object_name = "folder/test.bin"

    def _fake_download(_object_name: str):
        assert _object_name == object_name
        return _RespStub(content)

    monkeypatch.setattr(storage, "download_file", _fake_download)

    with storage.download_tmp(object_name) as local_path:
        assert isinstance(local_path, Path)
        assert local_path.suffix == ".bin"
        assert local_path.exists()
        assert local_path.is_file()
        with open(local_path, "rb") as f:
            assert f.read() == content

    assert not local_path.exists()
