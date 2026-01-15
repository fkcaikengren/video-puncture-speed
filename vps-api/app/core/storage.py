
from minio import Minio
from datetime import timedelta
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Generator
from .config import settings
from .tempfile_manager import TempfileManager


"""
Docs:

API quick start
https://docs.min.io/enterprise/aistor-object-store/developers/sdk/python/

API Reference
https://docs.min.io/enterprise/aistor-object-store/developers/sdk/python/api/

Github
https://github.com/minio/minio-py
"""

class MinioStorage:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._make_bucket()

    def _make_bucket(self):
        """确保 Bucket 存在"""
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def upload_bytes(self, file_data: BytesIO, object_name: str, content_type: str):
        """上传文件流"""
        file_size = file_data.getbuffer().nbytes
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=file_data,
            length=file_size,
            content_type=content_type
        )
        return object_name

    def upload_file(self, file_path: str | Path, object_name: str, content_type: str):
        """上传本地文件"""
        path = Path(file_path)
        self.client.fput_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            file_path=str(path),
            content_type=content_type,
        )
        return object_name

    def get_url(self, object_name: str, expires_hours: int = 24):
        """生成预签名下载链接（临时访问权限）"""
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(hours=expires_hours)
        )

    def delete_file(self, object_name: str):
        """删除文件"""
        self.client.remove_object(self.bucket_name, object_name)

    def download_file(self, object_name: str):
        """获取文件对象流"""
        return self.client.get_object(self.bucket_name, object_name)

    @contextmanager
    def download_tmp(
        self,
        object_name: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Generator[Path, None, None]:
        object_path = Path(object_name)
        suffix = object_path.suffix or '.mp4'
        prefix = f"minio_{object_path.stem}_" if object_path.stem else "minio_"

        with TempfileManager.create_temp_file(
            suffix=suffix,
            prefix=prefix,
            delete=True,
        ) as temp_path_str:
            local_path = Path(temp_path_str)

            response = self.download_file(object_name)
            try:
                with open(local_path, "wb") as f:
                    for chunk in response.stream(chunk_size):
                        f.write(chunk)
            finally:
                try:
                    response.close()
                    response.release_conn()
                except Exception:
                    pass

            yield local_path

    
# 实例化
storage = MinioStorage()
