import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.modules.knowledge.files import KnowledgeFileError, sanitize_filename


@dataclass
class StoredObject:
    content_length: int
    content_type: str
    path: Path | None = None
    stream: Iterator[bytes] | None = None


def store_knowledge_file(
    tenant_id: UUID,
    filename: str,
    data: bytes,
    content_type: str,
) -> tuple[str, str]:
    backend = _backend()
    key = (Path(str(tenant_id)) / str(uuid4()) / sanitize_filename(filename)).as_posix()
    if backend == "local":
        target = resolve_local_storage_key(key)
        target.parent.mkdir(parents=True, exist_ok=False)
        target.write_bytes(data)
        return backend, key

    client = _s3_client()
    _ensure_bucket(client)
    arguments = {
        "Bucket": settings.s3_bucket,
        "Key": key,
        "Body": data,
        "ContentLength": len(data),
        "ContentType": content_type,
        "ContentMD5": base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode(),
    }
    if settings.s3_server_side_encryption:
        arguments["ServerSideEncryption"] = settings.s3_server_side_encryption
    client.put_object(**arguments)
    return backend, key


def delete_knowledge_file(storage_backend: str, storage_key: str) -> None:
    if storage_backend == "local":
        path = resolve_local_storage_key(storage_key)
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass
        return
    if storage_backend != "s3":
        raise KnowledgeFileError(f"Unsupported storage backend: {storage_backend}")
    _s3_client().delete_object(Bucket=settings.s3_bucket, Key=storage_key)


def open_knowledge_file(storage_backend: str, storage_key: str) -> StoredObject:
    if storage_backend == "local":
        path = resolve_local_storage_key(storage_key)
        if not path.is_file():
            raise KnowledgeFileError("Stored file not found")
        return StoredObject(
            path=path,
            content_length=path.stat().st_size,
            content_type="application/octet-stream",
        )
    if storage_backend != "s3":
        raise KnowledgeFileError(f"Unsupported storage backend: {storage_backend}")
    try:
        response = _s3_client().get_object(Bucket=settings.s3_bucket, Key=storage_key)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        if code in {"NoSuchKey", "NoSuchBucket", "404"}:
            raise KnowledgeFileError("Stored file not found") from error
        raise
    body = response["Body"]

    def stream() -> Iterator[bytes]:
        try:
            yield from body.iter_chunks(chunk_size=64 * 1024)
        finally:
            body.close()

    return StoredObject(
        stream=stream(),
        content_length=int(response.get("ContentLength") or 0),
        content_type=str(response.get("ContentType") or "application/octet-stream"),
    )


def knowledge_file_exists(storage_backend: str, storage_key: str) -> bool:
    if storage_backend == "local":
        return resolve_local_storage_key(storage_key).is_file()
    if storage_backend != "s3":
        return False
    try:
        _s3_client().head_object(Bucket=settings.s3_bucket, Key=storage_key)
        return True
    except ClientError as error:
        if error.response.get("Error", {}).get("Code", "") in {"NoSuchKey", "404"}:
            return False
        raise


def resolve_local_storage_key(storage_key: str) -> Path:
    root = Path(settings.knowledge_upload_dir).expanduser().resolve()
    candidate = (root / storage_key).resolve()
    if not candidate.is_relative_to(root):
        raise KnowledgeFileError("Invalid knowledge file storage path")
    return candidate


def _backend() -> str:
    backend = settings.knowledge_storage_backend.lower().strip()
    if backend not in {"local", "s3"}:
        raise KnowledgeFileError(f"Unsupported storage backend: {backend}")
    return backend


def _s3_client() -> BaseClient:
    if not settings.s3_access_key or not settings.s3_secret_key:
        raise KnowledgeFileError("S3 access key and secret key are required")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _ensure_bucket(client: BaseClient) -> None:
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
        return
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        if code not in {"404", "NoSuchBucket"}:
            raise
    arguments = {"Bucket": settings.s3_bucket}
    if settings.s3_region != "us-east-1" and not settings.s3_endpoint_url:
        arguments["CreateBucketConfiguration"] = {"LocationConstraint": settings.s3_region}
    client.create_bucket(**arguments)
