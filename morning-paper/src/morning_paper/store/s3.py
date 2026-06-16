"""S3-compatible object store. boto3 imported lazily."""

from __future__ import annotations


class S3ObjectStore:
    """Store blobs in an S3 bucket under an optional key prefix.

    Endpoint/region/credentials come from the environment (AWS_*), which boto3
    resolves automatically.
    """

    def __init__(self, url: str) -> None:
        import boto3  # lazy

        self.bucket, self.prefix = _parse_s3_url(url)
        self._client = boto3.client("s3")

    def _full_key(self, key: str) -> str:
        if self.prefix:
            return f"{self.prefix.rstrip('/')}/{key}"
        return key

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        kw = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self.bucket, Key=self._full_key(key), Body=data, **kw)
        return self.url(key)

    def put_file(self, key: str, path: str, *, content_type: str | None = None) -> str:
        extra = {"ContentType": content_type} if content_type else None
        self._client.upload_file(path, self.bucket, self._full_key(key), ExtraArgs=extra)
        return self.url(key)

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self.bucket, Key=self._full_key(key))
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except ClientError:
            return False

    def url(self, key: str) -> str:
        return f"s3://{self.bucket}/{self._full_key(key)}"

    def open_path(self, key: str) -> str | None:
        return None  # remote


def _parse_s3_url(url: str) -> tuple[str, str]:
    """s3://bucket/prefix -> (bucket, prefix)."""
    rest = url[len("s3://"):] if url.startswith("s3://") else url
    bucket, _, prefix = rest.partition("/")
    return bucket, prefix
