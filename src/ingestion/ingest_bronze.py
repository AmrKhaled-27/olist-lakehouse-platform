"""Bronze Ingestion Pipeline for Olist Lakehouse Platform.

Lands raw Olist CSV datasets into MinIO Bronze bucket (s3://bronze/raw/...)
with ingestion audit metadata (batch ID, timestamp, file size, and SHA256 checksum).
Supports local files, starter sample generation, and automated Kaggle API downloading.
"""

import argparse
import hashlib
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ingestion.constants import (
    DEFAULT_BRONZE_BUCKET,
    DEFAULT_RAW_DATA_PATH,
    KAGGLE_DATASET_SLUG,
    OLIST_DATASET_DEFINITIONS,
    SAMPLE_DATASETS_PAYLOAD,
)
from src.utils.logger import get_logger
from src.utils.minio_client import MinioLakehouseClient

logger = get_logger(__name__)


class BronzeIngestionPipeline:
    """Orchestrates landing raw CSV files into the MinIO Bronze Lakehouse layer."""

    def __init__(
        self,
        minio_client: Optional[MinioLakehouseClient] = None,
        bronze_bucket: Optional[str] = None,
    ):
        """Initialize the Bronze ingestion pipeline."""
        self.minio_client = minio_client or MinioLakehouseClient()
        self.bronze_bucket = (
            bronze_bucket or os.getenv("MINIO_BUCKET_BRONZE") or DEFAULT_BRONZE_BUCKET
        )

    @staticmethod
    def calculate_file_checksum(file_path: Path) -> str:
        """Compute SHA256 checksum of a local file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    def discover_local_datasets(self, data_dir: Path) -> Dict[str, Path]:
        """Scan directory for matching Olist CSV files."""
        found_datasets: Dict[str, Path] = {}
        if not data_dir.exists():
            logger.warning("Data directory '%s' does not exist.", data_dir)
            return found_datasets

        for dataset_key, meta in OLIST_DATASET_DEFINITIONS.items():
            expected_name = meta["filename"]
            candidate_path = data_dir / expected_name
            if candidate_path.is_file():
                found_datasets[dataset_key] = candidate_path

        return found_datasets

    def download_from_kaggle(
        self,
        target_dir: Path,
        dataset_slug: str = KAGGLE_DATASET_SLUG,
    ) -> bool:
        """Download and extract official dataset from Kaggle using Kaggle API.

        Requires ~/.kaggle/kaggle.json or KAGGLE_USERNAME & KAGGLE_KEY environment variables.
        """
        logger.info("Initiating Kaggle download for dataset '%s'...", dataset_slug)
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
            logger.info("Kaggle API authentication successful.")

            logger.info("Downloading and unzipping '%s' into '%s'...", dataset_slug, target_dir)
            api.dataset_download_files(dataset_slug, path=str(target_dir), unzip=True)
            logger.info("Successfully downloaded and unpacked Kaggle dataset into %s", target_dir)
            return True
        except Exception as e:
            logger.error("Failed to download from Kaggle: %s", e)
            logger.error(
                "Tip: Create a token at https://www.kaggle.com/settings and save kaggle.json "
                "to ~/.kaggle/kaggle.json, or set KAGGLE_USERNAME & KAGGLE_KEY."
            )
            return False

    def create_sample_datasets(self, target_dir: Path) -> Dict[str, Path]:
        """Generate minimal sample CSV files for testing when raw files are not present."""
        target_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in SAMPLE_DATASETS_PAYLOAD.items():
            sample_file = target_dir / filename
            if not sample_file.exists():
                sample_file.write_text(content, encoding="utf-8")
                logger.info("Generated sample dataset file: %s", sample_file)

        return self.discover_local_datasets(target_dir)

    def ingest_datasets(
        self,
        data_dir: Path,
        dry_run: bool = False,
        allow_sample_generation: bool = False,
        download_kaggle: bool = False,
    ) -> List[Dict[str, Any]]:
        """Run Bronze ingestion for all detected Olist datasets.

        Args:
            data_dir: Path to directory containing raw CSVs.
            dry_run: If True, validate and print plan without writing to MinIO.
            allow_sample_generation: If True and no CSVs exist, generate sample files.
            download_kaggle: If True, download official dataset from Kaggle first.

        Returns:
            List of ingestion summary records.
        """
        batch_id = (
            f"batch_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_"
            f"{uuid.uuid4().hex[:6]}"
        )
        ingestion_timestamp = datetime.now(timezone.utc).isoformat()

        logger.info("=" * 70)
        logger.info("Starting Bronze Layer Ingestion [Batch ID: %s]", batch_id)
        logger.info("Source directory: %s", data_dir.resolve())
        logger.info("Target MinIO bucket: %s", self.bronze_bucket)
        logger.info("=" * 70)

        # Trigger Kaggle download if requested
        if download_kaggle:
            self.download_from_kaggle(data_dir)

        # Ensure MinIO bucket exists
        if not dry_run:
            self.minio_client.create_bucket_if_not_exists(self.bronze_bucket)

        # Discover datasets
        datasets = self.discover_local_datasets(data_dir)

        if not datasets and allow_sample_generation:
            logger.info("No datasets found in %s. Generating starter sample datasets...", data_dir)
            datasets = self.create_sample_datasets(data_dir)

        if not datasets:
            logger.error(
                "No valid Olist CSV files found in '%s'. Expected files: %s",
                data_dir,
                [m["filename"] for m in OLIST_DATASET_DEFINITIONS.values()],
            )
            return []

        logger.info("Discovered %d / 9 Olist datasets to ingest.", len(datasets))

        ingestion_results: List[Dict[str, Any]] = []

        for key, file_path in datasets.items():
            meta = OLIST_DATASET_DEFINITIONS[key]
            file_size_bytes = file_path.stat().st_size
            checksum = self.calculate_file_checksum(file_path)
            target_object_key = f"{meta['target_prefix']}/{file_path.name}"

            audit_metadata = {
                "batch-id": batch_id,
                "ingestion-timestamp": ingestion_timestamp,
                "dataset-name": key,
                "sha256-checksum": checksum,
                "source-filename": file_path.name,
                "source-filesize-bytes": str(file_size_bytes),
            }

            if dry_run:
                logger.info(
                    "[DRY-RUN] Would upload '%s' (%d bytes) -> s3://%s/%s",
                    file_path.name,
                    file_size_bytes,
                    self.bronze_bucket,
                    target_object_key,
                )
                destination_uri = f"s3://{self.bronze_bucket}/{target_object_key}"
            else:
                destination_uri = self.minio_client.upload_file(
                    local_path=str(file_path),
                    bucket_name=self.bronze_bucket,
                    object_name=target_object_key,
                    metadata=audit_metadata,
                )

            ingestion_results.append(
                {
                    "dataset": key,
                    "filename": file_path.name,
                    "size_bytes": file_size_bytes,
                    "checksum": checksum[:12] + "...",
                    "destination": destination_uri,
                    "batch_id": batch_id,
                    "status": "SUCCESS",
                }
            )

        # Print summary table
        logger.info("=" * 70)
        logger.info("Bronze Layer Ingestion Completed Successfully")
        logger.info("Summary of %d Ingested Datasets:", len(ingestion_results))
        for res in ingestion_results:
            logger.info(
                "  • %-25s | %8d bytes | %s",
                res["dataset"],
                res["size_bytes"],
                res["destination"],
            )
        logger.info("=" * 70)

        return ingestion_results


def run_ingestion(
    data_dir: str = DEFAULT_RAW_DATA_PATH,
    bucket: Optional[str] = None,
    dry_run: bool = False,
    generate_samples: bool = False,
    download_kaggle: bool = False,
) -> int:
    """CLI entry point for bronze data ingestion."""
    pipeline = BronzeIngestionPipeline(bronze_bucket=bucket)
    results = pipeline.ingest_datasets(
        data_dir=Path(data_dir),
        dry_run=dry_run,
        allow_sample_generation=generate_samples,
        download_kaggle=download_kaggle,
    )
    return 0 if results else 1


def main():
    """Parse CLI arguments and run ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest raw Olist CSV datasets into MinIO Bronze Layer."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.getenv("RAW_DATA_PATH", DEFAULT_RAW_DATA_PATH),
        help="Path to directory containing Olist CSV dataset files (default: ./data/raw)",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default=os.getenv("MINIO_BUCKET_BRONZE", DEFAULT_BRONZE_BUCKET),
        help="Target MinIO bucket (default: bronze)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files and print plan without writing to MinIO",
    )
    parser.add_argument(
        "--generate-samples",
        action="store_true",
        help="Generate sample Olist CSV files in data-dir if no files are found",
    )
    parser.add_argument(
        "--download-kaggle",
        action="store_true",
        help="Download and extract official dataset from Kaggle into data-dir",
    )

    args = parser.parse_args()
    sys.exit(
        run_ingestion(
            data_dir=args.data_dir,
            bucket=args.bucket,
            dry_run=args.dry_run,
            generate_samples=args.generate_samples,
            download_kaggle=args.download_kaggle,
        )
    )


if __name__ == "__main__":
    main()
