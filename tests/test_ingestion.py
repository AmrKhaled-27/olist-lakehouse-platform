"""Unit tests for Bronze Ingestion Pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from src.ingestion.ingest_bronze import BronzeIngestionPipeline, OLIST_DATASET_DEFINITIONS


def test_calculate_checksum(temp_data_dir: Path):
    """Test SHA256 checksum calculation."""
    test_file = temp_data_dir / "sample.csv"
    test_file.write_text("col1,col2\nval1,val2\n", encoding="utf-8")

    checksum = BronzeIngestionPipeline.calculate_file_checksum(test_file)
    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_create_sample_datasets(temp_data_dir: Path):
    """Test generation of sample datasets when raw files are missing."""
    pipeline = BronzeIngestionPipeline(bronze_bucket="test-bronze")
    datasets = pipeline.create_sample_datasets(temp_data_dir)

    assert len(datasets) == len(OLIST_DATASET_DEFINITIONS)
    for key, path in datasets.items():
        assert path.exists()
        assert path.stat().st_size > 0


def test_dry_run_ingestion(temp_data_dir: Path):
    """Test ingestion pipeline in dry-run mode."""
    mock_minio = MagicMock()
    pipeline = BronzeIngestionPipeline(minio_client=mock_minio, bronze_bucket="test-bronze")

    results = pipeline.ingest_datasets(
        data_dir=temp_data_dir,
        dry_run=True,
        allow_sample_generation=True,
    )

    assert len(results) == 9
    assert all(r["status"] == "SUCCESS" for r in results)
    # Ensure minio_client.upload_file was not called during dry-run
    mock_minio.upload_file.assert_not_called()


@patch("kaggle.api.kaggle_api_extended.KaggleApi")
def test_download_from_kaggle_success(mock_kaggle_api_class, temp_data_dir: Path):
    """Test successful Kaggle download call."""
    mock_api_instance = MagicMock()
    mock_kaggle_api_class.return_value = mock_api_instance

    pipeline = BronzeIngestionPipeline(bronze_bucket="test-bronze")
    success = pipeline.download_from_kaggle(target_dir=temp_data_dir)

    assert success is True
    mock_api_instance.authenticate.assert_called_once()
    mock_api_instance.dataset_download_files.assert_called_once_with(
        "olistbr/brazilian-ecommerce", path=str(temp_data_dir), unzip=True
    )


@patch("kaggle.api.kaggle_api_extended.KaggleApi")
def test_download_from_kaggle_auth_error(mock_kaggle_api_class, temp_data_dir: Path):
    """Test graceful handling of Kaggle authentication errors."""
    mock_api_instance = MagicMock()
    mock_api_instance.authenticate.side_effect = Exception("Credentials not found")
    mock_kaggle_api_class.return_value = mock_api_instance

    pipeline = BronzeIngestionPipeline(bronze_bucket="test-bronze")
    success = pipeline.download_from_kaggle(target_dir=temp_data_dir)

    assert success is False
