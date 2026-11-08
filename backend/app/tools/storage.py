"""Dataset storage: local filesystem (dev) or Amazon S3 (cloud).

Containers are ephemeral, so in ECS/EKS you'll switch STORAGE_BACKEND=s3 and
give the task/pod an IAM role -- a key lesson of the deployment journey.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings

log = logging.getLogger(__name__)

DATASET_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_dataset_name(name: str) -> str:
    if not DATASET_NAME_RE.match(name):
        raise ValueError("Dataset name must be 1-64 chars of letters, digits, '_' or '-'.")
    return name


def safe_table_filename(filename: str) -> str:
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[^a-z0-9_]", "_", stem).strip("_") or "table"
    if stem[0].isdigit():
        stem = f"t_{stem}"
    if Path(filename).suffix.lower() != ".csv":
        raise ValueError("Only .csv files are supported.")
    return f"{stem[:60]}.csv"


@dataclass
class DatasetFiles:
    name: str
    files: list[str]


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def list_datasets(self) -> list[DatasetFiles]:
        out = []
        for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
            files = sorted(f.name for f in d.glob("*.csv"))
            if files and DATASET_NAME_RE.match(d.name):
                out.append(DatasetFiles(d.name, files))
        return out

    def save(self, dataset: str, filename: str, content: bytes) -> None:
        target = self.root / safe_dataset_name(dataset)
        target.mkdir(parents=True, exist_ok=True)
        (target / safe_table_filename(filename)).write_bytes(content)

    def local_dir(self, dataset: str) -> Path:
        path = self.root / safe_dataset_name(dataset)
        if not path.is_dir():
            raise FileNotFoundError(f"Dataset '{dataset}' not found.")
        return path


class S3Storage:
    def __init__(self, bucket: str, prefix: str, cache_dir: Path, region: str) -> None:
        import boto3

        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self.cache_dir = cache_dir.resolve()
        self.s3 = boto3.client("s3", region_name=region)

    def _keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [o["Key"] for o in page.get("Contents", [])]
        return keys

    def list_datasets(self) -> list[DatasetFiles]:
        grouped: dict[str, list[str]] = {}
        for key in self._keys(self.prefix):
            rel = key[len(self.prefix) :]
            if rel.count("/") == 1 and rel.endswith(".csv"):
                ds, f = rel.split("/")
                if DATASET_NAME_RE.match(ds):
                    grouped.setdefault(ds, []).append(f)
        return [DatasetFiles(k, sorted(v)) for k, v in sorted(grouped.items())]

    def save(self, dataset: str, filename: str, content: bytes) -> None:
        key = f"{self.prefix}{safe_dataset_name(dataset)}/{safe_table_filename(filename)}"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType="text/csv")

    def local_dir(self, dataset: str) -> Path:
        """Download the dataset into a local cache so DuckDB can read it."""
        target = self.cache_dir / safe_dataset_name(dataset)
        target.mkdir(parents=True, exist_ok=True)
        keys = self._keys(f"{self.prefix}{dataset}/")
        if not keys:
            raise FileNotFoundError(f"Dataset '{dataset}' not found in s3://{self.bucket}.")
        for key in keys:
            if key.endswith(".csv"):
                self.s3.download_file(self.bucket, key, str(target / Path(key).name))
        log.info("Synced dataset %s from S3 (%d files)", dataset, len(keys))
        return target


def build_storage(s: Settings) -> LocalStorage | S3Storage:
    if s.storage_backend == "s3":
        if not s.s3_bucket:
            raise ValueError("S3_BUCKET must be set when STORAGE_BACKEND=s3")
        return S3Storage(s.s3_bucket, s.s3_prefix, s.cache_dir, s.aws_region)
    return LocalStorage(s.data_dir)
