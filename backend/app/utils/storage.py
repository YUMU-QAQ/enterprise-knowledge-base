"""MinIO file storage utilities"""

from io import BytesIO

from minio import Minio

from app.core.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # Ensure bucket exists
        if not _client.bucket_exists(settings.MINIO_BUCKET):
            _client.make_bucket(settings.MINIO_BUCKET)
    return _client


async def upload_file(
    file_name: str,
    file_data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload file to MinIO, return object path"""
    client = get_minio_client()
    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=file_name,
        data=BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return file_name


async def download_file(file_name: str) -> bytes:
    """Download file from MinIO"""
    client = get_minio_client()
    response = client.get_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=file_name,
    )
    return response.read()
