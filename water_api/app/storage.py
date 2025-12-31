import os

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from mypy_boto3_s3.client import S3Client

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "water-games")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


def get_s3_client() -> S3Client:
    """Get configured S3 client for MinIO"""
    return boto3.client(  # type: ignore[return-value]
        "s3",
        endpoint_url=f"http{'s' if MINIO_SECURE else ''}://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",  # MinIO doesn't care, but boto3 needs it
    )


def ensure_bucket_exists() -> None:
    """Create bucket if it doesn't exist"""
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=MINIO_BUCKET)
        else:
            raise


def upload_game_build(file_path: str, game_slug: str, version: str) -> str:
    """Upload game build to MinIO from file path and return object key"""
    s3 = get_s3_client()
    ensure_bucket_exists()

    object_key = f"games/{game_slug}/{version}/game.zip"

    with open(file_path, "rb") as f:
        s3.upload_fileobj(f, MINIO_BUCKET, object_key)

    return object_key


def upload_build_fileobj(file_obj, game_slug: str, version: str) -> str:
    """Upload game build to MinIO from file-like object and return object key"""
    s3 = get_s3_client()
    ensure_bucket_exists()

    object_key = f"games/{game_slug}/{version}/game.zip"
    s3.upload_fileobj(file_obj, MINIO_BUCKET, object_key)

    return object_key


def get_download_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate presigned download URL"""
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": MINIO_BUCKET, "Key": object_key},
        ExpiresIn=expires_in,
    )


def download_game_build(object_key: str, destination: str) -> None:
    """Download game build from MinIO"""
    s3 = get_s3_client()
    s3.download_file(MINIO_BUCKET, object_key, destination)
