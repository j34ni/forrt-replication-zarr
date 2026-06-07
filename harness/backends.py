"""
Store factory for Icechunk repositories.

Supported backends: local filesystem, MinIO (S3-compatible).

MinIO configuration via environment variables:
  MINIO_ENDPOINT    e.g. https://s3.nird.sigma2.no
  MINIO_BUCKET      your private bucket name (no default — must be set)
  MINIO_PREFIX      e.g. icechunk-atomicity-test   (dedicated test prefix — never touches other data)
  MINIO_ACCESS_KEY  your access key
  MINIO_SECRET_KEY  your secret key
"""
import os

import icechunk


def local_icechunk_repo(store_dir: str) -> icechunk.Repository:
    """Create a fresh local-filesystem-backed Icechunk repository."""
    storage = icechunk.local_filesystem_storage(str(store_dir))
    try:
        return icechunk.Repository.open(storage)
    except Exception:
        return icechunk.Repository.create(storage)


def minio_icechunk_repo(prefix: str) -> icechunk.Repository:
    """Create a fresh MinIO-backed Icechunk repository at the given prefix.

    prefix is appended under MINIO_PREFIX so all test data stays in one place.
    HTTPS is used (allow_http=False); force_path_style=True for MinIO compatibility.
    """
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    bucket = os.environ["MINIO_BUCKET"]
    base_prefix = os.environ.get("MINIO_PREFIX", "icechunk-atomicity-test")
    access_key = os.environ["MINIO_ACCESS_KEY"]
    secret_key = os.environ["MINIO_SECRET_KEY"]

    full_prefix = f"{base_prefix}/{prefix}"

    storage = icechunk.s3_storage(
        bucket=bucket,
        prefix=full_prefix,
        endpoint_url=endpoint,
        allow_http=False,
        access_key_id=access_key,
        secret_access_key=secret_key,
        force_path_style=True,
    )
    try:
        return icechunk.Repository.open(storage)
    except Exception:
        return icechunk.Repository.create(storage)


def minio_env_set() -> bool:
    """True if the required MinIO env vars are present."""
    return all(k in os.environ for k in ("MINIO_ENDPOINT", "MINIO_BUCKET", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"))


def probe_minio() -> tuple[bool, str]:
    """
    Probe the S3-compatible endpoint. Returns (reachable, message).

    Any HTTP response (including 4xx/5xx) counts as reachable — the endpoint is up
    and speaking HTTP. Only connection errors (timeout, DNS failure, TLS error) mean
    unreachable. This works for both MinIO and generic S3-compatible stores (e.g.
    NIRD/Sigma2) that don't expose /minio/health/live.
    """
    import urllib.request
    import ssl
    if not minio_env_set():
        return False, "MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY not set"
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    ctx = ssl.create_default_context()
    for url in [f"{endpoint}/minio/health/live", endpoint]:
        try:
            urllib.request.urlopen(url, timeout=5, context=ctx)
            return True, f"reachable at {url}"
        except urllib.request.HTTPError as e:
            # Any HTTP response means the server is up
            return True, f"reachable at {url} (HTTP {e.code})"
        except Exception:
            continue
    return False, f"endpoint unreachable: {endpoint}"
