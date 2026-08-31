# 🛒 Olist Lakehouse Platform

An end-to-end modern Lakehouse Platform designed for e-commerce data engineering, batch processing, and analytics using the **Brazilian E-Commerce Public Dataset by Olist**.

---

## 🏛️ Architecture Overview

```
[ Raw Olist CSVs ]
       │
       ▼ (Ingestion Pipeline: boto3 + sha256 metadata)
[ MinIO Bronze Layer ] ──> s3a://bronze/raw/...
       │
       ▼ (PySpark Transformation: Schemas, Cleansing, Deduplication)
[ MinIO Silver Layer ] ──> s3a://silver/tables/... (Parquet)
       │
       ▼ (dbt-duckdb: Star Schema Facts & Dimensions + Marts)
[ MinIO Gold Layer ] ───> s3a://gold/marts/... (Parquet & Views)
       │
       ▼ (BI & Analytics)
[ Streamlit / Metabase ]
```

---

## 📁 Repository Structure

```
olist-lakehouse-platform/
├── .github/workflows/          # CI/CD pipelines for linting, testing, and dbt
├── docker/
│   ├── Dockerfile.spark        # Spark 3.5 + Hadoop-AWS S3A connectors
│   ├── Dockerfile.dbt          # dbt + DuckDB runner
│   └── docker-compose.yml      # MinIO, MinIO-Init, Spark Master & Worker
├── configs/
│   ├── minio_config.yaml       # S3/MinIO bucket mappings and endpoints
│   └── spark_config.yaml       # PySpark driver, executor, and S3A configs
├── src/
│   ├── ingestion/
│   │   └── ingest_bronze.py    # Ingests raw CSVs into minio://bronze
│   ├── spark_jobs/             # Bronze -> Silver transformation jobs
│   └── utils/
│       ├── logger.py           # Structured logging
│       ├── minio_client.py     # Boto3 MinIO S3 wrapper
│       └── spark_session.py    # S3A MinIO SparkSession singleton
├── dbt_olist/                  # dbt models (Silver -> Gold star schema)
├── tests/                      # Unit & integration tests
├── dashboard/                  # Streamlit BI app
├── Makefile                    # Developer commands
├── pyproject.toml              # Python project metadata & tool config
├── requirements.txt            # Python dependencies
└── .env.example                # Sample environment variables
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.12+
- Docker & Docker Compose

### 2. Environment & Dependency Setup
```bash
# Create Python virtual environment and install dependencies
make venv
make install
```

### 3. Launch Lakehouse Infrastructure
```bash
# Start MinIO and Spark cluster
make up
```

Access Web UIs:
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)
- **Spark Master UI**: [http://localhost:8080](http://localhost:8080)
- **Spark Worker UI**: [http://localhost:8081](http://localhost:8081)

### 4. Run Bronze Layer Ingestion
```bash
# Ingest local datasets (or auto-generate starter samples if data/raw is empty)
make ingest
```

### 5. Run Unit Tests & Linting
```bash
make test
make lint
```
